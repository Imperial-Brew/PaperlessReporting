import asyncio
import os

from scripts.pipeline.builder import PipelineBuilder
from scripts.pipeline.processors import (
    PaperlessPartsDataAcquisitionStage,
    QuoteTransformer,
    QuoteItemTransformer,
    CSVLoader
)
from scripts.pipeline.validators import (
    QuoteValidator,
    QuoteItemValidator,
)
from scripts.pipeline.orchestrator import ContextExtractor
from scripts.pipeline.context_registry import set_global_context

# Get the project root directory
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


async def run_quote_pipeline():
    print("\n--- Running Quote Pipeline (7800-7899) ---")

    quote_pipeline = (
        PipelineBuilder("quote_pipeline")
        .add_acquisition(PaperlessPartsDataAcquisitionStage(start_id=7800, end_id=7899))
        .add_batch_processor(QuoteValidator())
        .add_batch_processor(QuoteTransformer())
        .add_loading(CSVLoader(os.path.join(PROJECT_ROOT, "data_real", "quotes.csv")))
        .build()
    )

    quote_pipeline.stages[0].configure_timeout(timeout=300.0)

    print("Starting quote pipeline execution...")
    quote_output = await quote_pipeline.run(None)
    print(f"Quote pipeline execution completed. Output: {quote_output is not None}")

    # Always try to get quote items from the acquisition stage, regardless of pipeline output
    quote_items = quote_pipeline.stages[0].get_context("quote_items")
    print(f"Quote items retrieved from context: {quote_items is not None}")

    if quote_items:
        print(f"Quote items type: {type(quote_items)}")
        print(f"Quote items length: {len(quote_items)}")
        set_global_context("quote_pipeline", "quote_items", quote_items)
        print(f"Stored {len(quote_items)} quote items in context.")
    else:
        print("No quote items found in context.")

    # Additional information about the pipeline output
    if quote_output is not None:
        print(f"Quote output type: {type(quote_output)}")
        if isinstance(quote_output, list):
            print(f"Quote output length: {len(quote_output)}")
    else:
        print("Quote pipeline returned None output.")


async def run_quote_item_pipeline():
    print("\n--- Running Quote Item Pipeline (from context) ---")

    # Create a custom context extractor that explicitly specifies the namespace
    from scripts.pipeline.context_registry import get_global_context
    from scripts.pipeline.base import TransformationStage
    from typing import Any, Dict, List


    # Create a custom context extractor that explicitly specifies the namespace
    class QuoteItemsExtractor(TransformationStage[Any, List[Dict[str, Any]]]):
        def __init__(self):
            super().__init__("quote_items_extractor")

        async def transform(self, _: Any) -> List[Dict[str, Any]]:
            items = get_global_context("quote_pipeline", "quote_items")
            if items is None:
                raise KeyError("Quote items not found in global context")
            return items

    # Create a custom pass-through transformer that doesn't modify the data
    class PassThroughTransformer(TransformationStage[List[Dict[str, Any]], List[Dict[str, Any]]]):
        def __init__(self):
            super().__init__("pass_through_transformer")

        async def transform(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            return data

    quote_item_pipeline = (
        PipelineBuilder("quote_item_pipeline")
        .add_stage(QuoteItemsExtractor())
        .add_batch_processor(QuoteItemValidator())
        # Skip the QuoteItemTransformer since the items are already in the correct format
        # Instead, use a pass-through transformer that doesn't modify the data
        .add_stage(PassThroughTransformer())
        .add_loading(CSVLoader(os.path.join(PROJECT_ROOT, "data_real", "quote_items.csv")))
        .build()
    )

    print("Starting quote item pipeline execution...")
    try:
        quote_item_output = await quote_item_pipeline.run(None)
        print(f"Quote item pipeline execution completed. Output: {quote_item_output is not None}")

        if quote_item_output is not None:
            print(f"Quote item output type: {type(quote_item_output)}")
            if isinstance(quote_item_output, list):
                print(f"Quote item output length: {len(quote_item_output)}")
        else:
            print("Quote item pipeline returned None output.")
    except Exception as e:
        print(f"Error running quote item pipeline: {str(e)}")


async def main():
    # Ensure data_real directory exists
    data_real_dir = os.path.join(PROJECT_ROOT, "data_real")
    os.makedirs(data_real_dir, exist_ok=True)

    await run_quote_pipeline()
    await run_quote_item_pipeline()


if __name__ == "__main__":
    asyncio.run(main())

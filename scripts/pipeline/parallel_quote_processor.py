"""
Parallel processing for quote items in the pipeline framework.

This module provides parallel implementations of quote item processing
to improve performance when processing large numbers of quotes and quote items.
"""

import asyncio
from typing import Any, Dict, List, Optional, Union

from scripts.pipeline.base import PipelineStage, TransformationStage
from scripts.pipeline.orchestrator import Pipeline, ContextExtractor
from scripts.pipeline.processors import BatchProcessor, QuoteItemTransformer, QuoteItemExtractor
from scripts.pipeline.validators import QuoteItemValidator, QuoteValidator
from scripts.utils.logging_config import get_logger

# Get logger for this module
logger = get_logger(__name__)


class ParallelQuoteItemProcessor:
    """
    Factory for creating pipelines that process quote items in parallel.

    This class provides methods for creating pipelines that extract and process
    quote items from quotes with parallel processing for improved performance.
    """

    @staticmethod
    def create_parallel_extraction_pipeline(
        max_concurrency: int = 5,
        batch_size: int = 100,
        output_path: Optional[str] = None,
        name: str = "parallel_quote_item_extraction_pipeline"
    ) -> Pipeline:
        """
        Create a pipeline for extracting and processing quote items in parallel.

        This pipeline extracts quote items from a list of quotes and processes
        them in parallel for improved performance.

        Args:
            max_concurrency: Maximum number of items to process concurrently
            batch_size: Maximum number of items to process in a single batch
            output_path: Path to the output CSV file (if None, no CSV is generated)
            name: Name of the pipeline

        Returns:
            Pipeline instance
        """
        from scripts.pipeline.processors import CSVLoader

        # Create pipeline
        pipeline = Pipeline(name)

        # Add extraction stage with parallel processing
        class ParallelQuoteItemExtractor(TransformationStage[List[Dict[str, Any]], List[Dict[str, Any]]]):
            """
            Transformation stage that extracts quote items from a list of quotes in parallel.
            """

            def __init__(self, name: str = "parallel_quote_item_extractor"):
                super().__init__(name)
                self.extractor = QuoteItemExtractor()

            async def transform(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
                """
                Extract quote items from a list of quotes in parallel.

                Args:
                    data: List of quotes

                Returns:
                    List of quote items
                """
                if not data:
                    return []

                # Create tasks for parallel extraction
                tasks = []
                for quote in data:
                    tasks.append(self.extractor.transform(quote))

                # Use asyncio.gather to run tasks in parallel
                results = await asyncio.gather(*tasks)

                # Flatten the list of lists
                quote_items = [item for sublist in results for item in sublist]

                # Record metrics
                self.record_metric("quotes_processed", len(data))
                self.record_metric("quote_items_extracted", len(quote_items))

                return quote_items

        # Add extraction stage
        pipeline.add_stage(ParallelQuoteItemExtractor())

        # Add validation stage with batch processing
        validator = QuoteItemValidator()
        batch_validator = BatchProcessor(
            validator,
            name="batch_quote_item_validator",
            batch_size=batch_size,
            max_concurrency=max_concurrency
        )
        pipeline.add_stage(batch_validator)

        # Add transformation stage with batch processing
        transformer = QuoteItemTransformer()
        batch_transformer = BatchProcessor(
            transformer,
            name="batch_quote_item_transformer",
            batch_size=batch_size,
            max_concurrency=max_concurrency
        )
        pipeline.add_stage(batch_transformer)

        # Add CSV loader if output path is provided
        if output_path:
            pipeline.add_stage(CSVLoader(output_path))

        return pipeline

    @staticmethod
    def create_parallel_processing_pipeline(
        max_concurrency: int = 5,
        batch_size: int = 100,
        output_path: Optional[str] = None,
        name: str = "parallel_quote_item_processing_pipeline"
    ) -> Pipeline:
        """
        Create a pipeline for processing quote items in parallel.

        This pipeline processes quote items from the context in parallel
        for improved performance.

        Args:
            max_concurrency: Maximum number of items to process concurrently
            batch_size: Maximum number of items to process in a single batch
            output_path: Path to the output CSV file (if None, no CSV is generated)
            name: Name of the pipeline

        Returns:
            Pipeline instance
        """
        from scripts.pipeline.processors import CSVLoader

        # Create pipeline
        pipeline = Pipeline(name)

        # Add context extraction stage
        pipeline.add_stage(ContextExtractor("quote_items", default=[]))

        # Add validation stage with batch processing
        validator = QuoteItemValidator()
        batch_validator = BatchProcessor(
            validator,
            name="batch_quote_item_validator",
            batch_size=batch_size,
            max_concurrency=max_concurrency
        )
        pipeline.add_stage(batch_validator)

        # Add transformation stage with batch processing
        transformer = QuoteItemTransformer()
        batch_transformer = BatchProcessor(
            transformer,
            name="batch_quote_item_transformer",
            batch_size=batch_size,
            max_concurrency=max_concurrency
        )
        pipeline.add_stage(batch_transformer)

        # Add CSV loader if output path is provided
        if output_path:
            pipeline.add_stage(CSVLoader(output_path))

        return pipeline

    @staticmethod
    def create_parallel_validation_pipeline(
        max_concurrency: int = 5,
        batch_size: int = 100,
        name: str = "parallel_quote_item_validation_pipeline"
    ) -> Pipeline:
        """
        Create a pipeline for validating quote items in parallel.

        Args:
            max_concurrency: Maximum number of items to process concurrently
            batch_size: Maximum number of items to process in a single batch
            name: Name of the pipeline

        Returns:
            Pipeline instance
        """
        # Create pipeline
        pipeline = Pipeline(name)

        # Add validation stage with batch processing
        validator = QuoteItemValidator()
        batch_validator = BatchProcessor(
            validator,
            name="batch_quote_item_validator",
            batch_size=batch_size,
            max_concurrency=max_concurrency
        )
        pipeline.add_stage(batch_validator)

        return pipeline

    @staticmethod
    def create_parallel_transformation_pipeline(
        max_concurrency: int = 5,
        batch_size: int = 100,
        name: str = "parallel_quote_item_transformation_pipeline"
    ) -> Pipeline:
        """
        Create a pipeline for transforming quote items in parallel.

        Args:
            max_concurrency: Maximum number of items to process concurrently
            batch_size: Maximum number of items to process in a single batch
            name: Name of the pipeline

        Returns:
            Pipeline instance
        """
        # Create pipeline
        pipeline = Pipeline(name)

        # Add validation stage with batch processing
        validator = QuoteItemValidator()
        batch_validator = BatchProcessor(
            validator,
            name="batch_quote_item_validator",
            batch_size=batch_size,
            max_concurrency=max_concurrency
        )
        pipeline.add_stage(batch_validator)

        # Add transformation stage with batch processing
        transformer = QuoteItemTransformer()
        batch_transformer = BatchProcessor(
            transformer,
            name="batch_quote_item_transformer",
            batch_size=batch_size,
            max_concurrency=max_concurrency
        )
        pipeline.add_stage(batch_transformer)

        return pipeline


class ParallelQuoteProcessor:
    """
    Factory for creating pipelines that process quotes and quote items in parallel.

    This class provides methods for creating pipelines that process quotes
    and their items with parallel processing for improved performance.
    """

    @staticmethod
    def create_acquisition_pipeline(
        start_id: Optional[int] = None,
        end_id: Optional[int] = None,
        max_concurrency: int = 5,
        batch_size: int = 100,
        output_path: Optional[str] = None,
        items_output_path: Optional[str] = None,
        name: str = "parallel_quote_acquisition_pipeline"
    ) -> Pipeline:
        """
        Create a pipeline for acquiring and processing quotes and their items in parallel.

        Args:
            start_id: Starting quote ID
            end_id: Ending quote ID
            max_concurrency: Maximum number of items to process concurrently
            batch_size: Maximum number of items to process in a single batch
            output_path: Path to the output CSV file for quotes
            items_output_path: Path to the output CSV file for quote items
            name: Name of the pipeline

        Returns:
            Pipeline instance
        """
        from scripts.pipeline.processors import QuotesDataAcquisitionStage, QuoteTransformer, BatchProcessor, CSVLoader

        # Create pipeline
        pipeline = Pipeline(name)

        # Add acquisition stage
        acquisition_stage = QuotesDataAcquisitionStage(start_id=start_id, end_id=end_id)
        pipeline.add_stage(acquisition_stage)

        # Add validation stage with batch processing
        validator = QuoteValidator()
        batch_validator = BatchProcessor(
            validator,
            name="batch_quote_validator",
            batch_size=batch_size,
            max_concurrency=max_concurrency
        )
        pipeline.add_stage(batch_validator)

        # Add transformation stage with batch processing
        transformer = QuoteTransformer()
        batch_transformer = BatchProcessor(
            transformer,
            name="batch_quote_transformer",
            batch_size=batch_size,
            max_concurrency=max_concurrency
        )
        pipeline.add_stage(batch_transformer)

        # Add CSV loader if output path is provided
        if output_path:
            pipeline.add_stage(CSVLoader(output_path))

        # Create and add a parallel stage for processing quote items if needed
        if items_output_path:
            # Create a parallel stage that will run after the main pipeline
            class QuoteItemsProcessor(PipelineStage[List[Dict[str, Any]], List[Dict[str, Any]]]):
                """
                Pipeline stage that processes quote items from the context.
                """

                def __init__(self, acquisition_stage: QuotesDataAcquisitionStage, output_path: str):
                    super().__init__("quote_items_processor")
                    self.acquisition_stage = acquisition_stage
                    self.output_path = output_path

                async def process_core(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
                    """
                    Process quote items from the context.

                    Args:
                        data: List of processed quotes (not used)

                    Returns:
                        List of processed quote items
                    """
                    # Get quote items from context
                    quote_items = self.acquisition_stage.get_context("quote_items", [])

                    if not quote_items:
                        logger.warning("No quote items found in context")
                        return []

                    # Create a pipeline for processing quote items
                    items_pipeline = ParallelQuoteItemProcessor.create_parallel_processing_pipeline(
                        max_concurrency=max_concurrency,
                        batch_size=batch_size,
                        output_path=self.output_path,
                        name="quote_items_processor_pipeline"
                    )

                    # Set the context for the pipeline
                    for stage in items_pipeline.stages:
                        stage.set_context("quote_items", quote_items)

                    # Run the pipeline
                    processed_items = await items_pipeline.run(None)

                    return processed_items

            # Add the quote items processor stage
            pipeline.add_stage(QuoteItemsProcessor(acquisition_stage, items_output_path))

        return pipeline


# Example usage
async def process_quotes_in_parallel(
    start_id: int,
    end_id: int,
    max_concurrency: int = 5,
    output_dir: str = "data_raw"
) -> None:
    """
    Process quotes and their items in parallel.

    Args:
        start_id: Starting quote ID
        end_id: Ending quote ID
        max_concurrency: Maximum number of items to process concurrently
        output_dir: Directory for output files
    """
    import os
    from pathlib import Path

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Create output paths
    quotes_path = os.path.join(output_dir, "quotes", "quotes.csv")
    items_path = os.path.join(output_dir, "quote_items", "quote_items.csv")

    # Ensure parent directories exist
    os.makedirs(os.path.dirname(quotes_path), exist_ok=True)
    os.makedirs(os.path.dirname(items_path), exist_ok=True)

    # Create and run the pipeline
    pipeline = ParallelQuoteProcessor.create_acquisition_pipeline(
        start_id=start_id,
        end_id=end_id,
        max_concurrency=max_concurrency,
        output_path=quotes_path,
        items_output_path=items_path
    )

    logger.info(f"Processing quotes {start_id} to {end_id} with max concurrency {max_concurrency}")
    await pipeline.run(None)
    logger.info("Processing completed")

    # Print metrics
    metrics = pipeline.get_metrics()
    logger.info(f"Pipeline duration: {metrics['duration']:.2f}s")
    logger.info(f"Quotes processed: {metrics['stage_metrics']['batch_quote_transformer']['metrics']['total_items']}")

    # Get quote items metrics if available
    if "quote_items_processor" in metrics["stage_metrics"]:
        items_metrics = metrics["stage_metrics"]["quote_items_processor"]["metrics"]
        if "pipeline_metrics" in items_metrics:
            items_pipeline_metrics = items_metrics["pipeline_metrics"]
            if "batch_quote_item_transformer" in items_pipeline_metrics["stage_metrics"]:
                transformer_metrics = items_pipeline_metrics["stage_metrics"]["batch_quote_item_transformer"]["metrics"]
                logger.info(f"Quote items processed: {transformer_metrics['total_items']}")


if __name__ == "__main__":
    import asyncio
    import argparse

    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Process quotes and their items in parallel")
    parser.add_argument("--start-id", type=int, help="Starting quote ID", default=1)
    parser.add_argument("--end-id", type=int, help="Ending quote ID", default=100)
    parser.add_argument("--max-concurrency", type=int, help="Maximum concurrency", default=5)
    parser.add_argument("--output-dir", type=str, help="Output directory", default="data_raw")

    args = parser.parse_args()

    # Run the processor
    asyncio.run(process_quotes_in_parallel(
        start_id=args.start_id,
        end_id=args.end_id,
        max_concurrency=args.max_concurrency,
        output_dir=args.output_dir
    ))

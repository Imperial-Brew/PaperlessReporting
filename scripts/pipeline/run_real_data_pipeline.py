"""
Script to run the pipeline with real data from the Paperless Parts API.

This script fetches quote data from the Paperless Parts API, processes it
through the pipeline, and saves the results to CSV files.
"""

import asyncio
import argparse
import os
import sys
from pathlib import Path
from typing import Optional, Union, Type

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

# Configure logging
from scripts.utils.logging_config import configure_logging, get_logger
configure_logging(level="INFO")
logger = get_logger(__name__)

# Import pipeline components
from scripts.pipeline.orchestrator import Pipeline, QuotePipeline
from scripts.pipeline.processors import PaperlessPartsDataAcquisitionStage, BatchProcessor, CSVLoader
from scripts.pipeline.validators import QuoteValidator
from scripts.pipeline.processors import QuoteTransformer
from scripts.pipeline.exceptions import PipelineError

# Import S3 integration (optional)
try:
    from scripts.pipeline.s3_integration import S3Loader, S3JSONLoader
    S3_AVAILABLE = True
except ImportError:
    logger.warning("S3 integration not available. Install boto3 to enable S3 support.")
    S3_AVAILABLE = False

# Import incremental processing (optional)
try:
    from scripts.pipeline.incremental import IncrementalDataAcquisitionStage
    INCREMENTAL_AVAILABLE = True
except ImportError:
    logger.warning("Incremental processing not available.")
    INCREMENTAL_AVAILABLE = False


class RealDataPipeline:
    """
    Factory for creating pipelines for processing real data from the Paperless Parts API.
    """

    @staticmethod
    def create_quotes_pipeline(start_id: int, end_id: int, 
                              output_path: str = None, 
                              s3_bucket: str = None,
                              s3_key: str = None,
                              s3_region: str = None,
                              include_revisions: bool = True,
                              incremental: bool = False,
                              state_file: str = None,
                              name: str = "real_quotes_pipeline") -> Pipeline:
        """
        Create a pipeline for fetching, validating, transforming, and exporting real quote data.

        Args:
            start_id: Starting quote ID
            end_id: Ending quote ID
            output_path: Path to the output CSV file (local filesystem)
            s3_bucket: S3 bucket name for output (if using S3)
            s3_key: S3 object key for output (if using S3)
            s3_region: AWS region for S3 (if using S3)
            include_revisions: Whether to include revised quotes
            incremental: Whether to process only new or changed quotes
            state_file: Path to the state file for tracking processed quotes
            name: Name of the pipeline

        Returns:
            Pipeline instance
        """
        # Create pipeline
        pipeline = Pipeline(name)

        # Add acquisition stage (incremental or regular)
        if incremental and INCREMENTAL_AVAILABLE:
            logger.info("Using incremental processing")
            acquisition_stage = IncrementalDataAcquisitionStage(
                start_id=start_id,
                end_id=end_id,
                include_revisions=include_revisions,
                state_file=state_file
            )
            # Configure a longer timeout for API requests
            acquisition_stage.configure_timeout(timeout=120.0)
            pipeline.add_stage(acquisition_stage)
        else:
            if incremental and not INCREMENTAL_AVAILABLE:
                logger.warning("Incremental processing requested but not available. Using regular processing.")
            acquisition_stage = PaperlessPartsDataAcquisitionStage(
                start_id=start_id,
                end_id=end_id,
                include_revisions=include_revisions
            )
            # Configure a longer timeout for API requests
            acquisition_stage.configure_timeout(timeout=120.0)
            pipeline.add_stage(acquisition_stage)

        # Add validation stage with batch processing
        pipeline.add_stage(BatchProcessor(QuoteValidator()))

        # Add transformation stage with batch processing
        pipeline.add_stage(BatchProcessor(QuoteTransformer()))

        # Add export stage (S3 or local filesystem)
        if s3_bucket and s3_key and S3_AVAILABLE:
            logger.info(f"Using S3 for output: s3://{s3_bucket}/{s3_key}")
            pipeline.add_stage(S3Loader(
                bucket_name=s3_bucket,
                object_key=s3_key,
                region_name=s3_region
            ))
        elif output_path:
            logger.info(f"Using local filesystem for output: {output_path}")
            pipeline.add_stage(CSVLoader(output_path))
        else:
            raise ValueError("Either output_path or (s3_bucket and s3_key) must be provided")

        return pipeline

    @staticmethod
    def create_quote_items_pipeline(acquisition_stage: PaperlessPartsDataAcquisitionStage, 
                                   output_path: str = None,
                                   s3_bucket: str = None,
                                   s3_key: str = None,
                                   s3_region: str = None,
                                   name: str = "real_quote_items_pipeline") -> Pipeline:
        """
        Create a pipeline for processing quote items extracted during acquisition.

        Args:
            acquisition_stage: Stage that provides quote items in its context
            output_path: Path to the output CSV file (local filesystem)
            s3_bucket: S3 bucket name for output (if using S3)
            s3_key: S3 object key for output (if using S3)
            s3_region: AWS region for S3 (if using S3)
            name: Name of the pipeline

        Returns:
            Pipeline instance
        """
        from scripts.pipeline.orchestrator import ValidateQuoteItems

        # Create a stage that extracts quote items from context
        class ExtractQuoteItems(QuoteTransformer):
            def __init__(self, acquisition_stage: PaperlessPartsDataAcquisitionStage):
                super().__init__("extract_quote_items")
                self.acquisition_stage = acquisition_stage

            async def transform(self, _: None) -> list:
                quote_items = self.acquisition_stage.get_context("quote_items", [])
                self.record_metric("quote_items_count", len(quote_items))
                return quote_items

        # Create pipeline
        pipeline = Pipeline(name)

        # Add extraction stage
        pipeline.add_stage(ExtractQuoteItems(acquisition_stage))

        # Add validation stage
        pipeline.add_stage(ValidateQuoteItems())

        # Add export stage (S3 or local filesystem)
        if s3_bucket and s3_key and S3_AVAILABLE:
            logger.info(f"Using S3 for quote items output: s3://{s3_bucket}/{s3_key}")
            pipeline.add_stage(S3Loader(
                bucket_name=s3_bucket,
                object_key=s3_key,
                region_name=s3_region
            ))
        elif output_path:
            logger.info(f"Using local filesystem for quote items output: {output_path}")
            pipeline.add_stage(CSVLoader(output_path))
        else:
            raise ValueError("Either output_path or (s3_bucket and s3_key) must be provided")

        return pipeline


async def process_real_data(
    start_id: int, 
    end_id: int, 
    output_dir: Optional[str] = None, 
    s3_bucket: Optional[str] = None,
    s3_prefix: Optional[str] = None,
    s3_region: Optional[str] = None,
    include_revisions: bool = True,
    incremental: bool = False,
    state_file: Optional[str] = None
):
    """
    Process real quote data from the Paperless Parts API.

    Args:
        start_id: Starting quote ID
        end_id: Ending quote ID
        output_dir: Directory for output files (local filesystem)
        s3_bucket: S3 bucket name for output (if using S3)
        s3_prefix: S3 prefix (folder) for output files (if using S3)
        s3_region: AWS region for S3 (if using S3)
        include_revisions: Whether to include revised quotes
        incremental: Whether to process only new or changed quotes
        state_file: Path to the state file for tracking processed quotes
    """
    # Validate output options
    if not output_dir and not (s3_bucket and s3_prefix):
        raise ValueError("Either output_dir or (s3_bucket and s3_prefix) must be provided")

    # Create local output directory if needed
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    # Determine output paths or S3 keys
    quotes_csv_path = None
    quotes_s3_key = None
    items_csv_path = None
    items_s3_key = None

    if output_dir:
        quotes_csv_path = os.path.join(output_dir, "quotes.csv")
        items_csv_path = os.path.join(output_dir, "quote_items.csv")

    if s3_bucket and s3_prefix:
        # Use timestamp in S3 keys for versioning
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        quotes_s3_key = f"{s3_prefix}/quotes_{timestamp}.csv"
        items_s3_key = f"{s3_prefix}/quote_items_{timestamp}.csv"

    # Set default state file if incremental processing is enabled
    if incremental and not state_file:
        if output_dir:
            state_file = os.path.join(output_dir, "pipeline_state.json")
        else:
            state_file = "pipeline_state.json"
        logger.info(f"Using state file: {state_file}")

    # Create and run the quotes pipeline
    logger.info(f"Processing quotes from {start_id} to {end_id}")
    quotes_pipeline = RealDataPipeline.create_quotes_pipeline(
        start_id=start_id,
        end_id=end_id,
        output_path=quotes_csv_path,
        s3_bucket=s3_bucket,
        s3_key=quotes_s3_key,
        s3_region=s3_region,
        include_revisions=include_revisions,
        incremental=incremental,
        state_file=state_file
    )

    try:
        # Run the pipeline
        await quotes_pipeline.run(None)  # No input needed for acquisition stage
        logger.info("Quote processing completed successfully")

        # Print metrics
        metrics = quotes_pipeline.get_metrics()
        logger.info(f"Pipeline duration: {metrics['duration']:.2f}s")

        # Get the acquisition stage to use as context provider
        acquisition_stage = quotes_pipeline.stages[0]

        # Create and run the quote items pipeline
        items_pipeline = RealDataPipeline.create_quote_items_pipeline(
            acquisition_stage=acquisition_stage,
            output_path=items_csv_path,
            s3_bucket=s3_bucket,
            s3_key=items_s3_key,
            s3_region=s3_region
        )

        await items_pipeline.run(None)  # No input needed, items come from context

        if items_csv_path:
            logger.info(f"Quote items exported to {items_csv_path}")
        if s3_bucket and items_s3_key:
            logger.info(f"Quote items exported to s3://{s3_bucket}/{items_s3_key}")

    except PipelineError as e:
        logger.error(f"Pipeline error: {e.message}")
        for error in quotes_pipeline.get_metrics().get("errors", []):
            logger.error(f"  {error['stage_name']}: {error['error_message']}")
        raise


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Process real quote data from the Paperless Parts API")

    # Quote range arguments
    parser.add_argument("--start-id", type=int, help="Starting quote ID", default=7500)
    parser.add_argument("--end-id", type=int, help="Ending quote ID", default=7550)
    parser.add_argument("--no-revisions", action="store_true", help="Exclude revised quotes")

    # Output options
    output_group = parser.add_argument_group("Output Options")
    output_group.add_argument("--output-dir", type=str, help="Local output directory")

    # S3 options
    s3_group = parser.add_argument_group("S3 Options")
    s3_group.add_argument("--s3-bucket", type=str, help="S3 bucket name for output")
    s3_group.add_argument("--s3-prefix", type=str, help="S3 prefix (folder) for output files")
    s3_group.add_argument("--s3-region", type=str, help="AWS region for S3")

    # Processing options
    processing_group = parser.add_argument_group("Processing Options")
    processing_group.add_argument("--incremental", action="store_true", help="Process only new or changed quotes")
    processing_group.add_argument("--state-file", type=str, help="Path to the state file for tracking processed quotes")

    args = parser.parse_args()

    # Validate output options
    if not args.output_dir and not (args.s3_bucket and args.s3_prefix):
        parser.error("Either --output-dir or (--s3-bucket and --s3-prefix) must be provided")

    # Run the pipeline
    asyncio.run(process_real_data(
        start_id=args.start_id,
        end_id=args.end_id,
        output_dir=args.output_dir,
        s3_bucket=args.s3_bucket,
        s3_prefix=args.s3_prefix,
        s3_region=args.s3_region,
        include_revisions=not args.no_revisions,
        incremental=args.incremental,
        state_file=args.state_file
    ))

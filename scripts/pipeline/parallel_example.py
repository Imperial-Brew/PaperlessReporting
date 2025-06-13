"""
Example of using parallel processing in the pipeline framework.

This module demonstrates how to use the enhanced BatchProcessor and
the new ParallelStage to process data in parallel.
"""

import asyncio
import sys
import time
import random
from pathlib import Path
from typing import Dict, Any, List

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

# Configure logging
from scripts.utils.logging_config import configure_logging, get_logger
configure_logging(level="INFO")
logger = get_logger(__name__)

# Import pipeline components
from scripts.pipeline.base import PipelineStage
from scripts.pipeline.orchestrator import Pipeline
from scripts.pipeline.processors import BatchProcessor, ParallelStage


class SlowProcessor(PipelineStage[Dict[str, Any], Dict[str, Any]]):
    """
    A slow processor that simulates a time-consuming operation.
    
    This processor adds a delay to simulate a slow operation,
    then adds a timestamp to the input data.
    """
    
    def __init__(self, name: str = "slow_processor", min_delay: float = 0.1, max_delay: float = 0.5):
        """
        Initialize the slow processor.
        
        Args:
            name: Name of the processor
            min_delay: Minimum delay in seconds
            max_delay: Maximum delay in seconds
        """
        super().__init__(name)
        self.min_delay = min_delay
        self.max_delay = max_delay
    
    async def process_core(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process the input data with a delay.
        
        Args:
            data: Input data to process
            
        Returns:
            Processed data with timestamp
        """
        # Simulate a slow operation
        delay = random.uniform(self.min_delay, self.max_delay)
        await asyncio.sleep(delay)
        
        # Add timestamp and processor name
        result = data.copy()
        result["timestamp"] = time.time()
        result["processor"] = self.name
        result["delay"] = delay
        
        return result


async def demo_batch_processor():
    """
    Demonstrate the enhanced BatchProcessor with parallel processing.
    """
    logger.info("=== BatchProcessor Parallel Processing Demo ===")
    
    # Create a list of items to process
    items = [{"id": i, "value": f"Item {i}"} for i in range(20)]
    
    # Create a slow processor
    processor = SlowProcessor("demo_processor", min_delay=0.2, max_delay=1.0)
    
    # Create a batch processor with different concurrency settings
    sequential_batch = BatchProcessor(processor, name="sequential_batch", max_concurrency=1)
    parallel_batch = BatchProcessor(processor, name="parallel_batch", max_concurrency=5)
    highly_parallel_batch = BatchProcessor(processor, name="highly_parallel_batch", max_concurrency=10)
    
    # Process items sequentially
    logger.info("Processing items sequentially (max_concurrency=1)...")
    start_time = time.time()
    sequential_results = await sequential_batch.process(items)
    sequential_time = time.time() - start_time
    logger.info(f"Sequential processing completed in {sequential_time:.2f} seconds")
    
    # Process items with moderate parallelism
    logger.info("Processing items with moderate parallelism (max_concurrency=5)...")
    start_time = time.time()
    parallel_results = await parallel_batch.process(items)
    parallel_time = time.time() - start_time
    logger.info(f"Moderate parallel processing completed in {parallel_time:.2f} seconds")
    
    # Process items with high parallelism
    logger.info("Processing items with high parallelism (max_concurrency=10)...")
    start_time = time.time()
    highly_parallel_results = await highly_parallel_batch.process(items)
    highly_parallel_time = time.time() - start_time
    logger.info(f"High parallel processing completed in {highly_parallel_time:.2f} seconds")
    
    # Compare results
    logger.info(f"Sequential processing time: {sequential_time:.2f}s")
    logger.info(f"Moderate parallel processing time: {parallel_time:.2f}s")
    logger.info(f"High parallel processing time: {highly_parallel_time:.2f}s")
    logger.info(f"Speedup (moderate vs sequential): {sequential_time / parallel_time:.2f}x")
    logger.info(f"Speedup (high vs sequential): {sequential_time / highly_parallel_time:.2f}x")


async def demo_parallel_stage():
    """
    Demonstrate the ParallelStage for running multiple stages concurrently.
    """
    logger.info("\n=== ParallelStage Demo ===")
    
    # Create input data
    data = {"id": 1, "value": "Test"}
    
    # Create several slow processors with different delays
    fast_processor = SlowProcessor("fast_processor", min_delay=0.1, max_delay=0.3)
    medium_processor = SlowProcessor("medium_processor", min_delay=0.5, max_delay=0.8)
    slow_processor = SlowProcessor("slow_processor", min_delay=1.0, max_delay=1.5)
    very_slow_processor = SlowProcessor("very_slow_processor", min_delay=2.0, max_delay=3.0)
    
    # Create a pipeline with sequential stages
    sequential_pipeline = Pipeline("sequential_pipeline")
    sequential_pipeline.add_stage(fast_processor)
    sequential_pipeline.add_stage(medium_processor)
    sequential_pipeline.add_stage(slow_processor)
    sequential_pipeline.add_stage(very_slow_processor)
    
    # Create a pipeline with a parallel stage
    parallel_pipeline = Pipeline("parallel_pipeline")
    parallel_stage = ParallelStage("parallel_stage")
    parallel_stage.add_stage("fast", fast_processor)
    parallel_stage.add_stage("medium", medium_processor)
    parallel_stage.add_stage("slow", slow_processor)
    parallel_stage.add_stage("very_slow", very_slow_processor)
    parallel_pipeline.add_stage(parallel_stage)
    
    # Run the sequential pipeline
    logger.info("Running sequential pipeline...")
    start_time = time.time()
    sequential_result = await sequential_pipeline.run(data)
    sequential_time = time.time() - start_time
    logger.info(f"Sequential pipeline completed in {sequential_time:.2f} seconds")
    
    # Run the parallel pipeline
    logger.info("Running parallel pipeline...")
    start_time = time.time()
    parallel_result = await parallel_pipeline.run(data)
    parallel_time = time.time() - start_time
    logger.info(f"Parallel pipeline completed in {parallel_time:.2f} seconds")
    
    # Compare results
    logger.info(f"Sequential pipeline time: {sequential_time:.2f}s")
    logger.info(f"Parallel pipeline time: {parallel_time:.2f}s")
    logger.info(f"Speedup: {sequential_time / parallel_time:.2f}x")
    
    # Show the parallel results
    logger.info("Parallel pipeline results:")
    for stage_name, result in parallel_result.items():
        logger.info(f"  {stage_name}: processor={result['processor']}, delay={result['delay']:.2f}s")


async def demo_parallel_stage_with_timeout():
    """
    Demonstrate the ParallelStage with timeout handling.
    """
    logger.info("\n=== ParallelStage Timeout Demo ===")
    
    # Create input data
    data = {"id": 1, "value": "Test"}
    
    # Create several slow processors with different delays
    fast_processor = SlowProcessor("fast_processor", min_delay=0.1, max_delay=0.3)
    medium_processor = SlowProcessor("medium_processor", min_delay=0.5, max_delay=0.8)
    slow_processor = SlowProcessor("slow_processor", min_delay=1.0, max_delay=1.5)
    very_slow_processor = SlowProcessor("very_slow_processor", min_delay=2.0, max_delay=3.0)
    
    # Create a parallel stage with a short timeout
    parallel_stage = ParallelStage("parallel_stage_with_timeout")
    parallel_stage.add_stage("fast", fast_processor)
    parallel_stage.add_stage("medium", medium_processor)
    parallel_stage.add_stage("slow", slow_processor)
    parallel_stage.add_stage("very_slow", very_slow_processor)
    parallel_stage.set_timeout(1.0)  # Set a 1-second timeout
    
    # Create a pipeline with the parallel stage
    pipeline = Pipeline("timeout_pipeline")
    pipeline.add_stage(parallel_stage)
    
    # Run the pipeline
    logger.info("Running pipeline with 1-second timeout...")
    try:
        start_time = time.time()
        result = await pipeline.run(data)
        execution_time = time.time() - start_time
        logger.info(f"Pipeline completed in {execution_time:.2f} seconds")
        
        # Show the results
        logger.info("Results:")
        for stage_name, stage_result in result.items():
            if stage_result is None:
                logger.info(f"  {stage_name}: Timed out")
            else:
                logger.info(f"  {stage_name}: processor={stage_result['processor']}, delay={stage_result['delay']:.2f}s")
    
    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(f"Pipeline failed after {execution_time:.2f} seconds: {str(e)}")


async def main():
    """
    Run all the demos.
    """
    await demo_batch_processor()
    await demo_parallel_stage()
    await demo_parallel_stage_with_timeout()


if __name__ == "__main__":
    asyncio.run(main())
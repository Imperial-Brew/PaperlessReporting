"""
Test script for context sharing in the pipeline framework.

This script tests the functionality of the global context registry,
the enhanced ContextExtractor class, and the utility functions for
transferring context between pipelines.
"""

import asyncio
import sys
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
from scripts.pipeline.base import TransformationStage
from scripts.pipeline.orchestrator import Pipeline, ContextExtractor
from scripts.pipeline.context_registry import (
    get_registry, set_global_context, get_global_context, 
    update_global_context, copy_global_context, transfer_pipeline_context
)
from scripts.pipeline.exceptions import PipelineError


class ContextSetter(TransformationStage[Dict[str, Any], Dict[str, Any]]):
    """
    Transformation stage that sets values in the context.
    """
    
    def __init__(self, context_values: Dict[str, Any], name: str = "context_setter"):
        """
        Initialize the context setter.
        
        Args:
            context_values: Dictionary of values to set in the context
            name: Name of the stage
        """
        super().__init__(name)
        self.context_values = context_values
    
    async def transform(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Set values in the context.
        
        Args:
            data: Input data
            
        Returns:
            Input data unchanged
        """
        for key, value in self.context_values.items():
            self.set_context(key, value)
            logger.info(f"Set context key '{key}' to {value}")
        
        return data


class GlobalContextSetter(TransformationStage[Dict[str, Any], Dict[str, Any]]):
    """
    Transformation stage that sets values in the global context registry.
    """
    
    def __init__(self, namespace: str, context_values: Dict[str, Any], name: str = "global_context_setter"):
        """
        Initialize the global context setter.
        
        Args:
            namespace: Namespace for the context values
            context_values: Dictionary of values to set in the global context registry
            name: Name of the stage
        """
        super().__init__(name)
        self.namespace = namespace
        self.context_values = context_values
    
    async def transform(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Set values in the global context registry.
        
        Args:
            data: Input data
            
        Returns:
            Input data unchanged
        """
        for key, value in self.context_values.items():
            set_global_context(self.namespace, key, value)
            logger.info(f"Set global context key '{key}' in namespace '{self.namespace}' to {value}")
        
        return data


class ContextPrinter(TransformationStage[Dict[str, Any], Dict[str, Any]]):
    """
    Transformation stage that prints values from the context.
    """
    
    def __init__(self, keys: List[str], name: str = "context_printer"):
        """
        Initialize the context printer.
        
        Args:
            keys: List of keys to print from the context
            name: Name of the stage
        """
        super().__init__(name)
        self.keys = keys
    
    async def transform(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Print values from the context.
        
        Args:
            data: Input data
            
        Returns:
            Input data unchanged
        """
        for key in self.keys:
            value = self.get_context(key, "Not found")
            logger.info(f"Context key '{key}': {value}")
        
        return data


class GlobalContextPrinter(TransformationStage[Dict[str, Any], Dict[str, Any]]):
    """
    Transformation stage that prints values from the global context registry.
    """
    
    def __init__(self, namespace: str, keys: List[str], name: str = "global_context_printer"):
        """
        Initialize the global context printer.
        
        Args:
            namespace: Namespace for the context values
            keys: List of keys to print from the global context registry
            name: Name of the stage
        """
        super().__init__(name)
        self.namespace = namespace
        self.keys = keys
    
    async def transform(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Print values from the global context registry.
        
        Args:
            data: Input data
            
        Returns:
            Input data unchanged
        """
        for key in self.keys:
            value = get_global_context(self.namespace, key, "Not found")
            logger.info(f"Global context key '{key}' in namespace '{self.namespace}': {value}")
        
        return data


async def test_local_context():
    """
    Test local context sharing between stages in the same pipeline.
    """
    logger.info("=== Testing Local Context ===")
    
    # Create a pipeline
    pipeline = Pipeline("local_context_pipeline")
    
    # Add stages
    pipeline.add_stage(ContextSetter({"key1": "value1", "key2": 42}))
    pipeline.add_stage(ContextPrinter(["key1", "key2", "key3"]))
    
    # Run the pipeline
    try:
        await pipeline.run({})
        logger.info("Local context test passed")
    except PipelineError as e:
        logger.error(f"Local context test failed: {e}")


async def test_context_extractor():
    """
    Test the ContextExtractor class.
    """
    logger.info("\n=== Testing ContextExtractor ===")
    
    # Create a pipeline
    pipeline = Pipeline("context_extractor_pipeline")
    
    # Add stages
    pipeline.add_stage(ContextSetter({"key1": "value1", "key2": 42}))
    pipeline.add_stage(ContextExtractor("key1"))
    
    # Run the pipeline
    try:
        result = await pipeline.run({})
        logger.info(f"ContextExtractor result: {result}")
        logger.info("ContextExtractor test passed")
    except PipelineError as e:
        logger.error(f"ContextExtractor test failed: {e}")
    
    # Test with default value
    logger.info("\n=== Testing ContextExtractor with Default Value ===")
    
    # Create a pipeline
    pipeline = Pipeline("context_extractor_default_pipeline")
    
    # Add stages
    pipeline.add_stage(ContextSetter({"key1": "value1"}))
    pipeline.add_stage(ContextExtractor("key3", default="default_value"))
    
    # Run the pipeline
    try:
        result = await pipeline.run({})
        logger.info(f"ContextExtractor with default result: {result}")
        logger.info("ContextExtractor with default test passed")
    except PipelineError as e:
        logger.error(f"ContextExtractor with default test failed: {e}")
    
    # Test with raise_if_missing=False
    logger.info("\n=== Testing ContextExtractor with raise_if_missing=False ===")
    
    # Create a pipeline
    pipeline = Pipeline("context_extractor_no_raise_pipeline")
    
    # Add stages
    pipeline.add_stage(ContextSetter({"key1": "value1"}))
    pipeline.add_stage(ContextExtractor("key3", default="default_value", raise_if_missing=False))
    
    # Run the pipeline
    try:
        result = await pipeline.run({})
        logger.info(f"ContextExtractor with raise_if_missing=False result: {result}")
        logger.info("ContextExtractor with raise_if_missing=False test passed")
    except PipelineError as e:
        logger.error(f"ContextExtractor with raise_if_missing=False test failed: {e}")


async def test_global_context_registry():
    """
    Test the global context registry.
    """
    logger.info("\n=== Testing Global Context Registry ===")
    
    # Create pipelines
    pipeline1 = Pipeline("global_context_pipeline1")
    pipeline2 = Pipeline("global_context_pipeline2")
    
    # Add stages to pipeline1
    pipeline1.add_stage(GlobalContextSetter("namespace1", {"key1": "value1", "key2": 42}))
    
    # Add stages to pipeline2
    pipeline2.add_stage(GlobalContextPrinter("namespace1", ["key1", "key2", "key3"]))
    
    # Run the pipelines
    try:
        await pipeline1.run({})
        await pipeline2.run({})
        logger.info("Global context registry test passed")
    except PipelineError as e:
        logger.error(f"Global context registry test failed: {e}")


async def test_context_transfer():
    """
    Test transferring context between pipelines.
    """
    logger.info("\n=== Testing Context Transfer ===")
    
    # Create pipelines
    pipeline1 = Pipeline("transfer_pipeline1")
    pipeline2 = Pipeline("transfer_pipeline2")
    
    # Add stages to pipeline1
    pipeline1.add_stage(ContextSetter({"key1": "value1", "key2": 42, "key3": [1, 2, 3]}))
    
    # Add stages to pipeline2
    pipeline2.add_stage(ContextPrinter(["key1", "key2", "key3"]))
    
    # Run pipeline1
    try:
        await pipeline1.run({})
        
        # Transfer context from pipeline1 to pipeline2
        transfer_pipeline_context(pipeline1, pipeline2)
        
        # Run pipeline2
        await pipeline2.run({})
        
        logger.info("Context transfer test passed")
    except PipelineError as e:
        logger.error(f"Context transfer test failed: {e}")
    
    # Test transferring specific keys
    logger.info("\n=== Testing Context Transfer with Specific Keys ===")
    
    # Create pipelines
    pipeline1 = Pipeline("transfer_specific_pipeline1")
    pipeline2 = Pipeline("transfer_specific_pipeline2")
    
    # Add stages to pipeline1
    pipeline1.add_stage(ContextSetter({"key1": "value1", "key2": 42, "key3": [1, 2, 3]}))
    
    # Add stages to pipeline2
    pipeline2.add_stage(ContextPrinter(["key1", "key2", "key3"]))
    
    # Run pipeline1
    try:
        await pipeline1.run({})
        
        # Transfer specific keys from pipeline1 to pipeline2
        transfer_pipeline_context(pipeline1, pipeline2, keys=["key1", "key3"])
        
        # Run pipeline2
        await pipeline2.run({})
        
        logger.info("Context transfer with specific keys test passed")
    except PipelineError as e:
        logger.error(f"Context transfer with specific keys test failed: {e}")


async def test_context_extractor_with_global_registry():
    """
    Test the ContextExtractor class with the global context registry.
    """
    logger.info("\n=== Testing ContextExtractor with Global Registry ===")
    
    # Set a value in the global context registry
    set_global_context("extractor_test", "global_key", "global_value")
    
    # Create a pipeline
    pipeline = Pipeline("extractor_test")
    
    # Add a context extractor stage
    pipeline.add_stage(ContextExtractor("global_key"))
    
    # Run the pipeline
    try:
        result = await pipeline.run({})
        logger.info(f"ContextExtractor with global registry result: {result}")
        logger.info("ContextExtractor with global registry test passed")
    except PipelineError as e:
        logger.error(f"ContextExtractor with global registry test failed: {e}")


async def main():
    """
    Run all the tests.
    """
    await test_local_context()
    await test_context_extractor()
    await test_global_context_registry()
    await test_context_transfer()
    await test_context_extractor_with_global_registry()


if __name__ == "__main__":
    asyncio.run(main())
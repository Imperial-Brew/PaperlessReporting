"""
Testing framework for the pipeline framework.

This module provides utilities for testing pipeline configurations,
setting up test data, and verifying pipeline outputs.
"""

import asyncio
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Callable, TypeVar, Generic

from scripts.pipeline.base import PipelineStage
from scripts.pipeline.orchestrator import Pipeline
from scripts.pipeline.exceptions import PipelineError
from scripts.utils.logging_config import get_logger

# Get logger for this module
logger = get_logger(__name__)

# Type variable for pipeline input
T = TypeVar('T')
# Type variable for pipeline output
U = TypeVar('U')


class PipelineTester(Generic[T, U]):
    """
    Utility class for testing pipelines.
    
    This class provides methods for running pipelines with test data
    and verifying the outputs.
    """
    
    def __init__(self, pipeline: Pipeline):
        """
        Initialize the pipeline tester.
        
        Args:
            pipeline: Pipeline to test
        """
        self.pipeline = pipeline
        self.test_results = {}
        self.assertions = []
        self.assertion_results = []
    
    async def run_with_data(self, data: T) -> U:
        """
        Run the pipeline with the given test data.
        
        Args:
            data: Test data to process
            
        Returns:
            Pipeline output
            
        Raises:
            PipelineError: If an error occurs during pipeline execution
        """
        try:
            start_time = asyncio.get_event_loop().time()
            result = await self.pipeline.run(data)
            end_time = asyncio.get_event_loop().time()
            
            # Record test results
            self.test_results = {
                "pipeline_name": self.pipeline.name,
                "success": True,
                "duration": end_time - start_time,
                "metrics": self.pipeline.get_metrics(),
                "output": result
            }
            
            return result
        except PipelineError as e:
            # Record test failure
            self.test_results = {
                "pipeline_name": self.pipeline.name,
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "metrics": self.pipeline.get_metrics()
            }
            
            raise
    
    def assert_success(self) -> bool:
        """
        Assert that the pipeline executed successfully.
        
        Returns:
            True if the assertion passed, False otherwise
        """
        success = self.test_results.get("success", False)
        self.assertions.append(("success", success))
        self.assertion_results.append(success)
        return success
    
    def assert_failure(self) -> bool:
        """
        Assert that the pipeline failed with an error.
        
        Returns:
            True if the assertion passed, False otherwise
        """
        failure = not self.test_results.get("success", False)
        self.assertions.append(("failure", failure))
        self.assertion_results.append(failure)
        return failure
    
    def assert_error_type(self, error_type: str) -> bool:
        """
        Assert that the pipeline failed with a specific error type.
        
        Args:
            error_type: Expected error type name
            
        Returns:
            True if the assertion passed, False otherwise
        """
        actual_error_type = self.test_results.get("error_type", "")
        result = actual_error_type == error_type
        self.assertions.append((f"error_type={error_type}", result))
        self.assertion_results.append(result)
        return result
    
    def assert_metric(self, stage_name: str, metric_name: str, expected_value: Any) -> bool:
        """
        Assert that a specific metric has the expected value.
        
        Args:
            stage_name: Name of the stage
            metric_name: Name of the metric
            expected_value: Expected value of the metric
            
        Returns:
            True if the assertion passed, False otherwise
        """
        metrics = self.test_results.get("metrics", {})
        stage_metrics = metrics.get("stage_metrics", {}).get(stage_name, {}).get("metrics", {})
        actual_value = stage_metrics.get(metric_name)
        result = actual_value == expected_value
        self.assertions.append((f"{stage_name}.{metric_name}={expected_value}", result))
        self.assertion_results.append(result)
        return result
    
    def assert_output(self, condition: Callable[[U], bool]) -> bool:
        """
        Assert that the output meets a specific condition.
        
        Args:
            condition: Function that takes the output and returns a boolean
            
        Returns:
            True if the assertion passed, False otherwise
        """
        if not self.test_results.get("success", False):
            result = False
        else:
            output = self.test_results.get("output")
            result = condition(output)
        
        self.assertions.append(("output_condition", result))
        self.assertion_results.append(result)
        return result
    
    def assert_output_equals(self, expected_output: U) -> bool:
        """
        Assert that the output equals the expected output.
        
        Args:
            expected_output: Expected output
            
        Returns:
            True if the assertion passed, False otherwise
        """
        return self.assert_output(lambda output: output == expected_output)
    
    def assert_output_contains(self, key: Any) -> bool:
        """
        Assert that the output contains a specific key.
        
        Args:
            key: Key to check for
            
        Returns:
            True if the assertion passed, False otherwise
        """
        return self.assert_output(lambda output: key in output if hasattr(output, "__contains__") else False)
    
    def assert_output_has_length(self, length: int) -> bool:
        """
        Assert that the output has a specific length.
        
        Args:
            length: Expected length
            
        Returns:
            True if the assertion passed, False otherwise
        """
        return self.assert_output(lambda output: len(output) == length if hasattr(output, "__len__") else False)
    
    def assert_all(self) -> bool:
        """
        Assert that all assertions passed.
        
        Returns:
            True if all assertions passed, False otherwise
        """
        return all(self.assertion_results)
    
    def print_results(self) -> None:
        """
        Print the test results.
        """
        logger.info(f"Pipeline: {self.pipeline.name}")
        logger.info(f"Success: {self.test_results.get('success', False)}")
        
        if not self.test_results.get("success", False):
            logger.error(f"Error: {self.test_results.get('error', 'Unknown error')}")
            logger.error(f"Error type: {self.test_results.get('error_type', 'Unknown')}")
        
        logger.info(f"Duration: {self.test_results.get('duration', 0):.2f}s")
        
        # Print assertions
        logger.info("Assertions:")
        for assertion, result in self.assertions:
            status = "PASSED" if result else "FAILED"
            logger.info(f"  {assertion}: {status}")
        
        # Print overall result
        overall = "PASSED" if self.assert_all() else "FAILED"
        logger.info(f"Overall: {overall}")


class TestDataGenerator:
    """
    Utility class for generating test data for pipelines.
    """
    
    @staticmethod
    def create_sample_order() -> Dict[str, Any]:
        """
        Create a sample order for testing.
        
        Returns:
            Sample order data
        """
        return {
            "order_number": "O12345",
            "status": "in_production",
            "quote_number": "Q12345",
            "quote_revision_number": 1,
            "created": "2023-01-01T12:00:00Z",
            "deliver_by": "2023-01-15T12:00:00Z",
            "ships_on": "2023-01-10T12:00:00Z",
            "payment_terms": "Net 30",
            "purchase_order_number": "PO12345",
            "salesperson_email": "sales@example.com",
            "customer_name": "Example Company",
            "order_items": [
                {
                    "id": 1,
                    "quantity": 10,
                    "unit_price": 25.50,
                    "total_price": 255.00,
                    "description": "Sample Part",
                    "export_controlled": False,
                    "components": [
                        {
                            "is_root_component": True,
                            "part_number": "PART-001",
                            "part_uuid": "abc123",
                            "revision": "A",
                            "material": {
                                "name": "Aluminum 6061"
                            },
                            "process": {
                                "name": "CNC Machining"
                            }
                        }
                    ]
                },
                {
                    "id": 2,
                    "quantity": 5,
                    "unit_price": 15.75,
                    "total_price": 78.75,
                    "description": "Another Part",
                    "export_controlled": False,
                    "components": [
                        {
                            "is_root_component": True,
                            "part_number": "PART-002",
                            "part_uuid": "def456",
                            "revision": "B",
                            "material": {
                                "name": "Steel 1018"
                            },
                            "process": {
                                "name": "Laser Cutting"
                            }
                        }
                    ]
                }
            ]
        }
    
    @staticmethod
    def create_sample_quote() -> Dict[str, Any]:
        """
        Create a sample quote for testing.
        
        Returns:
            Sample quote data
        """
        return {
            "quote_number": "Q12345",
            "revision_number": 1,
            "status": "sent",
            "created": "2023-01-01T12:00:00Z",
            "due_date": "2023-01-15T12:00:00Z",
            "contact": {
                "first_name": "John",
                "last_name": "Doe",
                "email": "john.doe@example.com",
                "account": {
                    "name": "Example Company"
                }
            },
            "estimator": {
                "email": "estimator@example.com"
            },
            "salesperson": {
                "email": "sales@example.com"
            },
            "quote_items": [
                {
                    "id": 1,
                    "workflow_status": "pending",
                    "export_controlled": False,
                    "components": [
                        {
                            "is_root_component": True,
                            "part_number": "PART-001",
                            "revision": "A",
                            "description": "Sample Part",
                            "type": "machined",
                            "material": {
                                "name": "Aluminum 6061"
                            },
                            "process": {
                                "name": "CNC Machining"
                            },
                            "quantities": [
                                {
                                    "quantity": 10,
                                    "unit_price": 25.50,
                                    "total_price": 255.00,
                                    "total_price_with_required_add_ons": 275.00,
                                    "lead_time": "2 weeks"
                                }
                            ]
                        }
                    ]
                }
            ]
        }
    
    @staticmethod
    def create_invalid_order() -> Dict[str, Any]:
        """
        Create an invalid order for testing error handling.
        
        Returns:
            Invalid order data
        """
        return {
            "number": "O12345",  # Wrong field name
            # Missing required status field
            "created": "2023-01-01T12:00:00Z",
            "salesperson_email": "not-an-email"  # Invalid email format
        }
    
    @staticmethod
    def create_invalid_quote() -> Dict[str, Any]:
        """
        Create an invalid quote for testing error handling.
        
        Returns:
            Invalid quote data
        """
        return {
            "number": "Q12345",  # Wrong field name
            # Missing required fields
            "contact": {
                "first_name": "John"
                # Missing last_name and email
            }
        }
    
    @staticmethod
    def save_to_temp_file(data: Any, prefix: str = "test_", suffix: str = ".json") -> str:
        """
        Save data to a temporary file.
        
        Args:
            data: Data to save
            prefix: Prefix for the temporary file name
            suffix: Suffix for the temporary file name
            
        Returns:
            Path to the temporary file
        """
        with tempfile.NamedTemporaryFile(prefix=prefix, suffix=suffix, delete=False, mode="w") as f:
            json.dump(data, f, indent=2)
            return f.name
    
    @staticmethod
    def create_temp_output_path(prefix: str = "output_", suffix: str = ".csv") -> str:
        """
        Create a temporary output path.
        
        Args:
            prefix: Prefix for the temporary file name
            suffix: Suffix for the temporary file name
            
        Returns:
            Path to the temporary file
        """
        with tempfile.NamedTemporaryFile(prefix=prefix, suffix=suffix, delete=False) as f:
            return f.name


async def test_pipeline(pipeline: Pipeline, input_data: Any, 
                        assertions: Optional[List[Callable[[PipelineTester], bool]]] = None) -> PipelineTester:
    """
    Test a pipeline with the given input data and assertions.
    
    Args:
        pipeline: Pipeline to test
        input_data: Input data for the pipeline
        assertions: List of assertion functions to run
        
    Returns:
        PipelineTester instance with test results
    """
    tester = PipelineTester(pipeline)
    
    try:
        await tester.run_with_data(input_data)
    except PipelineError:
        # Error is expected in some tests
        pass
    
    # Run assertions
    if assertions:
        for assertion in assertions:
            assertion(tester)
    
    # Print results
    tester.print_results()
    
    return tester


async def test_order_pipeline(pipeline: Pipeline, 
                             assertions: Optional[List[Callable[[PipelineTester], bool]]] = None) -> PipelineTester:
    """
    Test an order pipeline with sample order data.
    
    Args:
        pipeline: Order pipeline to test
        assertions: List of assertion functions to run
        
    Returns:
        PipelineTester instance with test results
    """
    sample_order = TestDataGenerator.create_sample_order()
    return await test_pipeline(pipeline, sample_order, assertions)


async def test_quote_pipeline(pipeline: Pipeline,
                             assertions: Optional[List[Callable[[PipelineTester], bool]]] = None) -> PipelineTester:
    """
    Test a quote pipeline with sample quote data.
    
    Args:
        pipeline: Quote pipeline to test
        assertions: List of assertion functions to run
        
    Returns:
        PipelineTester instance with test results
    """
    sample_quote = TestDataGenerator.create_sample_quote()
    return await test_pipeline(pipeline, sample_quote, assertions)


async def test_error_handling(pipeline: Pipeline, invalid_data: Any,
                             assertions: Optional[List[Callable[[PipelineTester], bool]]] = None) -> PipelineTester:
    """
    Test error handling in a pipeline with invalid data.
    
    Args:
        pipeline: Pipeline to test
        invalid_data: Invalid input data
        assertions: List of assertion functions to run
        
    Returns:
        PipelineTester instance with test results
    """
    tester = PipelineTester(pipeline)
    
    try:
        await tester.run_with_data(invalid_data)
    except PipelineError:
        # Error is expected
        pass
    
    # Run assertions
    if assertions:
        for assertion in assertions:
            assertion(tester)
    
    # Print results
    tester.print_results()
    
    return tester
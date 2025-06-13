# Context Sharing in the Pipeline Framework

This document explains how to properly share context between pipelines and provides examples of how to use the `ContextExtractor` class and the global context registry.

## Overview

The pipeline framework provides several mechanisms for sharing data between stages and pipelines:

1. **Local Context**: Each pipeline stage has its own local context that can be used to store and retrieve data within that stage.
2. **Global Context Registry**: A global registry that can be used to share context between different pipeline instances and stages.
3. **Context Extractor**: A pipeline stage that extracts data from the context (either local or global) and passes it to the next stage.
4. **Utility Functions**: Utility functions for transferring context between pipelines.

## Local Context

Each pipeline stage has its own local context that can be accessed using the following methods:

```python
# Set a value in the local context
stage.set_context("key", value)

# Get a value from the local context
value = stage.get_context("key")

# Get a value with a default if the key doesn't exist
value = stage.get_context("key", default_value)

# Update the local context with values from another context
stage.update_context(other_context)

# Get the full local context
context = stage.get_full_context()
```

Local context is automatically passed from one stage to the next within the same pipeline. However, it is not automatically shared between different pipeline instances.

## Global Context Registry

The global context registry provides a way to share context between different pipeline instances and stages. It is implemented as a singleton, so there is only one instance of the registry in the application.

```python
from scripts.pipeline.context_registry import (
    get_registry, set_global_context, get_global_context, 
    update_global_context, copy_global_context
)

# Set a value in the global context registry
set_global_context("namespace", "key", value)

# Get a value from the global context registry
value = get_global_context("namespace", "key")

# Get a value with a default if the key doesn't exist
value = get_global_context("namespace", "key", default_value)

# Update the global context registry with values from another context
update_global_context("namespace", other_context)

# Copy context values from one namespace to another
copy_global_context("source_namespace", "target_namespace")

# Copy only specific keys
copy_global_context("source_namespace", "target_namespace", keys=["key1", "key2"])
```

The global context registry uses namespaces to organize context values. A common practice is to use the pipeline name as the namespace.

## Context Extractor

The `ContextExtractor` class is a pipeline stage that extracts data from the context (either local or global) and passes it to the next stage. It is useful for extracting data that was stored in the context by previous stages, allowing pipelines to share data.

```python
from scripts.pipeline.orchestrator import Pipeline, ContextExtractor

# Create a pipeline
pipeline = Pipeline("my_pipeline")

# Add a context extractor stage
pipeline.add_stage(ContextExtractor("key"))

# Add a context extractor stage with a default value
pipeline.add_stage(ContextExtractor("key", default=default_value))

# Add a context extractor stage that doesn't raise an error if the key doesn't exist
pipeline.add_stage(ContextExtractor("key", default=default_value, raise_if_missing=False))
```

The `ContextExtractor` class first tries to get the value from the local context. If the key doesn't exist in the local context, it tries to get the value from the global context registry using the pipeline name as the namespace. If the key doesn't exist in either the local context or the global context registry, it returns the default value or raises a `KeyError` if `raise_if_missing` is `True`.

## Utility Functions

The pipeline framework provides utility functions for transferring context between pipelines.

```python
from scripts.pipeline.context_registry import transfer_pipeline_context

# Transfer context from one pipeline to another
transfer_pipeline_context(source_pipeline, target_pipeline)

# Transfer only specific keys
transfer_pipeline_context(source_pipeline, target_pipeline, keys=["key1", "key2"])
```

## Examples

### Example 1: Sharing Context Between Stages in the Same Pipeline

```python
from scripts.pipeline.orchestrator import Pipeline
from scripts.pipeline.base import TransformationStage

# Create a custom stage that sets a value in the context
class ContextSetter(TransformationStage):
    async def transform(self, data):
        # Set a value in the context
        self.set_context("my_key", "my_value")
        return data

# Create a custom stage that uses the value from the context
class ContextUser(TransformationStage):
    async def transform(self, data):
        # Get the value from the context
        value = self.get_context("my_key")
        print(f"Value from context: {value}")
        return data

# Create a pipeline
pipeline = Pipeline("my_pipeline")
pipeline.add_stage(ContextSetter("context_setter"))
pipeline.add_stage(ContextUser("context_user"))

# Run the pipeline
await pipeline.run(data)
```

### Example 2: Extracting Data from Context

```python
from scripts.pipeline.orchestrator import Pipeline, ContextExtractor
from scripts.pipeline.base import TransformationStage

# Create a custom stage that sets a value in the context
class ContextSetter(TransformationStage):
    async def transform(self, data):
        # Set a value in the context
        self.set_context("order_items", [{"id": 1}, {"id": 2}])
        return data

# Create a pipeline
pipeline = Pipeline("my_pipeline")
pipeline.add_stage(ContextSetter("context_setter"))
pipeline.add_stage(ContextExtractor("order_items"))

# The output of the pipeline will be the order items
order_items = await pipeline.run(data)
```

### Example 3: Sharing Context Between Different Pipelines

```python
from scripts.pipeline.orchestrator import Pipeline
from scripts.pipeline.base import TransformationStage
from scripts.pipeline.context_registry import transfer_pipeline_context

# Create a custom stage that sets a value in the context
class ContextSetter(TransformationStage):
    async def transform(self, data):
        # Set a value in the context
        self.set_context("order_items", [{"id": 1}, {"id": 2}])
        return data

# Create the first pipeline
pipeline1 = Pipeline("pipeline1")
pipeline1.add_stage(ContextSetter("context_setter"))

# Run the first pipeline
await pipeline1.run(data1)

# Create the second pipeline
pipeline2 = Pipeline("pipeline2")
pipeline2.add_stage(ContextExtractor("order_items"))

# Transfer context from the first pipeline to the second pipeline
transfer_pipeline_context(pipeline1, pipeline2)

# Run the second pipeline
order_items = await pipeline2.run(data2)
```

### Example 4: Using the Global Context Registry

```python
from scripts.pipeline.orchestrator import Pipeline
from scripts.pipeline.base import TransformationStage
from scripts.pipeline.context_registry import set_global_context, get_global_context

# Create a custom stage that sets a value in the global context registry
class GlobalContextSetter(TransformationStage):
    async def transform(self, data):
        # Set a value in the global context registry
        set_global_context("my_namespace", "my_key", "my_value")
        return data

# Create a custom stage that uses the value from the global context registry
class GlobalContextUser(TransformationStage):
    async def transform(self, data):
        # Get the value from the global context registry
        value = get_global_context("my_namespace", "my_key")
        print(f"Value from global context: {value}")
        return data

# Create the first pipeline
pipeline1 = Pipeline("pipeline1")
pipeline1.add_stage(GlobalContextSetter("global_context_setter"))

# Create the second pipeline
pipeline2 = Pipeline("pipeline2")
pipeline2.add_stage(GlobalContextUser("global_context_user"))

# Run the pipelines
await pipeline1.run(data1)
await pipeline2.run(data2)
```

### Example 5: Using ContextExtractor with Default Values

```python
from scripts.pipeline.orchestrator import Pipeline, ContextExtractor

# Create a pipeline
pipeline = Pipeline("my_pipeline")

# Add a context extractor stage with a default value
pipeline.add_stage(ContextExtractor("key_that_might_not_exist", default=[]))

# The output of the pipeline will be the value from the context or an empty list if the key doesn't exist
result = await pipeline.run(data)
```

## Best Practices

1. **Use Descriptive Keys**: Use descriptive keys for context values to make it clear what the value represents.
2. **Document Context Usage**: Document which context keys are used by each stage and pipeline.
3. **Provide Default Values**: When extracting values from the context, provide default values to handle cases where the key doesn't exist.
4. **Use Namespaces in the Global Registry**: When using the global context registry, use namespaces to organize context values and avoid key collisions.
5. **Clean Up Global Context**: When a pipeline is done, consider cleaning up its namespace in the global context registry to avoid memory leaks.
"""
Global context registry for the pipeline framework.

This module provides a global registry for sharing context between
different pipeline instances and stages.
"""

from typing import Any, Dict, Optional
import threading

class ContextRegistry:
    """
    Global registry for sharing context between pipelines.
    
    This class provides a singleton instance that can be used to
    store and retrieve context values across different pipeline
    instances and stages.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """
        Create a new ContextRegistry instance or return the existing one.
        
        Returns:
            ContextRegistry: The singleton instance
        """
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ContextRegistry, cls).__new__(cls)
                cls._instance._contexts = {}
            return cls._instance
    
    def __init__(self):
        """
        Initialize the context registry.
        
        Note that this is only called once when the singleton is first created.
        """
        # _contexts is initialized in __new__
        pass
    
    def set_context(self, namespace: str, key: str, value: Any) -> None:
        """
        Set a value in the context registry.
        
        Args:
            namespace: Namespace for the context (e.g., pipeline name)
            key: Context key
            value: Context value
        """
        if namespace not in self._contexts:
            self._contexts[namespace] = {}
        self._contexts[namespace][key] = value
    
    def get_context(self, namespace: str, key: str, default: Any = None) -> Any:
        """
        Get a value from the context registry.
        
        Args:
            namespace: Namespace for the context (e.g., pipeline name)
            key: Context key
            default: Default value if key doesn't exist
            
        Returns:
            Context value or default
        """
        if namespace not in self._contexts:
            return default
        return self._contexts[namespace].get(key, default)
    
    def update_context(self, namespace: str, context: Dict[str, Any]) -> None:
        """
        Update the context registry with values from another context.
        
        Args:
            namespace: Namespace for the context (e.g., pipeline name)
            context: Context dictionary to update from
        """
        if namespace not in self._contexts:
            self._contexts[namespace] = {}
        self._contexts[namespace].update(context)
    
    def get_namespace_context(self, namespace: str) -> Dict[str, Any]:
        """
        Get the full context dictionary for a namespace.
        
        Args:
            namespace: Namespace for the context (e.g., pipeline name)
            
        Returns:
            Context dictionary for the namespace
        """
        if namespace not in self._contexts:
            return {}
        return self._contexts[namespace].copy()
    
    def copy_context(self, source_namespace: str, target_namespace: str, keys: Optional[list] = None) -> None:
        """
        Copy context values from one namespace to another.
        
        Args:
            source_namespace: Source namespace
            target_namespace: Target namespace
            keys: Optional list of keys to copy (if None, copy all)
        """
        if source_namespace not in self._contexts:
            return
        
        if target_namespace not in self._contexts:
            self._contexts[target_namespace] = {}
        
        source_context = self._contexts[source_namespace]
        
        if keys is None:
            # Copy all keys
            self._contexts[target_namespace].update(source_context)
        else:
            # Copy only specified keys
            for key in keys:
                if key in source_context:
                    self._contexts[target_namespace][key] = source_context[key]
    
    def clear_namespace(self, namespace: str) -> None:
        """
        Clear all context values for a namespace.
        
        Args:
            namespace: Namespace to clear
        """
        if namespace in self._contexts:
            del self._contexts[namespace]
    
    def clear_all(self) -> None:
        """
        Clear all context values in the registry.
        """
        self._contexts.clear()


# Convenience functions for accessing the registry

def get_registry() -> ContextRegistry:
    """
    Get the global context registry instance.
    
    Returns:
        ContextRegistry: The singleton instance
    """
    return ContextRegistry()

def set_global_context(namespace: str, key: str, value: Any) -> None:
    """
    Set a value in the global context registry.
    
    Args:
        namespace: Namespace for the context (e.g., pipeline name)
        key: Context key
        value: Context value
    """
    registry = get_registry()
    registry.set_context(namespace, key, value)

def get_global_context(namespace: str, key: str, default: Any = None) -> Any:
    """
    Get a value from the global context registry.
    
    Args:
        namespace: Namespace for the context (e.g., pipeline name)
        key: Context key
        default: Default value if key doesn't exist
        
    Returns:
        Context value or default
    """
    registry = get_registry()
    return registry.get_context(namespace, key, default)

def update_global_context(namespace: str, context: Dict[str, Any]) -> None:
    """
    Update the global context registry with values from another context.
    
    Args:
        namespace: Namespace for the context (e.g., pipeline name)
        context: Context dictionary to update from
    """
    registry = get_registry()
    registry.update_context(namespace, context)

def copy_global_context(source_namespace: str, target_namespace: str, keys: Optional[list] = None) -> None:
    """
    Copy context values from one namespace to another in the global registry.
    
    Args:
        source_namespace: Source namespace
        target_namespace: Target namespace
        keys: Optional list of keys to copy (if None, copy all)
    """
    registry = get_registry()
    registry.copy_context(source_namespace, target_namespace, keys)

def transfer_pipeline_context(source_pipeline: 'Pipeline', target_pipeline: 'Pipeline', keys: Optional[list] = None) -> None:
    """
    Transfer context from one pipeline to another.
    
    This function copies context values from the stages of the source pipeline
    to the stages of the target pipeline.
    
    Args:
        source_pipeline: Source pipeline
        target_pipeline: Target pipeline
        keys: Optional list of keys to transfer (if None, transfer all)
    """
    # Get context from all stages in the source pipeline
    source_context = {}
    for stage in source_pipeline.stages:
        source_context.update(stage.get_full_context())
    
    # Filter keys if specified
    if keys is not None:
        source_context = {k: v for k, v in source_context.items() if k in keys}
    
    # Update context for all stages in the target pipeline
    for stage in target_pipeline.stages:
        stage.update_context(source_context)
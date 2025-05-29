"""
Asynchronous token bucket for rate limiting.

This module provides an AsyncTokenBucket class that wraps the TokenBucket class
for use in asynchronous contexts.
"""

import asyncio
from .token_bucket import TokenBucket


class AsyncTokenBucket:
    """
    Asynchronous token bucket for rate limiting.

    This class wraps the TokenBucket class to provide an asynchronous interface
    for rate limiting in async code. It can be used as an async context manager.
    """

    def __init__(self, rate, capacity):
        """
        Initialize the async token bucket.

        Args:
            rate: Rate at which tokens are added to the bucket (tokens per second)
            capacity: Maximum number of tokens the bucket can hold
        """
        self.bucket = TokenBucket(rate, capacity)

    async def __aenter__(self):
        """
        Enter the async context manager.

        Waits until a token is available before proceeding.
        """
        while not self.bucket.consume():
            await asyncio.sleep(0.01)  # Small sleep to avoid busy waiting
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Exit the async context manager.
        """
        pass  # Nothing to clean up
import asyncio
import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class AsyncTokenBucket:
    def __init__(self, rate: float, capacity: int):
        """
        An async implementation of the token bucket algorithm for rate limiting.
        
        Args:
            rate: Tokens per second to add to the bucket
            capacity: Maximum number of tokens the bucket can hold
        """
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_update = time.monotonic()
        self._lock = asyncio.Lock()
        
    async def acquire(self, tokens: int = 1, timeout: Optional[float] = None) -> bool:
        """
        Acquire tokens from the bucket.
        
        Args:
            tokens: Number of tokens to acquire
            timeout: Maximum time to wait for tokens (None for no timeout)
            
        Returns:
            bool: True if tokens were acquired, False if timeout occurred
        """
        start_time = time.monotonic()
        
        while True:
            async with self._lock:
                now = time.monotonic()
                # Add new tokens based on time elapsed
                elapsed = now - self.last_update
                self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
                self.last_update = now
                
                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return True
                
                if timeout is not None:
                    if time.monotonic() - start_time > timeout:
                        logger.warning(f"Timeout waiting for {tokens} tokens")
                        return False
            
            # Wait a bit before trying again
            await asyncio.sleep(0.1)
    
    async def __aenter__(self):
        """Support for async context manager."""
        await self.acquire()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Support for async context manager."""
        pass 
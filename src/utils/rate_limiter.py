"""
Rate limiting utilities
"""

import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class RateLimiter:
    """Simple rate limiter"""
    
    def __init__(self, max_requests: int, time_window: float):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []
        self._lock = asyncio.Lock()
    
    async def acquire(self):
        """Wait if necessary to not exceed the limit"""
        async with self._lock:
            now = asyncio.get_event_loop().time()
            
            # Remove old requests
            self.requests = [req_time for req_time in self.requests 
                           if now - req_time < self.time_window]
            
            # If limit reached, wait
            if len(self.requests) >= self.max_requests:
                sleep_time = self.time_window - (now - self.requests[0])
                if sleep_time > 0:
                    logger.info(f"Rate limit reached, sleeping for {sleep_time:.2f}s")
                    await asyncio.sleep(sleep_time)
                    # Update list after waiting
                    now = asyncio.get_event_loop().time()
                    self.requests = [req_time for req_time in self.requests 
                                   if now - req_time < self.time_window]
            
            # Add current request
            self.requests.append(now)
    
    def reset(self):
        """Reset the rate limiter"""
        self.requests.clear()
    
    def get_remaining_requests(self) -> int:
        """Get number of remaining requests in current window"""
        now = asyncio.get_event_loop().time()
        self.requests = [req_time for req_time in self.requests 
                        if now - req_time < self.time_window]
        return max(0, self.max_requests - len(self.requests))

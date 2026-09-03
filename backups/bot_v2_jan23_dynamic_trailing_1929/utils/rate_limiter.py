"""
Rate Limiter - Token bucket rate limiting for API calls
"""
import time
import threading
from typing import Optional
import logging


class RateLimiter:
    """
    Token bucket rate limiter for API calls.
    
    Allows burst up to max_tokens, then limits to tokens_per_second.
    Thread-safe for use across multiple modules.
    """
    
    def __init__(
        self,
        tokens_per_second: float = 2.0,
        max_tokens: int = 10,
        name: str = "default",
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize rate limiter.
        
        Args:
            tokens_per_second: Token refill rate
            max_tokens: Maximum burst capacity
            name: Limiter name for logging
            logger: Optional logger
        """
        self.tokens_per_second = tokens_per_second
        self.max_tokens = max_tokens
        self.name = name
        self.logger = logger or logging.getLogger(__name__)
        
        self._tokens = float(max_tokens)
        self._last_update = time.time()
        self._lock = threading.Lock()
        self._total_waits = 0
        self._total_wait_time = 0.0
    
    def _refill_tokens(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self._last_update
        self._tokens = min(
            self.max_tokens,
            self._tokens + elapsed * self.tokens_per_second
        )
        self._last_update = now
    
    def acquire(self, tokens: int = 1, timeout: Optional[float] = None) -> bool:
        """
        Acquire tokens, waiting if necessary.
        
        Args:
            tokens: Number of tokens to acquire
            timeout: Max wait time (None = wait forever)
            
        Returns:
            True if tokens acquired, False if timed out
        """
        start_time = time.time()
        
        with self._lock:
            while True:
                self._refill_tokens()
                
                if self._tokens >= tokens:
                    self._tokens -= tokens
                    return True
                
                # Calculate wait time for tokens to be available
                tokens_needed = tokens - self._tokens
                wait_time = tokens_needed / self.tokens_per_second
                
                # Check timeout
                if timeout is not None:
                    elapsed = time.time() - start_time
                    if elapsed + wait_time > timeout:
                        self.logger.debug(f"[{self.name}] Rate limit timeout")
                        return False
                
                # Wait and track stats
                self._total_waits += 1
                self._total_wait_time += wait_time
                
                if wait_time > 0.1:  # Only log significant waits
                    self.logger.debug(f"[{self.name}] Rate limiting: waiting {wait_time:.2f}s")
                
                # Release lock during wait
                self._lock.release()
                try:
                    time.sleep(wait_time)
                finally:
                    self._lock.acquire()
    
    def get_stats(self) -> dict:
        """Get rate limiter statistics."""
        return {
            "name": self.name,
            "total_waits": self._total_waits,
            "total_wait_time": round(self._total_wait_time, 2),
            "current_tokens": round(self._tokens, 2),
            "max_tokens": self.max_tokens,
            "tokens_per_second": self.tokens_per_second
        }
    
    def reset(self) -> None:
        """Reset limiter to full capacity."""
        with self._lock:
            self._tokens = float(self.max_tokens)
            self._last_update = time.time()


# Pre-configured rate limiters for common APIs
_rate_limiters = {}
_limiter_lock = threading.Lock()


def get_rate_limiter(
    name: str,
    tokens_per_second: float = 2.0,
    max_tokens: int = 10
) -> RateLimiter:
    """
    Get or create a named rate limiter.
    
    Args:
        name: Limiter name (e.g., 'yfinance', 'alpaca')
        tokens_per_second: Token refill rate
        max_tokens: Maximum burst capacity
        
    Returns:
        RateLimiter instance
    """
    with _limiter_lock:
        if name not in _rate_limiters:
            _rate_limiters[name] = RateLimiter(
                tokens_per_second=tokens_per_second,
                max_tokens=max_tokens,
                name=name
            )
        return _rate_limiters[name]


# Pre-configured limiter for yfinance (2 requests/sec, burst of 10)
def get_yfinance_limiter() -> RateLimiter:
    """Get rate limiter configured for yfinance API."""
    return get_rate_limiter('yfinance', tokens_per_second=2.0, max_tokens=10)


# Pre-configured limiter for Alpaca (3 requests/sec, burst of 20)
def get_alpaca_limiter() -> RateLimiter:
    """Get rate limiter configured for Alpaca API."""
    return get_rate_limiter('alpaca', tokens_per_second=3.0, max_tokens=20)

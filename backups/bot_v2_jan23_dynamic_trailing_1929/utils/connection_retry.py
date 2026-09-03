#!/usr/bin/env python3
"""
Connection Retry Utility
Provides retry logic with exponential backoff for API calls
"""
import time
import logging
from typing import Callable, Any, Optional
from functools import wraps

logger = logging.getLogger('bot_v2.connection_retry')


class ConnectionRetryHandler:
    """Handles retry logic for network connections with exponential backoff"""
    
    def __init__(
        self, 
        max_retries: int = 3,
        base_delay: float = 2.0,
        max_delay: float = 30.0,
        backoff_factor: float = 2.0
    ):
        """
        Initialize retry handler
        
        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Initial delay between retries (seconds)
            max_delay: Maximum delay between retries (seconds)
            backoff_factor: Multiplier for exponential backoff
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
    
    def retry_with_backoff(
        self, 
        func: Callable,
        *args,
        **kwargs
    ) -> Optional[Any]:
        """
        Execute function with exponential backoff retry
        
        Args:
            func: Function to execute
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function
            
        Returns:
            Function result or None if all retries failed
        """
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                # Attempt the function call
                result = func(*args, **kwargs)
                
                # If we had previous failures, log recovery
                if attempt > 0:
                    logger.info(f"✅ Connection recovered after {attempt} retries")
                
                return result
                
            except Exception as e:
                last_exception = e
                error_msg = str(e)
                
                # Check if it's a connection-related error
                is_connection_error = any([
                    'connection' in error_msg.lower(),
                    'timeout' in error_msg.lower(),
                    'name resolution' in error_msg.lower(),
                    'network' in error_msg.lower(),
                    'errno' in error_msg.lower(),
                    'max retries exceeded' in error_msg.lower()
                ])
                
                if not is_connection_error:
                    # Not a connection error, don't retry
                    logger.debug(f"Non-connection error, not retrying: {error_msg}")
                    raise
                
                if attempt < self.max_retries:
                    # Calculate delay with exponential backoff
                    delay = min(
                        self.base_delay * (self.backoff_factor ** attempt),
                        self.max_delay
                    )
                    
                    logger.warning(
                        f"⚠️ Connection failed (attempt {attempt + 1}/{self.max_retries + 1}): "
                        f"{error_msg}"
                    )
                    logger.info(f"🔄 Retrying in {delay:.1f} seconds...")
                    
                    time.sleep(delay)
                else:
                    # All retries exhausted
                    logger.error(
                        f"❌ Connection failed after {self.max_retries + 1} attempts: "
                        f"{error_msg}"
                    )
        
        # If we get here, all retries failed
        return None


def with_retry(max_retries: int = 3, base_delay: float = 2.0):
    """
    Decorator to add retry logic to any function
    
    Usage:
        @with_retry(max_retries=3, base_delay=2.0)
        def fetch_data():
            ...
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay between retries (seconds)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            handler = ConnectionRetryHandler(
                max_retries=max_retries,
                base_delay=base_delay
            )
            return handler.retry_with_backoff(func, *args, **kwargs)
        return wrapper
    return decorator


def test_retry_handler():
    """Test the retry handler"""
    print("🧪 Testing Connection Retry Handler")
    print("=" * 50)
    
    # Simulate a function that fails twice then succeeds
    call_count = 0
    
    @with_retry(max_retries=3, base_delay=1.0)
    def flaky_function():
        nonlocal call_count
        call_count += 1
        print(f"Attempt {call_count}")
        
        if call_count < 3:
            raise ConnectionError("Simulated connection failure")
        
        return "Success!"
    
    # Test retry logic
    result = flaky_function()
    print(f"Result: {result}")
    print(f"Total attempts: {call_count}")
    
    # Test non-connection error (should not retry)
    @with_retry(max_retries=3, base_delay=1.0)
    def bad_function():
        raise ValueError("Not a connection error")
    
    try:
        bad_function()
    except ValueError as e:
        print(f"✅ Correctly did not retry non-connection error: {e}")


if __name__ == "__main__":
    test_retry_handler()

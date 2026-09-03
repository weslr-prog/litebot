#!/usr/bin/env python3
"""
Live Integration Tests - Validates bot components work with real APIs
Run periodically (e.g., daily at 9:00 AM ET) to catch integration issues before market open.
"""

import os
import sys
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('integration_tests')


class IntegrationTestResult:
    """Result of a single integration test"""
    def __init__(self, name: str, passed: bool, message: str, duration_ms: float):
        self.name = name
        self.passed = passed
        self.message = message
        self.duration_ms = duration_ms


def run_test(test_func) -> IntegrationTestResult:
    """Run a test function and capture result"""
    import time
    start = time.time()
    try:
        passed, message = test_func()
        duration_ms = (time.time() - start) * 1000
        return IntegrationTestResult(test_func.__name__, passed, message, duration_ms)
    except Exception as e:
        duration_ms = (time.time() - start) * 1000
        return IntegrationTestResult(test_func.__name__, False, f"Exception: {str(e)}", duration_ms)


# ============================================================================
# DATA SOURCE TESTS
# ============================================================================

def test_yfinance_historical() -> Tuple[bool, str]:
    """Test yfinance historical data fetch"""
    from bot_v2.data.data_loader import DataLoader
    
    loader = DataLoader(enable_multi_source_validation=False)
    data = loader.get_historical_data('SPY', days=5)
    
    if data is None or data.empty:
        return False, "No data returned for SPY"
    
    if len(data) < 3:
        return False, f"Insufficient data: {len(data)} rows"
    
    required_cols = ['date', 'open', 'high', 'low', 'close', 'volume']
    missing = [c for c in required_cols if c not in data.columns]
    if missing:
        return False, f"Missing columns: {missing}"
    
    return True, f"OK - {len(data)} rows, latest: {data['date'].max()}"


def test_yfinance_current_price() -> Tuple[bool, str]:
    """Test yfinance current price fetch"""
    from bot_v2.data.data_loader import DataLoader
    
    loader = DataLoader(enable_multi_source_validation=False)
    price = loader.get_current_price('AAPL')
    
    if price is None:
        return False, "No price returned for AAPL"
    
    if not isinstance(price, (int, float)):
        return False, f"Invalid price type: {type(price)}"
    
    if price <= 0 or price > 10000:
        return False, f"Suspicious price: ${price}"
    
    return True, f"OK - AAPL: ${price:.2f}"


def test_alpaca_connection() -> Tuple[bool, str]:
    """Test Alpaca API connection"""
    api_key = os.getenv("APCA_API_KEY_ID")
    secret_key = os.getenv("APCA_API_SECRET_KEY")
    
    if not api_key or not secret_key:
        return True, "SKIP - Alpaca credentials not configured (test in live env)"
    
    try:
        from alpaca.trading.client import TradingClient
        
        # Check if paper trading
        is_paper = 'paper' in os.getenv("APCA_API_BASE_URL", "").lower()
        
        client = TradingClient(api_key, secret_key, paper=is_paper)
        account = client.get_account()
        
        if account.status != 'ACTIVE':
            return False, f"Account not active: {account.status}"
        
        return True, f"OK - Balance: ${float(account.equity):,.2f}, Paper: {is_paper}"
        
    except Exception as e:
        return False, f"Connection failed: {str(e)}"


def test_alpaca_positions() -> Tuple[bool, str]:
    """Test Alpaca position fetch"""
    api_key = os.getenv("APCA_API_KEY_ID")
    secret_key = os.getenv("APCA_API_SECRET_KEY")
    
    if not api_key or not secret_key:
        return True, "SKIP - Alpaca credentials not configured (test in live env)"
    
    try:
        from alpaca.trading.client import TradingClient
        
        is_paper = 'paper' in os.getenv("APCA_API_BASE_URL", "").lower()
        client = TradingClient(api_key, secret_key, paper=is_paper)
        
        positions = client.get_all_positions()
        
        return True, f"OK - {len(positions)} positions"
        
    except Exception as e:
        return False, f"Failed: {str(e)}"


# ============================================================================
# UTILITY TESTS
# ============================================================================

def test_market_calendar() -> Tuple[bool, str]:
    """Test market calendar holiday detection"""
    from bot_v2.utils.datetime_utils import is_market_holiday, get_next_trading_day, is_trading_day
    import datetime as dt
    
    # Test known holiday
    christmas = dt.date(2025, 12, 25)
    if not is_market_holiday(christmas):
        return False, "Christmas 2025 not detected as holiday"
    
    # Test weekend
    saturday = dt.date(2025, 1, 4)
    if is_trading_day(saturday):
        return False, "Saturday incorrectly marked as trading day"
    
    # Test next trading day after holiday
    next_day = get_next_trading_day(dt.date(2025, 12, 24))  # Christmas Eve
    if next_day != dt.date(2025, 12, 26):
        return False, f"Wrong next trading day after Christmas Eve: {next_day}"
    
    return True, "OK - Holiday detection working"


def test_rate_limiter() -> Tuple[bool, str]:
    """Test rate limiter functionality"""
    from bot_v2.utils.rate_limiter import RateLimiter
    import time
    
    limiter = RateLimiter(tokens_per_second=10.0, max_tokens=5, name="test")
    
    # Should get 5 tokens immediately (burst)
    start = time.time()
    for _ in range(5):
        limiter.acquire()
    burst_time = time.time() - start
    
    if burst_time > 0.1:
        return False, f"Burst took too long: {burst_time:.3f}s"
    
    # Next token should require waiting
    start = time.time()
    limiter.acquire()
    wait_time = time.time() - start
    
    if wait_time < 0.05:  # Should wait ~0.1s
        return False, f"No rate limiting: wait was {wait_time:.3f}s"
    
    return True, f"OK - Burst: {burst_time*1000:.1f}ms, Wait: {wait_time*1000:.1f}ms"


def test_error_tracker() -> Tuple[bool, str]:
    """Test error tracker"""
    from bot_v2.utils.error_tracker import ErrorTracker, ErrorSeverity
    
    tracker = ErrorTracker()
    
    # Track some errors
    try:
        raise ValueError("Test error 1")
    except Exception as e:
        tracker.track_error("test", "func1", e, symbol="AAPL", severity=ErrorSeverity.LOW)
    
    try:
        raise RuntimeError("Test error 2")
    except Exception as e:
        tracker.track_error("test", "func2", e, symbol="AAPL", severity=ErrorSeverity.MEDIUM)
    
    if len(tracker.errors) != 2:
        return False, f"Wrong error count: {len(tracker.errors)}"
    
    if tracker.symbol_failures["AAPL"] != 2:
        return False, f"Wrong symbol failure count: {tracker.symbol_failures['AAPL']}"
    
    summary = tracker.get_session_summary()
    if summary["total_errors"] != 2:
        return False, f"Summary wrong: {summary}"
    
    return True, "OK - Error tracking working"


# ============================================================================
# BOT MODULE TESTS
# ============================================================================

def test_position_tracker_imports() -> Tuple[bool, str]:
    """Test position tracker module loads"""
    try:
        from bot_v2.execution.position_tracker import AIPositionTracker
        return True, "OK - Module loads"
    except Exception as e:
        return False, f"Import failed: {str(e)}"


def test_signal_generator_imports() -> Tuple[bool, str]:
    """Test signal generator module loads"""
    try:
        from bot_v2.signal_generation.signal_generator import AISignalGenerator
        return True, "OK - Module loads"
    except Exception as e:
        return False, f"Import failed: {str(e)}"


def test_trading_engine_imports() -> Tuple[bool, str]:
    """Test trading engine module loads"""
    try:
        from bot_v2.core.trading_engine import ProductionTradingEngine
        return True, "OK - Module loads"
    except Exception as e:
        return False, f"Import failed: {str(e)}"


def test_fallback_universe() -> Tuple[bool, str]:
    """Test fallback universe has sufficient stocks"""
    from bot_v2.data.fallback_universe import get_fallback_universe, DIVERSIFIED_MID_CAP
    
    full_universe = get_fallback_universe(diversified=False)
    diversified = get_fallback_universe(diversified=True)
    
    if len(full_universe) < 30:
        return False, f"Full universe too small: {len(full_universe)} stocks"
    
    if len(diversified) < 15:
        return False, f"Diversified universe too small: {len(diversified)} stocks"
    
    return True, f"OK - Full: {len(full_universe)}, Diversified: {len(diversified)}"


# ============================================================================
# RUN ALL TESTS
# ============================================================================

def run_all_tests() -> Dict[str, List[IntegrationTestResult]]:
    """Run all integration tests"""
    
    test_suites = {
        "Data Sources": [
            test_yfinance_historical,
            test_yfinance_current_price,
            test_alpaca_connection,
            test_alpaca_positions,
        ],
        "Utilities": [
            test_market_calendar,
            test_rate_limiter,
            test_error_tracker,
        ],
        "Bot Modules": [
            test_position_tracker_imports,
            test_signal_generator_imports,
            test_trading_engine_imports,
            test_fallback_universe,
        ]
    }
    
    results = {}
    
    for suite_name, tests in test_suites.items():
        logger.info(f"\n{'='*60}")
        logger.info(f"Running: {suite_name}")
        logger.info('='*60)
        
        suite_results = []
        for test in tests:
            result = run_test(test)
            suite_results.append(result)
            
            status = "✅ PASS" if result.passed else "❌ FAIL"
            logger.info(f"{status} | {result.name}: {result.message} ({result.duration_ms:.0f}ms)")
        
        results[suite_name] = suite_results
    
    return results


def print_summary(results: Dict[str, List[IntegrationTestResult]]) -> bool:
    """Print test summary and return overall pass/fail"""
    logger.info("\n" + "="*60)
    logger.info("INTEGRATION TEST SUMMARY")
    logger.info("="*60)
    
    total_passed = 0
    total_failed = 0
    
    for suite_name, suite_results in results.items():
        passed = sum(1 for r in suite_results if r.passed)
        failed = sum(1 for r in suite_results if not r.passed)
        total_passed += passed
        total_failed += failed
        
        status = "✅" if failed == 0 else "❌"
        logger.info(f"{status} {suite_name}: {passed}/{len(suite_results)} passed")
        
        for r in suite_results:
            if not r.passed:
                logger.info(f"   ❌ {r.name}: {r.message}")
    
    logger.info("-"*60)
    logger.info(f"TOTAL: {total_passed}/{total_passed + total_failed} tests passed")
    
    if total_failed == 0:
        logger.info("✅ ALL TESTS PASSED - Bot is ready for trading")
        return True
    else:
        logger.info(f"❌ {total_failed} TESTS FAILED - Review issues before trading")
        return False


if __name__ == "__main__":
    logger.info(f"LiteBotX Integration Tests - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = run_all_tests()
    all_passed = print_summary(results)
    
    sys.exit(0 if all_passed else 1)

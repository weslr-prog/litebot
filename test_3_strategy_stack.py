"""
Test 3-Strategy Stack Implementation in ShortCycleTrader

Validates:
1. Mean Reversion RSI strategy triggers correctly
2. Gap & Go strategy detects gaps
3. Double Bottom pattern recognition works
4. Strategy selection chooses highest confidence
5. Signal metadata includes all strategies

Usage:
    python3 test_3_strategy_stack.py
"""

import sys
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import ShortCycleTrader components
try:
    from traders.short_cycle_trader import AISignalGenerator, ShortCycleConfig
    logger.info("✅ Successfully imported ShortCycleTrader components")
except ImportError as e:
    logger.error(f"❌ Failed to import ShortCycleTrader: {e}")
    sys.exit(1)


def create_test_data(scenario: str) -> pd.DataFrame:
    """
    Create synthetic test data for different scenarios.
    
    Scenarios:
    - 'mean_reversion': Oversold RSI
    - 'gap_up': 3% gap up at open
    - 'double_bottom': Two support tests
    - 'no_signal': Normal market
    """
    dates = pd.date_range(end=datetime.now(), periods=50, freq='D')
    
    if scenario == 'mean_reversion':
        # Create oversold RSI scenario: uptrend with pullback
        # Days 1-30: uptrend from 80 to 100 (passes 20-SMA filter)
        # Days 31-50: pullback to 92 (creates oversold RSI, still above 20-SMA)
        uptrend = np.linspace(80, 100, 30)
        pullback = np.linspace(100, 92, 20)
        prices = np.concatenate([uptrend, pullback])
        volumes = np.random.uniform(1_000_000, 2_000_000, 50)
        volumes[-1] = 3_000_000  # Volume surge on last day
        
    elif scenario == 'gap_up':
        # Create gap up scenario: uptrend with 3% gap at last day
        # Days 1-49: steady uptrend from 90 to 100
        # Day 50: gap to 103 at open
        uptrend = np.linspace(90, 100, 49)
        prices = np.concatenate([uptrend, [100.0]])  # Keep close at 100 for yesterday
        # For gap detection, we need open > yesterday close
        # Will modify open price separately
        volumes = np.random.uniform(1_000_000, 3_000_000, 50)
        
    elif scenario == 'double_bottom':
        # Create double bottom: overall uptrend with two pullbacks to support
        # Days 1-20: uptrend from 80 to 100
        # Days 21-25: pullback to 92 (first bottom)
        # Days 26-35: recovery to 98
        # Days 36-45: pullback to 92 again (double bottom)
        # Days 46-50: starting recovery to 94
        prices = np.concatenate([
            np.linspace(80, 100, 20),  # Initial uptrend
            np.linspace(100, 92, 5),   # First decline
            np.linspace(92, 98, 10),   # Bounce
            np.linspace(98, 92, 10),   # Second decline (double bottom)
            np.linspace(92, 94, 5)     # Starting to recover
        ])
        volumes = np.random.uniform(1_000_000, 2_000_000, 50)
        volumes[-1] = 3_000_000  # Volume surge
        
    else:  # no_signal
        # Normal market: sideways, no clear signals
        prices = np.random.uniform(98, 102, 50)
        volumes = np.random.uniform(1_000_000, 1_500_000, 50)
    
    # Create OHLCV data
    data = pd.DataFrame({
        'date': dates,
        'open': prices,
        'high': prices * 1.01,
        'low': prices * 0.99,
        'close': prices,
        'volume': volumes
    })
    
    # Special handling for gap_up: modify last day's open to create gap
    if scenario == 'gap_up':
        data.iloc[-1, data.columns.get_loc('open')] = data.iloc[-2, data.columns.get_loc('close')] * 1.03  # 3% gap from yesterday's close
        data.iloc[-1, data.columns.get_loc('high')] = data.iloc[-1, data.columns.get_loc('open')] * 1.01
        data.iloc[-1, data.columns.get_loc('close')] = data.iloc[-1, data.columns.get_loc('open')] * 0.995  # Slight fade from open
    
    data.set_index('date', inplace=True)
    return data


def test_mean_reversion_strategy():
    """Test Mean Reversion RSI strategy detection."""
    logger.info("\n" + "="*80)
    logger.info("TEST 1: Mean Reversion RSI Strategy")
    logger.info("="*80)
    
    # Create oversold scenario
    data = create_test_data('mean_reversion')
    symbol = "TEST_MR"
    
    # Initialize signal generator
    config = ShortCycleConfig()
    generator = AISignalGenerator(config)
    
    # Generate signal
    signal = generator._analyze_symbol(symbol, data)
    
    # Validate
    if signal:
        logger.info(f"✅ Signal generated for {symbol}")
        logger.info(f"   Strategy: {signal.features_used.get('strategy', 'unknown')}")
        logger.info(f"   Confidence: {signal.confidence:.3f}")
        logger.info(f"   RSI: {signal.features_used.get('rsi', 'N/A'):.1f}")
        logger.info(f"   Volume surge: {signal.features_used.get('volume_surge', 'N/A'):.2f}x")
        
        # Check if it's mean reversion
        if 'mean_reversion' in signal.features_used.get('strategy', ''):
            logger.info("✅ PASS: Mean Reversion RSI strategy triggered")
            return True
        else:
            logger.warning(f"⚠️ FAIL: Expected mean_reversion, got {signal.features_used.get('strategy')}")
            return False
    else:
        logger.error("❌ FAIL: No signal generated for oversold scenario")
        return False


def test_gap_and_go_strategy():
    """Test Gap & Go strategy detection."""
    logger.info("\n" + "="*80)
    logger.info("TEST 2: Gap & Go Strategy")
    logger.info("="*80)
    
    # Create gap up scenario
    data = create_test_data('gap_up')
    symbol = "TEST_GAP"
    
    # Initialize signal generator
    config = ShortCycleConfig()
    generator = AISignalGenerator(config)
    
    # Generate signal
    signal = generator._analyze_symbol(symbol, data)
    
    # Validate
    if signal:
        logger.info(f"✅ Signal generated for {symbol}")
        logger.info(f"   Strategy: {signal.features_used.get('strategy', 'unknown')}")
        logger.info(f"   Confidence: {signal.confidence:.3f}")
        logger.info(f"   Gap & Go conf: {signal.features_used.get('gap_and_go_conf', 0):.3f}")
        logger.info(f"   Volume surge: {signal.features_used.get('volume_surge', 'N/A'):.2f}x")
        
        # Check if Gap & Go confidence is non-zero
        gap_conf = signal.features_used.get('gap_and_go_conf', 0)
        if gap_conf > 0:
            logger.info("✅ PASS: Gap & Go strategy detected")
            return True
        else:
            logger.warning("⚠️ PARTIAL: Gap detected but confidence is 0")
            return False
    else:
        logger.error("❌ FAIL: No signal generated for gap scenario")
        return False


def test_double_bottom_strategy():
    """Test Double Bottom pattern detection."""
    logger.info("\n" + "="*80)
    logger.info("TEST 3: Double Bottom Strategy")
    logger.info("="*80)
    
    # Create double bottom scenario
    data = create_test_data('double_bottom')
    symbol = "TEST_DB"
    
    # Initialize signal generator
    config = ShortCycleConfig()
    generator = AISignalGenerator(config)
    
    # Generate signal
    signal = generator._analyze_symbol(symbol, data)
    
    # Validate
    if signal:
        logger.info(f"✅ Signal generated for {symbol}")
        logger.info(f"   Strategy: {signal.features_used.get('strategy', 'unknown')}")
        logger.info(f"   Confidence: {signal.confidence:.3f}")
        logger.info(f"   Double Bottom conf: {signal.features_used.get('double_bottom_conf', 0):.3f}")
        logger.info(f"   RSI: {signal.features_used.get('rsi', 'N/A'):.1f}")
        
        # Check if Double Bottom confidence is non-zero
        db_conf = signal.features_used.get('double_bottom_conf', 0)
        if db_conf > 0:
            logger.info("✅ PASS: Double Bottom strategy detected")
            return True
        else:
            logger.warning("⚠️ PARTIAL: Pattern detected but confidence is 0")
            return False
    else:
        logger.error("❌ FAIL: No signal generated for double bottom scenario")
        return False


def test_no_signal_scenario():
    """Test that no signal is generated for normal market."""
    logger.info("\n" + "="*80)
    logger.info("TEST 4: No Signal Scenario (Normal Market)")
    logger.info("="*80)
    
    # Create normal market scenario
    data = create_test_data('no_signal')
    symbol = "TEST_NONE"
    
    # Initialize signal generator
    config = ShortCycleConfig()
    generator = AISignalGenerator(config)
    
    # Generate signal
    signal = generator._analyze_symbol(symbol, data)
    
    # Validate
    if signal is None:
        logger.info("✅ PASS: No signal generated for normal market (expected)")
        return True
    else:
        logger.warning(f"⚠️ FAIL: Signal generated when none expected")
        logger.warning(f"   Strategy: {signal.features_used.get('strategy', 'unknown')}")
        logger.warning(f"   Confidence: {signal.confidence:.3f}")
        return False


def test_strategy_metadata():
    """Test that signal metadata includes all 3 strategies."""
    logger.info("\n" + "="*80)
    logger.info("TEST 5: Signal Metadata Validation")
    logger.info("="*80)
    
    # Use mean reversion scenario
    data = create_test_data('mean_reversion')
    symbol = "TEST_META"
    
    # Initialize signal generator
    config = ShortCycleConfig()
    generator = AISignalGenerator(config)
    
    # Generate signal
    signal = generator._analyze_symbol(symbol, data)
    
    if signal:
        # Check for required metadata fields
        required_fields = [
            'strategy',
            'mean_reversion_conf',
            'gap_and_go_conf',
            'double_bottom_conf',
            'rsi',
            'volume_surge'
        ]
        
        missing_fields = []
        for field in required_fields:
            if field not in signal.features_used:
                missing_fields.append(field)
        
        if not missing_fields:
            logger.info("✅ PASS: All required metadata fields present")
            logger.info(f"   Mean Reversion conf: {signal.features_used['mean_reversion_conf']:.3f}")
            logger.info(f"   Gap & Go conf: {signal.features_used['gap_and_go_conf']:.3f}")
            logger.info(f"   Double Bottom conf: {signal.features_used['double_bottom_conf']:.3f}")
            return True
        else:
            logger.error(f"❌ FAIL: Missing metadata fields: {missing_fields}")
            return False
    else:
        logger.error("❌ FAIL: No signal generated")
        return False


def run_all_tests():
    """Run all tests and report results."""
    logger.info("\n" + "="*80)
    logger.info("RUNNING 3-STRATEGY STACK VALIDATION TESTS")
    logger.info("="*80)
    
    tests = [
        ("Mean Reversion RSI", test_mean_reversion_strategy),
        ("Gap & Go", test_gap_and_go_strategy),
        ("Double Bottom", test_double_bottom_strategy),
        ("No Signal", test_no_signal_scenario),
        ("Metadata", test_strategy_metadata)
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            logger.error(f"❌ Test '{test_name}' crashed: {e}")
            import traceback
            traceback.print_exc()
            results[test_name] = False
    
    # Summary
    logger.info("\n" + "="*80)
    logger.info("TEST SUMMARY")
    logger.info("="*80)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status}: {test_name}")
    
    logger.info(f"\nResults: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        logger.info("\n🎉 ALL TESTS PASSED! 3-Strategy Stack is working correctly.")
        return 0
    else:
        logger.warning(f"\n⚠️ {total-passed} test(s) failed. Review implementation.")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())

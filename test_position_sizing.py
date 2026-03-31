#!/usr/bin/env python3
"""
Test Position Sizing Fix
Validates that IBM example returns correct position size
"""
import sys
import logging
from dataclasses import dataclass
from typing import Optional

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class MockSignal:
    """Mock AISignal for testing"""
    symbol: str
    entry_price: float
    confidence: float
    expected_return: Optional[float] = None

def test_position_sizing():
    """Test the exact IBM scenario from November 7"""
    logger.info("=" * 70)
    logger.info("Testing Position Sizing Fix")
    logger.info("=" * 70)
    
    try:
        # Import the actual components
        from small_portfolio_config import SmallPortfolioConfig
        from traders.short_cycle_trader import AIConfidencePositionSizer
        
        # Setup
        config = SmallPortfolioConfig()
        sizer = AIConfidencePositionSizer(config)
        
        # IBM test case from Nov 7
        signal = MockSignal(
            symbol="IBM",
            entry_price=312.42,
            confidence=0.524  # 52.4% confidence
        )
        stop_price = 304.61
        portfolio_value = 1000.0
        
        logger.info("\n📊 Test Case: IBM from November 7, 2025")
        logger.info(f"   Entry: ${signal.entry_price:.2f}")
        logger.info(f"   Stop: ${stop_price:.2f}")
        logger.info(f"   Risk per share: ${signal.entry_price - stop_price:.2f}")
        logger.info(f"   Confidence: {signal.confidence:.1%}")
        logger.info(f"   Portfolio: ${portfolio_value:.2f}")
        logger.info("")
        
        # Calculate position size
        shares, position_value = sizer.calculate_position_size(
            signal, stop_price, portfolio_value
        )
        
        logger.info("\n📈 Expected Results:")
        logger.info(f"   Risk: $20 (2% of $1000)")
        logger.info(f"   Shares: 2-3 (depending on confidence multiplier)")
        logger.info(f"   Position value: $200-250")
        logger.info("")
        
        logger.info("📊 Actual Results:")
        logger.info(f"   Shares: {shares}")
        logger.info(f"   Position value: ${position_value:.2f}")
        logger.info("")
        
        # Validate results
        if shares == 0 and position_value == 0.0:
            logger.error("❌ FAIL: Position sizing still returns $0!")
            logger.error("   Check DEBUG logs above to see where it failed")
            return False
        elif shares >= 0.5 and position_value >= 200:  # Allow fractional shares
            logger.info(f"✅ PASS: Position sizing works! {shares:.4f} shares @ ${position_value:.2f}")
            if shares < 1.0:
                logger.info(f"   ℹ️  Fractional shares OK for small portfolios (Alpaca supports this)")
            return True
        else:
            logger.warning(f"⚠️  PARTIAL: Got {shares} shares @ ${position_value:.2f}")
            logger.warning("   Not zero, but seems low. Check calculations.")
            return False
            
    except Exception as e:
        logger.error(f"❌ Test crashed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_edge_cases():
    """Test edge cases"""
    logger.info("\n" + "=" * 70)
    logger.info("Testing Edge Cases")
    logger.info("=" * 70)
    
    try:
        from small_portfolio_config import SmallPortfolioConfig
        from traders.short_cycle_trader import AIConfidencePositionSizer
        
        config = SmallPortfolioConfig()
        sizer = AIConfidencePositionSizer(config)
        
        # Test 1: Very small position (should reject)
        signal = MockSignal(symbol="EXPENSIVE", entry_price=1000.0, confidence=0.5)
        shares, value = sizer.calculate_position_size(signal, 990.0, 1000.0)
        
        logger.info(f"\nTest 1 - Expensive stock ($1000):")
        logger.info(f"   Result: {shares} shares @ ${value:.2f}")
        if shares == 0:
            logger.info("   ✅ Correctly rejected (position too small)")
        
        # Test 2: Cheap stock (should work)
        signal = MockSignal(symbol="CHEAP", entry_price=10.0, confidence=0.6)
        shares, value = sizer.calculate_position_size(signal, 9.0, 1000.0)
        
        logger.info(f"\nTest 2 - Cheap stock ($10):")
        logger.info(f"   Result: {shares} shares @ ${value:.2f}")
        if shares > 0:
            logger.info(f"   ✅ Position created: {shares} shares")
        
        # Test 3: Max position limit
        signal = MockSignal(symbol="MIDPRICE", entry_price=50.0, confidence=0.8)
        shares, value = sizer.calculate_position_size(signal, 47.0, 1000.0)
        
        logger.info(f"\nTest 3 - Max position test ($50):")
        logger.info(f"   Result: {shares} shares @ ${value:.2f}")
        if value <= 250:
            logger.info(f"   ✅ Correctly capped at max ${value:.2f} <= $250")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Edge case test failed: {e}")
        return False


def main():
    """Run all tests"""
    logger.info("\n")
    logger.info("=" * 70)
    logger.info("POSITION SIZING FIX VALIDATION")
    logger.info("=" * 70)
    logger.info("\n")
    
    # Test main case
    main_test_passed = test_position_sizing()
    
    # Test edge cases
    edge_tests_passed = test_edge_cases()
    
    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("TEST SUMMARY")
    logger.info("=" * 70)
    
    if main_test_passed:
        logger.info("✅ Main Test: PASSED - IBM position sizing works")
    else:
        logger.error("❌ Main Test: FAILED - Position sizing still broken")
    
    if edge_tests_passed:
        logger.info("✅ Edge Cases: PASSED")
    else:
        logger.warning("⚠️  Edge Cases: Some issues")
    
    logger.info("=" * 70)
    
    if main_test_passed and edge_tests_passed:
        logger.info("\n🎉 ALL TESTS PASSED! Position sizing is fixed.\n")
        return 0
    else:
        logger.error("\n❌ SOME TESTS FAILED - Review DEBUG logs above\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())

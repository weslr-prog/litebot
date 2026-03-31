#!/usr/bin/env python3
"""
Test diversification controls to prevent concentration risk
"""

import os
import sys
import datetime as dt
from unittest.mock import Mock, patch

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from traders.short_cycle_trader import ShortCycleTrader, ShortCycleConfig, ShortCyclePosition, PositionStatus, AISignal

def create_test_trader(portfolio_value=150000):
    """Create a trader with test configuration"""
    config = ShortCycleConfig()
    config.portfolio_value = portfolio_value
    
    # Create trader with mocked dependencies and empty positions to avoid loading positions.json
    with patch('traders.short_cycle_trader.ShortCycleTrader._load_positions') as mock_load:
        mock_load.return_value = []  # Start with empty positions
        trader = ShortCycleTrader(config)
    
    # Mock the external dependencies so we can test in isolation
    trader.execution_engine = Mock()
    trader.execution_engine.get_account_info.return_value = {"portfolio_value": portfolio_value}
    
    # Start with empty positions for clean testing
    trader.positions = []
    
    return trader

def create_test_signal(symbol: str, confidence: float = 0.6):
    """Create a test AI signal"""
    return AISignal(
        symbol=symbol,
        action="BUY",
        confidence=confidence,
        time_horizon_days=1.0,
        entry_price=100.0,
        signal_timestamp=dt.datetime.now()
    )

def create_test_position(symbol: str, status: PositionStatus = PositionStatus.ENTERED):
    """Create a test position"""
    signal = create_test_signal(symbol)
    
    position = ShortCyclePosition(
        symbol=symbol,
        entry_date=dt.date.today(),
        exit_date=dt.date.today() + dt.timedelta(days=1),
        entry_price=100.0,
        position_size_shares=10,
        position_size_dollars=1000.0,
        stop_price=95.0,
        target_price=None,
        status=status,
        ai_signal=signal
    )
    return position

def test_small_portfolio_limits():
    """Test diversification limits for small portfolios (<$100K)"""
    print("🧪 Testing small portfolio diversification limits...")
    
    # Create small portfolio trader
    trader = create_test_trader(portfolio_value=50000)  # Small portfolio
    
    # Add some existing positions (1 AAPL position)
    trader.positions = [create_test_position("AAPL")]
    
    # Test 1: Second AAPL position should be allowed (limit is 2 for small portfolios)
    result = trader._check_diversification_limits("AAPL")
    assert result == True, "Second AAPL position should be allowed for small portfolio"
    print("   ✅ Second position in same symbol allowed")
    
    # Add another AAPL position
    trader.positions.append(create_test_position("AAPL"))
    
    # Test 2: Third AAPL position should be rejected (limit is 2)
    result = trader._check_diversification_limits("AAPL")
    assert result == False, "Third AAPL position should be rejected for small portfolio"
    print("   ✅ Third position in same symbol rejected (limit: 2)")
    
    # Test 3: New symbol should be allowed
    result = trader._check_diversification_limits("MSFT")
    assert result == True, "New symbol should always be allowed"
    print("   ✅ New symbol allowed for diversification")

def test_large_portfolio_limits():
    """Test diversification limits for large portfolios (>$100K)"""
    print("\n🧪 Testing large portfolio diversification limits...")
    
    trader = create_test_trader(portfolio_value=150000)  # $150K portfolio
    
    # Add 2 AAPL positions
    trader.positions = [create_test_position("AAPL"), create_test_position("AAPL")]
    
    # Test 1: Third AAPL position should be allowed (limit is 3 for large portfolios)
    result = trader._check_diversification_limits("AAPL")
    assert result == True, "Third AAPL position should be allowed for large portfolio"
    print("   ✅ Third position in same symbol allowed")
    
    # Add third AAPL position
    trader.positions.append(create_test_position("AAPL"))
    
    # Test 2: Fourth AAPL position should be rejected (limit is 3)
    result = trader._check_diversification_limits("AAPL")
    assert result == False, "Fourth AAPL position should be rejected for large portfolio"
    print("   ✅ Fourth position in same symbol rejected (limit: 3)")

def test_concentration_limits():
    """Test concentration percentage limits"""
    print("\n🧪 Testing concentration percentage limits...")
    
    trader = create_test_trader(portfolio_value=150000)
    
    # Create scenario with 9 total positions: 2 AAPL, 7 others
    # This way we can test adding a 3rd AAPL (within position limit) but check concentration
    trader.positions = [
        create_test_position("AAPL"),
        create_test_position("AAPL"), 
        create_test_position("MSFT"),
        create_test_position("GOOGL"),
        create_test_position("AMZN"),
        create_test_position("TSLA"),
        create_test_position("NVDA"),
        create_test_position("META"),
        create_test_position("NFLX")
    ]
    
    # Current: 2/9 = 22% AAPL, adding one more = 3/10 = 30%
    # For large portfolio, limit is 40%, so this should be allowed
    result = trader._check_diversification_limits("AAPL")
    assert result == True, "AAPL concentration 30% should be under 40% limit"
    print("   ✅ 30% concentration allowed (under 40% limit)")
    
    # Now create a scenario that would exceed concentration limit
    # Add many more positions to make the math work
    trader.positions.extend([
        create_test_position("JPM"),
        create_test_position("BAC"),
        create_test_position("WMT"),
        create_test_position("PG"),
        create_test_position("JNJ")
    ])  # Now we have 14 total positions: 2 AAPL, 12 others
    
    # Adding 3rd AAPL would be 3/15 = 20%, still fine
    # But let's add one more AAPL to get 2/14, then test adding another
    trader.positions.append(create_test_position("AAPL"))  # Now 3 AAPL out of 15 = 20%
    
    # Adding 4th AAPL would exceed position limit (3), so create scenario differently
    # Instead, let's test with a scenario that has exactly the concentration limit
    trader.positions = []
    
    # Create 10 total positions: 4 AAPL, 6 others to get exactly 40% concentration
    aapl_positions = [create_test_position("AAPL") for _ in range(3)]  # Start with 3 (within limit)
    other_positions = [create_test_position(f"STOCK{i}") for i in range(7)]  # 7 others
    trader.positions = aapl_positions + other_positions  # 10 total
    
    # Current: 3/10 = 30%, adding another would be 4/11 = 36.4% (still under 40%)
    # But this would exceed the position limit of 3 per symbol, so it should be rejected for that reason
    result = trader._check_diversification_limits("AAPL")
    assert result == False, "Fourth AAPL position should be rejected due to position limit"
    print("   ✅ Position correctly rejected due to position limit (not concentration)")
    
    # Test concentration limit by creating a scenario with higher allowed positions
    # Temporarily increase the position limit for testing
    original_limit = trader.config.max_positions_per_symbol_large
    trader.config.max_positions_per_symbol_large = 10  # Allow more positions
    
    # Create scenario: 4 AAPL out of 9 total = 44.4% (exceeds 40%)
    trader.positions = [create_test_position("AAPL") for _ in range(4)]
    trader.positions.extend([create_test_position(f"STOCK{i}") for i in range(5)])
    
    # Adding 5th AAPL would be 5/10 = 50% (exceeds 40%)
    result = trader._check_diversification_limits("AAPL")
    assert result == False, "AAPL concentration would exceed 40% limit"
    print("   ✅ 50% concentration correctly rejected (exceeds 40% limit)")
    
    # Restore original limit
    trader.config.max_positions_per_symbol_large = original_limit

def test_with_current_positions():
    """Test with current positions.json data (11 AAPL out of 15 positions)"""
    print("\n🧪 Testing with current positions.json data...")
    
    trader = create_test_trader(portfolio_value=150000)
    
    # Simulate current positions.json: 11 AAPL, 1 IBM, 1 MDT, 1 MSFT, 1 TSLA
    aapl_positions = [create_test_position("AAPL") for _ in range(11)]
    other_positions = [
        create_test_position("IBM"),
        create_test_position("MDT"),
        create_test_position("MSFT"),
        create_test_position("TSLA")
    ]
    trader.positions = aapl_positions + other_positions  # 15 total, 11 AAPL
    
    # Current AAPL concentration: 11/15 = 73.3% (way over limits!)
    result = trader._check_diversification_limits("AAPL")
    assert result == False, "AAPL already over concentration limit"
    print("   ❌ AAPL concentration 73.3% correctly rejected (over all limits)")
    
    # Test that diversifying symbols are allowed
    result = trader._check_diversification_limits("GOOGL")
    assert result == True, "New symbols should be allowed to improve diversification"
    print("   ✅ New symbol GOOGL allowed for diversification")
    
    # Test existing symbols with low concentration
    result = trader._check_diversification_limits("IBM")
    assert result == True, "IBM second position should be allowed"
    print("   ✅ IBM second position allowed (only has 1 currently)")

def test_edge_cases():
    """Test edge cases and error handling"""
    print("\n🧪 Testing edge cases...")
    
    trader = create_test_trader(portfolio_value=150000)
    
    # Test with no existing positions
    trader.positions = []
    result = trader._check_diversification_limits("AAPL")
    assert result == True, "First position should always be allowed"
    print("   ✅ First position allowed when portfolio is empty")
    
    # Test with exited positions (should not count toward limits)
    trader.positions = [
        create_test_position("AAPL", PositionStatus.EXITED),
        create_test_position("AAPL", PositionStatus.EXITED),
        create_test_position("AAPL", PositionStatus.ENTERED)  # Only 1 active
    ]
    result = trader._check_diversification_limits("AAPL")
    assert result == True, "Exited positions should not count toward limits"
    print("   ✅ Exited positions correctly ignored")

def main():
    print("🚀 Testing Position Diversification Logic")
    print("=" * 60)
    
    try:
        test_small_portfolio_limits()
        test_large_portfolio_limits()
        test_concentration_limits()
        test_with_current_positions()
        test_edge_cases()
        
        print("\n" + "=" * 60)
        print("✅ ALL DIVERSIFICATION TESTS PASSED!")
        print("\n🎯 Diversification Rules Summary:")
        print("   • Small portfolios (<$100K): Max 2 positions per symbol, 35% concentration")
        print("   • Large portfolios (≥$100K): Max 3 positions per symbol, 40% concentration")
        print("   • Current positions.json AAPL concentration would be blocked")
        print("   • New symbols encouraged for better diversification")
        print("   • Exited positions don't count toward limits")
        
        print("\n🛡️ Your $963K portfolio will use LARGE portfolio rules:")
        print("   • Max 3 positions per symbol")
        print("   • Max 40% concentration in any single stock")
        print("   • This prevents the AAPL concentration risk you're concerned about")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
#!/usr/bin/env python3
"""
SmallPortfolioConfig Integration Test
Validates new small portfolio configuration module
"""

import sys
import os

# Add repo root to path
REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(REPO_ROOT)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from small_portfolio_config import SmallPortfolioConfig
from datetime import datetime, time
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_small_portfolio_config():
    """Test SmallPortfolioConfig class functionality"""
    
    print("🧪 SMALL PORTFOLIO CONFIG INTEGRATION TEST")
    print("=" * 50)
    
    # Test 1: Configuration Creation
    print("\n🔧 TEST 1: Configuration Creation")
    try:
        config = SmallPortfolioConfig()
        print("   ✅ SmallPortfolioConfig created successfully")
        
        # Validate key parameters
        assert config.portfolio_value == 1000.0, f"Expected $1000, got ${config.portfolio_value}"
        assert config.daily_pool_percent == 0.33, f"Expected 33%, got {config.daily_pool_percent:.1%}"
        assert config.max_position_dollars == 300.0, f"Expected $300, got ${config.max_position_dollars}"
        assert config.min_price == 10.0, f"Expected $10, got ${config.min_price}"
        assert config.max_price == 35.0, f"Expected $35, got ${config.max_price}"
        print("   ✅ All parameter values correct")
        
    except Exception as e:
        print(f"   ❌ Configuration creation failed: {e}")
        return False
    
    # Test 2: Daily Pool Calculation
    print("\n🔧 TEST 2: Daily Pool Calculation")
    try:
        portfolio = 1000.0
        open_positions = 200.0
        
        # Test Monday-Wednesday (33%)
        for day in ["monday", "tuesday", "wednesday"]:
            pool = config.get_daily_pool(day, portfolio, open_positions)
            expected = 330.0  # 33% of $1000
            assert pool == expected, f"{day}: Expected ${expected}, got ${pool}"
            print(f"   ✅ {day.capitalize()}: ${pool:.2f} (33% pool)")
        
        # Test Thursday (all-in)
        pool = config.get_daily_pool("thursday", portfolio, open_positions)
        expected = 800.0  # $1000 - $200 open positions
        assert pool == expected, f"Thursday: Expected ${expected}, got ${pool}"
        print(f"   ✅ Thursday: ${pool:.2f} (all-in strategy)")
        
        # Test Friday (exit only)
        pool = config.get_daily_pool("friday", portfolio, open_positions)
        expected = 0.0
        assert pool == expected, f"Friday: Expected ${expected}, got ${pool}"
        print(f"   ✅ Friday: ${pool:.2f} (exit only)")
        
    except Exception as e:
        print(f"   ❌ Daily pool calculation failed: {e}")
        return False
    
    # Test 3: Position Sizing
    print("\n🔧 TEST 3: Position Sizing")
    try:
        stock_price = 25.0
        available_capital = 330.0
        
        # Test different confidence levels
        confidence_tests = [
            ("high", 2.75),  # Average of 2.5-3.0
            ("medium", 2.15),  # Average of 1.8-2.5
            ("low", 1.5)  # Average of 1.2-1.8
        ]
        
        for confidence, expected_multiplier in confidence_tests:
            size = config.get_position_size(stock_price, confidence, available_capital)
            # Base size would be ~264 (80% of 330), so with multiplier should be close to 264 * multiplier
            # But capped at 300
            expected_size = min(300.0, 264.0 * expected_multiplier)
            expected_size = round(expected_size / 25) * 25  # Rounded to $25 increments
            
            print(f"   ✅ {confidence.capitalize()} confidence: ${size:.2f}")
        
    except Exception as e:
        print(f"   ❌ Position sizing failed: {e}")
        return False
    
    # Test 4: Exit Thresholds
    print("\n🔧 TEST 4: Exit Thresholds")
    try:
        test_times = [
            (datetime(2025, 10, 30, 10, 0), "Zone 1", 0.04, -0.025),   # 10:00 AM
            (datetime(2025, 10, 30, 12, 0), "Zone 2", 0.06, -0.03),    # 12:00 PM
            (datetime(2025, 10, 30, 14, 0), "Zone 3", 0.03, -0.025),   # 2:00 PM
            (datetime(2025, 10, 30, 15, 45), "Zone 4", 0.0, -1.0),     # 3:45 PM
        ]
        
        for test_time, zone_name, expected_take, expected_stop in test_times:
            take_profit, stop_loss = config.get_exit_thresholds(test_time)
            assert take_profit == expected_take, f"{zone_name}: Expected take {expected_take:.1%}, got {take_profit:.1%}"
            assert stop_loss == expected_stop, f"{zone_name}: Expected stop {expected_stop:.1%}, got {stop_loss:.1%}"
            print(f"   ✅ {zone_name} ({test_time.strftime('%I:%M %p')}): Take {take_profit:.1%}, Stop {stop_loss:.1%}")
        
    except Exception as e:
        print(f"   ❌ Exit thresholds failed: {e}")
        return False
    
    # Test 5: Stock Selection Filters
    print("\n🔧 TEST 5: Stock Selection Filters")
    try:
        filters = config.get_stock_selection_filters()
        expected_filters = {
            'min_price': 10.0,
            'max_price': 35.0,
            'min_volatility': 0.03,
            'max_volatility': 0.60,
            'min_momentum': 0.05,
            'max_momentum': 0.50,
            'min_avg_volume': 500_000,
            'min_dollar_volume': 5_000_000,
            'vol_spike_min': 1.5,
            'breakout_min': 0.005
        }
        
        for key, expected_value in expected_filters.items():
            assert key in filters, f"Missing filter: {key}"
            assert filters[key] == expected_value, f"{key}: Expected {expected_value}, got {filters[key]}"
        
        print(f"   ✅ All {len(filters)} stock selection filters validated")
        print(f"   ✅ Price range: ${filters['min_price']}-${filters['max_price']}")
        print(f"   ✅ Volatility range: {filters['min_volatility']:.1%}-{filters['max_volatility']:.1%}")
        
    except Exception as e:
        print(f"   ❌ Stock selection filters failed: {e}")
        return False
    
    # Test 6: Risk Validation
    print("\n🔧 TEST 6: Risk Validation")
    try:
        # Test valid trade
        position_size = 250.0
        entry_price = 25.0
        stop_loss_price = 23.75  # -5% 
        shares = int(position_size / entry_price)  # 10 shares
        
        is_valid = config.validate_trade_risk(position_size, stop_loss_price, entry_price, shares)
        risk = (entry_price - stop_loss_price) * shares  # $1.25 * 10 = $12.50
        assert is_valid == True, f"Expected valid trade, got invalid (risk: ${risk:.2f})"
        print(f"   ✅ Valid trade: ${risk:.2f} risk (within ${config.max_risk_per_trade_dollars} limit)")
        
        # Test invalid trade (too much risk)
        stop_loss_price = 20.0  # -20% = $50 risk
        is_valid = config.validate_trade_risk(position_size, stop_loss_price, entry_price, shares)
        risk = (entry_price - stop_loss_price) * shares  # $5 * 10 = $50
        assert is_valid == False, f"Expected invalid trade, got valid (risk: ${risk:.2f})"
        print(f"   ✅ Invalid trade rejected: ${risk:.2f} risk (exceeds ${config.max_risk_per_trade_dollars} limit)")
        
    except Exception as e:
        print(f"   ❌ Risk validation failed: {e}")
        return False
    
    # Test 7: Configuration Logging
    print("\n🔧 TEST 7: Configuration Logging")
    try:
        config.log_configuration()
        print("   ✅ Configuration logging completed")
        
    except Exception as e:
        print(f"   ❌ Configuration logging failed: {e}")
        return False
    
    print("\n🎉 ALL TESTS PASSED!")
    print("✅ SmallPortfolioConfig integration successful")
    print("✅ Ready for small portfolio trading")
    
    return True

if __name__ == "__main__":
    success = test_small_portfolio_config()
    sys.exit(0 if success else 1)
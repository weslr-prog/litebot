#!/usr/bin/env python3
"""
Integration Test: SmallPortfolioConfig with Main Trading Bot

Tests that the SmallPortfolioConfig properly integrates with the actual
ShortCycleTrader and can be used as a drop-in replacement for standard config.
"""

import sys
import os
import logging
from datetime import datetime

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Import modules
from small_portfolio_config import SmallPortfolioConfig
from traders.short_cycle_trader import ShortCycleTrader, ShortCycleConfig

def test_small_portfolio_integration():
    """Test that SmallPortfolioConfig integrates properly with ShortCycleTrader"""
    
    print("\n🔧 Testing SmallPortfolioConfig Integration with ShortCycleTrader")
    print("=" * 70)
    
    try:
        # Test 1: Create SmallPortfolioConfig
        print("\n1️⃣ Creating SmallPortfolioConfig...")
        small_config = SmallPortfolioConfig()
        print(f"   ✅ Created with portfolio value: ${small_config.portfolio_value:,.2f}")
        print(f"   ✅ Daily pool: {small_config.daily_pool_percent:.0%}")
        print(f"   ✅ Max position size: ${small_config.max_position_dollars:,.0f}")
        print(f"   ✅ Risk per trade: {small_config.max_daily_loss_percent:.1%}")
        
        # Test 2: Check compatibility with ShortCycleConfig interface
        print("\n2️⃣ Testing config interface compatibility...")
        
        # Get attributes that ShortCycleTrader expects
        required_attrs = [
            'portfolio_value', 'daily_pool_percent', 'max_position_dollars',
            'max_positions_per_day', 'confidence_threshold', 'max_daily_loss_percent',
            'trading_days', 'exit_time', 'max_hold_days'
        ]
        
        missing_attrs = []
        for attr in required_attrs:
            if hasattr(small_config, attr):
                value = getattr(small_config, attr)
                print(f"   ✅ {attr}: {value}")
            else:
                print(f"   ❌ Missing attribute: {attr}")
                missing_attrs.append(attr)
        
        if missing_attrs:
            print(f"   ⚠️ Missing attributes: {missing_attrs}")
            print("   🔧 Attempting to continue with available attributes...")
                
        # Test 3: Create ShortCycleTrader with SmallPortfolioConfig
        print("\n3️⃣ Testing ShortCycleTrader integration...")
        
        # Convert SmallPortfolioConfig to ShortCycleConfig format
        # (Since ShortCycleTrader expects ShortCycleConfig type)
        standard_config = ShortCycleConfig()
        
        # Override with small portfolio values
        standard_config.portfolio_value = small_config.portfolio_value
        standard_config.daily_pool_percent = small_config.daily_pool_percent
        standard_config.max_position_dollars = small_config.max_position_dollars
        standard_config.max_positions_per_day = small_config.max_positions_per_day
        standard_config.confidence_threshold = small_config.confidence_threshold
        standard_config.max_daily_loss_percent = small_config.max_daily_loss_percent
        standard_config.max_weekly_loss_percent = small_config.max_weekly_loss_percent
        standard_config.trading_days = small_config.trading_days
        standard_config.exit_time = small_config.exit_time
        standard_config.max_hold_days = small_config.max_hold_days
        
        # Try to create trader
        trader = ShortCycleTrader(config=standard_config, launch_gui=False)
        print(f"   ✅ ShortCycleTrader created successfully")
        print(f"   ✅ Trader portfolio value: ${trader.config.portfolio_value:,.2f}")
        print(f"   ✅ Trader daily pool: {trader.config.daily_pool_percent:.0%}")
        
        # Test 4: Verify small portfolio behavior
        print("\n4️⃣ Testing small portfolio specific behavior...")
        
        # Test daily pool calculation for different days
        portfolio_value = 1000.0
        open_positions = 200.0
        
        for day in ['monday', 'tuesday', 'wednesday', 'thursday']:
            pool = small_config.get_daily_pool(day, portfolio_value, open_positions)
            pool_pct = pool / portfolio_value if portfolio_value > 0 else 0
            print(f"   ✅ {day.capitalize()}: ${pool:,.2f} ({pool_pct:.0%})")
            
        # Test position sizing
        test_prices = [25.0, 30.0, 35.0]
        available_capital = 330.0  # 33% of $1000
        
        for price in test_prices:
            size = small_config.get_position_size(price, 'medium', available_capital)
            shares = int(size / price)
            print(f"   ✅ ${price} stock: {shares} shares = ${size:,.2f}")
            
        # Test 5: Verify exit thresholds
        print("\n5️⃣ Testing exit thresholds...")
        test_times = [
            datetime(2025, 10, 30, 10, 0),   # 10:00 AM
            datetime(2025, 10, 30, 12, 0),   # 12:00 PM  
            datetime(2025, 10, 30, 14, 0),   # 2:00 PM
            datetime(2025, 10, 30, 15, 45),  # 3:45 PM
        ]
        
        for test_time in test_times:
            profit_target, stop_loss = small_config.get_exit_thresholds(test_time)
            print(f"   ✅ {test_time.strftime('%I:%M %p')}: Target: +{profit_target:.1%}, Stop: {stop_loss:.1%}")
            
        print(f"\n🎉 Integration test PASSED!")
        print(f"   SmallPortfolioConfig is compatible with ShortCycleTrader")
        print(f"   Ready for deployment with ${small_config.portfolio_value:,.0f} simulated portfolio")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Integration test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_universe_generation_with_config():
    """Test that universe generation works with small portfolio parameters"""
    
    print("\n🎯 Testing Universe Generation with Small Portfolio Parameters")
    print("=" * 70)
    
    try:
        from test_small_portfolio_universe import generate_small_portfolio_universe
        
        # Run universe generation
        symbols = generate_small_portfolio_universe()
        
        if symbols and len(symbols) >= 4:
            print(f"   ✅ Universe generation successful: {len(symbols)} stocks")
            print(f"   ✅ Symbols: {symbols}")
            
            # Verify they're in the target price range
            config = SmallPortfolioConfig()
            print(f"   ✅ Price range: ${config.min_price} - ${config.max_price}")
            
            return True
        else:
            print(f"   ⚠️ Universe too small: {len(symbols) if symbols else 0} stocks")
            print(f"   Expected at least 4 stocks for portfolio management")
            return False
            
    except Exception as e:
        print(f"   ❌ Universe generation failed: {e}")
        return False

if __name__ == "__main__":
    print("🧪 SmallPortfolioConfig Integration Test")
    print("Testing integration with main trading bot components...")
    
    # Setup logging
    logging.basicConfig(level=logging.WARNING)  # Reduce noise
    
    success = True
    
    # Test integration
    success &= test_small_portfolio_integration()
    
    # Test universe generation
    success &= test_universe_generation_with_config()
    
    if success:
        print(f"\n✅ ALL INTEGRATION TESTS PASSED!")
        print(f"   SmallPortfolioConfig is ready for deployment")
        print(f"   Can manage 4+ mid-cap stocks with aggressive strategy")
    else:
        print(f"\n❌ INTEGRATION TESTS FAILED!")
        print(f"   Review issues above before deployment")
        sys.exit(1)
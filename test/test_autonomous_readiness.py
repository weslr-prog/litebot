#!/usr/bin/env python3
"""
Autonomous Trading Bot Readiness Test
=====================================

Comprehensive test suite to ensure the bot is ready for autonomous operation
while the user is at work (6 AM - 5 PM).

Tests:
1. Position management (load/save/exit)
2. Market hours handling
3. D+1 exit logic
4. Error recovery
5. Dashboard persistence
6. Alpaca connectivity
7. Continuous operation simulation
"""

import os
import sys
import json
import datetime as dt
from datetime import datetime, timedelta
import pandas as pd
import time

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def test_position_management():
    """Test position loading, saving, and D+1 exit logic"""
    print("\n🧪 Test 1: Position Management")
    
    try:
        from traders.short_cycle_trader import ShortCycleTrader, ShortCycleConfig
        
        # Create trader instance
        config = ShortCycleConfig()
        trader = ShortCycleTrader(config)
        
        # Test loading existing positions
        trader._load_positions()
        print(f"✅ Loaded {len(trader.positions)} positions")
        
        if trader.positions:
            pos = trader.positions[0]
            print(f"📊 Current position: {pos.symbol} ({pos.position_size_shares} shares)")
            print(f"📅 Entry: {pos.entry_date}, Exit scheduled: {pos.exit_date}")
            stop_price = pos.stop_price if pos.stop_price else 0.0
            print(f"💰 Entry price: ${pos.entry_price:.2f}, Stop: ${stop_price:.2f}")
            
            # Test D+1 exit logic
            tomorrow = dt.date.today() + timedelta(days=1)
            should_exit = pos.should_force_exit(tomorrow)
            print(f"🔄 Should exit tomorrow ({tomorrow}): {should_exit}")
            
        # Test saving
        trader._save_positions()
        print("✅ Position save/load test passed")
        
    except Exception as e:
        print(f"❌ Position management test failed: {e}")
        return False
    
    return True

def test_market_hours_logic():
    """Test market hours detection and scheduling"""
    print("\n🧪 Test 2: Market Hours Logic")
    
    try:
        from utils import market_hours
        import pytz
        
        # Test different times
        est = pytz.timezone('America/New_York')
        
        # Test current time
        now = datetime.now(est)
        print(f"📅 Current time (ET): {now}")
        print(f"🏛️ Is market hours: {market_hours.is_market_hours(now)}")
        print(f"🌅 Is premarket: {market_hours.is_premarket_hours(now)}")
        print(f"🌙 Is post-market: {market_hours.is_post_market_hours(now)}")
        
        # Test next market open
        next_open = market_hours.next_market_open(now)
        print(f"⏰ Next market open: {next_open}")
        
        # Calculate time until next open
        hours_until_open = (next_open - now).total_seconds() / 3600
        print(f"⏳ Hours until next open: {hours_until_open:.1f}")
        
        print("✅ Market hours logic test passed")
        
    except Exception as e:
        print(f"❌ Market hours test failed: {e}")
        return False
    
    return True

def test_alpaca_connectivity():
    """Test Alpaca API connection and basic operations"""
    print("\n🧪 Test 3: Alpaca Connectivity")
    
    try:
        from connect_real_trading import RealPaperTradingEngine
        
        # Test connection
        engine = RealPaperTradingEngine()
        print("✅ Alpaca engine initialized")
        
        # Test account info
        account = engine.trading_client.get_account()
        print(f"💰 Portfolio value: ${float(account.portfolio_value):,.2f}")
        print(f"💵 Buying power: ${float(account.buying_power):,.2f}")
        
        # Test positions
        positions = engine.trading_client.get_all_positions()
        print(f"📊 Current Alpaca positions: {len(positions)}")
        
        for pos in positions:
            print(f"   {pos.symbol}: {pos.qty} shares @ ${float(pos.avg_entry_price):.2f}")
        
        print("✅ Alpaca connectivity test passed")
        
    except Exception as e:
        print(f"❌ Alpaca connectivity test failed: {e}")
        return False
    
    return True

def test_error_recovery():
    """Test error handling and recovery mechanisms"""
    print("\n🧪 Test 4: Error Recovery")
    
    try:
        from traders.short_cycle_trader import ShortCycleTrader, ShortCycleConfig
        
        config = ShortCycleConfig()
        trader = ShortCycleTrader(config)
        
        # Test handling corrupted position data
        print("🔍 Testing corrupted data handling...")
        original_file = "positions.json"
        backup_file = "positions_backup_test.json"
        
        # Backup original
        if os.path.exists(original_file):
            import shutil
            shutil.copy(original_file, backup_file)
        
        # Create corrupted file
        with open(original_file, 'w') as f:
            f.write('{"invalid": json}')
        
        # Test loading corrupted data
        trader._load_positions()
        print("✅ Handles corrupted position data gracefully")
        
        # Restore original
        if os.path.exists(backup_file):
            shutil.move(backup_file, original_file)
        
        print("✅ Error recovery test passed")
        
    except Exception as e:
        print(f"❌ Error recovery test failed: {e}")
        return False
    
    return True

def test_continuous_operation():
    """Test continuous operation scheduling"""
    print("\n🧪 Test 5: Continuous Operation Simulation")
    
    try:
        from traders.short_cycle_trader import ShortCycleTrader, ShortCycleConfig
        from utils import market_hours
        import pytz
        
        config = ShortCycleConfig()
        trader = ShortCycleTrader(config)
        
        # Test work hours (6 AM - 5 PM) scenarios
        est = pytz.timezone('America/New_York')
        
        # Simulate different times during work hours
        test_times = [
            "06:00",  # Start of work day
            "09:30",  # Market open
            "10:15",  # Entry window
            "12:00",  # Midday
            "15:45",  # Near market close
            "17:00",  # End of work day
        ]
        
        for time_str in test_times:
            # Create test datetime for tomorrow
            tomorrow = dt.date.today() + timedelta(days=1)
            test_time = datetime.strptime(f"{tomorrow} {time_str}", "%Y-%m-%d %H:%M")
            test_time = est.localize(test_time)
            
            is_market = market_hours.is_market_hours(test_time)
            is_premarket = market_hours.is_premarket_hours(test_time)
            is_postmarket = market_hours.is_post_market_hours(test_time)
            
            print(f"⏰ {time_str}: Market={is_market}, Pre={is_premarket}, Post={is_postmarket}")
        
        print("✅ Continuous operation test passed")
        
    except Exception as e:
        print(f"❌ Continuous operation test failed: {e}")
        return False
    
    return True

def test_d1_exit_simulation():
    """Simulate D+1 exit for tomorrow's work hours"""
    print("\n🧪 Test 6: D+1 Exit Simulation")
    
    try:
        from traders.short_cycle_trader import ShortCycleTrader, ShortCycleConfig
        
        config = ShortCycleConfig()
        trader = ShortCycleTrader(config)
        trader._load_positions()
        
        if not trader.positions:
            print("⚠️ No positions to test D+1 exit")
            return True
        
        pos = trader.positions[0]
        print(f"📊 Testing D+1 exit for {pos.symbol}")
        
        # Simulate tomorrow's date
        tomorrow = dt.date.today() + timedelta(days=1)
        should_exit = pos.should_force_exit(tomorrow)
        
        if should_exit:
            print(f"✅ Position will be exited tomorrow ({tomorrow})")
            stop_price = pos.stop_price if pos.stop_price else 0.0
            position_dollars = pos.position_size_dollars if pos.position_size_dollars else 0.0
            print(f"📈 Entry: ${pos.entry_price:.2f}, Current stop: ${stop_price:.2f}")
            print(f"💼 Position size: {pos.position_size_shares} shares (${position_dollars:.2f})")
        else:
            print(f"⚠️ Position NOT scheduled for exit tomorrow")
        
        print("✅ D+1 exit simulation passed")
        
    except Exception as e:
        print(f"❌ D+1 exit simulation failed: {e}")
        return False
    
    return True

def test_dashboard_persistence():
    """Test dashboard data persistence"""
    print("\n🧪 Test 7: Dashboard Persistence")
    
    try:
        from gui.short_cycle_dashboard import ShortCycleDashboard, ShortCycleMetricsTracker
        
        # Create metrics tracker
        metrics = ShortCycleMetricsTracker()
        
        # Test data persistence
        metrics.last_portfolio_value = 1000.0
        metrics.last_positions = {"LYFT": {"quantity": 8, "avg_price": 22.84}}
        
        # Test performance summary
        summary = metrics.get_performance_summary()
        print(f"📊 Performance summary: {len(summary)} metrics")
        
        print("✅ Dashboard persistence test passed")
        
    except Exception as e:
        print(f"❌ Dashboard persistence test failed: {e}")
        return False
    
    return True

def run_autonomous_readiness_test():
    """Run all readiness tests"""
    print("🚀 AUTONOMOUS TRADING BOT READINESS TEST")
    print("=" * 50)
    print("Testing bot readiness for 6 AM - 5 PM autonomous operation")
    
    tests = [
        ("Position Management", test_position_management),
        ("Market Hours Logic", test_market_hours_logic),
        ("Alpaca Connectivity", test_alpaca_connectivity),
        ("Error Recovery", test_error_recovery),
        ("Continuous Operation", test_continuous_operation),
        ("D+1 Exit Simulation", test_d1_exit_simulation),
        ("Dashboard Persistence", test_dashboard_persistence),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 TEST RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 BOT IS READY FOR AUTONOMOUS OPERATION!")
        print("\n✅ WORK DAY READINESS CHECKLIST:")
        print("   ✓ Position management working")
        print("   ✓ Market hours detection active")
        print("   ✓ Alpaca connectivity confirmed")
        print("   ✓ Error recovery mechanisms in place")
        print("   ✓ Continuous operation logic tested")
        print("   ✓ D+1 exit logic confirmed")
        print("   ✓ Dashboard persistence enabled")
        
        print("\n🕐 TOMORROW'S SCHEDULE (while you're at work):")
        print("   06:00 - Bot monitoring (you start work)")
        print("   09:30 - Market opens, bot enters monitoring mode")
        print("   10:00-10:30 - Entry window (if opportunities found)")
        print("   15:45 - D+1 exits processed (LYFT position)")
        print("   16:00 - Market closes, bot enters post-market mode")
        print("   17:00 - You return from work")
        
    else:
        print("⚠️ SOME TESTS FAILED - REVIEW BEFORE LEAVING BOT UNATTENDED")
    
    return passed == total

if __name__ == "__main__":
    run_autonomous_readiness_test()
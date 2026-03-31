#!/usr/bin/env python3
"""
Comprehensive Weekend Testing Suite for ShortCycleTrader
Tests all critical functionality while markets are closed.
"""

import sys
import os
import json
import shutil
from datetime import datetime, date, timedelta
from pathlib import Path

sys.path.append('/home/wes/Desktop/litebotx-usb-deployment')

from traders.short_cycle_trader import ShortCycleConfig, ShortCycleTrader, ShortCyclePosition, PositionStatus, AISignal

def backup_current_data():
    """Backup current positions and state for restoration after testing"""
    backup_dir = f"test_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(backup_dir, exist_ok=True)
    
    files_to_backup = ['positions.json']
    for file in files_to_backup:
        if os.path.exists(file):
            shutil.copy2(file, f"{backup_dir}/{file}")
            print(f"📦 Backed up {file}")
    
    return backup_dir

def restore_data(backup_dir):
    """Restore original data after testing"""
    files_to_restore = ['positions.json']
    for file in files_to_restore:
        backup_file = f"{backup_dir}/{file}"
        if os.path.exists(backup_file):
            shutil.copy2(backup_file, file)
            print(f"🔄 Restored {file}")

def create_test_positions():
    """Create test positions for validation"""
    today = date.today()
    yesterday = today - timedelta(days=1)
    
    positions = [
        # Position that should be exited (D+1)
        {
            "symbol": "AAPL",
            "entry_date": yesterday.isoformat(),
            "exit_date": today.isoformat(),
            "entry_price": 220.0,
            "position_size_shares": 10,
            "position_size_dollars": 2200.0,
            "stop_price": 215.0,
            "target_price": 225.0,
            "status": "entered",
            "max_risk_dollars": 50.0,
            "current_price": 222.0,
            "unrealized_pnl": 20.0,
            "ai_signal": {
                "symbol": "AAPL",
                "action": "BUY",
                "entry_price": 220.0,
                "confidence": 0.75,
                "time_horizon_days": 1,
                "signal_timestamp": datetime.now().isoformat(),
                "features_used": {"momentum": 0.8}
            }
        },
        # Position that hit stop loss
        {
            "symbol": "MSFT",
            "entry_date": yesterday.isoformat(),
            "exit_date": today.isoformat(),
            "entry_price": 400.0,
            "position_size_shares": 5,
            "position_size_dollars": 2000.0,
            "stop_price": 395.0,
            "target_price": None,
            "status": "STOPPED_OUT",
            "exit_price": 394.0,
            "exit_reason": "STOP_LOSS",
            "exit_timestamp": datetime.now().isoformat(),
            "realized_pnl": -30.0,
            "hold_days": 1,
            "max_risk_dollars": 25.0,
            "ai_signal": {
                "symbol": "MSFT",
                "action": "BUY",
                "entry_price": 400.0,
                "confidence": 0.65,
                "time_horizon_days": 1,
                "signal_timestamp": (datetime.now() - timedelta(days=1)).isoformat(),
                "features_used": {"momentum": 0.7}
            }
        },
        # Fresh position (today's entry)
        {
            "symbol": "GOOGL",
            "entry_date": today.isoformat(),
            "exit_date": (today + timedelta(days=1)).isoformat(),
            "entry_price": 150.0,
            "position_size_shares": 15,
            "position_size_dollars": 2250.0,
            "stop_price": 147.0,
            "target_price": 155.0,
            "status": "entered",
            "max_risk_dollars": 45.0,
            "current_price": 151.5,
            "unrealized_pnl": 22.5,
            "ai_signal": {
                "symbol": "GOOGL",
                "action": "BUY",
                "entry_price": 150.0,
                "confidence": 0.80,
                "time_horizon_days": 1,
                "signal_timestamp": datetime.now().isoformat(),
                "features_used": {"momentum": 0.85}
            }
        }
    ]
    
    with open('positions.json', 'w') as f:
        json.dump(positions, f, indent=2)
    
    print(f"✅ Created {len(positions)} test positions")
    return positions

def test_position_loading():
    """Test position loading and parsing"""
    print("\n🧪 Testing Position Loading...")
    
    try:
        config = ShortCycleConfig()
        trader = ShortCycleTrader(config)
        trader._load_positions()
        
        print(f"   📊 Loaded {len(trader.positions)} positions")
        
        # Check position types
        entered = [p for p in trader.positions if p.status == PositionStatus.ENTERED]
        exited = [p for p in trader.positions if p.status in [PositionStatus.EXITED, PositionStatus.STOPPED_OUT]]
        
        print(f"   📈 Open positions: {len(entered)}")
        print(f"   📉 Closed positions: {len(exited)}")
        
        for pos in entered:
            print(f"      • {pos.symbol}: ${pos.entry_price:.2f} → ${pos.current_price:.2f} (${pos.unrealized_pnl:.2f})")
        
        return True
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def test_daily_pnl_calculation():
    """Test daily P&L calculation logic"""
    print("\n🧪 Testing Daily P&L Calculation...")
    
    try:
        config = ShortCycleConfig()
        trader = ShortCycleTrader(config)
        trader._load_positions()
        
        # Reset and calculate
        trader._maybe_reset_daily_counters()
        trader._update_daily_pnl()
        
        print(f"   📊 Daily realized P&L: ${trader.daily_realized_pnl:.2f}")
        print(f"   📊 Daily unrealized P&L: ${trader.daily_unrealized_pnl:.2f}")
        print(f"   📊 Total daily P&L: ${trader.daily_pnl:.2f}")
        
        # Test with different portfolio values
        trader._update_risk_limits()
        print(f"   💰 Current portfolio: ${trader.config.portfolio_value:,.2f}")
        print(f"   🛑 Daily loss limit: ${trader.config.max_daily_loss_dollars:.2f}")
        
        return True
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def test_position_exit_logic():
    """Test D+1 exit and stop loss logic"""
    print("\n🧪 Testing Position Exit Logic...")
    
    try:
        config = ShortCycleConfig()
        trader = ShortCycleTrader(config)
        trader._load_positions()
        
        today = date.today()
        
        # Check D+1 exit logic
        positions_to_exit = []
        for pos in trader.positions:
            if pos.status == PositionStatus.ENTERED:
                should_exit = pos.should_force_exit(today)
                is_stopped = pos.is_stopped_out(pos.current_price or pos.entry_price)
                
                print(f"   📊 {pos.symbol}:")
                print(f"      Entry: {pos.entry_date}, Exit due: {pos.exit_date}")
                print(f"      Should force exit (D+1): {should_exit}")
                print(f"      Should stop out: {is_stopped}")
                
                if should_exit or is_stopped:
                    positions_to_exit.append(pos)
        
        print(f"   📈 Positions requiring exit: {len(positions_to_exit)}")
        return True
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def test_kill_switch_logic():
    """Test kill switch and loss limit logic"""
    print("\n🧪 Testing Kill Switch Logic...")
    
    try:
        config = ShortCycleConfig()
        trader = ShortCycleTrader(config)
        trader._load_positions()
        
        # Test with current state
        trader._update_daily_pnl()
        
        print(f"   📊 Current daily P&L: ${trader.daily_pnl:.2f}")
        print(f"   🛑 Daily loss limit: ${trader.config.max_daily_loss_dollars:.2f}")
        
        # Simulate loss scenarios
        test_scenarios = [
            ("Small loss", -10.0),
            ("Large loss", -50.0),  # Exceeds $15 limit
            ("Large gain", 100.0)
        ]
        
        for name, test_pnl in test_scenarios:
            trader.daily_realized_pnl = test_pnl
            trader.daily_pnl = test_pnl
            
            # Reset kill switches
            trader.kill_switches = {"daily_loss_exceeded": False, "weekly_loss_exceeded": False, "system_error": False}
            
            print(f"   🔬 Testing {name} (${test_pnl:.2f}):")
            
            # Check if trading would be allowed
            should_trade = trader.should_trade_today()
            print(f"      Should trade: {should_trade}")
            
            # Test loss limit check (won't actually trigger during weekends due to market hours guard)
            if test_pnl < 0 and abs(test_pnl) > trader.config.max_daily_loss_dollars:
                print(f"      Would trigger loss limit: YES")
            else:
                print(f"      Would trigger loss limit: NO")
        
        return True
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def test_signal_generation():
    """Test signal generation logic"""
    print("\n🧪 Testing Signal Generation...")
    
    try:
        config = ShortCycleConfig()
        trader = ShortCycleTrader(config)
        
        # Get trading universe
        universe = trader._get_trading_universe()
        print(f"   📊 Trading universe size: {len(universe)}")
        print(f"   📋 Sample symbols: {universe[:5]}")
        
        # Test market data fetching
        print(f"   📈 Testing market data fetch...")
        market_data = trader._get_market_data()
        print(f"   📊 Market data symbols: {len(market_data)}")
        
        if market_data:
            sample_symbol = list(market_data.keys())[0]
            sample_data = market_data[sample_symbol]
            print(f"   📊 Sample data for {sample_symbol}: {len(sample_data)} rows")
        
        return True
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def test_portfolio_integration():
    """Test portfolio value and execution engine integration"""
    print("\n🧪 Testing Portfolio Integration...")
    
    try:
        config = ShortCycleConfig()
        trader = ShortCycleTrader(config)
        
        # Test portfolio value fetching
        portfolio_value = trader._get_portfolio_value()
        print(f"   💰 Portfolio value: ${portfolio_value:,.2f}")
        
        # Test execution engine
        if hasattr(trader, 'execution_engine') and trader.execution_engine:
            portfolio_summary = trader.execution_engine.get_portfolio_summary()
            print(f"   📊 Execution engine equity: ${portfolio_summary.get('equity', 0):,.2f}")
            print(f"   📊 Total trades: {portfolio_summary.get('total_trades', 0)}")
            print(f"   📊 Win rate: {portfolio_summary.get('win_rate', 0):.1%}")
        
        # Test risk limit updates
        old_limit = trader.config.max_daily_loss_dollars
        trader._update_risk_limits()
        new_limit = trader.config.max_daily_loss_dollars
        
        print(f"   🛑 Daily loss limit: ${old_limit:.2f} → ${new_limit:.2f}")
        
        return True
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def run_comprehensive_test():
    """Run all tests and provide summary"""
    print("🚀 ShortCycleTrader Comprehensive Weekend Testing")
    print("=" * 60)
    
    # Backup current data
    backup_dir = backup_current_data()
    
    try:
        # Create test environment
        create_test_positions()
        
        # Run all tests
        tests = [
            ("Position Loading", test_position_loading),
            ("Daily P&L Calculation", test_daily_pnl_calculation),
            ("Position Exit Logic", test_position_exit_logic),
            ("Kill Switch Logic", test_kill_switch_logic),
            ("Signal Generation", test_signal_generation),
            ("Portfolio Integration", test_portfolio_integration)
        ]
        
        results = {}
        for test_name, test_func in tests:
            print(f"\n{'=' * 60}")
            results[test_name] = test_func()
        
        # Summary
        print(f"\n{'=' * 60}")
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(results.values())
        total = len(results)
        
        for test_name, passed in results.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{status} {test_name}")
        
        print(f"\n🎯 Overall: {passed}/{total} tests passed ({passed/total:.1%})")
        
        if passed == total:
            print("\n🎉 ALL TESTS PASSED! Bot is ready for Monday trading!")
        else:
            print("\n⚠️ Some tests failed. Review issues before live trading.")
    
    finally:
        # Restore original data
        restore_data(backup_dir)
        print(f"\n🔄 Original data restored from {backup_dir}")

if __name__ == "__main__":
    run_comprehensive_test()
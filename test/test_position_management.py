#!/usr/bin/env python3
"""
Test Position Management - Verify position loading, D+1 logic, and dashboard integration
"""

import sys
import os
import json
import datetime as dt
from pathlib import Path

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from traders.short_cycle_trader import ShortCycleTrader, ShortCycleConfig
    print("✅ Successfully imported ShortCycleTrader")
except ImportError as e:
    print(f"❌ Failed to import ShortCycleTrader: {e}")
    sys.exit(1)

def test_position_loading():
    """Test that positions are correctly loaded from positions.json"""
    print("\n" + "="*60)
    print("🧪 Testing Position Loading from positions.json")
    print("="*60)
    
    # Create trader instance
    config = ShortCycleConfig()
    trader = ShortCycleTrader(config)
    
    # Check if positions.json exists
    positions_file = "positions.json"
    if not os.path.exists(positions_file):
        print(f"❌ positions.json not found at {os.path.abspath(positions_file)}")
        return False
    
    print(f"📄 Found positions.json at {os.path.abspath(positions_file)}")
    
    # Read raw JSON to verify format
    try:
        with open(positions_file, 'r') as f:
            raw_data = f.read()
            print(f"📝 Raw JSON content (first 200 chars): {raw_data[:200]}...")
            
        with open(positions_file, 'r') as f:
            position_data = json.load(f)
            print(f"✅ JSON is valid, contains {len(position_data)} position(s)")
            
        for i, pos in enumerate(position_data):
            print(f"   Position {i+1}: {pos.get('symbol', 'Unknown')} - {pos.get('status', 'Unknown status')}")
            print(f"      Entry Date: {pos.get('entry_date', 'Unknown')}")
            print(f"      Exit Date: {pos.get('exit_date', 'Unknown')}")
            
    except json.JSONDecodeError as e:
        print(f"❌ JSON format error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error reading positions.json: {e}")
        return False
    
    # Test trader's position loading
    print(f"\n🔄 Testing trader._load_positions()...")
    trader._load_positions()
    
    print(f"📊 Trader loaded {len(trader.positions)} position(s)")
    for i, pos in enumerate(trader.positions):
        print(f"   Position {i+1}: {pos.symbol}")
        print(f"      Status: {pos.status}")
        print(f"      Entry Date: {pos.entry_date}")
        print(f"      Exit Date: {pos.exit_date}")
        print(f"      Should Force Exit Today?: {pos.should_force_exit(dt.date.today())}")
    
    return len(trader.positions) > 0

def test_d1_exit_logic():
    """Test D+1 exit logic for positions"""
    print("\n" + "="*60)
    print("🧪 Testing D+1 Exit Logic")
    print("="*60)
    
    config = ShortCycleConfig()
    trader = ShortCycleTrader(config)
    trader._load_positions()
    
    today = dt.date.today()
    print(f"📅 Today's date: {today}")
    
    positions_to_exit = []
    for pos in trader.positions:
        if pos.status.value == "entered":
            should_exit = pos.should_force_exit(today)
            print(f"📊 {pos.symbol}:")
            print(f"   Entry Date: {pos.entry_date}")
            print(f"   Exit Date: {pos.exit_date}")
            print(f"   Status: {pos.status}")
            print(f"   Should Force Exit?: {should_exit}")
            
            if should_exit:
                positions_to_exit.append(pos)
    
    print(f"\n🎯 Found {len(positions_to_exit)} position(s) that should be force-exited")
    
    # Test the _process_existing_positions method
    print(f"\n🔄 Testing _process_existing_positions()...")
    try:
        trader._process_existing_positions()
        print("✅ _process_existing_positions() completed without errors")
        
        # Check if positions were actually exited
        exited_count = sum(1 for pos in trader.positions if pos.status.value in ["exited", "stopped_out"])
        print(f"📊 After processing: {exited_count} position(s) are now exited")
        
    except Exception as e:
        print(f"❌ Error in _process_existing_positions(): {e}")
        return False
    
    return True

def test_dashboard_connection():
    """Test if dashboard can access position data"""
    print("\n" + "="*60)
    print("🧪 Testing Dashboard Position Data Access")
    print("="*60)
    
    try:
        # Try to import dashboard components
        sys.path.append('gui')
        from connect_real_trading import RealPaperTradingEngine
        
        # Test RealPaperTradingEngine (used by dashboard)
        engine = RealPaperTradingEngine()
        print("✅ RealPaperTradingEngine initialized")
        
        # Test position access
        positions = engine.get_positions()
        print(f"📊 RealPaperTradingEngine found {len(positions)} Alpaca position(s)")
        
        # Test account info
        account_info = engine.get_account_info()
        if account_info:
            print(f"✅ Account access successful")
            print(f"   Portfolio Value: ${account_info['portfolio_value']:,.2f}")
        else:
            print("❌ Failed to get account info")
            
    except Exception as e:
        print(f"❌ Dashboard connection test failed: {e}")
        return False
    
    return True

def test_position_save_load_cycle():
    """Test complete save/load cycle for positions"""
    print("\n" + "="*60)
    print("🧪 Testing Position Save/Load Cycle")
    print("="*60)
    
    # Create a backup of current positions
    backup_file = "positions_backup.json"
    if os.path.exists("positions.json"):
        import shutil
        shutil.copy("positions.json", backup_file)
        print(f"📄 Created backup: {backup_file}")
    
    try:
        config = ShortCycleConfig()
        trader = ShortCycleTrader(config)
        
        # Clear existing positions
        trader.positions = []
        
        # Create a test position
        from traders.short_cycle_trader import ShortCyclePosition, PositionStatus, AISignal
        
        ai_signal = AISignal(
            symbol="TEST",
            action="BUY",
            confidence=0.75,
            time_horizon_days=1.5,
            entry_price=100.0,
            target_price=105.0,
            signal_timestamp=dt.datetime.now(),
            features_used={"test": True},
            risk_score=0.3
        )
        
        test_position = ShortCyclePosition(
            symbol="TEST",
            entry_date=dt.date.today(),
            exit_date=dt.date.today() + dt.timedelta(days=1),
            entry_price=100.0,
            position_size_shares=10,
            position_size_dollars=1000.0,
            stop_price=95.0,
            target_price=105.0,
            status=PositionStatus.ENTERED,
            ai_signal=ai_signal,
            max_risk_dollars=50.0
        )
        
        trader.positions.append(test_position)
        print(f"📊 Created test position: {test_position.symbol}")
        
        # Save positions
        trader._save_positions()
        print("✅ Positions saved")
        
        # Clear and reload
        trader.positions = []
        trader._load_positions()
        print(f"📊 Reloaded {len(trader.positions)} position(s)")
        
        # Verify the test position was loaded correctly
        if trader.positions and trader.positions[-1].symbol == "TEST":
            loaded_pos = trader.positions[-1]
            print(f"✅ Test position loaded correctly:")
            print(f"   Symbol: {loaded_pos.symbol}")
            print(f"   Status: {loaded_pos.status}")
            print(f"   Entry Price: ${loaded_pos.entry_price}")
            return True
        else:
            print("❌ Test position not found after reload")
            return False
            
    except Exception as e:
        print(f"❌ Save/load cycle test failed: {e}")
        return False
    
    finally:
        # Restore backup
        if os.path.exists(backup_file):
            import shutil
            shutil.copy(backup_file, "positions.json")
            os.remove(backup_file)
            print(f"📄 Restored original positions.json")

def main():
    """Run all position management tests"""
    print("🚀 Position Management Test Suite")
    print("=" * 60)
    
    tests = [
        ("Position Loading", test_position_loading),
        ("D+1 Exit Logic", test_d1_exit_logic),
        ("Dashboard Connection", test_dashboard_connection),
        ("Save/Load Cycle", test_position_save_load_cycle)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            print(f"\n🧪 Running: {test_name}")
            if test_func():
                print(f"✅ {test_name}: PASSED")
                passed += 1
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")
    
    print("\n" + "="*60)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    print("="*60)
    
    if passed == total:
        print("🎉 All tests passed!")
    else:
        print("⚠️  Some tests failed - check output above for details")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
#!/usr/bin/env python3
"""
PDT Protection Test - Verify same-day re-entry blocking
Created: November 11, 2025
Purpose: Test that bot correctly blocks same-day re-entry after exit (PDT violation prevention)
"""

import sys
import datetime as dt
import pytz
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

def test_pdt_protection():
    """
    Test the PDT protection fix:
    1. Simulate XOM exit at 9:46 AM
    2. Try to re-enter XOM at 10:02 AM (should be BLOCKED)
    3. Verify exit_timestamp is preserved across save/load
    """
    print("=" * 70)
    print("PDT PROTECTION TEST - Same-Day Re-Entry Blocking")
    print("=" * 70)
    
    import os
    import shutil
    
    from traders.short_cycle_trader import ShortCycleTrader, ShortCyclePosition, PositionStatus, AISignal
    from small_portfolio_config import SmallPortfolioConfig
    
    # Backup real positions.json and use test file
    test_positions_file = "positions_test_pdt.json"
    real_positions_file = "positions.json"
    backup_file = "positions.json.backup_pdt_test"
    
    if os.path.exists(real_positions_file):
        shutil.copy(real_positions_file, backup_file)
        print(f"✅ Backed up {real_positions_file} to {backup_file}")
    
    # Create minimal config
    config = SmallPortfolioConfig()
    config.cash_account_mode = False  # MARGIN ACCOUNT - PDT restricted
    config.enable_same_day_reentry = False  # NO same-day re-entry
    
    print("\n✅ Config: Margin account, PDT restricted (no same-day re-entry)")
    
    # Create trader instance (mock mode - no actual trading)
    trader = ShortCycleTrader(config)
    trader.positions = []  # Start with empty positions
    
    # Simulate XOM position that was exited today at 9:46 AM
    today = dt.date.today()
    exit_time = dt.datetime.now(pytz.UTC).replace(hour=9, minute=46, second=0, microsecond=0)
    
    print(f"\n📊 Simulating XOM exit at {exit_time.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    
    # Create an exited position
    signal = AISignal(
        symbol='XOM',
        action='BUY',
        confidence=0.5,
        time_horizon_days=1,
        entry_price=117.56,
        target_price=None,
        signal_timestamp=dt.datetime.now(pytz.UTC),
        features_used={}
    )
    
    position = ShortCyclePosition(
        symbol='XOM',
        entry_date=dt.date.today() - dt.timedelta(days=1),  # Entered yesterday (Nov 10)
        exit_date=today,
        entry_price=117.56,
        position_size_shares=2,
        position_size_dollars=235.12,
        stop_price=114.62,
        target_price=None,
        status=PositionStatus.EXITED,
        ai_signal=signal,
        max_risk_dollars=20.0
    )
    
    # CRITICAL: Set exit_timestamp to 9:46 AM today
    position.exit_timestamp = exit_time
    position.exit_price = 119.29
    position.exit_reason = "ZONE3_AFTERNOON_PROFIT"
    position.realized_pnl = 3.47
    
    # Add to trader's positions
    trader.positions.append(position)
    
    print(f"   Entry: {position.entry_date}")
    print(f"   Exit: {position.exit_date}")
    print(f"   Exit timestamp: {position.exit_timestamp}")
    print(f"   Status: {position.status.value}")
    
    # TEST 1: Check if PDT block works BEFORE saving/loading
    print("\n" + "=" * 70)
    print("TEST 1: PDT Block Before Save/Load")
    print("=" * 70)
    
    blocked = trader._has_same_day_activity('XOM')
    
    if blocked:
        print("✅ PASS - XOM re-entry correctly BLOCKED (exit_timestamp detected)")
    else:
        print("❌ FAIL - XOM re-entry NOT blocked (PDT protection failed!)")
        return False
    
    # TEST 2: Save and reload positions, verify exit_timestamp persists
    print("\n" + "=" * 70)
    print("TEST 2: Exit Timestamp Persistence After Save/Load")
    print("=" * 70)
    
    print("\n📝 Saving positions to JSON...")
    trader._save_positions()
    
    print("🔄 Clearing trader positions and reloading from JSON...")
    trader.positions = []
    trader._load_positions()
    
    # Check if position was loaded
    loaded_positions = [p for p in trader.positions if p.symbol == 'XOM']
    
    if not loaded_positions:
        print("❌ FAIL - XOM position not found after reload!")
        return False
    
    loaded_xom = loaded_positions[0]
    print(f"\n✅ XOM position reloaded:")
    print(f"   Status: {loaded_xom.status.value}")
    print(f"   Exit timestamp: {loaded_xom.exit_timestamp}")
    print(f"   Exit price: {loaded_xom.exit_price}")
    
    if not hasattr(loaded_xom, 'exit_timestamp') or loaded_xom.exit_timestamp is None:
        print("\n❌ FAIL - exit_timestamp was NOT preserved after save/load!")
        return False
    
    if loaded_xom.exit_timestamp.date() != today:
        print(f"\n❌ FAIL - exit_timestamp date mismatch: {loaded_xom.exit_timestamp.date()} != {today}")
        return False
    
    print("✅ PASS - exit_timestamp correctly preserved after save/load")
    
    # TEST 3: Check PDT block works AFTER loading
    print("\n" + "=" * 70)
    print("TEST 3: PDT Block After Save/Load")
    print("=" * 70)
    
    blocked_after_load = trader._has_same_day_activity('XOM')
    
    if blocked_after_load:
        print("✅ PASS - XOM re-entry correctly BLOCKED after reload (PDT protection working!)")
    else:
        print("❌ FAIL - XOM re-entry NOT blocked after reload (THIS WAS THE BUG!)")
        return False
    
    # TEST 4: Verify other symbols are NOT blocked
    print("\n" + "=" * 70)
    print("TEST 4: Other Symbols Not Blocked")
    print("=" * 70)
    
    blocked_amd = trader._has_same_day_activity('AMD')
    blocked_tsla = trader._has_same_day_activity('TSLA')
    
    if blocked_amd or blocked_tsla:
        print("❌ FAIL - Other symbols incorrectly blocked!")
        return False
    
    print("✅ PASS - AMD and TSLA not blocked (only XOM blocked)")
    
    # TEST 5: Verify entry_date today also blocks
    print("\n" + "=" * 70)
    print("TEST 5: Entry Today Also Blocks")
    print("=" * 70)
    
    # Add a position entered today
    signal2 = AISignal(
        symbol='UPS',
        action='BUY',
        confidence=0.5,
        time_horizon_days=1,
        entry_price=96.22,
        target_price=None,
        signal_timestamp=dt.datetime.now(pytz.UTC),
        features_used={}
    )
    
    position2 = ShortCyclePosition(
        symbol='UPS',
        entry_date=today,  # Entered TODAY
        exit_date=today + dt.timedelta(days=1),
        entry_price=96.22,
        position_size_shares=2,
        position_size_dollars=192.44,
        stop_price=93.81,
        target_price=None,
        status=PositionStatus.ENTERED,
        ai_signal=signal2,
        max_risk_dollars=20.0
    )
    
    trader.positions.append(position2)
    
    blocked_ups = trader._has_same_day_activity('UPS')
    
    if blocked_ups:
        print("✅ PASS - UPS entry today correctly blocks same-day re-entry")
    else:
        print("❌ FAIL - UPS entry today NOT blocked!")
        return False
    
    # Cleanup: Restore original positions.json
    if os.path.exists(backup_file):
        shutil.move(backup_file, real_positions_file)
        print(f"\n✅ Restored original {real_positions_file}")
    
    return True


if __name__ == "__main__":
    print("\n")
    print("🔬 Testing PDT Protection Fix")
    print("=" * 70)
    print("Bug: exit_timestamp was not saved/loaded, causing PDT protection to fail")
    print("Fix: Added exit_timestamp to _save_positions() and _load_positions()")
    print("=" * 70)
    
    try:
        success = test_pdt_protection()
        
        print("\n" + "=" * 70)
        print("FINAL RESULT")
        print("=" * 70)
        
        if success:
            print("\n🎉 ALL TESTS PASSED - PDT Protection Fixed!")
            print("\nWhat was fixed:")
            print("  1. exit_timestamp now saved to positions.json")
            print("  2. exit_timestamp restored when loading positions")
            print("  3. Same-day re-entry correctly blocked after exit")
            print("  4. PDT protection working across bot restarts")
            print("\nExpected behavior:")
            print("  - If XOM exited at 9:46 AM, cannot re-enter until next day")
            print("  - Prevents day trades (buy+sell same day)")
            print("  - Protects margin account from PDT violations")
            sys.exit(0)
        else:
            print("\n❌ TESTS FAILED - PDT Protection Still Broken!")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ TEST ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

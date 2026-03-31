#!/usr/bin/env python3
"""
Comprehensive Exit Strategy Testing Suite
==========================================

Tests ANY exit strategy with 50+ scenarios to ensure it's fully functional
"""

import datetime as dt
import sys
import os
from typing import List, Tuple

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from traders.short_cycle_trader import ShortCyclePosition, PositionStatus, AISignal

# Test result tracking
test_results = {
    'passed': 0,
    'failed': 0,
    'warnings': 0,
    'total': 0
}

def create_test_position(entry_date=None, exit_date=None, entry_price=100.0, entry_time=None):
    """Create a standard test position"""
    if entry_date is None:
        entry_date = dt.date(2025, 10, 13)
    if exit_date is None:
        exit_date = dt.date(2025, 10, 14)
    if entry_time is None:
        entry_time = dt.datetime(2025, 10, 13, 15, 45)
    
    ai_signal = AISignal(
        symbol="TEST",
        action="BUY",
        confidence=0.5,
        time_horizon_days=1.5,
        entry_price=entry_price
    )
    
    return ShortCyclePosition(
        symbol="TEST",
        entry_date=entry_date,
        exit_date=exit_date,
        entry_price=entry_price,
        position_size_shares=10,
        position_size_dollars=1000.0,
        stop_price=entry_price * 0.98,
        target_price=None,
        status=PositionStatus.ENTERED,
        ai_signal=ai_signal,
        entry_timestamp=entry_time,
        filled_at=entry_time
    )

def run_test(test_name: str, position: ShortCyclePosition, test_time: dt.datetime, 
             test_price: float, expected_exit: bool, expected_reason: str = None) -> bool:
    """Run a single test and return pass/fail"""
    global test_results
    test_results['total'] += 1
    
    should_exit, reason = position.should_smart_exit(
        current_date=test_time.date(),
        current_price=test_price,
        current_time=test_time
    )
    
    pnl_pct = (test_price - position.entry_price) / position.entry_price * 100
    
    # Check result
    passed = should_exit == expected_exit
    reason_match = True
    if expected_reason and reason != expected_reason:
        reason_match = False
    
    if passed:
        test_results['passed'] += 1
        status = "✅"
    else:
        test_results['failed'] += 1
        status = "❌"
    
    if not reason_match:
        test_results['warnings'] += 1
        status += " ⚠️"
    
    print(f"{status} {test_name}")
    print(f"   Time: {test_time.strftime('%I:%M %p')} | Price: ${test_price:.2f} ({pnl_pct:+.2f}%)")
    print(f"   Expected: Exit={expected_exit}", end="")
    if expected_reason:
        print(f" | Reason={expected_reason}", end="")
    print()
    print(f"   Got:      Exit={should_exit} | Reason={reason}")
    
    if not passed:
        print(f"   ❌ TEST FAILED: Expected {expected_exit}, got {should_exit}")
    elif not reason_match and expected_reason:
        print(f"   ⚠️  Reason mismatch (not critical)")
    
    print()
    
    return passed

def test_zone_1_morning():
    """Test Zone 1 (9:30-11:00 AM) logic"""
    print("\n" + "=" * 80)
    print("🌅 ZONE 1 TESTS: Morning (9:30-11:00 AM)")
    print("=" * 80)
    
    position = create_test_position()
    
    tests = [
        ("Morning: Up 0.5% - should wait", dt.datetime(2025, 10, 14, 9, 45), 100.5, False, None),
        ("Morning: Up 0.9% - should wait", dt.datetime(2025, 10, 14, 10, 0), 100.9, False, None),
        ("Morning: Up 1.0% - should wait (boundary)", dt.datetime(2025, 10, 14, 10, 15), 101.0, False, None),
        ("Morning: Up 1.1% - should exit", dt.datetime(2025, 10, 14, 10, 30), 101.1, True, "ZONE1_MORNING_PROFIT"),
        ("Morning: Up 2.0% - should exit", dt.datetime(2025, 10, 14, 10, 45), 102.0, True, "ZONE1_MORNING_PROFIT"),
        ("Morning: Down 0.5% - should wait", dt.datetime(2025, 10, 14, 9, 50), 99.5, False, None),
        ("Morning: Down 1.5% - should wait", dt.datetime(2025, 10, 14, 10, 20), 98.5, False, None),
        ("Morning: Down 2.5% - STOP LOSS", dt.datetime(2025, 10, 14, 10, 40), 97.5, True, "EMERGENCY_STOP_LOSS"),
    ]
    
    for test in tests:
        run_test(test[0], position, test[1], test[2], test[3], test[4] if len(test) > 4 else None)

def test_zone_2_midday():
    """Test Zone 2 (11:00 AM-2:00 PM) logic"""
    print("\n" + "=" * 80)
    print("☀️  ZONE 2 TESTS: Midday (11:00 AM-2:00 PM)")
    print("=" * 80)
    
    position = create_test_position()
    
    tests = [
        ("Midday: Up 0.3% - should wait", dt.datetime(2025, 10, 14, 11, 15), 100.3, False, None),
        ("Midday: Up 0.5% - should wait (boundary)", dt.datetime(2025, 10, 14, 11, 30), 100.5, False, None),
        ("Midday: Up 0.6% - should exit", dt.datetime(2025, 10, 14, 12, 0), 100.6, True, "ZONE2_MIDDAY_PROFIT"),
        ("Midday: Up 1.2% - should exit", dt.datetime(2025, 10, 14, 13, 0), 101.2, True, "ZONE2_MIDDAY_PROFIT"),
        ("Midday: Down 0.8% - should wait", dt.datetime(2025, 10, 14, 11, 45), 99.2, False, None),
        ("Midday: Down 2.1% - STOP LOSS", dt.datetime(2025, 10, 14, 13, 30), 97.9, True, "EMERGENCY_STOP_LOSS"),
        ("Midday: Up 3.5% - should exit big profit", dt.datetime(2025, 10, 14, 12, 30), 103.5, True, "ZONE2_MIDDAY_PROFIT"),
    ]
    
    for test in tests:
        run_test(test[0], position, test[1], test[2], test[3], test[4] if len(test) > 4 else None)

def test_zone_3_afternoon():
    """Test Zone 3 (2:00-3:30 PM) logic"""
    print("\n" + "=" * 80)
    print("🌤️  ZONE 3 TESTS: Afternoon (2:00-3:30 PM)")
    print("=" * 80)
    
    position = create_test_position()
    
    tests = [
        ("Afternoon: Up 0.1% - should exit (any profit)", dt.datetime(2025, 10, 14, 14, 15), 100.1, True, "ZONE3_AFTERNOON_PROFIT"),
        ("Afternoon: Up 0.5% - should exit", dt.datetime(2025, 10, 14, 14, 45), 100.5, True, "ZONE3_AFTERNOON_PROFIT"),
        ("Afternoon: Breakeven - should exit", dt.datetime(2025, 10, 14, 15, 0), 100.0, True, "ZONE3_AFTERNOON_PROFIT"),
        ("Afternoon: Down 0.5% - should wait", dt.datetime(2025, 10, 14, 14, 30), 99.5, False, None),
        ("Afternoon: Down 1.0% - should wait", dt.datetime(2025, 10, 14, 15, 15), 99.0, False, None),
        ("Afternoon: Down 1.6% - should exit (stop)", dt.datetime(2025, 10, 14, 15, 20), 98.4, True, "ZONE3_AFTERNOON_STOP"),
        ("Afternoon: Down 2.5% - EMERGENCY STOP", dt.datetime(2025, 10, 14, 14, 20), 97.5, True, "EMERGENCY_STOP_LOSS"),
    ]
    
    for test in tests:
        run_test(test[0], position, test[1], test[2], test[3], test[4] if len(test) > 4 else None)

def test_zone_4_late_day():
    """Test Zone 4 (3:30-3:45 PM) logic"""
    print("\n" + "=" * 80)
    print("🌆 ZONE 4 TESTS: Late Day (3:30-3:45 PM)")
    print("=" * 80)
    
    position = create_test_position()
    
    tests = [
        ("Late: Up 0.5% - should exit", dt.datetime(2025, 10, 14, 15, 35), 100.5, True, "ZONE4_LATE_EXIT"),
        ("Late: Breakeven - should exit", dt.datetime(2025, 10, 14, 15, 38), 100.0, True, "ZONE4_LATE_EXIT"),
        ("Late: Down 0.5% - should exit", dt.datetime(2025, 10, 14, 15, 40), 99.5, True, "ZONE4_LATE_EXIT"),
        ("Late: Down 0.9% - should exit", dt.datetime(2025, 10, 14, 15, 42), 99.1, True, "ZONE4_LATE_EXIT"),
        ("Late: Down 1.1% - should exit", dt.datetime(2025, 10, 14, 15, 44), 98.9, True, "ZONE4_LATE_EXIT"),
    ]
    
    for test in tests:
        run_test(test[0], position, test[1], test[2], test[3], test[4] if len(test) > 4 else None)

def test_zone_5_force_exit():
    """Test Zone 5 (3:45 PM+) logic"""
    print("\n" + "=" * 80)
    print("🌃 ZONE 5 TESTS: Final Minutes (3:45 PM+)")
    print("=" * 80)
    
    position = create_test_position()
    
    tests = [
        ("Final: Up 2% - FORCE EXIT", dt.datetime(2025, 10, 14, 15, 46), 102.0, True, "ZONE5_FORCE_EXIT"),
        ("Final: Up 0.1% - FORCE EXIT", dt.datetime(2025, 10, 14, 15, 50), 100.1, True, "ZONE5_FORCE_EXIT"),
        ("Final: Breakeven - FORCE EXIT", dt.datetime(2025, 10, 14, 15, 55), 100.0, True, "ZONE5_FORCE_EXIT"),
        ("Final: Down 1% - FORCE EXIT", dt.datetime(2025, 10, 14, 15, 58), 99.0, True, "ZONE5_FORCE_EXIT"),
        ("Final: Down 5% - FORCE EXIT", dt.datetime(2025, 10, 14, 15, 59), 95.0, True, "ZONE5_FORCE_EXIT"),
    ]
    
    for test in tests:
        run_test(test[0], position, test[1], test[2], test[3], test[4] if len(test) > 4 else None)

def test_emergency_rules():
    """Test emergency stop loss and profit take"""
    print("\n" + "=" * 80)
    print("🚨 EMERGENCY RULES TESTS")
    print("=" * 80)
    
    position = create_test_position()
    
    tests = [
        ("Emergency: Down 2.1% at 9:45 AM", dt.datetime(2025, 10, 14, 9, 45), 97.9, True, "EMERGENCY_STOP_LOSS"),
        ("Emergency: Down 3% at 12:00 PM", dt.datetime(2025, 10, 14, 12, 0), 97.0, True, "EMERGENCY_STOP_LOSS"),
        ("Emergency: Down 5% at 3:00 PM", dt.datetime(2025, 10, 14, 15, 0), 95.0, True, "EMERGENCY_STOP_LOSS"),
        ("Emergency: Up 3.1% at 10:00 AM", dt.datetime(2025, 10, 14, 10, 0), 103.1, True, "PROFIT_TAKE_3PCT"),
        ("Emergency: Up 5% at 2:00 PM", dt.datetime(2025, 10, 14, 14, 0), 105.0, True, "PROFIT_TAKE_3PCT"),
    ]
    
    for test in tests:
        run_test(test[0], position, test[1], test[2], test[3], test[4] if len(test) > 4 else None)

def test_friday_logic():
    """Test Friday weekend exit logic"""
    print("\n" + "=" * 80)
    print("🗓️  FRIDAY WEEKEND EXIT TESTS")
    print("=" * 80)
    
    # Create Friday position
    position = create_test_position(
        entry_date=dt.date(2025, 10, 16),  # Thursday
        exit_date=dt.date(2025, 10, 17),   # Friday
        entry_time=dt.datetime(2025, 10, 16, 15, 45)
    )
    
    tests = [
        ("Friday: Up 0.5% at 2:15 PM", dt.datetime(2025, 10, 17, 14, 15), 100.5, True, "FRIDAY_PROFIT_EXIT"),
        ("Friday: Up 0.2% at 3:00 PM", dt.datetime(2025, 10, 17, 15, 0), 100.2, True, "FRIDAY_PROFIT_EXIT"),
        ("Friday: Down 0.3% at 3:35 PM", dt.datetime(2025, 10, 17, 15, 35), 99.7, True, "FRIDAY_WEEKEND_EXIT"),
        ("Friday: Down 1% at 3:45 PM", dt.datetime(2025, 10, 17, 15, 45), 99.0, True, "FRIDAY_WEEKEND_EXIT"),
    ]
    
    for test in tests:
        run_test(test[0], position, test[1], test[2], test[3], test[4] if len(test) > 4 else None)

def test_d1_eligibility():
    """Test D+1 eligibility logic"""
    print("\n" + "=" * 80)
    print("📅 D+1 ELIGIBILITY TESTS (PDT Protection)")
    print("=" * 80)
    
    position = create_test_position(
        entry_time=dt.datetime(2025, 10, 13, 15, 45)
    )
    
    # Test same-day (should NOT be eligible)
    test_time = dt.datetime(2025, 10, 13, 16, 0)
    eligible = position.is_d1_eligible(test_time)
    test_results['total'] += 1
    if not eligible:
        test_results['passed'] += 1
        print(f"✅ Same-day exit blocked (PDT protection)")
        print(f"   Entry: {position.entry_timestamp}")
        print(f"   Test: {test_time}")
        print(f"   Eligible: {eligible} (correct - not same day)")
    else:
        test_results['failed'] += 1
        print(f"❌ FAILED: Same-day exit allowed (PDT violation!)")
        print(f"   Entry: {position.entry_timestamp}")
        print(f"   Test: {test_time}")
        print(f"   Eligible: {eligible} (WRONG - should be False)")
    print()
    
    # Test next-day (should be eligible)
    test_time = dt.datetime(2025, 10, 14, 9, 30)
    eligible = position.is_d1_eligible(test_time)
    test_results['total'] += 1
    if eligible:
        test_results['passed'] += 1
        print(f"✅ Next-day exit allowed")
        print(f"   Entry: {position.entry_timestamp}")
        print(f"   Test: {test_time}")
        print(f"   Eligible: {eligible} (correct)")
    else:
        test_results['failed'] += 1
        print(f"❌ FAILED: Next-day exit blocked")
        print(f"   Entry: {position.entry_timestamp}")
        print(f"   Test: {test_time}")
        print(f"   Eligible: {eligible} (WRONG - should be True)")
    print()

def test_edge_cases():
    """Test edge cases and boundary conditions"""
    print("\n" + "=" * 80)
    print("⚠️  EDGE CASE TESTS")
    print("=" * 80)
    
    position = create_test_position()
    
    tests = [
        ("Exact 1% at 10:00 AM (boundary)", dt.datetime(2025, 10, 14, 10, 0), 101.0, False, None),
        ("Exact 0.5% at 12:00 PM (boundary)", dt.datetime(2025, 10, 14, 12, 0), 100.5, False, None),
        ("Exact 0% at 2:30 PM (breakeven)", dt.datetime(2025, 10, 14, 14, 30), 100.0, True, "ZONE3_AFTERNOON_PROFIT"),
        ("Exact -1% at 3:40 PM (boundary)", dt.datetime(2025, 10, 14, 15, 40), 99.0, True, "ZONE4_LATE_EXIT"),
        ("Exact -2% (stop loss boundary)", dt.datetime(2025, 10, 14, 11, 0), 98.0, True, "EMERGENCY_STOP_LOSS"),
        ("Exact +3% (profit take boundary)", dt.datetime(2025, 10, 14, 11, 0), 103.0, True, "PROFIT_TAKE_3PCT"),
    ]
    
    for test in tests:
        run_test(test[0], position, test[1], test[2], test[3], test[4] if len(test) > 4 else None)

def print_test_summary():
    """Print final test summary"""
    print("\n" + "=" * 80)
    print("📊 TEST SUMMARY")
    print("=" * 80)
    
    total = test_results['total']
    passed = test_results['passed']
    failed = test_results['failed']
    warnings = test_results['warnings']
    
    pass_rate = (passed / total * 100) if total > 0 else 0
    
    print(f"\nTotal Tests:    {total}")
    print(f"Passed:         {passed} ✅")
    print(f"Failed:         {failed} ❌")
    print(f"Warnings:       {warnings} ⚠️")
    print(f"Pass Rate:      {pass_rate:.1f}%")
    
    print("\n" + "=" * 80)
    
    if failed == 0:
        print("✅ ALL TESTS PASSED - Strategy is fully functional!")
        print("=" * 80)
        return True
    else:
        print(f"❌ {failed} TESTS FAILED - Strategy needs fixes!")
        print("=" * 80)
        return False

def main():
    """Run all tests"""
    print("\n" + "█" * 80)
    print("█" + " " * 78 + "█")
    print("█" + "  🧪 COMPREHENSIVE EXIT STRATEGY TEST SUITE".center(78) + "█")
    print("█" + " " * 78 + "█")
    print("█" * 80)
    
    # Run all test suites
    test_zone_1_morning()
    test_zone_2_midday()
    test_zone_3_afternoon()
    test_zone_4_late_day()
    test_zone_5_force_exit()
    test_emergency_rules()
    test_friday_logic()
    test_d1_eligibility()
    test_edge_cases()
    
    # Print summary
    all_passed = print_test_summary()
    
    # Exit code
    sys.exit(0 if all_passed else 1)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Validate Exit Strategy Implementation
======================================

Tests the new exit zone logic with various scenarios
"""

import datetime as dt
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from traders.short_cycle_trader import ShortCyclePosition, PositionStatus, AISignal

def test_exit_zones():
    """Test the new exit zone logic"""
    
    print("\n" + "=" * 80)
    print("🧪 TESTING NEW EXIT ZONE STRATEGY")
    print("=" * 80)
    
    # Create a test position
    entry_date = dt.date(2025, 10, 13)
    exit_date = dt.date(2025, 10, 14)
    entry_price = 100.0
    
    ai_signal = AISignal(
        symbol="TEST",
        action="BUY",
        confidence=0.5,
        time_horizon_days=1.5,
        entry_price=entry_price
    )
    
    position = ShortCyclePosition(
        symbol="TEST",
        entry_date=entry_date,
        exit_date=exit_date,
        entry_price=entry_price,
        position_size_shares=10,
        position_size_dollars=1000.0,
        stop_price=98.0,
        target_price=None,
        status=PositionStatus.ENTERED,
        ai_signal=ai_signal,
        entry_timestamp=dt.datetime(2025, 10, 13, 15, 45),  # 3:45 PM yesterday
        filled_at=dt.datetime(2025, 10, 13, 15, 45, 23)
    )
    
    # Test scenarios
    scenarios = [
        # (time, price, expected_exit, zone)
        ("9:45 AM, up 0.8%", dt.datetime(2025, 10, 14, 9, 45), 100.8, False, "ZONE1: Need >1%"),
        ("10:00 AM, up 1.2%", dt.datetime(2025, 10, 14, 10, 0), 101.2, True, "ZONE1: >1% profit"),
        ("11:30 AM, up 0.6%", dt.datetime(2025, 10, 14, 11, 30), 100.6, True, "ZONE2: >0.5% profit"),
        ("2:30 PM, up 0.2%", dt.datetime(2025, 10, 14, 14, 30), 100.2, True, "ZONE3: Any profit"),
        ("2:30 PM, down 0.5%", dt.datetime(2025, 10, 14, 14, 30), 99.5, False, "ZONE3: Wait for better"),
        ("3:40 PM, down 0.8%", dt.datetime(2025, 10, 14, 15, 40), 99.2, True, "ZONE4: Not down >1%"),
        ("3:50 PM, down 2%", dt.datetime(2025, 10, 14, 15, 50), 98.0, True, "ZONE5: Force exit"),
        ("10:00 AM, down 2.5%", dt.datetime(2025, 10, 14, 10, 0), 97.5, True, "EMERGENCY: Stop loss"),
        ("11:00 AM, up 3.5%", dt.datetime(2025, 10, 14, 11, 0), 103.5, True, "EMERGENCY: Profit take"),
    ]
    
    print("\n📊 Exit Decision Tests:")
    print("-" * 80)
    
    for desc, test_time, test_price, expected_exit, expected_reason in scenarios:
        should_exit, reason = position.should_smart_exit(
            current_date=test_time.date(),
            current_price=test_price,
            current_time=test_time
        )
        
        pnl_pct = (test_price - entry_price) / entry_price * 100
        status = "✅" if should_exit == expected_exit else "❌"
        
        print(f"{status} {desc}")
        print(f"   Price: ${test_price:.2f} ({pnl_pct:+.2f}%)")
        print(f"   Exit: {should_exit} | Reason: {reason}")
        print(f"   Expected: {expected_exit} | {expected_reason}")
        print()
    
    # Test Friday logic
    print("\n🗓️  Friday Exit Tests:")
    print("-" * 80)
    
    friday_scenarios = [
        ("Friday 2:30 PM, up 0.3%", dt.datetime(2025, 10, 17, 14, 30), 100.3, True, "Friday afternoon profit"),
        ("Friday 3:40 PM, down 0.5%", dt.datetime(2025, 10, 17, 15, 40), 99.5, True, "Friday weekend exit"),
    ]
    
    for desc, test_time, test_price, expected_exit, expected_reason in friday_scenarios:
        should_exit, reason = position.should_smart_exit(
            current_date=test_time.date(),
            current_price=test_price,
            current_time=test_time
        )
        
        pnl_pct = (test_price - entry_price) / entry_price * 100
        status = "✅" if should_exit == expected_exit else "❌"
        
        print(f"{status} {desc}")
        print(f"   Price: ${test_price:.2f} ({pnl_pct:+.2f}%)")
        print(f"   Exit: {should_exit} | Reason: {reason}")
        print(f"   Expected: {expected_exit} | {expected_reason}")
        print()
    
    # Test D+1 eligibility
    print("\n📅 D+1 Eligibility Tests:")
    print("-" * 80)
    
    eligibility_tests = [
        ("Same day as entry", dt.datetime(2025, 10, 13, 16, 0), False, "Not eligible same day"),
        ("Next day morning", dt.datetime(2025, 10, 14, 9, 30), True, "Eligible next trading day"),
    ]
    
    for desc, test_time, expected_eligible, expected_reason in eligibility_tests:
        is_eligible = position.is_d1_eligible(test_time)
        status = "✅" if is_eligible == expected_eligible else "❌"
        
        print(f"{status} {desc}")
        print(f"   Time: {test_time}")
        print(f"   Eligible: {is_eligible}")
        print(f"   Expected: {expected_eligible} | {expected_reason}")
        print()
    
    print("=" * 80)
    print("✅ Exit Strategy Tests Complete")
    print("=" * 80)

if __name__ == "__main__":
    test_exit_zones()

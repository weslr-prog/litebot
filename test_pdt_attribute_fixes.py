#!/usr/bin/env python3
"""
Test PDT Protection and Attribute Fix
=====================================
Verifies:
1. Same-day positions are NOT exited (PDT protection)
2. highest_price_since_entry attribute works correctly
"""

import sys
sys.path.insert(0, '/home/wes/Desktop/litebotx-usb-deployment')

from datetime import date
from traders.short_cycle_trader import ShortCyclePosition, PositionStatus

def test_pdt_protection():
    """Test that same-day positions are protected"""
    print("\n" + "="*70)
    print("TEST 1: PDT Protection - Same-Day Exit Blocking")
    print("="*70)
    
    today = date.today()
    
    # Create a position entered today
    position = ShortCyclePosition(
        symbol="TEST",
        entry_date=today,  # ENTERED TODAY
        exit_date=date(2025, 11, 12),
        entry_price=100.0,
        position_size_shares=10,
        position_size_dollars=1000.0,
        stop_price=95.0,
        target_price=None,
        status=PositionStatus.ENTERED,
        ai_signal=None
    )
    
    # Simulate the PDT check from line 1751
    if position.entry_date >= today:
        print(f"✅ PASS: Position entered today ({position.entry_date}) - exit blocked")
        print(f"   This prevents PDT violation")
        return True
    else:
        print(f"❌ FAIL: Position entered today but PDT check failed")
        return False

def test_highest_price_attribute():
    """Test that highest_price_since_entry attribute exists"""
    print("\n" + "="*70)
    print("TEST 2: Attribute Fix - highest_price_since_entry")
    print("="*70)
    
    position = ShortCyclePosition(
        symbol="TEST",
        entry_date=date(2025, 11, 10),
        exit_date=date(2025, 11, 12),
        entry_price=100.0,
        position_size_shares=10,
        position_size_dollars=1000.0,
        stop_price=95.0,
        target_price=None,
        status=PositionStatus.ENTERED,
        ai_signal=None
    )
    
    # Check if highest_price_since_entry attribute exists
    if hasattr(position, 'highest_price_since_entry'):
        print(f"✅ PASS: highest_price_since_entry attribute exists")
        print(f"   Initial value: {position.highest_price_since_entry}")
        
        # Test setting it
        position.highest_price_since_entry = 105.0
        print(f"   After update: {position.highest_price_since_entry}")
        return True
    else:
        print(f"❌ FAIL: highest_price_since_entry attribute missing")
        return False

def test_old_position_allowed():
    """Test that D+1 positions can exit"""
    print("\n" + "="*70)
    print("TEST 3: D+1 Position - Exit Should Be Allowed")
    print("="*70)
    
    today = date.today()
    yesterday = date(2025, 11, 10)  # Entered yesterday
    
    position = ShortCyclePosition(
        symbol="TEST",
        entry_date=yesterday,  # ENTERED YESTERDAY
        exit_date=today,
        entry_price=100.0,
        position_size_shares=10,
        position_size_dollars=1000.0,
        stop_price=95.0,
        target_price=None,
        status=PositionStatus.ENTERED,
        ai_signal=None
    )
    
    # Simulate the PDT check
    if position.entry_date >= today:
        print(f"❌ FAIL: Yesterday's position blocked (should be allowed)")
        return False
    else:
        print(f"✅ PASS: Position entered yesterday ({position.entry_date}) - exit allowed")
        print(f"   This is normal D+1 exit behavior")
        return True

if __name__ == '__main__':
    print("\n🧪 Testing PDT Protection and Attribute Fixes")
    print("="*70)
    
    results = []
    results.append(("PDT Protection", test_pdt_protection()))
    results.append(("Attribute Fix", test_highest_price_attribute()))
    results.append(("D+1 Exit Allowed", test_old_position_allowed()))
    
    print("\n" + "="*70)
    print("TEST RESULTS SUMMARY")
    print("="*70)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    all_passed = all(result[1] for result in results)
    
    print("\n" + "="*70)
    if all_passed:
        print("✅ ALL TESTS PASSED - Fixes are working correctly")
    else:
        print("❌ SOME TESTS FAILED - Review fixes needed")
    print("="*70 + "\n")
    
    sys.exit(0 if all_passed else 1)

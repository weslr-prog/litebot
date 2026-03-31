#!/usr/bin/env python3
"""
Cash Account Day Trading Test Script
=====================================
Tests the new cash account mode features to ensure PDT blocks are removed
and same-day trading capabilities work correctly.

Run this BEFORE deploying to verify changes are working.

Author: LiteBotX Team
Date: October 31, 2025
"""

import sys
from pathlib import Path
from datetime import date, datetime, timedelta
import pytz

# Add project root
sys.path.insert(0, str(Path(__file__).parent))

from small_portfolio_config import SmallPortfolioConfig
from traders.short_cycle_trader import ShortCyclePosition, ShortCycleConfig, AISignal, PositionStatus
from settlement_tracker import SettlementTracker

print("=" * 80)
print("🧪 CASH ACCOUNT DAY TRADING - FEATURE TEST")
print("=" * 80)

# Test 1: Configuration Flags
print("\n" + "=" * 80)
print("TEST 1: Configuration Flags")
print("=" * 80)

config = SmallPortfolioConfig()

tests_passed = 0
tests_failed = 0

# Check cash account mode
if hasattr(config, 'cash_account_mode') and config.cash_account_mode == True:
    print("✅ cash_account_mode = True")
    tests_passed += 1
else:
    print("❌ cash_account_mode not found or not True")
    tests_failed += 1

# Check same-day exit
if hasattr(config, 'enable_same_day_exit') and config.enable_same_day_exit == True:
    print("✅ enable_same_day_exit = True")
    tests_passed += 1
else:
    print("❌ enable_same_day_exit not found or not True")
    tests_failed += 1

# Check same-day re-entry
if hasattr(config, 'enable_same_day_reentry') and config.enable_same_day_reentry == True:
    print("✅ enable_same_day_reentry = True")
    tests_passed += 1
else:
    print("❌ enable_same_day_reentry not found or not True")
    tests_failed += 1

# Check intraday scalping
if hasattr(config, 'enable_intraday_scalping') and config.enable_intraday_scalping == True:
    print("✅ enable_intraday_scalping = True")
    tests_passed += 1
else:
    print("❌ enable_intraday_scalping not found or not True")
    tests_failed += 1

# Check intraday parameters
if hasattr(config, 'intraday_take_profit'):
    print(f"✅ intraday_take_profit = {config.intraday_take_profit:.1%}")
    tests_passed += 1
else:
    print("❌ intraday_take_profit not found")
    tests_failed += 1

if hasattr(config, 'intraday_stop_loss'):
    print(f"✅ intraday_stop_loss = {config.intraday_stop_loss:.1%}")
    tests_passed += 1
else:
    print("❌ intraday_stop_loss not found")
    tests_failed += 1

if hasattr(config, 'intraday_max_hold_minutes'):
    print(f"✅ intraday_max_hold_minutes = {config.intraday_max_hold_minutes} min")
    tests_passed += 1
else:
    print("❌ intraday_max_hold_minutes not found")
    tests_failed += 1

# Check settlement tracking
if hasattr(config, 'enable_settlement_tracking'):
    print(f"✅ enable_settlement_tracking = {config.enable_settlement_tracking}")
    tests_passed += 1
else:
    print("❌ enable_settlement_tracking not found")
    tests_failed += 1

if hasattr(config, 'settlement_buffer_dollars'):
    print(f"✅ settlement_buffer_dollars = ${config.settlement_buffer_dollars:.2f}")
    tests_passed += 1
else:
    print("❌ settlement_buffer_dollars not found")
    tests_failed += 1

# Test 2: Same-Day Exit Capability
print("\n" + "=" * 80)
print("TEST 2: Same-Day Exit Capability")
print("=" * 80)

# Create a mock position entered today
today = datetime.now(pytz.UTC)
mock_signal = AISignal(
    symbol="TEST",
    confidence=0.8,
    action="BUY",
    time_horizon_days=1,
    entry_price=100.0,
    stop_price=95.0,
    target_price=110.0
)

position = ShortCyclePosition(
    symbol="TEST",
    entry_date=today.date(),
    exit_date=today.date() + timedelta(days=2),  # Extended to avoid "LATE" exits
    entry_price=100.0,
    position_size_shares=10,
    position_size_dollars=1000.0,
    stop_price=95.0,
    target_price=110.0,
    status=PositionStatus.ENTERED,
    ai_signal=mock_signal,
    entry_timestamp=today,
    filled_at=today
)

# Test with cash account mode
can_exit_cash = position.is_d1_eligible(today, cash_account_mode=True)
if can_exit_cash:
    print("✅ Cash account can exit same day")
    tests_passed += 1
else:
    print("❌ Cash account cannot exit same day (SHOULD BE ABLE TO!)")
    tests_failed += 1

# Test with margin account mode (should NOT be able to exit same day)
can_exit_margin = position.is_d1_eligible(today, cash_account_mode=False)
if not can_exit_margin:
    print("✅ Margin account correctly blocked from same-day exit")
    tests_passed += 1
else:
    print("❌ Margin account can exit same day (SHOULD BE BLOCKED!)")
    tests_failed += 1

# Test next day exit (should work for both)
tomorrow = today + timedelta(days=1)
can_exit_tomorrow_cash = position.is_d1_eligible(tomorrow, cash_account_mode=True)
can_exit_tomorrow_margin = position.is_d1_eligible(tomorrow, cash_account_mode=False)

if can_exit_tomorrow_cash and can_exit_tomorrow_margin:
    print("✅ Both account types can exit next day")
    tests_passed += 1
else:
    print("❌ Exit on D+1 not working correctly")
    tests_failed += 1

# Test 3: T+2 Settlement Tracking
print("\n" + "=" * 80)
print("TEST 3: T+2 Settlement Tracking")
print("=" * 80)

tracker = SettlementTracker(buffer_amount=50.0)

# Record a Monday sale
monday = date(2025, 11, 4)
settlement_record = tracker.record_sale(monday, 300.0, "AAPL")

if settlement_record.settlement_date == date(2025, 11, 6):  # Wednesday
    print(f"✅ Monday sale settles Wednesday (T+2): {settlement_record.settlement_date}")
    tests_passed += 1
else:
    print(f"❌ Settlement date calculation wrong: {settlement_record.settlement_date}")
    tests_failed += 1

# Check available cash on Monday
account_cash = 1000.0
available_monday = tracker.get_settled_cash(account_cash, monday)
expected_monday = account_cash - 300.0 - 50.0  # Total - Unsettled - Buffer

if abs(available_monday - expected_monday) < 0.01:
    print(f"✅ Available cash on Monday: ${available_monday:.2f} (correct)")
    tests_passed += 1
else:
    print(f"❌ Available cash wrong: ${available_monday:.2f}, expected ${expected_monday:.2f}")
    tests_failed += 1

# Check settlement on Wednesday
wednesday = date(2025, 11, 6)
newly_settled = tracker.update_settlements(wednesday)

if len(newly_settled) == 1 and newly_settled[0].symbol == "AAPL":
    print(f"✅ Settlement completed on Wednesday")
    tests_passed += 1
else:
    print(f"❌ Settlement not completed on Wednesday")
    tests_failed += 1

available_wednesday = tracker.get_settled_cash(account_cash, wednesday)
expected_wednesday = account_cash - 50.0  # Buffer only (funds settled)

if abs(available_wednesday - expected_wednesday) < 0.01:
    print(f"✅ Available cash on Wednesday: ${available_wednesday:.2f} (all settled)")
    tests_passed += 1
else:
    print(f"❌ Available cash wrong after settlement: ${available_wednesday:.2f}")
    tests_failed += 1

# Test violation risk detection
purchase_amount = 700.0
tracker.record_sale(monday, 300.0, "GOOGL")  # Add another unsettled
tracker.update_settlements(monday)  # Reset to Monday
is_risky, warning = tracker.check_violation_risk(purchase_amount, account_cash, monday)

if is_risky:
    print(f"✅ Violation risk detected for large purchase: {warning[:50]}...")
    tests_passed += 1
else:
    print(f"❌ Violation risk not detected (SHOULD WARNING!)")
    tests_failed += 1

# Test 4: Intraday Exit Logic
print("\n" + "=" * 80)
print("TEST 4: Intraday Exit Thresholds")
print("=" * 80)

# Use a non-Friday date for testing (Monday) and create position for that date
test_monday = datetime(2025, 11, 3, 10, 30, tzinfo=pytz.UTC)  # Monday 10:30 AM

# Create a fresh position for the test date
test_position = ShortCyclePosition(
    symbol="TEST2",
    entry_date=test_monday.date(),
    exit_date=test_monday.date() + timedelta(days=2),
    entry_price=100.0,
    position_size_shares=10,
    position_size_dollars=1000.0,
    stop_price=95.0,
    target_price=110.0,
    status=PositionStatus.ENTERED,
    ai_signal=mock_signal,
    entry_timestamp=test_monday,
    filled_at=test_monday
)

# Test profit-taking threshold
current_price_profit = 102.0  # +2% gain
should_exit, reason = test_position.should_smart_exit(
    test_monday.date(), 
    current_price_profit, 
    test_monday, 
    cash_account_mode=True
)

if should_exit and "PROFIT" in reason.upper():
    print(f"✅ Intraday profit exit triggered at +2%: {reason}")
    tests_passed += 1
else:
    print(f"❌ Profit exit not triggered at +2% (reason: {reason})")
    tests_failed += 1

# Test stop-loss threshold
current_price_loss = 98.0  # -2% loss
should_exit_loss, reason_loss = test_position.should_smart_exit(
    test_monday.date(),
    current_price_loss,
    test_monday,
    cash_account_mode=True
)

if should_exit_loss and "STOP" in reason_loss.upper():
    print(f"✅ Intraday stop-loss triggered at -2%: {reason_loss}")
    tests_passed += 1
else:
    print(f"❌ Stop-loss not triggered at -2% (reason: {reason_loss})")
    tests_failed += 1

# Test 5: Summary
print("\n" + "=" * 80)
print("TEST SUMMARY")
print("=" * 80)

total_tests = tests_passed + tests_failed
pass_rate = (tests_passed / total_tests * 100) if total_tests > 0 else 0

print(f"\n📊 Results:")
print(f"   Total Tests: {total_tests}")
print(f"   Passed: {tests_passed} ✅")
print(f"   Failed: {tests_failed} ❌")
print(f"   Pass Rate: {pass_rate:.1f}%")

if tests_failed == 0:
    print("\n🎉 ALL TESTS PASSED!")
    print("✅ Cash account day trading features are working correctly.")
    print("✅ Ready to proceed with paper trading tests.")
    sys.exit(0)
else:
    print(f"\n⚠️  {tests_failed} TEST(S) FAILED")
    print("❌ Review failed tests above before proceeding.")
    print("❌ Fix issues before deploying to paper trading.")
    sys.exit(1)

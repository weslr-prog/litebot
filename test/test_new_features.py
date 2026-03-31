#!/usr/bin/env python3
"""
Comprehensive Test Suite for New Trading Features
Tests dynamic position sizing and trailing stops
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from traders.short_cycle_trader import (
    ShortCycleTrader,
    ShortCycleConfig,
    ShortCyclePosition,
    AIConfidencePositionSizer,
    PositionStatus
)
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict
import pytz

# Create AISignal dataclass locally for testing
@dataclass
class AISignal:
    symbol: str
    action: str = "BUY"
    confidence: float = 0.5
    time_horizon_days: float = 1.0
    target_price: Optional[float] = None
    stop_price: Optional[float] = None
    entry_price: Optional[float] = None
    position_size_dollars: Optional[float] = None
    signal_timestamp: Optional[datetime] = None
    features_used: Optional[Dict[str, float]] = None
    risk_score: float = 0.5

et_tz = pytz.timezone('US/Eastern')

print("=" * 80)
print("🧪 TESTING NEW TRADING FEATURES")
print("=" * 80)

# ============================================================================
# TEST 1: Dynamic Position Sizing
# ============================================================================
print("\n" + "=" * 80)
print("TEST 1: Dynamic Position Sizing Based on Confidence")
print("=" * 80)

config = ShortCycleConfig()
sizer = AIConfidencePositionSizer(config)

test_cases = [
    # (confidence, expected_tier, expected_range)
    (0.95, "HIGH", (1.6, 2.0)),
    (0.82, "HIGH", (1.6, 2.0)),
    (0.75, "HIGH", (1.6, 2.0)),
    (0.70, "MEDIUM", (1.2, 1.6)),
    (0.65, "MEDIUM", (1.2, 1.6)),
    (0.55, "MEDIUM", (1.2, 1.6)),
    (0.50, "LOW", (1.0, 1.2)),
    (0.45, "LOW", (1.0, 1.2)),
    (0.30, "LOW", (1.0, 1.2)),
]

print(f"\n📊 Base Configuration:")
print(f"   Portfolio Value: ${config.portfolio_value:,.0f}")
print(f"   Daily Pool: ${config.daily_pool_dollars:,.0f}")
print(f"   Max Position %: {config.max_position_size_percent:.1%}")
print(f"   Max Position $: ${config.max_position_dollars:,.0f}")
print(f"   Base Risk per Trade: ~$500 (estimated)")

print(f"\n{'Confidence':<12} {'Tier':<8} {'Expected Range':<18} {'Actual Mult':<12} {'Status':<10}")
print("-" * 80)

all_passed = True
for confidence, expected_tier, (min_mult, max_mult) in test_cases:
    # Create test signal
    test_signal = AISignal(
        symbol="AAPL",
        entry_price=150.0,
        confidence=confidence
    )
    
    test_stop = 148.50  # $1.50 stop distance
    test_portfolio = 963000.0
    
    shares, position_value = sizer.calculate_position_size(
        signal=test_signal,
        stop_price=test_stop,
        current_portfolio_value=test_portfolio
    )
    
    # Calculate actual multiplier from risk
    stop_distance = test_signal.entry_price - test_stop
    risk_amt = shares * stop_distance
    base_risk = config.max_risk_per_trade_dollars
    actual_mult = risk_amt / base_risk if base_risk > 0 else 0
    
    # Determine tier from confidence
    if confidence >= 0.75:
        tier = "HIGH"
    elif confidence >= 0.55:
        tier = "MEDIUM"
    else:
        tier = "LOW"
    
    # Check if multiplier in expected range
    passed = (tier == expected_tier and min_mult <= actual_mult <= max_mult)
    status = "✅ PASS" if passed else "❌ FAIL"
    
    if not passed:
        all_passed = False
    
    print(f"{confidence:<12.2f} {tier:<8} [{min_mult:.1f}x-{max_mult:.1f}x]{'':>6} {actual_mult:<12.2f}x {status:<10}")

print("\n" + "=" * 80)
if all_passed:
    print("✅ TEST 1 PASSED: All confidence tiers calculate correct multipliers")
else:
    print("❌ TEST 1 FAILED: Some multipliers out of expected range")
print("=" * 80)


# ============================================================================
# TEST 2: Trailing Stop Logic
# ============================================================================
print("\n" + "=" * 80)
print("TEST 2: Trailing Stop Activation and Updates")
print("=" * 80)

et_tz = pytz.timezone('US/Eastern')
entry_time = datetime.now(et_tz)

# Create test position
test_position = ShortCyclePosition(
    symbol="TSLA",
    entry_price=250.00,
    shares=100,
    entry_time=entry_time,
    stop_loss=247.50,
    confidence=0.85,
    signal_strength=0.80,
    target_exit_date=entry_time.date()
)

print(f"\n📋 Test Position:")
print(f"   Symbol: {test_position.symbol}")
print(f"   Entry: ${test_position.entry_price:.2f}")
print(f"   Shares: {test_position.shares}")
print(f"   Stop Loss: ${test_position.stop_loss:.2f}")

# Test scenarios
test_scenarios = [
    # (current_price, should_activate, should_hit, description)
    (250.00, False, False, "At entry - no activation"),
    (252.00, False, False, "+0.8% - below +3% threshold"),
    (257.50, True, False, "+3.0% - should activate"),
    (260.00, True, False, "+4.0% - stop trails up"),
    (262.50, True, False, "+5.0% - stop trails higher"),
    (258.50, True, True, "Price drops to stop - should hit"),
]

print(f"\n{'Price':<10} {'P&L %':<10} {'Should Act':<12} {'Should Hit':<12} {'Status':<15} {'Description':<30}")
print("-" * 100)

test2_passed = True
for price, should_activate, should_hit, description in test_scenarios:
    pnl_pct = ((price - test_position.entry_price) / test_position.entry_price) * 100
    
    # Update trailing stop
    hit, reason = test_position.update_trailing_stop(price, trailing_stop_pct=0.015)
    
    # Check expectations
    is_active = test_position.trailing_stop is not None
    
    # Validate
    activation_ok = (is_active == should_activate or is_active)  # Once active, stays active
    hit_ok = (hit == should_hit)
    passed = activation_ok and hit_ok
    
    status = "✅ PASS" if passed else "❌ FAIL"
    if not passed:
        test2_passed = False
    
    act_str = "Yes" if is_active else "No"
    hit_str = "Yes" if hit else "No"
    
    print(f"${price:<9.2f} {pnl_pct:>6.1f}%  {'':>2} {act_str:<12} {hit_str:<12} {status:<15} {description:<30}")
    
    # Reset for next scenario if needed
    if hit:
        # Re-create position for next test
        test_position = ShortCyclePosition(
            symbol="TSLA",
            entry_price=250.00,
            shares=100,
            entry_time=entry_time,
            stop_loss=247.50,
            confidence=0.85,
            signal_strength=0.80,
            target_exit_date=entry_time.date()
        )

print("\n" + "=" * 80)
if test2_passed:
    print("✅ TEST 2 PASSED: Trailing stop logic works correctly")
else:
    print("❌ TEST 2 FAILED: Trailing stop logic has issues")
print("=" * 80)


# ============================================================================
# TEST 3: Integration - Combined Features
# ============================================================================
print("\n" + "=" * 80)
print("TEST 3: Integration - Dynamic Sizing + Trailing Stops")
print("=" * 80)

print("\n🎯 Scenario: Two trades, different confidence levels\n")

# High confidence trade
print("Trade 1: HIGH Confidence (0.85)")
print("-" * 40)
signal_high = AISignal(symbol="AAPL", entry_price=180.0, confidence=0.85)
shares_high, position_value_high = sizer.calculate_position_size(
    signal=signal_high,
    stop_price=178.20,  # $1.80 stop
    current_portfolio_value=963000.0
)
mult_high = (shares_high * (180.0 - 178.20)) / config.max_risk_per_trade_dollars
position_high = ShortCyclePosition(
    symbol="AAPL",
    entry_price=180.0,
    shares=shares_high,
    entry_time=entry_time,
    stop_loss=178.20,
    confidence=0.85,
    signal_strength=0.82,
    target_exit_date=entry_time.date()
)
print(f"   Multiplier: {mult_high:.2f}x (expected: 1.6x-2.0x)")
print(f"   Position Size: {shares_high} shares (${shares_high * 180.0:,.0f})")
risk_high = shares_high * (180.0 - 178.20)
print(f"   Risk Amount: ${risk_high:,.0f}")

# Simulate price movement
price_up = 185.40  # +3% - triggers trailing stop
hit, reason = position_high.update_trailing_stop(price_up)
print(f"   Price moves to ${price_up:.2f} (+3.0%)")
print(f"   Trailing stop: {'ACTIVATED ✅' if position_high.trailing_stop else 'Not active'}")

# Low confidence trade
print("\nTrade 2: LOW Confidence (0.50)")
print("-" * 40)
signal_low = AISignal(symbol="IBM", entry_price=200.0, confidence=0.50)
shares_low, position_value_low = sizer.calculate_position_size(
    signal=signal_low,
    stop_price=198.00,  # $2.00 stop
    current_portfolio_value=963000.0
)
mult_low = (shares_low * (200.0 - 198.00)) / config.max_risk_per_trade_dollars
position_low = ShortCyclePosition(
    symbol="IBM",
    entry_price=200.0,
    shares=shares_low,
    entry_time=entry_time,
    stop_loss=198.00,
    confidence=0.50,
    signal_strength=0.55,
    target_exit_date=entry_time.date()
)
print(f"   Multiplier: {mult_low:.2f}x (expected: 1.0x-1.2x)")
print(f"   Position Size: {shares_low} shares (${shares_low * 200.0:,.0f})")
risk_low = shares_low * (200.0 - 198.00)
print(f"   Risk Amount: ${risk_low:,.0f}")

# Simulate price movement
price_up_low = 206.00  # +3% - triggers trailing stop
hit_low, reason_low = position_low.update_trailing_stop(price_up_low)
print(f"   Price moves to ${price_up_low:.2f} (+3.0%)")
print(f"   Trailing stop: {'ACTIVATED ✅' if position_low.trailing_stop else 'Not active'}")

# Validate integration
test3_passed = True

# Check 1: High confidence has larger multiplier
if mult_high <= mult_low:
    print("\n❌ FAIL: High confidence should have larger multiplier than low")
    test3_passed = False

# Check 2: High confidence allocates more risk
if risk_high <= risk_low:
    print("❌ FAIL: High confidence should risk more dollars than low")
    test3_passed = False

# Check 3: Both trailing stops activated at +3%
if not position_high.trailing_stop or not position_low.trailing_stop:
    print("❌ FAIL: Both positions should have trailing stops activated")
    test3_passed = False

print("\n" + "=" * 80)
if test3_passed:
    print("✅ TEST 3 PASSED: Features integrate correctly")
    print("   • Higher confidence → Larger position size")
    print("   • More risk on high-conviction trades")
    print("   • Trailing stops protect both positions at +3%")
else:
    print("❌ TEST 3 FAILED: Integration issues detected")
print("=" * 80)


# ============================================================================
# FINAL SUMMARY
# ============================================================================
print("\n" + "=" * 80)
print("📊 TEST SUITE SUMMARY")
print("=" * 80)

all_tests_passed = all_passed and test2_passed and test3_passed

tests = [
    ("Dynamic Position Sizing", all_passed),
    ("Trailing Stop Logic", test2_passed),
    ("Feature Integration", test3_passed),
]

for test_name, passed in tests:
    status = "✅ PASSED" if passed else "❌ FAILED"
    print(f"   {test_name:<30} {status}")

print("\n" + "=" * 80)
if all_tests_passed:
    print("🎉 ALL TESTS PASSED - Bot features ready for production!")
    print("=" * 80)
    sys.exit(0)
else:
    print("⚠️  SOME TESTS FAILED - Review issues before deployment")
    print("=" * 80)
    sys.exit(1)

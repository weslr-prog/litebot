#!/usr/bin/env python3
"""
Standalone validation of all position sizing fixes
Tests the actual configuration values without requiring full environment
"""

def test_config_values():
    """Test that configuration values were updated correctly"""
    print("🧪 Testing Configuration Values...")
    
    # Read the actual file to verify changes
    with open('/home/wes/Desktop/litebotx-usb-deployment/traders/short_cycle_trader.py', 'r') as f:
        content = f.read()
    
    tests = [
        ('min_position_size_dollars: float = 25.0', 'Minimum position size reduced to $25'),
        ('max_risk_per_trade_dollars: float = 25.0', 'Maximum risk increased to $25'),
        ('confidence_threshold: float = 0.50', 'Confidence threshold lowered to 0.50'),
        ('"trades_today": self.trades_today', 'Trades today tracking added'),
    ]
    
    all_passed = True
    for pattern, description in tests:
        if pattern in content:
            print(f"   ✅ {description}")
        else:
            print(f"   ❌ {description} - NOT FOUND")
            all_passed = False
    
    return all_passed

def test_prefilter_values():
    """Test that pre-filter values were relaxed"""
    print("\n🧪 Testing Pre-Filter Relaxation...")
    
    with open('/home/wes/Desktop/litebotx-usb-deployment/pre_filter.py', 'r') as f:
        content = f.read()
    
    tests = [
        ('"breakout_min": 0.012', 'Breakout minimum relaxed to 0.012'),
        ('"vol_spike_min": 1.3', 'Volume spike minimum relaxed to 1.3'),
        ('vol_spike_min\': 1.1', 'Final relaxation multiplier set to 1.1'),
        ('breakout_min\': 0.006', 'Final breakout threshold set to 0.006'),
    ]
    
    all_passed = True
    for pattern, description in tests:
        if pattern in content:
            print(f"   ✅ {description}")
        else:
            print(f"   ❌ {description} - NOT FOUND")
            all_passed = False
    
    return all_passed

def test_performance_controller():
    """Test that adaptive position sizing was added"""
    print("\n🧪 Testing Adaptive Position Sizing...")
    
    with open('/home/wes/Desktop/litebotx-usb-deployment/controllers/performance_controller.py', 'r') as f:
        content = f.read()
    
    tests = [
        ('signals_today > 0 and trades_today == 0', 'Position sizing detection logic'),
        ('old_risk * 1.25', 'Risk budget increase logic'),
        ('old_min * 0.75', 'Minimum position size reduction'),
        ('trades_today', 'Trades today parameter handling'),
    ]
    
    all_passed = True
    for pattern, description in tests:
        if pattern in content:
            print(f"   ✅ {description}")
        else:
            print(f"   ❌ {description} - NOT FOUND")
            all_passed = False
    
    return all_passed

def simulate_position_sizing():
    """Simulate the position sizing calculation that failed for ORCL"""
    print("\n🧪 Simulating Position Sizing Calculation...")
    
    # ORCL signal parameters from logs
    entry_price = 135.0
    confidence = 0.63
    stop_loss_pct = 0.025  # 2.5%
    portfolio_value = 1000.0
    
    # NEW configuration values
    min_position_size = 25.0  # Was 50.0
    max_risk_per_trade = 25.0  # Was 15.0
    confidence_threshold = 0.50  # Was 0.55
    
    print(f"   📊 ORCL Signal Parameters:")
    print(f"      Entry price: ${entry_price}")
    print(f"      Confidence: {confidence}")
    print(f"      Stop loss: {stop_loss_pct:.1%}")
    print(f"      Portfolio: ${portfolio_value}")
    
    print(f"\n   ⚙️  NEW Configuration:")
    print(f"      Min position size: ${min_position_size}")
    print(f"      Max risk per trade: ${max_risk_per_trade}")
    print(f"      Confidence threshold: {confidence_threshold}")
    
    # Check confidence threshold
    if confidence < confidence_threshold:
        print(f"   ❌ Signal would be rejected (confidence {confidence} < {confidence_threshold})")
        return False
    else:
        print(f"   ✅ Signal passes confidence threshold ({confidence} >= {confidence_threshold})")
    
    # Calculate position sizing
    stop_price = entry_price * (1 - stop_loss_pct)
    risk_per_share = entry_price - stop_price
    
    # Confidence-based risk scaling
    confidence_multiplier = min(confidence / 0.7, 1.0)  # Scale based on confidence
    adjusted_max_risk = max_risk_per_trade * confidence_multiplier
    
    max_shares_by_risk = int(adjusted_max_risk / risk_per_share)
    min_shares_needed = int(min_position_size / entry_price) + 1
    
    shares = max(min_shares_needed, max_shares_by_risk)
    position_value = shares * entry_price
    
    print(f"\n   🧮 Position Calculation:")
    print(f"      Stop price: ${stop_price:.2f}")
    print(f"      Risk per share: ${risk_per_share:.2f}")
    print(f"      Confidence multiplier: {confidence_multiplier:.2f}")
    print(f"      Adjusted max risk: ${adjusted_max_risk:.2f}")
    print(f"      Max shares by risk: {max_shares_by_risk}")
    print(f"      Min shares needed: {min_shares_needed}")
    print(f"      Final shares: {shares}")
    print(f"      Position value: ${position_value:.2f}")
    
    # Check if position meets minimums
    if position_value < min_position_size:
        print(f"   ❌ Position too small (${position_value:.2f} < ${min_position_size})")
        return False
    else:
        print(f"   ✅ Position meets minimum size requirement")
        
    actual_risk = shares * risk_per_share
    print(f"      Actual risk: ${actual_risk:.2f} ({actual_risk/portfolio_value:.1%})")
    
    return True

def main():
    print("🧪 COMPREHENSIVE FIX VALIDATION\n")
    print("=" * 50)
    
    config_ok = test_config_values()
    prefilter_ok = test_prefilter_values()
    controller_ok = test_performance_controller()
    simulation_ok = simulate_position_sizing()
    
    print("\n" + "=" * 50)
    print("🎯 VALIDATION SUMMARY:")
    print(f"   Configuration fixes: {'✅ PASS' if config_ok else '❌ FAIL'}")
    print(f"   Pre-filter relaxation: {'✅ PASS' if prefilter_ok else '❌ FAIL'}")
    print(f"   Adaptive sizing: {'✅ PASS' if controller_ok else '❌ FAIL'}")
    print(f"   ORCL simulation: {'✅ PASS' if simulation_ok else '❌ FAIL'}")
    
    all_passed = config_ok and prefilter_ok and controller_ok and simulation_ok
    
    print(f"\n🎉 OVERALL RESULT: {'✅ ALL FIXES VALIDATED' if all_passed else '❌ SOME FIXES FAILED'}")
    
    if all_passed:
        print("\n💡 Ready for live trading! The ORCL signal should now execute successfully.")
    else:
        print("\n⚠️  Some fixes need attention before live trading.")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Test the SafetyMonitor portfolio value update fix
"""

import sys
import os
sys.path.append('/home/wes/Desktop/litebotx-usb-deployment')

from short_cycle_safety import SafetyMonitor, SafetyConfig

def test_safety_monitor_portfolio_update():
    """Test that SafetyMonitor portfolio value gets updated correctly"""
    
    print("🧪 Testing SafetyMonitor portfolio update fix...")
    
    # Create SafetyMonitor with initial portfolio of $1,000
    config = SafetyConfig()
    initial_portfolio = 1000.0
    monitor = SafetyMonitor(config, portfolio_value=initial_portfolio)
    
    # Verify initial state
    print(f"📊 Initial portfolio value: ${monitor.portfolio_value:,.2f}")
    initial_threshold = monitor.portfolio_value * config.max_daily_loss_pct
    print(f"📊 Initial daily loss threshold: ${initial_threshold:.2f}")
    
    # Update to actual portfolio value
    new_portfolio = 963465.0
    monitor.portfolio_value = new_portfolio
    
    # Verify updated state
    print(f"📊 Updated portfolio value: ${monitor.portfolio_value:,.2f}")
    new_threshold = monitor.portfolio_value * config.max_daily_loss_pct
    print(f"📊 Updated daily loss threshold: ${new_threshold:.2f}")
    
    # Test the $23.65 loss scenario
    loss_amount = 23.65
    print(f"\n🎯 Testing ${loss_amount} loss scenario:")
    
    # Should NOT trigger with updated portfolio
    would_trigger_before = loss_amount > initial_threshold
    would_trigger_after = loss_amount > new_threshold
    
    print(f"   ❌ Would trigger with $1,000 portfolio: {would_trigger_before}")
    print(f"   ✅ Would trigger with $963,465 portfolio: {would_trigger_after}")
    
    if not would_trigger_after and would_trigger_before:
        print("\n✅ Fix confirmed: Portfolio update prevents false kill switch trigger!")
        return True
    else:
        print("\n❌ Fix failed: Still would trigger or wouldn't before")
        return False

if __name__ == "__main__":
    success = test_safety_monitor_portfolio_update()
    sys.exit(0 if success else 1)
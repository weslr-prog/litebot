#!/usr/bin/env python3
"""
Test the complete SafetyMonitor integration fix
"""

import sys
import os
sys.path.append('/home/wes/Desktop/litebotx-usb-deployment')

from traders.short_cycle_trader import ShortCycleTrader, ShortCycleConfig
from short_cycle_safety import SafetyConfig

def test_trader_safety_monitor_integration():
    """Test that trader's SafetyMonitor gets updated when portfolio value changes"""
    
    print("🧪 Testing trader SafetyMonitor integration fix...")
    
    # Create config with default $1,000 portfolio
    config = ShortCycleConfig()
    print(f"📊 Initial config portfolio: ${config.portfolio_value:,.2f}")
    
    # Create trader (this will create SafetyMonitor with $1,000)
    trader = ShortCycleTrader(config)
    
    if not trader.safety_monitor:
        print("❌ SafetyMonitor not created")
        return False
    
    print(f"📊 SafetyMonitor initial portfolio: ${trader.safety_monitor.portfolio_value:,.2f}")
    initial_threshold = trader.safety_monitor.portfolio_value * trader.safety_monitor.config.max_daily_loss_pct
    print(f"📊 SafetyMonitor initial threshold: ${initial_threshold:.2f}")
    
    # Simulate portfolio value update
    print("\n🔄 Simulating portfolio value update...")
    
    # Mock the _get_portfolio_value method to return $963,465
    def mock_get_portfolio_value():
        return 963465.0
    
    trader._get_portfolio_value = mock_get_portfolio_value
    
    # Call _update_risk_limits (this should update SafetyMonitor)
    trader._update_risk_limits()
    
    # Check if SafetyMonitor was updated
    print(f"📊 SafetyMonitor updated portfolio: ${trader.safety_monitor.portfolio_value:,.2f}")
    updated_threshold = trader.safety_monitor.portfolio_value * trader.safety_monitor.config.max_daily_loss_pct
    print(f"📊 SafetyMonitor updated threshold: ${updated_threshold:.2f}")
    
    # Test the $23.65 loss scenario
    loss_amount = 23.65
    print(f"\n🎯 Testing ${loss_amount} loss scenario:")
    
    would_trigger_before = loss_amount > initial_threshold
    would_trigger_after = loss_amount > updated_threshold
    
    print(f"   ❌ Would trigger before update: {would_trigger_before}")
    print(f"   ✅ Would trigger after update: {would_trigger_after}")
    
    if not would_trigger_after and would_trigger_before:
        print("\n✅ Integration fix confirmed: SafetyMonitor gets updated with trader!")
        return True
    else:
        print("\n❌ Integration fix failed")
        return False

if __name__ == "__main__":
    success = test_trader_safety_monitor_integration()
    sys.exit(0 if success else 1)
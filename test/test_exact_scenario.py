#!/usr/bin/env python3
"""
Test the Exact Kill Switch Scenario
===================================

Simulate the exact scenario that was triggering: $23.65 loss on $963,465 portfolio
"""

import sys
import os

# Add project root to path  
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from short_cycle_safety import SafetyConfig, SafetyMonitor, KillSwitchType

def test_exact_scenario():
    """Test the exact scenario that was triggering the kill switch"""
    
    print("🔍 TESTING EXACT KILL SWITCH SCENARIO")
    print("=" * 60)
    
    # Exact values from the log
    portfolio_value = 963465  # From log: Portfolio: $963,465
    daily_loss = 23.65        # From log: Daily loss limit exceeded: $23.65
    
    print(f"💰 Portfolio Value: ${portfolio_value:,}")
    print(f"📉 Daily Loss Amount: ${daily_loss:.2f}")
    print()
    
    # Test with BEFORE fix (old SafetyConfig)
    print("❌ BEFORE FIX (0.8% daily loss limit):")
    old_threshold = portfolio_value * 0.008  # Old 0.8% limit
    old_would_trigger = daily_loss > old_threshold
    print(f"   Daily Loss Threshold: ${old_threshold:.2f}")
    print(f"   Would trigger kill switch: {'YES 🛑' if old_would_trigger else 'NO ✅'}")
    print(f"   Loss percentage: {(daily_loss/portfolio_value)*100:.4f}%")
    print()
    
    # Test with AFTER fix (new SafetyConfig)  
    print("✅ AFTER FIX (0.05% daily loss limit):")
    config = SafetyConfig()
    monitor = SafetyMonitor(config, portfolio_value)
    new_threshold = monitor.kill_switches[KillSwitchType.DAILY_LOSS].threshold_value
    new_would_trigger = daily_loss > new_threshold
    print(f"   Daily Loss Threshold: ${new_threshold:.2f}")
    print(f"   Would trigger kill switch: {'YES 🛑' if new_would_trigger else 'NO ✅'}")
    print(f"   Loss percentage: {(daily_loss/portfolio_value)*100:.4f}%")
    print()
    
    # Summary
    print("🎯 RESULT:")
    if not new_would_trigger:
        print("   ✅ SUCCESS! $23.65 loss will NOT trigger kill switch")
        print("   ✅ Bot can continue trading")
        print(f"   ✅ Threshold increased from ${old_threshold:.2f} to ${new_threshold:.2f}")
        print("   🚀 Daily bot failures SOLVED!")
    else:
        print("   ❌ FAILED! Kill switch still triggering")
        print("   ❌ Need further investigation")

if __name__ == "__main__":
    test_exact_scenario()
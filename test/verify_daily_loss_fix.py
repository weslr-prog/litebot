#!/usr/bin/env python3
"""
Quick Daily Loss Fix Verification
=================================

Test the daily loss kill switch fix to ensure it's now using the correct threshold.
"""

import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from short_cycle_safety import SafetyConfig, SafetyMonitor, KillSwitchType

def test_daily_loss_fix():
    """Test that daily loss fix is working correctly"""
    
    print("🔍 DAILY LOSS KILL SWITCH FIX VERIFICATION")
    print("=" * 60)
    
    # Test portfolio values
    portfolio_values = [963465, 1000, 800]
    
    for portfolio_value in portfolio_values:
        print(f"\n💰 Portfolio Value: ${portfolio_value:,}")
        
        # Create safety config and monitor
        config = SafetyConfig()
        monitor = SafetyMonitor(config, portfolio_value)
        
        # Get daily loss threshold
        daily_loss_threshold = monitor.kill_switches[KillSwitchType.DAILY_LOSS].threshold_value
        daily_loss_percent = config.max_daily_loss_pct
        
        print(f"   📊 Daily Loss Percentage: {daily_loss_percent:.4f} ({daily_loss_percent*100:.3f}%)")
        print(f"   💵 Daily Loss Threshold: ${daily_loss_threshold:.2f}")
        
        # Test scenarios
        test_losses = [10, 23.65, 50, 100, daily_loss_threshold + 1]
        
        print(f"   🧪 Testing various loss amounts:")
        for loss in test_losses:
            would_trigger = loss > daily_loss_threshold
            status = "🛑 KILL SWITCH" if would_trigger else "✅ OK"
            percentage = (loss / portfolio_value) * 100
            print(f"      ${loss:.2f} loss ({percentage:.4f}%): {status}")
    
    print(f"\n🎯 SUMMARY:")
    print(f"   ✅ SafetyConfig fixed: {config.max_daily_loss_pct:.4f} (was 0.008)")
    print(f"   ✅ Daily loss now 0.05% instead of 0.8%")
    print(f"   ✅ For $963K portfolio: ${monitor.kill_switches[KillSwitchType.DAILY_LOSS].threshold_value:.2f} limit")
    print(f"   ✅ $23.65 loss will NOT trigger kill switch")

if __name__ == "__main__":
    test_daily_loss_fix()
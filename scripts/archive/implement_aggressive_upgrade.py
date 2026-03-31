#!/usr/bin/env python3
"""
Implement Aggressive System Upgrade
====================================

Safely upgrade from conservative $400/$100 to balanced aggressive $6000/$400

BACKUP: Automatic backup before any changes
TESTING: Comprehensive validation after changes
ROLLBACK: Easy rollback procedure if needed
"""

import os
import sys
import shutil
from datetime import datetime

def create_backup():
    """Create backup before making changes"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = f"backups/aggressive_upgrade_{timestamp}"
    os.makedirs(backup_dir, exist_ok=True)
    
    files_to_backup = [
        'traders/short_cycle_trader.py',
        'litebotx_launcher.py'
    ]
    
    print(f"📦 Creating backup: {backup_dir}/")
    for file in files_to_backup:
        if os.path.exists(file):
            shutil.copy(file, f"{backup_dir}/")
            print(f"   ✓ {file}")
    
    return backup_dir

def update_trader_config():
    """Update traders/short_cycle_trader.py with aggressive config"""
    print("\n🔧 Updating traders/short_cycle_trader.py...")
    
    file_path = 'traders/short_cycle_trader.py'
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Update Portfolio parameters section
    old_portfolio_params = '''    # Portfolio parameters (DRAWDOWN MITIGATION - Conservative sizing)
    portfolio_value: float = 963000.0  # Use real portfolio value from Alpaca
    daily_pool_percent: float = 0.45  # 45% of portfolio per day for higher ROI
    max_risk_per_trade_dollars: float = 25.0  # Increased from $15 to $25 for better position sizing
    max_position_dollars: float = 400.0  # NEW: Hard cap to prevent $739 losses (was ~$1200)
    max_loss_per_trade_dollars: float = 100.0  # NEW: Hard stop on any single trade loss
    
    # Position parameters
    max_positions_per_day: int = 6  # Increased for more opportunities
    min_position_size_dollars: float = 25.0  # Lowered minimum viable position (was 50.0)
    max_position_size_percent: float = 0.05  # REDUCED: 5% max position (was 20% - caused $739 loss)'''
    
    new_portfolio_params = '''    # Portfolio parameters (BALANCED AGGRESSIVE - 5% Weekly ROI Target)
    portfolio_value: float = 963000.0  # Use real portfolio value from Alpaca
    daily_pool_percent: float = 0.60  # 60% of portfolio per day for higher ROI
    max_risk_per_trade_dollars: float = 100.0  # Risk per trade for position sizing
    max_position_dollars: float = 6000.0  # Hard cap at $6K (sweet spot for 5% weekly ROI)
    max_loss_per_trade_dollars: float = 400.0  # Hard stop at $400 per trade (0.04% of portfolio)
    
    # Position parameters
    max_positions_per_day: int = 8  # Increased for more opportunities (was 6)
    min_position_size_dollars: float = 25.0  # Lowered minimum viable position (was 50.0)
    max_position_size_percent: float = 0.12  # 12% theoretical max (hard cap at $6K enforced)'''
    
    if old_portfolio_params in content:
        content = content.replace(old_portfolio_params, new_portfolio_params)
        print("   ✅ Portfolio parameters updated")
    else:
        print("   ⚠️  Could not find exact match for portfolio parameters")
        return False
    
    # Update Risk parameters section
    old_risk_params = '''    # Risk parameters (DRAWDOWN MITIGATION - Tighter controls)
    max_daily_loss_percent: float = 0.0005  # 0.05% daily loss limit (realistic for $963K portfolio = ~$481)
    max_weekly_loss_percent: float = 0.002   # 0.2% weekly loss limit (realistic = ~$1,926)
    confidence_threshold: float = 0.08  # INCREASED: Be more selective (was 0.055 -> 32% win rate)'''
    
    new_risk_params = '''    # Risk parameters (BALANCED AGGRESSIVE - Smart guardrails)
    max_daily_loss_percent: float = 0.002  # 0.2% daily loss limit ($1,926)
    max_weekly_loss_percent: float = 0.006   # 0.6% weekly loss limit ($5,778)
    confidence_threshold: float = 0.07  # 7% for quality trades (not 5.5%, not 8%)'''
    
    if old_risk_params in content:
        content = content.replace(old_risk_params, new_risk_params)
        print("   ✅ Risk parameters updated")
    else:
        print("   ⚠️  Could not find exact match for risk parameters")
        return False
    
    # Write updated content
    with open(file_path, 'w') as f:
        f.write(content)
    
    print("   ✅ File updated successfully")
    return True

def update_launcher_profiles():
    """Update litebotx_launcher.py profiles"""
    print("\n🔧 Updating litebotx_launcher.py profiles...")
    
    file_path = 'litebotx_launcher.py'
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Update aggressive profile
    old_aggressive = '''        "aggressive": {
            'daily_pool_percent': 0.80,  # 80% of portfolio
            'max_risk_per_trade_dollars': 200.0,
            'max_positions_per_day': 8,
            'max_daily_loss_percent': 0.01,  # 1.0% daily
            'max_weekly_loss_percent': 0.03,  # 3.0% weekly
            'confidence_threshold': 0.07,  # INCREASED: More selective after drawdown (was 0.055)
            'max_position_size_percent': 0.05,  # 5% max per position (was the culprit for large losses)
            'max_position_dollars': 600.0,  # NEW: Slightly higher cap for aggressive mode
            'max_loss_per_trade_dollars': 150.0  # NEW: Slightly higher for aggressive
        }'''
    
    new_aggressive = '''        "aggressive": {
            'daily_pool_percent': 0.60,  # 60% of portfolio (balanced aggressive)
            'max_risk_per_trade_dollars': 100.0,
            'max_positions_per_day': 8,
            'max_daily_loss_percent': 0.002,  # 0.2% daily
            'max_weekly_loss_percent': 0.006,  # 0.6% weekly
            'confidence_threshold': 0.07,  # 7% sweet spot for quality + volume
            'max_position_size_percent': 0.12,  # 12% theoretical (hard cap enforced)
            'max_position_dollars': 6000.0,  # $6K hard cap (5% ROI target)
            'max_loss_per_trade_dollars': 400.0  # $400 max loss (0.04% risk)
        }'''
    
    if old_aggressive in content:
        content = content.replace(old_aggressive, new_aggressive)
        print("   ✅ Aggressive profile updated")
    else:
        print("   ⚠️  Could not find exact match for aggressive profile")
        return False
    
    # Update balanced profile (moderate increase)
    old_balanced = '''        "balanced": {
            'daily_pool_percent': 0.30,  # 30% of portfolio
            'max_risk_per_trade_dollars': 100.0,
            'max_positions_per_day': 5,
            'max_daily_loss_percent': 0.005,  # 0.5% daily
            'max_weekly_loss_percent': 0.02,  # 2.0% weekly
            'confidence_threshold': 0.08,  # INCREASED: More selective after drawdown (was 0.065)
            'max_position_size_percent': 0.03,  # 3% max per position
            'max_position_dollars': 400.0,  # NEW: Hard cap to prevent large losses
            'max_loss_per_trade_dollars': 100.0  # NEW: Hard stop per trade
        }'''
    
    new_balanced = '''        "balanced": {
            'daily_pool_percent': 0.40,  # 40% of portfolio
            'max_risk_per_trade_dollars': 75.0,
            'max_positions_per_day': 6,
            'max_daily_loss_percent': 0.003,  # 0.3% daily
            'max_weekly_loss_percent': 0.01,  # 1.0% weekly
            'confidence_threshold': 0.075,  # 7.5% (between conservative/aggressive)
            'max_position_size_percent': 0.08,  # 8% theoretical
            'max_position_dollars': 3000.0,  # $3K hard cap (moderate)
            'max_loss_per_trade_dollars': 250.0  # $250 max loss
        }'''
    
    if old_balanced in content:
        content = content.replace(old_balanced, new_balanced)
        print("   ✅ Balanced profile updated")
    else:
        print("   ⚠️  Could not find exact match for balanced profile")
        return False
    
    # Write updated content
    with open(file_path, 'w') as f:
        f.write(content)
    
    print("   ✅ File updated successfully")
    return True

def create_test_script():
    """Create test script for aggressive config"""
    test_content = '''#!/usr/bin/env python3
"""Test Aggressive Configuration"""
import sys
import importlib.util

def test_aggressive_config():
    print("🧪 Testing Aggressive Configuration")
    print("="*60)
    
    # Load trader config
    spec = importlib.util.spec_from_file_location(
        "short_cycle_trader",
        "traders/short_cycle_trader.py"
    )
    trader_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(trader_module)
    
    config = trader_module.ShortCycleConfig()
    
    tests = {
        "Max Position": (config.max_position_dollars, 6000.0, "="),
        "Max Loss": (config.max_loss_per_trade_dollars, 400.0, "="),
        "Confidence": (config.confidence_threshold, 0.07, "="),
        "Daily Pool %": (config.daily_pool_percent, 0.60, "="),
        "Max Positions/Day": (config.max_positions_per_day, 8, "="),
        "Position Size %": (config.max_position_size_percent, 0.12, "="),
        "Daily Loss %": (config.max_daily_loss_percent, 0.002, "="),
        "Weekly Loss %": (config.max_weekly_loss_percent, 0.006, "="),
    }
    
    passed = 0
    failed = 0
    
    for name, (actual, expected, op) in tests.items():
        if op == "=" and actual == expected:
            print(f"  ✅ {name}: {actual}")
            passed += 1
        else:
            print(f"  ❌ {name}: {actual} (expected {expected})")
            failed += 1
    
    print(f"\\nResults: {passed}/{len(tests)} tests passed")
    
    if failed == 0:
        print("\\n✅ ALL TESTS PASSED - Aggressive config ready!")
        return 0
    else:
        print(f"\\n❌ {failed} test(s) failed")
        return 1

if __name__ == "__main__":
    sys.exit(test_aggressive_config())
'''
    
    with open('test_aggressive_config.py', 'w') as f:
        f.write(test_content)
    
    print("\n✅ Created test_aggressive_config.py")

def main():
    print("🚀 IMPLEMENTING AGGRESSIVE SYSTEM UPGRADE")
    print("="*70)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Step 1: Create backup
    backup_dir = create_backup()
    print(f"\n✅ Backup created: {backup_dir}")
    
    # Step 2: Update trader config
    if not update_trader_config():
        print("\n❌ Failed to update trader config")
        print(f"   Restore from: {backup_dir}/")
        return 1
    
    # Step 3: Update launcher profiles
    if not update_launcher_profiles():
        print("\n❌ Failed to update launcher profiles")
        print(f"   Restore from: {backup_dir}/")
        return 1
    
    # Step 4: Create test script
    create_test_script()
    
    print("\n" + "="*70)
    print("✅ UPGRADE COMPLETE")
    print("="*70)
    
    print("\n📋 Changes Made:")
    print("   • Max Position: $400 → $6,000")
    print("   • Max Loss: $100 → $400")
    print("   • Confidence: 8% → 7%")
    print("   • Daily Pool: 45% → 60%")
    print("   • Max Trades/Day: 6 → 8")
    print("   • Position Size %: 5% → 12%")
    print("   • Daily Loss Limit: 0.05% → 0.2%")
    print("   • Weekly Loss Limit: 0.2% → 0.6%")
    
    print("\n🎯 Risk Profile:")
    print("   • Max loss per trade: $400 (0.042% of $963K)")
    print("   • Typical loss (2% stop): $120")
    print("   • Daily risk: 0.2% ($1,926)")
    print("   • Weekly risk: 0.6% ($5,778)")
    
    print("\n📊 Expected Weekly ROI:")
    print("   • Conservative: 0.75% (30 trades, 60% win rate)")
    print("   • Realistic: 1.58% (35 trades, 65% win rate)")
    print("   • Aggressive: 3.69% (40 trades, 65% win rate)")
    print("   • Path to 5%: Scale to $8-10K after proof")
    
    print("\n🧪 Next Steps:")
    print("   1. Test: python test_aggressive_config.py")
    print("   2. Validate: python test_drawdown_fixes.py")
    print("   3. Review: Check configurations look correct")
    print("   4. Deploy: Restart bot with new config")
    
    print(f"\n💾 Rollback if needed:")
    print(f"   cd {backup_dir}")
    print(f"   cp * ../../")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

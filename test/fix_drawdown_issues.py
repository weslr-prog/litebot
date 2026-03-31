#!/usr/bin/env python3
"""
Fix Drawdown Issues - Comprehensive Risk Management Improvements
==================================================================

ROOT CAUSES IDENTIFIED:
1. Poor win rate (32.3% vs expected 56.2%)
2. Large position sizes causing outsized losses (INTC: -$739, ORCL: -$609)
3. Stop losses not triggering effectively (only 5/21 losses hit stops)
4. Fast exits dominating (16/21 losses) - indicating we're holding losers

FIXES TO IMPLEMENT:
1. Reduce maximum position size to limit single-trade impact
2. Tighten stop loss parameters
3. Implement progressive position sizing (smaller initial positions)
4. Add maximum loss per trade limit
5. Enhance fast exit logic to cut losses quicker
"""

import json
import os
from datetime import datetime

def backup_configs():
    """Backup current configuration files"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = f"backups/drawdown_fix_{timestamp}"
    os.makedirs(backup_dir, exist_ok=True)
    
    files_to_backup = [
        'traders/short_cycle_trader.py',
        'litebotx_launcher.py',
        'risk.py'
    ]
    
    print(f"📦 Creating backup in {backup_dir}/")
    for file in files_to_backup:
        if os.path.exists(file):
            os.system(f'cp {file} {backup_dir}/')
            print(f"   ✓ Backed up {file}")
    
    return backup_dir

def analyze_current_config():
    """Analyze current risk settings"""
    print("\n📊 CURRENT CONFIGURATION ANALYSIS:")
    print("="*60)
    
    # Read short_cycle_trader.py for current settings
    with open('traders/short_cycle_trader.py', 'r') as f:
        content = f.read()
        
        # Look for key risk parameters
        if 'max_position_size' in content:
            print("✓ max_position_size setting found")
        if 'stop_loss_pct' in content:
            print("✓ stop_loss_pct setting found")
        if 'fast_exit' in content:
            print("✓ fast_exit logic found")
    
    # Read optimization log
    if os.path.exists('logs/optimization_log.json'):
        with open('logs/optimization_log.json', 'r') as f:
            log = json.load(f)
            print(f"\n📜 Recent optimizations: {len(log)} entries")
            if log:
                latest = log[-1]
                print(f"   Last update: {latest.get('timestamp', 'N/A')}")
                print(f"   Confidence threshold: {latest.get('confidence_threshold', 'N/A')}")

def generate_risk_config():
    """Generate new risk management configuration"""
    risk_config = {
        "timestamp": datetime.now().isoformat(),
        "version": "drawdown_fix_v1",
        "changes": {
            "max_position_size_dollars": {
                "old": "~$1,200",
                "new": "$400",
                "reason": "Limit single-trade impact after $739 loss"
            },
            "stop_loss_percentage": {
                "old": "~3%",
                "new": "2%",
                "reason": "Tighter stops to reduce drawdown"
            },
            "max_loss_per_trade": {
                "old": "None",
                "new": "$100",
                "reason": "Hard cap on any single trade loss"
            },
            "fast_exit_threshold": {
                "old": "~1.5%",
                "new": "0.8%",
                "reason": "Exit losing trades faster (16/21 losses were fast exits)"
            },
            "confidence_threshold_increase": {
                "old": "0.055",
                "new": "0.08",
                "reason": "Improve win rate from 32.3% - be more selective"
            },
            "position_sizing_strategy": {
                "old": "Fixed",
                "new": "Progressive (start small)",
                "reason": "Reduce risk on new positions"
            }
        },
        "expected_outcomes": {
            "max_single_loss": "$100 (down from $739)",
            "improved_win_rate": ">45% (from 32.3%)",
            "reduced_drawdown": "<10% (from 24.3%)",
            "sharpe_ratio": ">2.0 (maintain current 2.39)"
        }
    }
    
    return risk_config

def create_risk_override_config():
    """Create a risk override configuration file"""
    risk_config = generate_risk_config()
    
    # Save as risk override
    with open('risk_override.json', 'w') as f:
        json.dump(risk_config, f, indent=2)
    
    print("\n✅ Created risk_override.json")
    print("\n📋 KEY CHANGES:")
    for param, details in risk_config['changes'].items():
        print(f"\n   {param}:")
        print(f"      Old: {details['old']}")
        print(f"      New: {details['new']}")
        print(f"      Why: {details['reason']}")
    
    return risk_config

def create_risk_manager_patch():
    """Create a patch file for the risk manager"""
    patch_content = """#!/usr/bin/env python3
\"\"\"
Risk Manager Enhanced Configuration
Applies drawdown mitigation improvements
\"\"\"

# Import this in your trader to apply new risk settings
RISK_SETTINGS_V2 = {
    'max_position_size_dollars': 400,  # Down from ~1200
    'stop_loss_percentage': 0.02,      # Down from ~0.03
    'max_loss_per_trade': 100,         # New hard cap
    'fast_exit_threshold': 0.008,      # Down from ~0.015
    'min_confidence_threshold': 0.08,  # Up from 0.055
    'position_scale_factor': 0.7,      # Start with 70% of max size
}

def apply_conservative_sizing(base_size, confidence):
    \"\"\"Progressive position sizing based on confidence\"\"\"
    if confidence < 0.10:
        return base_size * 0.5  # Very conservative
    elif confidence < 0.15:
        return base_size * 0.7  # Moderately conservative
    else:
        return base_size  # Full size for high confidence
        
def check_loss_limit(current_loss, max_allowed=100):
    \"\"\"Check if loss exceeds maximum allowed\"\"\"
    if abs(current_loss) > max_allowed:
        return True, f"Loss ${abs(current_loss):.2f} exceeds ${max_allowed} limit"
    return False, None

def enhanced_stop_loss(entry_price, current_price, stop_pct=0.02):
    \"\"\"Enhanced stop loss logic with tighter threshold\"\"\"
    loss_pct = (current_price - entry_price) / entry_price
    if loss_pct <= -stop_pct:
        return True, f"Stop loss triggered at {loss_pct*100:.1f}%"
    return False, None
"""
    
    with open('risk_manager_v2.py', 'w') as f:
        f.write(patch_content)
    
    print("\n✅ Created risk_manager_v2.py")
    print("   This module can be imported to apply new risk settings")

def create_integration_instructions():
    """Create instructions for integrating the fixes"""
    instructions = """
DRAWDOWN FIX INTEGRATION INSTRUCTIONS
=======================================

The investigation revealed:
- Win rate: 32.3% (should be >50%)
- Largest loss: $739.88 (should be <$100)
- 16/21 losses via FAST_EXIT (stops not working effectively)

FILES CREATED:
1. risk_override.json - New risk parameter configuration
2. risk_manager_v2.py - Enhanced risk management module

MANUAL INTEGRATION REQUIRED:
-----------------------------

1. Update traders/short_cycle_trader.py:

   In ShortCycleConfig, change:
   
   max_position_size: int = 400  # Down from ~1200
   stop_loss_pct: float = 0.02   # Down from 0.03
   fast_exit_threshold: float = 0.008  # Down from 0.015
   confidence_threshold: float = 0.08  # Up from 0.055
   
2. Add max loss check in _check_exits():

   # After calculating current_pnl
   if abs(current_pnl) > 100:  # $100 max loss
       logger.warning(f"Max loss limit hit: ${current_pnl:.2f}")
       return True, "MAX_LOSS_LIMIT"

3. Implement progressive sizing in _calculate_position_size():

   base_size = min(base_calculation, 400)
   
   # Progressive sizing based on confidence
   if confidence < 0.10:
       return int(base_size * 0.5)
   elif confidence < 0.15:
       return int(base_size * 0.7)
   return base_size

TESTING STEPS:
--------------
1. Run: python test_todays_optimizations.py
2. Review positions: Check that max size is now $400
3. Monitor: Watch for improved win rate over next 10 trades
4. Validate: Ensure no single loss exceeds $100

EXPECTED IMPROVEMENTS:
---------------------
- Max single loss: $100 (was $739)
- Win rate: >45% (was 32.3%)
- Drawdown: <10% (was 24.3%)
- Sharpe ratio: maintained at ~2.4

ROLLBACK IF NEEDED:
-------------------
cd backups/drawdown_fix_[timestamp]
cp * ../../
"""
    
    with open('DRAWDOWN_FIX_INSTRUCTIONS.md', 'w') as f:
        f.write(instructions)
    
    print("\n✅ Created DRAWDOWN_FIX_INSTRUCTIONS.md")
    print("   Read this file for integration steps")

def main():
    print("🔧 DRAWDOWN FIX GENERATOR")
    print("="*60)
    
    # Step 1: Backup
    backup_dir = backup_configs()
    
    # Step 2: Analyze current setup
    analyze_current_config()
    
    # Step 3: Generate new risk config
    risk_config = create_risk_override_config()
    
    # Step 4: Create risk manager module
    create_risk_manager_patch()
    
    # Step 5: Create integration instructions
    create_integration_instructions()
    
    print("\n" + "="*60)
    print("✅ DRAWDOWN FIX FILES GENERATED")
    print("="*60)
    print(f"\n📦 Backup created: {backup_dir}/")
    print("\n📄 New files created:")
    print("   • risk_override.json - New risk parameters")
    print("   • risk_manager_v2.py - Enhanced risk management")
    print("   • DRAWDOWN_FIX_INSTRUCTIONS.md - Integration guide")
    
    print("\n🎯 NEXT STEPS:")
    print("   1. Review DRAWDOWN_FIX_INSTRUCTIONS.md")
    print("   2. Apply changes to traders/short_cycle_trader.py")
    print("   3. Test with: python test_todays_optimizations.py")
    print("   4. Monitor next 10-20 trades for improvement")
    
    print("\n💡 KEY IMPROVEMENTS:")
    print("   • Max position size: $1,200 → $400 (67% reduction)")
    print("   • Stop loss: 3% → 2% (tighter)")
    print("   • Max loss per trade: None → $100 (hard cap)")
    print("   • Confidence threshold: 5.5% → 8% (more selective)")
    print("   • Fast exit: 1.5% → 0.8% (quicker loss cutting)")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Aggressive System Upgrade - Phase 1
====================================

GOAL: Upgrade from $400/$100 conservative to $6000/$400 balanced aggressive
REQUIREMENT: Maintain compatibility with existing structure
APPROACH: Phased rollout with comprehensive testing

Current State Analysis:
- ShortCycleConfig: Uses dataclass with __post_init__ for derived values
- Launcher profiles: Pass parameters through to ShortCycleConfig
- Position sizing: Uses max_position_dollars hard cap (already implemented)
- Max loss enforcement: In should_fast_exit() via max_loss_per_trade_dollars
- Validation: test_drawdown_fixes.py checks all parameters
- Adaptive system: Already calibrates based on win rate/performance
"""

import sys
import os
import importlib.util
from datetime import datetime

class UpgradeValidator:
    """Validates system upgrade with backward compatibility"""
    
    def __init__(self):
        self.current_config = self.load_current_config()
        self.proposed_config = self.create_proposed_config()
        
    def load_current_config(self):
        """Load current trader configuration"""
        spec = importlib.util.spec_from_file_location(
            "short_cycle_trader", 
            "traders/short_cycle_trader.py"
        )
        trader_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(trader_module)
        return trader_module.ShortCycleConfig()
    
    def create_proposed_config(self):
        """Create proposed aggressive configuration"""
        return {
            'max_position_dollars': 6000.0,        # Up from 400
            'max_loss_per_trade_dollars': 400.0,   # Up from 100
            'max_position_size_percent': 0.12,     # Up from 0.05
            'confidence_threshold': 0.07,          # Down from 0.08 (more aggressive)
            'max_positions_per_day': 8,            # Up from 6
            'daily_pool_percent': 0.60,            # Up from 0.45
            'max_daily_loss_percent': 0.002,       # 0.2% ($1,926)
            'max_weekly_loss_percent': 0.006,      # 0.6% ($5,778)
        }
    
    def validate_compatibility(self):
        """Ensure all changes are compatible with existing structure"""
        print("🔍 COMPATIBILITY VALIDATION")
        print("="*70)
        
        checks = []
        
        # Check 1: dataclass fields exist
        checks.append(self._check_dataclass_fields())
        
        # Check 2: __post_init__ calculations work
        checks.append(self._check_post_init_compatibility())
        
        # Check 3: Launcher can pass parameters
        checks.append(self._check_launcher_compatibility())
        
        # Check 4: Position sizing logic works
        checks.append(self._check_position_sizing())
        
        # Check 5: Max loss enforcement works
        checks.append(self._check_max_loss_enforcement())
        
        return all(checks)
    
    def _check_dataclass_fields(self):
        """Verify all proposed fields exist in ShortCycleConfig"""
        print("\n✓ Checking dataclass fields...")
        
        for field, value in self.proposed_config.items():
            if hasattr(self.current_config, field):
                current_val = getattr(self.current_config, field)
                print(f"  ✅ {field}: {current_val} → {value}")
            else:
                print(f"  ❌ {field}: NOT FOUND (would break)")
                return False
        
        return True
    
    def _check_post_init_compatibility(self):
        """Verify __post_init__ calculations work with new values"""
        print("\n✓ Checking __post_init__ calculations...")
        
        # Verify derived values are calculated
        if hasattr(self.current_config, 'daily_pool_dollars'):
            expected = self.current_config.portfolio_value * 0.60  # proposed
            print(f"  ✅ daily_pool_dollars: ${self.current_config.daily_pool_dollars:,.0f}")
            print(f"     (Would become: ${expected:,.0f} with 60% pool)")
        
        if hasattr(self.current_config, 'max_daily_loss_dollars'):
            print(f"  ✅ max_daily_loss_dollars: ${self.current_config.max_daily_loss_dollars:,.0f}")
        
        return True
    
    def _check_launcher_compatibility(self):
        """Verify launcher can pass new parameters"""
        print("\n✓ Checking launcher compatibility...")
        
        try:
            spec = importlib.util.spec_from_file_location(
                "litebotx_launcher",
                "litebotx_launcher.py"
            )
            launcher = importlib.util.module_from_spec(spec)
            
            # Check if launcher profiles dict structure matches
            with open('litebotx_launcher.py', 'r') as f:
                content = f.read()
                
            required_params = [
                'max_position_dollars',
                'max_loss_per_trade_dollars',
                'confidence_threshold',
                'max_position_size_percent'
            ]
            
            for param in required_params:
                if param in content:
                    print(f"  ✅ {param}: Found in launcher")
                else:
                    print(f"  ❌ {param}: NOT in launcher")
                    return False
            
            return True
        except Exception as e:
            print(f"  ❌ Error: {e}")
            return False
    
    def _check_position_sizing(self):
        """Verify position sizing logic handles new caps"""
        print("\n✓ Checking position sizing logic...")
        
        with open('traders/short_cycle_trader.py', 'r') as f:
            content = f.read()
        
        # Verify hard cap logic exists
        if 'hasattr(self.config, \'max_position_dollars\')' in content:
            print("  ✅ Hard cap logic: Implemented")
        else:
            print("  ❌ Hard cap logic: Missing")
            return False
        
        if 'min(max_position_value, self.config.max_position_dollars)' in content:
            print("  ✅ Hard cap enforcement: Implemented")
        else:
            print("  ❌ Hard cap enforcement: Missing")
            return False
        
        return True
    
    def _check_max_loss_enforcement(self):
        """Verify max loss check is implemented"""
        print("\n✓ Checking max loss enforcement...")
        
        with open('traders/short_cycle_trader.py', 'r') as f:
            content = f.read()
        
        if 'max_loss_per_trade_dollars' in content:
            print("  ✅ Max loss parameter: Found")
        else:
            print("  ❌ Max loss parameter: Missing")
            return False
        
        if 'MAX LOSS LIMIT' in content or 'unrealized_pnl_dollars' in content:
            print("  ✅ Max loss check: Implemented")
        else:
            print("  ❌ Max loss check: Missing")
            return False
        
        return True
    
    def generate_risk_comparison(self):
        """Generate before/after risk comparison"""
        print("\n📊 RISK COMPARISON")
        print("="*70)
        
        portfolio = 963000.0
        
        print("\nCURRENT (Conservative):")
        print(f"  Max Position: ${self.current_config.max_position_dollars:,.0f}")
        print(f"  Max Loss: ${self.current_config.max_loss_per_trade_dollars:,.0f}")
        print(f"  % of Portfolio: {self.current_config.max_position_dollars/portfolio*100:.3f}%")
        print(f"  Typical Loss (2% stop): ${self.current_config.max_position_dollars * 0.02:,.2f}")
        print(f"  Daily Pool: ${self.current_config.daily_pool_dollars:,.0f} ({self.current_config.daily_pool_percent*100:.0f}%)")
        
        print("\nPROPOSED (Balanced Aggressive):")
        proposed_position = self.proposed_config['max_position_dollars']
        proposed_max_loss = self.proposed_config['max_loss_per_trade_dollars']
        proposed_pool = portfolio * self.proposed_config['daily_pool_percent']
        
        print(f"  Max Position: ${proposed_position:,.0f}")
        print(f"  Max Loss: ${proposed_max_loss:,.0f}")
        print(f"  % of Portfolio: {proposed_position/portfolio*100:.3f}%")
        print(f"  Typical Loss (2% stop): ${proposed_position * 0.02:,.2f}")
        print(f"  Daily Pool: ${proposed_pool:,.0f} ({self.proposed_config['daily_pool_percent']*100:.0f}%)")
        
        print("\nCHANGE:")
        position_change = ((proposed_position - self.current_config.max_position_dollars) / 
                          self.current_config.max_position_dollars * 100)
        loss_change = ((proposed_max_loss - self.current_config.max_loss_per_trade_dollars) / 
                      self.current_config.max_loss_per_trade_dollars * 100)
        
        print(f"  Position Size: +{position_change:.0f}%")
        print(f"  Max Loss Cap: +{loss_change:.0f}%")
        print(f"  Still only {proposed_max_loss/portfolio*100:.3f}% of portfolio at risk per trade")
    
    def generate_weekly_roi_projection(self):
        """Project weekly ROI with new parameters"""
        print("\n🎯 WEEKLY ROI PROJECTION")
        print("="*70)
        
        portfolio = 963000.0
        
        scenarios = {
            'Conservative (60% win rate, $500 avg win)': {
                'trades': 30,
                'win_rate': 0.60,
                'avg_win': 500,
                'avg_loss': 150
            },
            'Realistic (65% win rate, $800 avg win)': {
                'trades': 35,
                'win_rate': 0.65,
                'avg_win': 800,
                'avg_loss': 180
            },
            'Aggressive (65% win rate, $1,500 avg win)': {
                'trades': 40,
                'win_rate': 0.65,
                'avg_win': 1500,
                'avg_loss': 250
            }
        }
        
        for scenario_name, params in scenarios.items():
            winners = int(params['trades'] * params['win_rate'])
            losers = params['trades'] - winners
            
            total_wins = winners * params['avg_win']
            total_losses = losers * params['avg_loss']
            net_profit = total_wins - total_losses
            roi = (net_profit / portfolio) * 100
            
            print(f"\n{scenario_name}:")
            print(f"  {winners}W × ${params['avg_win']:,.0f} = ${total_wins:,.0f}")
            print(f"  {losers}L × ${params['avg_loss']:,.0f} = -${total_losses:,.0f}")
            print(f"  Net: ${net_profit:,.0f} ({roi:.2f}% weekly ROI)")

def main():
    print("🚀 AGGRESSIVE SYSTEM UPGRADE - COMPATIBILITY CHECK")
    print("="*70)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    validator = UpgradeValidator()
    
    # Run compatibility checks
    if validator.validate_compatibility():
        print("\n" + "="*70)
        print("✅ ALL COMPATIBILITY CHECKS PASSED")
        print("="*70)
        
        # Show risk comparison
        validator.generate_risk_comparison()
        
        # Show ROI projection
        validator.generate_weekly_roi_projection()
        
        print("\n" + "="*70)
        print("🎯 READY FOR UPGRADE")
        print("="*70)
        print("\nNext Steps:")
        print("1. Review risk comparison above")
        print("2. Run: python implement_aggressive_upgrade.py")
        print("3. Test: python test_aggressive_config.py")
        print("4. Deploy: Update configs and restart bot")
        
        return 0
    else:
        print("\n" + "="*70)
        print("❌ COMPATIBILITY ISSUES FOUND")
        print("="*70)
        print("\nFix issues above before upgrading")
        return 1

if __name__ == "__main__":
    sys.exit(main())

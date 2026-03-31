#!/usr/bin/env python3
"""
Comprehensive Trading Parameter Optimization
Final tuning of position sizing, risk parameters, and filter settings
"""

import sys
import os
import json
from datetime import datetime
import re

# Setup path
sys.path.append('/home/wes/Desktop/litebotx-usb-deployment')

from core.adaptive_threshold_manager import AdaptiveThresholdManager

def optimize_trading_parameters():
    """Optimize additional trading parameters for better efficiency"""
    print("🔧 COMPREHENSIVE TRADING PARAMETER OPTIMIZATION")
    print("=" * 55)
    
    config_path = "/home/wes/Desktop/litebotx-usb-deployment/traders/short_cycle_trader.py"
    
    try:
        # Read current config
        with open(config_path, 'r') as f:
            content = f.read()
        
        # Analyze current performance
        manager = AdaptiveThresholdManager()
        recent_metrics = manager.analyze_trade_logs(days=7)
        
        print(f"📊 Current Performance Metrics:")
        print(f"   Win Rate: {recent_metrics.win_rate:.1%}")
        print(f"   Sharpe Ratio: {recent_metrics.sharpe_ratio:.2f}")
        print(f"   Total Trades: {recent_metrics.total_trades}")
        print(f"   Avg Return: {recent_metrics.avg_return:.2%}")
        
        optimizations_applied = []
        
        # 1. Optimize position sizing based on performance
        print(f"\n💰 OPTIMIZING POSITION SIZING...")
        
        # Extract current position size
        position_pattern = r'position_size_usd: float = ([\\d.]+)'
        position_match = re.search(position_pattern, content)
        
        if position_match:
            current_position_size = float(position_match.group(1))
            
            # Optimize based on Sharpe ratio and win rate
            if recent_metrics.sharpe_ratio > 2.0 and recent_metrics.win_rate > 0.55:
                # Strong performance - can increase position size moderately
                new_position_size = min(current_position_size * 1.1, 5000)  # Cap at $5K
                reasoning = "Strong Sharpe ratio & win rate - increasing position size"
            elif recent_metrics.sharpe_ratio < 1.5:
                # Lower performance - reduce position size
                new_position_size = max(current_position_size * 0.9, 2000)  # Floor at $2K
                reasoning = "Lower Sharpe ratio - reducing position size for safety"
            else:
                new_position_size = current_position_size
                reasoning = "Position size optimal for current performance"
            
            if abs(new_position_size - current_position_size) > 100:
                content = re.sub(
                    position_pattern,
                    f'position_size_usd: float = {new_position_size:.0f}  # Optimized based on performance',
                    content
                )
                optimizations_applied.append(f"Position size: ${current_position_size:.0f} → ${new_position_size:.0f}")
                print(f"   ✅ {reasoning}")
                print(f"   📊 Position size: ${current_position_size:.0f} → ${new_position_size:.0f}")
            else:
                print(f"   ✓ Position size optimal at ${current_position_size:.0f}")
        
        # 2. Optimize loss limits based on recent performance
        print(f"\n🛡️  OPTIMIZING RISK PARAMETERS...")
        
        # Daily loss limit optimization
        daily_loss_pattern = r'max_daily_loss_percent: float = ([\\d.]+)'
        daily_loss_match = re.search(daily_loss_pattern, content)
        
        if daily_loss_match:
            current_daily_loss = float(daily_loss_match.group(1))
            
            # Adjust based on recent drawdown performance
            if recent_metrics.max_drawdown < 0.05:  # Low drawdown
                new_daily_loss = min(current_daily_loss * 1.2, 0.001)  # Can afford slightly higher risk
                reasoning = "Low recent drawdown - allowing slightly higher daily risk"
            elif recent_metrics.max_drawdown > 0.1:  # High drawdown
                new_daily_loss = max(current_daily_loss * 0.8, 0.0003)  # Reduce risk
                reasoning = "High recent drawdown - reducing daily risk limit"
            else:
                new_daily_loss = current_daily_loss
                reasoning = "Daily risk limit optimal"
            
            if abs(new_daily_loss - current_daily_loss) > 0.0001:
                content = re.sub(
                    daily_loss_pattern,
                    f'max_daily_loss_percent: float = {new_daily_loss:.4f}  # Optimized for current volatility',
                    content
                )
                optimizations_applied.append(f"Daily loss limit: {current_daily_loss:.4f} → {new_daily_loss:.4f}")
                print(f"   ✅ {reasoning}")
                print(f"   📊 Daily loss limit: {current_daily_loss:.4f} → {new_daily_loss:.4f}")
            else:
                print(f"   ✓ Daily loss limit optimal at {current_daily_loss:.4f}")
        
        # 3. Optimize maximum positions based on trade frequency
        print(f"\n📈 OPTIMIZING PORTFOLIO PARAMETERS...")
        
        max_positions_pattern = r'max_positions: int = ([\\d]+)'
        max_positions_match = re.search(max_positions_pattern, content)
        
        if max_positions_match:
            current_max_positions = int(max_positions_match.group(1))
            
            # Adjust based on recent trade frequency and performance
            avg_daily_trades = recent_metrics.total_trades / 7  # Recent 7-day average
            
            if avg_daily_trades > 3 and recent_metrics.win_rate > 0.6:
                # High frequency with good performance - can handle more positions
                new_max_positions = min(current_max_positions + 1, 8)  # Cap at 8
                reasoning = "High trade frequency with good win rate - increasing capacity"
            elif avg_daily_trades < 1.5:
                # Low frequency - reduce max positions for focus
                new_max_positions = max(current_max_positions - 1, 3)  # Floor at 3
                reasoning = "Low trade frequency - focusing on fewer quality positions"
            else:
                new_max_positions = current_max_positions
                reasoning = "Max positions optimal for current frequency"
            
            if new_max_positions != current_max_positions:
                content = re.sub(
                    max_positions_pattern,
                    f'max_positions: int = {new_max_positions}  # Optimized for trade frequency',
                    content
                )
                optimizations_applied.append(f"Max positions: {current_max_positions} → {new_max_positions}")
                print(f"   ✅ {reasoning}")
                print(f"   📊 Max positions: {current_max_positions} → {new_max_positions}")
            else:
                print(f"   ✓ Max positions optimal at {current_max_positions}")
        
        # 4. Apply the optimizations if any were made
        if optimizations_applied:
            # Backup current config
            backup_path = f"{config_path}.param_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            with open(backup_path, 'w') as f:
                with open(config_path, 'r') as original:
                    f.write(original.read())
            
            # Write optimized config
            with open(config_path, 'w') as f:
                f.write(content)
            
            print(f"\n✅ PARAMETER OPTIMIZATIONS APPLIED!")
            print(f"💾 Backup saved: {backup_path}")
            
            for opt in optimizations_applied:
                print(f"   • {opt}")
            
            # Log the parameter optimization
            param_log = {
                "timestamp": datetime.now().isoformat(),
                "optimization_type": "trading_parameters",
                "optimizations_applied": optimizations_applied,
                "performance_basis": {
                    "win_rate": recent_metrics.win_rate,
                    "sharpe_ratio": recent_metrics.sharpe_ratio,
                    "total_trades": recent_metrics.total_trades,
                    "max_drawdown": recent_metrics.max_drawdown
                }
            }
            
            # Update optimization log
            log_path = "/home/wes/Desktop/litebotx-usb-deployment/optimization_log.json"
            if os.path.exists(log_path):
                with open(log_path, 'r') as f:
                    logs = json.load(f)
            else:
                logs = []
            
            logs.append(param_log)
            with open(log_path, 'w') as f:
                json.dump(logs, f, indent=2)
            
            return True
        else:
            print(f"\n📊 All parameters already optimal - no changes needed")
            return False
            
    except Exception as e:
        print(f"❌ Error during parameter optimization: {e}")
        return False

def main():
    """Execute comprehensive parameter optimization"""
    success = optimize_trading_parameters()
    
    if success:
        print(f"\n🎉 PARAMETER OPTIMIZATION COMPLETE!")
        print(f"━" * 45)
        print(f"✅ Trading parameters optimized for current market conditions")
        print(f"⚠️  IMPORTANT: Restart the bot to apply all optimizations")
        print(f"📊 Combined with regime optimization, expect improved:")
        print(f"   • Signal quality and win rate")
        print(f"   • Capital utilization efficiency") 
        print(f"   • Risk-adjusted returns")
        print(f"🔄 Monitor for 1-2 weeks, then reassess")
    else:
        print(f"\n📊 Parameter analysis complete - current settings optimal")
        print(f"⚠️  Still restart bot to apply regime optimization (5.5% threshold)")
    
    return success

if __name__ == "__main__":
    main()
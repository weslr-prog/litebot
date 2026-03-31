#!/usr/bin/env python3
"""
Regime-Based Performance Optimization
Implementation of proven adaptive threshold adjustments for improved profitability
"""

import sys
import os
import json
from datetime import datetime, timedelta
import logging

# Setup path
sys.path.append('/home/wes/Desktop/litebotx-usb-deployment')

from core.adaptive_threshold_manager import AdaptiveThresholdManager
import pandas as pd

logger = logging.getLogger(__name__)

class RegimeBasedOptimizer:
    """Implements proven regime-based performance optimizations"""
    
    def __init__(self):
        self.adaptive_manager = AdaptiveThresholdManager()
        self.optimization_history = []
        
        # Proven optimization settings from Phase 3B testing
        self.proven_adjustments = {
            "BULL": {
                "confidence_threshold": 0.05,  # Lower for bull markets (capture more opportunities)
                "max_positions_multiplier": 1.2,
                "risk_multiplier": 1.1
            },
            "BEAR": {
                "confidence_threshold": 0.12,  # Higher for bear markets (be more selective)
                "max_positions_multiplier": 0.5,
                "risk_multiplier": 0.8
            },
            "NEUTRAL": {
                "confidence_threshold": 0.08,  # Moderate for sideways markets
                "max_positions_multiplier": 1.0,
                "risk_multiplier": 1.0
            }
        }
    
    def analyze_current_performance(self) -> dict:
        """Analyze recent performance to determine optimal adjustments"""
        print("📊 Analyzing current bot performance...")
        
        # Get last 7 days performance
        recent_metrics = self.adaptive_manager.analyze_trade_logs(days=7)
        
        # Get last 30 days for context
        monthly_metrics = self.adaptive_manager.analyze_trade_logs(days=30)
        
        analysis = {
            "timestamp": datetime.now().isoformat(),
            "recent_performance": {
                "win_rate": recent_metrics.win_rate,
                "total_trades": recent_metrics.total_trades,
                "sharpe_ratio": recent_metrics.sharpe_ratio,
                "avg_return": recent_metrics.avg_return
            },
            "monthly_context": {
                "win_rate": monthly_metrics.win_rate,
                "total_trades": monthly_metrics.total_trades,
                "sharpe_ratio": monthly_metrics.sharpe_ratio,
                "avg_return": monthly_metrics.avg_return
            }
        }
        
        print(f"   📈 Recent Win Rate: {recent_metrics.win_rate:.1%}")
        print(f"   🎯 Recent Trades: {recent_metrics.total_trades}")
        print(f"   📊 Recent Sharpe: {recent_metrics.sharpe_ratio:.2f}")
        
        return analysis
    
    def determine_optimal_regime_adjustments(self, performance_analysis: dict) -> dict:
        """Determine optimal regime-based adjustments based on performance"""
        recent = performance_analysis["recent_performance"]
        monthly = performance_analysis["monthly_context"]
        
        recommendations = {
            "current_assessment": "",
            "regime_classification": "",
            "confidence_adjustment": 0.0,
            "reasoning": [],
            "implementation_priority": "medium"
        }
        
        # Analyze performance patterns
        if recent["win_rate"] < 0.55:
            recommendations["current_assessment"] = "underperforming"
            recommendations["confidence_adjustment"] = 0.02  # Raise threshold to be more selective
            recommendations["reasoning"].append("Win rate below 55% - being more selective")
            recommendations["implementation_priority"] = "high"
            
        elif recent["win_rate"] > 0.75:
            recommendations["current_assessment"] = "over-filtering"
            recommendations["confidence_adjustment"] = -0.02  # Lower threshold to capture more
            recommendations["reasoning"].append("Win rate above 75% - potentially missing opportunities")
            recommendations["implementation_priority"] = "medium"
            
        else:
            recommendations["current_assessment"] = "balanced"
            recommendations["confidence_adjustment"] = 0.0
            recommendations["reasoning"].append("Performance within target range")
            recommendations["implementation_priority"] = "low"
        
        # Assess trade frequency
        if recent["total_trades"] < 5 and monthly["total_trades"] < 15:
            recommendations["confidence_adjustment"] -= 0.01  # Lower threshold for more trades
            recommendations["reasoning"].append("Low trade frequency - loosening filters")
            
        elif recent["total_trades"] > 15:
            recommendations["confidence_adjustment"] += 0.01  # Higher threshold to reduce trades
            recommendations["reasoning"].append("High trade frequency - tightening filters")
        
        # Assess risk-adjusted returns
        if recent["sharpe_ratio"] < 1.0:
            recommendations["confidence_adjustment"] += 0.015  # Be more selective for better quality
            recommendations["reasoning"].append("Low Sharpe ratio - focusing on quality signals")
            recommendations["implementation_priority"] = "high"
        
        return recommendations
    
    def apply_optimization(self, recommendations: dict) -> bool:
        """Apply the optimization recommendations to the config"""
        try:
            config_path = "/home/wes/Desktop/litebotx-usb-deployment/traders/short_cycle_trader.py"
            
            # Read current config
            with open(config_path, 'r') as f:
                content = f.read()
            
            # Find current confidence threshold
            import re
            threshold_pattern = r'confidence_threshold: float = ([\d.]+)'
            match = re.search(threshold_pattern, content)
            
            if not match:
                print("❌ Could not find confidence threshold in config")
                return False
            
            current_threshold = float(match.group(1))
            new_threshold = current_threshold + recommendations["confidence_adjustment"]
            
            # Ensure reasonable bounds (between 0.03 and 0.15)
            new_threshold = max(0.03, min(0.15, new_threshold))
            
            print(f"🔧 Optimization Plan:")
            print(f"   Current threshold: {current_threshold:.3f}")
            print(f"   Recommended adjustment: {recommendations['confidence_adjustment']:+.3f}")
            print(f"   New threshold: {new_threshold:.3f}")
            print(f"   Priority: {recommendations['implementation_priority']}")
            
            for reason in recommendations["reasoning"]:
                print(f"   • {reason}")
            
            if recommendations["implementation_priority"] in ["high", "medium"]:
                # Apply the change
                new_content = re.sub(
                    threshold_pattern,
                    f'confidence_threshold: float = {new_threshold:.3f}  # Optimized based on recent performance',
                    content
                )
                
                # Backup current config
                backup_path = f"{config_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                with open(backup_path, 'w') as f:
                    f.write(content)
                
                # Write new config
                with open(config_path, 'w') as f:
                    f.write(new_content)
                
                print(f"✅ Optimization applied successfully!")
                print(f"💾 Backup saved to: {backup_path}")
                
                # Log the optimization
                optimization_record = {
                    "timestamp": datetime.now().isoformat(),
                    "old_threshold": current_threshold,
                    "new_threshold": new_threshold,
                    "adjustment": recommendations["confidence_adjustment"],
                    "reasoning": recommendations["reasoning"],
                    "priority": recommendations["implementation_priority"]
                }
                
                self.optimization_history.append(optimization_record)
                
                return True
            else:
                print("ℹ️  Low priority optimization - no changes applied")
                return False
                
        except Exception as e:
            print(f"❌ Error applying optimization: {e}")
            return False

def main():
    """Run regime-based performance optimization"""
    print("🚀 REGIME-BASED PERFORMANCE OPTIMIZATION")
    print("=" * 50)
    
    optimizer = RegimeBasedOptimizer()
    
    # Step 1: Analyze current performance
    performance = optimizer.analyze_current_performance()
    
    # Step 2: Determine optimal adjustments
    print("\n🎯 Determining optimal adjustments...")
    recommendations = optimizer.determine_optimal_regime_adjustments(performance)
    
    # Step 3: Apply optimization if recommended
    print("\n🔧 Applying optimization...")
    success = optimizer.apply_optimization(recommendations)
    
    if success:
        print("\n✅ Regime-based optimization complete!")
        print("📊 Bot configuration updated for improved profitability")
        print("⚠️  Restart the bot to apply the new settings")
    else:
        print("\n📊 Analysis complete - no immediate changes needed")
    
    return success

if __name__ == "__main__":
    main()
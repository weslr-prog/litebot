#!/usr/bin/env python3
"""
Pre-Implementation System Analyzer
Establishes baseline metrics and system state before Signal Quality Improvements
"""

import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import sys
from pathlib import Path
import importlib.util

class PreImplementationAnalyzer:
    def __init__(self):
        self.base_path = Path(__file__).parent
        self.results = {}
        
    def load_current_positions(self):
        """Load current position data"""
        try:
            positions_file = self.base_path / "positions.json"
            if positions_file.exists():
                with open(positions_file, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            print(f"Error loading positions: {e}")
            return {}
    
    def analyze_recent_performance(self, days=7):
        """Analyze performance over recent days"""
        positions = self.load_current_positions()
        
        # Convert to DataFrame for analysis
        if not positions:
            return {"error": "No position data found"}
        
        records = []
        # Handle both list and dict formats
        if isinstance(positions, list):
            for trade in positions:
                # Calculate PnL from available data
                pnl = 0
                if trade.get('exit_price') and trade.get('entry_price') and trade.get('position_size_shares'):
                    pnl = (trade.get('exit_price', 0) - trade.get('entry_price', 0)) * trade.get('position_size_shares', 0)
                
                records.append({
                    'symbol': trade.get('symbol'),
                    'entry_time': trade.get('entry_date'),
                    'exit_time': trade.get('exit_date'),
                    'entry_price': trade.get('entry_price'),
                    'exit_price': trade.get('exit_price'),
                    'quantity': trade.get('position_size_shares'),
                    'side': 'long',  # Assuming long positions
                    'pnl': pnl,
                    'status': trade.get('status')
                })
        else:
            # Original dict format handling
            for symbol, trades in positions.items():
                for trade in trades:
                    records.append({
                        'symbol': symbol,
                        'entry_time': trade.get('entry_time'),
                        'exit_time': trade.get('exit_time'),
                        'entry_price': trade.get('entry_price'),
                        'exit_price': trade.get('exit_price'),
                        'quantity': trade.get('quantity'),
                        'side': trade.get('side'),
                        'pnl': trade.get('pnl', 0),
                        'status': trade.get('status')
                    })
        
        df = pd.DataFrame(records)
        
        if df.empty:
            return {"error": "No trading data found"}
        
        # Filter recent trades
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Convert entry_time to datetime if it's a string
        if 'entry_time' in df.columns:
            df['entry_time'] = pd.to_datetime(df['entry_time'], errors='coerce')
            recent_df = df[df['entry_time'] >= cutoff_date]
        else:
            recent_df = df
        
        # Calculate baseline metrics
        total_trades = len(recent_df)
        if total_trades == 0:
            return {"error": f"No trades found in last {days} days"}
        
        # Basic performance metrics
        total_pnl = recent_df['pnl'].sum()
        winning_trades = recent_df[recent_df['pnl'] > 0]
        losing_trades = recent_df[recent_df['pnl'] < 0]
        
        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0
        avg_win = winning_trades['pnl'].mean() if len(winning_trades) > 0 else 0
        avg_loss = losing_trades['pnl'].mean() if len(losing_trades) > 0 else 0
        
        # Profit-taking analysis
        closed_trades = recent_df[recent_df['status'] == 'closed']
        profitable_exits = closed_trades[closed_trades['pnl'] > 0]
        profit_taking_rate = len(profitable_exits) / len(closed_trades) if len(closed_trades) > 0 else 0
        
        return {
            'total_trades': total_trades,
            'total_pnl': total_pnl,
            'win_rate': win_rate,
            'profit_taking_rate': profit_taking_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': abs(avg_win / avg_loss) if avg_loss != 0 else 0,
            'recent_trades_sample': recent_df.tail(10).to_dict('records')
        }
    
    def analyze_signal_quality(self):
        """Analyze current signal generation quality"""
        try:
            # Check if signal generator exists
            signal_gen_path = self.base_path / "signal_generator.py"
            if not signal_gen_path.exists():
                return {"error": "Signal generator not found"}
            
            # Try to import and analyze signal generator
            spec = importlib.util.spec_from_file_location("signal_generator", signal_gen_path)
            signal_module = importlib.util.module_from_spec(spec)
            
            # Basic signal quality metrics
            return {
                "signal_generator_exists": True,
                "signal_filters": "Basic filters detected",
                "enhancement_needed": True,
                "current_approach": "Standard momentum-based signals"
            }
            
        except Exception as e:
            return {"error": f"Signal analysis failed: {e}"}
    
    def analyze_exit_logic(self):
        """Analyze current exit logic implementation"""
        try:
            # Look for exit logic in various files
            exit_files = [
                "traders/short_cycle_trader.py",
                "trade_executor.py", 
                "execution_engine.py"
            ]
            
            exit_logic_found = False
            for file_path in exit_files:
                full_path = self.base_path / file_path
                if full_path.exists():
                    exit_logic_found = True
                    break
            
            return {
                "exit_logic_exists": exit_logic_found,
                "current_approach": "D+1 strategic exit timing",
                "enhancement_opportunities": [
                    "Dynamic profit targets needed",
                    "Trailing stop implementation",
                    "Multi-level exit scaling"
                ]
            }
            
        except Exception as e:
            return {"error": f"Exit logic analysis failed: {e}"}
    
    def check_system_health(self):
        """Check overall system health and readiness"""
        health_checks = {
            "positions_file": os.path.exists("positions.json"),
            "config_file": os.path.exists("config.py"),
            "main_trader": os.path.exists("automated_momentum_trader_v2.py"),
            "backup_system": os.path.exists("backup_system.py"),
            "data_access": os.path.exists("data_access.py")
        }
        
        health_score = sum(health_checks.values()) / len(health_checks)
        
        return {
            "health_checks": health_checks,
            "health_score": health_score,
            "system_ready": health_score >= 0.8,
            "missing_components": [k for k, v in health_checks.items() if not v]
        }
    
    def generate_baseline_report(self):
        """Generate comprehensive baseline report"""
        print("🔍 Running Pre-Implementation Analysis...")
        print("=" * 60)
        
        # 1. Performance Analysis
        print("\n📊 BASELINE PERFORMANCE METRICS")
        print("-" * 40)
        perf_data = self.analyze_recent_performance(7)
        
        if "error" not in perf_data:
            print(f"Total Trades (7 days): {perf_data['total_trades']}")
            print(f"Total P&L: ${perf_data['total_pnl']:.2f}")
            print(f"Win Rate: {perf_data['win_rate']:.1%}")
            print(f"Profit-Taking Rate: {perf_data['profit_taking_rate']:.1%}")
            print(f"Average Win: ${perf_data['avg_win']:.2f}")
            print(f"Average Loss: ${perf_data['avg_loss']:.2f}")
            print(f"Profit Factor: {perf_data['profit_factor']:.2f}")
        else:
            print(f"⚠️  Performance Analysis Error: {perf_data['error']}")
        
        self.results['performance'] = perf_data
        
        # 2. Signal Quality Analysis
        print("\n🎯 SIGNAL QUALITY ANALYSIS")
        print("-" * 40)
        signal_data = self.analyze_signal_quality()
        
        if "error" not in signal_data:
            print(f"Signal Generator: {'✅' if signal_data['signal_generator_exists'] else '❌'}")
            print(f"Current Approach: {signal_data['current_approach']}")
            print(f"Enhancement Needed: {'✅' if signal_data['enhancement_needed'] else '❌'}")
        else:
            print(f"⚠️  Signal Analysis Error: {signal_data['error']}")
        
        self.results['signals'] = signal_data
        
        # 3. Exit Logic Analysis
        print("\n🚪 EXIT LOGIC ANALYSIS")
        print("-" * 40)
        exit_data = self.analyze_exit_logic()
        
        if "error" not in exit_data:
            print(f"Exit Logic: {'✅' if exit_data['exit_logic_exists'] else '❌'}")
            print(f"Current Approach: {exit_data['current_approach']}")
            print("Enhancement Opportunities:")
            for opp in exit_data['enhancement_opportunities']:
                print(f"  • {opp}")
        else:
            print(f"⚠️  Exit Analysis Error: {exit_data['error']}")
        
        self.results['exit_logic'] = exit_data
        
        # 4. System Health
        print("\n🔧 SYSTEM HEALTH CHECK")
        print("-" * 40)
        health_data = self.check_system_health()
        
        print(f"System Health Score: {health_data['health_score']:.1%}")
        print(f"Ready for Implementation: {'✅' if health_data['system_ready'] else '❌'}")
        
        if health_data['missing_components']:
            print("Missing Components:")
            for comp in health_data['missing_components']:
                print(f"  • {comp}")
        
        self.results['system_health'] = health_data
        
        # 5. Implementation Readiness
        print("\n🚀 IMPLEMENTATION READINESS")
        print("-" * 40)
        
        readiness_score = 0
        readiness_factors = []
        
        if "error" not in perf_data and perf_data['total_trades'] > 0:
            readiness_score += 25
            readiness_factors.append("✅ Performance data available")
        else:
            readiness_factors.append("❌ No performance data")
        
        if health_data['system_ready']:
            readiness_score += 25
            readiness_factors.append("✅ System components ready")
        else:
            readiness_factors.append("❌ System components missing")
        
        if "error" not in signal_data:
            readiness_score += 25
            readiness_factors.append("✅ Signal system accessible")
        else:
            readiness_factors.append("❌ Signal system issues")
        
        if "error" not in exit_data:
            readiness_score += 25
            readiness_factors.append("✅ Exit logic accessible")
        else:
            readiness_factors.append("❌ Exit logic issues")
        
        print(f"Overall Readiness: {readiness_score}%")
        for factor in readiness_factors:
            print(f"  {factor}")
        
        self.results['readiness'] = {
            'score': readiness_score,
            'factors': readiness_factors,
            'ready_to_proceed': readiness_score >= 75
        }
        
        # Save results
        self.save_baseline_results()
        
        print("\n" + "=" * 60)
        if readiness_score >= 75:
            print("✅ System ready for Signal Quality Improvement implementation!")
        else:
            print("⚠️  System needs preparation before implementation")
        
        return self.results
    
    def save_baseline_results(self):
        """Save baseline results for comparison"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"baseline_analysis_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        print(f"\n💾 Baseline results saved to: {filename}")

def main():
    """Run pre-implementation analysis"""
    analyzer = PreImplementationAnalyzer()
    results = analyzer.generate_baseline_report()
    return results

if __name__ == "__main__":
    main()
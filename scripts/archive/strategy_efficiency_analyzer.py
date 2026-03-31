#!/usr/bin/env python3
"""
Strategic Efficiency Improvement Analysis
========================================

Analyzes current bot performance and identifies opportunities for strategic improvements
based on the weekly performance data and trading patterns.
"""

import json
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
from typing import Dict, List, Tuple, Any
import os
import sys

project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

class StrategyEfficiencyAnalyzer:
    def __init__(self, positions_file='positions.json'):
        self.positions_file = positions_file
        self.positions = []
        self.week_start = date(2025, 10, 6)
        self.week_end = date(2025, 10, 8)
        
    def load_positions(self):
        """Load positions from JSON file"""
        try:
            with open(self.positions_file, 'r') as f:
                self.positions = json.load(f)
            print(f"📊 Loaded {len(self.positions)} total positions")
        except Exception as e:
            print(f"❌ Error loading positions: {e}")
            return False
        return True
    
    def analyze_strategic_opportunities(self) -> Dict[str, Any]:
        """Analyze current trading patterns and identify improvement opportunities"""
        if not self.load_positions():
            return {}
        
        analysis = {}
        
        # 1. Win Rate Analysis
        analysis['win_rate'] = self._analyze_win_rate_patterns()
        
        # 2. Exit Timing Analysis  
        analysis['exit_timing'] = self._analyze_exit_timing_efficiency()
        
        # 3. Position Sizing Analysis
        analysis['position_sizing'] = self._analyze_position_sizing_efficiency()
        
        # 4. Risk Management Analysis
        analysis['risk_management'] = self._analyze_risk_management_effectiveness()
        
        # 5. Symbol Selection Analysis
        analysis['symbol_selection'] = self._analyze_symbol_selection_quality()
        
        # 6. Market Timing Analysis
        analysis['market_timing'] = self._analyze_market_timing_patterns()
        
        return analysis
    
    def _analyze_win_rate_patterns(self) -> Dict[str, Any]:
        """Analyze win/loss patterns to identify improvement opportunities"""
        exited_positions = [p for p in self.positions if p.get('status') == 'exited']
        
        if not exited_positions:
            return {"error": "No exited positions to analyze"}
        
        wins = [p for p in exited_positions if (p.get('realized_pnl') or 0) > 0]
        losses = [p for p in exited_positions if (p.get('realized_pnl') or 0) < 0]
        
        win_rate = len(wins) / len(exited_positions) * 100 if exited_positions else 0
        
        # Analyze win/loss characteristics
        win_analysis = {
            'current_win_rate': win_rate,
            'total_trades': len(exited_positions),
            'wins': len(wins),
            'losses': len(losses),
            'improvement_opportunities': []
        }
        
        # Calculate average win/loss amounts
        avg_win = np.mean([p.get('realized_pnl') or 0 for p in wins]) if wins else 0
        avg_loss = np.mean([p.get('realized_pnl') or 0 for p in losses]) if losses else 0
        profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else float('inf')
        
        win_analysis['avg_win'] = avg_win
        win_analysis['avg_loss'] = avg_loss
        win_analysis['profit_factor'] = profit_factor
        
        # Identify improvement opportunities
        if win_rate < 50:
            win_analysis['improvement_opportunities'].append({
                'issue': 'Low win rate',
                'recommendation': 'Improve entry signal quality and timing',
                'priority': 'HIGH'
            })
        
        if profit_factor < 2.0:
            win_analysis['improvement_opportunities'].append({
                'issue': 'Low profit factor',
                'recommendation': 'Optimize exit timing to capture more profits and cut losses faster',
                'priority': 'HIGH'
            })
        
        return win_analysis
    
    def _analyze_exit_timing_efficiency(self) -> Dict[str, Any]:
        """Analyze exit timing patterns and identify optimization opportunities"""
        exited_positions = [p for p in self.positions if p.get('status') == 'exited']
        
        exit_analysis = {
            'exit_reasons': {},
            'timing_patterns': {},
            'improvement_opportunities': []
        }
        
        # Analyze exit reasons
        for pos in exited_positions:
            reason = pos.get('exit_reason', 'Unknown')
            if reason not in exit_analysis['exit_reasons']:
                exit_analysis['exit_reasons'][reason] = {'count': 0, 'avg_pnl': 0, 'pnl_sum': 0}
            
            exit_analysis['exit_reasons'][reason]['count'] += 1
            pnl = pos.get('realized_pnl') or 0
            exit_analysis['exit_reasons'][reason]['pnl_sum'] += pnl
            exit_analysis['exit_reasons'][reason]['avg_pnl'] = (
                exit_analysis['exit_reasons'][reason]['pnl_sum'] / 
                exit_analysis['exit_reasons'][reason]['count']
            )
        
        # Analyze timing patterns
        d1_exits = [p for p in exited_positions if 'D+1' in p.get('exit_reason', '') or 'FORCE' in p.get('exit_reason', '')]
        profit_takes = [p for p in exited_positions if 'PROFIT' in p.get('exit_reason', '')]
        stop_losses = [p for p in exited_positions if 'STOP' in p.get('exit_reason', '')]
        
        exit_analysis['timing_patterns'] = {
            'd1_exits': {
                'count': len(d1_exits),
                'avg_pnl': np.mean([p.get('realized_pnl') or 0 for p in d1_exits]) if d1_exits else 0,
                'percentage': len(d1_exits) / len(exited_positions) * 100 if exited_positions else 0
            },
            'profit_takes': {
                'count': len(profit_takes),
                'avg_pnl': np.mean([p.get('realized_pnl') or 0 for p in profit_takes]) if profit_takes else 0,
                'percentage': len(profit_takes) / len(exited_positions) * 100 if exited_positions else 0
            },
            'stop_losses': {
                'count': len(stop_losses),
                'avg_pnl': np.mean([p.get('realized_pnl') or 0 for p in stop_losses]) if stop_losses else 0,
                'percentage': len(stop_losses) / len(exited_positions) * 100 if exited_positions else 0
            }
        }
        
        # Identify improvement opportunities
        d1_pct = exit_analysis['timing_patterns']['d1_exits']['percentage']
        if d1_pct > 70:
            exit_analysis['improvement_opportunities'].append({
                'issue': f'High D+1 exit rate ({d1_pct:.1f}%)',
                'recommendation': 'Implement dynamic exit timing with intraday profit optimization',
                'priority': 'MEDIUM',
                'implementation': 'Add momentum-based exit signals and trailing stops'
            })
        
        profit_take_pct = exit_analysis['timing_patterns']['profit_takes']['percentage']
        if profit_take_pct < 30:
            exit_analysis['improvement_opportunities'].append({
                'issue': f'Low profit-taking rate ({profit_take_pct:.1f}%)',
                'recommendation': 'Implement dynamic profit targets based on volatility and momentum',
                'priority': 'HIGH',
                'implementation': 'Add ATR-based profit targets and momentum confirmation'
            })
        
        return exit_analysis
    
    def _analyze_position_sizing_efficiency(self) -> Dict[str, Any]:
        """Analyze position sizing patterns and identify optimization opportunities"""
        all_positions = [p for p in self.positions if p.get('position_size_dollars')]
        
        sizing_analysis = {
            'current_patterns': {},
            'efficiency_metrics': {},
            'improvement_opportunities': []
        }
        
        if not all_positions:
            return sizing_analysis
        
        position_sizes = [p['position_size_dollars'] for p in all_positions]
        
        sizing_analysis['current_patterns'] = {
            'avg_position_size': np.mean(position_sizes),
            'min_position_size': min(position_sizes),
            'max_position_size': max(position_sizes),
            'position_size_std': np.std(position_sizes),
            'size_range_ratio': max(position_sizes) / min(position_sizes) if min(position_sizes) > 0 else 0
        }
        
        # Analyze size vs performance correlation
        exited_with_size = [p for p in all_positions if p.get('status') == 'exited' and p.get('realized_pnl') is not None]
        
        if len(exited_with_size) > 5:
            sizes = [p['position_size_dollars'] for p in exited_with_size]
            pnls = [p.get('realized_pnl') or 0 for p in exited_with_size]
            returns = [pnl/size for pnl, size in zip(pnls, sizes)]
            
            # Calculate correlation between size and returns
            correlation = np.corrcoef(sizes, returns)[0, 1] if len(sizes) > 1 else 0
            
            sizing_analysis['efficiency_metrics'] = {
                'size_return_correlation': correlation,
                'avg_return_pct': np.mean(returns) * 100,
                'best_size_quartile_return': np.mean(sorted(returns)[-len(returns)//4:]) * 100 if len(returns) >= 4 else 0
            }
            
            # Identify improvement opportunities
            if abs(correlation) < 0.1:
                sizing_analysis['improvement_opportunities'].append({
                    'issue': 'Position sizing not correlated with performance',
                    'recommendation': 'Implement confidence-based position sizing',
                    'priority': 'MEDIUM',
                    'implementation': 'Scale position sizes based on signal confidence and volatility'
                })
            
            size_range = sizing_analysis['current_patterns']['size_range_ratio']
            if size_range > 10:
                sizing_analysis['improvement_opportunities'].append({
                    'issue': f'High position size variation (ratio: {size_range:.1f})',
                    'recommendation': 'Standardize position sizing methodology',
                    'priority': 'LOW',
                    'implementation': 'Use consistent risk-based position sizing'
                })
        
        return sizing_analysis
    
    def _analyze_risk_management_effectiveness(self) -> Dict[str, Any]:
        """Analyze risk management effectiveness and identify improvements"""
        all_positions = [p for p in self.positions if p.get('position_size_dollars')]
        exited_positions = [p for p in all_positions if p.get('status') == 'exited']
        
        risk_analysis = {
            'current_metrics': {},
            'loss_patterns': {},
            'improvement_opportunities': []
        }
        
        if not exited_positions:
            return risk_analysis
        
        pnls = [p.get('realized_pnl') or 0 for p in exited_positions]
        losses = [pnl for pnl in pnls if pnl < 0]
        
        risk_analysis['current_metrics'] = {
            'max_loss': min(losses) if losses else 0,
            'avg_loss': np.mean(losses) if losses else 0,
            'loss_frequency': len(losses) / len(exited_positions) * 100 if exited_positions else 0,
            'large_loss_count': len([l for l in losses if l < -500]),  # Losses > $500
            'total_losses': sum(losses) if losses else 0
        }
        
        # Analyze loss patterns
        stop_loss_exits = [p for p in exited_positions if 'STOP' in p.get('exit_reason', '')]
        large_losses = [p for p in exited_positions if (p.get('realized_pnl') or 0) < -500]
        
        risk_analysis['loss_patterns'] = {
            'stop_loss_effectiveness': {
                'count': len(stop_loss_exits),
                'avg_loss': np.mean([p.get('realized_pnl') or 0 for p in stop_loss_exits]) if stop_loss_exits else 0,
                'percentage_of_exits': len(stop_loss_exits) / len(exited_positions) * 100 if exited_positions else 0
            },
            'large_losses': {
                'count': len(large_losses),
                'symbols': [p.get('symbol') for p in large_losses],
                'avg_large_loss': np.mean([p.get('realized_pnl') or 0 for p in large_losses]) if large_losses else 0
            }
        }
        
        # Identify improvement opportunities
        max_loss = risk_analysis['current_metrics']['max_loss']
        if max_loss < -1000:
            risk_analysis['improvement_opportunities'].append({
                'issue': f'Large maximum loss (${abs(max_loss):,.2f})',
                'recommendation': 'Implement tighter stop losses and position size limits',
                'priority': 'HIGH',
                'implementation': 'Set maximum loss per trade to $500 and implement trailing stops'
            })
        
        stop_loss_pct = risk_analysis['loss_patterns']['stop_loss_effectiveness']['percentage_of_exits']
        if stop_loss_pct < 20:
            risk_analysis['improvement_opportunities'].append({
                'issue': f'Low stop loss usage ({stop_loss_pct:.1f}%)',
                'recommendation': 'Implement more aggressive stop loss management',
                'priority': 'MEDIUM',
                'implementation': 'Add trailing stops and volatility-based stop adjustments'
            })
        
        return risk_analysis
    
    def _analyze_symbol_selection_quality(self) -> Dict[str, Any]:
        """Analyze symbol selection effectiveness"""
        all_positions = [p for p in self.positions if p.get('symbol')]
        
        symbol_analysis = {
            'symbol_performance': {},
            'selection_metrics': {},
            'improvement_opportunities': []
        }
        
        # Group by symbol
        symbol_groups = {}
        for pos in all_positions:
            symbol = pos['symbol']
            if symbol not in symbol_groups:
                symbol_groups[symbol] = []
            symbol_groups[symbol].append(pos)
        
        # Analyze each symbol's performance
        for symbol, positions in symbol_groups.items():
            exited_positions = [p for p in positions if p.get('status') == 'exited']
            
            if exited_positions:
                pnls = [p.get('realized_pnl') or 0 for p in exited_positions]
                symbol_analysis['symbol_performance'][symbol] = {
                    'total_trades': len(exited_positions),
                    'total_pnl': sum(pnls),
                    'avg_pnl': np.mean(pnls),
                    'win_rate': len([p for p in pnls if p > 0]) / len(pnls) * 100,
                    'active_positions': len([p for p in positions if p.get('status') != 'exited'])
                }
        
        # Identify best and worst performers
        if symbol_analysis['symbol_performance']:
            sorted_symbols = sorted(
                symbol_analysis['symbol_performance'].items(),
                key=lambda x: x[1]['total_pnl'],
                reverse=True
            )
            
            symbol_analysis['selection_metrics'] = {
                'total_symbols_traded': len(symbol_groups),
                'best_performer': sorted_symbols[0] if sorted_symbols else None,
                'worst_performer': sorted_symbols[-1] if sorted_symbols else None,
                'profitable_symbols': len([s for s in sorted_symbols if s[1]['total_pnl'] > 0]),
                'unprofitable_symbols': len([s for s in sorted_symbols if s[1]['total_pnl'] < 0])
            }
            
            # Identify improvement opportunities
            profitable_pct = symbol_analysis['selection_metrics']['profitable_symbols'] / len(sorted_symbols) * 100
            if profitable_pct < 60:
                symbol_analysis['improvement_opportunities'].append({
                    'issue': f'Low profitable symbol rate ({profitable_pct:.1f}%)',
                    'recommendation': 'Improve symbol selection criteria and filtering',
                    'priority': 'HIGH',
                    'implementation': 'Add momentum and volume filters, sector rotation analysis'
                })
        
        return symbol_analysis
    
    def _analyze_market_timing_patterns(self) -> Dict[str, Any]:
        """Analyze market timing effectiveness"""
        all_positions = [p for p in self.positions if p.get('entry_date')]
        
        timing_analysis = {
            'entry_patterns': {},
            'time_based_performance': {},
            'improvement_opportunities': []
        }
        
        # Group by entry date
        date_groups = {}
        for pos in all_positions:
            entry_date = pos['entry_date']
            if entry_date not in date_groups:
                date_groups[entry_date] = []
            date_groups[entry_date].append(pos)
        
        # Analyze daily performance patterns
        daily_performance = {}
        for date_str, positions in date_groups.items():
            exited_positions = [p for p in positions if p.get('status') == 'exited']
            if exited_positions:
                pnls = [p.get('realized_pnl') or 0 for p in exited_positions]
                daily_performance[date_str] = {
                    'trades': len(exited_positions),
                    'total_pnl': sum(pnls),
                    'avg_pnl': np.mean(pnls),
                    'win_rate': len([p for p in pnls if p > 0]) / len(pnls) * 100
                }
        
        timing_analysis['entry_patterns'] = {
            'total_trading_days': len(date_groups),
            'daily_performance': daily_performance
        }
        
        # Identify patterns
        if daily_performance:
            best_day = max(daily_performance.items(), key=lambda x: x[1]['total_pnl'])
            worst_day = min(daily_performance.items(), key=lambda x: x[1]['total_pnl'])
            
            timing_analysis['time_based_performance'] = {
                'best_trading_day': best_day,
                'worst_trading_day': worst_day,
                'avg_daily_pnl': np.mean([d['total_pnl'] for d in daily_performance.values()]),
                'consistent_days': len([d for d in daily_performance.values() if d['total_pnl'] > 0])
            }
            
            # Improvement opportunities
            consistent_pct = timing_analysis['time_based_performance']['consistent_days'] / len(daily_performance) * 100
            if consistent_pct < 70:
                timing_analysis['improvement_opportunities'].append({
                    'issue': f'Inconsistent daily performance ({consistent_pct:.1f}% profitable days)',
                    'recommendation': 'Implement market regime detection and timing filters',
                    'priority': 'MEDIUM',
                    'implementation': 'Add VIX filtering, market breadth analysis, and regime-based position sizing'
                })
        
        return timing_analysis
    
    def generate_recommendations(self) -> List[Dict[str, Any]]:
        """Generate prioritized recommendations for strategic improvements"""
        analysis = self.analyze_strategic_opportunities()
        
        all_recommendations = []
        
        # Collect all improvement opportunities
        for category, data in analysis.items():
            if isinstance(data, dict) and 'improvement_opportunities' in data:
                for opp in data['improvement_opportunities']:
                    opp['category'] = category
                    all_recommendations.append(opp)
        
        # Sort by priority (HIGH > MEDIUM > LOW)
        priority_order = {'HIGH': 3, 'MEDIUM': 2, 'LOW': 1}
        all_recommendations.sort(key=lambda x: priority_order.get(x.get('priority', 'LOW'), 1), reverse=True)
        
        return all_recommendations
    
    def generate_improvement_report(self):
        """Generate comprehensive improvement analysis report"""
        print("="*80)
        print("⚡ STRATEGIC EFFICIENCY IMPROVEMENT ANALYSIS")
        print("="*80)
        
        analysis = self.analyze_strategic_opportunities()
        recommendations = self.generate_recommendations()
        
        print("\n📊 CURRENT PERFORMANCE ANALYSIS")
        print("-" * 50)
        
        # Win Rate Analysis
        if 'win_rate' in analysis:
            win_data = analysis['win_rate']
            print(f"Win Rate: {win_data.get('current_win_rate', 0):.1f}%")
            print(f"Profit Factor: {win_data.get('profit_factor', 0):.2f}")
            print(f"Average Win: ${win_data.get('avg_win', 0):.2f}")
            print(f"Average Loss: ${win_data.get('avg_loss', 0):.2f}")
        
        # Exit Timing Analysis
        if 'exit_timing' in analysis:
            exit_data = analysis['exit_timing']
            if 'timing_patterns' in exit_data:
                patterns = exit_data['timing_patterns']
                print(f"\nExit Timing Breakdown:")
                print(f"  D+1 Exits: {patterns.get('d1_exits', {}).get('percentage', 0):.1f}%")
                print(f"  Profit Takes: {patterns.get('profit_takes', {}).get('percentage', 0):.1f}%")
                print(f"  Stop Losses: {patterns.get('stop_losses', {}).get('percentage', 0):.1f}%")
        
        # Risk Management
        if 'risk_management' in analysis:
            risk_data = analysis['risk_management']
            if 'current_metrics' in risk_data:
                metrics = risk_data['current_metrics']
                print(f"\nRisk Metrics:")
                print(f"  Max Loss: ${metrics.get('max_loss', 0):.2f}")
                print(f"  Average Loss: ${metrics.get('avg_loss', 0):.2f}")
                print(f"  Large Losses (>$500): {metrics.get('large_loss_count', 0)}")
        
        print("\n⚡ PRIORITIZED IMPROVEMENT OPPORTUNITIES")
        print("-" * 50)
        
        if recommendations:
            for i, rec in enumerate(recommendations, 1):
                priority_emoji = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}
                emoji = priority_emoji.get(rec.get('priority', 'LOW'), "⚪")
                
                print(f"\n{i}. {emoji} {rec.get('priority', 'LOW')} PRIORITY")
                print(f"   Category: {rec.get('category', 'Unknown').replace('_', ' ').title()}")
                print(f"   Issue: {rec.get('issue', 'Not specified')}")
                print(f"   Recommendation: {rec.get('recommendation', 'Not specified')}")
                if 'implementation' in rec:
                    print(f"   Implementation: {rec['implementation']}")
        else:
            print("✅ No major improvement opportunities identified")
        
        print("\n🎯 TOP 3 STRATEGIC IMPROVEMENTS")
        print("-" * 50)
        
        top_3 = recommendations[:3] if len(recommendations) >= 3 else recommendations
        
        for i, rec in enumerate(top_3, 1):
            print(f"\n{i}. {rec.get('recommendation', 'Not specified')}")
            print(f"   Impact: {rec.get('priority', 'MEDIUM')} priority improvement")
            if 'implementation' in rec:
                print(f"   Action: {rec['implementation']}")
        
        print("\n" + "="*80)
        print("🚀 EFFICIENCY ANALYSIS COMPLETE")
        print("="*80)
        
        return analysis, recommendations

if __name__ == "__main__":
    analyzer = StrategyEfficiencyAnalyzer()
    analysis, recommendations = analyzer.generate_improvement_report()
#!/usr/bin/env python3
"""
Weekly Performance Analysis Tool
==============================

Analyzes bot performance for the week of October 6-8, 2025
Provides comprehensive metrics including profits, Sharpe ratio, drawdowns, and efficiency metrics.
"""

import json
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
from typing import Dict, List, Tuple
import math
import os
import sys

project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

class WeeklyPerformanceAnalyzer:
    def __init__(self, positions_file='positions.json'):
        self.positions_file = positions_file
        self.positions = []
        self.week_start = date(2025, 10, 6)  # Monday Oct 6
        self.week_end = date(2025, 10, 8)    # Current date
        
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
    
    def filter_weekly_positions(self) -> List[Dict]:
        """Filter positions for this week's activity"""
        weekly_positions = []
        
        for pos in self.positions:
            # Check entry date
            if 'entry_date' in pos:
                try:
                    entry_date = datetime.strptime(pos['entry_date'], '%Y-%m-%d').date()
                    if self.week_start <= entry_date <= self.week_end:
                        weekly_positions.append(pos)
                        continue
                except:
                    pass
            
            # Check exit date for positions closed this week
            if pos.get('status') == 'exited' and 'exit_date' in pos:
                try:
                    exit_date = datetime.strptime(pos['exit_date'], '%Y-%m-%d').date()
                    if self.week_start <= exit_date <= self.week_end:
                        weekly_positions.append(pos)
                except:
                    pass
        
        return weekly_positions
    
    def calculate_basic_metrics(self, weekly_positions: List[Dict]) -> Dict:
        """Calculate basic performance metrics"""
        metrics = {
            'total_trades': len(weekly_positions),
            'winning_trades': 0,
            'losing_trades': 0,
            'total_pnl': 0.0,
            'total_invested': 0.0,
            'max_position_size': 0.0,
            'min_position_size': float('inf'),
            'avg_position_size': 0.0
        }
        
        pnl_list = []
        position_sizes = []
        
        for pos in weekly_positions:
            # Position size
            pos_size = pos.get('position_size_dollars', 0.0)
            if pos_size > 0:
                position_sizes.append(pos_size)
                metrics['total_invested'] += pos_size
                metrics['max_position_size'] = max(metrics['max_position_size'], pos_size)
                metrics['min_position_size'] = min(metrics['min_position_size'], pos_size)
            
            # PnL for exited positions
            if pos.get('status') == 'exited':
                pnl = pos.get('realized_pnl', 0.0)
                pnl_list.append(pnl)
                metrics['total_pnl'] += pnl
                
                if pnl > 0:
                    metrics['winning_trades'] += 1
                else:
                    metrics['losing_trades'] += 1
        
        if position_sizes:
            metrics['avg_position_size'] = np.mean(position_sizes)
        
        if metrics['min_position_size'] == float('inf'):
            metrics['min_position_size'] = 0.0
        
        # Win rate
        total_closed = metrics['winning_trades'] + metrics['losing_trades']
        metrics['win_rate'] = (metrics['winning_trades'] / total_closed * 100) if total_closed > 0 else 0.0
        
        # Average win/loss
        winning_trades = [pnl for pnl in pnl_list if pnl > 0]
        losing_trades = [pnl for pnl in pnl_list if pnl < 0]
        
        metrics['avg_win'] = np.mean(winning_trades) if winning_trades else 0.0
        metrics['avg_loss'] = np.mean(losing_trades) if losing_trades else 0.0
        metrics['profit_factor'] = abs(sum(winning_trades) / sum(losing_trades)) if losing_trades else float('inf')
        
        return metrics, pnl_list
    
    def calculate_advanced_metrics(self, pnl_list: List[float], metrics: Dict) -> Dict:
        """Calculate advanced risk metrics"""
        advanced = {}
        
        if not pnl_list:
            return advanced
        
        # Sharpe Ratio (annualized, assuming daily returns)
        if len(pnl_list) > 1:
            daily_returns = np.array(pnl_list)
            mean_return = np.mean(daily_returns)
            std_return = np.std(daily_returns, ddof=1)
            
            if std_return > 0:
                # Annualized Sharpe (252 trading days)
                sharpe_ratio = (mean_return / std_return) * np.sqrt(252)
                advanced['sharpe_ratio'] = sharpe_ratio
            else:
                advanced['sharpe_ratio'] = 0.0
        else:
            advanced['sharpe_ratio'] = 0.0
        
        # Maximum Drawdown
        cumulative_pnl = np.cumsum(pnl_list)
        running_max = np.maximum.accumulate(cumulative_pnl)
        drawdown = cumulative_pnl - running_max
        max_drawdown = np.min(drawdown) if len(drawdown) > 0 else 0.0
        advanced['max_drawdown'] = max_drawdown
        
        # Sortino Ratio (downside deviation)
        negative_returns = [pnl for pnl in pnl_list if pnl < 0]
        if negative_returns:
            downside_deviation = np.std(negative_returns, ddof=1)
            if downside_deviation > 0:
                sortino_ratio = (np.mean(pnl_list) / downside_deviation) * np.sqrt(252)
                advanced['sortino_ratio'] = sortino_ratio
            else:
                advanced['sortino_ratio'] = 0.0
        else:
            advanced['sortino_ratio'] = float('inf')  # No negative returns
        
        # Calmar Ratio
        if max_drawdown < 0:
            annual_return = np.mean(pnl_list) * 252
            calmar_ratio = annual_return / abs(max_drawdown)
            advanced['calmar_ratio'] = calmar_ratio
        else:
            advanced['calmar_ratio'] = float('inf')
        
        # Return on Investment
        if metrics['total_invested'] > 0:
            roi_percent = (metrics['total_pnl'] / metrics['total_invested']) * 100
            advanced['roi_percent'] = roi_percent
        else:
            advanced['roi_percent'] = 0.0
        
        return advanced
    
    def analyze_efficiency(self, weekly_positions: List[Dict]) -> Dict:
        """Analyze trading efficiency metrics"""
        efficiency = {
            'symbols_traded': set(),
            'avg_hold_time': 0.0,
            'quick_exits': 0,  # Same day exits
            'strategic_exits': 0,  # D+1 exits
            'stop_loss_exits': 0,
            'profit_take_exits': 0
        }
        
        hold_times = []
        
        for pos in weekly_positions:
            symbol = pos.get('symbol', '')
            efficiency['symbols_traded'].add(symbol)
            
            # Analyze exit reasons
            exit_reason = pos.get('exit_reason', '') or ''
            if 'STOP' in exit_reason.upper():
                efficiency['stop_loss_exits'] += 1
            elif 'PROFIT' in exit_reason.upper() or 'TAKE' in exit_reason.upper():
                efficiency['profit_take_exits'] += 1
            elif 'D+1' in exit_reason.upper() or 'FORCE' in exit_reason.upper():
                efficiency['strategic_exits'] += 1
            
            # Calculate hold time
            if pos.get('status') == 'exited':
                try:
                    entry_date = datetime.strptime(pos['entry_date'], '%Y-%m-%d').date()
                    exit_date = datetime.strptime(pos['exit_date'], '%Y-%m-%d').date()
                    hold_days = (exit_date - entry_date).days
                    hold_times.append(hold_days)
                    
                    if hold_days == 0:
                        efficiency['quick_exits'] += 1
                except:
                    pass
        
        efficiency['symbols_traded'] = list(efficiency['symbols_traded'])
        efficiency['unique_symbols'] = len(efficiency['symbols_traded'])
        
        if hold_times:
            efficiency['avg_hold_time'] = np.mean(hold_times)
            efficiency['max_hold_time'] = max(hold_times)
            efficiency['min_hold_time'] = min(hold_times)
        
        return efficiency
    
    def generate_report(self):
        """Generate comprehensive weekly performance report"""
        print("="*80)
        print("📊 WEEKLY PERFORMANCE REPORT - October 6-8, 2025")
        print("="*80)
        
        if not self.load_positions():
            return
        
        # Filter this week's positions
        weekly_positions = self.filter_weekly_positions()
        print(f"📅 Analyzing {len(weekly_positions)} positions from this week")
        
        if not weekly_positions:
            print("⚠️ No trading activity found for this week")
            return
        
        # Calculate metrics
        basic_metrics, pnl_list = self.calculate_basic_metrics(weekly_positions)
        advanced_metrics = self.calculate_advanced_metrics(pnl_list, basic_metrics)
        efficiency_metrics = self.analyze_efficiency(weekly_positions)
        
        # Print Basic Performance
        print("\n📈 BASIC PERFORMANCE METRICS")
        print("-" * 50)
        print(f"Total Trades: {basic_metrics['total_trades']}")
        print(f"Closed Trades: {basic_metrics['winning_trades'] + basic_metrics['losing_trades']}")
        print(f"Winning Trades: {basic_metrics['winning_trades']}")
        print(f"Losing Trades: {basic_metrics['losing_trades']}")
        print(f"Win Rate: {basic_metrics['win_rate']:.1f}%")
        print(f"Total P&L: ${basic_metrics['total_pnl']:,.2f}")
        print(f"Average Win: ${basic_metrics['avg_win']:,.2f}")
        print(f"Average Loss: ${basic_metrics['avg_loss']:,.2f}")
        print(f"Profit Factor: {basic_metrics['profit_factor']:.2f}")
        
        # Print Risk Metrics
        print("\n⚖️ RISK METRICS")
        print("-" * 50)
        if 'sharpe_ratio' in advanced_metrics:
            print(f"Sharpe Ratio: {advanced_metrics['sharpe_ratio']:.2f}")
        if 'sortino_ratio' in advanced_metrics:
            sortino_str = f"{advanced_metrics['sortino_ratio']:.2f}" if advanced_metrics['sortino_ratio'] != float('inf') else "N/A (no negative returns)"
            print(f"Sortino Ratio: {sortino_str}")
        if 'max_drawdown' in advanced_metrics:
            print(f"Max Drawdown: ${advanced_metrics['max_drawdown']:,.2f}")
        if 'calmar_ratio' in advanced_metrics:
            calmar_str = f"{advanced_metrics['calmar_ratio']:.2f}" if advanced_metrics['calmar_ratio'] != float('inf') else "N/A"
            print(f"Calmar Ratio: {calmar_str}")
        if 'roi_percent' in advanced_metrics:
            print(f"ROI: {advanced_metrics['roi_percent']:.2f}%")
        
        # Print Position Sizing
        print("\n💰 POSITION SIZING")
        print("-" * 50)
        print(f"Total Capital Deployed: ${basic_metrics['total_invested']:,.2f}")
        print(f"Average Position Size: ${basic_metrics['avg_position_size']:,.2f}")
        print(f"Largest Position: ${basic_metrics['max_position_size']:,.2f}")
        print(f"Smallest Position: ${basic_metrics['min_position_size']:,.2f}")
        
        # Print Efficiency Metrics
        print("\n⚡ EFFICIENCY METRICS")
        print("-" * 50)
        print(f"Unique Symbols Traded: {efficiency_metrics['unique_symbols']}")
        print(f"Symbols: {', '.join(efficiency_metrics['symbols_traded'][:10])}")
        if 'avg_hold_time' in efficiency_metrics and efficiency_metrics['avg_hold_time'] > 0:
            print(f"Average Hold Time: {efficiency_metrics['avg_hold_time']:.1f} days")
            print(f"Max Hold Time: {efficiency_metrics.get('max_hold_time', 0)} days")
            print(f"Min Hold Time: {efficiency_metrics.get('min_hold_time', 0)} days")
        print(f"Quick Exits (same day): {efficiency_metrics['quick_exits']}")
        print(f"Strategic D+1 Exits: {efficiency_metrics['strategic_exits']}")
        print(f"Stop Loss Exits: {efficiency_metrics['stop_loss_exits']}")
        print(f"Profit Take Exits: {efficiency_metrics['profit_take_exits']}")
        
        # Current Portfolio Status
        print("\n📋 CURRENT PORTFOLIO STATUS")
        print("-" * 50)
        active_positions = [pos for pos in self.positions if pos.get('status') != 'exited']
        print(f"Active Positions: {len(active_positions)}")
        
        if active_positions:
            total_current_value = sum(pos.get('position_size_dollars', 0) for pos in active_positions)
            print(f"Current Portfolio Value: ${total_current_value:,.2f}")
            
            print("\nTop 5 Active Positions:")
            sorted_positions = sorted(active_positions, 
                                    key=lambda x: x.get('position_size_dollars', 0), 
                                    reverse=True)[:5]
            for i, pos in enumerate(sorted_positions, 1):
                symbol = pos.get('symbol', 'Unknown')
                shares = pos.get('position_size_shares', 0)
                value = pos.get('position_size_dollars', 0)
                entry_date = pos.get('entry_date', 'Unknown')
                print(f"  {i}. {symbol}: {shares} shares (${value:,.2f}) - Entered: {entry_date}")
        
        print("\n" + "="*80)
        print("📊 ANALYSIS COMPLETE")
        print("="*80)

if __name__ == "__main__":
    analyzer = WeeklyPerformanceAnalyzer()
    analyzer.generate_report()
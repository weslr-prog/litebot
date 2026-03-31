#!/usr/bin/env python3
"""
Deep analysis of backtest results to understand why tighter filters underperformed
"""

import json
import pandas as pd
from pathlib import Path

# Find latest backtest results
results_dir = Path('backtest/results')
json_files = sorted(results_dir.glob('backtest_summary_*.json'))
latest_json = json_files[-1]

print("="*75)
print("BACKTEST RESULTS DEEP ANALYSIS")
print("="*75)
print(f"\nAnalyzing: {latest_json.name}")
print()

# Load summary
with open(latest_json, 'r') as f:
    summary = json.load(f)

baseline = summary['baseline']
improved = summary['improved']

print("CONFIGURATION COMPARISON")
print("-"*75)
print(f"Baseline: {baseline['config_name']}")
print(f"Improved: {improved['config_name']}")
print()

print("TRADE COUNT ANALYSIS")
print("-"*75)
print(f"Baseline: {baseline['total_trades']} trades")
print(f"Improved: {improved['total_trades']} trades")
print(f"Reduction: {baseline['total_trades'] - improved['total_trades']} trades (-{(1 - improved['total_trades']/baseline['total_trades'])*100:.1f}%)")
print()

print("PERFORMANCE METRICS")
print("-"*75)
print(f"{'Metric':<20} {'Baseline':>15} {'Improved':>15} {'Change':>15}")
print("-"*75)

metrics_to_compare = [
    ('Total Return', 'total_return', '%'),
    ('Win Rate', 'win_rate', '%'),
    ('Win/Loss Ratio', 'win_loss_ratio', ':1'),
    ('Avg Win $', 'avg_win', '$'),
    ('Avg Loss $', 'avg_loss', '$'),
    ('Max Drawdown', 'max_drawdown', '%'),
    ('Sharpe Ratio', 'sharpe_ratio', ''),
]

for label, key, unit in metrics_to_compare:
    base_val = baseline[key]
    imp_val = improved[key]
    
    if unit == '%':
        base_str = f"{base_val*100:+.2f}%"
        imp_str = f"{imp_val*100:+.2f}%"
        change = imp_val - base_val
        change_str = f"{change*100:+.2f}%"
    elif unit == '$':
        base_str = f"${base_val:+.2f}"
        imp_str = f"${imp_val:+.2f}"
        change = imp_val - base_val
        change_str = f"${change:+.2f}"
    elif unit == ':1':
        base_str = f"{base_val:.2f}:1"
        imp_str = f"{imp_val:.2f}:1"
        change = imp_val - base_val
        change_str = f"{change:+.2f}"
    else:
        base_str = f"{base_val:.2f}"
        imp_str = f"{imp_val:.2f}"
        change = imp_val - base_val
        change_str = f"{change:+.2f}"
    
    print(f"{label:<20} {base_str:>15} {imp_str:>15} {change_str:>15}")

print()
print("="*75)
print("HYPOTHESIS: Why Did Tighter Filters Underperform?")
print("="*75)
print()
print("Possible Explanations:")
print()
print("1. TIMING ISSUE:")
print("   - 5% momentum filter may be too late (already ran up)")
print("   - Entering after big move = buying high, selling low next day")
print("   - 3.5% catches earlier momentum before overextension")
print()
print("2. SAMPLE BIAS:")
print("   - Test years (2017, 2018, 2020-2022) may favor looser filters")
print("   - Different market conditions than Nov 2025")
print("   - Historical != current market regime")
print()
print("3. D+1 EXIT PROBLEM:")
print("   - Exiting next day regardless of price action")
print("   - Tighter entry + forced D+1 exit = catching reversals")
print("   - Looser entry has more room to run by D+1")
print()
print("4. VOLUME FILTER ISSUE:")
print("   - 1.5x volume surge = extreme moves (often reversals)")
print("   - Extreme volume = capitulation/exhaustion")
print("   - Moderate volume (1.0-1.3x) = healthier trends")
print()

# Load trade details
baseline_trades_file = str(latest_json).replace('backtest_summary_', 'trades_baseline_').replace('.json', '.csv')
improved_trades_file = str(latest_json).replace('backtest_summary_', 'trades_improved_').replace('.json', '.csv')

if Path(baseline_trades_file).exists():
    baseline_trades = pd.read_csv(baseline_trades_file)
    improved_trades = pd.read_csv(improved_trades_file)
    
    print("="*75)
    print("TRADE MOMENTUM ANALYSIS")
    print("="*75)
    print()
    
    print("Baseline - Entry Momentum Distribution:")
    print(f"  Mean: {baseline_trades['entry_momentum'].mean()*100:.2f}%")
    print(f"  Median: {baseline_trades['entry_momentum'].median()*100:.2f}%")
    print(f"  25th percentile: {baseline_trades['entry_momentum'].quantile(0.25)*100:.2f}%")
    print(f"  75th percentile: {baseline_trades['entry_momentum'].quantile(0.75)*100:.2f}%")
    print()
    
    print("Improved - Entry Momentum Distribution:")
    print(f"  Mean: {improved_trades['entry_momentum'].mean()*100:.2f}%")
    print(f"  Median: {improved_trades['entry_momentum'].median()*100:.2f}%")
    print(f"  25th percentile: {improved_trades['entry_momentum'].quantile(0.25)*100:.2f}%")
    print(f"  75th percentile: {improved_trades['entry_momentum'].quantile(0.75)*100:.2f}%")
    print()
    
    # Analyze winning vs losing trades
    baseline_wins = baseline_trades[baseline_trades['pnl_pct'] > 0]
    baseline_losses = baseline_trades[baseline_trades['pnl_pct'] <= 0]
    improved_wins = improved_trades[improved_trades['pnl_pct'] > 0]
    improved_losses = improved_trades[improved_trades['pnl_pct'] <= 0]
    
    print("="*75)
    print("WINNERS vs LOSERS - Entry Momentum")
    print("="*75)
    print()
    
    print("Baseline:")
    print(f"  Winning trades avg momentum: {baseline_wins['entry_momentum'].mean()*100:.2f}%")
    print(f"  Losing trades avg momentum: {baseline_losses['entry_momentum'].mean()*100:.2f}%")
    print(f"  Difference: {(baseline_wins['entry_momentum'].mean() - baseline_losses['entry_momentum'].mean())*100:.2f}%")
    print()
    
    print("Improved:")
    print(f"  Winning trades avg momentum: {improved_wins['entry_momentum'].mean()*100:.2f}%")
    print(f"  Losing trades avg momentum: {improved_losses['entry_momentum'].mean()*100:.2f}%")
    print(f"  Difference: {(improved_wins['entry_momentum'].mean() - improved_losses['entry_momentum'].mean())*100:.2f}%")
    print()

print("="*75)
print("RECOMMENDATION")
print("="*75)
print()
print("The historical backtest suggests:")
print()
print("❌ DON'T use 5% momentum + 1.5x volume (underperformed baseline)")
print("   - Total return: -9% vs +35% baseline")
print("   - Lower win rate: 44.5% vs 45.2%")
print("   - Worse Sharpe ratio: -0.16 vs 0.30")
print()
print("NEXT STEPS:")
print()
print("1. Test intermediate thresholds:")
print("   - Try 4.0% or 4.5% momentum (between 3.5% and 5.0%)")
print("   - Try 1.25x or 1.3x volume (between 1.0x and 1.5x)")
print()
print("2. Analyze Nov 2025 week specifically:")
print("   - RIVN #2 (3.71% momentum) lost -11%")
print("   - Was this an anomaly or a pattern?")
print("   - Check if Nov market regime differs from 2017-2022")
print()
print("3. Consider different exit strategy:")
print("   - Maybe hold 2-3 days instead of D+1?")
print("   - Use trailing stop instead of fixed exit?")
print()
print("4. Focus on recent data:")
print("   - Backtest 2023-2024 (more relevant to current market)")
print("   - Use 3-6 month window instead of 5 years")
print()

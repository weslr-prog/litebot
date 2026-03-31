#!/usr/bin/env python3
"""
Comprehensive Backtest - Reconciliation Analysis Nov 19, 2025
Reconciling Nov 14 vs Nov 18 backtest results

Configurations to Test:
1. Nov 14 Winner: 3.5% momentum, 1.0x volume (best in 2023-2024)
2. Nov 18 Winner: 6.0% momentum, 1.25x volume (best Sharpe 2020-2024)
3. Current Nov 19: 5.5% momentum, 0.9x volume (current deployed)
4. Middle Ground: 4.5% momentum, 1.0x volume
5. Conservative: 5.0% momentum, 1.0x volume

Focus: Which parameters work best across ALL market periods?

Years to Test:
- Pre-COVID: 2017, 2018 (normal markets)
- COVID Era: 2020, 2021, 2022 (volatile periods)
- Recent: 2023, 2024 (current market regime)

Author: GitHub Copilot
Date: November 19, 2025 - Reconciliation Analysis
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backtest.strategy_backtest import BacktestConfig, StrategyBacktester, BacktestResults
from datetime import datetime
import json
import pandas as pd
from pathlib import Path

# Test configurations - Reconciling Nov 14 vs Nov 18 results
CONFIGS = [
    # Name, momentum, volume
    ("Nov 14 Winner (3.5%, 1.0x)", 0.035, 1.0),
    ("Nov 18 Winner (6.0%, 1.25x)", 0.060, 1.25),
    ("Current Nov 19 (5.5%, 0.9x)", 0.055, 0.9),
    ("Middle Ground (4.5%, 1.0x)", 0.045, 1.0),
    ("Conservative (5.0%, 1.0x)", 0.050, 1.0),
]

# Stocks to test - diverse mix of volatility profiles
SYMBOLS = [
    # High volatility momentum stocks
    'JBLU', 'AAL', 'PLUG', 'FCEL', 'GEVO',
    # Mid volatility
    'F', 'CCL', 'RCL', 'SBUX',
    # Lower volatility  
    'SIRI', 'CAKE',
    # Recent additions (if available)
    'VCYT', 'U'
]

def run_backtest_config(name: str, momentum: float, volume: float, years: list, label: str):
    """Run backtest for a single configuration"""
    print(f"\n{'='*75}")
    print(f"Testing: {name} - {label}")
    print(f"{'='*75}")
    print(f"Entry: {momentum*100:.2f}% momentum, {volume:.2f}x volume")
    print(f"Exit: Built-in D+1 strategy (smart zones)")
    print(f"Years: {', '.join(map(str, years))}")
    print()
    
    config = BacktestConfig(
        symbols=SYMBOLS,
        years=years,
        data_source='alpaca',  # Use Alpaca (will use cache if available)
        cache_dir='backtest/cache'
    )
    
    backtester = StrategyBacktester(config)
    result = backtester.run_full_backtest(name, momentum, volume)
    
    # Print summary with risk/reward analysis
    print(f"\nResults for {name}:")
    print(f"  Total Return: {result.total_return*100:+.2f}%")
    print(f"  Total Trades: {result.total_trades}")
    print(f"  Win Rate: {result.win_rate*100:.1f}%")
    print(f"  Win/Loss Ratio: {result.win_loss_ratio:.2f}:1")
    print(f"  Avg Win: ${result.avg_win:+.2f}")
    print(f"  Avg Loss: ${result.avg_loss:+.2f}")
    
    if result.avg_loss != 0:
        risk_reward = abs(result.avg_win / result.avg_loss)
        print(f"  Risk/Reward: {risk_reward:.2f}x")
    
    print(f"  Sharpe Ratio: {result.sharpe_ratio:.2f}")
    
    # Signal quality indicator
    if result.win_rate >= 0.35 and result.win_loss_ratio >= 1.3:
        print(f"  ✅ High quality signals")
    elif result.win_rate >= 0.25 and result.win_loss_ratio >= 1.0:
        print(f"  ⚠️  Acceptable quality")
    else:
        print(f"  ❌ Poor signal quality")
    
    return result

def main():
    print("="*75)
    print("COMPREHENSIVE BACKTEST ANALYSIS - RECONCILIATION")
    print("="*75)
    print(f"Stocks: {', '.join(SYMBOLS)}")
    print(f"Configurations: {len(CONFIGS)}")
    print()
    
    # Store all results
    pre_covid_results = {}
    historical_results = {}
    recent_results = {}
    
    # Test each configuration on pre-COVID data
    print("\n" + "="*75)
    print("PHASE 1: PRE-COVID DATA (2017, 2018)")
    print("="*75)
    
    pre_covid_years = [2017, 2018]
    for name, momentum, volume in CONFIGS:
        result = run_backtest_config(name, momentum, volume, pre_covid_years, "Pre-COVID")
        pre_covid_results[name] = result
    
    # Test each configuration on historical data
    print("\n" + "="*75)
    print("PHASE 2: COVID ERA DATA (2020, 2021, 2022)")
    print("="*75)
    
    historical_years = [2020, 2021, 2022]
    for name, momentum, volume in CONFIGS:
        result = run_backtest_config(name, momentum, volume, historical_years, "COVID Era")
        historical_results[name] = result
    
    # Test each configuration on recent data
    print("\n" + "="*75)
    print("PHASE 3: RECENT DATA (2023, 2024)")
    print("="*75)
    
    recent_years = [2023, 2024]
    for name, momentum, volume in CONFIGS:
        result = run_backtest_config(name, momentum, volume, recent_years, "Recent")
        recent_results[name] = result
    
    # Generate comparison report
    print("\n" + "="*75)
    print("PRE-COVID COMPARISON (2017-2018) - NORMAL MARKETS")
    print("="*75)
    print()
    print(f"{'Configuration':<45} {'Return':>10} {'Trades':>8} {'Win%':>8} {'W/L':>8} {'R/R':>8} {'Sharpe':>8}")
    print("-"*105)
    
    # Sort by Sharpe ratio
    sorted_pre_covid = sorted(pre_covid_results.items(), key=lambda x: x[1].sharpe_ratio, reverse=True)
    for name, result in sorted_pre_covid:
        rr = abs(result.avg_win / result.avg_loss) if result.avg_loss != 0 else 0
        print(f"{name:<45} {result.total_return*100:>9.2f}% {result.total_trades:>8} {result.win_rate*100:>7.1f}% {result.win_loss_ratio:>7.2f} {rr:>7.2f} {result.sharpe_ratio:>8.2f}")
    
    print("\n" + "="*75)
    print("COVID ERA COMPARISON (2020-2022) - VOLATILE MARKETS")
    print("="*75)
    print()
    print(f"{'Configuration':<45} {'Return':>10} {'Trades':>8} {'Win%':>8} {'W/L':>8} {'R/R':>8} {'Sharpe':>8}")
    print("-"*105)
    
    # Sort by Sharpe ratio
    sorted_historical = sorted(historical_results.items(), key=lambda x: x[1].sharpe_ratio, reverse=True)
    for name, result in sorted_historical:
        rr = abs(result.avg_win / result.avg_loss) if result.avg_loss != 0 else 0
        print(f"{name:<45} {result.total_return*100:>9.2f}% {result.total_trades:>8} {result.win_rate*100:>7.1f}% {result.win_loss_ratio:>7.2f} {rr:>7.2f} {result.sharpe_ratio:>8.2f}")
    
    print("\n" + "="*75)
    print("RECENT DATA COMPARISON (2023-2024) - CURRENT MARKET")
    print("="*75)
    print()
    print(f"{'Configuration':<45} {'Return':>10} {'Trades':>8} {'Win%':>8} {'W/L':>8} {'R/R':>8} {'Sharpe':>8}")
    print("-"*90)
    
    # Sort by Sharpe ratio
    sorted_recent = sorted(recent_results.items(), key=lambda x: x[1].sharpe_ratio, reverse=True)
    for name, result in sorted_recent:
        rr = abs(result.avg_win / result.avg_loss) if result.avg_loss != 0 else 0
        print(f"{name:<45} {result.total_return*100:>9.2f}% {result.total_trades:>8} {result.win_rate*100:>7.1f}% {result.win_loss_ratio:>7.2f} {rr:>7.2f} {result.sharpe_ratio:>8.2f}")
    
    # Combined analysis
    print("\n" + "="*75)
    print("COMBINED ANALYSIS - Signal Quality Focus")
    print("="*75)
    print()
    
    for name in [n for n, _, _ in CONFIGS]:
        hist = historical_results[name]
        recent = recent_results[name]
        
        print(f"\n{name}:")
        print(f"  Historical (2020-2022): {hist.total_return*100:+.2f}% ({hist.total_trades} trades, {hist.win_rate*100:.1f}% win rate)")
        print(f"  Recent (2023-2024):     {recent.total_return*100:+.2f}% ({recent.total_trades} trades, {recent.win_rate*100:.1f}% win rate)")
        
        if hist.total_trades > 0 and recent.total_trades > 0:
            hist_rr = abs(hist.avg_win / hist.avg_loss) if hist.avg_loss != 0 else 0
            recent_rr = abs(recent.avg_win / recent.avg_loss) if recent.avg_loss != 0 else 0
            
            print(f"  Historical R/R: {hist_rr:.2f}x, Recent R/R: {recent_rr:.2f}x")
            
            # Signal quality assessment
            hist_quality = hist.win_rate >= 0.30 and hist_rr >= 1.2
            recent_quality = recent.win_rate >= 0.30 and recent_rr >= 1.2
            
            if hist_quality and recent_quality:
                print(f"  ✅ Consistent quality signals across periods")
            elif recent_quality:
                print(f"  ⚠️  Quality improved in recent market")
            elif hist_quality:
                print(f"  ⚠️  Quality degraded in recent market")
            else:
                print(f"  ❌ Signal quality needs improvement")
    
    # Find best configuration
    print("\n" + "="*75)
    print("RECOMMENDATIONS - Pre-Filter & Signal Quality Analysis")
    print("="*75)
    print()
    
    best_historical = sorted_historical[0]
    best_recent = sorted_recent[0]
    
    print(f"Best Historical by Sharpe (2020-2022): {best_historical[0]}")
    print(f"  Return: {best_historical[1].total_return*100:+.2f}%")
    print(f"  Win Rate: {best_historical[1].win_rate*100:.1f}%")
    print(f"  Risk/Reward: {abs(best_historical[1].avg_win / best_historical[1].avg_loss):.2f}x")
    print(f"  Sharpe: {best_historical[1].sharpe_ratio:.2f}")
    print()
    
    print(f"Best Recent by Sharpe (2023-2024): {best_recent[0]}")
    print(f"  Return: {best_recent[1].total_return*100:+.2f}%")
    print(f"  Win Rate: {best_recent[1].win_rate*100:.1f}%")
    print(f"  Risk/Reward: {abs(best_recent[1].avg_win / best_recent[1].avg_loss):.2f}x")
    print(f"  Sharpe: {best_recent[1].sharpe_ratio:.2f}")
    print()
    
    if best_historical[0] == best_recent[0]:
        print(f"✅ CONSISTENT WINNER: {best_historical[0]}")
        print("   This configuration produces quality signals in both periods")
        print("   RECOMMENDATION: Use this configuration")
    else:
        print(f"⚠️  DIFFERENT WINNERS ACROSS PERIODS")
        print(f"   Historical best: {best_historical[0]}")
        print(f"   Recent best: {best_recent[0]}")
        print(f"   RECOMMENDATION: Favor recent winner for current market conditions")
    
    # Additional quality analysis
    print("\n" + "="*75)
    print("SIGNAL QUALITY RANKINGS (Combined Periods)")
    print("="*75)
    print()
    
    # Score based on win rate + risk/reward + sharpe
    quality_scores = {}
    for name, _, _ in CONFIGS:
        hist = historical_results[name]
        recent = recent_results[name]
        
        # Weight recent more (60/40)
        combined_win_rate = (hist.win_rate * 0.4) + (recent.win_rate * 0.6)
        hist_rr = abs(hist.avg_win / hist.avg_loss) if hist.avg_loss != 0 else 0
        recent_rr = abs(recent.avg_win / recent.avg_loss) if recent.avg_loss != 0 else 0
        combined_rr = (hist_rr * 0.4) + (recent_rr * 0.6)
        combined_sharpe = (hist.sharpe_ratio * 0.4) + (recent.sharpe_ratio * 0.6)
        
        # Quality score: win_rate + normalized_rr + sharpe
        quality_score = combined_win_rate + (combined_rr / 3.0) + (combined_sharpe / 2.0)
        quality_scores[name] = {
            'score': quality_score,
            'win_rate': combined_win_rate,
            'rr': combined_rr,
            'sharpe': combined_sharpe
        }
    
    ranked = sorted(quality_scores.items(), key=lambda x: x[1]['score'], reverse=True)
    
    print(f"{'Rank':<6} {'Configuration':<45} {'Quality':>10} {'Win%':>8} {'R/R':>8} {'Sharpe':>8}")
    print("-"*90)
    
    for i, (name, scores) in enumerate(ranked, 1):
        print(f"{i:<6} {name:<45} {scores['score']:>10.3f} {scores['win_rate']*100:>7.1f}% {scores['rr']:>7.2f} {scores['sharpe']:>8.2f}")
    
    print(f"\n✅ TOP RECOMMENDATION: {ranked[0][0]}")
    print(f"   Quality Score: {ranked[0][1]['score']:.3f}")
    print(f"   This configuration provides the best balance of:")
    print(f"   - Win rate: {ranked[0][1]['win_rate']*100:.1f}%")
    print(f"   - Risk/Reward: {ranked[0][1]['rr']:.2f}x")
    print(f"   - Risk-adjusted returns (Sharpe): {ranked[0][1]['sharpe']:.2f}")
    
    # Save results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    results_file = f"backtest/results/comprehensive_backtest_{timestamp}.json"
    
    results_data = {
        'timestamp': timestamp,
        'focus': 'Pre-filter quality and signal clarity - Nov 18 parameters',
        'configurations': [
            {
                'name': name,
                'momentum': momentum,
                'volume': volume
            }
            for name, momentum, volume in CONFIGS
        ],
        'historical': {
            name: {
                'total_return': result.total_return,
                'total_trades': result.total_trades,
                'win_rate': result.win_rate,
                'win_loss_ratio': result.win_loss_ratio,
                'sharpe_ratio': result.sharpe_ratio,
                'avg_win': result.avg_win,
                'avg_loss': result.avg_loss
            }
            for name, result in historical_results.items()
        },
        'recent': {
            name: {
                'total_return': result.total_return,
                'total_trades': result.total_trades,
                'win_rate': result.win_rate,
                'win_loss_ratio': result.win_loss_ratio,
                'sharpe_ratio': result.sharpe_ratio,
                'avg_win': result.avg_win,
                'avg_loss': result.avg_loss
            }
            for name, result in recent_results.items()
        }
    }
    
    Path(results_file).parent.mkdir(parents=True, exist_ok=True)
    with open(results_file, 'w') as f:
        json.dump(results_data, f, indent=2)
    
    print(f"\n✅ Results saved to: {results_file}")
    print("\n" + "="*75)
    print("BACKTEST COMPLETE")
    print("="*75)

if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
Run comprehensive backtest TWICE:
1. Full 14 years (2011-2024) INCLUDING 2020
2. 13 years (2011-2024) EXCLUDING 2020

This allows us to see the impact of COVID volatility on strategy performance.
"""

import sys
sys.path.insert(0, '/home/wes/Desktop/litebotx-usb-deployment')

from backtest.comprehensive_strategy_backtest import (
    BacktestConfig, BacktestPhase, StrategyConfig,
    ComprehensiveBacktestRunner
)
from pathlib import Path
import pandas as pd
from datetime import datetime

def run_with_2020():
    """Run backtest INCLUDING 2020 (COVID year)"""
    print("="*70)
    print("BACKTEST #1: 14 YEARS INCLUDING 2020 (COVID)")
    print("="*70)
    print()
    
    config = BacktestConfig(
        symbols=['JBLU', 'AAL', 'CCL', 'RCL', 'F', 'GEVO', 'PLUG', 'FCEL', 'SBUX', 'SIRI', 'CAKE'],
        phases=[
            BacktestPhase('In-Sample', 2011, 2016, 'Training period'),
            BacktestPhase('Validation', 2017, 2019, 'Overfitting check'),
            BacktestPhase('Out-of-Sample', 2020, 2024, 'Real-world with COVID')
        ],
        results_dir='backtest/results/with_2020'
    )
    
    # Top 3 strategies from optimization
    strategies = [
        StrategyConfig(
            name='Mean_Reversion_RSI_2852',
            test_id=2852,
            strategy_type='mean_reversion_rsi',
            rsi_period=7,
            oversold_threshold=20.0,
            overbought_threshold=80.0,
            exit_rsi_level=50.0,
            exit_strategy='rsi_neutral',
            profit_target_pct=0.02,
            stop_loss_pct=-0.02,
            max_hold_days=5,
            min_volume_surge=1.5
        ),
        StrategyConfig(
            name='Mean_Reversion_RSI_3831',
            test_id=3831,
            strategy_type='mean_reversion_rsi',
            rsi_period=21,
            oversold_threshold=25.0,
            overbought_threshold=80.0,
            exit_rsi_level=80.0,
            exit_strategy='rsi_opposite',
            profit_target_pct=0.03,
            stop_loss_pct=-0.02,
            max_hold_days=5,
            min_volume_surge=1.5
        ),
        StrategyConfig(
            name='Hybrid_4872',
            test_id=4872,
            strategy_type='hybrid',
            rsi_period=14,
            oversold_threshold=30.0,
            overbought_threshold=70.0,
            exit_strategy='profit_target',
            profit_target_pct=0.025,
            stop_loss_pct=-0.02,
            max_hold_days=5,
            min_volume_surge=1.5,
            min_momentum_pct=0.03
        )
    ]
    
    backtester = ComprehensiveBacktestRunner(config)
    results_with = backtester.run(strategies)
    
    return results_with


def run_without_2020():
    """Run backtest EXCLUDING 2020 (skip COVID year)"""
    print("="*70)
    print("BACKTEST #2: 13 YEARS EXCLUDING 2020 (NO COVID)")
    print("="*70)
    print()
    
    config = BacktestConfig(
        symbols=['JBLU', 'AAL', 'CCL', 'RCL', 'F', 'GEVO', 'PLUG', 'FCEL', 'SBUX', 'SIRI', 'CAKE'],
        phases=[
            BacktestPhase('In-Sample', 2011, 2016, 'Training period'),
            BacktestPhase('Validation', 2017, 2019, 'Overfitting check'),
            BacktestPhase('Out-of-Sample', 2021, 2024, 'Real-world WITHOUT COVID')
        ],
        results_dir='backtest/results/without_2020'
    )
    
    # Same top 3 strategies
    strategies = [
        StrategyConfig(
            name='Mean_Reversion_RSI_2852',
            test_id=2852,
            strategy_type='mean_reversion_rsi',
            rsi_period=7,
            oversold_threshold=20.0,
            overbought_threshold=80.0,
            exit_rsi_level=50.0,
            exit_strategy='rsi_neutral',
            profit_target_pct=0.02,
            stop_loss_pct=-0.02,
            max_hold_days=5,
            min_volume_surge=1.5
        ),
        StrategyConfig(
            name='Mean_Reversion_RSI_3831',
            test_id=3831,
            strategy_type='mean_reversion_rsi',
            rsi_period=21,
            oversold_threshold=25.0,
            overbought_threshold=80.0,
            exit_rsi_level=80.0,
            exit_strategy='rsi_opposite',
            profit_target_pct=0.03,
            stop_loss_pct=-0.02,
            max_hold_days=5,
            min_volume_surge=1.5
        ),
        StrategyConfig(
            name='Hybrid_4872',
            test_id=4872,
            strategy_type='hybrid',
            rsi_period=14,
            oversold_threshold=30.0,
            overbought_threshold=70.0,
            exit_strategy='profit_target',
            profit_target_pct=0.025,
            stop_loss_pct=-0.02,
            max_hold_days=5,
            min_volume_surge=1.5,
            min_momentum_pct=0.03
        )
    ]
    
    backtester = ComprehensiveBacktestRunner(config)
    results_without = backtester.run(strategies)
    
    return results_without


def compare_results(results_with, results_without):
    """Compare results with and without 2020"""
    print("\n" + "="*70)
    print("COMPARISON: WITH vs WITHOUT 2020")
    print("="*70)
    print()
    
    # For each strategy
    for strategy_name in ['Mean_Reversion_RSI_2852', 'Mean_Reversion_RSI_3831', 'Hybrid_4872']:
        print(f"\n{'='*70}")
        print(f"STRATEGY: {strategy_name}")
        print(f"{'='*70}\n")
        
        # Compare Out-of-Sample phase (the one that changed)
        phase = 'Out-of-Sample'
        
        if strategy_name in results_with and strategy_name in results_without:
            with_result = results_with[strategy_name].get(phase)
            without_result = results_without[strategy_name].get(phase)
            
            if with_result and without_result:
                print(f"📊 OUT-OF-SAMPLE COMPARISON:\n")
                
                print(f"WITH 2020 (2020-2024):")
                print(f"  Total Return: {with_result.total_return:.2f}%")
                print(f"  Win Rate: {with_result.win_rate:.1f}%")
                print(f"  Total Trades: {with_result.total_trades}")
                print(f"  Sharpe Ratio: {with_result.sharpe_ratio:.2f}")
                print(f"  Max Drawdown: {with_result.max_drawdown:.2f}%")
                print()
                
                print(f"WITHOUT 2020 (2021-2024):")
                print(f"  Total Return: {without_result.total_return:.2f}%")
                print(f"  Win Rate: {without_result.win_rate:.1f}%")
                print(f"  Total Trades: {without_result.total_trades}")
                print(f"  Sharpe Ratio: {without_result.sharpe_ratio:.2f}")
                print(f"  Max Drawdown: {without_result.max_drawdown:.2f}%")
                print()
                
                # Calculate impact
                return_diff = without_result.total_return - with_result.total_return
                wr_diff = without_result.win_rate - with_result.win_rate
                
                print(f"💡 COVID IMPACT:")
                print(f"  Return difference: {return_diff:+.2f}% ({'better' if return_diff > 0 else 'worse'} without 2020)")
                print(f"  Win rate difference: {wr_diff:+.1f}% ({'better' if wr_diff > 0 else 'worse'} without 2020)")
                
                if abs(return_diff) < 5:
                    print(f"  ✅ STABLE: Strategy performs similarly with/without COVID")
                elif return_diff > 0:
                    print(f"  ⚠️ COVID DRAG: 2020 reduced returns by {abs(return_diff):.1f}%")
                else:
                    print(f"  📈 COVID BOOST: 2020 increased returns by {abs(return_diff):.1f}%")
                print()


def save_comparison_report(results_with, results_without):
    """Save comparison to file"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_path = f'backtest/results/covid_impact_comparison_{timestamp}.txt'
    
    with open(report_path, 'w') as f:
        f.write("="*70 + "\n")
        f.write("BACKTEST COMPARISON: WITH vs WITHOUT 2020 (COVID IMPACT ANALYSIS)\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("="*70 + "\n\n")
        
        for strategy_name in ['Mean_Reversion_RSI_2852', 'Mean_Reversion_RSI_3831', 'Hybrid_4872']:
            f.write(f"\n{'='*70}\n")
            f.write(f"STRATEGY: {strategy_name}\n")
            f.write(f"{'='*70}\n\n")
            
            if strategy_name in results_with and strategy_name in results_without:
                # Write all phases
                for phase_name in ['In-Sample', 'Validation', 'Out-of-Sample']:
                    f.write(f"\n{phase_name.upper()}:\n")
                    f.write("-" * 40 + "\n")
                    
                    with_result = results_with[strategy_name].get(phase_name)
                    without_result = results_without[strategy_name].get(phase_name)
                    
                    if with_result:
                        f.write(f"WITH 2020:\n")
                        f.write(f"  Return: {with_result.total_return:.2f}%\n")
                        f.write(f"  Win Rate: {with_result.win_rate:.1f}%\n")
                        f.write(f"  Trades: {with_result.total_trades}\n")
                        f.write(f"  Sharpe: {with_result.sharpe_ratio:.2f}\n\n")
                    
                    if without_result and phase_name == 'Out-of-Sample':
                        f.write(f"WITHOUT 2020:\n")
                        f.write(f"  Return: {without_result.total_return:.2f}%\n")
                        f.write(f"  Win Rate: {without_result.win_rate:.1f}%\n")
                        f.write(f"  Trades: {without_result.total_trades}\n")
                        f.write(f"  Sharpe: {without_result.sharpe_ratio:.2f}\n\n")
    
    print(f"\n✅ Comparison report saved to: {report_path}")
    return report_path


if __name__ == '__main__':
    print("\n" + "="*70)
    print("COMPREHENSIVE BACKTEST: WITH AND WITHOUT 2020")
    print("Testing Mean Reversion RSI Strategy on 14 Years of Real Data")
    print("="*70)
    print()
    print("This will run TWO complete backtests:")
    print("  1. 2011-2024 INCLUDING 2020 (COVID volatility)")
    print("  2. 2011-2019, 2021-2024 EXCLUDING 2020")
    print()
    print("Expected runtime: 20-40 minutes total")
    print()
    
    # Run both backtests
    results_with = run_with_2020()
    print("\n" + "✅ Backtest #1 complete!\n")
    
    results_without = run_without_2020()
    print("\n" + "✅ Backtest #2 complete!\n")
    
    # Compare results
    compare_results(results_with, results_without)
    
    # Save comparison report
    save_comparison_report(results_with, results_without)
    
    print("\n" + "="*70)
    print("🎉 ALL BACKTESTS COMPLETE!")
    print("="*70)
    print()
    print("Results saved to:")
    print("  - backtest/results/with_2020/")
    print("  - backtest/results/without_2020/")
    print()
    print("Next steps:")
    print("  1. Review comparison report")
    print("  2. Check if strategy is stable with/without COVID")
    print("  3. Decide on deployment based on Out-of-Sample results")
    print()

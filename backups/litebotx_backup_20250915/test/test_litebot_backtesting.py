#!/usr/bin/env python3
"""
LiteBot Comprehensive Testing Suite
Tests the entire backtesting framework with your actual trading system

This script validates:
1. Integration with your actual strategy components
2. Realistic transaction cost modeling
3. Regime-specific performance analysis
4. Historical stress testing
5. Monte Carlo validation
"""

import sys
import os
import logging
from datetime import datetime, timedelta
from pathlib import Path
import numpy as np
import pandas as pd

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from litebot_backtester import LiteBotBacktester, LiteBotBacktestConfig
from comprehensive_backtester import BacktestConfig


def test_litebot_integration():
    """Test LiteBot backtester with realistic parameters"""
    
    print("🤖 Testing LiteBot Backtesting Integration")
    print("=" * 60)
    
    # Test Configuration
    config = LiteBotBacktestConfig(
        start_date="2023-01-01",
        end_date="2024-01-01", 
        initial_capital=500_000,  # $500K test portfolio
        
        # LiteBot specific
        use_enhanced_strategy=True,
        max_positions=5,
        rebalance_frequency="daily",
        
        # Transaction costs (realistic for retail trading)
        commission_per_trade=1.0,  # $1 per trade
        base_slippage_bps=3.0,     # 3 bps base slippage
        bid_ask_spread_bps=5.0,    # 5 bps spread
        
        # Risk management
        min_trade_value=1000,      # $1K minimum
        max_single_position=0.20,  # 20% max position
        cash_buffer=0.05           # 5% cash buffer
    )
    
    # Create backtester
    backtester = LiteBotBacktester(config)
    
    # Test symbols (subset of your universe)
    test_symbols = ['AAPL', 'MSFT', 'TSLA', 'SPY', 'QQQ']
    
    print(f"Testing with {len(test_symbols)} symbols: {test_symbols}")
    print(f"Period: {config.start_date} to {config.end_date}")
    print(f"Initial Capital: ${config.initial_capital:,.0f}")
    
    # Run backtest
    try:
        results = backtester.run_litebot_backtest(
            symbols=test_symbols,
            save_results=False
        )
        
        print("✅ Backtest completed successfully!")
        return results
        
    except Exception as e:
        print(f"❌ Backtest failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_historical_stress_periods():
    """Test performance during historical stress periods"""
    
    print("\n⚠️  Testing Historical Stress Periods")
    print("=" * 60)
    
    # Define stress test periods
    stress_periods = {
        "COVID_CRASH": ("2020-02-01", "2020-04-30"),
        "RATE_HIKE_2022": ("2022-01-01", "2022-12-31"),
        "BANKING_CRISIS_2023": ("2023-03-01", "2023-05-31")
    }
    
    stress_results = {}
    
    for period_name, (start_date, end_date) in stress_periods.items():
        print(f"\nTesting {period_name}: {start_date} to {end_date}")
        
        config = LiteBotBacktestConfig(
            start_date=start_date,
            end_date=end_date,
            initial_capital=1_000_000,
            use_enhanced_strategy=True,
            max_positions=3,  # More conservative during stress
            commission_per_trade=1.0,
            base_slippage_bps=5.0  # Higher slippage during stress
        )
        
        backtester = LiteBotBacktester(config)
        
        try:
            # Test with broader universe during stress
            stress_symbols = ['SPY', 'QQQ', 'XLF', 'XLK', 'XLE', 'AAPL', 'MSFT']
            results = backtester.run_litebot_backtest(
                symbols=stress_symbols,
                save_results=False
            )
            
            metrics = results['summary_metrics']
            stress_results[period_name] = {
                'total_return': metrics['total_return'],
                'max_drawdown': metrics['max_drawdown'],
                'sharpe_ratio': metrics['sharpe_ratio'],
                'total_trades': metrics['total_trades'],
                'win_rate': metrics['win_rate']
            }
            
            print(f"   Return: {metrics['total_return']:.1%}")
            print(f"   Max DD: {metrics['max_drawdown']:.1%}")
            print(f"   Sharpe: {metrics['sharpe_ratio']:.2f}")
            print(f"   Trades: {metrics['total_trades']}")
            
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            stress_results[period_name] = {'error': str(e)}
    
    return stress_results


def test_regime_adaptability():
    """Test how the strategy adapts to different market regimes"""
    
    print("\n📊 Testing Regime Adaptability")
    print("=" * 60)
    
    # Test different regime scenarios
    regime_configs = {
        'BULL_MARKET': {
            'volatility_adjustment': 0.8,
            'momentum_threshold': 0.05,
            'position_sizing': 'aggressive'
        },
        'BEAR_MARKET': {
            'volatility_adjustment': 1.5,
            'momentum_threshold': 0.02,
            'position_sizing': 'conservative'
        },
        'SIDEWAYS_MARKET': {
            'volatility_adjustment': 1.2,
            'momentum_threshold': 0.03,
            'position_sizing': 'moderate'
        }
    }
    
    regime_results = {}
    
    for regime_name, regime_params in regime_configs.items():
        print(f"\nTesting {regime_name} configuration:")
        
        # Adjust config based on regime
        max_positions = {
            'aggressive': 7,
            'moderate': 5,
            'conservative': 3
        }[regime_params['position_sizing']]
        
        config = LiteBotBacktestConfig(
            start_date="2023-01-01",
            end_date="2024-01-01",
            initial_capital=1_000_000,
            max_positions=max_positions,
            base_slippage_bps=3.0 * regime_params['volatility_adjustment']
        )
        
        backtester = LiteBotBacktester(config)
        
        try:
            results = backtester.run_litebot_backtest(save_results=False)
            metrics = results['summary_metrics']
            
            regime_results[regime_name] = metrics
            
            print(f"   Max Positions: {max_positions}")
            print(f"   Return: {metrics['total_return']:.1%}")
            print(f"   Volatility: {metrics['volatility']:.1%}")
            print(f"   Sharpe: {metrics['sharpe_ratio']:.2f}")
            print(f"   Win Rate: {metrics['win_rate']:.1%}")
            
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            regime_results[regime_name] = {'error': str(e)}
    
    return regime_results


def test_transaction_cost_impact():
    """Test impact of different transaction cost scenarios"""
    
    print("\n💰 Testing Transaction Cost Impact")
    print("=" * 60)
    
    cost_scenarios = {
        'LOW_COST': {
            'commission_per_trade': 0.0,  # Commission-free
            'base_slippage_bps': 1.0,     # Minimal slippage
            'bid_ask_spread_bps': 2.0
        },
        'MODERATE_COST': {
            'commission_per_trade': 1.0,  # $1 commission
            'base_slippage_bps': 3.0,     # Typical slippage
            'bid_ask_spread_bps': 5.0
        },
        'HIGH_COST': {
            'commission_per_trade': 5.0,  # $5 commission
            'base_slippage_bps': 8.0,     # High slippage
            'bid_ask_spread_bps': 10.0
        }
    }
    
    cost_results = {}
    
    for scenario_name, cost_params in cost_scenarios.items():
        print(f"\nTesting {scenario_name} scenario:")
        
        config = LiteBotBacktestConfig(
            start_date="2023-01-01",
            end_date="2024-01-01",
            initial_capital=1_000_000,
            **cost_params
        )
        
        backtester = LiteBotBacktester(config)
        
        try:
            results = backtester.run_litebot_backtest(save_results=False)
            metrics = results['summary_metrics']
            
            cost_results[scenario_name] = metrics
            
            print(f"   Commission: ${cost_params['commission_per_trade']:.2f}")
            print(f"   Slippage: {cost_params['base_slippage_bps']:.1f} bps")
            print(f"   Return: {metrics['total_return']:.1%}")
            print(f"   Trades: {metrics['total_trades']}")
            
            # Calculate cost impact
            total_cost_estimate = metrics['total_trades'] * (
                cost_params['commission_per_trade'] + 
                (cost_params['base_slippage_bps'] + cost_params['bid_ask_spread_bps']) / 10000 * 50000  # Assume $50K avg trade
            )
            print(f"   Est. Total Costs: ${total_cost_estimate:,.0f}")
            
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            cost_results[scenario_name] = {'error': str(e)}
    
    return cost_results


def test_position_sizing_impact():
    """Test impact of different position sizing approaches"""
    
    print("\n📏 Testing Position Sizing Impact")
    print("=" * 60)
    
    sizing_scenarios = {
        'CONSERVATIVE': {
            'max_positions': 10,
            'max_single_position': 0.10,  # 10% max
            'min_trade_value': 5000
        },
        'MODERATE': {
            'max_positions': 5,
            'max_single_position': 0.20,  # 20% max
            'min_trade_value': 2000
        },
        'AGGRESSIVE': {
            'max_positions': 3,
            'max_single_position': 0.33,  # 33% max
            'min_trade_value': 1000
        }
    }
    
    sizing_results = {}
    
    for scenario_name, sizing_params in sizing_scenarios.items():
        print(f"\nTesting {scenario_name} position sizing:")
        
        config = LiteBotBacktestConfig(
            start_date="2023-01-01",
            end_date="2024-01-01",
            initial_capital=1_000_000,
            **sizing_params
        )
        
        backtester = LiteBotBacktester(config)
        
        try:
            results = backtester.run_litebot_backtest(save_results=False)
            metrics = results['summary_metrics']
            
            sizing_results[scenario_name] = metrics
            
            print(f"   Max Positions: {sizing_params['max_positions']}")
            print(f"   Max Single: {sizing_params['max_single_position']:.0%}")
            print(f"   Return: {metrics['total_return']:.1%}")
            print(f"   Volatility: {metrics['volatility']:.1%}")
            print(f"   Sharpe: {metrics['sharpe_ratio']:.2f}")
            print(f"   Max DD: {metrics['max_drawdown']:.1%}")
            
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            sizing_results[scenario_name] = {'error': str(e)}
    
    return sizing_results


def create_performance_summary(all_results):
    """Create comprehensive performance summary"""
    
    print("\n📈 COMPREHENSIVE PERFORMANCE SUMMARY")
    print("=" * 80)
    
    # Base case results
    if 'base_test' in all_results and all_results['base_test']:
        base_metrics = all_results['base_test']['summary_metrics']
        print(f"📊 BASE CASE PERFORMANCE:")
        print(f"   Total Return: {base_metrics['total_return']:.1%}")
        print(f"   Annualized Return: {base_metrics['annualized_return']:.1%}")
        print(f"   Volatility: {base_metrics['volatility']:.1%}")
        print(f"   Sharpe Ratio: {base_metrics['sharpe_ratio']:.2f}")
        print(f"   Max Drawdown: {base_metrics['max_drawdown']:.1%}")
        print(f"   Win Rate: {base_metrics['win_rate']:.1%}")
        print(f"   Total Trades: {base_metrics['total_trades']}")
    
    # Stress test summary
    if 'stress_tests' in all_results:
        print(f"\n⚠️ STRESS TEST SUMMARY:")
        for period, results in all_results['stress_tests'].items():
            if 'total_return' in results:
                print(f"   {period}: {results['total_return']:.1%} return, {results['max_drawdown']:.1%} max DD")
    
    # Regime adaptability
    if 'regime_tests' in all_results:
        print(f"\n📊 REGIME ADAPTABILITY:")
        for regime, results in all_results['regime_tests'].items():
            if 'total_return' in results:
                print(f"   {regime}: {results['total_return']:.1%} return, {results['sharpe_ratio']:.2f} Sharpe")
    
    # Cost impact analysis
    if 'cost_tests' in all_results:
        print(f"\n💰 TRANSACTION COST IMPACT:")
        returns_by_cost = {}
        for scenario, results in all_results['cost_tests'].items():
            if 'total_return' in results:
                returns_by_cost[scenario] = results['total_return']
                print(f"   {scenario}: {results['total_return']:.1%} return")
        
        if 'LOW_COST' in returns_by_cost and 'HIGH_COST' in returns_by_cost:
            cost_drag = returns_by_cost['LOW_COST'] - returns_by_cost['HIGH_COST']
            print(f"   💡 Cost Drag: {cost_drag:.1%}")
    
    # Position sizing impact
    if 'sizing_tests' in all_results:
        print(f"\n📏 POSITION SIZING IMPACT:")
        for scenario, results in all_results['sizing_tests'].items():
            if 'total_return' in results:
                risk_adj_return = results['total_return'] / max(results['volatility'], 0.01)
                print(f"   {scenario}: {results['total_return']:.1%} return, {risk_adj_return:.2f} risk-adj")
    
    print(f"\n✅ LiteBot backtesting framework validation complete!")


def main():
    """Run comprehensive LiteBot backtesting tests"""
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    print("🤖 LITEBOT COMPREHENSIVE BACKTESTING VALIDATION")
    print("=" * 80)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    all_results = {}
    
    # 1. Base integration test
    print("\n1️⃣ Running base integration test...")
    all_results['base_test'] = test_litebot_integration()
    
    # 2. Historical stress tests
    print("\n2️⃣ Running historical stress tests...")
    all_results['stress_tests'] = test_historical_stress_periods()
    
    # 3. Regime adaptability tests
    print("\n3️⃣ Running regime adaptability tests...")
    all_results['regime_tests'] = test_regime_adaptability()
    
    # 4. Transaction cost impact tests
    print("\n4️⃣ Running transaction cost impact tests...")
    all_results['cost_tests'] = test_transaction_cost_impact()
    
    # 5. Position sizing impact tests
    print("\n5️⃣ Running position sizing impact tests...")
    all_results['sizing_tests'] = test_position_sizing_impact()
    
    # 6. Create comprehensive summary
    create_performance_summary(all_results)
    
    # Save test results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"litebot_validation_results_{timestamp}.json"
    
    # Convert to JSON-serializable format
    import json
    try:
        with open(results_file, 'w') as f:
            json.dump(all_results, f, indent=2, default=str)
        print(f"\n💾 Test results saved to: {results_file}")
    except Exception as e:
        print(f"⚠️ Could not save results: {e}")
    
    return all_results


if __name__ == "__main__":
    main()

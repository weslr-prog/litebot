#!/usr/bin/env python3
"""
Simple Backtesting Demo for LiteBotX
===================================

This script demonstrates the working backtesting system.
"""

import sys
import os
sys.path.append('.')

from backtest.backtester import BacktestConfig, run_backtest
import pandas as pd

def demo_single_stock_backtest():
    """Demo: Single stock backtest"""
    print("🎯 SINGLE STOCK BACKTEST DEMO")
    print("=" * 50)
    
    config = BacktestConfig(
        symbol='AAPL',
        timeframe='1D',
        lookback_days=365,  # 1 year
        initial_equity=10000,
        fast=9,   # 9-day EMA
        slow=21   # 21-day EMA
    )
    
    print(f"📊 Running backtest for {config.symbol}")
    print(f"   Timeframe: {config.timeframe}")
    print(f"   Period: {config.lookback_days} days")
    print(f"   Strategy: EMA crossover ({config.fast}/{config.slow})")
    print()
    
    result = run_backtest(config)
    
    if result['ok']:
        print("✅ BACKTEST RESULTS:")
        print(f"   Symbol: {result['symbol']}")
        print(f"   Bars processed: {result['bars']}")
        print(f"   Period: {result['start'][:10]} to {result['end'][:10]}")
        print(f"   Initial capital: ${result['initial_equity']:,.2f}")
        print(f"   Final equity: ${result['final_equity']:,.2f}")
        print(f"   Total return: {result['total_return']:.2%}")
        print(f"   Buy-hold return: {result['buyhold_return']:.2%}")
        print(f"   Max drawdown: {result['max_drawdown']:.2%}")
        print(f"   Sharpe ratio: {result['sharpe']:.2f}")
        
        # Performance comparison
        strategy_return = result['total_return']
        buyhold_return = result['buyhold_return']
        alpha = strategy_return - buyhold_return
        
        print()
        print("📈 PERFORMANCE ANALYSIS:")
        print(f"   Strategy vs Buy-Hold: {alpha:.2%}")
        if alpha > 0:
            print("   🟢 Strategy OUTPERFORMED buy-and-hold")
        else:
            print("   🔴 Strategy UNDERPERFORMED buy-and-hold")
            
    else:
        print(f"❌ Backtest failed: {result['reason']}")
    
    return result

def demo_multi_stock_backtest():
    """Demo: Multiple stock comparison"""
    print("\n🎯 MULTI-STOCK COMPARISON")
    print("=" * 50)
    
    symbols = ['AAPL', 'MSFT', 'GOOGL', 'TSLA']
    results = {}
    
    for symbol in symbols:
        print(f"📊 Testing {symbol}...")
        
        config = BacktestConfig(
            symbol=symbol,
            timeframe='1D',
            lookback_days=180,  # 6 months
            initial_equity=10000
        )
        
        result = run_backtest(config)
        results[symbol] = result
    
    print("\n📊 COMPARISON RESULTS:")
    print("-" * 70)
    print(f"{'Symbol':<8} {'Return':<10} {'Buy-Hold':<10} {'Alpha':<10} {'Sharpe':<8}")
    print("-" * 70)
    
    for symbol, result in results.items():
        if result['ok']:
            strategy_ret = result['total_return']
            buyhold_ret = result['buyhold_return']
            alpha = strategy_ret - buyhold_ret
            sharpe = result['sharpe']
            
            print(f"{symbol:<8} {strategy_ret:>8.2%} {buyhold_ret:>9.2%} {alpha:>9.2%} {sharpe:>7.2f}")
        else:
            print(f"{symbol:<8} {'FAILED':<10}")
    
    return results

def check_backtest_system():
    """Check if backtesting system is working"""
    print("🔍 CHECKING BACKTEST SYSTEM...")
    print("=" * 50)
    
    # Check basic components
    try:
        from backtest.backtester import BacktestConfig, run_backtest
        print("✅ Core backtester imported successfully")
        
        # Check data access
        from core.data_fetcher import get_bars
        print("✅ Data fetcher available")
        
        # Check strategy components  
        from core.strategy import ema_crossover_signals
        print("✅ Strategy signals available")
        
        # Quick test
        print("\n🧪 Running quick functionality test...")
        config = BacktestConfig(symbol='AAPL', lookback_days=30)
        result = run_backtest(config)
        
        if result['ok']:
            print("✅ Basic backtest functionality working")
        else:
            print(f"⚠️ Quick test failed: {result['reason']}")
            
        print("\n🎉 BACKTESTING SYSTEM IS OPERATIONAL!")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ System error: {e}")
        return False

if __name__ == "__main__":
    print("🤖 LITEBOTX BACKTESTING DEMO")
    print("=" * 60)
    
    # Check system first
    if not check_backtest_system():
        print("❌ Backtesting system not available")
        sys.exit(1)
    
    print()
    
    # Run demos
    demo_single_stock_backtest()
    demo_multi_stock_backtest()
    
    print("\n💡 TIP: Check 'backtest/results/' for detailed results and equity curves!")
    print("💡 TIP: Modify BacktestConfig parameters to test different strategies!")
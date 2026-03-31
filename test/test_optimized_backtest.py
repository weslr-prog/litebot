#!/usr/bin/env python3
"""
Updated Backtesting Demo for Optimized Strategy
Tests current optimized settings with 5.5% confidence threshold
"""

import sys
import os
from datetime import datetime, timedelta
sys.path.append('/home/wes/Desktop/litebotx-usb-deployment')

from backtest.backtester import BacktestConfig, run_backtest
from traders.short_cycle_trader import ShortCycleConfig

def test_optimized_strategy():
    """Test the current optimized strategy with backtesting"""
    print("🧪 BACKTESTING OPTIMIZED STRATEGY")
    print("=" * 45)
    print(f"Strategy: 5.5% confidence threshold (aggressive mode)")
    print(f"Test period: Last 90 days")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test symbols from current watchlist
    test_symbols = ['AAPL', 'NVDA', 'TSLA', 'MSFT', 'GOOGL']
    
    results = {}
    
    for symbol in test_symbols:
        print(f"\n📊 Testing {symbol}...")
        
        try:
            config = BacktestConfig(
                symbol=symbol,
                timeframe='1D',
                lookback_days=90,  # 3 months
                fast=9,
                slow=21,
                initial_equity=50000,  # $50K test capital
                results_dir='backtest/results'
            )
            
            result = run_backtest(config)
            
            if result:
                results[symbol] = result
                print(f"   ✅ {symbol}: {result.get('total_return_pct', 0):.1f}% return")
            else:
                print(f"   ❌ {symbol}: Backtest failed")
                
        except Exception as e:
            print(f"   ❌ {symbol}: Error - {e}")
    
    # Summary
    print(f"\n📈 BACKTEST SUMMARY:")
    print(f"=" * 30)
    
    if results:
        total_returns = [r.get('total_return_pct', 0) for r in results.values()]
        avg_return = sum(total_returns) / len(total_returns)
        win_rate = len([r for r in total_returns if r > 0]) / len(total_returns)
        
        print(f"   Symbols tested: {len(results)}")
        print(f"   Average return: {avg_return:.1f}%")
        print(f"   Win rate: {win_rate:.1%}")
        
        best_symbol = max(results.keys(), key=lambda k: results[k].get('total_return_pct', 0))
        worst_symbol = min(results.keys(), key=lambda k: results[k].get('total_return_pct', 0))
        
        print(f"   Best performer: {best_symbol} ({results[best_symbol].get('total_return_pct', 0):.1f}%)")
        print(f"   Worst performer: {worst_symbol} ({results[worst_symbol].get('total_return_pct', 0):.1f}%)")
        
        # Strategy validation
        if avg_return > 5 and win_rate > 0.5:
            print(f"   🎯 Strategy validation: PASSED")
        else:
            print(f"   ⚠️  Strategy validation: NEEDS REVIEW")
    else:
        print(f"   ❌ No successful backtests")
    
    return results

def test_walkforward_validation():
    """Run walkforward test on optimized strategy"""
    print(f"\n🚦 WALKFORWARD VALIDATION")
    print(f"=" * 30)
    
    try:
        # Import and run walkforward tester
        from walkforward_tester import walkforward_test
        walkforward_results = walkforward_test()
        print(f"   ✅ Walkforward test completed")
        return walkforward_results
    except Exception as e:
        print(f"   ❌ Walkforward test failed: {e}")
        return None

if __name__ == "__main__":
    print(f"🚀 LITEBOTX OPTIMIZED STRATEGY BACKTEST")
    print(f"=" * 50)
    
    # Run strategy backtest
    backtest_results = test_optimized_strategy()
    
    # Run walkforward validation
    walkforward_results = test_walkforward_validation()
    
    print(f"\n✅ Backtesting complete - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📝 Results logged to backtest/results/")
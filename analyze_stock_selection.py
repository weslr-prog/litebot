#!/usr/bin/env python3
"""
Stock Selection Analysis - Which stocks work best with our strategy?
Analyzes individual stock performance across all configurations and time periods
"""

import json
import pandas as pd
from pathlib import Path
from collections import defaultdict

# Load comprehensive backtest results
results_file = sorted(Path('backtest/results').glob('comprehensive_backtest_*.json'))[-1]
print("="*75)
print("STOCK SELECTION ANALYSIS")
print("="*75)
print(f"Analyzing: {results_file.name}\n")

with open(results_file, 'r') as f:
    data = json.load(f)

# Load individual backtest summaries to get per-stock data
summary_files = sorted(Path('backtest/results').glob('backtest_summary_*.json'))

# We need to re-run analysis on trade-level data
# Let me check if we have CSV files with individual trades
csv_files = sorted(Path('backtest/results').glob('trades_*.csv'))

if not csv_files:
    print("⚠️  No detailed trade CSV files found. Running quick analysis from summaries...\n")
    
    # Analyze from JSON data
    configs = ['historical', 'recent']
    
    for period_name in configs:
        if period_name not in data:
            continue
            
        print(f"\n{'='*75}")
        print(f"{period_name.upper()} PERIOD ANALYSIS")
        print(f"{'='*75}\n")
        
        period_data = data[period_name]
        
        # Sort configs by return
        sorted_configs = sorted(period_data.items(), key=lambda x: x[1]['total_return'], reverse=True)
        
        print(f"{'Configuration':<40} {'Return':>10} {'Win Rate':>10} {'Trades':>8}")
        print("-"*75)
        for config_name, metrics in sorted_configs:
            print(f"{config_name:<40} {metrics['total_return']*100:>9.2f}% {metrics['win_rate']*100:>9.1f}% {metrics['total_trades']:>8}")

else:
    print(f"✅ Found {len(csv_files)} trade CSV files\n")
    
    # Analyze most recent baseline and best configurations
    baseline_trades = None
    
    # Find baseline trades file
    for csv_file in csv_files:
        if 'baseline' in csv_file.name.lower():
            baseline_trades = pd.read_csv(csv_file)
            print(f"📊 Analyzing: {csv_file.name}")
            break
    
    if baseline_trades is None:
        print("⚠️  Could not find baseline trades CSV")
    else:
        # Analyze by symbol
        print(f"\n{'='*75}")
        print("STOCK PERFORMANCE ANALYSIS - BASELINE CONFIGURATION")
        print("="*75)
        print(f"Total trades: {len(baseline_trades)}\n")
        
        # Group by symbol
        stock_stats = {}
        
        for symbol in baseline_trades['symbol'].unique():
            symbol_trades = baseline_trades[baseline_trades['symbol'] == symbol]
            
            total_trades = len(symbol_trades)
            winning_trades = len(symbol_trades[symbol_trades['pnl_pct'] > 0])
            losing_trades = len(symbol_trades[symbol_trades['pnl_pct'] <= 0])
            win_rate = winning_trades / total_trades if total_trades > 0 else 0
            
            total_pnl = symbol_trades['pnl'].sum()
            avg_pnl_pct = symbol_trades['pnl_pct'].mean()
            
            avg_win_pct = symbol_trades[symbol_trades['pnl_pct'] > 0]['pnl_pct'].mean() if winning_trades > 0 else 0
            avg_loss_pct = symbol_trades[symbol_trades['pnl_pct'] <= 0]['pnl_pct'].mean() if losing_trades > 0 else 0
            
            avg_momentum = symbol_trades['momentum_at_entry'].mean()
            avg_volume = symbol_trades['volume_surge_at_entry'].mean()
            
            stock_stats[symbol] = {
                'trades': total_trades,
                'wins': winning_trades,
                'losses': losing_trades,
                'win_rate': win_rate,
                'total_pnl': total_pnl,
                'avg_pnl_pct': avg_pnl_pct,
                'avg_win_pct': avg_win_pct,
                'avg_loss_pct': avg_loss_pct,
                'avg_momentum': avg_momentum,
                'avg_volume': avg_volume
            }
        
        # Sort by total PnL
        sorted_by_pnl = sorted(stock_stats.items(), key=lambda x: x[1]['total_pnl'], reverse=True)
        
        print(f"{'Stock':<8} {'Trades':>7} {'Win%':>7} {'Total PnL':>12} {'Avg%':>8} {'AvgWin%':>10} {'AvgLoss%':>10}")
        print("-"*75)
        
        for symbol, stats in sorted_by_pnl:
            print(f"{symbol:<8} {stats['trades']:>7} {stats['win_rate']*100:>6.1f}% ${stats['total_pnl']:>10.2f} {stats['avg_pnl_pct']*100:>7.2f}% {stats['avg_win_pct']*100:>9.2f}% {stats['avg_loss_pct']*100:>9.2f}%")
        
        # Analyze best vs worst performers
        print(f"\n{'='*75}")
        print("TOP 3 PERFORMERS (By Total PnL)")
        print("="*75)
        
        for i, (symbol, stats) in enumerate(sorted_by_pnl[:3], 1):
            print(f"\n{i}. {symbol}")
            print(f"   Total PnL: ${stats['total_pnl']:+.2f}")
            print(f"   Trades: {stats['trades']} ({stats['wins']} wins, {stats['losses']} losses)")
            print(f"   Win Rate: {stats['win_rate']*100:.1f}%")
            print(f"   Avg Return: {stats['avg_pnl_pct']*100:+.2f}%")
            print(f"   Avg Win: {stats['avg_win_pct']*100:+.2f}% | Avg Loss: {stats['avg_loss_pct']*100:+.2f}%")
            print(f"   Avg Entry Momentum: {stats['avg_momentum']*100:.2f}%")
            print(f"   Avg Volume Surge: {stats['avg_volume']:.2f}x")
        
        print(f"\n{'='*75}")
        print("BOTTOM 3 PERFORMERS (By Total PnL)")
        print("="*75)
        
        for i, (symbol, stats) in enumerate(sorted_by_pnl[-3:][::-1], 1):
            print(f"\n{i}. {symbol}")
            print(f"   Total PnL: ${stats['total_pnl']:+.2f}")
            print(f"   Trades: {stats['trades']} ({stats['wins']} wins, {stats['losses']} losses)")
            print(f"   Win Rate: {stats['win_rate']*100:.1f}%")
            print(f"   Avg Return: {stats['avg_pnl_pct']*100:+.2f}%")
            print(f"   Avg Win: {stats['avg_win_pct']*100:+.2f}% | Avg Loss: {stats['avg_loss_pct']*100:+.2f}%")
            print(f"   Avg Entry Momentum: {stats['avg_momentum']*100:.2f}%")
            print(f"   Avg Volume Surge: {stats['avg_volume']:.2f}x")
        
        # Analyze by win rate
        sorted_by_winrate = sorted(stock_stats.items(), key=lambda x: x[1]['win_rate'], reverse=True)
        
        print(f"\n{'='*75}")
        print("STOCKS BY WIN RATE")
        print("="*75)
        print(f"\n{'Stock':<8} {'Win Rate':>10} {'Trades':>8} {'Avg Return':>12}")
        print("-"*75)
        
        for symbol, stats in sorted_by_winrate:
            print(f"{symbol:<8} {stats['win_rate']*100:>9.1f}% {stats['trades']:>8} {stats['avg_pnl_pct']*100:>11.2f}%")
        
        # Identify patterns
        print(f"\n{'='*75}")
        print("STOCK SELECTION INSIGHTS")
        print("="*75)
        
        # High win rate stocks (>50%)
        high_winrate = [(s, st) for s, st in stock_stats.items() if st['win_rate'] > 0.50 and st['trades'] >= 20]
        low_winrate = [(s, st) for s, st in stock_stats.items() if st['win_rate'] < 0.45 and st['trades'] >= 20]
        
        print(f"\n🎯 HIGH WIN RATE STOCKS (>50%, min 20 trades):")
        if high_winrate:
            for symbol, stats in sorted(high_winrate, key=lambda x: x[1]['win_rate'], reverse=True):
                print(f"   {symbol}: {stats['win_rate']*100:.1f}% win rate, {stats['trades']} trades, ${stats['total_pnl']:+.2f} total")
        else:
            print("   None found (all stocks <50% win rate)")
        
        print(f"\n⚠️  LOW WIN RATE STOCKS (<45%, min 20 trades):")
        if low_winrate:
            for symbol, stats in sorted(low_winrate, key=lambda x: x[1]['win_rate']):
                print(f"   {symbol}: {stats['win_rate']*100:.1f}% win rate, {stats['trades']} trades, ${stats['total_pnl']:+.2f} total")
        else:
            print("   None found (all stocks >45% win rate)")
        
        # Profitable vs unprofitable
        profitable = [(s, st) for s, st in stock_stats.items() if st['total_pnl'] > 0 and st['trades'] >= 20]
        unprofitable = [(s, st) for s, st in stock_stats.items() if st['total_pnl'] < 0 and st['trades'] >= 20]
        
        print(f"\n✅ NET PROFITABLE STOCKS (min 20 trades):")
        if profitable:
            for symbol, stats in sorted(profitable, key=lambda x: x[1]['total_pnl'], reverse=True):
                print(f"   {symbol}: ${stats['total_pnl']:+.2f} total, {stats['win_rate']*100:.1f}% win rate")
        
        print(f"\n❌ NET UNPROFITABLE STOCKS (min 20 trades):")
        if unprofitable:
            for symbol, stats in sorted(unprofitable, key=lambda x: x[1]['total_pnl']):
                print(f"   {symbol}: ${stats['total_pnl']:+.2f} total, {stats['win_rate']*100:.1f}% win rate")
        else:
            print("   ✅ ALL stocks are net profitable!")
        
        # Sector patterns
        print(f"\n{'='*75}")
        print("SECTOR ANALYSIS")
        print("="*75)
        
        sectors = {
            'Airlines/Travel': ['JBLU', 'AAL'],
            'Cruise': ['CCL', 'RCL'],
            'Automotive': ['F'],
            'Green Energy': ['GEVO', 'PLUG', 'FCEL'],
            'Consumer': ['SBUX', 'SIRI', 'CAKE']
        }
        
        for sector, symbols in sectors.items():
            sector_symbols = [s for s in symbols if s in stock_stats]
            if not sector_symbols:
                continue
                
            sector_trades = sum(stock_stats[s]['trades'] for s in sector_symbols)
            sector_pnl = sum(stock_stats[s]['total_pnl'] for s in sector_symbols)
            sector_wins = sum(stock_stats[s]['wins'] for s in sector_symbols)
            sector_win_rate = sector_wins / sector_trades if sector_trades > 0 else 0
            
            print(f"\n{sector}:")
            print(f"   Stocks: {', '.join(sector_symbols)}")
            print(f"   Total PnL: ${sector_pnl:+.2f}")
            print(f"   Total Trades: {sector_trades}")
            print(f"   Win Rate: {sector_win_rate*100:.1f}%")
            print(f"   Avg PnL per trade: ${sector_pnl/sector_trades:+.2f}")

print(f"\n{'='*75}")
print("RECOMMENDATIONS")
print("="*75)
print("\nBased on this analysis, consider:")
print("1. Favor stocks with consistent high win rates (>50%)")
print("2. Avoid or reduce exposure to stocks with <45% win rate")
print("3. Identify which sectors work best for this strategy")
print("4. Consider sector rotation based on market conditions")
print("\n")

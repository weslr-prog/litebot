#!/usr/bin/env python3
"""
Simple D+1 Strategy Performance Analyzer
Analyzes historical trades to validate strategy performance
Uses actual trade history from positions.json and logs
"""

import json
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import sys

def analyze_recent_trades(days_back=30):
    """Analyze recent trades from bot logs and positions.json"""
    print("=" * 70)
    print("🔍 LITEBOTX D+1 STRATEGY PERFORMANCE ANALYSIS")
    print("=" * 70)
    print(f"Analyzing last {days_back} days of trading")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Try to load positions.json
    positions_file = Path("positions.json")
    if not positions_file.exists():
        print("❌ positions.json not found")
        return None
    
    try:
        with open(positions_file) as f:
            data = json.load(f)
        
        # positions.json can be either a list or a dict
        if isinstance(data, list):
            exited_positions = [p for p in data if p.get('status') == 'EXITED' or p.get('exit_price')]
        else:
            exited_positions = data.get("exited_positions", [])
        
        if not exited_positions:
            print("⚠️  No exited positions found in positions.json")
            return None
        
        # Filter to last N days
        cutoff_date = datetime.now() - timedelta(days=days_back)
        recent_exits = []
        
        for pos in exited_positions:
            try:
                # Try exit_timestamp first, then entry_timestamp
                exit_ts = pos.get("exit_timestamp") or pos.get("entry_timestamp")
                if not exit_ts:
                    # Try to construct from exit_date
                    exit_date_str = pos.get("exit_date")
                    if exit_date_str:
                        exit_date = datetime.fromisoformat(exit_date_str)
                    else:
                        continue
                else:
                    exit_date = datetime.fromisoformat(exit_ts.replace('Z', '+00:00'))
                
                if exit_date > cutoff_date:
                    recent_exits.append(pos)
            except Exception as e:
                # Try to use any position with realized_pnl
                if 'realized_pnl' in pos:
                    recent_exits.append(pos)
                continue
        
        if not recent_exits:
            print(f"⚠️  No trades found in last {days_back} days")
            return None
        
        # Analyze trades
        df = pd.DataFrame(recent_exits)
        
        # Calculate metrics
        total_trades = len(df)
        winning_trades = df[df['realized_pnl'] > 0]
        losing_trades = df[df['realized_pnl'] <= 0]
        
        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0
        
        total_profit = winning_trades['realized_pnl'].sum() if len(winning_trades) > 0 else 0
        total_loss = abs(losing_trades['realized_pnl'].sum()) if len(losing_trades) > 0 else 0
        profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
        
        net_pnl = df['realized_pnl'].sum()
        
        avg_win = winning_trades['realized_pnl'].mean() if len(winning_trades) > 0 else 0
        avg_loss = losing_trades['realized_pnl'].mean() if len(losing_trades) > 0 else 0
        
        # Calculate avg hold time
        if 'hold_days' in df.columns:
            avg_hold = df['hold_days'].mean()
        else:
            avg_hold = 1.5  # D+1 strategy default
        
        # Group by exit reason
        exit_reasons = df.get('exit_reason', pd.Series()).value_counts() if 'exit_reason' in df.columns else {}
        
        # Print results
        print("📊 PERFORMANCE SUMMARY")
        print("-" * 70)
        print(f"Total Trades:        {total_trades}")
        print(f"Winning Trades:      {len(winning_trades)} ({len(winning_trades)/total_trades:.1%})")
        print(f"Losing Trades:       {len(losing_trades)} ({len(losing_trades)/total_trades:.1%})")
        print()
        print(f"Win Rate:            {win_rate:.1%}")
        print(f"Profit Factor:       {profit_factor:.2f}")
        print(f"Net P&L:             ${net_pnl:,.2f}")
        print(f"Avg Win:             ${avg_win:,.2f}")
        print(f"Avg Loss:            ${avg_loss:,.2f}")
        print(f"Avg Hold Time:       {avg_hold:.1f} days")
        print()
        
        # Top performers
        if len(df) > 0:
            print("🏆 TOP 5 WINNERS:")
            top_winners = df.nlargest(5, 'realized_pnl')[['symbol', 'realized_pnl', 'exit_reason']]
            for idx, row in top_winners.iterrows():
                print(f"   {row['symbol']}: ${row['realized_pnl']:,.2f} ({row.get('exit_reason', 'N/A')})")
            print()
            
            print("📉 TOP 5 LOSERS:")
            top_losers = df.nsmallest(5, 'realized_pnl')[['symbol', 'realized_pnl', 'exit_reason']]
            for idx, row in top_losers.iterrows():
                print(f"   {row['symbol']}: ${row['realized_pnl']:,.2f} ({row.get('exit_reason', 'N/A')})")
            print()
        
        # Exit reason distribution
        if len(exit_reasons) > 0:
            print("🎯 EXIT REASONS:")
            for reason, count in exit_reasons.head(10).items():
                pct = (count / total_trades) * 100
                print(f"   {reason}: {count} ({pct:.1f}%)")
            print()
        
        # Symbol performance
        if 'symbol' in df.columns:
            symbol_pnl = df.groupby('symbol')['realized_pnl'].agg(['sum', 'count', 'mean'])
            symbol_pnl = symbol_pnl.sort_values('sum', ascending=False)
            
            print("📈 SYMBOL PERFORMANCE (Top 10):")
            print(f"{'Symbol':<8} {'Trades':<8} {'Total P&L':<12} {'Avg P&L':<12}")
            print("-" * 50)
            for symbol, row in symbol_pnl.head(10).iterrows():
                print(f"{symbol:<8} {int(row['count']):<8} ${row['sum']:>10,.2f} ${row['mean']:>10,.2f}")
            print()
        
        # Strategy validation
        print("🎯 STRATEGY VALIDATION:")
        if win_rate > 0.55 and profit_factor > 1.5 and net_pnl > 0:
            print("   ✅ EXCELLENT - Strategy performing well")
        elif win_rate > 0.50 and profit_factor > 1.2 and net_pnl > 0:
            print("   ✅ GOOD - Strategy is profitable")
        elif net_pnl > 0:
            print("   ⚠️  MARGINAL - Strategy slightly profitable, needs monitoring")
        else:
            print("   ❌ POOR - Strategy needs optimization")
        
        print()
        print("=" * 70)
        
        return {
            'total_trades': total_trades,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'net_pnl': net_pnl,
            'avg_hold_days': avg_hold
        }
        
    except Exception as e:
        print(f"❌ Error analyzing trades: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    # Analyze last 30 days
    result = analyze_recent_trades(days_back=30)
    
    if result:
        # Save to backtest results
        output_dir = Path("backtest/results")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        summary_file = output_dir / f"d1_performance_analysis_{timestamp}.txt"
        
        with open(summary_file, 'w') as f:
            f.write(f"D+1 Strategy Performance Analysis\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"Total Trades: {result['total_trades']}\n")
            f.write(f"Win Rate: {result['win_rate']:.1%}\n")
            f.write(f"Profit Factor: {result['profit_factor']:.2f}\n")
            f.write(f"Net P&L: ${result['net_pnl']:,.2f}\n")
            f.write(f"Avg Hold: {result['avg_hold_days']:.1f} days\n")
        
        print(f"💾 Analysis saved to: {summary_file}")
        return 0
    else:
        return 1

if __name__ == "__main__":
    sys.exit(main())

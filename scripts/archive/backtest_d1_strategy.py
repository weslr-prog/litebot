#!/usr/bin/env python3
"""
LiteBotX Short-Cycle D+1 Strategy Backtester
Tests the actual live trading strategy with real watchlist symbols
"""

import sys
import os
import json
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd

sys.path.append('/home/wes/Desktop/litebotx-usb-deployment')

def get_live_watchlist():
    """Get the actual watchlist used by live trading bot"""
    try:
        # Try to load from config
        config_path = Path("config/short_cycle_universe.json")
        if config_path.exists():
            with open(config_path) as f:
                config = json.load(f)
                return config.get("base_universe", [])
    except Exception as e:
        print(f"⚠️  Could not load watchlist from config: {e}")
    
    # Fallback to PreFilter candidates (same as live bot)
    return [
        "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "NFLX", 
        "AMD", "AVGO", "INTC", "ORCL", "CRM", "ADBE", "CSCO", "QCOM"
    ]

def backtest_d1_strategy(symbol, days_back=90):
    """
    Backtest D+1 short-cycle strategy on a symbol
    
    Strategy Rules:
    - Enter on AI signal (simulated with momentum + volume)
    - Exit next day (D+1) when profitable using zone-based logic
    - Max hold: 2 days (force exit)
    - Stop loss: -2%
    - Target: +1-3% 
    """
    try:
        # Use Alpaca data API directly (no yfinance needed)
        from alpaca.data.historical import StockHistoricalDataClient
        from alpaca.data.requests import StockBarsRequest
        from alpaca.data.timeframe import TimeFrame
        import os
        from dotenv import load_dotenv
        
        load_dotenv()
        
        api_key = os.getenv("APCA_API_KEY_ID")
        secret_key = os.getenv("APCA_API_SECRET_KEY")
        
        if not api_key or not secret_key:
            # Try DataLoader as fallback
            try:
                from data_loader import DataLoader
                dl = DataLoader()
                df = dl.get_historical_data(symbol, days=days_back)
                if df is None or df.empty:
                    return None
            except:
                return None
        else:
            # Use Alpaca data
            data_client = StockHistoricalDataClient(api_key, secret_key)
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back * 2)  # Extra buffer for weekends
            
            request_params = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=TimeFrame.Day,
                start=start_date,
                end=end_date
            )
            
            bars = data_client.get_stock_bars(request_params)
            
            if not bars or symbol not in bars:
                return None
            
            # Convert to DataFrame
            bars_data = bars[symbol]
            df = pd.DataFrame([{
                'date': bar.timestamp,
                'open': float(bar.open),
                'high': float(bar.high),
                'low': float(bar.low),
                'close': float(bar.close),
                'volume': int(bar.volume)
            } for bar in bars_data])
        
        if df is None or df.empty or len(df) < 20:
            return None
        
        # Ensure we have the required columns
        if not all(col in df.columns for col in ['date', 'open', 'high', 'low', 'close', 'volume']):
            return None
        
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').reset_index(drop=True)
        
        # Keep only last days_back trading days
        if len(df) > days_back:
            df = df.tail(days_back).reset_index(drop=True)
        
        # Calculate indicators for entry signals
        # Momentum (RSI-like)
        df['price_change'] = df['close'].pct_change()
        df['momentum'] = df['price_change'].rolling(window=5).mean()
        
        # Volume spike
        df['avg_volume'] = df['volume'].rolling(window=20).mean()
        df['volume_ratio'] = df['volume'] / df['avg_volume']
        
        # Trend (moving averages)
        df['ma_fast'] = df['close'].rolling(window=5).mean()
        df['ma_slow'] = df['close'].rolling(window=20).mean()
        df['trend_up'] = df['ma_fast'] > df['ma_slow']
        
        # Simulate AI signal: momentum + volume + trend
        df['signal_strength'] = 0.0
        df.loc[(df['momentum'] > 0.005) & 
               (df['volume_ratio'] > 1.2) & 
               (df['trend_up']), 'signal_strength'] = 0.75
        
        # Backtest D+1 strategy
        initial_capital = 10000
        capital = initial_capital
        position = None
        trades = []
        
        for i in range(20, len(df) - 2):  # Need lookahead for D+1
            row = df.iloc[i]
            
            # Check for exits first (if in position)
            if position is not None:
                entry_price = position['entry_price']
                entry_idx = position['entry_idx']
                hold_days = i - entry_idx
                current_price = row['close']
                pnl_pct = (current_price - entry_price) / entry_price
                
                should_exit = False
                exit_reason = ""
                
                # D+1 eligible (next day after entry)
                if hold_days >= 1:
                    # Zone-based exit logic (simplified)
                    if pnl_pct > 0.01:  # >1% profit
                        should_exit = True
                        exit_reason = "D+1_PROFIT_TARGET"
                    elif pnl_pct < -0.02:  # -2% stop loss
                        should_exit = True
                        exit_reason = "STOP_LOSS"
                    elif hold_days >= 2:  # Force exit after 2 days
                        should_exit = True
                        exit_reason = "D+2_FORCE_EXIT"
                
                if should_exit:
                    # Exit position
                    pnl = capital * pnl_pct
                    capital += pnl
                    
                    trades.append({
                        'entry_date': df.iloc[entry_idx]['date'],
                        'exit_date': row['date'],
                        'entry_price': entry_price,
                        'exit_price': current_price,
                        'pnl_pct': pnl_pct * 100,
                        'pnl_dollars': pnl,
                        'hold_days': hold_days,
                        'exit_reason': exit_reason
                    })
                    
                    position = None
            
            # Check for new entries (if no position)
            if position is None and row['signal_strength'] > 0.6:
                # Enter position
                position = {
                    'entry_idx': i,
                    'entry_price': row['close'],
                    'entry_date': row['date']
                }
        
        # Close any open position at end
        if position is not None:
            final_row = df.iloc[-1]
            pnl_pct = (final_row['close'] - position['entry_price']) / position['entry_price']
            pnl = capital * pnl_pct
            capital += pnl
            
            trades.append({
                'entry_date': df.iloc[position['entry_idx']]['date'],
                'exit_date': final_row['date'],
                'entry_price': position['entry_price'],
                'exit_price': final_row['close'],
                'pnl_pct': pnl_pct * 100,
                'pnl_dollars': pnl,
                'hold_days': len(df) - 1 - position['entry_idx'],
                'exit_reason': 'END_OF_TEST'
            })
        
        # Calculate metrics
        if not trades:
            return None
        
        trades_df = pd.DataFrame(trades)
        total_return = ((capital - initial_capital) / initial_capital) * 100
        winning_trades = trades_df[trades_df['pnl_pct'] > 0]
        losing_trades = trades_df[trades_df['pnl_pct'] <= 0]
        
        win_rate = len(winning_trades) / len(trades) if trades else 0
        avg_win = winning_trades['pnl_pct'].mean() if len(winning_trades) > 0 else 0
        avg_loss = losing_trades['pnl_pct'].mean() if len(losing_trades) > 0 else 0
        
        total_wins = winning_trades['pnl_dollars'].sum() if len(winning_trades) > 0 else 0
        total_losses = abs(losing_trades['pnl_dollars'].sum()) if len(losing_trades) > 0 else 0
        profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')
        
        avg_hold_days = trades_df['hold_days'].mean()
        
        return {
            'symbol': symbol,
            'period': f"{df.iloc[0]['date'].strftime('%Y-%m-%d')} to {df.iloc[-1]['date'].strftime('%Y-%m-%d')}",
            'total_trades': len(trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate,
            'total_return_pct': total_return,
            'final_capital': capital,
            'avg_win_pct': avg_win,
            'avg_loss_pct': avg_loss,
            'profit_factor': profit_factor,
            'avg_hold_days': avg_hold_days,
            'trades': trades_df.to_dict('records')
        }
        
    except Exception as e:
        print(f"   ❌ Error backtesting {symbol}: {e}")
        return None

def save_results(results, output_dir='backtest/results'):
    """Save backtest results to CSV"""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Summary CSV
    summary_rows = []
    for result in results:
        summary_rows.append({
            'timestamp': datetime.now().isoformat(),
            'symbol': result['symbol'],
            'total_trades': result['total_trades'],
            'win_rate': f"{result['win_rate']:.2%}",
            'total_return_pct': f"{result['total_return_pct']:.2f}%",
            'profit_factor': f"{result['profit_factor']:.2f}",
            'avg_hold_days': f"{result['avg_hold_days']:.1f}",
            'period': result['period']
        })
    
    summary_df = pd.DataFrame(summary_rows)
    summary_file = f"{output_dir}/d1_strategy_summary_{timestamp}.csv"
    summary_df.to_csv(summary_file, index=False)
    print(f"\n💾 Summary saved: {summary_file}")
    
    # Detailed trades CSV
    all_trades = []
    for result in results:
        for trade in result['trades']:
            trade['symbol'] = result['symbol']
            all_trades.append(trade)
    
    if all_trades:
        trades_df = pd.DataFrame(all_trades)
        trades_file = f"{output_dir}/d1_strategy_trades_{timestamp}.csv"
        trades_df.to_csv(trades_file, index=False)
        print(f"💾 Trades saved: {trades_file}")

def main():
    print("=" * 70)
    print("🚀 LITEBOTX SHORT-CYCLE D+1 STRATEGY BACKTEST")
    print("=" * 70)
    print(f"Strategy: D+1 exit when profitable, max 2-day hold")
    print(f"Test Period: Last 90 days")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Get live watchlist
    watchlist = get_live_watchlist()
    print(f"📋 Testing {len(watchlist)} symbols from live bot watchlist")
    print(f"Symbols: {', '.join(watchlist[:10])}{'...' if len(watchlist) > 10 else ''}")
    print()
    
    results = []
    failed = []
    
    for symbol in watchlist:
        print(f"📊 Testing {symbol}...", end=' ')
        sys.stdout.flush()
        
        result = backtest_d1_strategy(symbol, days_back=90)
        
        if result:
            results.append(result)
            print(f"✅ {result['total_trades']} trades, {result['total_return_pct']:.1f}% return")
        else:
            failed.append(symbol)
            print(f"❌ No data or no trades")
    
    print()
    print("=" * 70)
    print("📈 BACKTEST RESULTS SUMMARY")
    print("=" * 70)
    
    if results:
        # Overall statistics
        total_trades = sum(r['total_trades'] for r in results)
        avg_win_rate = sum(r['win_rate'] for r in results) / len(results)
        avg_return = sum(r['total_return_pct'] for r in results) / len(results)
        avg_profit_factor = sum(r['profit_factor'] for r in results if r['profit_factor'] != float('inf')) / len([r for r in results if r['profit_factor'] != float('inf')])
        
        print(f"\n{'Symbol':<8} {'Trades':<8} {'Win Rate':<10} {'Return':<10} {'P.Factor':<10} {'Avg Hold':<10}")
        print("-" * 70)
        
        for result in sorted(results, key=lambda x: x['total_return_pct'], reverse=True):
            print(f"{result['symbol']:<8} {result['total_trades']:<8} "
                  f"{result['win_rate']:<10.1%} {result['total_return_pct']:<10.2f}% "
                  f"{result['profit_factor']:<10.2f} {result['avg_hold_days']:<10.1f}")
        
        print("-" * 70)
        print(f"{'AVERAGE':<8} {total_trades/len(results):<8.1f} "
              f"{avg_win_rate:<10.1%} {avg_return:<10.2f}% "
              f"{avg_profit_factor:<10.2f}")
        
        print()
        print(f"✅ Successful tests: {len(results)}/{len(watchlist)}")
        print(f"❌ Failed tests: {len(failed)}/{len(watchlist)}")
        
        if failed:
            print(f"   Failed symbols: {', '.join(failed[:10])}")
        
        # Strategy validation
        print()
        print("🎯 STRATEGY VALIDATION:")
        if avg_return > 3 and avg_win_rate > 0.55:
            print("   ✅ PASSED - Strategy shows positive edge")
        elif avg_return > 0 and avg_win_rate > 0.50:
            print("   ⚠️  MARGINAL - Strategy slightly profitable")
        else:
            print("   ❌ FAILED - Strategy needs optimization")
        
        print()
        print("📊 Key Metrics:")
        print(f"   Average Return: {avg_return:.2f}%")
        print(f"   Average Win Rate: {avg_win_rate:.1%}")
        print(f"   Average Profit Factor: {avg_profit_factor:.2f}")
        print(f"   Total Trades Simulated: {total_trades}")
        
        # Save results
        save_results(results)
        
    else:
        print("❌ No successful backtests completed")
    
    print()
    print("=" * 70)

if __name__ == "__main__":
    main()

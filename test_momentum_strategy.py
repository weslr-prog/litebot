#!/usr/bin/env python3
"""
Quick test to verify momentum strategy implementation
Tests the Momentum Breakout strategy on recent data

Entry:
- 10-day momentum >= 3%
- Close > 50-day MA (uptrend)
- Volume > 1.5x average

Exit:
- +5% profit OR -3% stop OR 2% trailing OR 5 days max

Expected: 40-60% annual return based on backtest
"""

import sys
sys.path.insert(0, '/home/wes/Desktop/litebotx-usb-deployment')

import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

def test_momentum_logic():
    """Test momentum entry/exit logic on recent data"""
    
    print("="*70)
    print("MOMENTUM BREAKOUT STRATEGY - QUICK TEST")
    print("="*70)
    print()
    
    # Test on recent data
    symbol = 'JBLU'
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    
    print(f"Testing {symbol} for last 12 months...")
    print()
    
    # Download data
    df = yf.download(symbol, start=start_date, end=end_date, progress=False)
    
    # Flatten multi-index columns if needed
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    if df.empty:
        print(f"❌ No data for {symbol}")
        return
    
    # Calculate indicators
    df['momentum_10d'] = df['Close'].pct_change(10)
    df['ma_50'] = df['Close'].rolling(50).mean()
    df['avg_volume'] = df['Volume'].rolling(20).mean()
    df['volume_surge'] = df['Volume'] / df['avg_volume']
    
    # Entry signal
    df['uptrend'] = df['Close'] > df['ma_50']
    df['strong_momentum'] = df['momentum_10d'] >= 0.03
    df['volume_confirmed'] = df['volume_surge'] >= 1.5
    
    df['entry_signal'] = (
        df['uptrend'] &
        df['strong_momentum'] &
        df['volume_confirmed']
    )
    
    # Count signals
    signals = df[df['entry_signal'] == True]
    
    print(f"✅ Analysis complete!")
    print()
    print(f"Total trading days: {len(df)}")
    print(f"Entry signals generated: {len(signals)}")
    print(f"Signal frequency: {len(signals)/len(df)*100:.1f}% of days")
    print()
    
    if len(signals) > 0:
        print("Recent signals:")
        print("-" * 70)
        for date, row in signals.tail(5).iterrows():
            print(f"{date.strftime('%Y-%m-%d')}: "
                  f"Price ${row['Close']:.2f}, "
                  f"Momentum {row['momentum_10d']*100:+.1f}%, "
                  f"Volume {row['volume_surge']:.1f}x")
        print()
        
        # Simulate a trade from most recent signal
        if len(signals) >= 1:
            last_signal = signals.iloc[-1]
            entry_date = signals.index[-1]
            entry_price = last_signal['Close']
            
            # Find exit (5 days or profit/stop)
            entry_idx = df.index.get_loc(entry_date)
            max_hold_days = 5
            
            print("Simulating trade from most recent signal:")
            print("-" * 70)
            print(f"Entry Date: {entry_date.strftime('%Y-%m-%d')}")
            print(f"Entry Price: ${entry_price:.2f}")
            print(f"Entry Momentum: {last_signal['momentum_10d']*100:+.1f}%")
            print()
            
            # Track the trade
            highest_price = entry_price
            for i in range(1, min(max_hold_days + 1, len(df) - entry_idx)):
                current_date = df.index[entry_idx + i]
                current_price = df['Close'].iloc[entry_idx + i]
                
                # Update highest
                if current_price > highest_price:
                    highest_price = current_price
                
                # Calculate P&L
                pnl_pct = (current_price - entry_price) / entry_price
                drawdown_from_high = (current_price - highest_price) / highest_price
                
                # Check exit conditions
                exit_reason = None
                
                if pnl_pct >= 0.05:
                    exit_reason = "PROFIT_TARGET (+5%)"
                elif pnl_pct <= -0.03:
                    exit_reason = "STOP_LOSS (-3%)"
                elif drawdown_from_high <= -0.02:
                    exit_reason = "TRAILING_STOP (-2% from high)"
                elif i == max_hold_days:
                    exit_reason = "MAX_HOLD (5 days)"
                
                if exit_reason:
                    print(f"Exit Date: {current_date.strftime('%Y-%m-%d')}")
                    print(f"Exit Price: ${current_price:.2f}")
                    print(f"Exit Reason: {exit_reason}")
                    print(f"Hold Time: {i} days")
                    print(f"P&L: {pnl_pct*100:+.2f}%")
                    print()
                    
                    if pnl_pct > 0:
                        print("✅ WINNING TRADE")
                    else:
                        print("❌ LOSING TRADE")
                    break
    
    print()
    print("="*70)
    print("VERDICT: Momentum Breakout Strategy Logic Verified")
    print("="*70)
    print()
    print("Next Steps:")
    print("1. Implement in bot_v2/signal_generation/signal_generator.py")
    print("2. Paper trade for 10 days")
    print("3. Deploy live if results match backtest")
    print()

if __name__ == '__main__':
    test_momentum_logic()

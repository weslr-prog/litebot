#!/usr/bin/env python3
"""
Diagnostic script to check why 25 prefilter candidates aren't generating signals
"""
import sys
sys.path.insert(0, '/home/wes/Desktop/litebotx-usb-deployment')

import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

# Today's 25 candidates (from log output)
candidates = [
    'AEO', 'AI', 'APA', 'AR', 'BEKE', 'CHWY', 'CLF', 'CPB', 'CPNG', 'DKNG',
    'HAL', 'LI', 'LYFT', 'MRNA', 'MUR', 'NOV', 'NTLA', 'PENN', 'PINS', 'PR',
    'S', 'SM', 'TAL', 'TWO', 'XPEV'
]

def calculate_rsi(data, window=7):
    """Calculate RSI"""
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

print("="*80)
print("DIAGNOSTIC: Why did 25 candidates not generate signals?")
print("="*80)
print()

rejection_summary = {
    'sma_reject': [],
    'momentum_reject': [],
    'rsi_high': [],
    'rsi_ok_low_confidence': [],
    'data_error': []
}

for symbol in candidates:
    try:
        # Fetch data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=60)
        ticker = yf.Ticker(symbol)
        data = ticker.history(start=start_date, end=end_date)
        
        if len(data) < 20:
            rejection_summary['data_error'].append(symbol)
            print(f"   ❌ {symbol}: Insufficient data")
            continue
        
        # Current price and SMA
        current_price = data['Close'].iloc[-1]
        sma_20 = data['Close'].rolling(20).mean().iloc[-1]
        price_vs_sma_pct = ((current_price - sma_20) / sma_20) * 100
        
        # 5-day momentum
        if len(data) >= 5:
            five_day_ago_price = data['Close'].iloc[-5]
            five_day_momentum_pct = ((current_price - five_day_ago_price) / five_day_ago_price) * 100
        else:
            five_day_momentum_pct = 0
        
        # RSI(7)
        rsi = calculate_rsi(data, window=7).iloc[-1]
        
        # Check rejection reasons
        rejected = False
        reason = []
        
        # SMA check (>6% below)
        if price_vs_sma_pct < -6:
            rejection_summary['sma_reject'].append(symbol)
            reason.append(f"SMA: {price_vs_sma_pct:.1f}% below (>-6% = reject)")
            rejected = True
        
        # Momentum check (< -5%)
        if five_day_momentum_pct < -5:
            rejection_summary['momentum_reject'].append(symbol)
            reason.append(f"5d mom: {five_day_momentum_pct:.1f}% (<-5% = reject)")
            rejected = True
        
        # RSI check (> 35 for entry)
        if rsi > 35:
            rejection_summary['rsi_high'].append(symbol)
            if not rejected:  # Only count as RSI reject if passed other filters
                reason.append(f"RSI: {rsi:.1f} (need ≤35)")
            rejected = True
        
        # Build output
        status = "❌" if rejected else "✅"
        rsi_str = f"RSI={rsi:.1f}"
        sma_str = f"SMA={price_vs_sma_pct:+.1f}%"
        mom_str = f"5d={five_day_momentum_pct:+.1f}%"
        
        reason_str = " | ".join(reason) if reason else "PASSED ALL FILTERS!"
        
        print(f"{status} {symbol:6} | {rsi_str:9} | {sma_str:11} | {mom_str:10} | {reason_str}")
        
    except Exception as e:
        rejection_summary['data_error'].append(symbol)
        print(f"   ❌ {symbol}: Error - {e}")

print()
print("="*80)
print("REJECTION SUMMARY")
print("="*80)
print(f"SMA Reject (>6% below):       {len(rejection_summary['sma_reject'])} stocks - {rejection_summary['sma_reject']}")
print(f"Momentum Reject (<-5%):        {len(rejection_summary['momentum_reject'])} stocks - {rejection_summary['momentum_reject']}")
print(f"RSI Too High (>35):            {len(rejection_summary['rsi_high'])} stocks - {rejection_summary['rsi_high']}")
print(f"Data Errors:                   {len(rejection_summary['data_error'])} stocks - {rejection_summary['data_error']}")
print()
print("="*80)
print("CONCLUSION")
print("="*80)
print("Today's market conditions:")
print("- Most stocks are NOT oversold (RSI > 35)")
print("- Some stocks still falling (5-day momentum < -5%)")
print("- Some stocks too far below trend (>6% below SMA)")
print()
print("Mean reversion strategy requires:")
print("✓ Stock in uptrend (within 6% of 20-day SMA)")
print("✓ Not falling knife (5-day momentum > -5%)")
print("✓ Oversold (RSI ≤ 35)")
print("✓ Sufficient confidence (>= 0.50)")
print()
print("No signals today = Market not oversold enough for mean reversion entries")
print("="*80)

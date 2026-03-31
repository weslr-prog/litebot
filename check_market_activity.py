#!/usr/bin/env python3
"""Quick market activity check"""
import yfinance as yf
import pandas as pd
from datetime import datetime

# Check major indices
print('=' * 70)
print(f'Market Overview - {datetime.now().strftime("%Y-%m-%d %H:%M")}')
print('=' * 70)

indices = {'^GSPC': 'S&P 500', '^DJI': 'Dow Jones', '^IXIC': 'NASDAQ', '^VIX': 'VIX'}
for idx, name in indices.items():
    try:
        data = yf.download(idx, period='1d', interval='1m', progress=False, auto_adjust=False)
        if not data.empty and len(data) > 1:
            current = float(data['Close'].iloc[-1])
            open_price = float(data['Open'].iloc[0])
            change_pct = ((current - open_price) / open_price) * 100
            print(f'{name:12} {current:8.2f} ({change_pct:+.2f}%)')
    except Exception as e:
        print(f'{name:12} Error: {e}')

print('\n' + '=' * 70)
print('Your Watchlist Performance Today')
print('=' * 70)

# Your watchlist
watchlist = ['RIVN', 'LLY', 'AMZN', 'AMD', 'GOOGL', 'CAT', 'NVDA', 'ROKU', 
             'JPM', 'C', 'GS', 'BMY', 'AVGO', 'MS', 'IBM']

results = []
for symbol in watchlist:
    try:
        data = yf.download(symbol, period='1d', interval='1m', progress=False, auto_adjust=False)
        if not data.empty and len(data) > 1:
            current = float(data['Close'].iloc[-1])
            open_price = float(data['Open'].iloc[0])
            change_pct = ((current - open_price) / open_price) * 100
            
            # Volume surge
            recent_vol = float(data['Volume'].iloc[-30:].mean())
            earlier_vol = float(data['Volume'].iloc[:-30].mean()) if len(data) > 60 else recent_vol
            vol_surge = recent_vol / earlier_vol if earlier_vol > 0 else 1.0
            
            results.append({
                'symbol': symbol,
                'change': change_pct,
                'price': current,
                'vol_surge': vol_surge
            })
    except Exception as e:
        pass

# Sort by momentum
if results:
    results_df = pd.DataFrame(results).sort_values('change', ascending=False)
    for _, row in results_df.iterrows():
        momentum = '🔥' if abs(row['change']) > 1.5 else '📊' if abs(row['change']) > 0.5 else '💤'
        volume = '📈' if row['vol_surge'] > 1.3 else '➡️' if row['vol_surge'] > 1.1 else '📉'
        print(f'{momentum} {row["symbol"]:6} ${row["price"]:7.2f} {row["change"]:+6.2f}%  Vol:{volume} {row["vol_surge"]:4.2f}x')

print('=' * 70)
print('\n🔄 Refreshing watchlist to find better stocks? (Y/n): ', end='')

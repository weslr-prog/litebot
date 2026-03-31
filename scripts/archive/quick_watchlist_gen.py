#!/usr/bin/env python3
"""
Quick Watchlist Generator
Generates a fresh watchlist for tomorrow using yfinance
"""
import json
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import pytz

def get_data(symbol, days=30):
    """Fetch historical data for a symbol"""
    try:
        ticker = yf.Ticker(symbol)
        end = datetime.now()
        start = end - timedelta(days=days*2)  # Get extra for weekends
        hist = ticker.history(start=start, end=end)
        if len(hist) > 0:
            return hist.tail(days)
        return None
    except Exception as e:
        print(f"  ❌ {symbol}: {e}")
        return None

def calculate_score(df):
    """Calculate a simple momentum score"""
    if len(df) < 10:
        return 0
    
    # Price momentum (last 10 days)
    price_momentum = (df['Close'].iloc[-1] / df['Close'].iloc[-10] - 1) * 100
    
    # Volume surge (last 3 days vs previous 7 days)
    recent_vol = df['Volume'].iloc[-3:].mean()
    prev_vol = df['Volume'].iloc[-10:-3].mean()
    vol_surge = recent_vol / prev_vol if prev_vol > 0 else 1
    
    # Combined score
    score = price_momentum * vol_surge
    
    return score

def main():
    print("\n🚀 QUICK WATCHLIST GENERATOR")
    print("=" * 60)
    
    # Load universe
    with open('config/short_cycle_universe.json', 'r') as f:
        config = json.load(f)
    
    universe = config.get('base_universe', [])
    print(f"📋 Scanning {len(universe)} symbols...")
    
    # Fetch data and score
    candidates = []
    for i, symbol in enumerate(universe, 1):
        if i % 10 == 0:
            print(f"  Progress: {i}/{len(universe)}")
        
        df = get_data(symbol, days=30)
        if df is not None and len(df) >= 10:
            score = calculate_score(df)
            if score > 0:  # Only positive momentum
                candidates.append({
                    'symbol': symbol,
                    'score': float(score),
                    'price': float(df['Close'].iloc[-1]),
                    'volume': int(df['Volume'].iloc[-1])
                })
    
    # Sort by score
    candidates.sort(key=lambda x: x['score'], reverse=True)
    
    # Take top 15
    top_candidates = candidates[:15]
    
    print("\n" + "=" * 60)
    print(f"✅ FOUND {len(top_candidates)} TOP CANDIDATES")
    print("=" * 60)
    
    for i, c in enumerate(top_candidates, 1):
        print(f"  {i:2d}. {c['symbol']:6s} | Score: {c['score']:7.2f} | Price: ${c['price']:.2f}")
    
    # Save to file
    watchlist = {
        'generated_at': datetime.now(pytz.timezone('US/Eastern')).isoformat(),
        'symbols': [c['symbol'] for c in top_candidates],
        'count': len(top_candidates),
        'config': {
            'max_size': 15,
            'min_size': 8,
            'pipeline': 'quick_momentum_scan'
        },
        'details': top_candidates
    }
    
    output_file = 'logs/current_watchlist.json'
    with open(output_file, 'w') as f:
        json.dump(watchlist, f, indent=2)
    
    print(f"\n💾 Watchlist saved to: {output_file}")
    print("\n✅ Ready for tomorrow's trading!")
    print("=" * 60)

if __name__ == "__main__":
    main()

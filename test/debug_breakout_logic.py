#!/usr/bin/env python3
"""
Debug the exact breakout filter logic step by step.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def debug_breakout_filter_step_by_step():
    """Debug each step of the breakout filter logic."""
    print("🔍 DEBUGGING BREAKOUT FILTER STEP BY STEP")
    print("=" * 60)
    
    # Create simple test data for AAPL
    base_date = datetime.now() - timedelta(days=30)
    data = []
    
    # 29 days of normal data
    for i in range(29):
        date = base_date + timedelta(days=i)
        close = 100 + np.random.normal(0, 2)  # Around $100
        high = close + np.random.uniform(0, 1)
        low = close - np.random.uniform(0, 1)
        volume = 200000 + int(np.random.normal(0, 20000))
        
        data.append({
            'symbol': 'AAPL',
            'date': date.strftime('%Y-%m-%d'),
            'open': close,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume
        })
    
    # Day 30: Guaranteed breakout
    final_date = base_date + timedelta(days=29)
    breakout_high = 110  # Way above previous highs
    breakout_close = 109
    breakout_volume = 600000  # 3x normal volume
    
    data.append({
        'symbol': 'AAPL',
        'date': final_date.strftime('%Y-%m-%d'),
        'open': 108,
        'high': breakout_high,
        'low': 107,
        'close': breakout_close,
        'volume': breakout_volume
    })
    
    df = pd.DataFrame(data)
    print(f"Created {len(df)} rows of test data")
    print(f"Date range: {df['date'].min()} to {df['date'].max()}")
    print(f"Close range: ${df['close'].min():.2f} to ${df['close'].max():.2f}")
    print(f"Volume range: {df['volume'].min():,} to {df['volume'].max():,}")
    
    # Step 1: Copy and sort (like the filter does)
    work = df.copy().sort_values(['symbol', 'date'])
    print(f"\n✅ Step 1: Copied and sorted data")
    
    # Step 2: Calculate volume spike
    avg_volume_window = 20
    min_periods_frac = 0.5
    minp = max(5, int(avg_volume_window * min_periods_frac))
    print(f"\n📊 Step 2: Calculating volume spike (window={avg_volume_window}, min_periods={minp})")
    
    work['avg_volume_20'] = work.groupby('symbol')['volume'].transform(
        lambda x: x.rolling(avg_volume_window, min_periods=minp).mean()
    )
    work['volume_spike'] = work['volume'] / work['avg_volume_20']
    
    print(f"Volume spike calculation:")
    print(work[['date', 'volume', 'avg_volume_20', 'volume_spike']].tail(5))
    
    # Step 3: Calculate prior high
    prior_high_window = 20
    minp_high = max(5, int(prior_high_window * min_periods_frac))
    print(f"\n📈 Step 3: Calculating prior high (window={prior_high_window}, min_periods={minp_high})")
    
    work['prior_high_20'] = work.groupby('symbol')['high'].transform(
        lambda x: x.rolling(prior_high_window, min_periods=minp_high).max().shift(1)
    )
    work['price_breakout'] = (work['close'] - work['prior_high_20']) / work['prior_high_20']
    
    print(f"Price breakout calculation:")
    print(work[['date', 'high', 'close', 'prior_high_20', 'price_breakout']].tail(5))
    
    # Step 4: Get latest snapshot
    print(f"\n📸 Step 4: Getting latest snapshot per symbol")
    snap = work.groupby('symbol').tail(1)
    print(f"Latest snapshot:")
    print(snap[['symbol', 'date', 'volume_spike', 'price_breakout', 'prior_high_20']])
    
    # Step 5: Check conditions
    volume_spike_min = 1.0
    price_breakout_min = 0.005
    
    print(f"\n🎯 Step 5: Checking breakout conditions")
    print(f"Required: vol_spike >= {volume_spike_min}, price_breakout >= {price_breakout_min}")
    
    conditions = {
        'prior_high_notna': snap['prior_high_20'].notna(),
        'volume_spike_ok': snap['volume_spike'] >= volume_spike_min,
        'price_breakout_ok': snap['price_breakout'] >= price_breakout_min
    }
    
    for condition, result in conditions.items():
        print(f"  {condition}: {result.iloc[0] if len(result) > 0 else 'NO DATA'}")
    
    # Final check
    eligible = snap[
        (snap['prior_high_20'].notna()) &
        (snap['volume_spike'] >= volume_spike_min) &
        (snap['price_breakout'] >= price_breakout_min)
    ]['symbol'].tolist()
    
    print(f"\n🏆 FINAL RESULT: {len(eligible)} eligible symbols")
    if eligible:
        print(f"Eligible symbols: {eligible}")
        print("✅ BREAKOUT FILTER WORKING!")
    else:
        print("❌ NO SYMBOLS ELIGIBLE")
        
        # Debug why not
        latest = snap.iloc[0]
        print(f"\nDebug latest values:")
        print(f"  prior_high_20: {latest['prior_high_20']} (notna: {pd.notna(latest['prior_high_20'])})")
        print(f"  volume_spike: {latest['volume_spike']} (>= {volume_spike_min}: {latest['volume_spike'] >= volume_spike_min})")
        print(f"  price_breakout: {latest['price_breakout']} (>= {price_breakout_min}: {latest['price_breakout'] >= price_breakout_min})")
    
    return work

if __name__ == "__main__":
    debug_breakout_filter_step_by_step()
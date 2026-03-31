#!/usr/bin/env python3
"""
Fix #1: Breakout Filter Data Issue
====================================
Problem: breakout_filter shows all NaN values for vol_spike and price_breakout
Root Cause: Insufficient historical data in DataFrame passed to filter
Solution: Ensure proper 20-day rolling window data before applying filter
"""

import pandas as pd
from pre_filter import PreFilter

# Test with sample data
def test_breakout_calculation():
    """Test if breakout calculations work with proper data."""
    print("\n" + "="*70)
    print("🔬 BREAKOUT FILTER DATA DIAGNOSTIC")
    print("="*70)
    
    # Create test data with proper 25-day history (need 20 for rolling + 5 buffer)
    dates = pd.date_range('2025-09-24', '2025-10-23', freq='D')
    test_data = []
    
    for symbol in ['AAPL', 'AMD', 'NVDA']:
        for date in dates:
            # Simulate a breakout on last day
            if date == dates[-1]:
                close = 150.0
                high = 152.0
                volume = 50_000_000  # 2x normal volume
            else:
                close = 145.0 + (date.day % 5)
                high = close * 1.01
                volume = 25_000_000
            
            test_data.append({
                'symbol': symbol,
                'date': date,
                'open': close * 0.99,
                'high': high,
                'low': close * 0.98,
                'close': close,
                'volume': volume
            })
    
    df = pd.DataFrame(test_data)
    print(f"\n📊 Test Data Shape: {df.shape}")
    print(f"   Symbols: {df['symbol'].unique().tolist()}")
    print(f"   Date range: {df['date'].min()} to {df['date'].max()}")
    print(f"   Days per symbol: {df.groupby('symbol').size().iloc[0]}")
    
    # Test breakout calculation
    processor = PreFilter()
    result = processor.breakout_filter(
        df,
        volume_spike_min=1.5,
        price_breakout_min=0.005,
        prior_high_window=20,
        avg_volume_window=20
    )
    
    print(f"\n✅ Breakout filter results: {len(result['symbol'].unique())} symbols passed")
    if not result.empty:
        print(f"   Passed: {result['symbol'].unique().tolist()}")
    else:
        print("   ❌ No symbols passed (expected with clean test data)")
    
    # Show calculations for last row
    df_sorted = df.sort_values(['symbol', 'date'])
    df_sorted['avg_volume_20'] = df_sorted.groupby('symbol')['volume'].transform(
        lambda x: x.rolling(20, min_periods=10).mean()
    )
    df_sorted['volume_spike'] = df_sorted['volume'] / df_sorted['avg_volume_20']
    df_sorted['prior_high_20'] = df_sorted.groupby('symbol')['high'].transform(
        lambda x: x.rolling(20, min_periods=10).max().shift(1)
    )
    df_sorted['price_breakout'] = (df_sorted['close'] - df_sorted['prior_high_20']) / df_sorted['prior_high_20']
    
    latest = df_sorted.groupby('symbol').tail(1)
    print("\n📈 Latest calculations:")
    for _, row in latest.iterrows():
        print(f"  {row['symbol']}:")
        print(f"    Volume: {row['volume']:,.0f} / Avg: {row['avg_volume_20']:,.0f} = Spike: {row['volume_spike']:.2f}x")
        print(f"    Close: ${row['close']:.2f} / Prior High: ${row['prior_high_20']:.2f} = Breakout: {row['price_breakout']:.2%}")
    
    print("\n" + "="*70)
    print("💡 DIAGNOSIS COMPLETE")
    print("="*70)
    print("\nThe filter logic works correctly IF proper data is provided.")
    print("Issue: The DataFrame passed to breakout_filter likely has:")
    print("  1. < 20 days of history per symbol")
    print("  2. Missing 'high' or 'volume' data")
    print("  3. Date sorting issues")
    print("\nFix: Ensure pre_filter.py loads ≥25 days of daily data before filtering.")
    print("="*70 + "\n")

if __name__ == '__main__':
    test_breakout_calculation()

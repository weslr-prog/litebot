#!/usr/bin/env python3
"""
Test Extended yfinance Data Filtering
Tests: earnings dates, institutional ownership, float, sector tagging
"""

import pandas as pd
from pre_filter import PreFilter

print("=" * 70)
print("Testing Extended yfinance Data Filtering")
print("=" * 70)

# Create test DataFrame with mid-cap symbols (more realistic for swing trading)
test_symbols = ['WMT', 'BAC', 'V', 'MA', 'HD', 'COST', 'PEP', 'ABBV']
df = pd.DataFrame({
    'symbol': test_symbols,
    'close': [78, 38, 275, 480, 380, 805, 170, 190],
    'volume': [5000000] * len(test_symbols),
    'pf_score': [0.5] * len(test_symbols)
})

print(f"\n📊 Test 1: Extended yfinance Filtering")
print(f"Input: {len(test_symbols)} mid-cap symbols")
print("-" * 70)

# Initialize PreFilter
pf = PreFilter(simulation_mode=False, fast_mode=True)

# Test extended filtering
filtered_df = pf.extended_yfinance_filter(
    df,
    filter_earnings=True,
    filter_ownership=True,
    filter_float=True,
    add_sector=True
)

print(f"\n✅ Results:")
print(f"   Filtered: {len(filtered_df['symbol'].unique())}/{len(test_symbols)} symbols passed")

if 'sector' in filtered_df.columns:
    print(f"\n📊 Sector Distribution:")
    for sector, count in filtered_df['sector'].value_counts().items():
        print(f"   {sector}: {count}")

print(f"\n✅ Symbols passed: {filtered_df['symbol'].unique().tolist()}")
print(f"❌ Symbols filtered: {[s for s in test_symbols if s not in filtered_df['symbol'].unique()]}")

print("\n" + "=" * 70)
print("✅ Extended yfinance filtering test complete!")
print("=" * 70)

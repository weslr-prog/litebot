#!/usr/bin/env python3
"""
Test Optimized bot_v2 PreFilter and Signal Generation
Validates simplified 3-stage filter with 150-stock universe
"""

import sys
import json
from pathlib import Path

# Add bot_v2 to path
sys.path.insert(0, str(Path(__file__).parent))

from bot_v2.config.prefilter_config import (
    SIMPLE_PREFILTER_CONFIG,
    MEAN_REVERSION_CONFIG,
    UNIVERSE_CONFIG
)
from data_loader import DataLoader
import pandas as pd
import time

def load_curated_universe():
    """Load 150-stock curated universe"""
    universe_path = Path(__file__).parent / 'bot_v2' / 'data' / 'mid_cap_universe.json'
    
    with open(universe_path, 'r') as f:
        data = json.load(f)
    
    # Flatten all sectors
    all_stocks = []
    for sector in ['technology', 'consumer_discretionary', 'healthcare_biotech', 
                   'financials', 'energy_clean', 'industrials', 'communication', 
                   'materials_commodities']:
        if sector in data:
            all_stocks.extend(data[sector])
    
    return list(set(all_stocks))  # Remove duplicates


def test_simple_prefilter():
    """Test simplified 3-stage PreFilter"""
    print("=" * 80)
    print("🧪 TESTING OPTIMIZED bot_v2 PREFILTER")
    print("=" * 80)
    print()
    
    # Load universe
    print("📊 Loading curated 150-stock universe...")
    universe = load_curated_universe()
    print(f"✅ Loaded {len(universe)} stocks")
    print()
    
    # Initialize data loader
    print("📡 Initializing data loader...")
    data_loader = DataLoader()
    print("✅ Data loader ready")
    print()
    
    # Fetch data
    print(f"📥 Fetching data for {len(universe)} stocks (this may take 10-15 seconds)...")
    start_time = time.time()
    
    all_data = []
    successful = 0
    failed = 0
    
    for i, symbol in enumerate(universe, 1):
        if i % 20 == 0:
            print(f"   Progress: {i}/{len(universe)} stocks...")
        
        try:
            df = data_loader.get_historical_data(symbol, days=30)
            if df is not None and not df.empty and len(df) >= 15:
                df['symbol'] = symbol
                all_data.append(df)
                successful += 1
            else:
                failed += 1
        except Exception:
            failed += 1
    
    fetch_time = time.time() - start_time
    print(f"✅ Data fetch complete: {successful} successful, {failed} failed ({fetch_time:.1f}s)")
    print()
    
    if not all_data:
        print("❌ No data fetched - cannot continue test")
        return
    
    # Combine data
    combined_df = pd.concat(all_data, ignore_index=True)
    print(f"📊 Combined DataFrame: {len(combined_df)} rows, {combined_df['symbol'].nunique()} symbols")
    print()
    
    # Apply simplified 3-stage filter
    print("🔍 Applying Simplified 3-Stage PreFilter...")
    print("-" * 80)
    
    config = SIMPLE_PREFILTER_CONFIG
    
    # Stage 1: Price Filter
    print(f"\n📌 STAGE 1: Price Range Filter")
    print(f"   Range: ${config['min_price']:.0f} - ${config['max_price']:.0f}")
    
    latest_prices = combined_df.groupby('symbol')['close'].last()
    stage1_symbols = latest_prices[
        (latest_prices >= config['min_price']) & 
        (latest_prices <= config['max_price'])
    ].index.tolist()
    
    stage1_df = combined_df[combined_df['symbol'].isin(stage1_symbols)]
    print(f"   ✅ Passed: {len(stage1_symbols)} / {combined_df['symbol'].nunique()} stocks")
    
    if stage1_df.empty:
        print("❌ No stocks passed price filter")
        return
    
    # Stage 2: Volume Filter
    print(f"\n📌 STAGE 2: Volume Filter")
    print(f"   Min Volume: {config['min_volume']:,} shares")
    print(f"   Min Dollar Volume: ${config['min_dollar_volume']:,}")
    
    stage2_df = stage1_df.copy()
    stage2_df['dollar_volume'] = stage2_df['volume'] * stage2_df['close']
    stage2_df['avg_volume'] = stage2_df.groupby('symbol')['volume'].transform(
        lambda x: x.rolling(20, min_periods=10).mean()
    )
    stage2_df['avg_dollar_volume'] = stage2_df.groupby('symbol')['dollar_volume'].transform(
        lambda x: x.rolling(20, min_periods=10).mean()
    )
    
    stage2_filtered = stage2_df[
        (stage2_df['avg_volume'] >= config['min_volume']) &
        (stage2_df['avg_dollar_volume'] >= config['min_dollar_volume'])
    ]
    stage2_symbols = stage2_filtered['symbol'].unique().tolist()
    
    print(f"   ✅ Passed: {len(stage2_symbols)} / {len(stage1_symbols)} stocks")
    
    if not stage2_symbols:
        print("❌ No stocks passed volume filter")
        return
    
    # Stage 3: Volatility Filter
    print(f"\n📌 STAGE 3: Volatility Filter (ATR%)")
    print(f"   Range: {config['min_atr_pct']*100:.1f}% - {config['max_atr_pct']*100:.1f}%")
    
    stage3_df = stage2_filtered.copy()
    
    # Calculate ATR
    high_low = (stage3_df['high'] - stage3_df['low']).abs()
    high_close = (stage3_df['high'] - stage3_df['close'].shift(1)).abs()
    low_close = (stage3_df['low'] - stage3_df['close'].shift(1)).abs()
    stage3_df['true_range'] = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    stage3_df['atr_14'] = stage3_df.groupby('symbol')['true_range'].transform(
        lambda x: x.rolling(14, min_periods=7).mean()
    )
    stage3_df['atr_pct'] = stage3_df['atr_14'] / stage3_df['close']
    
    # Filter by volatility
    latest_volatility = stage3_df.groupby('symbol')['atr_pct'].last()
    stage3_symbols = latest_volatility[
        (latest_volatility >= config['min_atr_pct']) &
        (latest_volatility <= config['max_atr_pct'])
    ].index.tolist()
    
    print(f"   ✅ Passed: {len(stage3_symbols)} / {len(stage2_symbols)} stocks")
    print()
    
    # Final Results
    print("=" * 80)
    print("📊 PREFILTER RESULTS")
    print("=" * 80)
    print(f"Input Universe: {len(universe)} stocks")
    print(f"Data Available: {successful} stocks")
    print(f"Stage 1 (Price): {len(stage1_symbols)} stocks")
    print(f"Stage 2 (Volume): {len(stage2_symbols)} stocks")
    print(f"Stage 3 (Volatility): {len(stage3_symbols)} stocks")
    print()
    print(f"✅ FINAL CANDIDATES: {len(stage3_symbols)} stocks")
    print(f"   Target Range: {config['target_min_candidates']}-{config['target_max_candidates']}")
    
    if len(stage3_symbols) < config['target_min_candidates']:
        print(f"   ⚠️ WARNING: Below target minimum ({config['target_min_candidates']})")
    elif len(stage3_symbols) > config['target_max_candidates']:
        print(f"   ⚠️ WARNING: Above target maximum ({config['target_max_candidates']})")
    else:
        print(f"   ✅ Within target range!")
    
    print()
    print(f"🎯 Quality Candidates:")
    for symbol in sorted(stage3_symbols)[:20]:  # Show first 20
        vol = latest_volatility.get(symbol, 0) * 100
        price = latest_prices.get(symbol, 0)
        print(f"   {symbol:6s}: ${price:6.2f} | ATR: {vol:4.1f}%")
    
    if len(stage3_symbols) > 20:
        print(f"   ... and {len(stage3_symbols) - 20} more")
    
    print()
    print(f"⏱️  Total Time: {fetch_time:.1f}s (Target: <10s)")
    
    if fetch_time > 10:
        print(f"   ⚠️ WARNING: Scan took longer than target 10s")
    else:
        print(f"   ✅ Within performance target!")
    
    print()
    print("=" * 80)
    print("✅ TEST COMPLETE")
    print("=" * 80)
    
    return stage3_symbols


if __name__ == "__main__":
    try:
        candidates = test_simple_prefilter()
        
        if candidates:
            print(f"\n💾 Saving {len(candidates)} candidates to bot_v2/data/test_candidates.json...")
            output_path = Path(__file__).parent / 'bot_v2' / 'data' / 'test_candidates.json'
            with open(output_path, 'w') as f:
                json.dump({
                    'timestamp': pd.Timestamp.now().isoformat(),
                    'count': len(candidates),
                    'candidates': candidates
                }, f, indent=2)
            print(f"✅ Saved to {output_path}")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

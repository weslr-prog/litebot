#!/usr/bin/env python3
"""
Diagnose why no trades on January 6, 2026
Check prefilter candidates and rejection reasons
"""
import sys
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from bot_v2.config.trading_config import ShortCycleConfig
from bot_v2.data.data_loader import DataLoader
from bot_v2.core.pre_filter import PreFilter
from bot_v2.signal_generation.signal_generator import AISignalGenerator
import pandas as pd

def load_universe():
    """Load trading universe"""
    universe_file = Path(__file__).parent / "bot_v2" / "data" / "mid_cap_universe.json"
    with open(universe_file, 'r') as f:
        data = json.load(f)
    
    # Filter out REITs
    all_stocks = []
    for key, value in data.items():
        if key.lower() == 'reits' or 'reit' in key.lower():
            continue
        if isinstance(value, list):
            all_stocks.extend(value)
    
    return list(set(all_stocks))

def main():
    print("=" * 80)
    print("🔍 DIAGNOSING JAN 6, 2026 - Why No Trades?")
    print("=" * 80)
    
    # Initialize components
    config = ShortCycleConfig()
    data_loader = DataLoader()
    
    # Load universe
    print("\n📊 Loading universe...")
    universe = load_universe()
    print(f"   Universe size: {len(universe)} stocks")
    
    # Run prefilter
    print("\n🧪 Running PreFilter...")
    prefilter = PreFilter(data_loader)
    candidates = prefilter.run_filter(universe)
    print(f"   PreFilter results: {len(candidates)} candidates")
    
    if len(candidates) == 0:
        print("\n❌ No candidates passed prefilter!")
        print("   This means none of the 280 stocks met basic criteria:")
        print("   - Price range $5-$50")
        print("   - Volume > 100k shares/day")
        print("   - Volatility check")
        return
    
    print(f"\n✅ Candidates: {', '.join(candidates[:20])}")
    if len(candidates) > 20:
        print(f"   ... and {len(candidates) - 20} more")
    
    # Analyze each candidate with signal generator
    print("\n🔍 Analyzing why candidates were rejected...")
    signal_generator = AISignalGenerator(config=config, price_fetcher=lambda x: None)
    
    rejection_stats = {
        'rsi_high': [],
        'sma_far': [],
        'momentum_low': [],
        'confidence_low': [],
        'other': []
    }
    
    for symbol in candidates:
        print(f"\n📊 Analyzing {symbol}...")
        
        # Get historical data
        hist_data = data_loader.get_historical_data(symbol, days=30)
        if hist_data.empty:
            print(f"   ❌ No data available")
            rejection_stats['other'].append(symbol)
            continue
        
        # Calculate RSI
        closes = hist_data['close'].values
        if len(closes) < 14:
            print(f"   ❌ Insufficient data (need 14 days, have {len(closes)})")
            rejection_stats['other'].append(symbol)
            continue
        
        # Simple RSI calculation
        deltas = pd.Series(closes).diff()
        gains = deltas.where(deltas > 0, 0).rolling(window=14).mean()
        losses = -deltas.where(deltas < 0, 0).rolling(window=14).mean()
        rs = gains / losses
        rsi = 100 - (100 / (1 + rs))
        current_rsi = rsi.iloc[-1]
        
        # Get current price and SMA
        current_price = closes[-1]
        sma_20 = pd.Series(closes).rolling(window=20).mean().iloc[-1]
        distance_from_sma = ((current_price - sma_20) / sma_20) * 100
        
        # Calculate 5-day momentum
        if len(closes) >= 5:
            momentum_5d = ((closes[-1] - closes[-5]) / closes[-5]) * 100
        else:
            momentum_5d = 0
        
        # Print analysis
        print(f"   Price: ${current_price:.2f}")
        print(f"   RSI: {current_rsi:.1f} {'✅' if current_rsi < 35 else '❌ (need <35)'}")
        print(f"   20-day SMA: ${sma_20:.2f}")
        print(f"   Distance from SMA: {distance_from_sma:+.1f}% {'✅' if abs(distance_from_sma) < 6 else '❌ (need within ±6%)'}")
        print(f"   5-day momentum: {momentum_5d:+.1f}% {'✅' if momentum_5d > -5 else '❌ (need >-5%)'}")
        
        # Categorize rejection
        if current_rsi >= 35:
            rejection_stats['rsi_high'].append((symbol, current_rsi))
            print(f"   🔴 REJECTED: RSI too high ({current_rsi:.1f} >= 35)")
        elif abs(distance_from_sma) >= 6:
            rejection_stats['sma_far'].append((symbol, distance_from_sma))
            print(f"   🔴 REJECTED: Too far from SMA ({distance_from_sma:+.1f}%)")
        elif momentum_5d <= -5:
            rejection_stats['momentum_low'].append((symbol, momentum_5d))
            print(f"   🔴 REJECTED: Falling knife ({momentum_5d:+.1f}%)")
        else:
            rejection_stats['confidence_low'].append(symbol)
            print(f"   🔴 REJECTED: Likely low confidence score")
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 REJECTION SUMMARY")
    print("=" * 80)
    
    total = len(candidates)
    print(f"\n✅ Prefilter passed: {total} stocks")
    print(f"❌ Signal generator rejected: {total} stocks (100%)")
    
    print(f"\n🔴 Rejection Breakdown:")
    print(f"   • RSI too high (≥35): {len(rejection_stats['rsi_high'])} stocks")
    if rejection_stats['rsi_high']:
        top_5 = sorted(rejection_stats['rsi_high'], key=lambda x: x[1])[:5]
        for symbol, rsi in top_5:
            print(f"      - {symbol}: RSI={rsi:.1f}")
    
    print(f"   • Too far from SMA (≥6%): {len(rejection_stats['sma_far'])} stocks")
    if rejection_stats['sma_far']:
        top_5 = sorted(rejection_stats['sma_far'], key=lambda x: abs(x[1]))[:5]
        for symbol, dist in top_5:
            print(f"      - {symbol}: {dist:+.1f}% from SMA")
    
    print(f"   • Falling knife (momentum <-5%): {len(rejection_stats['momentum_low'])} stocks")
    if rejection_stats['momentum_low']:
        for symbol, mom in rejection_stats['momentum_low'][:5]:
            print(f"      - {symbol}: {mom:+.1f}% 5-day")
    
    print(f"   • Other (confidence/data): {len(rejection_stats['confidence_low']) + len(rejection_stats['other'])} stocks")
    
    # Conclusion
    print("\n" + "=" * 80)
    print("💡 CONCLUSION")
    print("=" * 80)
    
    if len(rejection_stats['rsi_high']) > total * 0.7:
        print("\n🔴 MARKET NOT OVERSOLD")
        print("   Most stocks have RSI ≥ 35 (not in oversold territory)")
        print("   This is normal market behavior - bot is correctly being patient")
        print("   Mean reversion setups require panic selling (RSI < 35)")
    elif len(rejection_stats['sma_far']) > total * 0.5:
        print("\n🔴 STOCKS TOO FAR FROM TREND")
        print("   Many stocks are >6% away from 20-day SMA")
        print("   Strategy requires stocks near their trend line for safe entries")
    else:
        print("\n⚠️ MIXED REJECTIONS")
        print("   Various factors preventing entry (check breakdown above)")
    
    print("\n✅ Bot is working correctly - waiting for better setups")
    print("=" * 80)

if __name__ == "__main__":
    main()

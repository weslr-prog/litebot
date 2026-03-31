#!/usr/bin/env python3
"""
Show confidence scores for all candidates - including rejections
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from bot_v2.data.data_loader import DataLoader
from bot_v2.core.pre_filter import PreFilter
import pandas as pd
import json

def load_universe():
    universe_file = Path(__file__).parent / "bot_v2" / "data" / "mid_cap_universe.json"
    with open(universe_file, 'r') as f:
        data = json.load(f)
    all_stocks = []
    for key, value in data.items():
        if key.lower() == 'reits' or 'reit' in key.lower():
            continue
        if isinstance(value, list):
            all_stocks.extend(value)
    return list(set(all_stocks))

def calculate_stats(symbol, data_loader):
    """Calculate RSI, SMA distance, momentum for a symbol"""
    hist_data = data_loader.get_historical_data(symbol, days=30)
    if hist_data.empty or len(hist_data) < 20:
        return None
    
    closes = hist_data['close'].values
    
    # RSI
    deltas = pd.Series(closes).diff()
    gains = deltas.where(deltas > 0, 0).rolling(window=14).mean()
    losses = -deltas.where(deltas < 0, 0).rolling(window=14).mean()
    rs = gains / losses
    rsi = 100 - (100 / (1 + rs))
    current_rsi = rsi.iloc[-1]
    
    # SMA
    current_price = closes[-1]
    sma_20 = pd.Series(closes).rolling(window=20).mean().iloc[-1]
    sma_dist = ((current_price - sma_20) / sma_20) * 100
    
    # Momentum
    mom_5d = ((closes[-1] - closes[-5]) / closes[-5]) * 100 if len(closes) >= 5 else 0
    
    # Confidence (using bot's formula)
    confidence = max((35 - current_rsi) / 20.0, 0.0)
    
    return {
        'rsi': current_rsi,
        'sma_dist': sma_dist,
        'momentum': mom_5d,
        'confidence': confidence,
        'price': current_price
    }

print("=" * 100)
print("📊 CONFIDENCE SCORES FOR ALL CANDIDATES (Jan 6, 2026)")
print("=" * 100)

data_loader = DataLoader()
universe = load_universe()
prefilter = PreFilter(data_loader)
candidates = prefilter.run_filter(universe)

print(f"\nAnalyzing {len(candidates)} prefilter candidates...")
print(f"Confidence threshold: 25% (0.25)\n")

results = []
for symbol in candidates:
    stats = calculate_stats(symbol, data_loader)
    if stats:
        results.append((symbol, stats))

# Sort by confidence descending
results.sort(key=lambda x: x[1]['confidence'], reverse=True)

print(f"{'Symbol':<8} {'RSI':<7} {'Conf%':<8} {'SMA%':<8} {'Mom%':<8} {'Status':<15} {'Reason'}")
print("-" * 100)

passing = []
failing = []

for symbol, stats in results:
    rsi = stats['rsi']
    conf = stats['confidence']
    sma = stats['sma_dist']
    mom = stats['momentum']
    
    # Determine status
    reasons = []
    if rsi >= 35:
        reasons.append("RSI≥35")
    if abs(sma) >= 6:
        reasons.append("SMA>6%")
    if mom <= -5:
        reasons.append("Mom<-5%")
    if conf < 0.25:
        reasons.append("Conf<25%")
    
    if not reasons:
        status = "✅ PASS"
        passing.append(symbol)
    else:
        status = "❌ REJECT"
        failing.append(symbol)
    
    reason_str = ", ".join(reasons) if reasons else "All checks pass"
    
    print(f"{symbol:<8} {rsi:>6.1f} {conf:>7.1%} {sma:>+7.1f}% {mom:>+7.1f}% {status:<15} {reason_str}")

print("=" * 100)
print(f"\n📈 SUMMARY:")
print(f"   Total candidates: {len(results)}")
print(f"   ✅ Passing all filters: {len(passing)}")
print(f"   ❌ Rejected: {len(failing)}")

if passing:
    print(f"\n✅ STOCKS THAT SHOULD TRADE TODAY:")
    for sym in passing:
        stats = next(s for symbol, s in results if symbol == sym)
        print(f"   • {sym}: RSI {stats['rsi']:.1f}, Confidence {stats['confidence']:.1%}")

print("\n" + "=" * 100)

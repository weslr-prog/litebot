#!/usr/bin/env python3
"""
Test signal generation with 25% confidence threshold
See if any stocks qualify today
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from bot_v2.config.trading_config import ShortCycleConfig
from bot_v2.data.data_loader import DataLoader
from bot_v2.signal_generation.signal_generator import AISignalGenerator
from bot_v2.core.pre_filter import PreFilter
import json

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

print("=" * 80)
print("🧪 TESTING WITH 25% CONFIDENCE THRESHOLD")
print("=" * 80)

# Initialize with 25% threshold
config = ShortCycleConfig()
print(f"\n✅ Config loaded - Confidence threshold: {config.confidence_threshold:.0%}")

# Load data
data_loader = DataLoader()
universe = load_universe()
print(f"✅ Universe loaded: {len(universe)} stocks")

# Run prefilter
print("\n🔍 Running PreFilter...")
prefilter = PreFilter(data_loader)
candidates = prefilter.run_filter(universe)
print(f"✅ PreFilter: {len(candidates)} candidates")

if len(candidates) == 0:
    print("\n❌ No candidates from prefilter - can't test signal generation")
    sys.exit(1)

# Test signal generation
print(f"\n🎯 Running Signal Generator on {len(candidates)} candidates...")
signal_generator = AISignalGenerator(config=config, price_fetcher=lambda x: None)

signals = []
for symbol in candidates:  # Test ALL candidates
    print(f"  Testing {symbol}...", end=" ")
    hist_data = data_loader.get_historical_data(symbol, days=30)
    if hist_data.empty:
        print(f"⚠️ No data")
        continue
    
    signal = signal_generator._analyze_symbol(symbol=symbol, data=hist_data)
    
    if signal:
        signals.append(signal)
        print(f"✅ SIGNAL! Confidence: {signal.confidence:.1%}")
    else:
        print("❌")

print("\n" + "=" * 80)
print("📊 RESULTS")
print("=" * 80)
print(f"\nCandidates tested: {len(candidates)}")
print(f"Signals generated: {len(signals)}")

if signals:
    print(f"\n✅ SUCCESS - Signals generated with 25% threshold:")
    for sig in signals:
        print(f"   • {sig.symbol}: {sig.confidence:.1%} confidence | Entry: ${sig.entry_price:.2f}")
else:
    print(f"\n⚠️ No signals generated even with 25% threshold")
    print("   This suggests today's market truly has no viable setups")

print("\n" + "=" * 80)

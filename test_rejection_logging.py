#!/usr/bin/env python3
"""Quick test of rejection logging with confidence scores"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from bot_v2.config.trading_config import ShortCycleConfig
from bot_v2.data.data_loader import DataLoader
from bot_v2.signal_generation.signal_generator import AISignalGenerator

print("Testing confidence score logging...\n")

config = ShortCycleConfig()
print(f"Confidence threshold: {config.confidence_threshold:.0%}\n")

data_loader = DataLoader()
signal_generator = AISignalGenerator(config=config, price_fetcher=lambda x: None)

# Test with a few stocks
test_stocks = ['WEN', 'KDP', 'CLF', 'AI', 'VIPS']
market_data = {}

for symbol in test_stocks:
    data = data_loader.get_historical_data(symbol, days=30)
    if not data.empty:
        market_data[symbol] = data

print(f"Loaded data for {len(market_data)} stocks")
print("Generating signals...\n")

signals = signal_generator.generate_signals(
    universe=test_stocks,
    market_data=market_data,
    active_positions=[]
)

print(f"\n✅ Generated {len(signals)} signals")
for sig in signals:
    print(f"   • {sig.symbol}: {sig.confidence:.1%} confidence")

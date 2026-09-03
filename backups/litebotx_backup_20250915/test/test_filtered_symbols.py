#!/usr/bin/env python3
import pandas as pd
from core.data_loader import DataLoader
from core.pre_filter import PreFilter
from core.data_fetcher import DataFetcher
from core.strategy import StrategyEngine
from datetime import datetime, timedelta, timezone

# Load and filter symbols like in main.py
print("Loading universe...")
data_loader = DataLoader(api_key="test", api_secret="test")
pre_filter = PreFilter()
universe = data_loader.load_universe()
print(f'Loaded {len(universe)} symbols from universe')

# Apply filters
print("Applying filters...")
filtered = pre_filter.filter_symbols(universe)
print(f'After filtering: {len(filtered)} symbols')

# Test with first 10 filtered symbols
test_symbols = filtered.head(10)['symbol'].tolist() if not filtered.empty else []
print(f'Testing with symbols: {test_symbols[:5]}...')

# Test each symbol
fetcher = DataFetcher()
strategy_engine = StrategyEngine()
signal_counts = {'buy': 0, 'sell': 0, 'hold': 0}

for i, symbol in enumerate(test_symbols):
    try:
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=365)
        data = fetcher.fetch_data(symbol, timeframe='1D', start=start_date, end=end_date)
        
        if data is None or len(data) < 10:
            print(f'{symbol}: Insufficient data')
            signal = 'hold'
        else:
            signal = strategy_engine.predict(data)
            print(f'{symbol}: {signal} (data shape: {data.shape})')
        
        signal_counts[signal] = signal_counts.get(signal, 0) + 1
        
    except Exception as e:
        print(f'{symbol}: ERROR - {e}')
        signal_counts['hold'] = signal_counts.get('hold', 0) + 1

print(f'\nFinal signal counts: {signal_counts}')

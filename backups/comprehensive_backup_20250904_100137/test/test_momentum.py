#!/usr/bin/env python3

import pandas as pd
import numpy as np
import sys
import os
from core.data_loader import DataLoader
from core.momentum_strategy import MomentumStrategy

# Test the momentum strategy
def test_momentum():
    print("🧪 Testing Phase 1 Momentum Strategy")
    print("=" * 50)
    
    # Initialize
    data_loader = DataLoader()
    momentum_strategy = MomentumStrategy()
    
    # Load universe (just a few symbols for quick test)
    test_symbols = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA']
    
    universe_data = {}
    for symbol in test_symbols:
        try:
            data = data_loader.get_historical_data(symbol, limit=100)
            if data is not None and len(data) > 63:  # Need at least 63 days
                # Ensure we have the right columns
                if 'close' in data.columns and 'volume' in data.columns:
                    universe_data[symbol] = data
                    print(f"✅ {symbol}: {len(data)} bars loaded")
                else:
                    print(f"⚠️ {symbol}: Missing required columns")
            else:
                print(f"❌ {symbol}: Insufficient data ({len(data) if data is not None else 0} bars)")
        except Exception as e:
            print(f"❌ {symbol}: Error loading - {e}")
    
    print(f"\n📊 Loaded data for {len(universe_data)} symbols")
    
    if len(universe_data) >= 3:  # Need at least 3 symbols for ranking
        print("\n🚀 Generating momentum signals...")
        signals = momentum_strategy.generate_signals(universe_data, portfolio_value=10000)
        
        if signals:
            print(f"\n✅ Generated {len(signals)} signals:")
            print("Rank | Symbol | Position Value | Weight | Momentum Score | Volatility")
            print("-" * 75)
            for i, signal in enumerate(signals, 1):
                print(f"{i:4d} | {signal['symbol']:6s} | ${signal['position_value']:10.0f} | "
                      f"{signal['weight']:6.1%} | {signal['momentum_score']:13.3f} | "
                      f"{signal['volatility']:10.3f}")
            
            total_allocation = sum(s['weight'] for s in signals)
            print(f"\nTotal Portfolio Allocation: {total_allocation:.1%}")
            
            return True
        else:
            print("❌ No signals generated")
            return False
    else:
        print("❌ Need at least 3 symbols for testing")
        return False

if __name__ == "__main__":
    success = test_momentum()
    sys.exit(0 if success else 1)

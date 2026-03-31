#!/usr/bin/env python3
"""
Smoke test for current price retrieval via DataLoader.
Prints current price for a few symbols using Alpaca (IEX) if configured, else yfinance fallback.
"""
import sys
from data_loader import DataLoader

def main(symbols):
    dl = DataLoader()
    for s in symbols:
        try:
            price = dl.get_current_price(s)
            print(f"{s}: {price}")
        except Exception as e:
            print(f"{s}: ERROR {e}")

if __name__ == "__main__":
    symbols = sys.argv[1:] or ["AAPL", "MSFT", "SPY"]
    main(symbols)

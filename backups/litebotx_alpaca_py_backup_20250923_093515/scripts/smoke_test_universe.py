#!/usr/bin/env python3
import sys
import os

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(REPO_ROOT)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from traders.short_cycle_trader import ShortCycleTrader

def main():
    trader = ShortCycleTrader()
    universe = trader._get_trading_universe()
    print(f"Universe size: {len(universe)}")
    print(universe)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Manual Alpaca Connectivity Test Script
Forces a buy and sell to verify API and order routing.
"""
from connect_real_trading import RealPaperTradingEngine
import time

if __name__ == "__main__":
    engine = RealPaperTradingEngine()
    symbol = "AAPL"
    qty = 1

    print(f"\n--- FORCED BUY TEST ---")
    buy_result = engine.submit_order(symbol, qty, side='buy')
    print(f"Buy order result: {buy_result}")

    # Wait a few seconds for order to fill
    time.sleep(5)

    print(f"\n--- FORCED SELL TEST ---")
    sell_result = engine.submit_order(symbol, qty, side='sell')
    print(f"Sell order result: {sell_result}")

    print("\nCheck your Alpaca dashboard for order status and fills.")

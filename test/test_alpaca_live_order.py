#!/usr/bin/env python3
"""
Test Alpaca API connectivity and ability to open/close a position.
This will place a small test order (buy 1 share of AAPL) and then attempt to close it.
"""
import os
import time
from alpaca_trade_api.rest import REST, TimeFrame
from dotenv import load_dotenv

# Load API keys from .env or environment
load_dotenv()
API_KEY = os.getenv('APCA_API_KEY_ID')
API_SECRET = os.getenv('APCA_API_SECRET_KEY')
BASE_URL = os.getenv('APCA_API_BASE_URL', 'https://paper-api.alpaca.markets')

assert API_KEY and API_SECRET, "Alpaca API keys not found in environment!"

api = REST(API_KEY, API_SECRET, BASE_URL)

symbol = 'AAPL'
qty = 1

print(f"🧪 Placing test BUY order for {qty} share of {symbol}...")
order = api.submit_order(symbol=symbol, qty=qty, side='buy', type='market', time_in_force='gtc')
print(f"Order submitted: {order.id}")

# Wait for fill
for _ in range(10):
    o = api.get_order(order.id)
    if o.filled_at:
        print(f"✅ Buy order filled at {o.filled_avg_price}")
        break
    print("Waiting for fill...")
    time.sleep(2)
else:
    print("❌ Buy order not filled in time!")
    exit(1)

# Now close the position
print(f"🧪 Closing position for {symbol}...")
close = api.submit_order(symbol=symbol, qty=qty, side='sell', type='market', time_in_force='gtc')
print(f"Sell order submitted: {close.id}")

for _ in range(10):
    o = api.get_order(close.id)
    if o.filled_at:
        print(f"✅ Sell order filled at {o.filled_avg_price}")
        break
    print("Waiting for sell fill...")
    time.sleep(2)
else:
    print("❌ Sell order not filled in time!")
    exit(1)

print("✅ Alpaca open/close test complete!")

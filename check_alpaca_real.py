#!/usr/bin/env python3
"""
Check Alpaca Account - What's Really There
"""
import sys
sys.path.insert(0, '.')

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetOrdersRequest
from alpaca.trading.enums import OrderSide, QueryOrderStatus
from datetime import datetime, timedelta
import pytz

print("=" * 80)
print("🔍 Checking Real Alpaca Account")
print("=" * 80)

# Load credentials
import os
api_key = os.environ.get('APCA_API_KEY_ID')
secret_key = os.environ.get('APCA_API_SECRET_KEY')

if not api_key or not secret_key:
    print("❌ Alpaca credentials not found in environment")
    print("   Set APCA_API_KEY_ID and APCA_API_SECRET_KEY")
    sys.exit(1)

# Initialize Alpaca client
client = TradingClient(api_key, secret_key, paper=True)

# Get account
account = client.get_account()
print(f"\n💰 Account Balance:")
print(f"   Equity: ${float(account.equity):,.2f}")
print(f"   Cash: ${float(account.cash):,.2f}")
print(f"   Buying Power: ${float(account.buying_power):,.2f}")

# Get current positions
positions = client.get_all_positions()
print(f"\n📊 Current Positions: {len(positions)}")
if positions:
    for pos in positions:
        qty = float(pos.qty)
        entry = float(pos.avg_entry_price)
        current = float(pos.current_price)
        pnl = float(pos.unrealized_pl)
        pnl_pct = float(pos.unrealized_plpc) * 100
        print(f"   {pos.symbol:6s} {qty:>8.2f} shares @ ${entry:>8.2f} → ${current:>8.2f} | "
              f"P&L: ${pnl:>8.2f} ({pnl_pct:>+6.2f}%)")
else:
    print("   No open positions")

# Get today's orders
et_tz = pytz.timezone('US/Eastern')
today = datetime.now(et_tz).date()

print(f"\n📋 Today's Orders ({today}):")

# Get all recent orders
request = GetOrdersRequest(
    status=QueryOrderStatus.ALL,
    limit=100
)
orders = client.get_orders(filter=request)

today_orders = [o for o in orders if o.created_at.date() == today]

if today_orders:
    for order in today_orders:
        print(f"\n   {order.symbol:6s} {order.side.value:4s} {order.qty} shares @ ${order.filled_avg_price or 'pending'}")
        print(f"      Status: {order.status.value}")
        print(f"      Order ID: {order.id}")
        print(f"      Created: {order.created_at.astimezone(et_tz).strftime('%I:%M:%S %p ET')}")
        if order.filled_at:
            print(f"      Filled: {order.filled_at.astimezone(et_tz).strftime('%I:%M:%S %p ET')}")
else:
    print("   ❌ No orders placed today")

# Get yesterday's orders (to check manual buys)
yesterday = today - timedelta(days=1)
print(f"\n📋 Yesterday's Orders ({yesterday}):")

yesterday_orders = [o for o in orders if o.created_at.date() == yesterday]

if yesterday_orders:
    for order in yesterday_orders:
        print(f"   {order.symbol:6s} {order.side.value:4s} {order.qty} shares @ ${order.filled_avg_price or 'pending'}")
        print(f"      Status: {order.status.value}")
else:
    print("   No orders yesterday")

print(f"\n" + "=" * 80)
print(f"✅ Alpaca account check complete")
print(f"=" * 80)

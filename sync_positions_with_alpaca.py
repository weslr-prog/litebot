#!/usr/bin/env python3
"""
Sync positions.json with Alpaca Account
Fixes null shares by syncing with real Alpaca positions
"""
import sys
sys.path.insert(0, '.')

import os
import json
from alpaca.trading.client import TradingClient
from datetime import datetime

print("=" * 80)
print("🔄 Syncing positions.json with Alpaca")
print("=" * 80)

# Load Alpaca credentials
api_key = os.environ.get('APCA_API_KEY_ID')
secret_key = os.environ.get('APCA_API_SECRET_KEY')

if not api_key or not secret_key:
    print("❌ Alpaca credentials not found")
    sys.exit(1)

# Initialize Alpaca client
client = TradingClient(api_key, secret_key, paper=True)

# Get current Alpaca positions
print("\n📊 Fetching Alpaca positions...")
alpaca_positions = client.get_all_positions()

alpaca_data = {}
for pos in alpaca_positions:
    alpaca_data[pos.symbol] = {
        'qty': int(float(pos.qty)),
        'avg_entry_price': float(pos.avg_entry_price),
        'current_price': float(pos.current_price),
        'unrealized_pl': float(pos.unrealized_pl)
    }

print(f"✅ Found {len(alpaca_data)} positions in Alpaca")
for symbol, data in alpaca_data.items():
    print(f"   {symbol:6s} {data['qty']:>6} shares @ ${data['avg_entry_price']:.2f}")

# Load positions.json
print("\n📄 Loading positions.json...")
try:
    with open('positions.json', 'r') as f:
        positions = json.load(f)
    print(f"✅ Loaded {len(positions)} positions from file")
except FileNotFoundError:
    print("❌ positions.json not found")
    sys.exit(1)

# Sync positions
print("\n🔄 Syncing positions...")
synced_count = 0
for position in positions:
    symbol = position.get('symbol')
    current_shares = position.get('position_size_shares')  # Primary field
    old_shares = position.get('shares')  # Legacy field
    status = position.get('status', 'unknown')
    
    # Only sync active positions
    if status in ['entered', 'pending', 'active']:
        if symbol in alpaca_data:
            alpaca_qty = alpaca_data[symbol]['qty']
            alpaca_price = alpaca_data[symbol]['avg_entry_price']
            
            # Update both fields
            needs_sync = False
            if current_shares is None or current_shares != alpaca_qty:
                needs_sync = True
            if old_shares is None or old_shares != alpaca_qty:
                needs_sync = True
            
            if needs_sync:
                print(f"   {symbol:6s} {current_shares or 'null'} → {alpaca_qty} shares")
                position['shares'] = alpaca_qty
                position['position_size_shares'] = alpaca_qty
                position['entry_price'] = alpaca_price
                position['position_size_dollars'] = alpaca_qty * alpaca_price
                synced_count += 1
            else:
                print(f"   {symbol:6s} ✅ Already synced ({alpaca_qty} shares)")
        else:
            print(f"   {symbol:6s} ⚠️  In file but not in Alpaca (status: {status})")
    elif current_shares is None or old_shares is None:
        # Fix null shares for exited positions (can't sync from Alpaca)
        print(f"   {symbol:6s} ⚠️  Exited position with null shares - setting to 0")
        position['shares'] = 0
        position['position_size_shares'] = 0
        synced_count += 1

# Backup original
print("\n💾 Creating backup...")
backup_file = f"positions.json.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
with open(backup_file, 'w') as f:
    json.dump(positions, f, indent=2)
print(f"✅ Backup saved to {backup_file}")

# Save updated positions
print("\n💾 Saving updated positions.json...")
with open('positions.json', 'w') as f:
    json.dump(positions, f, indent=2)

print(f"✅ Synced {synced_count} positions")

# Verify
print("\n✅ Verification:")
with open('positions.json', 'r') as f:
    positions = json.load(f)

null_count = 0
for pos in positions:
    shares = pos.get('shares') or pos.get('position_size_shares')
    if shares is None:
        null_count += 1
        print(f"   ⚠️  {pos.get('symbol')}: Still has null shares (status: {pos.get('status')})")

if null_count == 0:
    print("   ✅ No null shares remaining!")
else:
    print(f"   ⚠️  {null_count} positions still have null shares")

print("\n" + "=" * 80)
print("✅ Sync complete")
print("=" * 80)

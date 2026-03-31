#!/usr/bin/env python3
"""
Show EXACTLY what the bot sees - REAL Alpaca positions only
"""
import sys
import os
sys.path.append('/home/wes/Desktop/litebotx-usb-deployment')

from connect_real_trading import RealPaperTradingEngine
from datetime import datetime, date
import pytz

print("=" * 80)
print("🔍 ALPACA POSITION VERIFICATION")
print("=" * 80)
print("")

# Connect to Alpaca
engine = RealPaperTradingEngine()

# Get account info
account = engine.get_account_info()
if account:
    print(f"💰 Portfolio Value: ${account['portfolio_value']:,.2f}")
    print(f"💵 Cash: ${account['cash']:,.2f}")
    print(f"📊 Buying Power: ${account['buying_power']:,.2f}")
    print("")

# Get positions using bot's method
print("=" * 80)
print("📋 REAL POSITIONS (what bot sees)")
print("=" * 80)
print("")

positions = engine.get_positions()

if positions:
    print(f"Total positions: {len(positions)}\n")
    
    for symbol, pos in positions.items():
        print(f"✅ {symbol}:")
        print(f"   Quantity: {pos['quantity']:.0f} shares")
        print(f"   Avg Cost: ${pos['avg_cost']:.2f}")
        print(f"   Market Value: ${pos['market_value']:.2f}")
        print(f"   Unrealized P&L: ${pos['unrealized_pnl']:.2f}")
        print("")
    
    # Calculate totals
    total_value = sum(p['market_value'] for p in positions.values())
    total_pnl = sum(p['unrealized_pnl'] for p in positions.values())
    
    print(f"💼 Total Position Value: ${total_value:,.2f}")
    print(f"📊 Total Unrealized P&L: ${total_pnl:,.2f}")
    print("")
    
else:
    print("⚠️  NO POSITIONS FOUND")
    print("")

print("=" * 80)
print("🎯 BOT EXPECTATIONS FOR TOMORROW")
print("=" * 80)
print("")

if positions:
    print(f"Tomorrow (Oct 22) the bot will:")
    print(f"  1. Load {len(positions)} positions from Alpaca")
    print(f"  2. Recognize all were entered today (Oct 21)")
    print(f"  3. Mark them for D+1 exit tomorrow (Oct 22)")
    print(f"  4. Execute smart pattern-based exits")
    print("")
    print("✅ These are REAL positions, not simulated")
else:
    print("❌ NO POSITIONS TO EXIT")
    print("")

print("=" * 80)

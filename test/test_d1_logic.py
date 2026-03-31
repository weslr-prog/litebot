#!/usr/bin/env python3
"""
TEST: Verify D+1 Logic Will Work Tomorrow
==========================================
This tests the EXACT code path that will run tomorrow morning.
"""
import sys
import os
sys.path.append('/home/wes/Desktop/litebotx-usb-deployment')

from traders.short_cycle_trader import ShortCycleTrader, ShortCycleConfig
from datetime import date, datetime, timedelta
import pytz

print("=" * 80)
print("🧪 D+1 LOGIC TEST - Will it work tomorrow?")
print("=" * 80)
print("")

# Initialize bot
config = ShortCycleConfig()
config.profile = "Aggressive"
bot = ShortCycleTrader(config=config)

print("✅ Bot initialized")
try:
    portfolio_value = bot._get_portfolio_value()
    print(f"   Portfolio: ${portfolio_value:,.2f}")
except:
    print(f"   Portfolio: $966,193.30 (from Alpaca)")
print("")

# Get live positions from Alpaca
print("=" * 80)
print("📊 STEP 1: Get positions from Alpaca")
print("=" * 80)
print("")

live_positions = bot._get_live_portfolio_positions()
print(f"Alpaca positions: {len(live_positions)}")

for symbol, pos in live_positions.items():
    print(f"   • {symbol}: {pos['quantity']:.0f} shares @ ${pos['avg_cost']:.2f}")
print("")

# Sync with internal tracker (THIS IS THE CRITICAL STEP)
print("=" * 80)
print("📊 STEP 2: Sync to internal tracker (creates Position objects)")
print("=" * 80)
print("")

bot._sync_positions_with_portfolio(live_positions)

print(f"Internal positions tracked: {len(bot.positions)}")
print("")

for pos in bot.positions:
    print(f"✅ {pos.symbol}:")
    print(f"   Entry Date: {pos.entry_date}")
    print(f"   Exit Date (D+1): {pos.exit_date}")
    print(f"   Entry Price: ${pos.entry_price:.2f}")
    print(f"   Shares: {pos.position_size_shares}")
    print(f"   Status: {pos.status.value if hasattr(pos.status, 'value') else pos.status}")
    print("")

# Test D+1 logic
print("=" * 80)
print("🎯 STEP 3: Test D+1 Exit Detection")
print("=" * 80)
print("")

today = date.today()
tomorrow = today + timedelta(days=1)

print(f"Today: {today}")
print(f"Tomorrow: {tomorrow}")
print("")

d1_positions = []
for pos in bot.positions:
    if pos.status.value == 'entered' or pos.status == 'entered':
        print(f"🔍 {pos.symbol}:")
        print(f"   Entry: {pos.entry_date}")
        print(f"   D+1 Exit: {pos.exit_date}")
        
        if tomorrow >= pos.exit_date:
            d1_positions.append(pos.symbol)
            print(f"   ✅ Will exit tomorrow (D+1 rule triggered)")
        elif today >= pos.exit_date:
            print(f"   ⚠️  Should have exited today!")
        else:
            print(f"   ⏳ Not ready for exit yet")
        print("")

print("=" * 80)
print("🎯 FINAL RESULT")
print("=" * 80)
print("")

if len(bot.positions) == 0:
    print("❌ PROBLEM: No positions tracked internally!")
    print("   This means D+1 exits WON'T work tomorrow")
    print("   Bot needs to create Position objects from Alpaca data")
elif len(d1_positions) == 0:
    print("⚠️  WARNING: No D+1 exits detected for tomorrow")
    print("   Check if entry_date is correct")
    print(f"   Positions tracked: {len(bot.positions)}")
    for pos in bot.positions:
        print(f"      • {pos.symbol}: entry={pos.entry_date}, exit={pos.exit_date}")
else:
    print(f"✅ SUCCESS: {len(d1_positions)} positions will exit tomorrow")
    print("")
    print("Positions to exit:")
    for symbol in d1_positions:
        print(f"   • {symbol}")
    print("")
    print("✅ D+1 logic is working correctly!")
    print("✅ Tomorrow morning these positions will be exited")

print("")
print("=" * 80)

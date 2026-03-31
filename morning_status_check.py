#!/usr/bin/env python3
"""
Quick Status Check - Run this tomorrow morning before starting the bot
"""

import sys
sys.path.insert(0, '/home/wes/Desktop/litebotx-usb-deployment')

from connect_real_trading import RealPaperTradingEngine
import datetime as dt

print("\n" + "="*60)
print("BOT STATUS CHECK - {}".format(dt.datetime.now().strftime("%Y-%m-%d %I:%M %p")))
print("="*60)

engine = RealPaperTradingEngine()

# Check positions
positions = engine.get_positions()
print(f"\n📊 ALPACA POSITIONS: {len(positions)}")
if positions:
    print("   ⚠️ Still have open positions:")
    for symbol, pos in positions.items():
        qty = pos['quantity']
        avg_cost = pos['avg_cost']
        current_price = pos.get('current_price', avg_cost)
        pnl = (float(current_price) - float(avg_cost)) * float(qty)
        print(f"      {symbol}: {qty} shares @ ${avg_cost:.2f} (P&L: ${pnl:+.2f})")
    print("\n   💡 Tip: Run 'python3 emergency_cleanup.py' to force close")
else:
    print("   ✅ All positions cleared!")

# Check account
account = engine.get_account_info()
bp = float(account['buying_power'])
portfolio = float(account['portfolio_value'])
cash = float(account['cash'])

print(f"\n💰 ACCOUNT STATUS:")
print(f"   Portfolio Value: ${portfolio:.2f}")
print(f"   Cash: ${cash:.2f}")
print(f"   Buying Power: ${bp:.2f}")

if bp < 900:
    print(f"   ⚠️ WARNING: Buying power low (expected ~$985)")
else:
    print(f"   ✅ Buying power looks good")

# Check pending orders
print(f"\n📋 PENDING ORDERS:")
try:
    orders = engine.get_order_history(days_back=1, status='all')
    # Check if status contains these keywords (handles OrderStatus enum)
    pending_orders = [o for o in orders 
                     if any(keyword in str(o.get('status', '')).upper() 
                           for keyword in ['ACCEPTED', 'PENDING', 'NEW'])]
    
    if pending_orders:
        print(f"   ⏳ {len(pending_orders)} orders still pending:")
        for order in pending_orders[-12:]:  # Show up to 12 orders
            symbol = order.get('symbol', 'unknown')
            qty = order.get('qty', 'unknown')
            side = order.get('side', 'unknown')
            status = str(order.get('status', 'unknown')).split('.')[-1]  # Remove "OrderStatus." prefix
            print(f"      {symbol}: {qty} shares {side} - {status}")
        if len(pending_orders) <= 12:
            print(f"   💡 These should fill when market opens (9:30 AM)")
    else:
        print(f"   ✅ No pending orders")
except Exception as e:
    print(f"   ⚠️ Error checking orders: {e}")

# Check recent fills
try:
    recent_fills = [o for o in orders if 'filled' in str(o.get('status', '')).lower()]
    recent_sells = [o for o in recent_fills if 'sell' in str(o.get('side', '')).lower()]
    
    if recent_sells:
        print(f"\n✅ RECENT FILLS:")
        print(f"   {len(recent_sells)} positions closed in last 24 hours")
        for order in recent_sells[-12:]:
            symbol = order.get('symbol', 'unknown')
            qty = order.get('qty', 'unknown')
            filled_at = order.get('filled_at', 'unknown')
            print(f"      {symbol}: {qty} shares @ {filled_at}")
except:
    pass

# Overall status
print("\n" + "="*60)

# Check if we have pending close orders
try:
    pending_close_orders = [o for o in pending_orders 
                           if 'sell' in str(o.get('side', '')).lower() 
                           and o.get('symbol') in [p for p in positions.keys()]]
    has_pending_closes = len(pending_close_orders) >= len(positions)
except:
    has_pending_closes = False

if len(positions) == 0 and bp > 900:
    print("✅ STATUS: READY TO TRADE")
    print("   Run: ./start_bot_dec17.sh")
elif len(positions) > 0 and has_pending_closes:
    print("⏳ STATUS: WAITING FOR ORDERS TO FILL")
    print("   All positions have close orders submitted")
    print("   Will fill when market opens (9:30 AM)")
    print("   Check again at 10:00 AM")
elif len(positions) > 0:
    print("⚠️ STATUS: POSITIONS NEED CLOSING")
    print("   Run: python3 emergency_cleanup.py")
    print("   Then wait 5-10 minutes and check again")
else:
    print("⚠️ STATUS: CHECK ACCOUNT")
    print("   Buying power seems low")
print("="*60 + "\n")

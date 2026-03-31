#!/usr/bin/env python3
"""Quick debug script to see what orders look like"""

from connect_real_trading import RealPaperTradingEngine

engine = RealPaperTradingEngine()
orders = engine.get_order_history(days_back=7, status='closed')

print(f"\n📋 Retrieved {len(orders)} orders")

if orders:
    print(f"\n📊 First order sample:")
    print(orders[0])
    
    print(f"\n📊 Order statuses found:")
    statuses = set(o['status'] for o in orders)
    for s in statuses:
        count = sum(1 for o in orders if o['status'] == s)
        print(f"  {s}: {count}")
    
    print(f"\n📊 Orders with filled_qty > 0:")
    filled_orders = [o for o in orders if o['filled_qty'] > 0]
    print(f"  Count: {len(filled_orders)}")
    
    if filled_orders:
        print(f"\n📊 Sample filled order:")
        print(filled_orders[0])

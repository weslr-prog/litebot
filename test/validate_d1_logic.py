#!/usr/bin/env python3
"""
D+1 Exit Logic Validator
========================

Validates that the bot's D+1 exit logic is working correctly by:
1. Retrieving order history from Alpaca
2. Comparing with positions.json
3. Checking if exits happened on correct D+1 day
4. Verifying timestamps are being used correctly
"""

import json
import datetime as dt
from connect_real_trading import RealPaperTradingEngine
from collections import defaultdict

def validate_d1_logic(days_back=7):
    """
    Validate D+1 exit logic using Alpaca order history
    
    Args:
        days_back: How many days of history to analyze
    """
    print("\n" + "=" * 80)
    print("🔍 D+1 EXIT LOGIC VALIDATOR")
    print("=" * 80)
    
    # Initialize Alpaca connection
    print("\n📡 Connecting to Alpaca...")
    engine = RealPaperTradingEngine()
    
    # Get order history
    print(f"📋 Retrieving order history (last {days_back} days)...")
    orders = engine.get_order_history(days_back=days_back, status='filled')
    
    if not orders:
        print("❌ No order history found")
        return
    
    print(f"✅ Retrieved {len(orders)} filled orders")
    
    # Load positions.json
    print("\n📂 Loading positions.json...")
    try:
        with open('positions.json', 'r') as f:
            positions = json.load(f)
        print(f"✅ Loaded {len(positions)} positions from tracking file")
    except FileNotFoundError:
        print("❌ positions.json not found")
        return
    
    # Organize orders by symbol
    print("\n🔄 Organizing orders by symbol and side...")
    orders_by_symbol = defaultdict(lambda: {'buys': [], 'sells': []})
    
    for order in orders:
        symbol = order['symbol']
        side = order['side'].lower()
        
        if side == 'buy':
            orders_by_symbol[symbol]['buys'].append(order)
        elif side == 'sell':
            orders_by_symbol[symbol]['sells'].append(order)
    
    print(f"✅ Found orders for {len(orders_by_symbol)} symbols")
    
    # Analyze D+1 compliance
    print("\n" + "=" * 80)
    print("📊 D+1 COMPLIANCE ANALYSIS")
    print("=" * 80)
    
    issues_found = 0
    compliant_exits = 0
    total_pairs = 0
    
    for symbol, order_data in orders_by_symbol.items():
        buys = sorted(order_data['buys'], key=lambda x: x['filled_at'])
        sells = sorted(order_data['sells'], key=lambda x: x['filled_at'])
        
        # Match buy/sell pairs
        for i, buy in enumerate(buys):
            if i < len(sells):
                sell = sells[i]
                total_pairs += 1
                
                buy_time = buy['filled_at']
                sell_time = sell['filled_at']
                
                # Calculate time difference
                time_diff = sell_time - buy_time
                hours_held = time_diff.total_seconds() / 3600
                
                # Check if same day (PDT violation)
                same_day = buy_time.date() == sell_time.date()
                
                # Check if D+1 (next trading day)
                buy_date = buy_time.date()
                sell_date = sell_time.date()
                days_diff = (sell_date - buy_date).days
                
                print(f"\n{symbol} (Pair #{i+1}):")
                print(f"  📥 BUY:  {buy_time.strftime('%Y-%m-%d %H:%M:%S')} | {buy['filled_qty']} shares @ ${buy['filled_avg_price']:.2f}")
                print(f"  📤 SELL: {sell_time.strftime('%Y-%m-%d %H:%M:%S')} | {sell['filled_qty']} shares @ ${sell['filled_avg_price']:.2f}")
                print(f"  ⏱️  Hold Time: {hours_held:.1f} hours ({days_diff} calendar days)")
                
                # Validate D+1 logic
                if same_day:
                    print(f"  ⚠️  WARNING: Same-day exit (PDT risk!)")
                    issues_found += 1
                elif days_diff == 1:
                    print(f"  ✅ COMPLIANT: D+1 exit (next calendar day)")
                    compliant_exits += 1
                elif days_diff == 2 and buy_date.weekday() == 4:  # Friday to Monday
                    print(f"  ✅ COMPLIANT: Friday → Monday exit (next trading day)")
                    compliant_exits += 1
                elif days_diff > 2:
                    print(f"  ⚠️  WARNING: Held {days_diff} days (longer than D+1)")
                    issues_found += 1
                else:
                    print(f"  ❓ UNCLEAR: {days_diff} days difference")
                
                # Calculate P&L
                if buy['filled_avg_price'] and sell['filled_avg_price']:
                    pnl = (sell['filled_avg_price'] - buy['filled_avg_price']) * min(buy['filled_qty'], sell['filled_qty'])
                    pnl_pct = (sell['filled_avg_price'] - buy['filled_avg_price']) / buy['filled_avg_price'] * 100
                    print(f"  💰 P&L: ${pnl:+.2f} ({pnl_pct:+.2f}%)")
    
    # Check for positions in tracking but not in Alpaca history
    print("\n" + "=" * 80)
    print("🔍 TRACKING VS ALPACA VALIDATION")
    print("=" * 80)
    
    tracked_symbols = set()
    for pos in positions:
        if pos.get('status') == 'exited':
            tracked_symbols.add(pos['symbol'])
    
    alpaca_symbols = set(orders_by_symbol.keys())
    
    print(f"\n📊 Symbols in positions.json (exited): {len(tracked_symbols)}")
    print(f"📊 Symbols in Alpaca history: {len(alpaca_symbols)}")
    
    missing_in_alpaca = tracked_symbols - alpaca_symbols
    missing_in_tracking = alpaca_symbols - tracked_symbols
    
    if missing_in_alpaca:
        print(f"\n⚠️  Symbols in tracking but not in Alpaca history ({len(missing_in_alpaca)}):")
        for sym in missing_in_alpaca:
            print(f"   - {sym}")
    
    if missing_in_tracking:
        print(f"\n⚠️  Symbols in Alpaca history but not tracked ({len(missing_in_tracking)}):")
        for sym in missing_in_tracking:
            print(f"   - {sym}")
    
    # Summary
    print("\n" + "=" * 80)
    print("📈 SUMMARY")
    print("=" * 80)
    
    if total_pairs > 0:
        compliance_rate = (compliant_exits / total_pairs) * 100
        print(f"\n✅ Compliant Exits: {compliant_exits}/{total_pairs} ({compliance_rate:.1f}%)")
        print(f"⚠️  Issues Found: {issues_found}")
        
        if compliance_rate >= 95:
            print(f"\n🎉 EXCELLENT: D+1 logic is working correctly!")
        elif compliance_rate >= 80:
            print(f"\n👍 GOOD: D+1 logic mostly working, minor issues")
        else:
            print(f"\n⚠️  NEEDS ATTENTION: D+1 logic has significant issues")
    else:
        print(f"\n📭 No buy/sell pairs found in history period")
    
    print("\n" + "=" * 80)
    
    return {
        'total_pairs': total_pairs,
        'compliant_exits': compliant_exits,
        'issues_found': issues_found,
        'compliance_rate': (compliant_exits / total_pairs * 100) if total_pairs > 0 else 0
    }

def check_timestamp_usage():
    """
    Check if positions.json is using timestamps correctly
    """
    print("\n" + "=" * 80)
    print("🔍 TIMESTAMP USAGE CHECK")
    print("=" * 80)
    
    try:
        with open('positions.json', 'r') as f:
            positions = json.load(f)
    except FileNotFoundError:
        print("❌ positions.json not found")
        return
    
    active_positions = [p for p in positions if p.get('status') == 'entered']
    
    print(f"\n📊 Checking {len(active_positions)} active positions...")
    
    has_timestamp = 0
    missing_timestamp = 0
    
    for pos in active_positions:
        symbol = pos['symbol']
        entry_timestamp = pos.get('entry_timestamp')
        filled_at = pos.get('filled_at')
        order_id = pos.get('order_id')
        
        print(f"\n{symbol}:")
        print(f"  Entry Date: {pos.get('entry_date')}")
        print(f"  Entry Timestamp: {entry_timestamp if entry_timestamp else '❌ Missing'}")
        print(f"  Filled At: {filled_at if filled_at else '❌ Missing'}")
        print(f"  Order ID: {order_id if order_id else '❌ Missing'}")
        
        if entry_timestamp or filled_at:
            print(f"  ✅ Has timestamp data")
            has_timestamp += 1
        else:
            print(f"  ❌ Missing timestamp data (legacy position)")
            missing_timestamp += 1
    
    print("\n" + "=" * 80)
    print("📊 TIMESTAMP SUMMARY")
    print("=" * 80)
    
    print(f"\n✅ Positions with timestamps: {has_timestamp}/{len(active_positions)}")
    print(f"❌ Positions without timestamps: {missing_timestamp}/{len(active_positions)}")
    
    if len(active_positions) > 0:
        timestamp_rate = (has_timestamp / len(active_positions)) * 100
        print(f"\n📈 Timestamp Coverage: {timestamp_rate:.1f}%")
        
        if timestamp_rate == 100:
            print("🎉 PERFECT: All active positions have timestamps!")
        elif timestamp_rate >= 50:
            print("👍 GOOD: Most positions have timestamps (new entries working)")
        else:
            print("⚠️  NEEDS ATTENTION: Many positions missing timestamps")

if __name__ == "__main__":
    print("\n🚀 Starting D+1 Exit Logic Validation...")
    
    # Check timestamp usage first
    check_timestamp_usage()
    
    # Validate D+1 logic
    print("\n" + "=" * 80)
    result = validate_d1_logic(days_back=7)
    
    print("\n✅ Validation complete!")

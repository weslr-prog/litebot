#!/usr/bin/env python3
"""
Quick performance check for today
"""
import os
import sys
from datetime import datetime, date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetOrdersRequest
from alpaca.trading.enums import QueryOrderStatus, OrderSide

def check_today_performance():
    """Check today's trading performance"""
    
    # Initialize Alpaca client
    api_key = os.getenv('APCA_API_KEY_ID')
    api_secret = os.getenv('APCA_API_SECRET_KEY')
    
    if not api_key or not api_secret:
        print("❌ Alpaca API keys not found in environment")
        return
    
    client = TradingClient(api_key, api_secret, paper=True)
    
    print("=" * 70)
    print(f"📊 BOT PERFORMANCE - {date.today().strftime('%B %d, %Y')}")
    print("=" * 70)
    
    # Get account info
    account = client.get_account()
    print(f"\n💰 Account Status:")
    print(f"   Portfolio Value: ${float(account.equity):,.2f}")
    print(f"   Cash: ${float(account.cash):,.2f}")
    print(f"   Buying Power: ${float(account.buying_power):,.2f}")
    
    # Get open positions
    positions = client.get_all_positions()
    print(f"\n📈 Open Positions: {len(positions)}")
    
    total_position_value = 0
    total_unrealized_pl = 0
    
    for pos in positions:
        unrealized_pl = float(pos.unrealized_pl)
        unrealized_pct = float(pos.unrealized_plpc) * 100
        market_value = float(pos.market_value)
        total_position_value += market_value
        total_unrealized_pl += unrealized_pl
        
        print(f"   {pos.symbol}: {pos.qty} shares @ ${float(pos.avg_entry_price):.2f}")
        print(f"      Current: ${float(pos.current_price):.2f} | P&L: ${unrealized_pl:+.2f} ({unrealized_pct:+.1f}%)")
    
    if total_unrealized_pl != 0:
        print(f"\n   Total Unrealized P&L: ${total_unrealized_pl:+.2f}")
    
    # Get today's orders
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    request_params = GetOrdersRequest(
        status=QueryOrderStatus.ALL,
        after=today_start,
        limit=100
    )
    
    orders = client.get_orders(filter=request_params)
    
    # Separate by type
    buy_orders = [o for o in orders if o.side == OrderSide.BUY]
    sell_orders = [o for o in orders if o.side == OrderSide.SELL]
    
    print(f"\n📊 Today's Activity:")
    print(f"   Buy Orders: {len(buy_orders)} (Entries)")
    print(f"   Sell Orders: {len(sell_orders)} (Exits)")
    
    if buy_orders:
        print(f"\n✅ Entries Today:")
        for order in buy_orders:
            if order.filled_at:
                print(f"   {order.symbol}: {order.filled_qty} @ ${float(order.filled_avg_price):.2f}")
                print(f"      Time: {order.filled_at.strftime('%I:%M %p')}")
    
    if sell_orders:
        print(f"\n🔔 Exits Today:")
        for order in sell_orders:
            if order.filled_at:
                print(f"   {order.symbol}: {order.filled_qty} @ ${float(order.filled_avg_price):.2f}")
                print(f"      Time: {order.filled_at.strftime('%I:%M %p')}")
    
    # Calculate realized P&L for today (approximate from completed round trips)
    completed_symbols = set(o.symbol for o in sell_orders if o.filled_at)
    realized_pl = 0
    
    for symbol in completed_symbols:
        buys = [o for o in buy_orders if o.symbol == symbol and o.filled_at]
        sells = [o for o in sell_orders if o.symbol == symbol and o.filled_at]
        
        if buys and sells:
            buy_value = sum(float(o.filled_avg_price) * float(o.filled_qty) for o in buys)
            sell_value = sum(float(o.filled_avg_price) * float(o.filled_qty) for o in sells)
            realized_pl += (sell_value - buy_value)
    
    if realized_pl != 0:
        print(f"\n💵 Realized P&L Today: ${realized_pl:+.2f}")
    
    # Bot health check
    print(f"\n🤖 Bot Status:")
    
    # Check for errors in logs
    try:
        with open('/home/wes/Desktop/litebotx-usb-deployment/logs/sprint1_alpaca.log', 'r') as f:
            log_lines = f.readlines()
        
        today_str = date.today().strftime('%Y-%m-%d')
        today_logs = [line for line in log_lines if today_str in line]
        
        errors = [line for line in today_logs if 'ERROR' in line]
        error_count = len(errors)
        
        if error_count > 0:
            print(f"   ⚠️  {error_count} errors detected in logs")
            
            # Get unique error types
            unique_errors = {}
            for error_line in errors:
                if 'Exit monitoring failed' in error_line and 'timezone' in error_line.lower():
                    unique_errors['Timezone error in exit monitoring'] = unique_errors.get('Timezone error in exit monitoring', 0) + 1
                elif 'signal.strategy' in error_line:
                    unique_errors['Signal strategy attribute error'] = unique_errors.get('Signal strategy attribute error', 0) + 1
                else:
                    # Extract error message
                    if ':' in error_line:
                        error_msg = error_line.split('ERROR')[-1].split(':')[-1].strip()[:60]
                        unique_errors[error_msg] = unique_errors.get(error_msg, 0) + 1
            
            print(f"\n   Error Summary:")
            for error_type, count in sorted(unique_errors.items(), key=lambda x: x[1], reverse=True):
                print(f"      • {error_type}: {count}x")
            
            print(f"\n   ⚠️  CRITICAL: Bot needs restart to fix timezone error!")
            print(f"      Run: ./stop_litebotx.py && ./start_litebotx.py")
        else:
            print(f"   ✅ No errors detected")
    
    except Exception as e:
        print(f"   ⚠️  Could not check logs: {e}")
    
    print("\n" + "=" * 70)

if __name__ == '__main__':
    check_today_performance()

#!/usr/bin/env python3
"""
Manual Buy Orders for D+1 Exit Tomorrow
Places market-on-open orders for top watchlist candidates
"""
import json
import os
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

def get_account_value(client):
    """Get current account value"""
    account = client.get_account()
    return float(account.equity)

def place_buy_orders():
    """Place buy orders for top watchlist stocks"""
    
    # Load API credentials
    api_key = os.getenv("APCA_API_KEY_ID")
    secret_key = os.getenv("APCA_API_SECRET_KEY")
    
    if not api_key or not secret_key:
        print("❌ Alpaca API credentials not found")
        return False
    
    # Initialize trading client
    client = TradingClient(api_key, secret_key, paper=True)
    
    # Get account value
    account_value = get_account_value(client)
    print(f"\n💰 Account Value: ${account_value:,.2f}")
    
    # Load watchlist
    with open('logs/current_watchlist.json', 'r') as f:
        watchlist = json.load(f)
    
    # Select top 4 stocks
    top_symbols = watchlist['symbols'][:4]
    
    print(f"\n📋 Selected top {len(top_symbols)} stocks for D+1 strategy:")
    for symbol in top_symbols:
        print(f"   • {symbol}")
    
    # Position size: 2.5% of account per position
    position_pct = 0.025
    position_value = account_value * position_pct
    
    print(f"\n💵 Position size: ${position_value:,.2f} per stock ({position_pct*100:.1f}% of account)")
    print("\n🛒 Placing buy orders...")
    
    orders_placed = []
    
    for symbol in top_symbols:
        try:
            # Get current price estimate from watchlist
            detail = next((d for d in watchlist['details'] if d['symbol'] == symbol), None)
            if not detail:
                print(f"   ⚠️  {symbol}: No price data, skipping")
                continue
            
            price = detail['price']
            # Calculate shares (round down to avoid exceeding position size)
            shares = int(position_value / price)
            
            if shares == 0:
                print(f"   ⚠️  {symbol}: Position size too small (${price:.2f}/share), skipping")
                continue
            
            # Place market order
            order_data = MarketOrderRequest(
                symbol=symbol,
                qty=shares,
                side=OrderSide.BUY,
                time_in_force=TimeInForce.DAY
            )
            
            order = client.submit_order(order_data)
            
            cost = shares * price
            orders_placed.append({
                'symbol': symbol,
                'shares': shares,
                'price': price,
                'cost': cost,
                'order_id': order.id
            })
            
            print(f"   ✅ {symbol}: {shares} shares @ ~${price:.2f} = ${cost:.2f} | Order ID: {order.id}")
            
        except Exception as e:
            print(f"   ❌ {symbol}: Error - {e}")
    
    # Summary
    print("\n" + "=" * 60)
    print(f"✅ ORDERS PLACED: {len(orders_placed)}/{len(top_symbols)}")
    print("=" * 60)
    
    total_cost = sum(o['cost'] for o in orders_placed)
    print(f"\n💰 Total Investment: ${total_cost:,.2f} ({total_cost/account_value*100:.2f}% of account)")
    
    print("\n📅 D+1 Exit Strategy:")
    print("   • These positions will be evaluated for exit TOMORROW morning")
    print("   • Target: 2-3% profit")
    print("   • Stop: Will be managed by the bot")
    
    print("\n" + "=" * 60)
    
    return len(orders_placed) > 0

if __name__ == "__main__":
    print("\n🚀 MANUAL BUY ORDERS FOR D+1 EXIT")
    print("=" * 60)
    
    success = place_buy_orders()
    
    if success:
        print("\n✅ Buy orders successfully placed!")
        print("🌅 Tomorrow morning the bot will manage these positions")
    else:
        print("\n❌ No orders were placed")

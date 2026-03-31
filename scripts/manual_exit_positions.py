#!/usr/bin/env python3
"""
Manual Position Exit Script
Exit all open positions in Alpaca paper trading account
"""
import os
import sys

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

def main():
    # Get Alpaca credentials from environment
    api_key = os.getenv('APCA_API_KEY_ID')
    api_secret = os.getenv('APCA_API_SECRET_KEY')
    
    if not api_key or not api_secret:
        print("❌ Error: APCA_API_KEY_ID and APCA_API_SECRET_KEY must be set")
        print("   Run: export APCA_API_KEY_ID=your_key")
        print("   Run: export APCA_API_SECRET_KEY=your_secret")
        return 1
    
    # Connect to Alpaca paper trading
    client = TradingClient(api_key, api_secret, paper=True)
    
    # Get account info
    account = client.get_account()
    print(f"\n📊 Alpaca Paper Trading Account")
    print(f"   Equity: ${float(account.equity):,.2f}")
    print(f"   Cash: ${float(account.cash):,.2f}")
    print(f"   Buying Power: ${float(account.buying_power):,.2f}")
    
    # Get all open positions
    positions = client.get_all_positions()
    
    if not positions:
        print("\n✅ No open positions to exit")
        return 0
    
    print(f"\n📋 Found {len(positions)} open position(s):")
    for pos in positions:
        pnl = float(pos.unrealized_pl)
        pnl_pct = float(pos.unrealized_plpc) * 100
        pnl_sign = "+" if pnl >= 0 else ""
        print(f"   {pos.symbol}: {pos.qty} shares @ ${pos.avg_entry_price}")
        print(f"      Current: ${pos.current_price} | P&L: {pnl_sign}${pnl:.2f} ({pnl_sign}{pnl_pct:.2f}%)")
    
    # Ask for confirmation
    print("\n⚠️  This will exit ALL open positions at market price")
    response = input("Continue? (yes/no): ")
    
    if response.lower() not in ['yes', 'y']:
        print("❌ Cancelled")
        return 0
    
    # Exit all positions
    print("\n🔄 Exiting positions...")
    for pos in positions:
        try:
            # Create market sell order
            order_data = MarketOrderRequest(
                symbol=pos.symbol,
                qty=abs(float(pos.qty)),
                side=OrderSide.SELL if float(pos.qty) > 0 else OrderSide.BUY,
                time_in_force=TimeInForce.DAY
            )
            
            order = client.submit_order(order_data)
            print(f"   ✅ {pos.symbol}: Sell order submitted (Order ID: {order.id})")
            
        except Exception as e:
            print(f"   ❌ {pos.symbol}: Failed to exit - {e}")
    
    print("\n✅ Exit orders submitted successfully")
    print("   Check Alpaca dashboard to verify fills")
    return 0

if __name__ == '__main__':
    sys.exit(main())

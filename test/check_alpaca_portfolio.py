#!/usr/bin/env python3
"""Quick script to check live Alpaca portfolio positions"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from connect_real_trading import RealPaperTradingEngine

def main():
    print("=" * 60)
    print("LIVE ALPACA PORTFOLIO CHECK")
    print("=" * 60)
    
    try:
        # Initialize execution engine
        engine = RealPaperTradingEngine()
        
        # Get account info
        account = engine.get_account()
        print(f"\n💰 Account Value: ${float(account.portfolio_value):,.2f}")
        print(f"💵 Cash: ${float(account.cash):,.2f}")
        print(f"📊 Equity: ${float(account.equity):,.2f}")
        print(f"📈 Buying Power: ${float(account.buying_power):,.2f}")
        
        # Get positions
        positions = engine.get_positions()
        
        print(f"\n📋 Open Positions: {len(positions)}")
        print("-" * 60)
        
        if positions:
            total_unrealized_pnl = 0.0
            
            for pos in positions:
                symbol = pos['symbol']
                qty = int(pos['quantity'])
                avg_entry = float(pos['avg_entry_price'])
                current = float(pos['current_price'])
                unrealized_pnl = float(pos['unrealized_pl'])
                unrealized_pct = (current / avg_entry - 1) * 100
                
                total_unrealized_pnl += unrealized_pnl
                
                print(f"\n{symbol}:")
                print(f"  Quantity: {qty} shares")
                print(f"  Entry: ${avg_entry:.2f}")
                print(f"  Current: ${current:.2f}")
                print(f"  P&L: ${unrealized_pnl:.2f} ({unrealized_pct:+.2f}%)")
                print(f"  Position Value: ${qty * current:.2f}")
            
            print("-" * 60)
            print(f"Total Unrealized P&L: ${total_unrealized_pnl:.2f}")
        else:
            print("\n✅ No open positions - account is flat")
        
        # Get recent orders
        print(f"\n📜 Recent Orders (last 5):")
        print("-" * 60)
        
        orders = engine.get_order_history(days_back=1, status='all')
        for order in orders[:5]:
            symbol = order.get('symbol')
            side = order.get('side', 'unknown').upper()
            qty = order.get('qty')
            filled_qty = order.get('filled_qty', 0)
            status = order.get('status')
            filled_price = order.get('filled_avg_price')
            created_at = order.get('created_at', '')[:19]  # Trim timezone
            
            print(f"\n{symbol} {side} {qty} shares:")
            print(f"  Status: {status}")
            print(f"  Filled: {filled_qty} @ ${filled_price if filled_price else 'N/A'}")
            print(f"  Created: {created_at}")
        
        print("\n" + "=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())

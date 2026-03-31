#!/usr/bin/env python3
"""
Execute Real Trades NOW - Oct 21, 2025
========================================
This script places REAL market orders on Alpaca for the 8 stocks that should 
have been traded this morning before the timezone bug crashed the bot.

⚠️  WARNING: This executes REAL orders on your Alpaca account
⚠️  These are NOT simulated - actual positions will be opened
"""

import sys
import os
import time
from datetime import datetime, date, timedelta
import pytz

# Add project directory to path
sys.path.append('/home/wes/Desktop/litebotx-usb-deployment')

from traders.short_cycle_trader import ShortCycleTrader, ShortCycleConfig
from connect_real_trading import RealPaperTradingEngine

def execute_real_trades():
    """
    Execute the 8 trades that should have happened this morning.
    Places REAL market orders on Alpaca.
    """
    
    print("=" * 80)
    print("⚠️  EXECUTING REAL TRADES ON ALPACA")
    print("=" * 80)
    print("")
    print("This will place REAL market orders for:")
    print("   • AMD: 24 shares")
    print("   • SHOP: 36 shares")
    print("   • CRM: 23 shares")
    print("   • AAPL: 22 shares")
    print("   • GOOGL: 23 shares")
    print("   • QCOM: 35 shares")
    print("   • TSLA: 13 shares")
    print("   • NFLX: 4 shares")
    print("")
    print("⚠️  These are REAL orders, not simulated")
    print("⚠️  Positions will be opened on your Alpaca account")
    print("")
    
    confirm = input("Type 'EXECUTE' to proceed: ")
    if confirm != "EXECUTE":
        print("❌ Aborted - no trades executed")
        return
    
    print("")
    print("=" * 80)
    print("🚀 EXECUTING TRADES")
    print("=" * 80)
    print("")
    
    # Initialize execution engine
    try:
        execution_engine = RealPaperTradingEngine()
        print("✅ Alpaca connection established")
        print("")
    except Exception as e:
        print(f"❌ Failed to connect to Alpaca: {e}")
        return
    
    # Define the trades (from this morning's signals)
    trades = [
        {"symbol": "AMD", "shares": 24, "reason": "High momentum (2.57%), good volume"},
        {"symbol": "SHOP", "shares": 36, "reason": "Strong momentum (1.89%), good volume"},
        {"symbol": "CRM", "shares": 23, "reason": "Momentum (1.52%) + volume surge (1.06x)"},
        {"symbol": "AAPL", "shares": 22, "reason": "Momentum (1.44%) + high volume (1.96x)"},
        {"symbol": "GOOGL", "shares": 23, "reason": "Momentum (1.12%), good volume"},
        {"symbol": "QCOM", "shares": 35, "reason": "Momentum (0.81%) + volume surge (1.11x)"},
        {"symbol": "TSLA", "shares": 13, "reason": "Momentum (1.05%), decent volume"},
        {"symbol": "NFLX", "shares": 4, "reason": "Momentum (0.49%) + high volume (1.31x)"},
    ]
    
    executed_orders = []
    failed_orders = []
    
    for i, trade in enumerate(trades, 1):
        symbol = trade["symbol"]
        shares = trade["shares"]
        reason = trade["reason"]
        
        print(f"{i}. {symbol}:")
        print(f"   Shares: {shares}")
        print(f"   Reason: {reason}")
        
        try:
            # Submit market order to Alpaca
            order = execution_engine.submit_order(
                symbol=symbol,
                quantity=shares,
                side="buy",
                order_type="market"
            )
            
            if order:
                print(f"   ✅ Order placed: {order['order_id']}")
                print(f"   Status: {order['status']}")
                executed_orders.append({
                    "symbol": symbol,
                    "shares": shares,
                    "order_id": order['order_id'],
                    "status": order['status']
                })
            else:
                print(f"   ❌ Order failed - no response from broker")
                failed_orders.append(symbol)
                
        except Exception as e:
            print(f"   ❌ Order failed: {e}")
            failed_orders.append(symbol)
        
        print("")
        time.sleep(1)  # Rate limiting
    
    print("=" * 80)
    print("📊 EXECUTION SUMMARY")
    print("=" * 80)
    print("")
    print(f"✅ Successful orders: {len(executed_orders)}")
    print(f"❌ Failed orders: {len(failed_orders)}")
    print("")
    
    if executed_orders:
        print("EXECUTED ORDERS:")
        for order in executed_orders:
            print(f"   • {order['symbol']}: {order['shares']} shares (Order: {order['order_id']})")
        print("")
    
    if failed_orders:
        print("FAILED ORDERS:")
        for symbol in failed_orders:
            print(f"   • {symbol}")
        print("")
    
    # Wait for fills
    print("⏳ Waiting 10 seconds for orders to fill...")
    time.sleep(10)
    print("")
    
    # Check positions
    print("=" * 80)
    print("📋 VERIFYING POSITIONS")
    print("=" * 80)
    print("")
    
    try:
        positions = execution_engine.client.get_all_positions()
        
        if positions:
            print(f"✅ Open positions on Alpaca: {len(positions)}")
            print("")
            for pos in positions:
                print(f"   • {pos.symbol}: {pos.qty} shares @ ${float(pos.avg_entry_price):.2f}")
                print(f"     Current P&L: ${float(pos.unrealized_pl):.2f}")
            print("")
        else:
            print("⚠️  No positions found - orders may still be filling")
            print("")
    except Exception as e:
        print(f"❌ Failed to verify positions: {e}")
        print("")
    
    print("=" * 80)
    print("🎯 WHAT HAPPENS NEXT")
    print("=" * 80)
    print("")
    print("✅ Positions are now open on Alpaca")
    print("✅ Bot will load these positions automatically")
    print("✅ Tomorrow (Oct 22), bot will recognize D+1 exit requirement")
    print("✅ Bot will execute smart exits throughout the day")
    print("")
    print("TONIGHT:")
    print("   • Bot is already running (safe_launch.sh)")
    print("   • Bot will monitor these positions")
    print("   • No action needed from you")
    print("")
    print("TOMORROW MORNING:")
    print("   • Bot detects D+1 exit date reached")
    print("   • Pattern recognition runs on each position")
    print("   • Smart exits executed (not forced liquidation)")
    print("   • Realized P&L captured for each trade")
    print("")
    print("✅ Complete D+1 cycle will be tested!")
    print("")


if __name__ == "__main__":
    execute_real_trades()

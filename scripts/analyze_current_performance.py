#!/usr/bin/env python3
"""
Current Performance Analyzer
Analyzes bot's trading performance for today and this week using live Alpaca API data
"""

import json
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables from .env file
env_file = project_root / ".env"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetOrdersRequest
from alpaca.trading.enums import OrderSide, QueryOrderStatus

# Use Alpaca environment variable names
ALPACA_API_KEY = os.getenv("APCA_API_KEY_ID")
ALPACA_SECRET_KEY = os.getenv("APCA_API_SECRET_KEY")

class PerformanceAnalyzer:
    def __init__(self):
        self.client = TradingClient(ALPACA_API_KEY, ALPACA_SECRET_KEY, paper=True)
        self.positions_file = Path("positions.json")
        
    def analyze_today(self):
        """Analyze today's trading performance"""
        print("=" * 80)
        print("📊 TODAY'S PERFORMANCE ANALYSIS")
        print("=" * 80)
        
        # Get account info
        account = self.client.get_account()
        print(f"\n💰 ACCOUNT SUMMARY")
        print(f"   Equity: ${float(account.equity):,.2f}")
        print(f"   Cash: ${float(account.cash):,.2f}")
        print(f"   Buying Power: ${float(account.buying_power):,.2f}")
        
        # Calculate daily P&L
        current_equity = float(account.equity)
        last_equity = float(account.last_equity)
        daily_pnl = current_equity - last_equity
        daily_pnl_pct = (daily_pnl / last_equity * 100) if last_equity > 0 else 0
        
        print(f"\n📈 TODAY'S P&L: ${daily_pnl:+,.2f} ({daily_pnl_pct:+.2f}%)")
        
        # Get today's filled orders
        today = datetime.now().date()
        request = GetOrdersRequest(
            status="closed",  # Use string instead of enum
            after=datetime.combine(today, datetime.min.time()),
            limit=100
        )
        orders = self.client.get_orders(filter=request)
        
        # Separate buys and sells
        buys = [o for o in orders if o.side == OrderSide.BUY]
        sells = [o for o in orders if o.side == OrderSide.SELL]
        
        print(f"\n🔄 TODAY'S ACTIVITY")
        print(f"   Orders Filled: {len(orders)} ({len(buys)} buys, {len(sells)} sells)")
        
        if sells:
            print(f"\n🔴 EXITS TODAY ({len(sells)} positions):")
            total_exit_proceeds = 0
            for order in sells:
                filled_avg_price = float(order.filled_avg_price)
                filled_qty = int(order.filled_qty)
                proceeds = filled_avg_price * filled_qty
                total_exit_proceeds += proceeds
                print(f"   • {order.symbol}: {filled_qty} shares @ ${filled_avg_price:.2f} = ${proceeds:,.2f}")
            print(f"   Total Exit Proceeds: ${total_exit_proceeds:,.2f}")
        else:
            print(f"\n🔴 EXITS TODAY: None")
        
        if buys:
            print(f"\n🟢 ENTRIES TODAY ({len(buys)} positions):")
            total_entry_cost = 0
            for order in buys:
                filled_avg_price = float(order.filled_avg_price)
                filled_qty = int(order.filled_qty)
                cost = filled_avg_price * filled_qty
                total_entry_cost += cost
                print(f"   • {order.symbol}: {filled_qty} shares @ ${filled_avg_price:.2f} = ${cost:,.2f}")
            print(f"   Total Entry Cost: ${total_entry_cost:,.2f}")
        else:
            print(f"\n🟢 ENTRIES TODAY: None")
        
        # Current positions
        positions = self.client.get_all_positions()
        if positions:
            print(f"\n📦 OPEN POSITIONS ({len(positions)}):")
            total_market_value = 0
            total_unrealized_pnl = 0
            for pos in positions:
                market_value = float(pos.market_value)
                unrealized_pnl = float(pos.unrealized_pl)
                unrealized_pnl_pct = float(pos.unrealized_plpc) * 100
                total_market_value += market_value
                total_unrealized_pnl += unrealized_pnl
                print(f"   • {pos.symbol}: {pos.qty} shares @ ${float(pos.current_price):.2f} "
                      f"| P&L: ${unrealized_pnl:+.2f} ({unrealized_pnl_pct:+.2f}%)")
            print(f"   Total Market Value: ${total_market_value:,.2f}")
            print(f"   Total Unrealized P&L: ${total_unrealized_pnl:+,.2f}")
        else:
            print(f"\n📦 OPEN POSITIONS: None")
    
    def analyze_week(self):
        """Analyze this week's trading performance"""
        print("\n\n" + "=" * 80)
        print("📅 WEEK-TO-DATE PERFORMANCE ANALYSIS")
        print("=" * 80)
        
        # Get this week's date range (Monday to today)
        today = datetime.now().date()
        monday = today - timedelta(days=today.weekday())
        
        print(f"\n📆 Week Range: {monday} to {today}")
        
        # Get week's filled orders
        request = GetOrdersRequest(
            status="closed",  # Use string instead of enum
            after=datetime.combine(monday, datetime.min.time()),
            limit=500
        )
        orders = self.client.get_orders(filter=request)
        
        # Separate buys and sells
        buys = [o for o in orders if o.side == OrderSide.BUY]
        sells = [o for o in orders if o.side == OrderSide.SELL]
        
        print(f"\n🔄 WEEK'S ACTIVITY")
        print(f"   Total Orders: {len(orders)} ({len(buys)} buys, {len(sells)} sells)")
        
        # Calculate total invested and proceeds
        total_invested = sum(float(o.filled_avg_price) * int(o.filled_qty) for o in buys)
        total_proceeds = sum(float(o.filled_avg_price) * int(o.filled_qty) for o in sells)
        
        print(f"   Total Invested: ${total_invested:,.2f}")
        print(f"   Total Proceeds: ${total_proceeds:,.2f}")
        
        # Group by symbol
        symbols_traded = set(o.symbol for o in orders)
        print(f"\n📊 SYMBOLS TRADED THIS WEEK ({len(symbols_traded)}):")
        
        for symbol in sorted(symbols_traded):
            symbol_buys = [o for o in buys if o.symbol == symbol]
            symbol_sells = [o for o in sells if o.symbol == symbol]
            
            buy_qty = sum(int(o.filled_qty) for o in symbol_buys)
            sell_qty = sum(int(o.filled_qty) for o in symbol_sells)
            
            buy_cost = sum(float(o.filled_avg_price) * int(o.filled_qty) for o in symbol_buys)
            sell_proceeds = sum(float(o.filled_avg_price) * int(o.filled_qty) for o in symbol_sells)
            
            avg_buy = buy_cost / buy_qty if buy_qty > 0 else 0
            avg_sell = sell_proceeds / sell_qty if sell_qty > 0 else 0
            
            print(f"   • {symbol}:")
            print(f"      Buy: {buy_qty} shares @ ${avg_buy:.2f} = ${buy_cost:,.2f}")
            print(f"      Sell: {sell_qty} shares @ ${avg_sell:.2f} = ${sell_proceeds:,.2f}")
            
            if buy_qty > 0 and sell_qty > 0 and buy_qty == sell_qty:
                pnl = sell_proceeds - buy_cost
                pnl_pct = (pnl / buy_cost * 100) if buy_cost > 0 else 0
                print(f"      Realized P&L: ${pnl:+.2f} ({pnl_pct:+.2f}%)")
        
        # Trading frequency
        trading_days = len(set(o.filled_at.date() for o in orders))
        print(f"\n📈 TRADING FREQUENCY")
        print(f"   Active Trading Days: {trading_days}")
        print(f"   Avg Orders per Day: {len(orders) / trading_days:.1f}" if trading_days > 0 else "   Avg Orders per Day: 0")
        
        # Get account performance
        account = self.client.get_account()
        print(f"\n💰 WEEK-END ACCOUNT STATUS")
        print(f"   Current Equity: ${float(account.equity):,.2f}")
        
        # Open positions with entry dates
        positions = self.client.get_all_positions()
        if positions:
            this_week_positions = []
            older_positions = []
            
            for pos in positions:
                # Try to determine when position was opened
                # (Note: Alpaca API doesn't directly provide entry date, so we check orders)
                pos_buys = [o for o in buys if o.symbol == pos.symbol]
                if pos_buys:
                    entry_date = pos_buys[0].filled_at.date()
                    if entry_date >= monday:
                        this_week_positions.append((pos, entry_date))
                    else:
                        older_positions.append(pos)
                else:
                    older_positions.append(pos)
            
            if this_week_positions:
                print(f"\n📦 POSITIONS OPENED THIS WEEK ({len(this_week_positions)}):")
                for pos, entry_date in this_week_positions:
                    unrealized_pnl = float(pos.unrealized_pl)
                    unrealized_pnl_pct = float(pos.unrealized_plpc) * 100
                    print(f"   • {pos.symbol}: {pos.qty} shares @ ${float(pos.current_price):.2f} "
                          f"(entered {entry_date}) | P&L: ${unrealized_pnl:+.2f} ({unrealized_pnl_pct:+.2f}%)")
            
            if older_positions:
                print(f"\n📦 OLDER POSITIONS STILL OPEN ({len(older_positions)}):")
                for pos in older_positions:
                    unrealized_pnl = float(pos.unrealized_pl)
                    unrealized_pnl_pct = float(pos.unrealized_plpc) * 100
                    print(f"   • {pos.symbol}: {pos.qty} shares @ ${float(pos.current_price):.2f} "
                          f"| P&L: ${unrealized_pnl:+.2f} ({unrealized_pnl_pct:+.2f}%)")

def main():
    try:
        analyzer = PerformanceAnalyzer()
        analyzer.analyze_today()
        analyzer.analyze_week()
        
        print("\n" + "=" * 80)
        print("✅ Analysis Complete!")
        print("=" * 80 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

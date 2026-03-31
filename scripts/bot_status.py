#!/usr/bin/env python3
"""
Bot Status Report
=================
Quick status report showing both operational health and financial performance.
Run this anytime to see how the bot is doing today and this week.

Usage:
    python scripts/bot_status.py
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
from alpaca.trading.enums import OrderSide

ALPACA_API_KEY = os.getenv("APCA_API_KEY_ID")
ALPACA_SECRET_KEY = os.getenv("APCA_API_SECRET_KEY")


class BotStatusReporter:
    def __init__(self):
        self.client = TradingClient(ALPACA_API_KEY, ALPACA_SECRET_KEY, paper=True)
        self.positions_file = Path("positions.json")
        self.log_file = Path("logs/short_cycle_trader.log")
        
    def show_status(self):
        """Show complete bot status"""
        print("=" * 90)
        print(f"🤖 LITEBOTX STATUS REPORT - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 90)
        
        # Get account info
        account = self.client.get_account()
        
        # Show operational health first
        self._show_operational_health()
        
        # Then financial performance
        self._show_financial_performance(account)
        
        print("\n" + "=" * 90)
        print("✅ Status Report Complete!")
        print("=" * 90 + "\n")
    
    def _show_operational_health(self):
        """Show operational health metrics"""
        print("\n" + "━" * 90)
        print("🏥 OPERATIONAL HEALTH")
        print("━" * 90)
        
        # Check if bot is running
        bot_running = self._check_bot_running()
        print(f"\n🔌 Bot Status: {'✅ RUNNING' if bot_running else '⚠️  NOT RUNNING'}")
        
        # Check recent log activity
        log_health = self._check_log_health()
        print(f"📝 Log Activity: {log_health['status']}")
        if log_health.get('last_entry'):
            print(f"   Last Entry: {log_health['last_entry']}")
        
        # Check for errors
        error_count = log_health.get('recent_errors', 0)
        if error_count > 0:
            print(f"⚠️  Recent Errors: {error_count} (in last 100 log lines)")
        else:
            print(f"✅ Recent Errors: None")
        
        # Check positions file
        positions = self._load_positions()
        print(f"📊 Position Tracking: {'✅ Active' if positions else '⚠️  No positions tracked'}")
        
    def _show_financial_performance(self, account):
        """Show financial performance metrics"""
        print("\n" + "━" * 90)
        print("💰 FINANCIAL PERFORMANCE")
        print("━" * 90)
        
        # TODAY
        print("\n📊 TODAY:")
        current_equity = float(account.equity)
        last_equity = float(account.last_equity)
        daily_pnl = current_equity - last_equity
        daily_pnl_pct = (daily_pnl / last_equity * 100) if last_equity > 0 else 0
        
        print(f"   Equity: ${current_equity:,.2f}")
        print(f"   P&L: ${daily_pnl:+,.2f} ({daily_pnl_pct:+.2f}%)")
        print(f"   Cash: ${float(account.cash):,.2f}")
        print(f"   Buying Power: ${float(account.buying_power):,.2f}")
        
        # Get today's orders
        today = datetime.now().date()
        request = GetOrdersRequest(
            status="closed",
            after=datetime.combine(today, datetime.min.time()),
            limit=100
        )
        today_orders = self.client.get_orders(filter=request)
        buys_today = [o for o in today_orders if o.side == OrderSide.BUY]
        sells_today = [o for o in today_orders if o.side == OrderSide.SELL]
        
        print(f"\n   Orders: {len(buys_today)} buys, {len(sells_today)} sells")
        
        if sells_today:
            print(f"   Exits: {', '.join(o.symbol for o in sells_today)}")
        if buys_today:
            print(f"   Entries: {', '.join(o.symbol for o in buys_today)}")
        
        # THIS WEEK
        print("\n📅 THIS WEEK:")
        monday = today - timedelta(days=today.weekday())
        request = GetOrdersRequest(
            status="closed",
            after=datetime.combine(monday, datetime.min.time()),
            limit=500
        )
        week_orders = self.client.get_orders(filter=request)
        buys_week = [o for o in week_orders if o.side == OrderSide.BUY]
        sells_week = [o for o in week_orders if o.side == OrderSide.SELL]
        
        total_invested = sum(float(o.filled_avg_price) * int(o.filled_qty) for o in buys_week)
        total_proceeds = sum(float(o.filled_avg_price) * int(o.filled_qty) for o in sells_week)
        
        # Calculate realized P&L for completed trades
        symbols_traded = set(o.symbol for o in week_orders)
        total_realized_pnl = 0
        winning_trades = 0
        losing_trades = 0
        
        for symbol in symbols_traded:
            symbol_buys = [o for o in buys_week if o.symbol == symbol]
            symbol_sells = [o for o in sells_week if o.symbol == symbol]
            
            buy_qty = sum(int(o.filled_qty) for o in symbol_buys)
            sell_qty = sum(int(o.filled_qty) for o in symbol_sells)
            
            buy_cost = sum(float(o.filled_avg_price) * int(o.filled_qty) for o in symbol_buys)
            sell_proceeds = sum(float(o.filled_avg_price) * int(o.filled_qty) for o in symbol_sells)
            
            if buy_qty > 0 and sell_qty > 0 and buy_qty == sell_qty:
                pnl = sell_proceeds - buy_cost
                total_realized_pnl += pnl
                if pnl > 0:
                    winning_trades += 1
                else:
                    losing_trades += 1
        
        total_trades = winning_trades + losing_trades
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        print(f"   Trades Closed: {total_trades} ({winning_trades}W/{losing_trades}L)")
        print(f"   Win Rate: {win_rate:.1f}%")
        print(f"   Realized P&L: ${total_realized_pnl:+,.2f}")
        print(f"   Capital Deployed: ${total_invested:,.2f}")
        
        # OPEN POSITIONS
        positions = self.client.get_all_positions()
        if positions:
            total_unrealized = sum(float(p.unrealized_pl) for p in positions)
            print(f"\n📦 OPEN POSITIONS: {len(positions)}")
            print(f"   Unrealized P&L: ${total_unrealized:+,.2f}")
            
            # Show each position
            for pos in positions:
                unrealized_pnl = float(pos.unrealized_pl)
                unrealized_pnl_pct = float(pos.unrealized_plpc) * 100
                print(f"   • {pos.symbol}: {pos.qty} @ ${float(pos.current_price):.2f} "
                      f"| P&L: ${unrealized_pnl:+.2f} ({unrealized_pnl_pct:+.2f}%)")
        else:
            print(f"\n📦 OPEN POSITIONS: None")
    
    def _check_bot_running(self):
        """Check if bot process is running"""
        try:
            import subprocess
            result = subprocess.run(
                ['ps', 'aux'],
                capture_output=True,
                text=True
            )
            # Look for common bot process names
            for line in result.stdout.split('\n'):
                if any(name in line for name in ['start_litebotx', 'automated_momentum_trader', 'short_cycle_trader']):
                    if 'python' in line:
                        return True
            return False
        except:
            return None  # Can't determine
    
    def _check_log_health(self):
        """Check recent log activity"""
        health = {
            'status': '⚠️  No log file found',
            'last_entry': None,
            'recent_errors': 0
        }
        
        if not self.log_file.exists():
            return health
        
        try:
            # Read last 100 lines
            with open(self.log_file, 'r') as f:
                lines = f.readlines()
                recent_lines = lines[-100:] if len(lines) > 100 else lines
            
            if recent_lines:
                # Get last timestamp
                for line in reversed(recent_lines):
                    if line.strip():
                        health['last_entry'] = line[:30]  # First 30 chars usually has timestamp
                        break
                
                # Count errors
                health['recent_errors'] = sum(1 for line in recent_lines if 'ERROR' in line)
                
                # Check if recent (within last hour)
                try:
                    last_time = datetime.strptime(health['last_entry'][:19], '%Y-%m-%d %H:%M:%S')
                    time_diff = datetime.now() - last_time
                    if time_diff.total_seconds() < 3600:  # Within last hour
                        health['status'] = '✅ Active (recent activity)'
                    else:
                        health['status'] = f'⚠️  Last activity {int(time_diff.total_seconds() / 3600)}h ago'
                except:
                    health['status'] = '✅ Active'
            
            return health
        except Exception as e:
            health['status'] = f'⚠️  Error reading log: {e}'
            return health
    
    def _load_positions(self):
        """Load positions from JSON file"""
        try:
            if self.positions_file.exists():
                with open(self.positions_file, 'r') as f:
                    data = json.load(f)
                    return data if isinstance(data, list) else []
            return []
        except:
            return []


def main():
    try:
        reporter = BotStatusReporter()
        reporter.show_status()
    except Exception as e:
        print(f"\n❌ Error generating status report: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

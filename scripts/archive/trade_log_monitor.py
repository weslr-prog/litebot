#!/usr/bin/env python3
"""
Trade Log Monitor and Dashboard
Monitor and display trade logs in real-time with enhanced formatting
"""

import os
import sys
import time
import json
from datetime import datetime, timedelta
from pathlib import Path

class TradeLogMonitor:
    """Monitor and display trade logs with enhanced formatting"""

    def __init__(self, log_directory="logs"):
        self.log_directory = Path(log_directory)
        self.sprint1_log = self.log_directory / "sprint1_alpaca.log"
        self.last_position = 0

    def get_recent_trades(self, hours=24):
        """Get recent trades from the last N hours"""
        if not self.sprint1_log.exists():
            return []

        trades = []
        cutoff_time = datetime.now() - timedelta(hours=hours)

        try:
            with open(self.sprint1_log, 'r') as f:
                for line in f:
                    if "Trade executed" in line or "BUY order submitted" in line or "SELL order submitted" in line:
                        # Parse timestamp
                        try:
                            timestamp_str = line.split(' - ')[0]
                            # Handle format: 2025-09-10 16:49:25,586
                            log_time = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S,%f')

                            if log_time > cutoff_time:
                                trades.append({
                                    'timestamp': log_time,
                                    'line': line.strip()
                                })
                        except (ValueError, IndexError) as e:
                            # Debug: print parsing errors
                            if "Trade executed" in line or "BUY order submitted" in line or "SELL order submitted" in line:
                                print(f"Failed to parse timestamp: {timestamp_str} | Error: {e}")
                            continue

        except Exception as e:
            print(f"Error reading log file: {e}")

        return trades

    def format_trade_display(self, trade):
        """Format a trade entry for display"""
        line = trade['line']
        timestamp = trade['timestamp'].strftime('%H:%M:%S')

        if "BUY order submitted" in line:
            # Extract trade details
            parts = line.split(' - AlpacaTradeExecutor - INFO - 🟢 BUY order submitted: ')
            if len(parts) > 1:
                trade_info = parts[1].split(' @ ')
                if len(trade_info) > 0:
                    symbol_shares = trade_info[0]
                    price = trade_info[1] if len(trade_info) > 1 else "N/A"

                    return f"🟢 {timestamp} | BUY | {symbol_shares} | ${price}"

        elif "SELL order submitted" in line:
            parts = line.split(' - AlpacaTradeExecutor - INFO - 🔴 SELL order submitted: ')
            if len(parts) > 1:
                trade_info = parts[1].split(' @ ')
                if len(trade_info) > 0:
                    symbol_shares = trade_info[0]
                    price = trade_info[1] if len(trade_info) > 1 else "N/A"

                    return f"🔴 {timestamp} | SELL | {symbol_shares} | ${price}"

        elif "Trade executed" in line:
            parts = line.split("✅ Trade executed: ")
            if len(parts) > 1:
                try:
                    trade_data = eval(parts[1])  # Safe since we control the log format
                    action = trade_data.get('action', 'unknown').upper()
                    symbol = trade_data.get('symbol', 'N/A')
                    shares = trade_data.get('shares', 0)
                    price = trade_data.get('price', 0)
                    order_id = str(trade_data.get('order_id', 'N/A'))[:8]

                    return f"✅ {timestamp} | {action} | {symbol} x{shares} | ${price:.2f} | ID:{order_id}"
                except:
                    return f"✅ {timestamp} | Trade executed (details parsing failed)"

        return f"📝 {timestamp} | {line.split(' - ')[-1][:80]}..."

    def display_trade_summary(self, hours=24):
        """Display a summary of recent trades"""
        trades = self.get_recent_trades(hours)

        print(f"\n📊 TRADE LOG SUMMARY (Last {hours} hours)")
        print("=" * 60)

        if not trades:
            print("❌ No trades found in the specified time period")
            print("💡 Check if the trading system is running and connected to Alpaca")
            return

        # Group trades by symbol
        symbol_trades = {}
        total_buy_value = 0
        total_sell_value = 0
        buy_count = 0
        sell_count = 0

        for trade in trades:
            line = trade['line']

            if "BUY order submitted" in line:
                buy_count += 1
                # Extract value
                try:
                    parts = line.split('BUY order submitted: ')[1].split(' @ ')
                    symbol_shares = parts[0]
                    symbol = symbol_shares.split(' x')[0]
                    shares = int(symbol_shares.split(' x')[1])
                    price = float(parts[1])

                    if symbol not in symbol_trades:
                        symbol_trades[symbol] = {'buys': 0, 'sells': 0, 'buy_value': 0, 'sell_value': 0}

                    symbol_trades[symbol]['buys'] += shares
                    symbol_trades[symbol]['buy_value'] += shares * price
                    total_buy_value += shares * price
                except:
                    pass

            elif "SELL order submitted" in line:
                sell_count += 1
                try:
                    parts = line.split('SELL order submitted: ')[1].split(' @ ')
                    symbol_shares = parts[0]
                    symbol = symbol_shares.split(' x')[0]
                    shares = int(symbol_shares.split(' x')[1])
                    price = float(parts[1])

                    if symbol not in symbol_trades:
                        symbol_trades[symbol] = {'buys': 0, 'sells': 0, 'buy_value': 0, 'sell_value': 0}

                    symbol_trades[symbol]['sells'] += shares
                    symbol_trades[symbol]['sell_value'] += shares * price
                    total_sell_value += shares * price
                except:
                    pass

        # Display summary
        print(f"📈 Total Trades: {len(trades)}")
        print(f"🟢 Buy Orders: {buy_count}")
        print(f"🔴 Sell Orders: {sell_count}")
        print(".2f")
        print(".2f")

        if symbol_trades:
            print(f"\n📋 Trades by Symbol:")
            for symbol, data in symbol_trades.items():
                print(f"   {symbol}: {data['buys']} buys, {data['sells']} sells")

        print(f"\n📝 Recent Trade Details:")
        print("-" * 60)

        # Display last 10 trades
        for trade in trades[-10:]:
            print(self.format_trade_display(trade))

    def monitor_live_trades(self, interval_seconds=30):
        """Monitor trades in real-time"""
        print("🔴 LIVE TRADE MONITOR (Press Ctrl+C to stop)")
        print("=" * 60)
        print("Monitoring for new trades every", interval_seconds, "seconds...")
        print("Last 5 trades will be shown")
        print()

        try:
            while True:
                trades = self.get_recent_trades(hours=1)  # Last hour

                if trades:
                    # Clear screen and show last 5 trades
                    print("\033[2J\033[H")  # Clear screen
                    print("🔴 LIVE TRADE MONITOR")
                    print("=" * 60)
                    print(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")
                    print()

                    for trade in trades[-5:]:
                        print(self.format_trade_display(trade))

                    print()
                    print("⏳ Waiting for next update...")

                time.sleep(interval_seconds)

        except KeyboardInterrupt:
            print("\n👋 Trade monitoring stopped")

def main():
    """Main function"""
    import argparse

    parser = argparse.ArgumentParser(description='Trade Log Monitor')
    parser.add_argument('--hours', type=int, default=24, help='Hours to look back')
    parser.add_argument('--live', action='store_true', help='Monitor trades in real-time')
    parser.add_argument('--interval', type=int, default=30, help='Live monitoring interval in seconds')

    args = parser.parse_args()

    monitor = TradeLogMonitor()

    if args.live:
        monitor.monitor_live_trades(args.interval)
    else:
        monitor.display_trade_summary(args.hours)

if __name__ == "__main__":
    main()

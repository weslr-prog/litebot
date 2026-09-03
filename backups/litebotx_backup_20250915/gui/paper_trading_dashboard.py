#!/usr/bin/env python3
"""
Sprint 1 Paper Trading Dashboard
Real-time monitoring of paper trading performance
"""

import os
import sys
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List

def clear_screen():
    """Clear terminal screen"""
    os.system('clear' if os.name == 'posix' else 'cls')

def read_log_file(log_path: str, lines: int = 50) -> List[str]:
    """Read recent lines from log file"""
    try:
        with open(log_path, 'r') as f:
            return f.readlines()[-lines:]
    except FileNotFoundError:
        return ["Log file not found"]
    except Exception as e:
        return [f"Error reading log: {e}"]

def parse_trading_signals(log_lines: List[str]) -> List[Dict]:
    """Extract trading signals from log lines"""
    signals = []
    for line in log_lines:
        if "Generated Signals:" in line or "buy" in line or "sell" in line:
            signals.append({
                'timestamp': datetime.now(),
                'signal': line.strip()
            })
    return signals[-10:]  # Last 10 signals

def get_system_status() -> Dict:
    """Get current system status"""
    try:
        # Check if any python processes are running sprint1
        import subprocess
        result = subprocess.run(['pgrep', '-f', 'sprint1'], capture_output=True, text=True)
        is_running = bool(result.stdout.strip())
        
        return {
            'is_running': is_running,
            'processes': result.stdout.strip().split('\n') if is_running else [],
            'timestamp': datetime.now()
        }
    except Exception as e:
        return {
            'is_running': False,
            'error': str(e),
            'timestamp': datetime.now()
        }

def display_dashboard():
    """Display real-time dashboard"""
    while True:
        try:
            clear_screen()
            
            print("📊 Sprint 1 Paper Trading Dashboard")
            print("=" * 60)
            print(f"🕐 Current Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print()
            
            # System Status
            status = get_system_status()
            print("🔧 System Status:")
            if status['is_running']:
                print(f"  ✅ Paper Trading: RUNNING")
                print(f"  🔢 Process Count: {len(status['processes'])}")
            else:
                print(f"  ❌ Paper Trading: STOPPED")
                if 'error' in status:
                    print(f"  ⚠️  Error: {status['error']}")
            print()
            
            # Market Hours Check
            now = datetime.now()
            market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
            market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)
            is_market_hours = market_open <= now <= market_close and now.weekday() < 5
            
            print("📈 Market Status:")
            print(f"  🕘 Market Hours: {'OPEN' if is_market_hours else 'CLOSED'}")
            print(f"  📅 Day: {now.strftime('%A')}")
            if is_market_hours:
                remaining = market_close - now
                print(f"  ⏰ Time to Close: {str(remaining).split('.')[0]}")
            else:
                if now.weekday() < 5:  # Weekday
                    if now.hour < 9 or (now.hour == 9 and now.minute < 30):
                        next_open = market_open
                        print(f"  🌅 Time to Open: {str(next_open - now).split('.')[0]}")
                    else:
                        next_open = (now + timedelta(days=1)).replace(hour=9, minute=30)
                        print(f"  🌅 Next Open: Tomorrow {next_open.strftime('%H:%M')}")
                else:
                    # Weekend
                    days_to_monday = 7 - now.weekday()
                    next_monday = (now + timedelta(days=days_to_monday)).replace(hour=9, minute=30)
                    print(f"  🌅 Next Open: {next_monday.strftime('%A %H:%M')}")
            print()
            
            # Recent Log Activity
            print("📋 Recent Activity:")
            log_path = "logs/realtime_data_feed.log"
            if os.path.exists(log_path):
                recent_logs = read_log_file(log_path, 5)
                for log_line in recent_logs:
                    if log_line.strip():
                        # Truncate long lines
                        display_line = log_line.strip()
                        if len(display_line) > 80:
                            display_line = display_line[:77] + "..."
                        print(f"  {display_line}")
            else:
                print(f"  ⚠️  Log file not found: {log_path}")
            print()
            
            # Trading Signals
            print("🎯 Recent Signals:")
            if os.path.exists(log_path):
                log_lines = read_log_file(log_path, 100)
                signals = parse_trading_signals(log_lines)
                if signals:
                    for signal in signals[-5:]:  # Last 5 signals
                        print(f"  📈 {signal['signal']}")
                else:
                    print("  📭 No recent signals")
            else:
                print("  ⚠️  Cannot read signals - log file missing")
            print()
            
            # Commands
            print("🛠️  Commands:")
            print("  Ctrl+C: Exit Dashboard")
            print("  📊 Dashboard refreshes every 30 seconds")
            
            # Performance Stats
            if os.path.exists(log_path):
                log_lines = read_log_file(log_path, 1000)
                error_count = sum(1 for line in log_lines if "ERROR" in line)
                signal_count = sum(1 for line in log_lines if "signals generated:" in line.lower())
                
                print()
                print("📊 Session Statistics:")
                print(f"  🎯 Signals Generated: {signal_count}")
                print(f"  ❌ Errors Logged: {error_count}")
                print(f"  📈 Error Rate: {(error_count / max(len(log_lines), 1)) * 100:.1f}%")
            
            print("\n" + "=" * 60)
            print("🚀 Sprint 1 Paper Trading - Weekly ROI Validation")
            
            # Wait for next refresh
            time.sleep(30)
            
        except KeyboardInterrupt:
            print("\n👋 Dashboard stopped by user")
            break
        except Exception as e:
            print(f"\n❌ Dashboard error: {e}")
            time.sleep(5)

def main():
    """Launch the paper trading dashboard"""
    print("🚀 Starting Sprint 1 Paper Trading Dashboard...")
    print("📊 Monitoring paper trading system in real-time")
    print("⚠️  Make sure paper trading is running in another terminal")
    print()
    
    input("Press Enter to start dashboard...")
    display_dashboard()

if __name__ == "__main__":
    main()

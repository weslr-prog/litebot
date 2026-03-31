#!/usr/bin/env python3
"""
Bot Status Monitor - Quick status check for autonomous operation
===============================================================

Use this script to quickly check bot status while you're at work.
"""

import os
import sys
import json
import datetime as dt
from datetime import datetime, timedelta
import subprocess

def check_bot_process():
    """Check if bot process is running"""
    try:
        result = subprocess.run(['pgrep', '-f', 'launch_paper_testing'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            pids = result.stdout.strip().split('\n')
            return len(pids), pids
        else:
            return 0, []
    except Exception:
        return 0, []

def check_positions():
    """Check current positions"""
    try:
        if not os.path.exists("positions.json"):
            return "No positions file found"
        
        with open("positions.json", 'r') as f:
            positions = json.load(f)
        
        if not positions:
            return "No positions"
        
        status = []
        for pos in positions:
            if pos['status'] == 'entered':
                entry_date = pos['entry_date']
                exit_date = pos['exit_date']
                pnl = ""
                if pos.get('realized_pnl'):
                    pnl = f" (P&L: ${pos['realized_pnl']:.2f})"
                
                status.append(f"{pos['symbol']}: {pos['position_size_shares']} shares @ ${pos['entry_price']:.2f}{pnl}")
                status.append(f"  Entry: {entry_date}, Exit: {exit_date}")
            elif pos['status'] == 'exited':
                pnl = pos.get('realized_pnl', 0)
                status.append(f"{pos['symbol']}: EXITED - P&L: ${pnl:.2f}")
        
        return '\n'.join(status) if status else "No active positions"
        
    except Exception as e:
        return f"Error reading positions: {e}"

def check_recent_logs():
    """Check recent bot activity"""
    try:
        log_files = ['bot.log', 'logs/trading_bot.log', 'trading_bot.log']
        
        for log_file in log_files:
            if os.path.exists(log_file):
                # Get last few lines
                with open(log_file, 'r') as f:
                    lines = f.readlines()
                
                if lines:
                    recent_lines = lines[-5:]  # Last 5 lines
                    return ''.join(recent_lines)
        
        return "No recent log activity found"
        
    except Exception as e:
        return f"Error reading logs: {e}"

def main():
    print("🤖 BOT STATUS MONITOR")
    print("=" * 40)
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check process
    process_count, pids = check_bot_process()
    if process_count > 0:
        print(f"✅ Bot running (PID: {', '.join(pids)})")
    else:
        print("❌ Bot not running")
    
    print()
    
    # Check positions
    print("📊 POSITIONS:")
    print("-" * 20)
    positions_status = check_positions()
    print(positions_status)
    
    print()
    
    # Check D+1 schedule
    print("📅 D+1 EXIT SCHEDULE:")
    print("-" * 20)
    try:
        with open("positions.json", 'r') as f:
            positions = json.load(f)
        
        tomorrow = dt.date.today() + timedelta(days=1)
        exits_tomorrow = []
        
        for pos in positions:
            if pos['status'] == 'entered' and pos.get('exit_date'):
                exit_date = dt.datetime.strptime(pos['exit_date'], '%Y-%m-%d').date()
                if exit_date == tomorrow:
                    exits_tomorrow.append(f"{pos['symbol']} ({pos['position_size_shares']} shares)")
        
        if exits_tomorrow:
            print(f"Tomorrow ({tomorrow}): {', '.join(exits_tomorrow)}")
        else:
            print("No exits scheduled for tomorrow")
            
    except Exception as e:
        print(f"Error checking schedule: {e}")
    
    print()
    
    # Recent activity
    print("📋 RECENT ACTIVITY:")
    print("-" * 20)
    recent_logs = check_recent_logs()
    print(recent_logs[-200:])  # Last 200 characters
    
    print()
    print("🔄 Run this script anytime to check bot status")

if __name__ == "__main__":
    main()
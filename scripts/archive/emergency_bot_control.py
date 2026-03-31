#!/usr/bin/env python3
"""
Emergency Bot Control - Stop/Start bot remotely
==============================================

Quick commands for emergency bot control while at work.
"""

import subprocess
import sys
import os

def stop_bot():
    """Stop the trading bot"""
    try:
        print("🛑 Stopping trading bot...")
        
        # Kill bot processes
        result = subprocess.run(['pkill', '-f', 'launch_paper_testing'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Bot stopped successfully")
        else:
            print("ℹ️ No bot processes found to stop")
        
        # Also try to kill any dashboard processes
        subprocess.run(['pkill', '-f', 'dashboard'], capture_output=True)
        
        return True
        
    except Exception as e:
        print(f"❌ Error stopping bot: {e}")
        return False

def start_bot():
    """Start the trading bot"""
    try:
        print("🚀 Starting trading bot...")
        
        # Check if already running
        result = subprocess.run(['pgrep', '-f', 'launch_paper_testing'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print("⚠️ Bot is already running")
            return True
        
        # Start bot in background
        subprocess.Popen(['bash', '-c', 'cd /home/wes/Desktop/litebotx-usb-deployment && echo "3" | nohup bash scripts/launch_paper_testing.sh > bot.log 2>&1 &'])
        
        print("✅ Bot started in background")
        print("📋 Use 'python3 check_bot_status.py' to verify status")
        
        return True
        
    except Exception as e:
        print(f"❌ Error starting bot: {e}")
        return False

def show_help():
    """Show available commands"""
    print("🤖 EMERGENCY BOT CONTROL")
    print("=" * 30)
    print("Commands:")
    print("  stop    - Stop the trading bot")
    print("  start   - Start the trading bot") 
    print("  status  - Check bot status")
    print("  help    - Show this help")
    print()
    print("Examples:")
    print("  python3 emergency_bot_control.py stop")
    print("  python3 emergency_bot_control.py start")

def check_status():
    """Quick status check"""
    try:
        result = subprocess.run(['pgrep', '-f', 'launch_paper_testing'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            pids = result.stdout.strip().split('\n')
            print(f"✅ Bot running (PID: {', '.join(pids)})")
        else:
            print("❌ Bot not running")
            
    except Exception as e:
        print(f"❌ Error checking status: {e}")

def main():
    if len(sys.argv) < 2:
        show_help()
        return
    
    command = sys.argv[1].lower()
    
    if command == "stop":
        stop_bot()
    elif command == "start":
        start_bot()
    elif command == "status":
        check_status()
    elif command == "help":
        show_help()
    else:
        print(f"❌ Unknown command: {command}")
        show_help()

if __name__ == "__main__":
    main()
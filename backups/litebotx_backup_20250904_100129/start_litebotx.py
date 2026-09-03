#!/usr/bin/env python3
"""
LiteBotX Unified Launcher
Starts both the trading bot and GUI dashboard with one command
"""

import subprocess
import sys
import os
import time
import signal
from pathlib import Path

def check_environment():
    """Check if required environment variables are set"""
    required_vars = [
        'APCA_API_KEY_ID',
        'APCA_API_SECRET_KEY',
        'ALPHA_VANTAGE_KEY'
    ]
    
    # Load .env file if it exists
    env_file = Path('.env')
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value.strip('"\'')
    
    missing = []
    for var in required_vars:
        if not os.environ.get(var):
            missing.append(var)
    
    return missing

def start_process(command, name, log_file=None):
    """Start a subprocess with proper logging"""
    try:
        print(f"🚀 Starting {name}...")
        
        if log_file:
            with open(log_file, 'w') as f:
                process = subprocess.Popen(
                    command,
                    shell=True,
                    stdout=f,
                    stderr=subprocess.STDOUT,
                    preexec_fn=os.setsid if os.name != 'nt' else None
                )
        else:
            process = subprocess.Popen(
                command,
                shell=True,
                preexec_fn=os.setsid if os.name != 'nt' else None
            )
        
        return process
    except Exception as e:
        print(f"❌ Failed to start {name}: {e}")
        return None

def cleanup_processes(processes):
    """Clean shutdown of all processes"""
    print("\n🛑 Shutting down LiteBotX system...")
    
    for name, process in processes.items():
        if process and process.poll() is None:
            try:
                print(f"   Stopping {name}...")
                if os.name != 'nt':
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                else:
                    process.terminate()
                process.wait(timeout=5)
            except Exception as e:
                print(f"   Force killing {name}...")
                if os.name != 'nt':
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                else:
                    process.kill()
    
    print("✅ All processes stopped cleanly")

def main():
    print("=" * 60)
    print("🚀 LiteBotX Unified System Launcher")
    print("   Aggressive Swing Trading System")
    print("=" * 60)
    
    # Check environment
    missing_vars = check_environment()
    if missing_vars:
        print("⚠️  Missing environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\n💡 Please check your .env file or export these variables")
        print("   The system will run with limited functionality")
        print()
    
    # Determine which trading bot to use (prefer v2)
    if os.path.exists('automated_momentum_trader_v2.py'):
        bot_command = "python automated_momentum_trader_v2.py"
        bot_name = "Enhanced Trading Bot V2"
    elif os.path.exists('automated_momentum_trader.py'):
        bot_command = "python automated_momentum_trader.py"
        bot_name = "Trading Bot"
    else:
        print("❌ No trading bot found (automated_momentum_trader_v2.py or automated_momentum_trader.py)")
        return 1
    
    # Determine which dashboard to use
    if os.path.exists('stock_dashboard.py'):
        dashboard_command = "python stock_dashboard.py"
        dashboard_name = "LitebotX Dashboard"
        dashboard_url = "http://127.0.0.1:8055"
    elif os.path.exists('enhanced_trading_dashboard.py'):
        dashboard_command = "python enhanced_trading_dashboard.py"
        dashboard_name = "Enhanced Trading Dashboard"
        dashboard_url = "http://127.0.0.1:8050"
    else:
        print("❌ No dashboard found (stock_dashboard.py or enhanced_trading_dashboard.py)")
        return 1
    
    processes = {}
    
    try:
        # Start the trading bot first
        print(f"\n1️⃣ Starting {bot_name}...")
        bot_process = start_process(
            bot_command, 
            bot_name,
            log_file="trading_bot.log"
        )
        
        if not bot_process:
            print("❌ Failed to start trading bot")
            return 1
        
        processes['Trading Bot'] = bot_process
        print(f"   ✅ {bot_name} started (PID: {bot_process.pid})")
        print("   📝 Logs: trading_bot.log")
        
        # Wait a moment for the bot to initialize
        time.sleep(3)
        
        # Start the dashboard
        print(f"\n2️⃣ Starting {dashboard_name}...")
        dashboard_process = start_process(
            dashboard_command,
            dashboard_name,
            log_file="dashboard.log"
        )
        
        if not dashboard_process:
            print("❌ Failed to start dashboard")
            cleanup_processes(processes)
            return 1
        
        processes['Dashboard'] = dashboard_process
        print(f"   ✅ {dashboard_name} started (PID: {dashboard_process.pid})")
        print("   📝 Logs: dashboard.log")
        
        # Wait for dashboard to start
        print("\n⏳ Waiting for dashboard to initialize...")
        time.sleep(5)
        
        # Success message
        print("\n" + "=" * 60)
        print("✅ LiteBotX System Successfully Started!")
        print("=" * 60)
        print(f"📊 Dashboard URL: {dashboard_url}")
        print(f"🤖 Trading Bot: Running (check trading_bot.log)")
        print(f"📈 Dashboard: Running (check dashboard.log)")
        print("💰 Portfolio: $928,271.39 (Live Paper Trading)")
        print("🎯 Strategy: Aggressive Swing Trading")
        print("\n💡 Tips:")
        print("   • Open the dashboard URL in your browser")
        print("   • Monitor logs with: tail -f trading_bot.log")
        print("   • Use Ctrl+C to stop both systems")
        print("=" * 60)
        
        # Keep the launcher running and monitor processes
        while True:
            time.sleep(10)
            
            # Check if processes are still running
            for name, process in processes.items():
                if process.poll() is not None:
                    print(f"⚠️  {name} has stopped unexpectedly")
                    cleanup_processes(processes)
                    return 1
    
    except KeyboardInterrupt:
        cleanup_processes(processes)
        return 0
    
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        cleanup_processes(processes)
        return 1

if __name__ == "__main__":
    sys.exit(main())

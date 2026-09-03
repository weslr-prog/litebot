#!/usr/bin/env python3
"""
LiteBotX Emergency Stop Script
Safely stops all trading and frees ports
"""

import subprocess
import os
import signal
import sys
import time

def kill_processes_by_name(process_names):
    """Kill processes by name"""
    killed = []
    
    for process_name in process_names:
        try:
            # Find processes
            result = subprocess.run(['pgrep', '-f', process_name], 
                                 capture_output=True, text=True)
            
            if result.returncode == 0:
                pids = result.stdout.strip().split('\n')
                for pid in pids:
                    if pid:
                        try:
                            os.kill(int(pid), signal.SIGTERM)
                            killed.append(f"{process_name} (PID: {pid})")
                            time.sleep(1)
                            
                            # Force kill if still running
                            try:
                                os.kill(int(pid), 0)  # Check if still alive
                                os.kill(int(pid), signal.SIGKILL)
                                print(f"   Force killed {process_name} (PID: {pid})")
                            except ProcessLookupError:
                                pass  # Already dead
                                
                        except ProcessLookupError:
                            pass  # Already dead
        except Exception as e:
            print(f"   Error stopping {process_name}: {e}")
    
    return killed

def free_ports():
    """Free common ports used by LiteBotX"""
    ports = [8050, 8055, 8056]
    
    for port in ports:
        try:
            # Find processes using the port
            result = subprocess.run(['lsof', '-ti', f':{port}'], 
                                 capture_output=True, text=True)
            
            if result.returncode == 0:
                pids = result.stdout.strip().split('\n')
                for pid in pids:
                    if pid:
                        try:
                            os.kill(int(pid), signal.SIGTERM)
                            print(f"   Freed port {port} (PID: {pid})")
                        except ProcessLookupError:
                            pass
        except Exception as e:
            print(f"   Error freeing port {port}: {e}")

def main():
    print("🛑 LiteBotX Emergency Stop")
    print("=" * 40)
    
    # Stop trading processes
    print("\n🤖 Stopping trading bot...")
    trading_processes = [
        'automated_momentum_trader',
        'start_litebotx.py',
        'momentum_trader'
    ]
    killed_trading = kill_processes_by_name(trading_processes)
    
    # Stop dashboard processes
    print("\n📊 Stopping dashboard...")
    dashboard_processes = [
        'stock_dashboard',
        'enhanced_trading_dashboard',
        'dashboard.py'
    ]
    killed_dashboard = kill_processes_by_name(dashboard_processes)
    
    # Free ports
    print("\n🔓 Freeing ports...")
    free_ports()
    
    # Summary
    print("\n" + "=" * 40)
    print("✅ Emergency Stop Complete")
    print("=" * 40)
    
    if killed_trading:
        print("🤖 Trading Bot Stopped:")
        for proc in killed_trading:
            print(f"   ✅ {proc}")
    
    if killed_dashboard:
        print("📊 Dashboard Stopped:")
        for proc in killed_dashboard:
            print(f"   ✅ {proc}")
    
    print("\n💡 All trading activity has been halted")
    print("🔓 All ports have been freed")
    print("🔒 System is safe to restart")

if __name__ == "__main__":
    main()

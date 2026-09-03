#!/usr/bin/env python3
"""
Dual Dashboard Launcher
Launch both Stock Dashboard (8055) and Crypto Dashboard (8050) simultaneously
"""

import os
import sys
import subprocess
import time
from pathlib import Path
import signal


def load_env_file():
    """Load environment variables from .env file"""
    env_file = Path(".env")
    if env_file.exists():
        print("📁 Loading .env file...")
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value


def check_files():
    """Check if required dashboard files exist"""
    required_files = [
        "stock_dashboard.py",
        "enhanced_trading_dashboard.py"  # Your crypto dashboard
    ]
    
    missing_files = []
    for file in required_files:
        if not Path(file).exists():
            missing_files.append(file)
    
    if missing_files:
        print("❌ Missing required files:")
        for file in missing_files:
            print(f"   - {file}")
        return False
    
    return True


def launch_dashboard(script_name, dashboard_name, port):
    """Launch a dashboard in a separate process"""
    try:
        print(f"🚀 Starting {dashboard_name}...")
        print(f"📊 {dashboard_name} will be available at: http://127.0.0.1:{port}")
        
        # Start the dashboard process
        process = subprocess.Popen(
            [sys.executable, script_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        return process
    
    except Exception as e:
        print(f"❌ Failed to launch {dashboard_name}: {e}")
        return None


def main():
    """Main launcher function"""
    print("🚀 LiteBotX Dual Dashboard Launcher")
    print("=" * 50)
    print("📊 Stock Dashboard (Port 8055)")
    print("💰 Crypto Dashboard (Port 8050)")
    print("=" * 50)
    
    # Load environment variables
    load_env_file()
    
    # Check required files
    if not check_files():
        print("💡 Please ensure all dashboard files are in the current directory")
        sys.exit(1)
    
    processes = []
    
    try:
        # Launch Stock Dashboard
        stock_process = launch_dashboard(
            "stock_dashboard.py", 
            "Stock Trading Dashboard", 
            8055
        )
        if stock_process:
            processes.append(("Stock Dashboard", stock_process))
            time.sleep(2)  # Give it time to start
        
        # Launch Crypto Dashboard (if it exists)
        if Path("enhanced_trading_dashboard.py").exists():
            crypto_process = launch_dashboard(
                "enhanced_trading_dashboard.py", 
                "Crypto Trading Dashboard", 
                8050
            )
            if crypto_process:
                processes.append(("Crypto Dashboard", crypto_process))
                time.sleep(2)
        
        print("\n" + "=" * 50)
        print("✅ Both dashboards launched successfully!")
        print("\n🌐 Access your dashboards:")
        print("📊 Stock Dashboard:  http://127.0.0.1:8055")
        print("💰 Crypto Dashboard: http://127.0.0.1:8050")
        print("\n💡 Press Ctrl+C to stop both dashboards")
        print("=" * 50)
        
        # Monitor processes
        while True:
            time.sleep(1)
            # Check if any process has died
            for name, process in processes:
                if process.poll() is not None:
                    print(f"⚠️ {name} has stopped")
    
    except KeyboardInterrupt:
        print("\n👋 Stopping all dashboards...")
        
        # Terminate all processes
        for name, process in processes:
            try:
                print(f"🛑 Stopping {name}...")
                process.terminate()
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                print(f"🔨 Force killing {name}...")
                process.kill()
            except Exception as e:
                print(f"⚠️ Error stopping {name}: {e}")
        
        print("✅ All dashboards stopped")
    
    except Exception as e:
        print(f"❌ Error in main loop: {e}")
        
        # Clean up processes
        for name, process in processes:
            try:
                process.terminate()
            except:
                pass


if __name__ == "__main__":
    main()

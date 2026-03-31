#!/usr/bin/env python3
"""
Simple launcher for automated momentum trading
"""

import sys
import subprocess
import signal
import os
from datetime import datetime

def main():
    print("🤖 LiteBotX Automated Momentum Trader Launcher")
    print("=" * 50)
    
    try:
        # Show current time
        now = datetime.now()
        print(f"⏰ Current Time: {now.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Start the automated trader
        print("�� Starting automated momentum trader...")
        print("💡 Press Ctrl+C to stop")
        print()
        
        # Run the automated trader
        process = subprocess.run([
            sys.executable, 
            "automated_momentum_trader.py"
        ])
        
    except KeyboardInterrupt:
        print("\n🛑 Stopping automated trader...")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("👋 Automated trader stopped")

if __name__ == "__main__":
    main()

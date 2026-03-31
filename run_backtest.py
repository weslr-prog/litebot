#!/usr/bin/env python3
"""
Run Backtest and Implement Filter Changes
November 14, 2025

This script:
1. Implements the 5% momentum + 1.5x volume filters
2. Runs comprehensive backtests
3. Compares baseline vs improved performance
"""

import sys
import subprocess
from pathlib import Path

print("="*75)
print("FILTER IMPLEMENTATION & BACKTEST RUNNER")
print("="*75)
print()

# Step 1: Verify filter changes
print("Step 1: Verifying filter changes...")
print("-"*75)

config_file = Path("/home/wes/Desktop/litebotx-usb-deployment/small_portfolio_config.py")
with open(config_file, 'r') as f:
    content = f.read()
    if "min_momentum: float = 0.050" in content:
        print("✅ Momentum filter updated to 5.0%")
    else:
        print("⚠️  Momentum filter NOT updated (still at 3.5%)")
        print("   Manual update required in small_portfolio_config.py line ~67")

# Step 2: Check dependencies
print()
print("Step 2: Checking dependencies...")
print("-"*75)

try:
    import yfinance
    print("✅ yfinance installed")
except ImportError:
    print("⚠️  yfinance not installed")
    print("   Run: pip install yfinance")
    sys.exit(1)

try:
    import pandas
    print("✅ pandas installed")
except ImportError:
    print("⚠️  pandas not installed")
    sys.exit(1)

try:
    import numpy
    print("✅ numpy installed")
except ImportError:
    print("⚠️  numpy not installed")
    sys.exit(1)

# Step 3: Run backtest
print()
print("Step 3: Running backtest...")
print("-"*75)
print()

backtest_script = Path("/home/wes/Desktop/litebotx-usb-deployment/backtest/strategy_backtest.py")

if not backtest_script.exists():
    print(f"❌ Backtest script not found at {backtest_script}")
    sys.exit(1)

try:
    result = subprocess.run(
        [sys.executable, str(backtest_script)],
        cwd="/home/wes/Desktop/litebotx-usb-deployment",
        capture_output=False,
        text=True
    )
    
    if result.returncode == 0:
        print()
        print("="*75)
        print("✅ BACKTEST COMPLETED SUCCESSFULLY")
        print("="*75)
        print()
        print("Results saved to: backtest/results/")
        print("Review the comparison report to see baseline vs improved performance")
    else:
        print()
        print("❌ BACKTEST FAILED")
        print(f"Exit code: {result.returncode}")
        
except Exception as e:
    print(f"❌ Error running backtest: {e}")
    sys.exit(1)

print()
print("="*75)
print("NEXT STEPS:")
print("="*75)
print("1. Review results in backtest/results/")
print("2. Check comparison report for baseline vs improved metrics")
print("3. If improved performance is better, keep 5% momentum filter")
print("4. If not, adjust threshold and re-run")
print()

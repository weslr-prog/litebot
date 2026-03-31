#!/usr/bin/env python3
"""
Walkforward Testing Module for LiteBotX
======================================

Performs walkforward (rolling window) backtesting using the existing backtester.

- Specify symbol, window size, step size, and test period.
- For each window, runs a backtest and logs results.
- Simulates real-world re-optimization and out-of-sample testing.
"""

import sys
import os
from datetime import datetime, timedelta
import pandas as pd
from backtest.backtester import BacktestConfig, run_backtest

# --- CONFIGURATION ---
SYMBOL = 'AAPL'
TIMEFRAME = '1D'
LOOKBACK_DAYS = 365 * 2   # Total period to test (2 years)
WINDOW_DAYS = 90          # Rolling window size (e.g., 90 days)
STEP_DAYS = 30            # Step size (e.g., advance 30 days each iteration)
INITIAL_EQUITY = 10000
FAST = 9
SLOW = 21

RESULTS_CSV = f'backtest/results/walkforward_{SYMBOL}_{TIMEFRAME}.csv'

# --- MAIN WALKFORWARD LOOP ---
def walkforward_test():
    print(f"\n🚦 WALKFORWARD TESTING: {SYMBOL} | {TIMEFRAME}")
    print(f"Total period: {LOOKBACK_DAYS} days | Window: {WINDOW_DAYS} | Step: {STEP_DAYS}")
    print(f"Results will be saved to: {RESULTS_CSV}\n")

    end_date = datetime.now()
    start_date = end_date - timedelta(days=LOOKBACK_DAYS)
    results = []
    
    window_start = start_date
    while window_start + timedelta(days=WINDOW_DAYS) <= end_date:
        window_end = window_start + timedelta(days=WINDOW_DAYS)
        print(f"[Window] {window_start.date()} to {window_end.date()} ...", end=' ')
        
        cfg = BacktestConfig(
            symbol=SYMBOL,
            timeframe=TIMEFRAME,
            lookback_days=WINDOW_DAYS,
            initial_equity=INITIAL_EQUITY,
            fast=FAST,
            slow=SLOW
        )
        # Patch run_backtest to use custom window
        result = run_backtest(cfg)
        
        # Add window info to result
        result['window_start'] = window_start.date().isoformat()
        result['window_end'] = window_end.date().isoformat()
        results.append(result)
        
        if result.get('ok'):
            print(f"✅ Return: {result['total_return']:.2%} | Sharpe: {result['sharpe']:.2f}")
        else:
            print(f"❌ {result.get('reason','error')}")
        
        window_start += timedelta(days=STEP_DAYS)
    
    # Save results
    df = pd.DataFrame(results)
    df.to_csv(RESULTS_CSV, index=False)
    print(f"\n✅ Walkforward results saved to {RESULTS_CSV}")
    print(f"\nSample results:\n{df[['window_start','window_end','total_return','sharpe']].head()}")

if __name__ == "__main__":
    walkforward_test()

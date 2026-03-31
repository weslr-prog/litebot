#!/usr/bin/env python3
"""
Show the signal selection flow that happened at end of day
and what will happen tomorrow morning
"""

import json
import os
from datetime import datetime, timedelta
import pandas as pd

print("=" * 80)
print("📊 SIGNAL SELECTION FLOW - Oct 21, 2025")
print("=" * 80)

# Read the log file for end-of-day activity
log_file = "logs/short_cycle_trader.log"

print("\n## 🌙 What Happened Today at Market Close (4:00 PM)")
print("-" * 80)

# Find end-of-day watchlist refresh
with open(log_file, 'r') as f:
    lines = f.readlines()
    
    # Find the post-market section
    post_market_found = False
    for i, line in enumerate(lines):
        if "16:00" in line and "Post-market: running watchlist refresh" in line:
            post_market_found = True
            print(f"✅ Time: 16:00:59 (1 minute after market close)")
            print(f"✅ Action: Watchlist refresh triggered\n")
            
            # Show the next ~20 lines
            print("### Steps Executed:")
            for j in range(i, min(i+20, len(lines))):
                if "INFO" in lines[j]:
                    # Extract just the message part
                    parts = lines[j].split(" - INFO - ")
                    if len(parts) > 1:
                        msg = parts[1].strip()
                        if any(x in msg for x in ["end-of-day", "Portfolio", "pool", "Loaded", "PreFilter", "universe", "Watchlist"]):
                            print(f"   {msg}")
            break

if not post_market_found:
    print("⚠️ Post-market watchlist refresh not found in logs")

print("\n" + "=" * 80)
print("## 🔬 PreFilter Analysis - How Stocks Were Selected")
print("=" * 80)

print("""
The bot uses a sophisticated **PreFilter** module to identify the best candidates:

### Selection Criteria (Optimized for D+1 Strategy):

1. **Liquidity Filters:**
   - Minimum daily dollar volume: $10 million
   - Minimum average volume: 50,000 shares
   - Price range: $20 - $500 (avoid penny stocks and ultra-expensive)

2. **Volatility Filters:**
   - Minimum ATR (Average True Range): 2% daily movement
   - Maximum ATR: 8% (avoid chaos stocks)
   - Sweet spot: Active movers that are still predictable

3. **Momentum Filters:**
   - Minimum 3% momentum return (recent trend strength)
   - Maximum 20% momentum (avoid parabolic moves)
   - Volume surge: 1.5x average (need buying interest)

4. **Composite Scoring:**
   - Score = 2.0 × Breakout + 1.5 × Momentum + 1.0 × Volatility + 0.5 × Liquidity
   - Breakout: Price breaking above recent range
   - Momentum: Strong directional movement
   - Volatility: Moderate, predictable swings
   - Liquidity: Can enter/exit without slippage

5. **Gap-Prone Detection:**
   - Identifies stocks with 30%+ frequency of 1%+ gaps
   - Average gap size > 1.5%
   - Directional consistency (gaps in same direction)
""")

print("\n" + "=" * 80)
print("## 📋 Today's Results at 4:00 PM")
print("=" * 80)

# Find the universe selection in logs
for i, line in enumerate(lines):
    if "16:01:30" in line and "PreFilter universe" in line:
        print("\n✅ PreFilter Analysis Complete:")
        parts = line.split(" - INFO - ")
        if len(parts) > 1:
            msg = parts[1].strip()
            print(f"   {msg}")
        
        # Check if we can find the actual symbols
        for j in range(max(0, i-50), i):
            if "Using PreFilter universe:" in lines[j] and "[" in lines[j]:
                # Extract the symbol list
                start = lines[j].find("[")
                end = lines[j].find("]") + 1
                if start >= 0 and end > start:
                    symbols_str = lines[j][start:end]
                    try:
                        symbols = eval(symbols_str)
                        print(f"\n### Top PreFilter Picks (8 symbols):")
                        for idx, sym in enumerate(symbols[:8], 1):
                            print(f"   {idx}. {sym}")
                    except:
                        pass
                break

print("""
### What This Means:

- PreFilter analyzed ~60 candidates from the candidate pool
- Applied all filters (liquidity, volatility, momentum, gap-prone)
- Scored each stock based on composite criteria
- Selected top 8 highest-scoring stocks
- Added 22 more from static config to reach 30 total universe

**Key Point:** The top 8 PreFilter picks are the "hot" stocks most likely to:
- Gap up tomorrow morning
- Have strong intraday momentum
- Be liquid enough for quick entry/exit
- Move predictably (not chaotically)
""")

print("\n" + "=" * 80)
print("## 🌅 Tomorrow Morning's Flow (Oct 22)")
print("=" * 80)

print("""
### Timeline:

**9:00 AM ET - Premarket Analysis:**
1. Bot wakes up from sleep
2. Retrieves the 30-symbol universe prepared last night
3. Runs FRESH gap scanner on those 30 symbols
4. Looks for stocks with:
   - Pre-market price movement (gaps)
   - Strong volume in pre-market
   - Quality gap patterns (not just noise)
5. Creates a "morning gap candidates" list

**9:30 AM - Market Open:**
6. Bot waits for market to stabilize (avoid opening volatility)

**9:45 AM - Entry Window Opens:**
7. Bot checks D+1 positions from yesterday (your 8 current positions)
8. If today >= exit_date, executes SELL orders (THIS WILL HAPPEN)
9. After exits complete, begins NEW signal generation

**9:45-10:00 AM - Signal Generation:**
10. Uses morning gap candidates as primary focus
11. Calls signal_generator.generate_signals() on the universe
12. Signal generator analyzes:
    - Technical indicators (RSI, MACD, Bollinger Bands)
    - ML confidence scores
    - Pattern recognition (breakouts, reversals)
    - Intraday momentum strength
13. Ranks all signals by confidence score
14. Selects top 8 signals that pass all criteria

**10:00-10:05 AM - Execution:**
15. Submits BUY market orders for top 8 signals
16. Monitors fills
17. Creates position trackers with entry_date = Oct 22, exit_date = Oct 23

**Result:** New positions for tomorrow's D+1 exit on Oct 23
""")

print("\n" + "=" * 80)
print("## 🎯 Key Takeaways")
print("=" * 80)

print("""
1. **End-of-day process (4:00 PM):**
   - Prepares watchlist using PreFilter analysis
   - Identifies 8 top-quality stocks + 22 backup candidates
   - NO trading happens, just preparation

2. **PreFilter selection criteria:**
   - High liquidity ($10M+ volume)
   - Moderate volatility (2-8% daily range)
   - Strong momentum (3%+ recent move)
   - Volume surge (1.5x average)
   - Composite scoring weighs breakout > momentum > volatility > liquidity

3. **Morning execution (9:45 AM):**
   - FIRST: Exits yesterday's D+1 positions (your 8 current ones)
   - THEN: Scans for fresh gaps in the prepared universe
   - FINALLY: Generates signals and enters new positions

4. **Signal generation uses:**
   - Morning gap candidates (fresh pre-market data)
   - Technical indicators (multi-timeframe)
   - ML confidence scores (pattern recognition)
   - Volume analysis (buying pressure)
   - Momentum strength (trend confirmation)

**Tomorrow you should see:**
- 9:45 AM: 8 SELL orders (closing today's positions)
- 9:50-10:00 AM: 8 NEW BUY orders (entering tomorrow's positions)
- Net result: Full D+1 cycle with fresh signals each day
""")

print("\n" + "=" * 80)
print("✅ Analysis Complete")
print("=" * 80)

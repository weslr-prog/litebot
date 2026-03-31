# Enhanced Logging System Guide

## Overview

The bot now has a **rich, multi-channel logging system** designed for fast debugging when you get home from work. Instead of sending notifications, all critical information is captured in structured, searchable logs.

---

## Log Files Created

### 1. **trading_activity.log** - Human-Readable Timeline
**Purpose:** Quick overview of what happened today  
**Format:** Simple, clean, chronological timeline

```
[2025-12-17 10:01:23] [ENTRY] 📈 ENTRY: SOFI | $8.45 × 5 = $42.25 | Score: 0.85 | Mean Reversion
[2025-12-17 10:01:24] [ENTRY] 📈 ENTRY: UPST | $48.20 × 1 = $48.20 | Score: 0.82 | Gap & Go
[2025-12-17 14:32:15] [EXIT] 📉 EXIT: CNP | Entry: $37.48 → Exit: $38.20 | P&L: $0.72 (+1.92%) | WIN | Days: 5 | D+1 force exit
```

**Best for:** Quick scanning when you get home - "What did the bot do today?"

---

### 2. **debug_detailed.log** - Verbose Technical Details
**Purpose:** Deep technical debugging with full context  
**Format:** Timestamped with milliseconds + context data

```
[2025-12-17 10:01:23.456] PreFilter rejections: low_volume: 32, high_volatility: 15
    Context: {
      "total": 107,
      "passed": 52,
      "duration_ms": 8234
    }
```

**Best for:** Investigating why something didn't work as expected

---

### 3. **daily_summary_YYYYMMDD.json** - Structured Data
**Purpose:** Machine-readable summary for analysis/parsing  
**Format:** JSON with complete session data

```json
{
  "date": "2025-12-17",
  "start_time": "2025-12-17T07:00:00",
  "positions": {
    "entered": [
      {
        "symbol": "SOFI",
        "price": 8.45,
        "shares": 5,
        "value": 42.25,
        "signal_score": 0.85,
        "reason": "Mean Reversion"
      }
    ],
    "exited": [
      {
        "symbol": "CNP",
        "entry_price": 37.48,
        "exit_price": 38.20,
        "pnl": 0.72,
        "pnl_pct": 1.92,
        "result": "WIN",
        "days_held": 5,
        "reason": "D+1 force exit"
      }
    ]
  },
  "errors": [],
  "performance": {
    "prefilter_duration_ms": 8234,
    "signal_generation_ms": 1523
  },
  "daily_summary": {
    "entries": 2,
    "exits": 12,
    "wins": 8,
    "losses": 4,
    "win_rate": 66.7,
    "total_pnl": 25.48,
    "final_portfolio": 1002.67
  }
}
```

**Best for:** Analyzing patterns, exporting to Excel, building dashboards

---

### 4. **sprint1_alpaca.log** - Main Detailed Log (Existing)
**Purpose:** Complete detailed log with all bot activity  
**Format:** Standard Python logging format

**Best for:** Full context when debugging complex issues

---

## Quick Start: Viewing Logs

### Method 1: Interactive Log Viewer (Recommended)
```bash
./view_logs.sh
```

This gives you a menu:
```
1) Activity Timeline (human-readable)
2) Debug Details (verbose)
3) Daily Summary (JSON)
4) Main Log (sprint1_alpaca.log)
5) Errors Only
6) Entries & Exits Only
7) Position Status
8) Performance Metrics
9) Live Tail (follow logs)
10) Search Logs
```

### Method 2: Direct File Access
```bash
# Quick activity overview
cat logs/trading_activity.log

# Last 50 entries/exits
grep -E "ENTRY|EXIT" logs/trading_activity.log | tail -50

# All errors
grep -E "ERROR|WARNING" logs/trading_activity.log

# Today's summary
cat logs/daily_summary_$(date +%Y%m%d).json | python3 -m json.tool
```

### Method 3: Live Monitoring
```bash
# Follow main log
tail -f logs/sprint1_alpaca.log

# Follow activity log
tail -f logs/trading_activity.log

# Follow debug log
tail -f logs/debug_detailed.log
```

---

## What Gets Logged

### Session Events
- ✅ **Bot startup** - Portfolio value, positions loaded, buying power
- ✅ **Phase changes** - Premarket → Entry → Monitoring → Postmarket
- ✅ **Watchlist refresh** - How many stocks loaded
- ✅ **Session end** - Daily summary with win rate, P&L

### Position Lifecycle
- ✅ **Entry signal** - Symbol, price, shares, score, reason
- ✅ **Entry execution** - Confirmed order with actual price
- ✅ **Exit signal** - Why position should exit (D+1, stop loss, etc.)
- ✅ **Exit execution** - Confirmed sale with P&L calculation
- ✅ **Stuck positions** - Positions that failed to exit with reason

### Signal Generation
- ✅ **PreFilter results** - How many stocks passed, rejection reasons
- ✅ **Signal generation** - How many signals created, duration
- ✅ **Performance metrics** - Timing for each phase

### Errors & Warnings
- ✅ **Full error context** - Error type, message, traceback
- ✅ **Warning conditions** - No activity, stuck positions, low buying power
- ✅ **Failed operations** - Failed orders, API errors, data fetch failures

### Monitoring
- ✅ **Active position count** - How many positions being monitored
- ✅ **Exit checks** - When positions were checked for exit signals
- ✅ **Price fetch status** - Real-time vs fallback prices
- ✅ **Monitoring cycle performance** - Duration per cycle

---

## Common Debugging Scenarios

### Scenario 1: "Why didn't the bot trade today?"
```bash
./view_logs.sh
# Select: 1) Activity Timeline

# Look for:
- Did PreFilter pass any candidates? (Should be ~50 from 107 stocks)
- Did signal generation create any signals?
- Were there errors during entry scan?
- Was there sufficient buying power?
```

**What to check:**
```bash
grep "PreFilter" logs/trading_activity.log
grep "Generated.*signals" logs/trading_activity.log
grep "buying power\|insufficient" logs/sprint1_alpaca.log
```

---

### Scenario 2: "Why didn't positions exit?"
```bash
./view_logs.sh
# Select: 7) Position Status

# Look for:
- Are positions marked as "OVERDUE"?
- Check error log: 5) Errors Only
```

**What to check:**
```bash
# See if exit signals triggered
grep "Exit Signal\|should_exit" logs/sprint1_alpaca.log | tail -20

# See if orders failed
grep "execute_sell_order\|Order execution failed" logs/sprint1_alpaca.log | tail -20

# Check stuck positions
grep "STUCK POSITION" logs/trading_activity.log
```

---

### Scenario 3: "What was the P&L today?"
```bash
./view_logs.sh
# Select: 3) Daily Summary

# Or directly:
python3 << 'EOF'
import json
from pathlib import Path
import datetime as dt

summary_file = f"logs/daily_summary_{dt.date.today().strftime('%Y%m%d')}.json"
if Path(summary_file).exists():
    with open(summary_file) as f:
        data = json.load(f)
    
    summary = data.get('daily_summary', {})
    print(f"Entries: {summary.get('entries', 0)}")
    print(f"Exits: {summary.get('exits', 0)}")
    print(f"Win Rate: {summary.get('win_rate', 0):.1f}%")
    print(f"Total P&L: ${summary.get('total_pnl', 0):+.2f}")
    print(f"Portfolio: ${summary.get('final_portfolio', 0):.2f}")
else:
    print("No summary for today yet")
EOF
```

---

### Scenario 4: "Were there any errors?"
```bash
./view_logs.sh
# Select: 5) Errors Only

# Or search for specific error:
./view_logs.sh
# Select: 10) Search Logs
# Enter: "NoneType"
```

---

### Scenario 5: "How long did PreFilter take?"
```bash
./view_logs.sh
# Select: 8) Performance Metrics

# Or directly:
grep "PreFilter.*ms\|SIGNALS.*ms" logs/trading_activity.log
```

---

## Log Rotation

Logs are **not automatically rotated** to preserve history. To manually clean up:

```bash
# Archive old logs (keep last 30 days)
cd logs
mkdir -p archive
find . -name "*.log" -mtime +30 -exec mv {} archive/ \;

# Compress archived logs
tar -czf archive/logs_$(date +%Y%m%d).tar.gz archive/*.log
rm archive/*.log
```

---

## Analyzing Logs When You Get Home

### 5-Minute Quick Check
```bash
cd /home/wes/Desktop/litebotx-usb-deployment

# 1. Check if bot is still running
pgrep -f "python3 bot_v2/launcher.py"

# 2. Quick activity summary
./view_logs.sh
# Select: 1) Activity Timeline
# Scroll to see entries/exits

# 3. Check for errors
./view_logs.sh
# Select: 5) Errors Only

# 4. Position status
./view_logs.sh
# Select: 7) Position Status

# Done! You now know:
# - What traded today
# - If there were any errors
# - Current position status
```

### 15-Minute Deep Dive
If something looks wrong:

```bash
# 1. View daily summary
./view_logs.sh
# Select: 3) Daily Summary
# This shows structured data with all metrics

# 2. Check debug log for context
./view_logs.sh
# Select: 2) Debug Details
# Look for the specific time when issue occurred

# 3. Search for specific symbols or errors
./view_logs.sh
# Select: 10) Search Logs
# Enter symbol name or error message

# 4. Compare with positions.json
python3 << 'EOF'
import json
with open('positions.json') as f:
    positions = json.load(f)
    
for p in positions:
    if p['status'] == 'entered':
        print(f"{p['symbol']}: entry={p['entry_date']}, exit={p['exit_date']}, price=${p['entry_price']}")
EOF
```

---

## Advanced: Parsing Logs Programmatically

### Extract All Exits
```python
import json
from pathlib import Path

summary_file = f"logs/daily_summary_{date}.json"
with open(summary_file) as f:
    data = json.load(f)

exits = data['positions']['exited']
for exit in exits:
    print(f"{exit['symbol']}: ${exit['pnl']:+.2f} ({exit['pnl_pct']:+.2f}%) - {exit['result']}")
```

### Calculate Win Rate Over Last Week
```python
from pathlib import Path
import json
import datetime as dt

wins = 0
losses = 0

for i in range(7):
    date = (dt.date.today() - dt.timedelta(days=i)).strftime('%Y%m%d')
    summary_file = f"logs/daily_summary_{date}.json"
    
    if Path(summary_file).exists():
        with open(summary_file) as f:
            data = json.load(f)
            summary = data.get('daily_summary', {})
            wins += summary.get('wins', 0)
            losses += summary.get('losses', 0)

total = wins + losses
win_rate = (wins / total * 100) if total > 0 else 0
print(f"7-Day Win Rate: {win_rate:.1f}% ({wins}W / {losses}L)")
```

---

## Benefits of This System

### 1. **Comprehensive Context**
Unlike notifications that only tell you "something went wrong", logs show:
- What led up to the issue
- Full stack traces for errors
- Performance metrics (timing)
- All data values at time of error

### 2. **Searchable History**
- Search across all logs: `grep "SOFI" logs/*.log`
- Find patterns: `grep "insufficient buying power" logs/*.log | wc -l`
- Track specific positions through their lifecycle

### 3. **No Message Spam**
- No 50 notifications to wade through
- All data in one place, organized by type
- View only what you need when you need it

### 4. **Fast Debugging**
With the log viewer (`./view_logs.sh`), you can:
- Get daily overview in 30 seconds
- Find errors in 1 minute
- Deep dive into specific issues in 5 minutes

### 5. **Audit Trail**
- Every trade decision is logged with reasoning
- Full position lifecycle tracked
- Can reconstruct exactly what happened and why

---

## Summary

**Instead of notifications that interrupt you at work**, this system gives you a **comprehensive, structured record** that makes debugging **fast and efficient** when you get home.

**5 seconds:** Is bot running? `pgrep -f launcher.py`  
**30 seconds:** What happened today? `./view_logs.sh` → Option 1  
**2 minutes:** Were there errors? `./view_logs.sh` → Option 5  
**5 minutes:** Full daily analysis: `./view_logs.sh` → Option 3  

All the information you need, **organized for fast access**, without cluttering your phone with notifications you can't act on while at work.

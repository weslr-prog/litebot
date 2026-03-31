# Bot Overnight Startup - December 16-17, 2025

## What Was Done

### 1. ✅ Modified Startup Script
- Changed `start_bot_dec17.sh` to run in **background mode**
- Bot will run overnight and through tomorrow's trading day
- Logs to timestamped file: `logs/bot_overnight_YYYYMMDD_HHMMSS.log`
- Saves PID to `logs/bot.pid` for easy monitoring

### 2. ✅ Implemented Enhanced Logging System
Created multi-channel logging for fast debugging:

#### Log Files:
- **trading_activity.log** - Human-readable timeline (entries, exits, phase changes)
- **debug_detailed.log** - Verbose technical details with full context
- **daily_summary_YYYYMMDD.json** - Structured JSON for analysis
- **sprint1_alpaca.log** - Main detailed log (existing)

#### What Gets Logged:
- ✅ Session start (portfolio, positions, buying power)
- ✅ Position entries (symbol, price, shares, signal score, reason)
- ✅ Position exits (entry/exit prices, P&L, win/loss, days held, reason)
- ✅ Stuck positions (overdue exits with context)
- ✅ PreFilter results (candidates, rejections, duration)
- ✅ Signal generation (timing, candidates in/out)
- ✅ Phase changes (premarket → entry → monitoring → postmarket)
- ✅ Errors with full context and tracebacks
- ✅ Performance metrics (timing for each operation)
- ✅ Daily summary (entries, exits, win rate, P&L)

### 3. ✅ Created Log Viewer Tool
Interactive menu-driven log viewer: `./view_logs.sh`

**Options:**
1. Activity Timeline - Quick overview
2. Debug Details - Verbose technical info
3. Daily Summary - Structured JSON data
4. Main Log - Full detailed log
5. Errors Only - All errors across logs
6. Entries & Exits Only - Trading activity
7. Position Status - Current positions
8. Performance Metrics - Timing data
9. Live Tail - Follow logs in real-time
10. Search Logs - Find specific terms

### 4. ✅ Updated Monitor Script
Enhanced `monitor_bot.sh`:
- Shows bot PID and running status
- Displays active positions with status
- Shows recent log activity
- Color-coded output for quick scanning

---

## How to Start Tonight

### Option 1: Start Now (Recommended)
```bash
cd /home/wes/Desktop/litebotx-usb-deployment
./start_bot_dec17.sh
```

**What happens:**
1. Bot starts in background
2. Logs to `logs/bot_overnight_20251216_HHMMSS.log`
3. PID saved to `logs/bot.pid`
4. Bot will run overnight (closed mode, checking every 10 minutes)
5. At 7:00 AM: Enters premarket mode
6. At 10:00 AM: 12 positions will trigger D+1 exits
7. Bot continues trading throughout the day

### Option 2: Manual Start
```bash
cd /home/wes/Desktop/litebotx-usb-deployment
source litebotx_env/bin/activate
nohup python3 bot_v2/launcher.py > logs/bot_overnight.log 2>&1 &
echo $! > logs/bot.pid
```

---

## What to Expect Tomorrow (Dec 17)

### Timeline:
- **7:00 AM** - Premarket scan, portfolio summary
- **9:45 AM** - Entry window opens, scans 107 stocks
- **10:00 AM** - Monitoring begins
- **10:01 AM** - **All 12 positions trigger D+1 exit signals** ⚠️
- **10:02-10:15 AM** - Execute 12 sell orders (~$483 freed up)
- **Throughout day** - Monitor for new entries
- **11 AM, 12 PM, 1 PM** - Midday refresh windows (if no entries yet)
- **3:45 PM** - Force exit window (safety net)
- **4:00 PM** - Postmarket, watchlist refresh

### Expected Results:
- ✅ 12 positions will exit (4-5 days overdue)
- ✅ $483.13 buying power freed up
- ✅ 9-10 new entries possible ($50 each)
- ✅ All activity logged to multiple log files

---

## Checking Status While at Work

### Quick Health Check (30 seconds):
```bash
# SSH into your machine, then:
cd /home/wes/Desktop/litebotx-usb-deployment
./monitor_bot.sh
```

Shows:
- Bot running status
- Active positions
- Recent activity

### View Logs Remotely (2 minutes):
```bash
./view_logs.sh
# Select: 1) Activity Timeline
# Scroll to see what happened
```

### Check If Exits Happened:
```bash
grep "EXIT.*D+1" logs/trading_activity.log
# Should see 12 lines around 10:00-10:15 AM
```

---

## When You Get Home

### 5-Minute Quick Check:
```bash
cd /home/wes/Desktop/litebotx-usb-deployment

# 1. Is bot running?
pgrep -f "python3 bot_v2/launcher.py"

# 2. What happened today?
./view_logs.sh
# Select: 1) Activity Timeline

# 3. Any errors?
./view_logs.sh
# Select: 5) Errors Only

# 4. Position status
./view_logs.sh
# Select: 7) Position Status
```

### Full Analysis (15 minutes):
```bash
# Daily summary with all metrics
./view_logs.sh
# Select: 3) Daily Summary

# Entries/Exits breakdown
./view_logs.sh
# Select: 6) Entries & Exits Only

# Search for specific symbols
./view_logs.sh
# Select: 10) Search Logs
# Enter: "CNP" (or any symbol)
```

---

## Troubleshooting

### If bot stopped overnight:
```bash
# Check last few lines of log
tail -50 logs/bot_overnight_*.log

# Restart
./start_bot_dec17.sh
```

### If positions didn't exit:
```bash
# Check for exit signals
grep "Exit Signal\|should_exit" logs/sprint1_alpaca.log | grep -A2 "10:0[0-9]:"

# Check for order failures
grep "execute_sell_order" logs/sprint1_alpaca.log | tail -20

# View stuck positions
./view_logs.sh
# Select: 7) Position Status
```

### If bot encountered errors:
```bash
# All errors with context
./view_logs.sh
# Select: 5) Errors Only

# Search for specific error
grep -A5 -B5 "ERROR" logs/trading_activity.log | tail -30
```

---

## Stopping the Bot

```bash
# Method 1: Kill by PID
cat logs/bot.pid | xargs kill

# Method 2: Kill by process name
pkill -f "python3 bot_v2/launcher.py"

# Method 3: Force kill if unresponsive
pkill -9 -f "python3 bot_v2/launcher.py"
```

---

## Benefits Over Notification System

### Why Logging > Notifications:

1. **Can't act on notifications at work anyway**
   - Notifications just create anxiety
   - Can't SSH in to fix issues during work
   - Better to have complete record when you get home

2. **Comprehensive context**
   - Notifications: "Error occurred"
   - Logs: Full error message, stack trace, context, what led to it

3. **Fast debugging**
   - With `./view_logs.sh`: Find any issue in 1-5 minutes
   - Structured logs make patterns obvious
   - Can search/filter/analyze

4. **Audit trail**
   - Complete record of every decision
   - Can reconstruct exactly what happened
   - JSON summary for programmatic analysis

5. **No spam**
   - 50+ notifications = overwhelming
   - Organized log files = scan what you need

---

## Summary

**Bot is ready to run overnight and trade tomorrow autonomously.**

### Start Command:
```bash
./start_bot_dec17.sh
```

### Check Status:
```bash
./monitor_bot.sh
```

### View Logs:
```bash
./view_logs.sh
```

### Expected Tomorrow:
- ✅ 12 exits around 10 AM
- ✅ $483 freed up
- ✅ 9-10 new entries possible
- ✅ All activity comprehensively logged

### When You Get Home:
- 5 minutes to understand what happened
- Structured logs for fast debugging
- No notification spam to wade through

**See LOGGING_SYSTEM_GUIDE.md for complete logging documentation.**

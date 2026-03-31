# How to Run LiteBotX V2 - Quick Reference

## ✅ Fixed Issues (December 11, 2025)

### 1. Removed Launcher-Level PDT Check
**Problem**: Launcher was checking PDT before knowing if trade was intraday or D+1  
**Fix**: Removed PDT check from launcher - order_manager handles it correctly  
**Result**: D+1 trades (your strategy) will NOT be blocked by PDT

### 2. Suppressed yfinance Error Spam
**Problem**: Hundreds of "possibly delisted" warnings flooding logs  
**Fix**: Added `logging.getLogger('yfinance').setLevel(logging.CRITICAL)`  
**Result**: Clean logs, no more error spam

---

## 🚀 Starting the Bot (FOREGROUND MODE)

### Option 1: Use the Startup Script (RECOMMENDED)

```bash
cd /home/wes/Desktop/litebotx-usb-deployment
./start_bot_foreground.sh
```

**What it does:**
- ✅ Loads environment variables from .env
- ✅ Checks for existing bot processes and stops them
- ✅ Starts bot in foreground (you see all output)
- ✅ Saves logs to both terminal AND logs/sprint1_alpaca.log
- ✅ Press Ctrl+C to stop cleanly

---

### Option 2: Manual Start (Alternative)

```bash
cd /home/wes/Desktop/litebotx-usb-deployment
export $(grep -v '^#' .env | xargs)
source litebotx_env/bin/activate
python3 -m bot_v2.launcher
```

**Press Ctrl+C to stop**

---

## 🛑 Stopping the Bot

### If Running in Foreground:
**Just press Ctrl+C** - it will stop gracefully

### If Running in Background (should not happen now):
```bash
pkill -f "bot_v2.launcher"
```

---

## 📊 Monitoring

### Watch Live Output:
The bot outputs to your terminal in real-time

### Check Logs Later:
```bash
tail -50 logs/sprint1_alpaca.log
```

### Check Bot Status:
```bash
ps aux | grep "bot_v2.launcher" | grep -v grep
```

### Check PDT Status:
```bash
cat data/day_trades.json
# Should show: {"trades": []}
```

### Check Positions:
```bash
cat positions.json
# Should show: [] when no positions
```

---

## 🔍 What You'll See

### During Entry Window (9:45-10:00 AM):
```
🎯 ENTRY SCAN (9:45-10:00 AM)
📊 PreFilter: X candidates from 262 stocks
✅ Generated Y entry signals
✅ Entry executed: SYMBOL @ $XX.XX
```

### During Monitoring (10:00 AM - 3:45 PM):
```
⏰ Monitoring Exits - Next check in 1.0 minutes
```

### During Exit Window (3:45-4:00 PM):
```
🔄 Checking exits for D+1 positions...
✅ Exit executed: SYMBOL @ $XX.XX (P&L: +$X.XX)
```

---

## ⚠️ Important Notes

### PDT Status:
- **D+1 trades are NOT day trades** (you buy today, sell tomorrow)
- PDT tracker should stay at 0 trades used
- You can make **unlimited D+1 trades** without PDT limits
- Only same-day round trips count as day trades

### 0 Candidates Days:
- If PreFilter returns 0 candidates, **this is normal**
- Means no stocks meet all criteria (oversold + uptrend + volume)
- Bot is protecting capital by waiting for quality setups
- **This is good behavior**, not an error

### yfinance Errors:
- Now suppressed at logging level
- Don't affect bot operation
- If you see any, they're harmless

---

## 📁 Key Files

| File | Purpose | Expected State |
|------|---------|----------------|
| `positions.json` | Active positions | `[]` when no positions |
| `data/day_trades.json` | PDT tracking | `{"trades": []}` for D+1 strategy |
| `logs/sprint1_alpaca.log` | Detailed logs | Growing file with all activity |
| `.env` | API credentials | Contains APCA_API_KEY_ID, etc. |

---

## 🐛 Troubleshooting

### Bot Won't Start:
```bash
# Check Python environment
source litebotx_env/bin/activate
python3 --version  # Should be 3.11+

# Check dependencies
pip list | grep alpaca

# Try manual start to see errors
python3 -m bot_v2.launcher
```

### No Trades Executing:
```bash
# Check if scans ran
grep "ENTRY SCAN" logs/sprint1_alpaca.log | tail -5

# Check signal count
grep "Generated.*signals" logs/sprint1_alpaca.log | tail -5

# Check PDT (should be 0)
cat data/day_trades.json
```

### Duplicate Processes:
```bash
# Kill all
pkill -f "bot_v2.launcher"

# Restart cleanly
./start_bot_foreground.sh
```

---

## 📈 Expected Behavior Today (Dec 11)

- ✅ Bot running in foreground (you see output)
- ✅ Entry scans at 9:45, 9:50, 9:55, 10:00 AM
- ✅ 0-3 trades executed (if setups found)
- ✅ No PDT blocking
- ✅ Clean logs (no yfinance spam)
- ✅ Positions saved to positions.json
- ✅ Exits at 3:45 PM tomorrow (D+1)

---

**Generated**: December 11, 2025  
**Next Review**: After first successful trade cycle

# 🚀 QUICK START GUIDE - Intraday Analysis

**Date**: October 15, 2025  
**Status**: ✅ READY FOR PAPER TRADING

---

## ⚡ Daily Workflow (Copy This!)

### **Morning (Before 9:30 AM ET)**
```bash
cd /home/wes/Desktop/litebotx-usb-deployment
python3 litebotx_launcher.py
# Select option 3 (Aggressive Trading)
# Confirm "yes" to start
# Walk away - bot runs automatically
```

### **Evening (After 4:00 PM ET)**
```bash
# Check today's performance
python3 analyze_d1_performance.py

# Review logs
tail -100 unified_trading.log | grep "intraday"

# Check API usage
grep "API usage" unified_trading.log | tail -1
```

---

## 🎯 What the Bot Does (Automatically)

1. **9:30 AM**: Market opens
   - PreFilter scans 30+ candidates
   - Fetches 5-min intraday data
   - Analyzes opening range (9:30-10:00 AM)
   - Scores momentum + volume surge
   - Enhances top candidates

2. **Throughout Day**:
   - Executes trades on BUY signals
   - Skips low-quality SKIP signals
   - Manages positions
   - Applies D+1 exits

3. **4:00 PM**: Market closes
   - Finalizes positions
   - Saves results to positions.json
   - Ready for next day

---

## 📊 Key Metrics to Watch

### **Daily Checks**
```bash
# 1. API usage (should be < 500/day)
grep "API usage" unified_trading.log | tail -5

# 2. Intraday enhancements (should see ~10-50/day)
grep "Intraday analysis applied" unified_trading.log | wc -l

# 3. Score adjustments
grep "Score adjusted" unified_trading.log | tail -10
```

### **Weekly Checks**
- Win rate vs baseline (target: 62-65% vs 57.1%)
- Average profit per trade
- API usage trend
- Number of SKIP vs BUY recommendations

---

## 🛡️ Safety Limits (Already Configured)

✅ Max 50 intraday analyses per day  
✅ Max 1000 API calls per day  
✅ Rate limiter: 0.3s between calls  
✅ Graceful fallback if intraday fails  
✅ No intraday during simulation/testing  

---

## 🔧 Quick Config Changes

### **Disable Intraday** (if needed)
Edit: `core/config.py`
```python
# Line 48
enable_intraday_analysis: bool = False  # Change True to False
```

### **Reduce API Usage**
Edit: `core/config.py`
```python
# Line 49
max_intraday_analyses_per_day: int = 20  # Change 50 to 20
```

### **Re-enable After Changes**
```bash
# Just restart the launcher
python3 litebotx_launcher.py
```

---

## 📝 Log Messages (What to Expect)

### **Good Signs** ✅
```
INFO: 📊 Intraday analysis enabled (max 50 analyses/day)
INFO: ✅ IntradayAnalyzer initialized with Alpaca free tier
INFO: ✅ Intraday analysis applied to PreFilter results
INFO: 🎯 Score adjusted: AAPL +25% (strong BUY signal)
INFO: 📊 API usage: 23/1000 calls, 12/50 analyses today
```

### **Normal Warnings** ⚠️
```
WARNING: ⚠️ Intraday data not available for XYZ (outside market hours)
WARNING: ⚠️ Hit daily analysis limit (50/50), using original scores
```

### **Problems** ❌
```
ERROR: ❌ Alpaca API connection failed
ERROR: ❌ Rate limit exceeded (1000+ calls)
```

---

## 🐛 Quick Fixes

### **Problem: No intraday activity in logs**
**Check**: Are you running during market hours (9:30 AM - 4:00 PM ET)?  
**Fix**: Wait for market hours or check next trading day

### **Problem: API rate limit errors**
**Check**: `grep "API usage" unified_trading.log | tail -1`  
**Fix**: Reduce `max_intraday_analyses_per_day` to 20 in config

### **Problem: Bot not starting**
**Check**: `python3 test_intraday_integration_full.py`  
**Fix**: If tests fail, review error messages

---

## 📞 Emergency Disable

If something goes wrong and you need to **immediately disable** intraday:

```bash
# Option 1: Edit config
nano core/config.py
# Change line 48: enable_intraday_analysis: bool = False
# Save (Ctrl+O, Enter, Ctrl+X)

# Option 2: Use conservative/balanced mode instead
python3 litebotx_launcher.py
# Select option 1 or 2 (no intraday)
```

---

## ✅ Pre-Flight Checklist

Before starting each day:

- [ ] Alpaca API credentials valid?
- [ ] Internet connection stable?
- [ ] Sufficient disk space for logs?
- [ ] Bot launcher script working?
- [ ] Previous day's positions reviewed?

---

## 📊 Expected Results (Week 1)

### **Baseline (No Intraday)**
- Win Rate: 57.1%
- Profit: ~$267/day

### **Target (With Intraday)**
- Win Rate: 62-65%
- Profit: ~$300-350/day
- Improvement: +5-10%

### **Validation Period**
- **Oct 16-20**: Monitor and validate
- **Oct 21**: Decide to keep/adjust/disable
- **Oct 22+**: Continue if successful

---

## 🎯 Success Criteria

After 1 week, intraday analysis is successful if:

✅ Win rate improved by ≥5%  
✅ No API errors or crashes  
✅ API usage stayed under 500 calls/day  
✅ Trades with BUY signals outperform SKIP signals  

If all criteria met → **KEEP IT RUNNING**  
If not → Review and adjust or disable

---

**Last Updated**: October 15, 2025  
**Status**: ✅ ALL SYSTEMS GO  
**Your Action**: Run launcher tomorrow morning before market open

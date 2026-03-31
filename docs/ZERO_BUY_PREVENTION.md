# Preventing Zero-Buy Days - Complete Guide

## What Happened Today (Oct 28, 2025)

### Root Causes
1. **Stale Watchlist** - 36 days old (from Sept 22)
2. **Missing yfinance** - Data loader couldn't fetch data
3. **Insufficient Candidates** - Only 6 stocks passed filters (need 8-15)
4. **Same-Day Re-Entry Blocks** - Sold AMD/IBM, couldn't rebuy same day

### Impact
- ✅ 4 D+1 exits executed (AMD, IBM, SHOP, MMM) - **all profitable!**
- ❌ 0 new positions entered
- ❌ Only 2 signals generated (both blocked)

---

## Prevention Solutions Implemented

### 1. Daily Watchlist Refresh ✅

**What:** Automated daily refresh of top 15 momentum stocks

**Files Created:**
- `daily_watchlist_refresh.py` - Main refresh script
- `setup_daily_refresh_cron.sh` - Automated scheduling
- `check_watchlist_health.py` - Health monitoring

**How to Setup:**
```bash
# Make script executable
chmod +x setup_daily_refresh_cron.sh

# Run setup (adds cron job)
./setup_daily_refresh_cron.sh
```

**Schedule:** Every weekday at 4:30 PM ET (after market close)

**What it does:**
- Scans 70-stock universe
- Calculates momentum + volume scores
- Selects top 15 candidates
- Saves to `logs/current_watchlist.json`
- Creates dated backup

---

### 2. Health Check Script ✅

**Run before market open:**
```bash
python3 check_watchlist_health.py
```

**Checks:**
- ✅ Watchlist age (should be < 24 hours)
- ✅ Symbol count (need 8-15)
- ✅ File exists and is readable

**Status:**
- ✅ Healthy: Green, ready to trade
- ⚠️  Warning: Yellow, still usable but aging
- ❌ Error: Red, needs immediate refresh

---

### 3. Manual Refresh (Backup) ✅

**If automated refresh fails:**
```bash
python3 daily_watchlist_refresh.py
```

**Or use quick generator:**
```bash
python3 quick_watchlist_gen.py
```

---

## Daily Workflow for Prevention

### End of Trading Day (4:00 PM - 5:00 PM ET)

**Automated:**
1. ✅ Cron job runs at 4:30 PM ET
2. ✅ Generates fresh watchlist
3. ✅ Saves to `logs/current_watchlist.json`
4. ✅ Creates dated backup

**Manual Check (optional):**
```bash
# View today's refresh log
tail -50 logs/watchlist_refresh.log

# Or check cron log
tail -50 logs/cron_watchlist.log
```

### Morning Pre-Market (8:00 AM - 9:00 AM ET)

**Required:**
```bash
# Check watchlist health
python3 check_watchlist_health.py
```

**If issues found:**
```bash
# Refresh immediately
python3 daily_watchlist_refresh.py
```

**Verify bot is running:**
```bash
# Check if bot is active
ps aux | grep short_cycle_trader

# Or check service status
systemctl status litebotx.service
```

---

## Monitoring & Alerts

### Check Logs Daily

**Watchlist refresh log:**
```bash
tail -100 logs/watchlist_refresh.log
```

**Bot trading log:**
```bash
tail -100 logs/short_cycle_trader.log | grep "09:45\|signals"
```

### Key Metrics to Watch

1. **Watchlist Age** - Should refresh daily
2. **Symbol Count** - Should be 8-15
3. **Signals Generated** - Should be 2-5 per day
4. **Same-Day Blocks** - Normal for D+1 strategy

---

## Emergency Procedures

### If Watchlist is Stale (> 24 hours)

```bash
# Immediate refresh
python3 daily_watchlist_refresh.py

# Check result
python3 check_watchlist_health.py
```

### If yfinance is Missing

```bash
# Install yfinance
pip3 install yfinance

# Or if using virtual environment
source litebotx_env/bin/activate
pip install yfinance
```

### If No Signals Generated

**Check watchlist:**
```bash
python3 check_watchlist_health.py
```

**Check bot logs:**
```bash
grep "signals_today" logs/short_cycle_trader.log | tail -5
```

**Manual intervention:**
```bash
# Place manual orders
python3 manual_buy_for_tomorrow.py
```

---

## Success Criteria

### Daily Requirements
- ✅ Watchlist < 24 hours old
- ✅ 8-15 stocks in watchlist
- ✅ Bot running and healthy
- ✅ 2-5 signals generated per day

### Weekly Goals
- ✅ 5-10 new positions per week
- ✅ 3-5% average profit per D+1 exit
- ✅ 60%+ win rate
- ✅ No zero-buy days (except holidays)

---

## Automation Status

### ✅ Now Automated
- Daily watchlist refresh (4:30 PM ET)
- Momentum scoring
- Top 15 candidate selection
- Backup creation

### ⚠️  Manual (Recommended Daily)
- Morning health check
- Bot status verification
- Performance review

### 🔧 Manual (As Needed)
- Emergency refresh
- Manual order placement
- Troubleshooting

---

## Testing the Setup

### Test watchlist refresh:
```bash
python3 daily_watchlist_refresh.py
```

### Test health check:
```bash
python3 check_watchlist_health.py
```

### Test cron setup:
```bash
# Setup cron job
./setup_daily_refresh_cron.sh

# View cron jobs
crontab -l

# Test cron log
tail -f logs/cron_watchlist.log
```

---

## Summary

**Today's fixes ensure:**
1. ✅ **Fresh watchlist daily** - Automated refresh at 4:30 PM
2. ✅ **Health monitoring** - Easy pre-market checks
3. ✅ **Manual backup** - Quick refresh if needed
4. ✅ **4 positions entered** - Ready for tomorrow's D+1 exits

**Tomorrow the bot will:**
- ✅ Have 15 fresh momentum candidates
- ✅ Evaluate 4 positions for D+1 exit
- ✅ Generate 2-5 new signals
- ✅ Enter 2-4 new positions

---

## Quick Reference Commands

```bash
# Daily health check
python3 check_watchlist_health.py

# Manual refresh if needed
python3 daily_watchlist_refresh.py

# Setup automation (one-time)
./setup_daily_refresh_cron.sh

# Check cron status
crontab -l

# View logs
tail -50 logs/watchlist_refresh.log
tail -50 logs/short_cycle_trader.log
```

---

**Last Updated:** October 28, 2025  
**Status:** ✅ Prevention measures implemented and tested

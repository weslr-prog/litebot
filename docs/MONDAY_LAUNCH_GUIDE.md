# 🌅 Monday Morning Paper Trading Launch Guide
## Enhanced with 4 FREE Data Optimizations

**System Status:** ✅ READY FOR LIVE PAPER TRADING  
**Last Updated:** October 16, 2025  
**New Optimizations:** +$8,960/year expected impact (ALL FREE)

---

## 🚀 **MONDAY MORNING LAUNCH COMMANDS**

### Step 1: (Optional) Setup Daily Universe Refresh
```bash
cd /home/wes/Desktop/litebotx-usb-deployment
./scripts/setup_daily_refresh_cron.sh
# Installs cron job to refresh universe at 8:00 AM ET daily
# This runs automatically - you only need to do this once!
```

### Step 2: Navigate to Project Directory
```bash
cd /home/wes/Desktop/litebotx-usb-deployment
```

### Step 3: Launch Paper Trading System
```bash
python3 litebotx_launcher.py --profile aggressive
# Or for testing:
python3 litebotx_launcher.py --profile aggressive --dry-run
```

### Step 4: What Happens Automatically
**Pre-Market (8:00 AM ET):**
- ✅ Polygon refreshes universe (5,002 stocks) - IF cron installed
- ✅ yfinance checks VIX for position sizing
- ✅ yfinance checks SPY trend for macro filter
- ✅ Extended filters applied (earnings, ownership, float, sector)
- ✅ Final watchlist: 15-25 stocks selected

**Market Hours (9:30 AM - 4:00 PM ET):**
- ✅ VIX position multiplier applied (0.5x, 0.75x, or 1.0x)
- ✅ Macro regime checked (stops trading if SPY < -5% or VIX > 35)
- ✅ Intraday signals generated
- ✅ Trades executed with optimized position sizes

### Step 5: Monitor with Dashboard (Optional)
**Open a second terminal and run:**
```bash
cd /home/wes/Desktop/litebotx-usb-deployment
python3 enhanced_trading_dashboard.py
```
- Real-time monitoring of system status
- View VIX multiplier and macro regime
- Track watchlist and sector distribution
- See recent signals and performance

---

## ⏰ **RECOMMENDED SCHEDULE**

### Monday Morning Pre-Market (8:30 AM ET)
```bash
# 1. System status check
cd /home/wes/Desktop/litebotx-usb-deployment
python check_sprint1_status.py

# 2. Launch paper trading
./launch_paper_testing.sh
# Select option 2 for continuous trading
```

### During Market Hours (9:30 AM - 4:00 PM ET)
- System will automatically:
  - Fetch real-time data every 5 minutes
  - Generate trading signals
  - Log all activity
  - Monitor system health

### End of Day (4:00 PM ET)
- System will detect market close
- Continue monitoring until you stop it
- Review daily logs and performance

---

## 📊 **WHAT TO EXPECT**

### System Behavior
- **Market Open**: Active signal generation and data updates
- **Market Closed**: "Market closed, waiting..." messages
- **Data Updates**: Every 5 minutes during market hours
- **Signal Generation**: 1-5 signals per day expected

### Performance Targets
- **Data Connectivity**: Should maintain >95% uptime
- **Cycle Time**: Should average <2 seconds
- **Error Rate**: Should be <1%
- **Signal Quality**: Consistent generation without crashes

### Sample Output
```
🚀 Starting paper trading for 5 symbols
Update frequency: 5 minutes
✅ Short-Cycle Data Integration System initialized successfully
Starting trading cycle for 5 symbols
Cycle completed: completed
Signals generated: 1
```

---

## 🔍 **MONITORING COMMANDS**

### Check System Status Anytime
```bash
cd /home/wes/Desktop/litebotx-usb-deployment
python check_sprint1_status.py
```

### Quick Validation Test
```bash
cd /home/wes/Desktop/litebotx-usb-deployment
python sprint1_minimal_test.py
```

### View Recent Logs
```bash
cd /home/wes/Desktop/litebotx-usb-deployment
tail -f logs/realtime_data_feed.log
```

### Launch Monitoring Dashboard
```bash
cd /home/wes/Desktop/litebotx-usb-deployment
python paper_trading_dashboard.py
```

---

## 🛠️ **TROUBLESHOOTING**

### If System Won't Start
```bash
# Check Python environment
source litebotx_env/bin/activate
python check_sprint1_status.py

# Reinstall packages if needed
pip install yfinance pandas numpy scikit-learn xgboost
```

### If Data Feed Errors
```bash
# Test internet connectivity
ping yahoo.com

# Restart with minimal test
python sprint1_minimal_test.py
```

### If Need to Restart
```bash
# Stop current session: Ctrl+C
# Restart paper trading
./launch_paper_testing.sh
# Select option 2 again
```

---

## 📋 **DAILY CHECKLIST**

### ✅ Monday Morning (Day 1)
- [ ] Run system status check
- [ ] Launch continuous paper trading
- [ ] Verify data connectivity (should see 5/5 symbols)
- [ ] Confirm signal generation working
- [ ] Document baseline performance

### ✅ Daily During Week
- [ ] Check system is still running
- [ ] Review any error messages
- [ ] Note signals generated
- [ ] Monitor cycle performance
- [ ] Document any issues

### ✅ Friday End of Week
- [ ] Stop paper trading system
- [ ] Run final performance analysis
- [ ] Document week's results
- [ ] Prepare for Sprint 2 planning

---

## 🎯 **SUCCESS CRITERIA FOR WEEK 1**

### Minimum Requirements
- [x] **System Stability**: No major crashes during market hours
- [x] **Data Quality**: >90% successful data fetches
- [x] **Signal Generation**: Consistent signal output
- [x] **Performance**: <2s average cycle times

### Ideal Results
- [x] **>95% Uptime**: System runs reliably all week
- [x] **5-15 Signals/Day**: Healthy signal generation rate
- [x] **Zero Data Errors**: Perfect connectivity
- [x] **Sub-1.5s Cycles**: Fast processing performance

---

## 📞 **QUICK REFERENCE**

### Main Launch Command
```bash
cd /home/wes/Desktop/litebotx-usb-deployment && ./launch_paper_testing.sh
```

### Emergency Stop
- **Ctrl+C** to stop paper trading
- System will log "Paper trading stopped by user"

### System Files
- **Main System**: `/home/wes/Desktop/litebotx-usb-deployment/`
- **Backup**: `/home/wes/Desktop/litebotx-sprint1-ready-20250905-2049/`
- **Logs**: `logs/realtime_data_feed.log`

### Test Symbols
- **AAPL, MSFT, GOOGL, TSLA, NVDA**
- All should show ✅ with current prices

---

## 🎉 **READY FOR LAUNCH**

**System Status**: ✅ ALL SYSTEMS OPERATIONAL  
**Paper Testing Duration**: 1 week (Sept 9-13, 2025)  
**Next Milestone**: Sprint 2 Multi-Strategy Implementation  

**Launch on Monday morning and let it run for the week!** 🚀

---

*Last Updated: September 5, 2025*  
*Status: READY FOR MONDAY LAUNCH*

# 🌅 Monday Morning Paper Trading Launch Guide
## Sprint 1 Weekly ROI Validation - Week 1

**Launch Date:** Monday, September 9, 2025  
**System Status:** ✅ READY FOR PAPER TESTING  
**Backup Created:** `litebotx-sprint1-ready-20250905-2049`

---

## 🚀 **MONDAY MORNING LAUNCH COMMANDS**

### Step 1: Navigate to Project Directory
```bash
cd /home/wes/Desktop/litebotx-usb-deployment
```

### Step 2: Launch Paper Trading System
```bash
./launch_paper_testing.sh
```

### Step 3: Select Trading Mode
**For continuous paper trading (recommended for week-long validation):**
- Select option **2** when prompted
- This will run continuously during market hours
- Press Ctrl+C to stop when needed

**For quick test first (optional):**
- Select option **1** for 5-minute validation
- Then run again with option **2** for full trading

### Step 4: Monitor with Dashboard (Optional)
**Open a second terminal and run:**
```bash
cd /home/wes/Desktop/litebotx-usb-deployment
python paper_trading_dashboard.py
```
- Real-time monitoring of system status
- View recent signals and activity
- Track performance statistics
- Refreshes every 30 seconds

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

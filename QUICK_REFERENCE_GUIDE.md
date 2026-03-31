# LiteBotX Quick Reference Guide
**Date:** November 14, 2025  
**For:** Daily Operation & Monitoring

---

## 🚀 QUICK START

### Daily Checklist (5 minutes)
```bash
# 1. Activate environment
cd /home/wes/Desktop/litebotx-usb-deployment
source litebotx_env/bin/activate

# 2. Check logs for overnight activity
tail -100 logs/trading_bot.log

# 3. Run bot (if not automated)
python3 start_litebotx.py

# 4. Monitor real-time (optional)
tail -f logs/trading_bot.log | grep "ENTRY SCREENING\|BLOCKING\|EARNINGS"
```

---

## 📊 KEY LOG MESSAGES TO WATCH

### Entry Quality Screening (NEW)
```
📊 ENTRY SCREENING: AAPL → 🟢 IDEAL: 7.0% momentum sweet spot, 1.60x volume
📊 ENTRY SCREENING: RIVN → 🔴 REJECT: Momentum too weak (3.7% < 4%)
```
**Action:** Count IDEAL vs REJECT daily, track which correlate with wins

### Earnings Protection (ACTIVE)
```
❌ TSLA: BLOCKED - Earnings in 2 days (2025-11-16)
⚠️ AAPL: EARNINGS EXIT - Earnings tomorrow (2025-11-15)
```
**Action:** None needed - bot handles automatically

### Risk Alerts
```
⚠️ Daily loss limit approaching: -$25 / $30
🚫 Weekly loss limit hit: -$100
⚠️ Gap detected: NCLH -3.2% pre-market
```
**Action:** Monitor for patterns, verify limits working

---

## 📈 PERFORMANCE TRACKING

### Daily Summary (End of Day)
```bash
# Extract today's performance
grep "$(date +%Y-%m-%d)" logs/trading_bot.log | grep "P&L\|ENTRY\|EXIT"

# Count screening results
grep "$(date +%Y-%m-%d)" logs/trading_bot.log | grep "ENTRY SCREENING" | sort | uniq -c
```

### Weekly Tracking Spreadsheet
| Date | P&L | Trades | Wins | Losses | Win Rate | Notes |
|------|-----|--------|------|--------|----------|-------|
| Nov 15 | TBD | 0 | 0 | 0 | - | First day with screener |
| Nov 18 | | | | | | |
| Nov 19 | | | | | | |
| Nov 20 | | | | | | |
| Nov 21 | | | | | | |
| Nov 22 | | | | | | |
| **WEEK** | | | | | | |

---

## 🎯 CURRENT CONFIGURATION

### Entry Criteria (VALIDATED)
- **Momentum:** 3.5% minimum (backtest-proven optimal)
- **Volume:** 0.8x minimum (no upper filter)
- **Price:** $10-$30 range
- **Liquidity:** 200K shares/day minimum

### Entry Quality Screening (OBSERVATION MODE)
- **IDEAL:** 6-9% momentum + 1.5-2.0x volume → 61% win rate expected
- **GOOD:** 6-9% momentum OR 1.25-2.0x volume → 51% win rate expected
- **ACCEPTABLE:** 4-6% momentum + moderate volume → 47% win rate
- **REJECT:** <4% or >10% momentum, or volume issues → 35% win rate
- **Mode:** Logging only (not blocking yet)

### Risk Limits (ACTIVE)
- Daily loss: $30 max (3% of $1K)
- Weekly loss: $100 max (10% of $1K)
- Position risk: 2% per trade
- Emergency stop: -4% on all positions

### Protections (ACTIVE)
- ✅ Earnings: 3-day blackout before earnings
- ✅ Weekend: No entries after Friday 1 PM
- ✅ Gaps: -3% gap → immediate exit
- ✅ PDT: No same-day round trips

---

## 🔧 TROUBLESHOOTING

### Issue: No entries happening
**Check:**
```bash
# 1. Daily/weekly limits not hit?
grep "loss limit" logs/trading_bot.log

# 2. Universe has signals?
grep "signals found" logs/trading_bot.log

# 3. Earnings blocking everything?
grep "BLOCKED - Earnings" logs/trading_bot.log
```

### Issue: Screener not logging
**Check:**
```bash
# 1. Is it initialized?
grep "Entry quality screener initialized" logs/trading_bot.log

# 2. Are signals being generated?
grep "AISignal" logs/trading_bot.log

# 3. Any errors?
grep "ERROR.*screen" logs/trading_bot.log
```

### Issue: Too many rejections
**Check thresholds:**
```python
# In entry_quality_screener.py
MOMENTUM_MIN = 0.04  # Lower to 0.035 if too strict
MOMENTUM_MAX = 0.10  # Raise to 0.12 if too strict
VOLUME_MIN = 1.25    # Lower to 1.0 if too strict
```

---

## 📁 FILE LOCATIONS

### Logs
```
logs/trading_bot.log          - Main log (check daily)
logs/dashboard.log             - Dashboard activity
```

### Configuration
```
small_portfolio_config.py      - Main config (3.5% momentum, etc.)
entry_quality_screener.py      - Screening thresholds
earnings_calendar.py           - Earnings protection
```

### Backups
```
/home/wes/Desktop/litebotx-backup-nov14-2025-screener-integrated.tar.gz
```

### Documentation
```
BOT_STATUS_REPORT_NOV14_2025.md    - Complete status
ROADMAP_NOV14_2025.md              - Development timeline
SCREENER_INTEGRATION_COMPLETE.md   - Screener details
```

---

## 🔔 ALERTS TO MONITOR

### Critical (Immediate Action)
- 🚨 Daily loss limit hit: Review what went wrong
- 🚨 Weekly loss limit hit: Stop trading, analyze
- 🚨 System crash: Check logs, restart

### Warning (Monitor Closely)
- ⚠️ Multiple REJECT entries in a day: Market conditions poor
- ⚠️ Gap >5%: Emergency exit triggered
- ⚠️ Earnings block: Verify calendar correct

### Info (Good to Know)
- ✅ IDEAL entry: High-quality setup
- ✅ Earnings protection: Disaster avoided
- ✅ Weekend exit: Risk management working

---

## 📞 EMERGENCY PROCEDURES

### Stop All Trading
```bash
# 1. Stop the bot
pkill -f start_litebotx.py

# 2. Close all positions manually (if needed)
python3 -c "from execution_engine import *; engine = RealPaperTradingEngine(); engine.close_all_positions()"

# 3. Review logs
tail -200 logs/trading_bot.log
```

### Restore from Backup
```bash
cd /home/wes/Desktop
tar -xzf litebotx-backup-nov14-2025-screener-integrated.tar.gz
cd litebotx-usb-deployment
source litebotx_env/bin/activate
```

### Contact Support
- Review: BOT_STATUS_REPORT_NOV14_2025.md
- Check: Recent log files
- Document: What happened, when, error messages

---

## 🎓 LEARNING RESOURCES

### Understanding Screening Results
```
🟢 IDEAL (6-9% momentum + 1.5-2x volume)
   → Historical win rate: 61%
   → Action: These should be winners
   → Track: Are they actually winning?

🟡 GOOD (6-9% momentum OR 1.25-2x volume)
   → Historical win rate: 51%
   → Action: Decent setups
   → Track: Performance vs IDEAL

🟠 ACCEPTABLE (4-6% momentum + moderate volume)
   → Historical win rate: 47%
   → Action: Marginal setups
   → Track: Worth keeping?

🔴 REJECT (<4% or >10% momentum, volume issues)
   → Historical win rate: 35%
   → Action: Should avoid
   → Track: Would blocking these help?
```

### Interpreting Performance
- **Win Rate 50%+:** On track (validated by backtest)
- **Win Rate 45-50%:** Acceptable (market dependent)
- **Win Rate <45%:** Review recent changes, check logs
- **P&L Positive:** Good regardless of win rate
- **P&L Negative:** Review risk management, check quality levels

---

## ✅ WEEKLY REVIEW CHECKLIST

### Friday End of Week (30 min)
- [ ] Calculate weekly P&L: `$_____`
- [ ] Count total trades: `___`
- [ ] Win rate: `___%`
- [ ] Screening distribution:
  - [ ] IDEAL: `___`
  - [ ] GOOD: `___`
  - [ ] ACCEPTABLE: `___`
  - [ ] REJECT: `___`
- [ ] Win rate by quality:
  - [ ] IDEAL wins: `___` / `___` = `___%`
  - [ ] REJECT wins: `___` / `___` = `___%`
- [ ] Any risk limit breaches? `Yes / No`
- [ ] Any earnings blocks? `___` stocks
- [ ] Any weekend exits? `Yes / No`
- [ ] Notes: `_____________________`

### Decision Points
- [ ] After 2 weeks (Nov 29): Enable enforcement? `Yes / No / Extend`
- [ ] After 4 weeks (Dec 13): Thresholds good? `Yes / Adjust`
- [ ] After 6 weeks (Dec 27): Production ready? `Yes / No`

---

## 🎯 SUCCESS CRITERIA

### Week 1-2 (Observation)
- ✅ 10+ signals screened
- ✅ Quality levels correlate with wins/losses
- ✅ No screener errors
- ✅ Data sufficient for enforcement decision

### Week 3-4 (Enforcement)
- ✅ Win rate improves 5-10%
- ✅ Still getting 2-4 entries/day
- ✅ P&L trending positive
- ✅ No over-filtering

### Week 5-6 (Production Readiness)
- ✅ 50%+ win rate sustained
- ✅ At least 2 profitable weeks
- ✅ Zero daily/weekly limit breaches
- ✅ System stable (no crashes)

---

## 📞 QUICK COMMANDS

```bash
# Check if bot is running
ps aux | grep start_litebotx

# View real-time logs
tail -f logs/trading_bot.log

# Count today's screening results
grep "$(date +%Y-%m-%d)" logs/trading_bot.log | grep "ENTRY SCREENING" | wc -l

# Find IDEAL entries today
grep "$(date +%Y-%m-%d)" logs/trading_bot.log | grep "IDEAL"

# Find REJECT entries today
grep "$(date +%Y-%m-%d)" logs/trading_bot.log | grep "REJECT"

# Check earnings blocks
grep "BLOCKED - Earnings" logs/trading_bot.log

# See recent trades
grep "P&L" logs/trading_bot.log | tail -10

# Backup now
cd /home/wes/Desktop && tar --exclude='litebotx_env' --exclude='__pycache__' -czf "litebotx-backup-$(date +%Y%m%d).tar.gz" litebotx-usb-deployment/
```

---

**Quick Reference Version:** 1.0  
**Last Updated:** November 14, 2025  
**Next Update:** November 29, 2025 (after observation period)

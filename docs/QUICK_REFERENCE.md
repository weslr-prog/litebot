# Quick Reference: Aggressive System Config
**October 1, 2025** | **Status: DEPLOYED** ✅

---

## 🎯 CURRENT SETTINGS

```
Max Position:      $6,000    (was $400)
Max Loss/Trade:    $400      (was $100)
Confidence:        7%        (was 8%)
Daily Pool:        60%       (was 45%)
Max Trades/Day:    8         (was 6)
Stop Loss:         2%        (was 3%)
Daily Loss Limit:  0.2%      ($1,926)
Weekly Loss Limit: 0.6%      ($5,778)
```

---

## 📊 RISK PROFILE

- **Single Trade Risk:** 0.04% of $963K portfolio
- **Typical Loss:** $120 (with 2% stop on $6K position)
- **Max Loss:** $400 (hard cap prevents $739+ disasters)
- **Position Size:** $6K (can make $300-$1,500 per winning trade)

---

## 🎯 TARGETS

### Week 1-2: **1-2% ROI** (Calibration)
- Prove consistency with $6K positions
- Win rate > 50%
- Drawdown < 5%

### Week 3-4: **2-3% ROI** (Growth)
- Consider scaling to $8K positions
- Win rate > 55%
- Sharpe > 2.0

### Week 5+: **4-5% ROI** (Aggressive)
- Full aggressive with $8-10K positions
- Win rate > 60%
- Path to 5% weekly ROI

---

## ✅ WHAT'S PROTECTED

1. ✅ No loss can exceed $400 (vs $739 INTC)
2. ✅ Stop losses at 2% (tighter than 3%)
3. ✅ Daily loss limit: 0.2%
4. ✅ Weekly loss limit: 0.6%
5. ✅ Confidence threshold: 7% (quality trades)
6. ✅ Adaptive system continues to calibrate

---

## 🚀 COMMANDS

**Test Configuration:**
```bash
python test_aggressive_config.py
python test_drawdown_fixes.py
```

**Start Bot:**
```bash
python litebotx_launcher.py
# Select "aggressive" mode
```

**Monitor Performance:**
```bash
cat logs/daily_validation.json
```

**Rollback if Needed:**
```bash
cd backups/aggressive_upgrade_20251001_184610
cp * ../../
```

---

## 📈 WEEKLY ROI PROJECTIONS

**Conservative (60% win rate):**
- 30 trades × $500 avg = **0.75% weekly ROI**

**Realistic (65% win rate):**
- 35 trades × $800 avg = **1.58% weekly ROI**

**Aggressive (65% win rate):**
- 40 trades × $1,500 avg = **3.69% weekly ROI**

---

## 🎯 SUCCESS CHECKLIST

Daily:
- [ ] Check for alerts in logs
- [ ] Verify win rate > 50%
- [ ] Confirm no losses > $400
- [ ] Check positions < $6K

Weekly:
- [ ] Calculate weekly ROI
- [ ] Review win rate trend
- [ ] Analyze largest losses
- [ ] Check Sharpe ratio

---

## 💡 KEY PRINCIPLE

**"Aggressive execution, intelligent guardrails"**

- Give bot room to achieve 5% ROI target
- Let adaptive systems calibrate automatically
- Protect against disasters with hard caps
- Monitor and adjust as needed

---

**System Status:** READY TO TRADE ✅  
**All Tests:** PASSING ✅  
**Backups:** CREATED ✅  
**Documentation:** COMPLETE ✅

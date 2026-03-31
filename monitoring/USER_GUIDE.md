# Self-Monitoring System - User Guide
## Essentials Package for Autonomous Operation

**Date:** October 5, 2025  
**Status:** ✅ COMPLETE & READY TO USE

---

## 🎯 What This System Does

Your bot can now **monitor itself** and **fix problems automatically** while you're at work. No more coming home to wonder "did it trade today?" or "were there PDT violations?"

### Key Features:

1. **PDT Violation Detection** - Scans positions.json daily, catches any same-day exits that slipped through
2. **System Health Monitoring** - Tracks positions opened, signals blocked, filter results, errors
3. **Auto-Correction** - Automatically adjusts filter parameters when issues detected
4. **Daily Reports** - Generates human-readable summary you can read when you get home

---

## 📁 What Was Created

```
monitoring/
├── pdt_auditor.py              # Scans for PDT violations
├── daily_health_checker.py     # System health diagnostics
├── auto_corrector.py           # Auto-adjusts parameters
├── daily_report_generator.py   # Creates readable reports
├── monitoring_system.py        # Coordinates everything
├── integration_hook.py         # Instructions for integration
│
├── reports/
│   ├── pdt/                    # PDT audit reports (JSON)
│   ├── health/                 # Health check reports (JSON)
│   └── ...
│
├── daily_reports/              # Human-readable summaries
│   └── daily_report_YYYY-MM-DD.txt
│
├── correction_history.json     # History of auto-adjustments
└── monitoring_system.log       # Monitoring system log
```

---

## 🚀 How to Use

### Quick Start (Standalone Testing)

Test the monitoring system independently:

```bash
# Test PDT auditor
python monitoring/pdt_auditor.py

# Test health checker
python monitoring/daily_health_checker.py

# Run full monitoring
python monitoring/monitoring_system.py

# Check specific date
python monitoring/monitoring_system.py 2025-10-04
```

### Integration with Trading Bot

The monitoring system needs to be called at end of trading day. Two options:

#### Option 1: Automatic (Integrated into Bot)
Add to `traders/short_cycle_trader.py` - see `monitoring/integration_hook.py` for exact code

#### Option 2: Manual Cron Job
Add to crontab to run daily after market close (5:00 PM ET = 10:00 PM UTC):

```bash
# Run monitoring at 5:30 PM ET daily
0 22 * * 1-5 cd /home/wes/Desktop/litebotx-usb-deployment && python monitoring/monitoring_system.py >> monitoring/cron.log 2>&1
```

---

## 📊 What You'll See When You Get Home

### Daily Report Location:
```
monitoring/daily_reports/daily_report_2025-10-05.txt
```

### Report Contents:

```
================================================================================
LITEBOTX DAILY TRADING REPORT
================================================================================
Date: 2025-10-05
Generated: 2025-10-05 17:05:00

EXECUTIVE SUMMARY
--------------------------------------------------------------------------------
Overall Status: ✅ ALL SYSTEMS OPERATIONAL

Quick Stats:
  • Positions Opened: 12
  • Positions Closed: 8
  • PDT Compliance: PASS
  • System Health: HEALTHY (95/100)
  • Issues Detected: 0
  • Auto-Corrections: 0

PDT COMPLIANCE AUDIT
--------------------------------------------------------------------------------
Compliance Status: PASS
Positions Checked: 20
Violations Found: 0
Critical Violations: 0

✅ No PDT violations detected - excellent compliance!

SYSTEM HEALTH CHECK
--------------------------------------------------------------------------------
Health Status: HEALTHY
Health Score: 95/100
Issues Found: 0

✅ System is healthy - all checks passed!

TRADING PERFORMANCE
--------------------------------------------------------------------------------
Signal Processing:
  • Signals Generated: 15
  • Signals Executed: 12
  • Signals Blocked: 3
  • Execution Rate: 80.0%

Pre-Filter Results:
  • Input Symbols: 500
  • Output Candidates: 15

Position Activity:
  • Positions Opened: 12
  • Positions Closed: 8

Exit Reasons:
  • SMART_D1_EXIT: 6
  • STOP_LOSS: 2

RECOMMENDATIONS
--------------------------------------------------------------------------------
✅ No action required - system is operating optimally

================================================================================
END OF REPORT
```

---

## 🔧 What Gets Auto-Corrected

### Issue: No Trades (Pre-filter returns 0)
**Detection:** `positions_opened == 0` and `prefilter_candidates == 0`

**Auto-Correction:**
- Reduces `min_rows` from 30 → 25 → 20 (minimum: 15)
- Reduces `min_avg_volume` by 30% if needed
- Logs: "🔧 AUTO-ADJUST: Relaxing min_rows 30 → 25"

**Safety Limits:**
- Max 3 corrections per day
- Never reduces min_rows below 15
- Never reduces volume below 20,000

### Issue: PDT Violations Detected
**Detection:** Same-day exits found in positions.json

**Auto-Response:**
- Creates `EMERGENCY_PDT_MODE.flag`
- Blocks all new trading until manual review
- Logs: "🔒 EMERGENCY: PDT violation detected - trading restricted"

**Manual Override:**
```bash
rm monitoring/EMERGENCY_PDT_MODE.flag
```

---

## 📋 Daily Checklist (When You Get Home)

1. **Read the Daily Report**
   ```bash
   cat monitoring/daily_reports/daily_report_$(date +%Y-%m-%d).txt
   ```

2. **Check Status Summary**
   - PDT Compliance: Should say "PASS"
   - System Health: Should say "HEALTHY"
   - Auto-Corrections: Note any adjustments made

3. **Review Violations (if any)**
   ```bash
   ls -lh monitoring/reports/pdt/
   cat monitoring/reports/pdt/pdt_audit_$(date +%Y-%m-%d).json
   ```

4. **Check Auto-Corrections**
   ```bash
   cat monitoring/correction_history.json | tail -20
   ```

---

## ⚙️ Configuration & Safety

### Auto-Correction Limits

These are hardcoded safety limits in `auto_corrector.py`:

```python
min_safe_min_rows = 15              # Never go below 15 days data
min_safe_volume = 20_000            # Never go below 20k volume
max_adjustments_per_day = 3         # Max 3 corrections per day
```

### Health Check Thresholds

In `daily_health_checker.py`:

```python
min_expected_positions = 5          # Expect at least 5 positions
max_block_rate = 0.7               # Max 70% signals blocked
max_errors_per_day = 10            # Max 10 errors
min_prefilter_candidates = 10      # Expect 10+ candidates
```

To adjust these, edit the `__init__` methods in respective files.

---

## 🚨 Emergency Situations

### Emergency PDT Mode Activated

**What it means:** The system detected PDT violations and automatically restricted trading.

**What to do:**
1. Read the PDT audit report
2. Verify the violations are real (check positions.json)
3. If false positive, clear the flag:
   ```bash
   rm monitoring/EMERGENCY_PDT_MODE.flag
   ```
4. If real violations, investigate why D+1 protection failed

### System Health CRITICAL

**What it means:** Multiple serious issues detected (high errors, no trades, filter failures)

**What to do:**
1. Read the health report for details
2. Check logs: `logs/short_cycle_trader.log`
3. Verify API connectivity
4. Check if market was open (holidays, weekends)
5. Review recommended actions in report

---

## 📈 Weekly Review

Run weekly PDT summary:

```python
from monitoring.pdt_auditor import PDTAuditor

auditor = PDTAuditor()
summary = auditor.generate_weekly_summary()

print(f"Weekly Compliance Rate: {summary['compliance_rate']:.1f}%")
print(f"Total Violations: {summary['total_violations']}")
```

Or check correction trends:

```python
from monitoring.auto_corrector import AutoCorrector

corrector = AutoCorrector()
summary = corrector.get_correction_summary(days=7)

print(f"Total Corrections (7 days): {summary['total_corrections']}")
```

---

## 🐛 Troubleshooting

### "Module not found" errors

```bash
cd /home/wes/Desktop/litebotx-usb-deployment
export PYTHONPATH=/home/wes/Desktop/litebotx-usb-deployment:$PYTHONPATH
python monitoring/monitoring_system.py
```

### Monitoring not running automatically

Check if integrated into trader:
```bash
grep "SelfMonitoringSystem" traders/short_cycle_trader.py
```

If not found, follow integration instructions in `monitoring/integration_hook.py`

### Reports not being generated

Check permissions:
```bash
ls -la monitoring/
chmod +x monitoring/*.py
```

Check log:
```bash
tail -50 monitoring/monitoring_system.log
```

---

## 📞 What to Look For Each Day

### ✅ Good Signs:
- PDT Compliance: PASS
- Health Status: HEALTHY
- Health Score: 80-100
- Positions Opened: 5-15
- No emergency flags

### ⚠️ Warning Signs:
- PDT Compliance: PASS but with rapid re-entries
- Health Status: WARNING
- Health Score: 50-79
- Positions Opened: 1-4 (lower than expected)
- 1-2 auto-corrections applied

### 🚨 Critical Signs:
- PDT Compliance: FAIL
- Health Status: CRITICAL
- Health Score: <50
- Positions Opened: 0
- Emergency PDT mode active
- 3+ auto-corrections in one day

---

## 📝 Notes

### What This System Does NOT Do:
- ❌ Does not send emails (you said you don't need them)
- ❌ Does not modify trading strategy logic
- ❌ Does not place or cancel orders
- ❌ Does not change risk parameters

### What This System DOES Do:
- ✅ Monitors for PDT violations after-the-fact
- ✅ Adjusts pre-filter parameters (min_rows, volume)
- ✅ Detects system health issues
- ✅ Generates daily reports
- ✅ Logs all actions with reasoning

---

## 🎓 Advanced Usage

### Custom Monitoring Schedule

Run monitoring at specific time:
```bash
# Add to crontab
30 17 * * 1-5 cd /path/to/bot && python monitoring/monitoring_system.py
```

### Query Specific Dates

```bash
# Check last week
for i in {1..7}; do
    date=$(date -d "$i days ago" +%Y-%m-%d)
    echo "Checking $date..."
    python monitoring/monitoring_system.py $date
done
```

### Export to CSV

```python
import json
import pandas as pd

# Load health reports
reports = []
for file in Path("monitoring/reports/health").glob("*.json"):
    with open(file) as f:
        reports.append(json.load(f))

# Convert to DataFrame
df = pd.DataFrame([{
    'date': r['check_date'],
    'health_score': r['system_health_score'],
    'positions': r['metrics']['positions_opened'],
    'status': r['overall_status']
} for r in reports])

df.to_csv('health_history.csv', index=False)
```

---

## ✅ System Status Check

Run this to verify everything is working:

```bash
cd /home/wes/Desktop/litebotx-usb-deployment

echo "Testing PDT Auditor..."
python monitoring/pdt_auditor.py

echo "Testing Health Checker..."
python monitoring/daily_health_checker.py

echo "Testing Full System..."
python monitoring/monitoring_system.py

echo "✅ All modules tested!"
```

---

## 🎯 Summary

You now have a **self-monitoring, self-correcting trading bot**. While you're at work:

1. ✅ Bot trades automatically
2. ✅ Monitors itself for PDT violations
3. ✅ Tracks system health
4. ✅ Auto-adjusts filters if needed
5. ✅ Generates daily report

When you get home:

1. ✅ Read `monitoring/daily_reports/daily_report_YYYY-MM-DD.txt`
2. ✅ Check PDT Compliance status
3. ✅ Review any auto-corrections
4. ✅ Verify system health score

**No more wondering what happened during the day!** 🎉

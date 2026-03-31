# ⚠️ RESTORE PRODUCTION SETTINGS AFTER FIRST TRADE

## Current Temporary Test Mode Settings

**File:** `small_portfolio_config.py`

### Changes Made (November 6, 2025 @ 10:47 AM)

1. **Line ~77:** `confidence_threshold`
   - **CURRENT (TEST):** `0.025` (2.5%)
   - **RESTORE TO:** `0.05` (5%)
   
2. **Line ~129:** `late_entry_confidence_multiplier`
   - **CURRENT (TEST):** `1.05` (5% over base)
   - **RESTORE TO:** `1.3` (30% over base)

---

## Why Relaxed?

**Market Conditions Today:** Slow market day, no momentum
- S&P 500: -0.31%
- NASDAQ: -0.56%
- Your watchlist: All stocks < 1% movement
- No volume surges

**Goal:** See bot execute ONE trade to verify:
- ✅ Config fixes work
- ✅ Position sizing works
- ✅ Trade execution works
- ✅ Logging works

---

## When to Restore

**IMMEDIATELY AFTER:**
1. Bot executes 1 paper trade successfully
2. You see trade confirmation in logs
3. Position shows in dashboard/logs

**Expected Timeline:** Within next 2-3 hours (until 2:30 PM cutoff)

---

## How to Restore

### Option 1: Manual Edit
Edit `small_portfolio_config.py`:
```python
# Line ~77 (restore this)
confidence_threshold: float = 0.05  # 5% confidence threshold

# Line ~129 (restore this)
late_entry_confidence_multiplier: float = 1.3  # Require 1.3x confidence for late entries
```

### Option 2: Quick Command
```bash
cd /home/wes/Desktop/litebotx-usb-deployment
sed -i 's/confidence_threshold: float = 0.025/confidence_threshold: float = 0.05/' small_portfolio_config.py
sed -i 's/late_entry_confidence_multiplier: float = 1.05/late_entry_confidence_multiplier: float = 1.3/' small_portfolio_config.py

# Restart bot
pkill -f start_small_portfolio_trader.py
sleep 3
source litebotx_env/bin/activate
nohup python3 start_small_portfolio_trader.py > /dev/null 2>&1 &
```

---

## Current Bot Status

**Running:** PID 218960 (started 10:47 AM)
**Mode:** 🧪 TEST MODE - Relaxed thresholds
**Scanning:** AMD, MMM, IBM, UPS, SHOP, CSCO (6 stocks)
**Next Check:** Every 5 minutes until 2:30 PM

**New Thresholds:**
- Base confidence: 2.5% (vs 5% production)
- Late entry: 2.625% (2.5% × 1.05) vs 6.5% before

**This should be LOW ENOUGH to catch weak signals on slow market days.**

---

## What to Watch For

Monitor logs for:
```bash
tail -f logs/short_cycle_trader.log | grep -E "Late entry signal|Paper trade|ENTRY"
```

**Success looks like:**
```
✅ AMD: Late entry signal (confidence: 2.8%)
📝 Paper trade: BUY AMD @ $242.37, size: 2 shares ($50)
```

---

## Risk Assessment

**Risk Level:** ✅ VERY LOW
- Paper trading only (no real money)
- Small position sizes ($50-75)
- Same-day exit at 3:45 PM
- All safety monitors still active

**Worst Case:** Bot takes 1-2 weak trades that exit for small loss. This helps validate the system works.

---

**Created:** November 6, 2025 @ 10:47 AM  
**Status:** ⏳ AWAITING FIRST TRADE  
**Restore By:** End of trading day or after first trade

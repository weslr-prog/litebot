# 🚨 CRITICAL BUG DISCOVERED - October 28, 2025

## The Problem

Bot generated 6 signals today but **shares = null** (not even 0!)

```json
{
  "symbol": "SHOP",
  "shares": null,      ← CRITICAL BUG
  "entry_price": 174.877059
}
```

## Evidence

All 6 entries today have the same issue:
- SHOP, MMM, INTC, PYPL, QCOM, UPS
- All have `entry_price` ✅
- All have `shares: null` ❌

## What This Means

1. **Signal Generation:** ✅ Working (6 signals found)
2. **Price Discovery:** ✅ Working (entry prices recorded)
3. **Position Sizing:** ❌ **BROKEN** (returns `null` instead of share count)
4. **Order Execution:** ❌ Likely skipped (can't place order with `null` shares)

## Root Cause

The position sizing calculation in `risk.py` or `execution_engine.py` is returning `null`/`None` instead of an integer share count.

### Possible Causes

1. **Division by zero** in position sizing formula
2. **Missing account balance** data
3. **Capital pool calculation** returning None
4. **Risk calculation** hitting an error and returning None
5. **Type error** in share calculation (e.g., `None * price = None`)

## Impact

### Today's Missed Trades
```
If we had bought 6 positions:
Expected: ~$24K per position = $144K total
Actual: $0 invested (null shares)

Potential profit based on today's moves:
- UPS:  +8.03% = ~$1,924
- INTC: +5.03% = ~$1,207  
- NVDA: +4.98% = ~$1,195
- PYPL: +3.94% = ~$946
- Others: ~$0 net

Total missed: ~$5,272 🔥
```

## Comparison to Manual Orders (Oct 27)

Manual orders **worked fine**:
```
QCOM: 133 shares ← Real number
UPS:  252 shares ← Real number
PYPL: 329 shares ← Real number
INTC: 582 shares ← Real number
```

But automated bot today returned:
```
All symbols: null shares ← Bug!
```

## Critical Questions

1. **Why does manual script work but automated bot doesn't?**
   - Different code path?
   - Different risk calculation?
   - Different account balance fetch?

2. **What changed between Oct 27 (manual) and Oct 28 (automated)?**
   - Bot restart?
   - Config change?
   - API issue?

3. **Where exactly is None being returned?**
   - Risk manager?
   - Execution engine?
   - Trader logic?

## Debugging Steps

### 1. Check Risk Manager
```python
# In risk.py
def calculate_position_size(symbol, price, ...):
    shares = ...
    print(f"DEBUG: {symbol} calculated {shares} shares")
    return shares  # Is this returning None?
```

### 2. Check Execution Engine
```python
# In execution_engine.py  
def place_order(symbol, shares, ...):
    print(f"DEBUG: Placing order for {shares} shares of {symbol}")
    if shares is None:
        print(f"ERROR: shares is None!")
        return None
```

### 3. Check Capital Pool
```python
# Check daily capital allocation
print(f"DEBUG: Daily pool = ${daily_pool}")
print(f"DEBUG: Per position = ${per_position_size}")
print(f"DEBUG: Shares = {per_position_size / price}")
```

## Urgent Fix Needed

**Priority:** 🔴 CRITICAL - Bot is finding trades but not executing them!

**Timeline:**
- **Today:** Identify exact line returning None
- **Tomorrow:** Fix and test with paper trades
- **This Week:** Deploy fix and verify with real trades

## Temporary Workaround

Until fixed, use manual entry script:
```bash
# If bot shows 0 entries, run manual script
python3 scripts/archive/manual_buy_for_tomorrow.py
```

---

**Status:** 🚨 Bug identified, needs immediate fix  
**Impact:** High - Missing all automated trades  
**Next Step:** Debug risk.py and execution_engine.py for None returns

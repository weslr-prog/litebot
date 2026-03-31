# HARDCODED VALUES AUDIT
## November 11, 2025

This document lists ALL hardcoded values found in the trading system and categorizes them by whether they should be dynamic or remain static.

---

## 🔴 CRITICAL: Should Be Dynamic (Currently Hardcoded)

### 1. Trading Universe (Line 3068 - `traders/short_cycle_trader.py`)
**Current:** Hardcoded 60-symbol list
```python
candidates = [
    "PLTR","RIVN","LCID","NIO","XPEV","LI","GOEV","FSR",
    "HOOD","SOFI","UPST","AFRM","SQ","OPEN","COIN",
    # ... 60 total symbols
]
```

**Should Be:** Dynamic daily fetch from Alpaca API
- Fetch ALL tradable stocks from Alpaca (8000+ stocks)
- Filter by exchange (NYSE, NASDAQ)
- Filter by price range ($10-30)
- PreFilter applies momentum/volatility/volume filters
- Updates daily automatically

**Impact:** 
- ❌ Manual maintenance required
- ❌ No auto-discovery of new IPOs
- ❌ Doesn't remove delisted stocks
- ❌ Limited sector diversity (only 60 symbols)

**Solution:** Use `dynamic_universe_generator.py` (just created)

---

## 🟡 MODERATE: Partially Dynamic

### 2. Price Range Filters (7 locations in `pre_filter.py`)
**Current:** Dynamic but configured with constants
```python
MIN_PRICE = 10.0  # Line 135
MAX_PRICE = 30.0  # Line 136
```

**Status:** ✅ FIXED (Nov 11) - Now uses class constants, propagates everywhere
- All 7 hardcoded ranges replaced with MIN_PRICE/MAX_PRICE
- Single source of truth
- Easy to adjust for different portfolio sizes

**Recommendation:** Keep as configurable constants (not dynamic)

---

## 🟢 ACCEPTABLE: Should Remain Static

### 3. PDT Protection Threshold
**Location:** Various files
```python
PDT_THRESHOLD = 25000  # FINRA regulation
```
**Reason:** Legal requirement, cannot change

### 4. Market Hours
**Location:** `market_hours.py`
```python
MARKET_OPEN = "09:30"
MARKET_CLOSE = "16:00"
```
**Reason:** NYSE/NASDAQ official hours (rarely change)

### 5. Risk Parameters
**Location:** Portfolio configs
```python
MAX_POSITION_SIZE = 0.15  # 15% per position
MAX_PORTFOLIO_RISK = 0.02  # 2% max loss
```
**Reason:** Trading strategy design choices (should be configurable, not dynamic)

### 6. Technical Indicator Periods
**Location:** `indicator_calculator.py`
```python
RSI_PERIOD = 14
MACD_FAST = 12
MACD_SLOW = 26
```
**Reason:** Standard indicator settings (can be configured but not dynamic)

---

## 📊 COMPREHENSIVE SEARCH RESULTS

### Hardcoded Lists Found:

1. **Trading Universe Candidates** (`short_cycle_trader.py` line 3068)
   - Status: 🔴 SHOULD BE DYNAMIC
   - Count: 60 symbols
   - Last updated: November 11, 2025 (manually)

2. **S&P 500 List** (`scripts/archive/dynamic_watchlist_generator.py` line 75)
   - Status: 🟡 ARCHIVED (not currently used)
   - Count: ~100 symbols
   - Note: This was designed to be dynamic but had fallback list

### Hardcoded Numeric Values Found:

**Price Ranges (✅ FIXED):**
- `pre_filter.py` lines 135-136: MIN_PRICE/MAX_PRICE constants
- All other instances now reference these constants

**Volume Requirements:**
- `pre_filter.py` line 138: `MIN_AVG_VOLUME = 100_000`
- `pre_filter.py` line 305: `min_volume=100000` (default parameter)
- Status: 🟢 ACCEPTABLE - Quality filter threshold

**Volatility Thresholds:**
- `pre_filter.py` line 139: `MIN_ATR = 3.0`
- Status: 🟢 ACCEPTABLE - Strategy parameter

**Position Sizing:**
- `small_portfolio_config.py`: Various risk parameters
- Status: 🟢 ACCEPTABLE - Strategy design

**Timeframes:**
- Multiple files: `1Min`, `5Min`, `1Hour`, `1Day` bars
- Status: 🟢 ACCEPTABLE - Technical analysis standard

---

## 🔍 SEARCH METHODOLOGY

### Commands Run:
```bash
grep -r "candidates\s*=\s*\[" traders/
grep -r "MIN_PRICE|MAX_PRICE" pre_filter.py
grep -r "HARDCODED" **/*.py
grep -r "\[.*\].*#.*symbols" **/*.py
```

### Files Reviewed:
- ✅ traders/short_cycle_trader.py (3,646 lines)
- ✅ pre_filter.py (1,745 lines)
- ✅ small_portfolio_config.py (374 lines)
- ✅ scripts/archive/dynamic_watchlist_generator.py (563 lines)
- ✅ All config files (stock_config.py, etc.)

---

## ✅ RECOMMENDATIONS

### HIGH PRIORITY (Do Now):

1. **Integrate Dynamic Universe Generator**
   - File created: `dynamic_universe_generator.py`
   - Replace line 3068 in `short_cycle_trader.py`
   - Use `get_dynamic_universe()` instead of hardcoded list
   - Schedule daily refresh (cache/dynamic_universe.json)

### MEDIUM PRIORITY (Next Week):

2. **Create Configuration System**
   - Centralize all strategy parameters
   - Move price ranges, volume, volatility to config
   - Version control for different strategies

3. **Add Universe Diversity Tracking**
   - Monitor sector distribution
   - Ensure not over-concentrated in one sector
   - Alert if universe becomes too homogeneous

### LOW PRIORITY (Future):

4. **Machine Learning Parameter Tuning**
   - Auto-tune RSI periods, MACD settings
   - Adaptive thresholds based on market conditions
   - But keep human oversight on major changes

---

## 🎯 SUMMARY

**Found Hardcoded Values:**
- 🔴 CRITICAL (1): Trading universe candidate list
- 🟡 MODERATE (0): All fixed today (price ranges)
- 🟢 ACCEPTABLE (15+): Strategy parameters, legal requirements

**Action Items:**
1. ✅ Price ranges → FIXED (Nov 11)
2. ✅ PDT logic → FIXED (Nov 11)
3. ❌ Universe generation → NEEDS FIX (dynamic generator created, needs integration)
4. ✅ All other values → Properly configured as constants

**Next Step:**
Integrate `dynamic_universe_generator.py` into `short_cycle_trader.py` line 3068.

---

## 📝 NOTES

- Most "hardcoded" values are actually proper strategy parameters
- The main issue is the trading universe list (60 symbols)
- Solution exists: `get_dynamic_universe()` fetches from Alpaca API
- Daily caching ensures reliability even if API fails
- Emergency fallback to mid-cap list if both fail

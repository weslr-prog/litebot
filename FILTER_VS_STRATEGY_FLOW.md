# Filter vs Strategy: Where Does Each Check Happen?

## The Complete Flow (9:45 AM Entry Scan)

```
107 stocks in universe
    ↓
┌─────────────────────────────────────────────────────────────┐
│  STAGE 1: PREFILTER (bot_v2/core/pre_filter.py)           │
│  Purpose: Fast elimination of unsuitable stocks             │
│  Cost: ~15 seconds (cheap yfinance data)                   │
└─────────────────────────────────────────────────────────────┘
    │
    ├─→ Stage 1: Price Filter ($8-$35)
    │   • Checks: Latest close price
    │   • Rejects: Penny stocks (<$8), slow mega-caps (>$35)
    │   • Result: 71/107 pass (66.4%)
    │
    ├─→ Stage 2: Volume/Liquidity Filter (2M-20M shares, $25M)
    │   • Checks: 30-day average volume (excluding today)
    │   • Checks: 30-day average dollar volume
    │   • Rejects: Illiquid stocks (<2M), mega-caps (>20M)
    │   • Result: 48/71 pass (67.6%)
    │
    └─→ Stage 3: Volatility Filter (2.5%-5.5% ATR)
        • Checks: 14-day ATR as % of price
        • Rejects: Low volatility (<2.5%), chaotic (>5.5%)
        • Result: 25/48 pass (52.1%)
        
    ↓
25 candidates pass prefilter
    ↓
┌─────────────────────────────────────────────────────────────┐
│  MARKET DATA FETCH                                          │
│  Cost: ~5 seconds (100 days of history for 25 stocks)      │
└─────────────────────────────────────────────────────────────┘
    ↓
25 candidates with full market data
    ↓
┌─────────────────────────────────────────────────────────────┐
│  STAGE 2: STRATEGY CHECKS (signal_generator.py)            │
│  Purpose: Find specific entry setups                        │
│  Cost: ~3 seconds (calculations on 25 stocks)              │
└─────────────────────────────────────────────────────────────┘
    │
    ├─→ D+1 Rule Filter (line 214)
    │   • Checks: Do we already have a position in this stock?
    │   • Purpose: Prevent PDT violations
    │   • Rejects: Any stock with active position
    │   • Example: If STLA is open, can't enter STLA again
    │
    ├─→ Blacklist Filter (line 225)
    │   • Checks: Is this a chronic loser?
    │   • Purpose: Avoid repeating mistakes
    │   • Rejects: T, TU, OGE, BXMT, VIPS, VIRT, JD, NI
    │   • Result: ~23/25 remain (2 blacklisted)
    │
    ├─→ Per-Symbol Analysis (_analyze_symbol, line 240)
    │   │
    │   ├─→ Trend Filter: 20-day SMA (line 265)
    │   │   • Checks: Is price within 6% of 20-day average?
    │   │   • Purpose: Avoid broken stocks/structural issues
    │   │   • Rejects: Price >6% below SMA (too far for mean reversion)
    │   │   • Example: "INTC: Price $36.20 more than 6% below SMA $38.88"
    │   │
    │   ├─→ Momentum Filter: 5-day change (line 286)
    │   │   • Checks: Did stock drop >5% in last 5 days?
    │   │   • Purpose: Avoid falling knives
    │   │   • Rejects: Momentum < -5% (still falling too fast)
    │   │   • Example: "MRNA: 5-day momentum -7.7%"
    │   │
    │   ├─→ **RSI CHECK** (line 312, 372) ⭐ THIS IS WHERE RSI HAPPENS
    │   │   • Calculates: RSI(7) on close prices
    │   │   • Checks: Is RSI <= 30? (oversold threshold)
    │   │   • Purpose: Find panic-sold stocks ready to bounce
    │   │   • Formula: RSI confidence = (30 - current_rsi) / 20.0
    │   │   • Example: RSI=25 → confidence=0.25, RSI=20 → confidence=0.50
    │   │
    │   ├─→ Liquidity Check (line 358)
    │   │   • Checks: Average dollar volume >= $500K/day
    │   │   • Purpose: Ensure we can exit without slippage
    │   │   • Note: Already filtered 2M+ volume in PreFilter
    │   │   • This is a double-check at strategy level
    │   │
    │   ├─→ Earnings Filter (line 496)
    │   │   • Checks: Is earnings within 3 days before / 1 day after?
    │   │   • Purpose: Avoid earnings volatility
    │   │   • Rejects: Stocks near earnings announcements
    │   │
    │   ├─→ Quality Scoring (line 435) [OPTIONAL]
    │   │   • Checks: Price action quality, volume patterns, sector strength
    │   │   • Purpose: Boost confidence for high-quality setups
    │   │   • Result: Multiplies base confidence by 1x-3x
    │   │
    │   └─→ Confidence Threshold (line 443)
    │       • Checks: Is final confidence >= 50%?
    │       • Purpose: Only trade high-probability setups
    │       • Rejects: Low-confidence signals (<50%)
    │
    └─→ Signal Generation
        • Result: 0-7 high-quality entry signals
        • Sorted by confidence (highest first)
        • Max 12 positions per day

    ↓
0-7 entry signals
    ↓
┌─────────────────────────────────────────────────────────────┐
│  EXECUTION (order_manager.py)                               │
│  Purpose: Execute trades for approved signals               │
└─────────────────────────────────────────────────────────────┘
```

---

## What's Checked Where?

### **PreFilter (Lines 691-697 in launcher.py)**
**Cost:** ~15 seconds for 107 stocks

| Check | Purpose | Why Here? |
|-------|---------|-----------|
| **Price** ($8-$35) | Eliminate penny stocks & slow mega-caps | Fast, no calculation needed |
| **Volume** (2M-20M) | Eliminate illiquid & too-stable stocks | Fast, just average volume |
| **ATR** (2.5%-5.5%) | Eliminate low-volatility chronic losers | Fast calculation (14-day ATR) |

**Why these go first:**
- ✅ Cheap to calculate (basic math on 30-day data)
- ✅ Eliminate 75% of universe (107→25 stocks)
- ✅ No need to fetch full market data for rejects

---

### **Strategy (_analyze_symbol, line 240+)**
**Cost:** ~3 seconds for 25 candidates

| Check | Line | Purpose | Why Here? |
|-------|------|---------|-----------|
| **D+1 Rule** | 214 | Prevent re-entering active positions | Requires position state |
| **Blacklist** | 225 | Avoid chronic losers | Requires historical performance data |
| **20-SMA Trend** | 265 | Reject broken stocks (>6% below average) | Requires 20 days of data |
| **5-Day Momentum** | 286 | Reject falling knives (<-5%) | Requires 5 days of data |
| **RSI(7)** | 312, 372 | Find oversold bounces (RSI<=30) | ⭐ **MAIN ENTRY SIGNAL** |
| **Liquidity** | 358 | Double-check $500K+ daily volume | Verify slippage protection |
| **Earnings** | 496 | Skip stocks near earnings | Requires calendar lookup |
| **Quality Score** | 435 | Boost confidence for high-quality setups | Requires 100 days of data |
| **Confidence** | 443 | Filter low-probability setups (<50%) | Final gatekeeper |

**Why these go second:**
- ✅ Require full market data (100 days)
- ✅ More expensive calculations (RSI, SMA, momentum)
- ✅ Only run on 25 pre-filtered candidates (not all 107)
- ✅ Specific entry logic (RSI oversold, etc.)

---

## Your Questions Answered

### **1. When does my bot check RSI?**

**Answer:** Line 312 in `signal_generator.py`, AFTER prefilter

**Flow:**
```
9:45 AM: Entry scan starts
   → PreFilter runs (107 → 25 stocks) [15 seconds]
   → Market data fetched for 25 candidates [5 seconds]
   → For each of 25 candidates:
      → Calculate RSI(7) [line 312]
      → Check if RSI <= 30 [line 372]
      → If YES: Calculate confidence & create signal
      → If NO: Reject (not oversold)
```

**Why it works this way:**
- RSI calculation requires 7+ days of close prices
- Expensive to calculate for all 107 stocks
- Cheaper to filter to 25 candidates first, THEN calculate RSI

---

### **2. Am I checking liquidity twice?**

**Answer:** YES, but for different reasons

**PreFilter Liquidity (Stage 2):**
- **When:** Lines 212-220 in pre_filter.py
- **Check:** 2M-20M volume, $25M dollar volume
- **Purpose:** Eliminate illiquid stocks BEFORE fetching full data
- **Reason:** "Can we trade this stock at all?"

**Strategy Liquidity (Line 358):**
- **When:** Inside `_analyze_symbol()` in signal_generator.py
- **Check:** $500K+ average dollar volume
- **Purpose:** Final verification before creating signal
- **Reason:** "Can we exit this specific trade without slippage?"

**Why both?**
1. PreFilter catches illiquid stocks early (don't waste API calls)
2. Strategy double-checks before actual entry (safety net)
3. Different thresholds ($25M vs $500K) for different purposes

**Efficiency verdict:** ✅ Good design
- PreFilter is strict (2M-20M, $25M) to eliminate bad stocks
- Strategy is lenient ($500K) as a safety check
- Only 25 stocks reach strategy check, so 2nd check is cheap

---

### **3. Are you doing the right things at the correct point?**

**Answer:** YES, but there's one optimization opportunity

**✅ GOOD:**
1. **Price filter first** - Cheapest check, eliminates 36 stocks
2. **Volume filter second** - Fast check, eliminates 23 more stocks
3. **ATR filter third** - Requires calculation but still cheap, eliminates 23 more
4. **RSI check AFTER prefilter** - Expensive, only done on 25 candidates
5. **Liquidity double-check** - Safety net, minimal cost

**⚠️ OPTIMIZATION OPPORTUNITY:**

**Current order in Strategy:**
```
1. D+1 Rule (cheap)
2. Blacklist (cheap)
3. 20-SMA Trend (requires calculation)
4. 5-Day Momentum (requires calculation)
5. RSI (requires calculation) ← MAIN SIGNAL
6. Liquidity (cheap)
7. Earnings (API call)
8. Quality Score (expensive calculation)
```

**More efficient order:**
```
1. D+1 Rule (cheap) ✅
2. Blacklist (cheap) ✅
3. Earnings (API call) ← MOVE UP
4. Liquidity (cheap) ← MOVE UP
5. 20-SMA Trend (calculation)
6. 5-Day Momentum (calculation)
7. RSI (calculation) ← MAIN SIGNAL
8. Quality Score (expensive)
```

**Why move Earnings & Liquidity up?**
- If earnings are in 3 days, no point calculating RSI
- If liquidity fails, no point calculating RSI
- These are cheap checks that reject stocks early
- Saves RSI calculation cycles

**Estimated savings:** ~0.5 seconds per entry scan (minor but better)

---

## Summary: Filter vs Strategy

| Stage | What | Where | Cost | Stocks | Purpose |
|-------|------|-------|------|--------|---------|
| **PreFilter** | Price, Volume, ATR | pre_filter.py | 15s | 107→25 | Fast elimination |
| **Strategy** | RSI, Trend, Momentum, etc. | signal_generator.py | 3s | 25→0-7 | Find entry setups |
| **Execution** | Place orders | order_manager.py | 1s | 0-7→fills | Execute trades |

**Total scan time:** ~20 seconds
**Result:** 0-7 high-quality entry signals

---

## Key Insight

**Your current design is 95% optimal!**

The only improvement would be moving the cheap checks (Earnings, Liquidity double-check) earlier in the strategy flow to avoid unnecessary RSI calculations on stocks that will be rejected anyway.

But this is a **micro-optimization** - your current flow is already very efficient:
- ✅ Filters 75% of universe BEFORE expensive calculations
- ✅ Only calculates RSI on viable candidates
- ✅ Double-checks liquidity before entry (safety)
- ✅ Separates filtering (speed) from strategy (accuracy)

**The design is sound.** The filters end where they should, and the strategy begins at the right point. 🎯

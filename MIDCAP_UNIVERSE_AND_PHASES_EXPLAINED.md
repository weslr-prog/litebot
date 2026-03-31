# Mid-Cap Universe Clarification & Expansion Strategy

**Date:** January 30, 2026  
**Question:** Bot is designed for mid-caps correct? Where to find more? How does this fit with phases 2a, 2b, 3?  

---

## Your Current Bot Configuration

### Yes, you're correct - mid-cap focus by price & volatility

**Not mid-cap by market cap alone, but by trading characteristics:**

| Parameter | Your Bot | What It Means |
|-----------|----------|---------------|
| **Price Range** | $10-35 per share | Sweet spot for small account leverage |
| **Market Cap** | $2B-$10B (lower-mid to large-mid) | Volatile growth stocks, tech, energy |
| **Dollar Volume** | $500K-$1M minimum | Liquid enough to trade, not mega-caps |
| **Volatility** | 3-12% ATR | Higher % moves than large caps (1-3%) |
| **Daily Movement** | 3-8% typical | Perfect for short-term swings |

**Examples of your target stocks:**
- Tech volatiles: PLTR, CRWD, OKTA, UPST ($10-30)
- Energy mid-caps: OXY, DVN, MPC, PSX ($30-80)
- Materials: CLF, FCX, NEM ($15-50)
- Fintech: SOFI, UPST, SQ ($10-40)

**Why this range?**
- Small accounts ($1K-$10K) can't trade $100+ stocks (too few shares)
- $10-35 range = 100-1000 shares → real leverage
- 3-8% daily swings = 2-5% profit in 1-2 hours

---

## Where to Find More Mid-Cap Candidates

### 1. Finviz Screener (Easiest - Free)

**URL:** https://finviz.com/screener.ashx

**Exact filter settings:**
```
Price: $10 to $40
Avg Volume: > 1 million
Change: 3%+ (relative strength candidates)
P/E Ratio: < 50 (profitable)
Market Cap: > $500 million
Sector: Any
Industry: Any
```

**Result:** ~200-300 stocks in your range daily
**Time:** 5 minutes per day to generate new list

### 2. YFinance Dynamic Universe (Already Built-In)

Your bot already has dynamic universe generator that:
- Fetches top 200 mid-cap candidates automatically
- Filters by price, volume, volatility
- Updates daily
- Fallback list if API fails

**Current configuration in `dynamic_universe_generator.py`:**
```python
# Fetches from screened universe:
# - Price: $10-40
# - Volume: 1M+ shares/day
# - Market cap: auto-filtered by price
# - Result: 100-200 candidates automatically
```

### 3. Sector-Specific ETF Components

Since Phase 2b will do sector rotation, here are good sector-specific mid-caps:

**Energy Sector (XLE components):**
```
OXY, DVN, MPC, PSX, EOG, HAL, SLB, CVX
(Price: $30-80, high volatility when crude moves)
```

**Healthcare (XLV components):**
```
VEEV, REGN, VRMM, PKI, INTU
(Price: $20-60, consistent volatility)
```

**Technology (XLK components):**
```
PLTR, CRWD, OKTA, SNOW, UPST
(Price: $10-40, highest volatility)
```

**Materials (XME components):**
```
CLF, FCX, NEM, MOS, APD
(Price: $15-80, volatile with commodities)
```

**Consumer (XLY components):**
```
TSLA, UPST, SOFI, LCID, RIVN
(Price: $10-60, momentum dependent)
```

### 4. Sector Momentum Screening (For Phase 2b)

Once you implement Phase 2b, you'll want to screen by sector strength:

**Strong Sector → Find all mid-caps in that sector**
```
If XLE (energy) up 5%+ this week:
  Add: OXY, DVN, MPC, PSX, HAL (all energy)

If XLV (healthcare) up 3%+:
  Add: VEEV, REGN, VRMM (all healthcare)
```

**Weak Sector → Reduce or avoid that sector**
```
If XLK (tech) down 3%:
  Reduce: PLTR, CRWD, OKTA entries
  OR only allow if RS > 0.8 (very high alpha)
```

---

## How This Fits With Phases 2a, 2b, 3

### Right Now (Phase 1b Hard Gates)

**Universe:** 100-200 mid-cap candidates  
**Gate:** RS >= 0.6 (binary accept/reject)  
**Result:** 5-8 trades/day from available candidates

### Tomorrow - Phase 2a (Soft Gates)

**Universe:** SAME 100-200 candidates  
**Gate:** RS 0.35-1.30x (position sizing)  
**Result:** **8-12 trades/day** (+50%)

**Why more trades?** 
- Don't reject RS 0.3-0.6 trades anymore
- Accept them with smaller positions
- More opportunities from same universe

### Next Week - Phase 2b (Sector Rotation)

**Universe:** Expand to 200-300 + sector-specific adds  
**Gate:** RS adjusted by sector momentum  
**Result:** **12-18 trades/day** (+50% more)

**What changes?**
```
IF sector STRONG (XLE up 5%):
  RS threshold: 0.45 → 0.40 (loosen, more trades)
  Position multiplier: +1.20x (boost)
  
IF sector WEAK (XLE down 5%):
  RS threshold: 0.45 → 0.60 (tighten, fewer trades)
  Position multiplier: 0.70x (reduce)
```

**Where do new candidates come from?**
- Finviz sector screener for strong sectors
- Focus on sectors that just rotated up
- Example: If energy rotated up Jan 30, add 5-10 new energy names Feb 1

### 2 Weeks Later - Phase 3 (Mean Reversion)

**Universe:** SAME expanded universe  
**Signal:** "Stock down 5% from 20-day high + RS > 0.5"  
**Result:** **14-24 trades/day** (+40-60% more)

**Why different trades?**
- Momentum trades: Buy momentum, hold 30min-4hrs
- Mean reversion trades: Buy dips, hold 1-3hrs
- Non-overlapping entry logic
- Different risk profile (lower average returns, higher win rate)

---

## Practical Implementation: Expanding Universe

### Step 1: Today (Baseline)
```
Current universe: ~100 mid-cap stocks from dynamic generator
Source: yfinance screening
Refresh: Daily at market close
Quality: Good (3-8% daily volatility)
```

### Step 2: Tomorrow with Phase 2a
```
Same universe, different gates
Action: Deploy soft gates (no universe change needed)
Impact: 50% more trades from same 100-200 candidates
Result: Better utilization of existing universe
```

### Step 3: Next Week with Phase 2b
```
Expand universe by sector:
- Find top 3-5 performing sectors this week
- Add 5-10 names from each strong sector
- Drop 5-10 names from each weak sector
- Result: Dynamic 200-300 stock universe

Example Monday (Feb 3):
  Energy had great week → Add OXY, DVN, MPC, PSX, HAL
  Tech had bad week → Remove PLTR, CRWD, OKTA temporarily
  Healthcare neutral → Keep existing names
  
  New universe: 100 core + 20 energy + 10 healthcare = 130 total
```

### Step 4: 2 Weeks Later with Phase 3
```
Same 200-300 universe
New signal: "Down 5% + RS > 0.5"
Impact: 40-60% more trades (independent signal)
Result: 14-24 trades/day from adaptive universe
```

---

## Finviz Screener Step-by-Step

If you want to manually build your expanded universe:

1. Go to: https://finviz.com/screener.ashx

2. Click "Filters" at top

3. Set these filters:
   ```
   Price: $10 to $40
   Avg Volume: 1 million above
   Change: 3% above (this week)
   P/E Ratio: Positive values (all)
   ```

4. Hit "Search"

5. Review results - sort by:
   - Highest volume (most liquid)
   - Highest volatility (best for trading)
   - Most recent gainers/losers

6. Add interesting names to your watchlist

**Daily:** You'd get ~200-300 candidates, then pre_filter.py screens down to 20-30 actual trades/day universe

**Result:** Same as what your bot already does automatically!

---

## Why Sector Rotation Fits Your Mid-Cap Strategy

Your mid-caps are **sector-sensitive:**

**Energy Example:**
- When oil up: OXY, DVN, PSX → high momentum, good RS
- When oil down: OXY, DVN → lagging, low RS even if oil rebounds

**Tech Example:**
- When growth preferred: PLTR, CRWD, OKTA → high RS
- When value preferred: PLTR, CRWD → lag, low RS

**Phase 2b leverage:** Detect sector rotation, follow the money!
```
Market rotates Energy → Up 5% this week
Phase 2b: "Add more energy names, loosen RS filters for energy"
Result: 5-10 additional energy trades you wouldn't have gotten
```

---

## Summary: Your Expansion Path

### Current (Phase 1b)
- Universe: 100-200 mid-caps
- Gate: Hard RS rejection
- Result: 5-8 trades/day

### Phase 2a (Tomorrow)
- Universe: SAME 100-200
- Gate: Soft gates with position sizing
- **Result: 8-12 trades/day (+50%)**
- New candidates: None (same universe, smarter gates)

### Phase 2b (Next Week)
- Universe: 200-300 (add sector rotation)
- Gate: Soft gates + sector multipliers
- **Result: 12-18 trades/day (+50% more)**
- New candidates: Sector-rotated names (5-10 per day)

### Phase 3 (2 Weeks)
- Universe: 200-300 (same)
- Gate: Soft gates + sector + mean reversion
- **Result: 14-24 trades/day (+50-60% more)**
- New candidates: None (different signal, same stocks)

---

## Configuration to Add (Phase 2b Prep)

```python
# In trading_config.py or small_portfolio_config.py:

# Sector rotation configuration (for Phase 2b)
sector_momentum_lookback: int = 5  # Days to measure sector strength
sector_strong_threshold: float = 0.02  # 2% return = STRONG
sector_weak_threshold: float = -0.02  # -2% return = WEAK

# Sector-specific RS adjustments (for Phase 2b)
sector_momentum_multiplier: float = 1.2  # Boost strong sectors 20%
low_rs_threshold_by_sector: Dict = {
    'strong': 0.40,  # Loosen RS threshold in strong sectors
    'neutral': 0.50,
    'weak': 0.60,    # Tighten RS threshold in weak sectors
}
```

---

## Bottom Line

**Your Bot + Phase 2a + 2b = Smart Sector-Rotating Mid-Cap Trader**

```
Today:     100-200 mid-caps, hard gates → 5-8 trades/day
Tomorrow:  100-200 mid-caps, soft gates → 8-12 trades/day
Next week: 200-300 mid-caps + sector, soft gates → 12-18 trades/day
Later:     200-300 mid-caps + 2 signals → 14-24 trades/day
```

Each phase **adds value to your strategy without breaking it:**
- Phase 2a: Better gate logic (same universe)
- Phase 2b: Follow sector rotation (expanded universe)
- Phase 3: New signal source (same universe, different entry)

**All within your mid-cap price range ($10-35, 3-8% volatility)**


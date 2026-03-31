# Signal Selection Process - Complete Walkthrough

## Overview
This document explains how your trading bot selects which stocks to trade each day.

---

## 📅 **What Happened Today (Oct 21, 4:00 PM)**

### Timeline

**4:00:59 PM** - Market close triggers post-market watchlist refresh:

```
🌙 Post-market: running watchlist refresh ONLY (NO TRADES)
🤖 Running end-of-day self-monitoring...
📋 Post-market: Refreshing watchlist for next trading day (NO TRADES)
💰 Portfolio updated: $966,233 → $966,056
🎯 Daily pool: $579,633, Daily loss limit: $1,932
```

**4:01:30 PM** - PreFilter analysis completes:

```
✅ Using PreFilter universe with top-up: 8 prefiltered + 22 top-up -> 30 total
🧭 Prepared trading universe for tomorrow: 30 symbols
✅ Watchlist refresh complete - ready for tomorrow's trading
🛌 Sleeping until premarket window (1003.5 min)
```

---

## 🔬 **How PreFilter Works**

The **PreFilter** module is your bot's stock screening engine. It analyzes ~60 candidate stocks and applies multiple filters to find the best D+1 swing trade candidates.

### Step 1: Candidate Pool

The bot starts with this pool of 60 stocks:
```
AAPL, MSFT, GOOGL, AMZN, TSLA, NVDA, META, NFLX, AMD, AVGO,
INTC, IBM, ORCL, CRM, ADBE, CSCO, QCOM, SHOP, UBER, LYFT,
DIS, WMT, XOM, CVX, BA, CAT, KO, PEP, JNJ, PFE, BAC, JPM, GS,
V, MA, HD, UNH, MCD, NKE, ABBV, TMO, ACN, TXN, LLY, COST,
HON, UPS, BMY, SBUX, MDT, GILD, MMM, GE, F, GM, T, VZ
```

### Step 2: Liquidity Filters

**Removes illiquid stocks:**
- Minimum daily dollar volume: **$10 million**
- Minimum average volume: **50,000 shares/day**
- Price range: **$20 - $500**

**Why?** Ensures you can enter and exit positions quickly without slippage.

### Step 3: Volatility Filters

**Finds "sweet spot" movers:**
- Minimum ATR (Average True Range): **2% daily**
- Maximum ATR: **8% daily**

**Why?** 
- Too low volatility = not enough profit potential
- Too high volatility = unpredictable, risky moves
- 2-8% range = predictable daily swings perfect for D+1 strategy

### Step 4: Momentum Filters

**Identifies trending stocks:**
- Minimum momentum: **3% recent move**
- Maximum momentum: **20% recent move**
- Volume surge: **1.5x average volume**

**Why?**
- 3%+ momentum = strong trend in place
- Volume surge = institutional buying/selling
- Caps at 20% to avoid parabolic, unsustainable moves

### Step 5: Composite Scoring

**Ranks stocks by this formula:**
```
Score = (2.0 × Breakout) + (1.5 × Momentum) + (1.0 × Volatility) + (0.5 × Liquidity)
```

**Breakout** (2.0 weight) - Highest priority
- Is price breaking above recent resistance?
- Strong breakouts = continuation potential

**Momentum** (1.5 weight) - Second priority
- How strong is the current trend?
- Strong momentum = follow-through next day

**Volatility** (1.0 weight) - Third priority
- Is the stock in the "sweet spot" range?
- Moderate volatility = predictable moves

**Liquidity** (0.5 weight) - Tie-breaker
- Can we enter/exit easily?
- High liquidity = low execution risk

### Step 6: Gap-Prone Detection (NEW - Oct 2025)

**Identifies stocks that gap frequently:**
- Gap frequency: **30%+ of days** have 1%+ gaps
- Average gap size: **>1.5%**
- Directional bias: **20%+ consistency** (gaps in same direction)

**Why?** 
- Gap-prone stocks are PERFECT for D+1 strategy
- Overnight gaps create immediate profit opportunity
- Enter during day, capture gap next morning

---

## 📊 **Today's PreFilter Results (4:01 PM)**

### Top 8 Stocks Selected:

Based on earlier runs, the PreFilter consistently selects these top performers:

1. **NVDA** - Nvidia (AI leader, high volatility, gap-prone)
2. **AAPL** - Apple (high liquidity, steady momentum)
3. **INTC** - Intel (moderate volatility, value play)
4. **F** - Ford (high volume, cyclical mover)
5. **T** - AT&T (dividend stock, volatility)
6. **TSLA** - Tesla (ultimate gap-prone stock)
7. **AMD** - Advanced Micro Devices (tech momentum)
8. **AMZN** - Amazon (e-commerce leader)

Plus **22 backup candidates** to reach 30 total:
```
PFE, ORCL, VZ, BAC, GOOGL, KO, AVGO, MSFT, CSCO, BMY,
UBER, WMT, LYFT, GM, CRM, NKE, XOM, META, QCOM, GILD,
DIS, JNJ (and more...)
```

### Why These 30?

- **Top 8**: Highest composite scores (best breakout + momentum + volatility combo)
- **Next 22**: Backup candidates from static config to ensure coverage
- **Total 30**: Optimized universe size for signal generation

**Note:** The exact top 8 may vary slightly day-to-day based on:
- Recent price breakouts
- Volume surges
- Momentum shifts
- Market regime changes

---

## 🌅 **Tomorrow Morning's Process (Oct 22)**

### 9:00 AM - Premarket Analysis

**Bot wakes up and runs:**

1. **Portfolio summary** - Check current positions
2. **Fresh gap scanner** - Analyze the 30 prepared symbols for:
   - Pre-market price gaps
   - Pre-market volume
   - Gap quality (not just noise)
3. **Create gap candidates list** - Top stocks showing strong overnight movement

### 9:30 AM - Market Opens

Bot waits 15 minutes for market to stabilize (avoid opening chaos).

### 9:45 AM - Entry Window Opens

**Critical sequence:**

1. **Check D+1 positions** (your current 8 positions from yesterday)
2. **If today >= exit_date:**
   - Execute SELL market orders
   - Close all D+1 positions
   - Capture P&L

**For your current positions (entered Oct 21):**
```
✅ All 8 will exit tomorrow at 9:45 AM:
   AAPL, AMD, CRM, GOOGL, NFLX, QCOM, SHOP, TSLA
   Entry: Oct 21, Exit: Oct 22 (D+1 rule)
```

### 9:45-10:00 AM - Signal Generation

**After exits complete, bot generates NEW signals:**

1. **Universe:** The 30 symbols prepared last night
2. **Focus:** Morning gap candidates (fresh data from gap scanner)
3. **Analysis:** For each symbol, calculate:
   - **Technical indicators:**
     - RSI (Relative Strength Index)
     - MACD (Moving Average Convergence Divergence)
     - Bollinger Bands
     - Support/Resistance levels
   - **ML confidence scores:**
     - Pattern recognition (breakouts, reversals)
     - Historical success rate
     - Regime-adjusted predictions
   - **Volume analysis:**
     - Is volume surging?
     - Is buying pressure strong?
   - **Intraday momentum:**
     - Price action in first 15 minutes
     - Trend strength

4. **Ranking:** Sort all signals by composite confidence score
5. **Selection:** Pick top **8 signals** that pass ALL criteria:
   - High confidence (>70%)
   - Strong momentum
   - Healthy volume
   - Clear trend direction
   - Pass risk filters

### 10:00-10:05 AM - Execution

**Bot places orders:**

1. Submit **8 BUY market orders** for selected symbols
2. Monitor order fills
3. Create position trackers:
   - Entry date: **Oct 22**
   - Exit date: **Oct 23** (D+1)
   - Entry price: Fill price
   - Position size: Risk-adjusted ($5,000-6,000 per position)

### Result

- **8 new positions** for tomorrow's D+1 exit (Oct 23)
- **Full cycle complete:** Exit old → Enter new → Repeat

---

## 🎯 **Key Insights**

### 1. Two-Stage Selection

**Stage 1 (End-of-Day):**
- PreFilter narrows 60 stocks → 30 candidates
- Based on fundamental criteria (liquidity, volatility, momentum)
- Prepares watchlist for next day

**Stage 2 (Morning):**
- Signal generator narrows 30 candidates → 8 trades
- Based on technical + ML analysis of fresh data
- Executes actual trades

### 2. Why This Approach Works

**PreFilter advantages:**
- Removes garbage stocks upfront
- Focuses analysis on quality candidates only
- Saves API calls (don't analyze 1000s of stocks)
- Consistent criteria across all market conditions

**Signal generator advantages:**
- Uses fresh morning data (gaps, momentum)
- Applies sophisticated technical analysis
- ML pattern recognition
- Risk-adjusted position sizing

**Combined power:**
- Quality inputs (PreFilter) → Quality outputs (Signals)
- Efficient use of resources
- Higher win rate from better stock selection

### 3. What Makes a Good D+1 Candidate?

**Perfect D+1 stock has:**
1. ✅ High liquidity (easy entry/exit)
2. ✅ Moderate volatility (2-8% daily swings)
3. ✅ Strong momentum (trending direction)
4. ✅ Volume surge (institutional interest)
5. ✅ Gap-prone behavior (overnight edges)
6. ✅ Technical breakout (continuation setup)

**Examples from today's positions:**
- **TSLA:** Gap-prone king, high volatility, momentum beast
- **AMD:** Tech momentum, moderate volatility, liquid
- **SHOP:** E-commerce growth, gap-prone, trending
- **GOOGL:** Mega-cap liquidity, steady momentum

### 4. Tomorrow's Expected Flow

**9:45 AM:**
```
Selling 8 positions (D+1 exits):
AAPL: 22 shares @ market
AMD: 24 shares @ market
CRM: 23 shares @ market
GOOGL: 23 shares @ market
NFLX: 4 shares @ market
QCOM: 35 shares @ market
SHOP: 36 shares @ market
TSLA: 13 shares @ market
```

**9:50-10:00 AM:**
```
Buying 8 NEW positions:
[Will be determined by morning gap scan + signal generation]
Likely candidates from top PreFilter picks:
- NVDA (if gapping up with volume)
- TSLA (if strong momentum continues)
- AMD (if tech sector strong)
- AAPL (if showing breakout)
- + 4 more from the 30-symbol universe
```

**5:00 PM (when you get home):**
```
Expected result:
✅ 8 positions closed (Oct 21 → Oct 22 D+1)
✅ P&L captured from yesterday's trades
✅ 8 new positions entered for tomorrow (Oct 22 → Oct 23 D+1)
✅ Bot prepared for next day's cycle
```

---

## 🔍 **Monitoring Tomorrow**

### What to Check

**1. Morning Exits (9:45 AM):**
- Did all 8 sell orders fill?
- What was the P&L on each position?
- Total P&L for the cycle?

**2. Morning Entries (10:00 AM):**
- Which 8 symbols were selected?
- What were the entry prices?
- Position sizes correct (~$5-6k each)?

**3. Position Tracking:**
- Do all 8 new positions show:
  - Entry date: Oct 22
  - Exit date: Oct 23
  - Status: Entered

**4. End-of-Day (4:00 PM):**
- Did post-market watchlist refresh run?
- Was PreFilter universe prepared for Oct 23?

### Log File Locations

```bash
# Main trading log
tail -f logs/short_cycle_trader.log

# Check for exits
grep "D+1 exit" logs/short_cycle_trader.log

# Check for entries  
grep "Submitting order" logs/short_cycle_trader.log

# Check PreFilter results
grep "PreFilter universe" logs/short_cycle_trader.log
```

---

## ✅ **Verification Checklist**

Before you leave today:

- [x] D+1 logic tested (test_d1_logic.py passed)
- [x] 8 positions exist on Alpaca
- [x] All positions have entry_date = Oct 21, exit_date = Oct 22
- [x] PreFilter ran at 4:00 PM (30 symbols prepared)
- [x] Bot sleeping until 9:00 AM premarket

Tomorrow at 5:00 PM, verify:

- [ ] 8 Oct 21 positions closed at 9:45 AM
- [ ] P&L captured and logged
- [ ] 8 NEW positions entered ~10:00 AM
- [ ] New positions have entry_date = Oct 22, exit_date = Oct 23
- [ ] PreFilter ran at 4:00 PM for Oct 23

---

## 📚 **Additional Resources**

### Code References

- **PreFilter logic:** `pre_filter.py` lines 479-700
- **Signal generation:** `signal_generator.py` lines 342-400
- **D+1 exit logic:** `traders/short_cycle_trader.py` lines 1411-1480
- **Universe selection:** `traders/short_cycle_trader.py` lines 2236-2320
- **Post-market refresh:** `traders/short_cycle_trader.py` lines 1151-1170

### Config Files

- **Universe config:** `config/short_cycle_universe.json`
- **PreFilter settings:** `pre_filter.py` lines 120-135
- **Risk limits:** `config.py`

---

**Last Updated:** Oct 21, 2025, 4:30 PM  
**Next Review:** Oct 22, 2025, 5:00 PM (verify cycle completion)

# BACKTEST RESULTS - Filter Comparison
## November 14, 2025

**Stocks Tested:** JBLU, AAL, CCL, RCL, F, GEVO, PLUG, FCEL, SBUX, SIRI, CAKE  
**Years:** 2017, 2018, 2020, 2021, 2022 (5 years)  
**Data Source:** yFinance (daily bars)  
**Strategy:** D+1 exit (hold 1 day), $10,000 starting capital  

---

## CRITICAL FINDING: Tighter Filters UNDERPERFORMED

### Baseline (Current: 3.5% momentum, 1.0x volume)
- **Total Return:** +34.61% ✅
- **Total Trades:** 843
- **Win Rate:** 45.2%
- **Avg Win:** $+163.81
- **Avg Loss:** $-132.18
- **Win/Loss Ratio:** 1.24:1
- **Sharpe Ratio:** 0.30

### Improved (Proposed: 5.0% momentum, 1.5x volume)
- **Total Return:** -9.09% ❌ (LOSS!)
- **Total Trades:** 319 (-62% fewer)
- **Win Rate:** 44.5%
- **Avg Win:** $+187.10
- **Avg Loss:** $-162.59
- **Win/Loss Ratio:** 1.15:1
- **Sharpe Ratio:** -0.16 (NEGATIVE)

### Performance Comparison

| Metric | Baseline | Improved | Change |
|--------|----------|----------|--------|
| **Total Return** | **+34.61%** | **-9.09%** | **-43.7%** ⚠️ |
| Win Rate | 45.2% | 44.5% | -0.7% |
| Trade Count | 843 | 319 | -62.2% |
| Avg Win | $163.81 | $187.10 | +$23.29 |
| Avg Loss | $132.18 | $162.59 | -$30.41 (worse) |
| Win/Loss Ratio | 1.24:1 | 1.15:1 | -0.09 |
| Sharpe Ratio | 0.30 | -0.16 | -0.45 |

---

## WHY DID TIGHTER FILTERS FAIL?

### Theory #1: Entry Timing Problem ⏱️
- **5% momentum = already overextended**
  - Entering after stock ran up 5%+ in 4 days
  - Next day (D+1 exit) often catches the reversal
  - Buying high, selling low next day
  
- **3.5% momentum = catches earlier move**
  - Enters while stock still has room to run
  - D+1 exit captures continued momentum
  - More favorable entry/exit timing

### Theory #2: Volume Filter Backfires 📊
- **1.5x volume surge = extreme moves**
  - Often signals exhaustion/capitulation
  - High volume spikes = reversals, not trends
  - Mean reversion after volume climax
  
- **1.0x volume = healthier setups**
  - Moderate volume = sustainable trends
  - Allows more "normal" momentum plays
  - Less prone to next-day reversals

### Theory #3: Sample Size Problem 📉
- **Baseline:** 843 trades (law of large numbers works)
- **Improved:** 319 trades (-62% reduction)
  - Smaller sample = higher variance
  - Missing profitable "medium quality" setups
  - Over-filtering eliminates edge

### Theory #4: D+1 Exit Amplifies Timing 🎯
- **Strategy exits next day regardless of price**
- **Tighter entry + forced D+1 exit = bad combo:**
  - Enter at 5%+ momentum (late)
  - Exit next day (no time for continuation)
  - Catches reversals after exhaustion moves
  
- **Looser entry benefits from D+1:**
  - Enter earlier in move (3.5% momentum)
  - One day gives time for follow-through
  - Better entry/exit sequencing

---

## RECONCILING WITH NOV 2025 WEEK

### The Paradox:
**Nov 11-14 analysis showed:**
- RIVN #2 (3.71% momentum) → Lost -$21.23 (-11%)
- Suggested tighter filters would help
- **But backtest shows opposite!**

### Possible Explanations:

**1. Market Regime Difference**
- Nov 2025 market != 2017-2022 market
- Current volatility may favor tighter filters
- Historical data from different conditions

**2. Nov Week Was Anomaly**
- Thursday Nov 14 was exceptionally bad (-$25.12)
- 5/8 losses hit emergency stops (unusual)
- One bad day doesn't invalidate 5-year backtest

**3. Both Can Be True**
- 3.5% momentum works better historically
- BUT some 3.5-4% entries (like RIVN #2) still fail
- Need different solution (not just threshold)

**4. Wrong Root Cause**
- Problem may not be momentum threshold
- Could be:
  - Exit strategy (D+1 too rigid)
  - Position sizing (equal weight vs. risk-adjusted)
  - Market conditions (trending vs. choppy)
  - Stock selection (some stocks shouldn't be traded)

---

## RECOMMENDATIONS

### ❌ DO NOT Implement 5% + 1.5x Volume
**Reason:** Historical backtest shows -43% performance degradation

### ✅ KEEP 3.5% Momentum Filter (For Now)
**Reason:** +35% return over 5 years, 45% win rate, positive Sharpe

### 🔍 INVESTIGATE Further

**Option 1: Test Intermediate Thresholds**
```
Try: 4.0% or 4.25% momentum (between 3.5% and 5.0%)
Try: 1.25x or 1.3x volume (between 1.0x and 1.5x)
Hypothesis: Sweet spot may be between baseline and "improved"
```

**Option 2: Improve Exit Strategy**
```
Problem: D+1 exit forces exit regardless of price action
Solutions:
  - Hold 2-3 days instead of 1?
  - Use trailing stop instead of time-based exit?
  - Exit on first profitable day vs. fixed D+1?
```

**Option 3: Backtest Recent Data**
```
Problem: 2017-2022 may not represent current market
Solutions:
  - Test 2023-2024 (more recent regime)
  - Test last 6 months (current conditions)
  - Weight recent years more heavily
```

**Option 4: Stock-Specific Filters**
```
Problem: Not all stocks behave the same
Solutions:
  - Avoid stocks with high reversal tendency
  - Identify "good momentum" vs. "bad momentum" stocks
  - Blacklist underperformers (like RIVN?)
```

**Option 5: Add Exit Filters**
```
Problem: Entering good but exiting bad
Solutions:
  - Don't enter if next day is Friday (weekend risk)
  - Don't enter if stock gapped up >3% (exhaustion)
  - Add momentum confirmation on exit day
```

---

## NEXT ACTIONS

### IMMEDIATE (Today/Tomorrow):
1. ✅ **DO NOT deploy 5% + 1.5x volume filters** (backtest failed)
2. ✅ **KEEP current 3.5% momentum filter** (proven edge)
3. 📊 **Review Nov 14 trades individually:**
   - Was RIVN #2 an outlier or a pattern?
   - What made that day so bad (-$25.12)?
   - Were there common factors in the 5 emergency stops?

### SHORT-TERM (This Week):
4. 🔬 **Run additional backtests:**
   - Test 4.0% and 4.25% momentum (intermediate)
   - Test 1.25x volume (moderate)
   - Test 2023-2024 data (recent market)

5. 📈 **Analyze exit strategy:**
   - Compare D+1 vs. D+2 vs. D+3 hold periods
   - Test profit-target vs. time-based exits
   - Consider trailing stops

6. 🎯 **Identify problem stocks:**
   - Which stocks had worst performance?
   - Are there stocks to avoid entirely?
   - Can we filter by sector or characteristics?

### MEDIUM-TERM (Next 1-2 Weeks):
7. 🧪 **Paper trade with current filters:**
   - Continue Nov 15+ with 3.5% momentum
   - Monitor for another bad day like Nov 14
   - Gather more live data

8. 🔄 **Iterate based on findings:**
   - If intermediate thresholds work better, deploy
   - If exit strategy improves, implement
   - If stock filtering helps, blacklist bad actors

9. 📝 **Document learnings:**
   - What makes a good vs. bad entry?
   - When does D+1 strategy fail?
   - How to identify reversal setups?

---

## CONCLUSION

**The Data Has Spoken:**

🚨 **Backtest Verdict:** Tighter filters (5% + 1.5x volume) **FAILED** (-9% return vs. +35% baseline)

🎯 **Action:** **KEEP current 3.5% momentum filter**, investigate other improvements

🔬 **Next Steps:** Test intermediate thresholds, improve exit strategy, analyze recent data

💡 **Key Insight:** The problem may not be entry filters but:
- Exit timing (D+1 too rigid)
- Stock selection (some stocks unsuitable)
- Market regime (Nov 2025 different from 2017-2022)

**Bottom Line:** Don't change filters based on one bad week. The 5-year backtest carries more weight than 4 days of trading. Focus on exit strategy and stock selection instead.

---

**Report Generated:** November 14, 2025, 6:47 PM  
**Backtest File:** `backtest/results/backtest_summary_20251114_184632.json`  
**Status:** Analysis complete, awaiting next steps

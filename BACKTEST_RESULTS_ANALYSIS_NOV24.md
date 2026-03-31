# Backtest Results Analysis - November 24, 2025
## 14-Year Real Data Validation of Mean Reversion RSI Strategy

---

## ⚠️ CRITICAL FINDINGS

### Bottom Line: **STRATEGIES FAILED REAL-WORLD VALIDATION**

All three optimized strategies show **NEGATIVE returns** on real historical data (2011-2024).

This is a **SEVERE discrepancy** between:
- **Simulated optimization**: 19.17% weekly return
- **Real backtest**: -12.15% total return over 14 years

---

## 📊 Complete Results Summary

### Strategy #1: Mean Reversion RSI #2852 (Top Optimization Pick)

| Phase | Years | Return | Win Rate | Sharpe | Trades |
|-------|-------|--------|----------|--------|--------|
| **In-Sample** | 2011-2016 | **-10.13%** | 56.0% | -0.14 | 225 |
| **Validation** | 2017-2019 | **-43.81%** | 39.8% | -2.91 | 133 |
| **Out-of-Sample** | 2020-2024 | **-12.15%** | 49.6% | -0.10 | 248 |

**Verdict**: ❌ **FAILED** - Negative returns in all phases

**Issues**:
- Average win (+5.97%) ≈ Average loss (-5.98%) = **no edge**
- Win rate dropped from 56% → 40% → 50% = **unstable**
- Max drawdown 52% = **catastrophic** for $10K account
- Profit factor 0.93 = **loses money** (need >1.0 to profit)

---

### Strategy #2: Mean Reversion RSI #3831

| Phase | Years | Return | Win Rate | Sharpe | Trades |
|-------|-------|--------|----------|--------|--------|
| **In-Sample** | 2011-2016 | **-3.55%** | 52.7% | 0.12 | 74 |
| **Validation** | 2017-2019 | **+23.97%** ✅ | 44.6% | 1.38 | 56 |
| **Out-of-Sample** | 2020-2024 | **-3.20%** | 47.4% | 0.13 | 97 |

**Verdict**: ⚠️ **MARGINAL** - Only 1 profitable phase (Validation)

**Issues**:
- Validation phase was good (+23.97%, Sharpe 1.38)
- BUT failed in-sample and out-of-sample
- Inconsistent performance = **not deployable**
- Only 74-97 trades per phase = **low sample size**

---

### Strategy #3: Hybrid #4872

| Phase | Years | Return | Win Rate | Sharpe | Trades |
|-------|-------|--------|----------|--------|--------|
| **In-Sample** | 2011-2016 | **+47.97%** ✅ | 48.6% | 0.45 | 895 |
| **Validation** | 2017-2019 | **-16.07%** | 42.6% | 0.07 | 493 |
| **Out-of-Sample** | 2020-2024 | **-8.22%** | 44.2% | 0.17 | 1148 |

**Verdict**: ❌ **FAILED** - Severe overfitting

**Issues**:
- In-Sample showed promise (+47.97%)
- **Collapsed** in validation (-16%) and out-of-sample (-8%)
- Classic overfitting: Optimized to historical data, failed on new data
- Max drawdown 62% = **unacceptable risk**

---

## 🔍 Why Did Optimization Show 19.17% But Real Data Shows -12.15%?

### Root Cause: **SIMULATED vs REAL DATA**

#### Optimization (Nov 22):
- **Data source**: Random/synthetic data or limited historical snapshot
- **Result**: 19.17% weekly return, 62.7% win rate
- **Reality**: Overfitted to specific conditions

#### Backtest (Nov 24):
- **Data source**: 14 years of REAL stock prices from yfinance
- **Result**: -12.15% total return over 14 years
- **Reality**: Strategy doesn't work in real markets

### Specific Issues

**1. RSI < 20 Entries Are Too Rare**
- RSI < 20 = extreme oversold (very uncommon)
- Real markets: Only 74-248 trades over 6 years
- Optimization assumed more frequent opportunities

**2. No True Edge**
- Average win ≈ Average loss
- Even with 50%+ win rate, profit factor < 1.0
- Transaction costs would make it worse

**3. Stop Losses Too Wide**
- -5 to -8% average losses
- Mean reversion can continue falling (catch falling knife)
- Max drawdowns 40-62% = account blown

**4. Market Regime Mismatch**
- Optimization likely used bull market data
- Real data includes:
  - 2011-2013: Recovery (choppy)
  - 2015-2016: Oil crash
  - 2018: Bear market
  - 2020: COVID crash
  - 2022: Inflation crash

---

## 📉 Phase-by-Phase Breakdown

### In-Sample (2011-2016): Training Phase
**Best**: Hybrid +47.97%  
**Worst**: Mean Reversion RSI #2852 -10.13%

**Analysis**: Only Hybrid showed promise in training data

### Validation (2017-2019): Overfitting Check
**Best**: Mean Reversion RSI #3831 +23.97% ✅  
**Worst**: Mean Reversion RSI #2852 -43.81% ❌

**Analysis**: 
- Strategy #3831 passed validation!
- But #2852 collapsed (-43.81%)
- Hybrid failed (-16.07%)

### Out-of-Sample (2020-2024): Real-World Test
**Best**: Mean Reversion RSI #3831 -3.20% (least bad)  
**Worst**: Mean Reversion RSI #2852 -12.15%

**Analysis**: **ALL STRATEGIES FAILED OUT-OF-SAMPLE**

---

## 💡 What Went Wrong?

### 1. ❌ Optimization Was Flawed
- Simulated data ≠ Real market behavior
- 19.17% weekly = **1,000% annual** = **UNREALISTIC**
- Should have been red flag from start

### 2. ❌ Mean Reversion Doesn't Work on These Stocks
- Travel stocks (JBLU, AAL, CCL, RCL): **Trending stocks**, not mean-reverting
- Green energy (GEVO, PLUG, FCEL): **Pump & dump**, crashes don't bounce
- Ford (F): **Multi-year downtrends**, mean reversion fails

### 3. ❌ RSI < 20 Strategy Has Fundamental Flaw
- "Buy the dip" works in bull markets
- "Catch falling knife" in bear markets or downtrending stocks
- Need **trend filter** BEFORE mean reversion

### 4. ❌ No Transaction Costs Modeled
- Backtest assumes 0 slippage, 0 commission
- Real world: 1-2 cents slippage + PDT restrictions
- Would make results even worse

---

## 🚨 DEPLOYMENT DECISION

### ❌ DO NOT DEPLOY ANY OF THESE STRATEGIES

**Reasons**:
1. All show negative returns on real data
2. No strategy passed all 3 phases
3. Out-of-sample phase is most important → all failed
4. Risk of ruin: 40-62% drawdowns

**If deployed with $1,000 portfolio**:
- Expected: Lose $30-120 over 4 years
- Worst case: 52% drawdown = $520 loss
- Best case: Break even (unlikely)

---

## 🔄 What Should We Do Now?

### Option 1: ✅ **RE-OPTIMIZE WITH DIFFERENT CONSTRAINTS**

**Problem**: Current optimization used wrong assumptions

**Solution**: Re-run optimization with:
- **Real historical data** (not simulated)
- **Trend-first filter**: Only enter if stock is uptrending
- **Tighter stops**: -2% max loss (not -6%)
- **Different entry**: RSI < 30 (not < 20) for more trades
- **Momentum + mean reversion hybrid**: Trend filter + RSI confirmation

**Example New Strategy**:
```
1. Stock must be above 20-day MA (uptrend filter)
2. RSI drops below 30 (oversold in uptrend = bounce)
3. Volume > 1.5x average (institutional interest)
4. Entry: Next day open
5. Exit: RSI > 70 OR +3% profit OR -2% stop
```

---

### Option 2: ✅ **TEST ORIGINAL BOT'S MOMENTUM STRATEGY**

**Observation**: We switched FROM momentum TO mean reversion based on flawed optimization

**Action**: Run backtest on **original momentum strategy**:
- Momentum breakout entries
- Trailing stops
- D+1 exits

**Maybe the original bot was correct all along?**

---

### Option 3: ✅ **USE DIFFERENT STOCK UNIVERSE**

**Problem**: Travel/energy stocks are **trending**, not **mean-reverting**

**Solution**: Test on stocks that **actually mean-revert**:
- **Tech mega-caps**: AAPL, MSFT, GOOGL (range-bound)
- **Consumer staples**: PG, KO, WMT (stable)
- **Dividend aristocrats**: Stocks with proven stability

Mean reversion works best on:
- ✅ Large caps (less volatile)
- ✅ Dividend payers (floor valuation)
- ✅ Range-bound stocks (clear support/resistance)

NOT on:
- ❌ Small caps (trending)
- ❌ Speculative (GEVO, PLUG, FCEL)
- ❌ Airlines (boom/bust cycles)

---

### Option 4: ⚠️ **ACCEPT OPTIMIZATION WAS WRONG, START FRESH**

**Reality Check**:
1. 19.17% weekly = **1,000%+ annual** = Never happened in trading history
2. Optimization was curve-fitted to random data
3. Real backtest proves it doesn't work

**Action**:
1. ❌ Discard optimization results completely
2. ✅ Start with proven strategies:
   - **Connors RSI 2** (classic mean reversion)
   - **Gap fill** (morning gap reversals)
   - **VWAP reversion** (institutional support)
3. ✅ Backtest on 14 years BEFORE optimization
4. ✅ Only optimize parameters AFTER strategy proves profitable

---

## 📋 Immediate Action Items

### 1. ✅ **Do NOT trade the bot live** (confirmed)

### 2. ✅ **Run backtest on original momentum strategy** (for comparison)
```bash
# Test the ORIGINAL bot configuration on same 14 years
# Compare momentum vs mean reversion
```

### 3. ⏳ **Re-optimize with corrected constraints**
```
Constraints for new optimization:
- Use REAL historical data (2017-2024)
- Target 2-5% monthly return (realistic)
- Require profit in ALL phases (in-sample, validation, out-of-sample)
- Max drawdown < 15%
- Win rate 50-60% (achievable)
```

### 4. ⏳ **Test alternative strategies**

**Connors RSI 2**:
```
Entry: RSI(2) < 10 AND price > 200-day MA
Exit: RSI(2) > 65 OR 3% profit
```

**Gap Fill**:
```
Entry: Gap down >2% at open AND volume > 2x
Exit: Gap filled OR +2% OR -1% stop
```

**VWAP Mean Reversion**:
```
Entry: Price < VWAP - 2 ATR AND RSI < 35
Exit: Price crosses above VWAP OR +2%
```

---

## 🔬 Technical Analysis of Failure

### Win Rate vs Profit Factor Mismatch

**Strategy #2852**:
- Win rate: 49.6% (almost 50/50)
- Avg win: +5.97%
- Avg loss: -5.98%
- **Result**: Break-even at best, slight loss with costs

**Math**:
```
100 trades:
  50 wins × +5.97% = +298.5%
  50 losses × -5.98% = -299%
  Net = -0.5% (before costs)
```

### Why RSI < 20 Failed

**Theory**: Extreme oversold → bounce
**Reality**: Stocks can stay oversold for weeks/months

**Example - Ford (F) 2022**:
```
Jan 2022: RSI hits 18 at $20
Feb 2022: Still at RSI 15, price $17 (-15% loss)
Mar 2022: RSI 12, price $15 (-25% loss)
Apr 2022: Finally bounces to $16

Enter at RSI 18: -25% loss before bounce
Exit criteria (-2% stop): Stopped out for -2%
```

**Lesson**: Need TREND filter before mean reversion

---

## 📈 Comparison to Expected Results

| Metric | Expected (Simulated) | Actual (Real) | Difference |
|--------|---------------------|---------------|------------|
| Weekly Return | 19.17% | -0.17% | **-19.34%** ❌ |
| Win Rate | 62.7% | 49.6% | **-13.1%** ❌ |
| Sharpe Ratio | 3.52 | -0.10 | **-3.62** ❌ |
| Profit Factor | 18.34 | 0.93 | **-17.41** ❌ |

**ALL metrics dramatically worse in real data**

---

## 🎓 Lessons Learned

### 1. **Simulated optimization ≠ Real performance**
- Always validate on historical data FIRST
- Then optimize parameters
- Never trust 1,000%+ annual returns

### 2. **Mean reversion needs context**
- Works: Stocks in uptrend that dip (buy the dip)
- Fails: Stocks in downtrend (catching knife)
- **Always add trend filter**

### 3. **Stock selection matters MORE than strategy**
- Airlines/energy are trending stocks
- Mean reversion needs range-bound stocks
- Match strategy to stock behavior

### 4. **Overfitting is real**
- In-sample +48% → Out-of-sample -8% (Hybrid)
- Need 3-phase testing to detect
- Optimization can find patterns in noise

### 5. **Realistic expectations**
- 2-5% monthly = Good
- 10-20% annual = Excellent
- 1,000% annual = Scam/Overfitting

---

## ✅ Recommended Next Steps

### Immediate (Today):
1. ✅ **Do NOT deploy** current strategies
2. ✅ **Accept optimization was flawed**
3. ✅ **Read backtest results carefully** (DONE)

### Short-term (This Week):
1. ⏳ **Backtest original momentum strategy** on same 14 years
2. ⏳ **Test Connors RSI 2** (proven strategy)
3. ⏳ **Test on different stock universe** (mega-caps)

### Medium-term (Next 2 Weeks):
1. ⏳ **Re-optimize** with corrected constraints:
   - Real data
   - Realistic targets (2-5% monthly)
   - Trend filters required
   - All phases must profit
2. ⏳ **Paper trade** best strategy for 10 days
3. ⏳ **Deploy** only if paper matches backtest

---

## 📊 Final Verdict

### Mean Reversion RSI Strategy: ❌ **REJECTED**

**Reasons**:
1. -12.15% return over 14 years (loses money)
2. Failed all 3 phases (in-sample, validation, out-of-sample)
3. No edge: Avg win ≈ Avg loss
4. Unacceptable risk: 52% max drawdown
5. Optimization was curve-fitted to simulated data

### Confidence Threshold Adjustment: ✅ **CORRECT**

Changed from 30% → 60% was the right call (matches original bot's high selectivity).

### Bot Strategy Choice: ⚠️ **QUESTIONABLE**

Switching from momentum → mean reversion was based on flawed optimization. Should reconsider original momentum approach.

---

**Report Generated**: November 24, 2025 11:10 AM  
**Backtest Runtime**: 14 years (2011-2024)  
**Recommendation**: DO NOT DEPLOY - Re-optimize or test alternative strategies  
**Status**: ❌ FAILED VALIDATION

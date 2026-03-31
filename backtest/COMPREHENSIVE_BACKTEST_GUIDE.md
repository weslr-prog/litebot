# Comprehensive 3-Phase Backtest Guide

## Overview

This backtest implements a rigorous 3-phase testing methodology to validate the top 3 strategies from optimization results against **14 years of real market data** (2011-2024).

### Test Phases

| Phase | Years | Purpose | Expected Result |
|-------|-------|---------|-----------------|
| **In-Sample** | 2011-2016 | Parameter validation | Confirms optimization parameters work on real data |
| **Validation** | 2017-2019 | Overfitting check | Should match in-sample within 20-30% |
| **Out-of-Sample** | 2020-2024 | Real-world test | Most recent market conditions (COVID, inflation, 2024) |

### Strategies Tested

Based on optimization results analysis:

1. **Mean Reversion RSI #2852** (Best Overall)
   - RSI(7) < 20 oversold entry
   - Exit: RSI > 50 (neutral) or 2% profit
   - Simulated: 19.17% weekly, 62.72% win rate

2. **Mean Reversion RSI #3831** (Runner-up)
   - RSI(21) < 25 oversold entry
   - Exit: RSI > 80 (overbought) or 3% profit
   - Simulated: 18.93% weekly, 61.17% win rate

3. **Hybrid #4872** (Best Hybrid)
   - Combines momentum + mean reversion
   - RSI(14) < 30 OR momentum >= 3%
   - Exit: 2.5% profit target
   - Simulated: 17.97% weekly, 59.99% win rate

## Quick Start

### Run Full Backtest

```bash
# Run comprehensive 3-phase backtest (all strategies, all phases)
python3 backtest/comprehensive_strategy_backtest.py
```

**Runtime:** ~15-30 minutes (downloads + caches 14 years of data for 11 symbols)

**Output:**
- Results saved to: `backtest/results/comprehensive/`
- Trade logs: `{strategy}_{phase}_trades_TIMESTAMP.csv`
- Summary report: `comprehensive_backtest_summary_TIMESTAMP.txt`

### What to Expect

**In-Sample (2011-2016):**
- Expected: 6-12% weekly return (vs 19% simulated)
- This phase had strong bull markets (2013-2016)
- Higher returns expected here

**Validation (2017-2019):**
- Expected: 5-10% weekly return
- Should be within 70-100% of in-sample
- If much lower, indicates overfitting

**Out-of-Sample (2020-2024):**
- Expected: 4-8% weekly return
- Most important phase (recent market)
- Includes COVID crash (2020), inflation (2022), 2024 volatility
- If >= 5% weekly here, strategy is robust

## Interpreting Results

### Success Criteria

✅ **PASS Criteria:**
- Out-of-Sample return >= 5% weekly
- Win rate >= 45% across all phases
- Sharpe ratio >= 1.5 in Out-of-Sample
- Out-of-Sample >= 50% of In-Sample return

⚠️ **CAUTION Criteria:**
- Out-of-Sample 3-5% weekly (marginal)
- Win rate 40-45% (risky)
- Sharpe ratio 1.0-1.5 (moderate risk-adjusted)
- Out-of-Sample 30-50% of In-Sample (some degradation)

❌ **FAIL Criteria:**
- Out-of-Sample < 3% weekly (not viable)
- Win rate < 40% (losing strategy)
- Sharpe ratio < 1.0 (poor risk-adjusted)
- Out-of-Sample < 30% of In-Sample (severe overfitting)

### Key Metrics

**Total Return:**
- Measures overall profitability
- Compare across phases for consistency

**Win Rate:**
- Should stay 45%+ across all phases
- Sharp drops indicate regime changes

**Sharpe Ratio:**
- Risk-adjusted returns
- Target: 1.5+ (good), 2.0+ (excellent)
- Below 1.0 = too volatile for returns

**Max Drawdown:**
- Worst peak-to-trough decline
- Target: < 15% for viable strategy
- > 25% = too risky

**Profit Factor:**
- Gross profit / gross loss
- Target: 2.0+ (good), 3.0+ (excellent)
- Below 1.5 = marginal edge

## Example Results Analysis

### Scenario 1: Strong Strategy
```
                                    In-Sample   Validation   Out-of-Sample
Mean Reversion RSI #2852               12.5%        10.2%            8.7%
Win Rate                               58.3%        55.1%           52.4%
Sharpe                                  2.45         2.12            1.87

✅ DECISION: DEPLOY
- Consistent performance across all phases
- Out-of-Sample 70% of In-Sample (expected degradation)
- Win rate stable, Sharpe strong
```

### Scenario 2: Overfit Strategy
```
                                    In-Sample   Validation   Out-of-Sample
Mean Reversion RSI #3831               15.2%         6.1%            2.3%
Win Rate                               62.5%        48.2%           38.7%
Sharpe                                  3.12         1.45            0.68

❌ DECISION: REJECT
- Severe degradation in Validation and Out-of-Sample
- Out-of-Sample only 15% of In-Sample (overfitting)
- Win rate collapsed, Sharpe below 1.0
```

### Scenario 3: Marginal Strategy
```
                                    In-Sample   Validation   Out-of-Sample
Hybrid #4872                            9.8%         7.2%            4.5%
Win Rate                               54.2%        51.3%           47.8%
Sharpe                                  1.95         1.68            1.22

⚠️ DECISION: PAPER TRADE FIRST
- Moderate performance, Out-of-Sample 46% of In-Sample
- Win rate acceptable but declining
- Sharpe marginal in Out-of-Sample
- Test with paper trading before live
```

## Advanced Usage

### Test Single Strategy

Modify `main()` function to test only one strategy:

```python
strategies = [
    StrategyConfig(
        name="Mean Reversion RSI #2852",
        test_id=2852,
        strategy_type='mean_reversion_rsi',
        rsi_period=7,
        oversold_threshold=20.0,
        exit_strategy='rsi_neutral',
        exit_rsi_level=50.0,
        profit_target_pct=0.02,
        stop_loss_pct=-0.02,
        max_hold_days=5,
        min_volume_surge=1.5
    )
]
```

### Test Different Symbols

Modify `BacktestConfig`:

```python
config = BacktestConfig(
    symbols=['AAPL', 'TSLA', 'NVDA', 'AMD'],  # Different symbols
    ...
)
```

### Adjust Phase Years

```python
config = BacktestConfig(
    phases=[
        BacktestPhase('Training', 2010, 2017, 'Extended training'),
        BacktestPhase('Validation', 2018, 2020, 'Recent validation'),
        BacktestPhase('Out-of-Sample', 2021, 2024, 'Latest market')
    ],
    ...
)
```

## Output Files

### Trade Logs (`*_trades_*.csv`)

Each CSV contains detailed trade records:

| Column | Description |
|--------|-------------|
| symbol | Stock ticker |
| entry_date | Trade entry timestamp |
| entry_price | Entry price |
| entry_rsi | RSI at entry |
| exit_date | Trade exit timestamp |
| exit_price | Exit price |
| exit_rsi | RSI at exit |
| exit_reason | Why trade closed (RSI_NEUTRAL, PROFIT_TARGET, etc.) |
| shares | Position size |
| pnl | Profit/loss in dollars |
| pnl_pct | Profit/loss percentage |
| hold_days | Days held |

### Summary Report (`comprehensive_backtest_summary_*.txt`)

Contains:
1. Overall performance by strategy and phase
2. Cross-strategy comparison tables
3. Key insights and recommendations
4. Consistency checks

## Common Issues

### Issue: "No data for {symbol}"
**Solution:** Symbol may not have data for earlier years (2011-2016). Remove from symbols list or adjust phases.

### Issue: Very few trades
**Solution:** 
- RSI thresholds may be too strict (try RSI < 25 instead of < 20)
- Volume filter too high (try 1.2x instead of 1.5x)
- Check if symbols had low volatility in that period

### Issue: All strategies fail Out-of-Sample
**Solution:**
- Market regime may have changed (2020+ very different from 2011-2016)
- Consider retraining with more recent in-sample (2017-2020)
- Adjust parameters based on validation phase feedback

## Next Steps After Backtest

### If Strategy PASSES:

1. **Paper Trading** (1-2 weeks)
   - Deploy with paper money
   - Monitor real-time performance
   - Compare to backtest expectations

2. **Live Testing** (small position)
   - Start with 1-2 positions max
   - Position size: $100-200 per trade
   - Run for 5-10 trading days

3. **Scale Gradually**
   - If achieving 45%+ win rate live
   - If weekly returns >= 3%
   - Increase to 3 positions, normal sizing

### If Strategy FAILS:

1. **Re-optimize** with updated framework
   - Run new optimization (17,145 tests)
   - Use Connors RSI, Gap Reversal, BB Squeeze
   - Focus on Out-of-Sample period (2020-2024)

2. **Hybrid Approach**
   - Combine best elements from multiple strategies
   - Use regime detection to switch strategies
   - Adaptive thresholds based on market conditions

3. **Parameter Adjustment**
   - Analyze which trades failed in Out-of-Sample
   - Adjust RSI thresholds, profit targets, exits
   - Re-run backtest with new parameters

## Performance Expectations

### Conservative Estimates (Real Markets)

Based on simulated → real conversion factors:

| Simulated | Expected Real (Out-of-Sample) |
|-----------|-------------------------------|
| 19% weekly | 5-8% weekly |
| 63% win rate | 48-55% win rate |
| 3.5 Sharpe | 1.5-2.2 Sharpe |

**Rule of Thumb:** Real performance = 40-60% of simulated for out-of-sample.

### Why Lower?

1. **Slippage:** Real fills worse than backtest assumptions
2. **Regime Changes:** 2020-2024 different from optimization data
3. **Overfitting:** Parameters optimized on simulated data
4. **Market Impact:** Bot affects prices (minimal but real)
5. **Execution Timing:** Real trades have delays

## Validation Checklist

Before deploying live:

- [ ] All 3 strategies tested on all 3 phases
- [ ] At least 1 strategy passes Out-of-Sample (>=5% weekly)
- [ ] Win rate >= 45% in Out-of-Sample for chosen strategy
- [ ] Sharpe >= 1.5 in Out-of-Sample
- [ ] Max drawdown < 20% in Out-of-Sample
- [ ] Trade logs reviewed for anomalies
- [ ] Exit reasons make sense (not all STOP_LOSS)
- [ ] Hold times reasonable (1-5 days average)
- [ ] Performance stable across different symbols
- [ ] Results saved and documented
- [ ] Paper trading plan prepared

## Contact

Questions or issues? Check:
- `OPTIMIZATION_README.md` - Optimization framework details
- `README_DEPLOYMENT.md` - Deployment procedures
- `BOT_ANALYSIS_DOCUMENTATION.md` - Current strategy status

---

**Generated:** November 22, 2025
**Framework:** 14-year comprehensive backtest (2011-2024)
**Strategies:** Top 3 from 5,466 optimization tests

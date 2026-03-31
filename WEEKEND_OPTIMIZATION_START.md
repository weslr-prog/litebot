# Weekend Parameter Optimization - Getting Started

**Date**: November 22, 2025  
**Goal**: Find optimal parameters for highest weekly return  
**Duration**: Run 1-hour sessions throughout the weekend

---

## ✅ Setup Complete

The optimization engine is ready to run. Here's what you have:

### Files Created
1. **optimize_parameters.py** - Main optimization engine
2. **run_optimization.sh** - Quick start script (1-hour runs)
3. **OPTIMIZATION_README.md** - Full documentation
4. **This file** - Quick start guide

### Strategies to Test
- ✅ Momentum with Moving Averages (1,350 combinations)
- ✅ Momentum with Trailing Stops (1,080 combinations)
- ✅ Momentum with Candlestick Patterns (48 combinations)
- ✅ Mean Reversion with Bollinger Bands (288 combinations)
- ✅ Mean Reversion with RSI (1,728 combinations)
- ✅ Hybrid Strategies (972 combinations)

**Total**: 5,466 parameter combinations to test

---

## 🚀 How to Run

### Option 1: Simple (Recommended)
```bash
cd /home/wes/Desktop/litebotx-usb-deployment
./run_optimization.sh
```

This will:
- Run for 1 hour
- Test all strategies
- Save results automatically
- Show you the best parameters at the end

### Option 2: Direct Command
```bash
python3 optimize_parameters.py --duration 60
```

### Option 3: Specific Strategies Only
```bash
# Test only momentum strategies
python3 optimize_parameters.py --duration 60 --strategies momentum_ma momentum_trailing

# Test only mean reversion
python3 optimize_parameters.py --duration 60 --strategies mean_reversion_bb mean_reversion_rsi

# Test only candlestick patterns
python3 optimize_parameters.py --duration 60 --strategies momentum_candlestick
```

---

## 📊 What Gets Tested

### Price Range
**KEPT AS IS** - Your current range ($5-$500) stays the same

### Moving Averages
- **Types**: SMA vs EMA
- **Fast MA**: 5, 8, 10, 13, 20 periods
- **Slow MA**: 20, 30, 50, 100, 200 periods
- **Best range tested**: 5-200 period combinations

### Trailing Stops
- **Activation**: 0.5%, 1%, 2%, 3% profit
- **Distance**: 1%, 1.5%, 2%, 2.5%, 3%
- **Adaptive**: On/Off
- **Strong momentum**: 1.8%, 2%, 2.5% trail
- **Weak momentum**: 1%, 1.2%, 1.5% trail

### Momentum Triggers
- **Volume surge**: 1.2x, 1.5x, 2.0x average
- **RSI thresholds**: 30, 40, 50
- **Confirmation types**: MA cross, Volume, RSI
- **Lookback periods**: 3, 5, 10 minutes

### Candlestick Patterns (NEW)
- Bullish engulfing
- Hammer
- Morning star
- Piercing line
- Three white soldiers
- Volume/MA confirmation options

### Mean Reversion (NEW)
- **Bollinger Bands**: 10/20/30 period, 1.5-3.0 std dev
- **RSI extremes**: Oversold (20-35), Overbought (65-80)
- **Exit strategies**: Neutral return, opposite extreme, profit target

---

## 📈 Results You'll Get

After each 1-hour run, you'll see:

### 1. Best Overall Parameters
File: `optimization_results/best_parameters.json`

Example:
```json
{
  "strategy_name": "momentum_trailing",
  "weekly_return": 5.82%,
  "win_rate": 48.5%,
  "sharpe_ratio": 2.14,
  "parameters": {
    "trailing_activation_pct": 0.01,
    "adaptive_trailing": true,
    "strong_momentum_trail": 0.02,
    ...
  }
}
```

### 2. Top 10 Performers by Metric
- `top_10_weekly_return.csv` - **Your primary goal**
- `top_10_sharpe_ratio.csv` - Risk-adjusted returns
- `top_10_win_rate.csv` - Highest win percentage
- `top_10_profit_factor.csv` - Best profit factor

### 3. Complete Results
- `all_results.csv` - All tests (open in Excel)
- `checkpoint.json` - Auto-save progress

### 4. Logs
- `optimization.log` - Detailed execution log

---

## 🔄 Running Multiple Sessions

The optimizer auto-saves progress every 10 tests. You can run it multiple times:

### Friday Evening (Session 1)
```bash
./run_optimization.sh
```
Result: ~500-800 tests completed

### Saturday Morning (Session 2)
```bash
./run_optimization.sh
```
Result: Continues from test 801, completes ~500-800 more

### Saturday Afternoon (Session 3)
```bash
./run_optimization.sh
```
Result: Continues from test 1601, completes ~500-800 more

### Sunday (Session 4)
```bash
./run_optimization.sh
```
Result: Continues from test 2401, may finish all 5,466 tests

**Total Weekend**: ~2,000-3,200 tests completed

---

## 📋 Performance Metrics

Each test measures:

| Metric | Description | Goal |
|--------|-------------|------|
| **Weekly Return** | Avg return per week (PRIMARY GOAL) | Maximize |
| Win Rate | % winning trades | >40% |
| Sharpe Ratio | Risk-adjusted return | >1.5 |
| Profit Factor | Winners / Losers | >2.0 |
| Avg Winner | Avg winning trade % | >2% |
| Avg Loser | Avg losing trade % | <1.5% |
| Max Drawdown | Worst loss from peak | <10% |

---

## 🎯 Expected Timeline

### 1-Hour Session
- **Tests completed**: ~500-800 (depends on strategy complexity)
- **Strategies tested**: Mix of all 6 types
- **Progress saved**: Every 10 tests

### Full Weekend (4-5 hours)
- **Tests completed**: 2,000-3,200 (40-60% of total)
- **Enough for**: Strong conclusions on best strategy type
- **Best use**: Test all strategies first hour, focus on top performers in later sessions

### Complete All Tests (7-9 hours)
- **Tests completed**: All 5,466
- **Coverage**: Every combination tested
- **Best use**: If you want exhaustive analysis

---

## 🔍 Viewing Results in Real-Time

### Watch progress
```bash
tail -f optimization.log
```

### Check how many tests completed
```bash
cat optimization_results/checkpoint.json | grep "completed"
```

### View current best
```bash
cat optimization_results/best_parameters.json
```

### Open results in spreadsheet
```bash
libreoffice optimization_results/all_results.csv
# Or copy to Windows and open in Excel
```

---

## 💡 Strategy Selection Tips

### Start Broad (First Hour)
```bash
# Test everything
./run_optimization.sh
```

### Then Focus (Sessions 2-4)
After seeing which strategy type performs best:

```bash
# If momentum_trailing was best, focus on it
python3 optimize_parameters.py --duration 60 --strategies momentum_trailing

# If mean_reversion_bb was best
python3 optimize_parameters.py --duration 60 --strategies mean_reversion_bb

# If hybrid strategies worked well
python3 optimize_parameters.py --duration 60 --strategies hybrid
```

---

## 🛠️ Commands Cheat Sheet

```bash
# Run for 1 hour
./run_optimization.sh

# Run for 2 hours
python3 optimize_parameters.py --duration 120

# Run specific tests only
python3 optimize_parameters.py --max-tests 100

# Resume from checkpoint
python3 optimize_parameters.py --duration 60 --resume

# Start fresh (delete checkpoint)
python3 optimize_parameters.py --duration 60 --reset

# View best params
cat optimization_results/best_parameters.json

# View top 10
cat optimization_results/top_10_weekly_return.csv

# Watch live progress
tail -f optimization.log
```

---

## ✅ Next Steps After Optimization

Once you find the best parameters:

1. **Review Results**
   ```bash
   cat optimization_results/best_parameters.json
   ```

2. **Check Top 10 Alternatives**
   ```bash
   cat optimization_results/top_10_weekly_return.csv
   ```

3. **Compare Strategy Types**
   - Look at which strategy type dominates top 10
   - Note if momentum or mean reversion performs better
   - Check if candlestick patterns add value

4. **Implement in Bot**
   - Copy best parameters to `config.py` or `traders/short_cycle_trader.py`
   - Update trailing stop activation/distances
   - Update MA periods if different from current
   - Add candlestick pattern logic if tested well

5. **Validate**
   - Backtest on different time period
   - Paper trade for 1 week
   - Monitor performance vs optimization results

6. **Document**
   - Save winning parameters
   - Note which strategies failed
   - Update `BOT_ANALYSIS_DOCUMENTATION.md`

---

## ⚠️ Important Notes

### This is Simulated Data
The current version uses **statistical simulation** to test parameters quickly. For production:
- Replace with actual historical data backtesting
- Validate top performers on real data
- Paper trade before live deployment

### Overfitting Risk
- More tests = higher risk of curve-fitting to noise
- Always validate on out-of-sample data
- Paper trade best params before going live

### Market Conditions
- Results may vary in different market regimes
- Test in bull, bear, and sideways markets
- Consider current market conditions when implementing

---

## 🚀 Ready to Start?

**Recommended approach:**

1. **Friday evening**: Run first 1-hour session
   ```bash
   ./run_optimization.sh
   ```

2. **Check results**: View best parameters
   ```bash
   cat optimization_results/best_parameters.json
   ```

3. **Saturday morning**: Continue for another hour
   ```bash
   ./run_optimization.sh
   ```

4. **Review progress**: Check top 10 by different metrics

5. **Saturday afternoon**: Focus on best strategy type
   ```bash
   python3 optimize_parameters.py --duration 60 --strategies [best_type]
   ```

6. **Sunday**: Final session or focused testing

7. **Sunday evening**: Analyze all results, pick winners, implement

---

**Good luck! 🎯**

The optimization engine will find the best parameters for maximum weekly return. Let it run and check back to see what works best!

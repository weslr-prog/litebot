# LiteBotX Parameter Optimization Engine

**Automated backtesting framework for finding optimal trading parameters**

## Quick Start (1-Hour Optimization)

```bash
# Simple: Run for 1 hour with all strategies
./run_optimization.sh

# Or directly:
python3 optimize_parameters.py --duration 60
```

The script will:
- Test 6 different strategy types
- Try hundreds of parameter combinations
- Save progress every 10 tests
- Generate performance rankings
- Identify best parameters

## Strategy Types Tested

### 1. Momentum - Moving Average Variations
- Tests: SMA vs EMA
- Fast MA: 5, 8, 10, 13, 20 periods
- Slow MA: 20, 30, 50, 100, 200 periods
- Volume confirmation: 1.2x, 1.5x, 2.0x
- RSI filters: 30, 40, 50 thresholds
- **Combinations**: ~300 tests

### 2. Momentum - Trailing Stop Variations
- Activation: 0.5%, 1%, 2%, 3% profit
- Distance: 1%, 1.5%, 2%, 2.5%, 3%
- Adaptive trailing: On/Off
- Strong momentum trail: 1.8%, 2%, 2.5%
- Weak momentum trail: 1%, 1.2%, 1.5%
- Momentum lookback: 3, 5, 10 minutes
- **Combinations**: ~200 tests

### 3. Momentum - Candlestick Patterns
- Patterns: Bullish engulfing, hammer, morning star, three white soldiers
- Volume confirmation: On/Off
- MA confirmation: On/Off
- Min body size: 50%, 60%, 70%
- **Combinations**: ~50 tests

### 4. Mean Reversion - Bollinger Bands
- Period: 10, 20, 30
- Std Dev: 1.5, 2.0, 2.5, 3.0
- Entry: Touch band vs break below
- Exit: Middle band vs upper band
- RSI filter: On/Off (< 30)
- **Combinations**: ~150 tests

### 5. Mean Reversion - RSI Extremes
- RSI period: 7, 14, 21, 28
- Oversold: 20, 25, 30, 35
- Overbought: 65, 70, 75, 80
- Exit strategy: Neutral RSI, opposite extreme, profit target
- Profit target: 1%, 2%, 3%
- **Combinations**: ~200 tests

### 6. Hybrid - Momentum Entry + Mean Reversion Exit
- Entry: MA cross, breakout, volume surge
- Exit: BB upper, RSI overbought, profit target
- Fast MA: 8, 10, 13
- Slow MA: 20, 30, 50
- BB period: 20, 30
- Profit target: 2%, 3%, 5%
- **Combinations**: ~150 tests

**Total Parameter Combinations**: ~1,050 tests

## Usage Examples

### Run for 1 hour (default)
```bash
python3 optimize_parameters.py --duration 60
```

### Run for 2 hours
```bash
python3 optimize_parameters.py --duration 120
```

### Test specific strategies only
```bash
# Test only momentum strategies
python3 optimize_parameters.py --duration 60 --strategies momentum_ma momentum_trailing

# Test only mean reversion
python3 optimize_parameters.py --duration 60 --strategies mean_reversion_bb mean_reversion_rsi
```

### Run exactly 100 tests (ignore time limit)
```bash
python3 optimize_parameters.py --max-tests 100
```

### Resume from last checkpoint
```bash
python3 optimize_parameters.py --duration 60 --resume
```

### Start fresh (delete checkpoint)
```bash
python3 optimize_parameters.py --duration 60 --reset
```

## Output Files

All results saved to `optimization_results/`:

### 1. `checkpoint.json`
- Auto-saved progress (every 10 tests)
- Allows resuming if interrupted
- Contains all completed test results

### 2. `all_results.csv`
- Complete results table
- All parameters and performance metrics
- Sortable in Excel/Google Sheets

### 3. `top_10_weekly_return.csv`
- Best 10 parameter sets by weekly return
- **PRIMARY GOAL METRIC** (highest weekly return)

### 4. `top_10_sharpe_ratio.csv`
- Best 10 parameter sets by risk-adjusted return
- Good for consistency

### 5. `top_10_win_rate.csv`
- Best 10 parameter sets by win percentage
- Good for psychological comfort

### 6. `top_10_profit_factor.csv`
- Best 10 parameter sets by profit factor (winners/losers)
- Good for overall edge

### 7. `best_parameters.json`
- Single best parameter set (by weekly return)
- Ready to implement in bot

## Performance Metrics Tracked

For each parameter combination:
- **Weekly Return**: Primary goal (annualized return / 52)
- **Total Return**: Overall % gain/loss
- **Win Rate**: % of winning trades
- **Num Trades**: Total trades executed
- **Avg Winner**: Average winning trade %
- **Avg Loser**: Average losing trade %
- **Winner/Loser Ratio**: Avg winner / Avg loser
- **Max Drawdown**: Worst peak-to-trough loss
- **Sharpe Ratio**: Risk-adjusted return
- **Profit Factor**: Total wins / Total losses

## Viewing Results

### Quick view best parameters
```bash
cat optimization_results/best_parameters.json
```

### View top 10 by weekly return
```bash
cat optimization_results/top_10_weekly_return.csv | column -t -s,
```

### Open in spreadsheet
```bash
# Linux
libreoffice optimization_results/all_results.csv

# Or copy to your desktop to open in Excel
```

### Check progress
```bash
tail -f optimization.log
```

## Continuing for Another Hour

After the first hour completes:

```bash
# Continue from where it left off
python3 optimize_parameters.py --duration 60 --resume
```

Or just run the script again:

```bash
./run_optimization.sh
```

The checkpoint system automatically resumes from the last completed test.

## Example Output

```
🚀 Starting optimization for 60 minutes
📊 Testing strategies: momentum_ma, momentum_trailing, mean_reversion_bb, ...
🔄 Resuming from 0 completed tests
📈 Total parameter combinations: 1050

======================================================================
Test 1/1050 - momentum_ma
Parameters: {
  "strategy_type": "momentum",
  "ma_type": "EMA",
  "fast_ma": 10,
  "slow_ma": 50,
  "volume_multiplier": 1.5,
  ...
}
📊 Results: Return=3.45% weekly, Win Rate=42.3%, Sharpe=1.67

...

✅ Optimization completed!
⏱️  Time elapsed: 60.2 minutes
🧪 Tests completed this run: 847
📊 Total tests: 847/1050

🏆 BEST PARAMETERS (by weekly return):
Strategy: momentum_trailing
Weekly Return: 5.82%
Win Rate: 48.5%
Sharpe Ratio: 2.14
Parameters: {
  "trailing_activation_pct": 0.01,
  "adaptive_trailing": true,
  "strong_momentum_trail": 0.02,
  "weak_momentum_trail": 0.012,
  ...
}
```

## Tips for Weekend Optimization

### Run multiple 1-hour sessions
```bash
# Session 1: Friday evening
./run_optimization.sh

# Session 2: Saturday morning (auto-resumes)
./run_optimization.sh

# Session 3: Saturday afternoon
./run_optimization.sh

# Session 4: Sunday
./run_optimization.sh
```

Each session adds ~500-1000 tests depending on strategy complexity.

### Focus on specific strategies
If a strategy type shows promise, focus on it:

```bash
# Momentum trailing showed best results, test more combinations
python3 optimize_parameters.py --duration 120 --strategies momentum_trailing
```

### Compare strategies
```bash
# Test momentum vs mean reversion head-to-head
python3 optimize_parameters.py --duration 60 --strategies momentum_ma mean_reversion_bb
```

## Implementing Best Parameters

Once you find optimal parameters:

1. Check `optimization_results/best_parameters.json`
2. Copy parameters to bot configuration
3. Update `traders/short_cycle_trader.py` with new values
4. Backtest on historical data to validate
5. Paper trade for 1 week before live deployment

## Notes

- **Simulated backtests**: Current version uses statistical simulation
- **Replace with real data**: Connect to actual backtest engine for production
- **Overfitting risk**: More tests = higher risk of curve-fitting
- **Validation required**: Always paper trade best params before live
- **Market conditions**: Results may vary in different market regimes

## Troubleshooting

### "No results to analyze"
- Check if tests are completing (view optimization.log)
- Reduce duration or max-tests if running too long

### "Checkpoint corrupted"
```bash
python3 optimize_parameters.py --reset --duration 60
```

### "Too slow"
- Reduce number of strategies tested
- Use --max-tests to limit total tests
- Focus on most promising strategy types

## Advanced: Custom Parameter Spaces

Edit `optimize_parameters.py` to add your own parameter combinations:

```python
PARAMETER_SPACES["my_custom_strategy"] = {
    "name": "My Custom Strategy",
    "description": "Custom parameter sweep",
    "params": {
        "strategy_type": ["custom"],
        "my_param_1": [1, 2, 3, 5, 10],
        "my_param_2": [True, False],
        ...
    }
}
```

Then run:
```bash
python3 optimize_parameters.py --duration 60 --strategies my_custom_strategy
```

---

**Happy optimizing! 🚀**

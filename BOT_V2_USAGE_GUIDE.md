# bot_v2 Usage Guide

## Two Operation Modes

### 1. Single-Run Mode (Testing/Manual)
**File**: `run_bot_v2.py`

**Use this for**:
- Testing the bot
- Manual trading sessions
- Debugging
- One-time execution

**Command**:
```bash
python run_bot_v2.py
```

**What it does**:
1. Loads credentials from `.env`
2. Connects to Alpaca
3. Initializes bot
4. Runs ONE trading cycle
5. **Exits**

**Terminal Output Example**:
```
======================================================================
bot_v2 ProductionTradingEngine - Daily Trading Cycle
======================================================================

✅ Loaded credentials from .env
   Mode: PAPER TRADING
   Base URL: https://paper-api.alpaca.markets

📋 Configuration:
   Portfolio Value: $1,000
   Daily Pool: $500 (50%)
   Confidence Threshold: 60%
   Max Positions/Day: 12
   Max Daily Loss: $80 (8%)

🔌 Connecting to Alpaca...
✅ Connected to Alpaca
   Account Value: $985.49
   Buying Power: $851.32

📊 Initializing data loader...
✅ Data loader ready

🤖 Initializing bot_v2 ProductionTradingEngine...
✅ bot_v2 initialized successfully

======================================================================
Starting Daily Trading Cycle
======================================================================

🚀 Starting daily trading cycle (bot_v2)
...
✅ Daily Trading Cycle Complete

📊 Portfolio Summary:
   Portfolio Value: $985.49
   Open Positions: 0
   Trades Today: 0
   Daily P&L: $0.00
```

---

### 2. Continuous Operation Mode (Production)
**File**: `run_bot_v2_continuous.py`

**Use this for**:
- Production trading
- Long-term operation
- Automated 24/7 operation
- Matching original bot behavior

**Command**:
```bash
python run_bot_v2_continuous.py
```

**What it does**:
1. Loads credentials and initializes bot (once)
2. **Runs continuously in a loop**
3. Executes scheduled activities based on time:
   - **Pre-Market (6:00 AM - 9:30 AM ET)**: Data loading & preparation
   - **Market Hours (9:30 AM - 4:00 PM ET)**: Trading cycle every 5 minutes
   - **Post-Market (4:00 PM - 8:00 PM ET)**: Reporting & cleanup
   - **After Hours / Weekends**: Sleeps until next activity
4. **Never exits** (until Ctrl+C)

**Terminal Output Example**:
```
======================================================================
bot_v2 ProductionTradingEngine - CONTINUOUS OPERATION MODE
======================================================================

✅ Loaded credentials from .env
   Mode: PAPER TRADING
   Base URL: https://paper-api.alpaca.markets

📋 Configuration:
   Portfolio Value: $1,000
   Daily Pool: $500 (50%)
   Confidence Threshold: 60%
   Max Positions/Day: 12
   Max Daily Loss: $80 (8%)

🔌 Connecting to Alpaca...
✅ Connected to Alpaca
   Account Value: $985.49
   Buying Power: $851.32

📊 Initializing data loader...
✅ Data loader ready

🤖 Initializing bot_v2 ProductionTradingEngine...
✅ bot_v2 initialized successfully

======================================================================
🔄 CONTINUOUS OPERATION MODE ACTIVE
======================================================================

Bot will now run continuously with scheduled activities:
  🌅 Pre-Market (6:00 AM - 9:30 AM): Data loading & preparation
  📈 Market Hours (9:30 AM - 4:00 PM): Active trading every 5 min
  🌙 Post-Market (4:00 PM - 8:00 PM): Reporting & cleanup
  💤 After Hours / Weekends: Sleep until next activity

Press Ctrl+C to stop the bot
======================================================================

💤 [11:30:45 PM ET] WEEKEND: Sleeping for 6h 29m
   Next activity: Monday 06:00 AM ET

```

**During Pre-Market (6:00 AM - 9:30 AM)**:
```
======================================================================
🌅 PRE-MARKET PREPARATION - 06:00 AM ET
======================================================================

📊 Loading market data...
🔍 Refreshing watchlist...
📈 Analyzing overnight moves...
✅ Pre-market preparation complete
```

**During Market Hours (9:30 AM - 4:00 PM)**:
```
======================================================================
📈 MARKET HOURS TRADING - 09:30 AM ET
======================================================================

🚀 Running daily trading cycle...
✅ Trading cycle complete

🔄 [09:35:00 AM ET] Checking for trading opportunities...
🔄 [09:40:00 AM ET] Checking for trading opportunities...
🔄 [09:45:00 AM ET] Checking for trading opportunities...
...
```

**During Post-Market (4:00 PM - 8:00 PM)**:
```
======================================================================
🌙 POST-MARKET CLEANUP - 04:00 PM ET
======================================================================

📊 Daily Performance Summary:
   Portfolio Value: $1,025.50
   Open Positions: 2
   Trades Today: 3
   Daily P&L: +$25.50

💾 Saving position data...
📝 Generating daily report...
✅ Post-market cleanup complete
```

---

## Bot Configuration

### Current Configuration (bot_v2)
The bot uses `bot_v2/config/trading_config.py` with these **default settings**:

```python
portfolio_value = 1000.0           # $1,000 portfolio
daily_pool_percent = 0.50          # 50% deployment per day
max_positions_per_day = 12         # 12 trades/month target
confidence_threshold = 0.60        # 60% minimum confidence
max_position_dollars = 200.0       # $200 max per position (20%)
max_risk_per_trade_dollars = 20.0  # $20 max risk per trade (2%)
max_daily_loss_percent = 0.08      # 8% daily loss limit
max_weekly_loss_percent = 0.15     # 15% weekly loss limit
```

### ⚠️ Important: bot_v2 vs Original Bot Strategy

**bot_v2 is NOT configured to match BOT_ANALYSIS_DOCUMENTATION.md yet.**

- **BOT_ANALYSIS_DOCUMENTATION.md** describes your **original bot** (ShortCycleTrader)
  - Located in: `traders/short_cycle_trader.py`
  - 4,234 lines of production-tested code
  - Phase 1 Exit Strategy (Nov 21, 2025)
  - Momentum-adaptive trailing stops
  - Friday 3:45 PM force exits
  - All the strategies documented in BOT_ANALYSIS_DOCUMENTATION.md

- **bot_v2** is the **refactored modular version**
  - Located in: `bot_v2/` directory
  - Clean modular architecture (19 files vs 1)
  - **Same configuration parameters** (portfolio size, risk limits)
  - **May not have all advanced features yet** (trailing stops, etc.)

### How to Match Original Bot Behavior

If you want bot_v2 to trade like the original bot documented in BOT_ANALYSIS_DOCUMENTATION.md:

1. **Use the original bot** (already configured):
   ```bash
   python start_small_portfolio_trader.py
   ```

2. **OR** wait for full bot_v2 feature parity (work in progress)

3. **OR** manually copy features from original bot to bot_v2

---

## Stopping the Bot

### Single-Run Mode
- Bot exits automatically after one cycle

### Continuous Mode
- Press **Ctrl+C** to stop gracefully
- Bot will display final portfolio summary
- Position data is saved automatically

**Example**:
```
^C
======================================================================
⚠️  Bot shutdown requested by user
======================================================================

📊 Final Portfolio Summary:
   Portfolio Value: $1,025.50
   Open Positions: 2
   Trades Today: 3

✅ Bot shutdown complete
```

---

## Checking if Bot is Running

### Visual Confirmation
Look for these indicators in terminal:

**Bot IS running if you see**:
```
🔄 CONTINUOUS OPERATION MODE ACTIVE
```
or
```
💤 [11:30:45 PM ET] WEEKEND: Sleeping for 6h 29m
```
or
```
🔄 [09:35:00 AM ET] Checking for trading opportunities...
```

**Bot is NOT running if**:
- Terminal shows shell prompt (`$` or `wes@hostname`)
- No new output for >5 minutes during market hours
- Last line says "✅ Daily Trading Cycle Complete"

### Process Check
```bash
# Check if bot is running
ps aux | grep run_bot_v2_continuous.py

# If running, you'll see:
# wes  12345  0.5  2.1  ... python run_bot_v2_continuous.py
```

---

## Troubleshooting

### Bot exits immediately
**Problem**: `run_bot_v2_continuous.py` exits after initialization

**Solution**: Check for errors in terminal output. Common issues:
- Missing `.env` file (credentials not found)
- Invalid Alpaca credentials
- Import errors (missing modules)

### No terminal output
**Problem**: Can't tell if bot is running

**Solution**: Use continuous mode (`run_bot_v2_continuous.py`) which has verbose output

### Bot not trading during market hours
**Problem**: Continuous mode shows "Checking for trading opportunities" but no trades

**Possible Reasons**:
- No signals meet 60% confidence threshold
- Day trade limit reached (PDT restriction)
- Max positions already open
- Weekend (markets closed)
- Kill switch activated (portfolio loss limits)

**Check**:
```python
python -c "
from bot_v2.core import ProductionTradingEngine
from bot_v2.config import ShortCycleConfig
bot = ProductionTradingEngine(config=ShortCycleConfig())
summary = bot.get_portfolio_summary()
print(summary)
"
```

---

## Next Steps

1. **Test in single-run mode first**:
   ```bash
   python run_bot_v2.py
   ```
   Verify it connects and runs one cycle successfully.

2. **Then switch to continuous mode**:
   ```bash
   python run_bot_v2_continuous.py
   ```
   Let it run and observe the scheduled activities.

3. **Monitor logs** to see detailed bot activity:
   ```bash
   tail -f logs/trading_bot.log  # (if logging is enabled)
   ```

4. **Review performance** after 5-10 trades to validate bot_v2 behavior.

---

## Summary

| Feature | Single-Run (`run_bot_v2.py`) | Continuous (`run_bot_v2_continuous.py`) |
|---------|------------------------------|----------------------------------------|
| **Runs once** | ✅ Yes, then exits | ❌ No, runs forever |
| **Continuous operation** | ❌ No | ✅ Yes |
| **Pre-market activities** | ❌ No | ✅ Yes (6:00 AM) |
| **Market hours trading** | ✅ Yes (once) | ✅ Yes (every 5 min) |
| **Post-market cleanup** | ⚠️ Basic summary | ✅ Full reporting |
| **Sleep/wake cycles** | ❌ No | ✅ Yes (after hours/weekends) |
| **Terminal output** | ✅ Yes | ✅ Yes (verbose) |
| **Best for** | Testing, debugging | Production, 24/7 operation |

**Recommendation**: Use **`run_bot_v2_continuous.py`** for production trading (matches original bot behavior).

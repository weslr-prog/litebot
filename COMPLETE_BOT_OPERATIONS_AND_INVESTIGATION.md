# LiteBotX Bot V2 — Complete Operational Documentation & Performance Investigation

**Date:** February 26, 2026  
**Source:** Direct code analysis of every production file (NOT from prior documentation)  
**Purpose:** External review document — describes exactly what the code does, with all parameters, for identifying improvement opportunities  

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [System Architecture Overview](#2-system-architecture-overview)
3. [Complete Daily Cycle: Market Close → Next Market Close](#3-complete-daily-cycle)
4. [Stock Universe & PreFilter Pipeline](#4-stock-universe--prefilter-pipeline)
5. [Signal Generation — The 3-Strategy Stack](#5-signal-generation--the-3-strategy-stack)
6. [Order Execution & Fill Handling](#6-order-execution--fill-handling)
7. [Position Monitoring & Exit Logic](#7-position-monitoring--exit-logic)
8. [Data Sources & Price Fetching](#8-data-sources--price-fetching)
9. [Position Sync with Alpaca](#9-position-sync-with-alpaca)
10. [Actual Performance Data](#10-actual-performance-data)
11. [Root Cause Investigation](#11-root-cause-investigation)
12. [Complete Parameter Reference](#12-complete-parameter-reference)

---

## 1. Executive Summary

LiteBotX Bot V2 is a Python-based automated stock trading bot running against the Alpaca paper trading API. It trades mid-cap stocks ($2B–$10B market cap) using three strategies: Gap & Go, Fade/Short, and Momentum. It runs in a continuous loop from 7:00 AM to 7:00 PM ET on trading days.

**Actual performance over 32 trading days (Jan 13 – Feb 25, 2026):**

| Metric | Value |
|--------|-------|
| Starting equity | ~$1,000 |
| Current equity | $969 |
| Cumulative P&L | -$95.71 |
| Total entries (log) | 86 |
| Total exits (log) | 124 |
| Exit wins | 60 |
| Exit losses | 62 |
| Signal scans returning 0 | 760 (86.3%) |
| Signal scans producing signals | 121 (13.7%) |
| Days with zero entries (last 8 trading days) | 6 of 8 |
| Last entries | Feb 20 (4 entries), Feb 23 (1 entry) |

---

## 2. System Architecture Overview

### File Structure (Production Code)

| File | Purpose | Lines |
|------|---------|-------|
| `bot_v2/launcher.py` | Main loop, phase scheduling, entry/exit orchestration | 1,955 |
| `bot_v2/signal_generation/signal_generator.py` | 3-strategy stack, confidence scoring, data source enhancements | 1,486 |
| `bot_v2/core/pre_filter.py` | 3-stage stock filtering (price, volume, volatility) | 1,881 |
| `bot_v2/execution/exit_manager.py` | Traditional exit logic (stop loss, profit target, time stop) | 548 |
| `bot_v2/utils/smart_exit_manager.py` | "Smart" exit logic with 8 strategies | 343 |
| `bot_v2/execution/order_manager.py` | Order submission, anti-churning, fill price tracking | 518 |
| `bot_v2/config/trading_config.py` | All configuration parameters | 415 |
| `bot_v2/config/prefilter_config.py` | PreFilter thresholds | 156 |
| `bot_v2/data/data_loader.py` | yfinance data fetching | 381 |
| `bot_v2/models/positions.py` | Position model with exit logic | 291 |
| `connect_real_trading.py` | Alpaca API wrapper | 382 |

### Data Flow Chain

```
Stock Universe (4,718 symbols in data/universe.csv)
        ↓
PreFilter (3-stage: price → volume → volatility)
        ↓  ~15-21 candidates pass (~7-8%)
yfinance data fetch (100 days daily bars per candidate)
        ↓
Signal Generator (EMA filter → Momentum filter → 3 strategies)
        ↓  Typically 0 signals. Occasionally 1-5.
Order Manager → Alpaca market order (buy)
        ↓
Position Tracker (positions.json)
        ↓
Exit Monitor loop (every 60 seconds during market hours)
        ↓
SmartExitManager + ExitManager → Alpaca market order (sell)
```

---

## 3. Complete Daily Cycle

The bot runs `run_continuous_loop()` in `launcher.py` (line 1594). This is an infinite loop with a `time.sleep` between iterations. The loop determines the current **trading phase** and executes the corresponding handler.

### Phase Determination

The method `_get_trading_phase()` (launcher.py line 820) defines these phases based on Eastern Time:

| Phase | Time Window (ET) | What Happens |
|-------|-----------------|--------------|
| `premarket` | 7:00 AM – 9:30 AM | Session startup, position sync with Alpaca, data loading |
| `entry_window` | 9:45 AM – 10:30 AM | Primary entry scans every ~7 minutes |
| `continuous_entry` | 10:30 AM – 1:00 PM | Continue scanning for entries |
| `late_entry` | 1:00 PM – 2:30 PM | Higher-confidence afternoon entries (1.2x threshold, 75% size) |
| `monitoring` | 2:30 PM – 3:30 PM | Exit monitoring only, no new entries |
| `force_exit_losers` | 3:30 PM – 4:00 PM (Friday only) | Force-exit positions down >2% |
| `postmarket` | 4:00 PM – 7:00 PM | Session wrap-up, daily summary |
| `closed` | 7:00 PM – 7:00 AM | Sleep loop, checks every 300 seconds |

### Detailed Phase-by-Phase Walkthrough

#### Phase 0: Overnight / Closed (7:00 PM – 7:00 AM ET)

**What actually happens in the code:**

The main loop in `run_continuous_loop()` calls `_get_trading_phase()` which returns `"closed"`. The loop then sleeps for 300 seconds (5 minutes) and loops again. No trading activity occurs. The bot does NOT shut down — it stays running in an infinite loop.

During this time:
- No data is fetched
- No positions are monitored
- No orders are submitted
- The bot simply checks the time every 5 minutes

#### Phase 1: Premarket (7:00 AM – 9:30 AM ET)

**Code location:** `_handle_premarket()` in launcher.py

The premarket phase runs once per session. On the first call:

1. **Session initialization** — resets `session_data` dictionary:
   - `scans_run = 0`
   - `entries_executed = []`
   - `exits_executed = []`
   - `candidates_reviewed = []`
   - `signals_generated = 0`
   - `rejections = {}`

2. **Position sync with Alpaca** — calls `_sync_positions_with_alpaca()`:
   - Fetches all current positions from Alpaca via `trading_engine.get_positions()`
   - Compares against the internal `position_tracker` (positions.json)
   - **For positions in Alpaca but NOT in tracker:** Creates a "dummy" `ShortCyclePosition` with:
     - `entry_price` = Alpaca's `avg_cost`
     - `position_size_shares` = Alpaca's `quantity`
     - `ai_signal` = dummy AISignal with `confidence=0.5`, `strategy='synced'`
     - `entry_date` = today
     - `exit_date` = 3 trading days from now
   - **For positions in tracker but NOT in Alpaca:** Marks them as exited with reason `"sync_cleanup"` and realizes P&L based on last known price

3. **Portfolio value fetch** — calls `trading_engine.get_account_info()` to get current equity from Alpaca

4. Logs the session start: `"SESSION START | Portfolio: $X | Positions: Y"`

After the first pass, subsequent premarket iterations sleep for 60 seconds.

#### Phase 2: Entry Window (9:45 AM – 10:30 AM ET)

**Code location:** `_run_entry_scan()` in launcher.py (line 1024)

This is the primary entry phase. The scan runs approximately every 7 minutes (the prefilter takes ~60-110 seconds, then there's processing time before the next iteration).

**Step-by-step execution:**

1. **Get Universe** — `_get_universe()` loads `data/universe.csv` (4,718 symbols) and returns a list of symbol strings. No filtering at this step.

2. **Run PreFilter** — instantiates `PreFilter(data_loader, SIMPLE_PREFILTER_CONFIG)` and calls `prefilter.run_filter(full_universe)`. This reduces the 4,718 symbols to ~15-21 candidates. Details in Section 4.

3. **Fetch historical data** — For each of the ~15-21 candidates, calls `data_loader.get_historical_data(symbol, days=100)`. This fetches 100 calendar days of daily OHLCV bars from yfinance. **This is the data the signal generator receives — it is daily bars, not real-time data.**

4. **Generate signals** — calls `signal_generator.generate_signals(universe=candidates, market_data=market_data, active_positions=active_positions)`. This applies the EMA filter, momentum filter, and 3-strategy checks. Returns 0-5 signals. Details in Section 5.

5. **Execute entries** — For each signal:
   - Checks daily entry cap (max 5 per day)
   - Checks earnings blackout
   - Checks **sector concentration** (max 2 per sector — newly added)
   - Calls `order_manager.execute_entry(signal)` which:
     - Calculates shares = `$150 / entry_price`
     - Creates a `ShortCyclePosition`
     - Calls `execute_buy_order()` which submits a **market order** to Alpaca
     - Polls up to 10 seconds for fill
     - Checks fill price divergence (>5% = auto-unwind)
     - Records anti-churning timestamps

#### Phase 3: Continuous Entry (10:30 AM – 1:00 PM ET)

Identical to the entry_window phase. Same `_run_entry_scan()` function is called. Scans continue every ~7 minutes with the same prefilter and signal generation pipeline.

#### Phase 4: Late Entry (1:00 PM – 2:30 PM ET)

**Code location:** `_run_late_entry_scan()` in launcher.py (line 1170)

Similar to the entry scan but with modifications:
- **Confidence multiplier:** 1.2x (requires 20% higher confidence to enter)
- **Position size:** 75% of normal ($112.50 instead of $150)
- **Min ADR:** 2.5% (higher volatility requirement)
- Scans every 15 minutes (not 7 minutes)
- Uses `signal_generator.generate_signals()` with the same universe/prefilter pipeline
- **Note:** The late entry code temporarily modifies `self.config.max_position_dollars` to the reduced size, then restores it after the scan

#### Phase 5: Exit Monitoring (Runs during ALL market phases)

**Code location:** `_monitor_exits()` in launcher.py (line 1340)

This runs continuously alongside entry scans. For each active position in the tracker:

1. **Get current price** — Primary: tries to get real-time price via `price_fetcher` (which uses Alpaca's ask price). Fallback: calls `data_loader.get_current_price(symbol)` which fetches from yfinance — **this returns the LAST DAILY CLOSE, not real-time**

2. **Update highest price** — tracks `position.highest_price` for trailing stop calculations

3. **Fetch RSI/Volume data** — calls `data_loader.get_historical_data(symbol, days=30)` from yfinance to calculate current RSI(7) and volume ratio. **These are daily bars with ~15-minute delay.**

4. **Calculate hours held** — compares current time to `position.filled_at` or `position.entry_timestamp`

5. **Check SmartExitManager first** — calls `smart_exit_manager.should_exit(position, current_price, rsi, volume_ratio, hours_held)`. This checks 8 exit strategies (detailed in Section 7).

6. **If SmartExitManager says no exit** — calls `exit_manager.should_exit(position, current_price, data)` as a fallback. This checks stop loss, profit target, time stop, Friday losers.

7. **Also checks position's own exit logic** — calls `position.should_smart_exit()` which has its own stop/profit/RSI/time logic

8. **If any exit triggers** — calls `order_manager.execute_sell_order(position, exit_price, reason)` which submits a market sell order to Alpaca

#### Phase 6: Force Exit Losers (3:30 PM – 4:00 PM, Friday Only)

Iterates active positions and force-exits any position that is down more than 2%. Uses the same `order_manager.execute_sell_order()` path.

#### Phase 7: Postmarket (4:00 PM – 7:00 PM ET)

**Code location:** `_handle_postmarket()` in launcher.py

1. Runs daily summary generation (daily_summary.py)
2. Updates P&L history file (`pnl_history.json`)
3. Saves position tracker state
4. Logs session summary

Then the bot enters the `closed` phase and loops every 5 minutes until 7:00 AM the next trading day.

---

## 4. Stock Universe & PreFilter Pipeline

### Universe

The trading universe is loaded from `data/universe.csv` — a static file with 4,718 stock symbols from Alpaca's tradeable assets (NYSE + NASDAQ). This file was last refreshed October 2025. It is NOT dynamically updated.

### PreFilter (3-Stage Pipeline)

**Code location:** `bot_v2/core/pre_filter.py`, config from `bot_v2/config/prefilter_config.py`

The prefilter uses a `SIMPLE_PREFILTER_CONFIG` dictionary with these exact thresholds:

| Stage | Filter | Min | Max |
|-------|--------|-----|-----|
| 1 - Price | Share price | $10.00 | $50.00 |
| 2 - Volume | Average daily volume (shares) | 3,000,000 | 30,000,000 |
| 2 - Volume | Average daily dollar volume | $30,000,000 | — |
| 3 - Volatility | ATR% (14-day) | 3.5% | 6.0% |
| Data | Minimum historical data rows | 15 days | — |

**What the prefilter does for each symbol:**

1. Fetches yfinance data (this is where the 60-110 seconds comes from — fetching data for 4,718 symbols)
2. Checks current price is between $10 and $50
3. Checks 20-day average volume is between 3M and 30M shares
4. Checks average daily dollar volume (price × volume) ≥ $30M
5. Checks 14-day ATR as a percentage of price is between 3.5% and 6.0%
6. Requires at least 15 rows of data

**Actual result from logs:** Typically 15-21 out of 257 pass (the universe is first filtered down to ~257 symbols that have data, then ~7-8% pass the 3 stages). The count dropped from ~37 in January to ~15-16 in late February.

### Note on Data Source for PreFilter

The prefilter fetches yfinance daily data for each symbol in the universe. This is free but rate-limited and can be stale. The 4,718-symbol universe is never fully scanned — the prefilter has internal caching that reduces the effective scan to ~257 cached symbols.

---

## 5. Signal Generation — The 3-Strategy Stack

**Code location:** `bot_v2/signal_generation/signal_generator.py`

When `generate_signals()` is called with the ~15-21 candidates that passed the prefilter, it processes each symbol through a serial pipeline:

### Pre-Strategy Filters (Applied to ALL Candidates)

These filters run BEFORE any strategy check. If a symbol fails either filter, it is immediately rejected with no further analysis.

#### Filter 1: Swing Continuation Filter (20 EMA)

```
IF price < 20-day EMA → REJECT ("Below 20 EMA")
IF 20-day EMA slope over last 3 bars ≤ 0 → REJECT ("20 EMA slope negative")
```

- Uses Exponential Moving Average (more responsive than SMA)
- EMA slope is calculated as: `(EMA_today - EMA_3_days_ago) / EMA_3_days_ago`
- **This filter rejects any stock in a downtrend or trading below its trend**
- This is the #1 rejection reason in current market conditions

#### Filter 2: 5-Day Momentum Filter

```
IF 5-day price change < -5% → REJECT ("Falling knife")
```

- Calculated as: `(current_close - close_5_days_ago) / close_5_days_ago`
- Prevents buying stocks that are actively falling

### Strategy 1: Gap & Go (70% Capital Allocation)

**Time window:** Only scans between 9:35 AM and 9:50 AM ET (15-minute window)

**Entry conditions (ALL must be true):**
- Gap = `(today_open - yesterday_close) / yesterday_close`
- Gap between 2% and 8% (inclusive)
- RSI(7) < 75
- Current close > yesterday's close (gap is "holding")
- Gap holding check: current price within 0.5% of today's open

**Confidence calculation:**
- Base: `gap_pct × 5` (e.g., 4% gap = 0.20 base)
- RSI bonus: +0.15 if RSI < 60
- Holding bonus: +0.10 if price near open
- Confirmation: +0.15 if above yesterday's high
- Result is capped at 1.0

**Critical issue with Gap & Go in this bot:**
- The bot fetches **yfinance daily bars** — these are end-of-day data with ~15 minute delay
- The "gap" calculation uses `open` vs yesterday's `close` from yfinance daily bars
- By the time the bot runs at 9:45 AM, yfinance may not yet have today's data
- If yfinance hasn't updated, this strategy sees yesterday's data and cannot detect today's gap
- The 15-minute scan window (9:35–9:50) is extremely narrow

### Strategy 2: Fade/Short (15% Capital Allocation)

**Time window:** Only scans between 10:00 AM and 2:00 PM ET

**Entry conditions (ALL must be true):**
- RSI(7) > 70 (overbought)
- Price is 10%+ above 20-day SMA
- Volume surge ≥ 1.3x (current day volume / 20-day average)
- Exhaustion signal detection (optional bonus):
  - Volume divergence: price making new high but volume declining
  - RSI divergence: price making new high but RSI declining

**Confidence calculation:**
- Base from RSI level and extension above SMA
- Exhaustion signals add confidence bonus
- Volume surge adds confidence bonus

**What "Fade/Short" actually does:** Despite the name, the bot submits a **BUY** order (long entry). The signal_generator creates a standard long AISignal. There is no short-selling logic anywhere in the order execution code. The "fade" concept is that the stock is overbought and should reverse, but the bot buys it at the overbought level — which is contradictory to a fade strategy.

### Strategy 3: Momentum (15% Capital Allocation)

**Time window:** Only scans between 10:30 AM and 2:30 PM ET

**Entry conditions (ALL must be true):**
- RSI(7) between 45 and 65 (healthy trend, not overbought)
- Price above 20-day SMA
- 5-day return between +3% and +15%
- ADR (Average Daily Range) > 2%

**Confidence calculation:**
- Base from RSI position within 45-65 range
- 5-day return contribution
- ADR contribution

### Post-Strategy Processing

After a strategy triggers, additional checks apply:

1. **Liquidity check:** Average dollar volume ≥ $500,000/day
2. **Market cap filter:** Must be $2B–$10B (mid-cap)
3. **Earnings blackout:** Skip if earnings within 3 days before or 1 day after
4. **Symbol blacklist:** Automated underperformer list
5. **Same-day re-entry block:** Can't buy a stock that was sold today

### Confidence Enhancement (Data Sources)

If a base signal passes, these optional data sources modify confidence:

- **News sentiment** (Alpaca News API): No news articles = -20% confidence, 1 article = -15%, few low-quality = -5%
- **Dark pool detection** (Alpaca IEX): Institutional buying detected = confidence boost
- **Options flow** (Alpaca): Unusual options activity = confidence modifier
- **Quality scorer**: Multiplier from 1.0x to 3.0x based on scoring (rarely available — requires 100 days of data)

### Dynamic Confidence Threshold

The confidence threshold varies based on how many positions are open:

| Active Positions (of 5 max) | Threshold |
|-----------------------------|-----------|
| 0-1 (< 25% full) | 0.25 (base) |
| 2 (25-50% full) | 0.35 |
| 3 (50-75% full) | 0.45 |
| 4-5 (75-100% full) | 0.55 |

### Position Sizing

Fixed for all strategies:
- `max_position_dollars = $150` (15% of $1,000 portfolio)
- `shares = int($150 / entry_price)`
- No dynamic position sizing based on volatility, confidence, or risk

---

## 6. Order Execution & Fill Handling

**Code location:** `bot_v2/execution/order_manager.py`, `connect_real_trading.py`

### Buy Order Flow

1. `order_manager.execute_entry(signal)` receives an `AISignal`
2. Calculates shares: `int($150 / signal.entry_price)`
3. Creates `ShortCyclePosition` with:
   - `stop_price` from signal
   - `target_price` from signal
   - `exit_date` = D+3 (default), D+5 (high-vol stocks), extended for Thu/Fri entries
4. Anti-churning checks:
   - **Duplicate entry block:** No re-entry within 5 minutes of last entry for same symbol
   - **Cooldown after exit:** 60-minute cooldown after selling before re-buying same symbol
5. Submits `MarketOrderRequest` to Alpaca via `submit_order()`
6. Polls Alpaca up to 10 times (1 second apart) for fill confirmation
7. **Fill price divergence guard:** If actual fill price is >5% different from the signal price, the position is immediately unwound (sold back) and the entry is rejected
8. Updates `position.entry_price` with actual fill price
9. Recalculates stop/target from actual fill price

### Sell Order Flow

1. `order_manager.execute_sell_order(position, exit_price, reason)`
2. Anti-churning: Minimum 30-minute hold (unless stop loss or force exit)
3. Submits `MarketOrderRequest` (sell) to Alpaca
4. Captures fill price and calculates slippage
5. Records exit timestamp for cooldown tracking

### Entry Price Source Issue

The `signal.entry_price` comes from yfinance's daily `close` column — this is yesterday's closing price. The actual fill from Alpaca is at the current market price. The divergence guard catches cases where these differ by more than 5%, but a 1-4% difference is accepted silently. This means stop/target calculations start from a potentially stale price point.

---

## 7. Position Monitoring & Exit Logic

### Exit Check Architecture

There are **three separate exit check systems** that run for each position:

1. **SmartExitManager** (`smart_exit_manager.py`) — checked first
2. **ExitManager** (`exit_manager.py`) — checked if SmartExitManager says hold
3. **Position.should_smart_exit()** (`positions.py`) — also checked independently

If ANY of the three says exit, the position is sold.

### SmartExitManager — 8 Exit Strategies

**Code location:** `bot_v2/utils/smart_exit_manager.py`

Checked in this exact order:

| # | Strategy | Condition | Min Hold |
|---|----------|-----------|----------|
| 1 | Emergency Stop Loss | P&L ≤ -4% | None (always active) |
| 2 | Min Hold Wait | P&L > -4% AND held < 2 hours | Blocks all other exits |
| 3 | Quick Profit | P&L ≥ +4% | 48 hours |
| 4 | RSI Overbought | RSI ≥ 80 AND P&L > +1% | 48 hours |
| 5 | RSI Exhaustion | RSI ≥ 85 | 48 hours |
| 6 | Standard Profit Target | P&L ≥ +6% | None (immediate) |
| 7 | Volume Exhaustion | Volume < 0.5x avg AND RSI > 70 AND P&L > +2% | 48 hours |
| 8 | Time-Based Max Hold | Hours held ≥ 120 (5 days) | Forces exit regardless |

**Special cases:**
- **High-vol stocks** (NTLA, PL, OSCR, MRNA, PLUG, LCID, RIVN, NIO, MARA, RIOT, AMC, GME): Only emergency stop (-6%) and trailing stop. No RSI exits.
- **"Let Winners Run" mode:** If P&L ≥ +3%, switches to dynamic trailing stop only (no other exit triggers). Trail distance based on gain size: 1.5% gain → 1% trail, 5% → 2%, 10% → 3%, 15% → 3.5%, 20% → 4%, 30% → 5%.
- **Trailing stop activation:** `TRAILING_STOP_TRIGGER = 0.99` — effectively requires 99% gain to activate. **This means trailing stops are DISABLED in SmartExitManager.**

### ExitManager — Traditional Exits

**Code location:** `bot_v2/execution/exit_manager.py`

| Check | Condition | Action |
|-------|-----------|--------|
| Hard stop loss | P&L ≤ -4% (configurable per strategy) | Immediate exit |
| Trailing stop | Trigger at 99% gain | **Effectively disabled** |
| Profit target | P&L ≥ +6% | Exit |
| Time stop | Calendar days > max_hold_days + 2 (= 7 days) | Exit |
| Friday losers | Friday + P&L ≤ -2% | Exit at 3:30 PM |
| Earnings protection | Earnings within 3 days | Force exit |
| D+10 absolute | 10 calendar days held | Force exit |

### Position.should_smart_exit() — Embedded Exit Logic

**Code location:** `bot_v2/models/positions.py`

This has its OWN set of exit checks:

| Check | Condition |
|-------|-----------|
| Emergency stop | P&L ≤ -4% |
| Opening patience | Before 10 AM + not at stop → hold |
| Trailing stop active | If trailing is running → don't interfere |
| Profit target | P&L ≥ +6% |
| RSI overbought | RSI > 85 + P&L > 1% (requires market data) |
| RSI fading | RSI > 80 + 3+ days held + P&L > 1% |
| Time stop | 7+ calendar days held |
| Friday losers | Friday, 3:30 PM, P&L ≤ -3% |
| Quick profit low confidence | Signal confidence < 0.65 + P&L ≥ +4% |

### Trailing Stop System (Position Model)

**Code location:** `positions.py` — `update_trailing_stop()`

- Activates at +3% profit
- Trail distance: 2.5% (with adaptive 1.5%-2.5% based on momentum)
- Only moves upward, never down
- Checks if price has dropped below trailing stop price

**BUT:** The config parameter `enable_trailing_stops = False` and `trailing_trigger_pct = 0.99`. The SmartExitManager also has `TRAILING_STOP_TRIGGER = 0.99`. In practice, the trailing stop never activates because it would require the stock to gain 99%.

### Effective Exit Behavior

Given the above, the bot's ACTUAL exit behavior is:

1. **-4% stop loss** → exit immediately
2. **+6% profit target** → exit immediately
3. **120 hours (5 trading days) time stop** → exit regardless of P&L
4. **Friday at 3:30 PM if down >2-3%** → exit
5. That's it. No trailing stops. No RSI exits (require 48h hold + rare RSI levels).

This means the bot either hits its stop (-4%) or hits its target (+6%) or times out. Given that the risk/reward ratio is -4% to +6% (1.5:1), the bot needs a **40% win rate** just to break even. With a 17.1% win rate, losses dominate.

---

## 8. Data Sources & Price Fetching

### Primary Data Source: yfinance

**Code location:** `bot_v2/data/data_loader.py`

- **Free, no API key required**
- Returns **daily OHLCV bars** (not intraday, not real-time)
- Data delay: approximately 15-20 minutes after market events
- Rate limited: yfinance has per-IP rate limits that can cause failures

**`get_historical_data(symbol, days=100)`**:
- Downloads 100 calendar days of daily bars
- Normalizes column names to lowercase
- Returns a pandas DataFrame with columns: `open, high, low, close, volume`

**`get_current_price(symbol)`**:
- Calls yfinance to get latest data
- Returns the most recent `close` value
- **This is NOT a real-time price — it's the last daily close, which could be yesterday's close if called before end of day**

### Secondary Data Source: Alpaca API

Used for:
- **Order execution** (real-time): Market orders submitted and filled via Alpaca
- **Account info**: Portfolio value, cash, buying power
- **Position data**: Current holdings with market values
- **News sentiment**: Alpaca News API (free tier)
- **Price fetcher** (when available): Uses Alpaca ask price for real-time pricing

### Price Architecture Problem

The bot uses DIFFERENT price sources for different operations:

| Operation | Price Source | Latency |
|-----------|-------------|---------|
| PreFilter scan | yfinance daily bars | 15-20 min delay |
| Signal generation | yfinance close (yesterday or today) | Potentially 24h stale |
| Signal `entry_price` | yfinance close | Potentially 24h stale |
| Actual buy fill | Alpaca market order | Real-time |
| Exit monitoring `current_price` | Alpaca ask price (primary) / yfinance close (fallback) | 0-20 min delay |
| Actual sell fill | Alpaca market order | Real-time |
| Stop/target calculation | Based on signal's yfinance price | Stale base |

This means the bot may calculate a stop loss based on yesterday's closing price, while the actual entry fill is at today's market price — potentially 1-4% different.

---

## 9. Position Sync with Alpaca

**Code location:** `_sync_positions_with_alpaca()` in launcher.py

This runs during premarket startup. It's designed to reconcile the bot's internal position tracker with what Alpaca actually holds.

### What it does:

1. **Fetches Alpaca positions** — gets all current holdings
2. **Fetches tracker positions** — gets all positions from `positions.json`
3. **Orphaned Alpaca positions** (in Alpaca but not in tracker):
   - Creates a "dummy" `ShortCyclePosition`
   - Entry price = Alpaca's average cost
   - Signal confidence = 0.5, strategy = 'synced'
   - This position then gets monitored for exits

4. **Stale tracker positions** (in tracker but not in Alpaca):
   - Marks them as exited
   - Exit reason = "sync_cleanup"
   - Exit price = last known price from tracker
   - Realizes P&L based on entry vs last known price

### Problems with Position Sync:

This sync mechanism has been a major source of phantom P&L entries:

- When the bot creates a dummy synced position, the entry_price is from Alpaca (actual cost), which may differ significantly from the original signal price
- If a position was bought at signal price $21.23 but Alpaca reports avg_cost as $19.69 (because of a fill during a dip), the synced position has a different baseline
- When these synced positions are later exited, the P&L calculation uses the wrong baseline
- The `sync_cleanup` exits appear in P&L history as real losses/wins even though no actual trade occurred
- **Feb 25 example:** 4 positions from Feb 20 (SM, APA, AR, MGY) were all exited via this sync mechanism, recording material losses

---

## 10. Actual Performance Data

### From `pnl_history.json` (32 Trading Days)

| Period | Realized P&L | Wins | Losses | Win Rate |
|--------|-------------|------|--------|----------|
| Jan 13-17 | -$4.19 | 1 | 8 | 11.1% |
| Jan 19-23 | -$8.80 | 1 | 10 | 9.1% |
| Jan 26-30 | -$5.76 | 3 | 12 | 20.0% |
| Feb 2-6 | -$14.45 | 2 | 9 | 18.2% |
| Feb 9-13 | -$15.83 | 3 | 9 | 25.0% |
| Feb 17-21 | -$17.35 | 1 | 5 | 16.7% |
| Feb 23-25 | -$29.33 | 1 | 5 | 16.7% |
| **Total** | **-$95.71** | **12** | **58** | **17.1%** |

### From `trading_activity.log`

| Metric | Value |
|--------|-------|
| Total ENTRY events | 86 |
| Total EXIT events | 124 |
| Exit WINs | 60 |
| Exit LOSSes | 62 |
| Signal scans with 0 results | 760 |
| Signal scans with 1+ results | 121 |
| Signal success rate | 13.7% of scans |

**Note:** The activity log shows 60 wins / 62 losses (roughly 50/50), but pnl_history.json shows 12 wins / 58 losses. The discrepancy is because log "WIN" includes phantom wins from position sync (e.g., VFC on Feb 23 showed as +7.82% WIN in the log, but this was a sync artifact where the entry price was wrong).

### Recent Trading Activity (Last 8 Trading Days)

| Date | Candidates | Signals | Entries | Result |
|------|------------|---------|---------|--------|
| Feb 14-17 | 0 (holiday/none) | 0 | 0 | — |
| Feb 18 | 21 | 0 | 0 | No activity |
| Feb 19 | 20 | 0 | 0 | No activity |
| Feb 20 | 20 | 4 (one scan) | 4 | SM, APA, AR, MGY (all energy) |
| Feb 21 | — | — | — | Weekend |
| Feb 23 | 19 | 1 (one scan) | 1 | VFC (momentum) |
| Feb 24 | 15 | 0 | 0 | No activity |
| Feb 25 | 16 | 0 | 0 | 4 exits (energy positions) |

**The bot generated zero signals on 6 of the last 8 trading days.** On Feb 20, all 4 entries were clustered in a single scan at 10:05 AM, and all were energy sector stocks. On every other scan (dozens per day), zero signals were generated.

### Feb 25 Exit Details (Last Exits)

| Symbol | Entry | Exit | P&L | Reason |
|--------|-------|------|-----|--------|
| SM | $23.48 | $22.46 | -$6.12 (-4.34%) | STOP LOSS |
| APA | $29.08 | $28.62 | -$2.30 (-1.58%) | Max hold 120h |
| MGY | $27.08 | $27.19 | +$0.55 (+0.41%) | Max hold 120h (tiny win) |
| AR | $34.48 | $33.83 | -$2.60 (-1.89%) | Max hold 126h |

---

## 11. Root Cause Investigation

### Problem 1: The Bot Rarely Generates Signals (86.3% Empty Scans)

**Root cause:** The combination of pre-strategy filters and narrow strategy windows means almost no stocks qualify.

1. **20 EMA filter** eliminates stocks below their 20-day moving average — in a down or sideways market, this rejects the majority of candidates
2. **EMA slope filter** requires the trend to be actively rising over the last 3 bars — further reduces the pool
3. **Strategy time windows** are extremely narrow:
   - Gap & Go: 9:35-9:50 AM only (15 minutes!)
   - Fade/Short: Requires RSI > 70 + 10% above SMA20 (rare)
   - Momentum: Requires RSI 45-65 + 3-15% 5-day return + above SMA20 (specific)

4. **Result:** Even when 20 candidates pass the prefilter, the signal generator rejects all of them. The strategies were designed for a strongly trending bull market. In current conditions, almost nothing qualifies.

### Problem 2: When Signals DO Generate, They Cluster in One Sector

**Evidence:** Feb 20 — SM, APA, AR, MGY are all energy sector E&P companies. The bot has no sector diversification (the fix was recently added but hasn't been tested in production).

**Root cause:** When the EMA and momentum filters do pass, it tends to be for stocks moving together in the same sector rotation. The signal generator has no "sector spread" logic — it just picks the top N by confidence.

### Problem 3: Gap & Go Strategy Cannot Work With Delayed Data

**Root cause:** Gap & Go requires knowing the gap between today's open and yesterday's close. The bot uses yfinance daily bars:
- Before market close, yfinance may not have today's bar yet
- The signal generator checks at 9:45 AM, but yfinance may still show yesterday's data
- Even if today's data is available, the signal checks `current close > yesterday close` — but the "current close" is the most recent daily close (could be yesterday)
- **This means Gap & Go effectively never fires on delayed data**

Evidence: In the last 30 signal-producing scans, ALL signals were either Fade/Short or Momentum. Gap & Go has likely never produced a signal in production.

### Problem 4: Fade/Short Strategy Buys Instead of Shorts

**Root cause:** The "Fade/Short" strategy identifies overbought stocks (RSI > 70, 10%+ above SMA20) — these are stocks that should be sold short or faded (waited for reversal). But the execution code submits a **BUY** order. This means the bot is buying at the exact point a stock is most likely to reverse downward.

### Problem 5: Exit System Relies on Delayed Price Data

**Root cause:** The exit monitoring loop calls `data_loader.get_current_price()` which returns yfinance daily close — potentially yesterday's close. This means:
- Stop losses may not trigger when they should (price already past the stop)
- Profit targets may not trigger (price already past the target)
- Time stops (5 days) become the most common exit — by design they capture whatever P&L exists at that point, which is often negative

**Evidence from Feb 25:** 3 of 4 exits were "Max hold" (time stop), and the fourth was "STOP LOSS" — suggesting the stop was hit over the 5-day period but wasn't caught in real-time.

### Problem 6: Position Sync Creates Phantom P&L

**Root cause:** When the bot restarts or positions get out of sync:
- Dummy positions are created with Alpaca's cost basis (not the original signal price)
- When these positions are later exited, the P&L doesn't match reality
- Exit reasons like "sync_cleanup" and "position replaced" inflate/deflate the P&L history
- 38 more exits than entries (124 vs 86) suggests ~38 phantom exits

### Problem 7: Trailing Stops Are Disabled But Code Complexity Remains

**Root cause:** `TRAILING_STOP_TRIGGER = 0.99` (99% gain required). No stock will gain 99% in a 5-day hold period. This means the only exits are:
- -4% stop loss (downside limited to $6 per $150 position)
- +6% profit target (upside limited to $9 per $150 position)
- Time stop at 5 days (exits at whatever P&L exists)

The risk/reward is 1.5:1 (+$9 max vs -$6 max), requiring 40% win rate to break even. Actual win rate is 17.1%.

### Problem 8: PreFilter Universe is Too Narrow and Static

**Root cause:** The 4,718-symbol universe was loaded in October 2025 and never refreshed. Only ~257 have cached data, and only 15-21 pass the 3-stage filter. Combined with the signal generator's EMA/momentum filters, the effective tradeable universe on any given day is often ZERO stocks.

### Problem 9: No Intraday Data at Any Point in the Pipeline

The entire system — prefilter, signal generation, exit monitoring — runs on yfinance daily bars. There is no intraday data (1-min, 5-min, 15-min bars) anywhere in the pipeline. Every strategy's logic is evaluated against the last known daily close, not real-time prices. The only real-time element is the actual order fill from Alpaca.

---

## 12. Complete Parameter Reference

### Portfolio & Sizing Parameters

| Parameter | Value | Location |
|-----------|-------|----------|
| `portfolio_value` | Fetched from Alpaca (fallback $1,000) | trading_config.py |
| `daily_pool_percent` | 45% | trading_config.py |
| `max_position_dollars` | $150 | trading_config.py |
| `max_risk_per_trade_dollars` | $30 | trading_config.py |
| `max_loss_per_trade_dollars` | $30 | trading_config.py |
| `min_position_size_dollars` | $50 | trading_config.py |
| `max_position_size_percent` | 15% | trading_config.py |
| `max_positions_per_day` | 5 | trading_config.py |
| `max_daily_entries` | 5 | trading_config.py |

### Market Cap Filter

| Parameter | Value |
|-----------|-------|
| `min_market_cap` | $2,000,000,000 ($2B) |
| `max_market_cap` | $10,000,000,000 ($10B) |
| `require_market_cap_verification` | True (reject if can't verify) |

### Time & Hold Parameters

| Parameter | Value |
|-----------|-------|
| `max_hold_days` | 5 trading days |
| `default_hold_days` | 3 trading days |
| `high_vol_hold_days` | 5 trading days |
| `exit_time` | 15:45 ET |
| `friday_force_exit_enabled` | False |
| `friday_exit_losers_only` | True |
| `friday_loser_threshold` | -2% |
| `weekend_hold_enabled` | True |

### Stop/Target Parameters

| Parameter | Value |
|-----------|-------|
| `stop_loss_pct` | 4% |
| `profit_target_pct` | 6% |
| `enable_trailing_stops` | False |
| `trailing_trigger_pct` | 99% (disabled) |
| `trailing_distance_pct` | 99% (disabled) |
| `max_daily_loss_percent` | 8% |
| `max_weekly_loss_percent` | 15% |

### Strategy-Specific Stops

| Strategy | Stop | Target |
|----------|------|--------|
| Gap & Go | 4% | 6% |
| Fade/Short | 3% | 4% |
| Momentum | 4% | 6% |

### Strategy Allocations

| Strategy | Allocation | Enabled |
|----------|------------|---------|
| Gap & Go | 70% | Yes |
| Fade/Short | 15% | Yes |
| Momentum | 15% | Yes |
| Gap & Go priority | Yes (wins conflicts) | — |

### Gap & Go Parameters

| Parameter | Value |
|-----------|-------|
| `gap_min_pct` | 2% |
| `gap_max_pct` | 8% |
| `gap_rsi_max` | 75 |
| `gap_scan_time` | 09:35 ET |

### Fade/Short Parameters

| Parameter | Value |
|-----------|-------|
| `fade_rsi_min` | 70 |
| `fade_extension_min_pct` | 10% above 20-SMA |
| `fade_min_volume_surge` | 1.3x |
| `fade_scan_start` | 10:00 ET |
| `fade_scan_end` | 14:00 ET |

### Momentum Parameters

| Parameter | Value |
|-----------|-------|
| `momentum_sma_period` | 20 |
| `momentum_rsi_min` | 45 |
| `momentum_rsi_max` | 65 |
| `momentum_min_adr_pct` | 2% |
| `momentum_min_5d_return` | 3% |
| `momentum_max_5d_return` | 15% |
| `momentum_scan_start` | 10:30 ET |
| `momentum_scan_end` | 14:30 ET |

### PreFilter Parameters

| Parameter | Value |
|-----------|-------|
| Price range | $10 – $50 |
| Volume range | 3M – 30M shares/day |
| Dollar volume minimum | $30M/day |
| ATR% range | 3.5% – 6.0% |
| Min data rows | 15 |

### Confidence & Quality Parameters

| Parameter | Value |
|-----------|-------|
| `confidence_threshold` | 0.25 (base) |
| Dynamic threshold range | 0.25 → 0.55 |
| Late entry multiplier | 1.2x |
| Late entry position size | 75% |
| Late entry min ADR | 2.5% |

### SmartExitManager Parameters

| Parameter | Value |
|-----------|-------|
| `QUICK_PROFIT_TARGET` | 4% |
| `STANDARD_PROFIT_TARGET` | 6% |
| `RSI_NORMALIZATION` | 80 |
| `RSI_QUICK_EXIT` | 85 |
| `TRAILING_STOP_TRIGGER` | 99% (disabled) |
| `MIN_HOLD_HOURS` | 48 |
| `MAX_HOLD_HOURS` | 120 (5 days) |
| `EMERGENCY_DOLLAR_THRESHOLD` | $10 |
| `EMERGENCY_PCT_THRESHOLD` | -6% |
| `LET_WINNERS_RUN_THRESHOLD` | 3% |
| `LET_WINNERS_RUN_TRAIL` | 1.5% |

### Anti-Churning Parameters

| Parameter | Value |
|-----------|-------|
| `min_hold_time_minutes` | 30 |
| `entry_cooldown_minutes` | 60 |
| `duplicate_entry_window_minutes` | 5 |

### Timing Parameters

| Phase | Sleep/Interval |
|-------|---------------|
| Entry window scan interval | ~7 minutes (prefilter duration + processing) |
| Late entry scan interval | 15 minutes |
| Exit monitoring interval | 60 seconds |
| Closed market check | 300 seconds |
| Trailing stop update | 60 seconds |

---

## Summary of Key Structural Issues

1. **Data source mismatch:** Daily bars from yfinance (free, delayed) power all decisions, but orders execute at real-time Alpaca prices. Strategies designed for intraday signals (Gap & Go) cannot function with daily data.

2. **Signal drought:** The EMA trend filter + EMA slope filter + narrow strategy windows = zero signals on most days. The bot went 6 of 8 trading days with zero entries in the latest period.

3. **Contradictory Fade/Short strategy:** Identifies stocks to short (overbought, extended) but buys them long. This is the opposite of the intended direction.

4. **No working trailing stops:** Both config and SmartExitManager set trailing trigger at 99%, making the exit system binary: either hit -4% stop or +6% target or 5-day time-out.

5. **Position sync creates phantom P&L:** Dummy positions from Alpaca sync generate artificial wins/losses that distort performance tracking.

6. **Universe staleness:** 4,718-symbol universe from Oct 2025, never refreshed. Effective daily universe is 15-21 stocks after prefilter.

7. **Win rate too low for risk/reward:** The 1.5:1 R:R (-4% stop / +6% target) needs 40% wins to break even. Actual: 17.1%. The strategies are selecting stocks that go down more often than they go up within the 5-day hold window.

---

## 13. Fixes Applied (Feb 25, 2026)

### Tier 1 — Strategy Fixes (Immediate)

| Fix | File | Change | Impact |
|-----|------|--------|--------|
| Disable Gap & Go | `trading_config.py` | `enable_gap_and_go=False`, allocation=0% | Removes strategy that can't work with daily bars |
| Disable Fade/Short | `trading_config.py` | `enable_fade_short=False`, allocation=0% | Removes broken buy-instead-of-short strategy |
| Momentum sole strategy | `trading_config.py` | `momentum_allocation=1.00` | Only viable strategy gets full capital |
| Trail stops re-enabled | `trading_config.py` + `smart_exit_manager.py` | trigger=3%, trail=2% (was 99%/99%) | Locks in gains on trend continuation |
| EMA slope loosened | `signal_generator.py` | `< -0.5%` (was `<= 0`) | Allows flat markets, only rejects clear downtrends |
| Phantom P&L fixed | `launcher.py` | 3 sync paths set P&L=$0.00 instead of fabricating | Stops fake gains/losses from position sync |

### Tier 2 — Real-Time Data (Critical Infrastructure)

| Fix | File | Change | Impact |
|-----|------|--------|--------|
| Broken Alpaca import | `data_loader.py` | `StockMarketDataClient` → `StockHistoricalDataClient` | Import was failing silently since day 1 |
| Broken API method | `data_loader.py` | `get_latest_trade()` → `get_stock_latest_trade()` | Method didn't exist on correct client |
| New Alpaca helper | `alpaca_data_helper.py` (NEW) | Snapshot, batch prices, intraday bars | Clean real-time data layer via Alpaca IEX |
| Exit price fix | `launcher.py` → `_get_realtime_price()` | Uses Alpaca helper (was referencing non-existent `self.trading_engine.api`) | Exit monitoring had NO real-time prices — always None, fell back to daily close |
| Exit fallback fix | `launcher.py` → exit monitoring | Removed stale `get_historical_data(days=1)` fallback | Was using yesterday's close for exit decisions |
| Signal RT prices | `signal_generator.py` | New `set_realtime_prices()` + last-close override | Entry signals now use real-time prices, not yesterday's close |
| Launcher RT inject | `launcher.py` → `_run_entry_scan()` + `_run_late_entry_scan()` | Batch Alpaca price fetch before each scan | All scan cycles get real-time data |
| Universe cleanup | `mid_cap_universe.json` | Removed 19 delisted/inactive symbols | 274 → 255 active tradeable stocks |

### Critical Bugs Discovered During Tier 2

1. **`StockMarketDataClient` doesn't exist** in the installed alpaca-py SDK. The `data_loader.py` import silently fell back to `None`, meaning `get_current_price()` NEVER used Alpaca IEX — it always fell back to yfinance daily close.

2. **`_get_realtime_price()` in launcher.py** referenced `self.trading_engine.api.get_latest_quote()` — but `RealPaperTradingEngine` has `self.client` (not `self.api`), and `TradingClient` doesn't have `get_latest_quote()` (that's the old alpaca-trade-api v1 API). This method returned `None` on EVERY call.

3. **Exit monitoring fallback** used `data_loader.get_historical_data(symbol, days=1)` which returns daily bars — meaning exit decisions during market hours used YESTERDAY'S close, not the current price. A stock dropping 4% intraday wouldn't trigger the stop loss until the next day.

### Test Results

**33 assertions, all passing:**
- 9 Tier 1 config assertions (strategies, allocations, trailing stops)
- 5 SmartExitManager assertions (trailing, hold times)
- 6 Alpaca data client assertions (init, prices, snapshots, batch)
- 3 Signal generator RT price assertions (injection, override)
- 4 Universe assertions (cleaned, delisted removed)
- 6 File compilation assertions (all 6 modified files compile clean)

---

*Document generated from direct code analysis of production files. All values, parameters, and behaviors reflect what the code actually does, not what comments or documentation say it should do.*

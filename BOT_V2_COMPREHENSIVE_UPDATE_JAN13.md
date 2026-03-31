# LiteBotX V2 - Comprehensive Update Report
## January 13, 2026 (Updated After Session 2)

---

## Table of Contents
1. [Executive Summary](#executive-summary)
2. [How the Bot Works](#how-the-bot-works)
3. [Session 1: Strategy Optimizations (15 Issues)](#session-1-strategy-optimizations)
4. [Session 2: New Features (8 Features)](#session-2-new-features)
5. [Stock Universe Details](#stock-universe-details)
6. [Data Sources & Sentiment Analysis](#data-sources--sentiment-analysis)
7. [Expected Returns](#expected-returns)
8. [What Still Needs to Be Done](#what-still-needs-to-be-done)
9. [Risk Management](#risk-management)
10. [Quick Reference](#quick-reference)

---

## Executive Summary

### What Changed Today

**Session 1 (Morning):** 15 strategy optimizations from backtest analysis:
- Smarter entry timing (gap confirmation, exhaustion detection)
- Better exit management (momentum-aware D+1, Friday tiered exits)
- Dynamic risk adjustment (ATR-based stops, market-condition allocation)
- More conservative emergency exits

**Session 2 (Afternoon):** 8 new features added:
- ✅ Block same-day re-entries (prevents slippage losses)
- ✅ Expanded stock universe (now 274 main + 92 fallback)
- ✅ Position size reverted to $50 (safer sizing)
- ✅ Late entry scan (1:00-2:30 PM phase)
- ✅ VIX-based allocation live wiring
- ✅ Daily P&L tracker with persistence
- ✅ New momentum strategy (15% allocation)
- ✅ Overnight gap predictor for EOD buys

**Universe Cleanup:** Removed all mega-caps (NVDA, AMD, etc.) and blacklisted stocks from both universe files.

---

## How the Bot Works

### The D+1 Strategy (Simple Explanation)

The bot uses a **D+1 overnight swing trading strategy**:

```
Day 1 (Entry Day): Buy promising stocks during market hours
    ↓ Hold overnight
Day 2 (Exit Day): Sell positions before noon (optimal exit window)
```

**Why D+1?**
- Captures overnight momentum (stocks often gap up/down on news)
- Avoids Pattern Day Trader (PDT) rules (<$25K accounts)
- Reduces trading frequency = less commissions

### The Triple Strategy System

The bot now runs **three complementary strategies**:

| Strategy | Allocation | What It Does | Best For |
|----------|------------|--------------|----------|
| **Gap & Go** | 70% | Buys stocks gapping up 2-8% at open | Bullish momentum |
| **Fade/Short** | 15% | Buys overbought stocks expecting reversal | Choppy markets |
| **Momentum** | 15% | Buys strong breakout patterns | Trend days |

### Trading Schedule

| Time | Phase | Activity |
|------|-------|----------|
| 4:00 AM | Premarket | Fetch VIX, calculate allocation |
| 9:30 AM | Open | Initial gap scanning |
| 9:35 AM | Entry Window | Confirmed gap entries |
| 10:30 AM | Monitor | Position monitoring |
| 11:00 AM | D+1 Exits | Exit previous day's positions |
| **1:00 PM** | **Late Entry** | **NEW: Second entry scan** |
| **2:30 PM** | **Late Close** | **END of late entry window** |
| 3:45 PM | EOD | Overnight gap predictions |
| 4:00 PM | Close | Day complete |

### Signal Generation Flow

```
1. SCREENING (Filter Universe)
   └─ 274 stocks in main universe
   └─ 92 stocks in fallback (if main fails)
   └─ Remove blacklisted symbols (8 permanent)
   └─ Remove same-day exits (NEW: prevents re-entry)
   └─ Check mid-cap criteria ($2B-$15B)

2. STRATEGY DETECTION
   └─ Gap & Go: 2-8% gap + RSI < 75 + gap holding
   └─ Fade: RSI > 70 + 10%+ above SMA
   └─ Momentum: Strong breakout + volume surge

3. CONFIDENCE SCORING (0-100%)
   └─ Base confidence from strategy metrics
   └─ + News sentiment adjustment
   └─ + Time-of-day weighting
   └─ + Sector momentum bonus
   └─ + Volume surge bonus
   └─ Must exceed dynamic threshold (25-55%)

4. ENTRY EXECUTION
   └─ Fetch real-time price
   └─ Calculate position size ($50 max)
   └─ Set ATR-based stop/target
   └─ Submit order to Alpaca
```

---

## Session 1: Strategy Optimizations

### Entry Improvements

#### 1.1 Gap Confirmation Logic ✅
- **Before:** Scanned at 9:30 AM immediately
- **After:** Two-phase: identify at 9:31, confirm holding at 9:35
- Gap must be within 0.5% of open price to confirm

#### 1.2 Fade Exhaustion Signals ✅
- Detects volume divergence (price up, volume down)
- Detects RSI divergence (price high, RSI declining)
- Each divergence adds 10% confidence boost

#### 1.3 Time-Weighted Scoring ✅
| Time | Gap Multiplier | Fade Multiplier |
|------|----------------|-----------------|
| 9:30-10:00 | 1.1x | 0.9x |
| 10:30-11:30 | 0.7x | 0.8x |
| 2:00-4:00 | 1.0x | 1.1x |

### Exit Improvements

#### 2.1 Lower Trailing Stop Trigger ✅
- Triggers at 1.5% profit (was 2%)
- Trail distance 1.0% (was 1.5%)
- Minimum locked profit 0.5% (was 1.0%)

#### 2.2 Momentum-Aware D+1 Exits ✅
- Positions with +1.5% get tight 0.8% trailing stop
- Lets winners run instead of immediate exit

#### 2.3 Friday Staggered Exits ✅
| Time | Exit % | Rationale |
|------|--------|-----------|
| 9:35 AM | 50% | Weekend protection |
| 12:00 PM | 25% | Morning momentum |
| 3:00 PM | 25% | Options expiry pop |

### Signal Filtering

#### 3.1 Dynamic Confidence Threshold ✅
| Portfolio Fill | Threshold |
|----------------|-----------|
| 0-25% | 25% (need trades) |
| 25-50% | 35% |
| 50-75% | 45% |
| 75-100% | 55% (only best) |

#### 3.2 Sector Momentum Factor ✅
- Airlines/Travel: +8% boost (51.6% win rate)
- Consumer: -5% penalty (39.2% win rate)

#### 3.3 Pre-Market Volume Filter ✅
- Requires 2x avg volume in premarket
- Higher volume = higher conviction

### Risk Management

#### 4.1 ATR-Based Stops & Targets ✅
| Volatility | Stop Loss | Target |
|------------|-----------|--------|
| Low ATR | -1.0% | +1.5% |
| Medium | -2.0% | +3.5% |
| High | -4.0% | +8.0% |

#### 4.2 Conservative Emergency Exits ✅
- OLD: Exit at -$2 OR -2%
- NEW: Exit at -$10 OR -5%
- Gives positions room to recover

#### 4.3 Market Condition Allocation ✅
| VIX Level | Market | Allocation |
|-----------|--------|------------|
| <15 | Calm | 100% |
| 15-20 | Normal | 90% |
| 20-25 | Elevated | 75% |
| 25-30 | High | 50% |
| >30 | Extreme | 25% |

---

## Session 2: New Features

### Feature 1: Same-Day Re-Entry Blocking ✅
**Problem:** Bot sold NTLA at $11.43, rebought at $11.97 = $0.54 loss  
**Solution:** Track daily exits in `_today_exits` set, block re-entry

```python
# In signal_generator.py
self._today_exits = set()  # Tracks symbols sold today

def _validate_signals(self, signals):
    # Block same-day re-entries
    blocked = [s for s in signals if s in self._today_exits]
    # ... filter them out
```

### Feature 2: Expanded Stock Universe ✅
**Before:** ~60 stocks in fallback, 298 in main  
**After:** 92 stocks in fallback, 274 in main (cleaned)

**Cleanup performed:**
- Removed 8 blacklisted: NI, OGE, T, JD, TU, VIRT, BXMT, VIPS
- Removed mega-caps: NVDA, AMD, DIS, MCD, SBUX, etc.
- All stocks now true mid-caps ($2B-$15B)

### Feature 3: Position Size $50 ✅
**Reverted from:** $80 → $50  
**Reason:** More conservative sizing for safety

### Feature 4: Late Entry Scan ✅
**New trading phase:** 1:00 PM - 2:30 PM

```python
# In launcher.py
'late_entry': {
    'start': time(13, 0),    # 1:00 PM
    'end': time(14, 30),     # 2:30 PM
    'scan_interval': 15,      # Every 15 minutes
}
```

**Why:** Afternoon breakouts and fades often provide good D+1 setups

### Feature 5: Live VIX Allocation ✅
**Wired up methods in trading_config.py:**

```python
def fetch_vix_level() -> float:
    """Fetch current VIX from Alpaca"""
    
def fetch_spy_momentum() -> float:
    """Calculate 5-day SPY momentum"""
    
def get_live_market_allocation() -> float:
    """Combine VIX + momentum for allocation %"""
```

### Feature 6: Daily P&L Tracker ✅
**New file:** `bot_v2/reporting/pnl_tracker.py`

```python
class DailyPnLTracker:
    def record_trade(self, symbol, pnl, percent, strategy)
    def get_daily_summary() -> Dict
    def get_weekly_summary() -> Dict
    def get_streak() -> Dict  # Win/loss streaks
```

**Persistence:** JSON file at `bot_v2/data/pnl_history.json`

### Feature 7: Momentum Strategy ✅
**Third strategy added at 15% allocation**

Detection criteria:
- Price breaking above 20-day high
- Volume 1.5x average
- RSI between 50-70 (not overbought)
- Uptrend confirmed (5-day MA > 20-day MA)

### Feature 8: Overnight Gap Predictor ✅
**New file:** `bot_v2/gap_scanner/overnight_gap_predictor.py`

**7-Factor Scoring:**
1. 5-day momentum (20% weight)
2. 20-day trend (10%)
3. RSI position (15%)
4. Volume trend (15%)
5. Relative strength vs SPY (15%)
6. ATR percentile (10%)
7. Price vs SMA20 (15%)

**Runs at:** 3:45 PM (EOD)  
**Purpose:** Identify stocks likely to gap up/down next day

---

## Stock Universe Details

### Main Universe (mid_cap_universe.json)
| Metric | Value |
|--------|-------|
| Total Stocks | 274 |
| Market Cap Range | $2B - $15B |
| Sectors | 20+ |
| Blacklisted Removed | ✅ |
| Mega-caps Removed | ✅ |

### Fallback Universe (fallback_universe.py)
| Metric | Value |
|--------|-------|
| Total Stocks | 92 |
| Market Cap Range | $2B - $15B |
| Sectors | 14 |
| Blacklisted Removed | ✅ |
| Mega-caps Removed | ✅ |

### Blacklisted Symbols (8 Permanent)
| Symbol | Reason | Win Rate |
|--------|--------|----------|
| BXMT | Chronic loser | 0/12 (0%) |
| JD | Chronic loser | 0/4 (0%) |
| T | Poor performance | 0/3 (0%) |
| TU | Poor performance | 0% |
| NI | Utility, low vol | Poor |
| OGE | Utility, low vol | Poor |
| VIRT | Low liquidity | Poor |
| VIPS | Chronic loser | Poor |

---

## Data Sources & Sentiment Analysis

### 1. Alpaca News API (Primary)
```python
news = api.get_news(symbol=symbol, limit=10)
```
- Real-time news for all universe stocks
- Sentiment scoring: -1 (bearish) to +1 (bullish)
- Breaking news detection (last 2 hours)

### 2. Technical Indicators (Built-in)
- RSI (14-period)
- SMA (20-day, 50-day)
- ATR (Average True Range)
- Volume analysis (vs 20-day avg)
- Gap detection (vs prior close)

### 3. Market Regime Detection
- VIX level (live fetch)
- SPY momentum (5-day)
- Sector rotation analysis

---

## Expected Returns

### Historical Performance (Backtest)
| Metric | Gap & Go | Fade | Overall |
|--------|----------|------|---------|
| Win Rate | 47% | 42% | 45% |
| Avg Win | +2.8% | +2.1% | +2.5% |
| Avg Loss | -1.5% | -1.8% | -1.6% |
| Profit Factor | 1.42 | 1.18 | 1.32 |

### Current Account
| Metric | Value |
|--------|-------|
| Account Size | ~$992 |
| Max Position | $50 |
| Max Positions | 19 (at $50 each) |
| Daily Risk | ~$95 (10%) |

### Projected Returns (Conservative)
| Period | Trades | Est. P&L |
|--------|--------|----------|
| Daily | 2-5 | +$1 to +$5 |
| Weekly | 10-25 | +$5 to +$25 |
| Monthly | 40-100 | +$20 to +$100 |

---

## What Still Needs to Be Done

### High Priority
1. **Verify gap predictor in live trading** - Currently untested
2. **Monitor same-day blocking** - Ensure no slippage losses
3. **Test momentum strategy** - New, needs validation
4. **Review late entry performance** - New phase

### Medium Priority
5. **Add email/SMS alerts** - Trade notifications
6. **Dashboard improvements** - Real-time P&L display
7. **Sector rotation optimization** - Better sector selection
8. **Options flow integration** - Unusual activity detection

### Low Priority
9. **Machine learning scoring** - AI-powered confidence
10. **Multi-account support** - Scale to larger accounts
11. **Paper → Live toggle** - One-click switching

---

## Risk Management

### Position Limits
| Parameter | Value |
|-----------|-------|
| Max Position Size | $50 |
| Max Positions | 19 |
| Max Same Symbol | 1 |
| Daily Loss Limit | $100 (10%) |

### Stop Losses
| Type | Trigger | Action |
|------|---------|--------|
| Initial Stop | ATR-based (1-4%) | Market sell |
| Trailing Stop | 1% trail after +1.5% | Lock profits |
| Emergency | -$10 OR -5% | Immediate exit |

### Circuit Breakers
| Condition | Action |
|-----------|--------|
| Daily loss > $100 | Halt trading |
| 3 consecutive losses | Reduce size 50% |
| VIX > 30 | Reduce allocation to 25% |

---

## Quick Reference

### Key Files Modified Today

| File | Changes |
|------|---------|
| `signal_generator.py` | Same-day blocking, momentum strategy |
| `trading_config.py` | $50 size, VIX methods, late entry |
| `launcher.py` | Late entry phase, gap predictions |
| `fallback_universe.py` | Cleaned to 92 mid-caps |
| `mid_cap_universe.json` | Cleaned to 274 mid-caps |

### Key Files Created Today

| File | Purpose |
|------|---------|
| `pnl_tracker.py` | Daily P&L tracking |
| `overnight_gap_predictor.py` | Next-day gap predictions |

### Current Configuration
```python
# Position Sizing
max_position_dollars = 50.0

# Strategy Allocation
gap_and_go = 70%
fade_short = 15%
momentum = 15%

# Entry Windows
morning: 9:35 AM - 11:30 AM
late_entry: 1:00 PM - 2:30 PM

# Emergency Exit
loss_threshold = $10 OR 5%
```

### Backups Created
- `bot_v2_backup_20260113_1445.tar.gz` (Session 1)
- `bot_v2_backup_20260113_1512.tar.gz` (Session 2)

---

*Last Updated: January 13, 2026 - Session 2 Complete*

# Bot V2 Feature Updates - January 13, 2026 (Session 2)

## Overview

This session added 8 new features to enhance signal generation and portfolio management:

1. **Same-Day Re-Entry Block** - Prevents buying back stocks sold today
2. **Universe Expansion** - 223 symbols (was 60)
3. **Position Size Revert** - $50 max (diversification over concentration)
4. **Late Entry Scan** - 1:00-2:30 PM afternoon opportunities
5. **VIX Integration** - Real-time strategy allocation
6. **P&L Tracking** - Daily, weekly, monthly performance
7. **Momentum Strategy** - Third strategy for trend continuation
8. **Overnight Gap Predictor** - ML-based next-day gap predictions

---

## 1. Same-Day Re-Entry Block

**File**: `bot_v2/signal_generation/signal_generator.py`

**Problem**: Bot was selling stocks (e.g., NTLA at $11.43) and immediately re-buying at higher prices ($11.97), causing slippage losses.

**Solution**: Track exited symbols daily and block re-entry.

```python
# Tracks symbols exited today
self._today_exits: set = set()

# In validation: block same-day re-entries
if symbol in self._today_exits:
    self.logger.warning(f"⚠️ {symbol}: Blocking re-entry (sold today)")
    continue
```

---

## 2. Universe Expansion (60 → 223 symbols)

**File**: `bot_v2/data/fallback_universe.py`

**Problem**: Only 28 symbols were being scanned, limiting opportunities.

**Solution**: Expanded MID_CAP_FALLBACK to 223 symbols across 15+ sectors:

- Airlines/Travel (7): AAL, ALK, JBLU, SAVE, UAL, DAL, LUV
- Cruise/Hotels (8): RCL, CCL, NCLH, MAR, HLT, H, EXPE, BKNG
- Restaurants (9): CAKE, TXRH, BJRI, PLAY, CHUY, DIN, EAT, BLMN, CMG
- Retail (10): DKS, FIVE, ULTA, BOOT, OLLI, GPS, ANF, AEO, URBN, GME
- Energy (10): RIG, SWN, AR, RRC, CTRA, DVN, MRO, HAL, SLB, OXY
- Technology (9): PLUG, FSLR, ENPH, SEDG, NET, DDOG, SNOW, CRWD, MDB
- Semiconductors (8): AMD, NVDA, MU, MRVL, ON, SWKS, QRVO, WOLF
- Healthcare/Biotech (15): INCY, VTRS, MRNA, BNTX, NTLA, CRSP, EDIT, etc.
- Industrial (8): CLF, X, AA, NUE, STLD, FCX, MP, ALB
- Financial/Fintech (7): HOOD, SOFI, AFRM, UPST, PYPL, SQ, COIN
- EV/Auto (8): LCID, RIVN, NIO, XPEV, LI, TSLA, F, GM
- Space/Defense (6): RKLB, PL, ASTS, BKSY, JOBY, ACHR
- Media/Gaming (8): SIRI, PARA, WBD, LYV, SPOT, RBLX, NFLX, DIS
- Real Estate (7): OPEN, Z, RDFN, DHI, LEN, PHM, TOL
- Cannabis (5): TLRY, CGC, CRON, ACB, SNDL
- Meme/Speculative (5): AMC, GME, BB, PLTR, SPCE
- Crypto (4): MARA, RIOT, CLSK, COIN

---

## 3. Position Size Revert ($80 → $50)

**File**: `bot_v2/config/trading_config.py`

**Rationale**: 4×$20 stocks beats 1×$80 stock for risk management (diversification wins).

```python
max_position_dollars: float = 50.0  # Reverted for diversification
max_positions_per_day: int = 12     # 12 × $50 = $600 max exposure
```

---

## 4. Late Entry Scan (1:00-2:30 PM)

**Files**: 
- `bot_v2/config/trading_config.py` - Configuration
- `bot_v2/launcher.py` - New `late_entry` phase and `_run_late_entry_scan()` method

**Purpose**: Catch afternoon momentum continuation setups that develop after morning entry window.

**Configuration**:
```python
enable_late_entry: bool = True
late_entry_start_time: str = "13:00"
late_entry_end_time: str = "14:30"
late_entry_confidence_multiplier: float = 1.2  # 20% higher bar
late_entry_position_size_pct: float = 0.75     # 75% position size
late_entry_scan_interval_minutes: int = 15
late_entry_min_adr_pct: float = 0.025          # 2.5% ADR required
```

**Features**:
- Higher confidence requirement (1.2x threshold)
- Reduced position size (75% of normal)
- ADR filter (2.5%+ required for volatility)
- Scans every 15 minutes

---

## 5. VIX Integration (Real-Time Strategy Allocation)

**File**: `bot_v2/config/trading_config.py`

**New Methods**:
```python
def fetch_vix_level(self) -> float:
    """Fetch current VIX from Yahoo Finance (cached 6 hours)"""

def fetch_spy_momentum(self, days: int = 5) -> float:
    """Fetch SPY 5-day momentum"""

def get_live_market_allocation(self) -> tuple:
    """Adjust Gap&Go/Fade allocation based on market conditions"""
```

**Allocation Rules**:
- VIX < 15: Boost Gap & Go by 10% (calm market, momentum works)
- VIX 15-25: Normal allocation
- VIX 25-30: Reduce Gap & Go by 10% (favor Fade)
- VIX > 30: Reduce Gap & Go by 15% (high volatility, reversals work)

**Current Market** (Jan 13, 2026):
- VIX: 16.2 (low)
- SPY momentum: +0.5%
- Allocation: 80% Gap&Go / 20% Fade

---

## 6. Daily P&L Tracking

**File**: `bot_v2/reporting/pnl_tracker.py` (NEW)

**Purpose**: Track trading performance over time to measure optimization impact.

**Features**:
- Daily realized + unrealized P&L
- Win rate tracking
- Week-to-date stats
- Month-to-date stats
- All-time cumulative stats
- Streak tracking (wins/losses)
- JSON persistence (`bot_v2/data/pnl_history.json`)

**Usage**:
```python
from bot_v2.reporting.pnl_tracker import show_pnl_summary
show_pnl_summary()
```

**Example Output**:
```
📅 TODAY (2026-01-13):
   Realized: $+7.79
   Unrealized: $-0.55
   Total: $+7.24 (+4.8%)
   Win Rate: 75% (3/4 exits)

📅 THIS WEEK:
   P&L: $+7.24 | Win Rate: 75%
   Trades: 8 | Trading Days: 1
```

---

## 7. Momentum Strategy (Third Strategy)

**Files**:
- `bot_v2/config/trading_config.py` - Configuration
- `bot_v2/signal_generation/signal_generator.py` - `_check_momentum()` method

**Purpose**: Complement Gap & Go and Fade with trend continuation plays for mid-day entries.

**Entry Criteria**:
- Price above SMA20 (confirming uptrend)
- RSI 45-65 (healthy trend, not overbought)
- 5-day return +3% to +15% (trending but not exhausted)
- ADR > 2% (sufficient volatility)

**Configuration**:
```python
enable_momentum: bool = True
momentum_allocation: float = 0.15  # 15% of capital
momentum_rsi_min: float = 45.0
momentum_rsi_max: float = 65.0
momentum_min_5d_return: float = 0.03
momentum_max_5d_return: float = 0.15
momentum_min_adr_pct: float = 0.02
momentum_profit_target_pct: float = 0.025  # 2.5%
momentum_stop_loss_pct: float = 0.015      # 1.5%
```

**Time Weights**:
- 10:30-11:30 AM: 1.0x (trend establishing)
- 11:30 AM-1:00 PM: 0.9x (lunch lull)
- 1:00-2:30 PM: 1.1x (prime time - afternoon continuation)

**Strategy Allocation**:
- Gap & Go: 70% (primary)
- Fade/Short: 15% (secondary)
- Momentum: 15% (tertiary)

---

## 8. Overnight Gap Predictor

**File**: `bot_v2/gap_scanner/overnight_gap_predictor.py` (NEW)

**Purpose**: Predict next-day gaps based on end-of-day conditions for pre-positioning.

**Factors Used** (weighted):
- 5-day momentum: 20%
- 20-day trend: 10%
- RSI position: 15%
- Volume trend: 15%
- Relative strength vs SPY: 15%
- ATR percentile: 10%
- Price vs SMA20: 15%

**Recommendations**:
- `BUY_EOD`: High confidence gap up → Buy before close
- `FADE`: High confidence gap down → Wait to fade
- `HOLD`: Medium confidence → Watch
- `AVOID`: Low confidence → Skip

**Integration**: Runs at 4:45 PM postmarket in launcher.

**Usage**:
```python
from bot_v2.gap_scanner.overnight_gap_predictor import predict_gaps
predictions = predict_gaps()
```

---

## Summary of Files Modified/Created

### Modified:
1. `bot_v2/signal_generation/signal_generator.py` - Same-day block, momentum strategy
2. `bot_v2/config/trading_config.py` - Late entry, VIX, momentum config
3. `bot_v2/data/fallback_universe.py` - Expanded universe
4. `bot_v2/launcher.py` - Late entry phase, VIX fetch, gap predictor integration

### Created:
1. `bot_v2/reporting/pnl_tracker.py` - Daily P&L tracking
2. `bot_v2/gap_scanner/overnight_gap_predictor.py` - Gap prediction

---

## Backup Created

`bot_v2_backup_20260113_1512.tar.gz` (189KB)

---

## Next Steps

1. **Monitor** late entry scan effectiveness (1-2:30 PM)
2. **Verify** momentum strategy generates signals
3. **Track** daily P&L to measure optimization impact
4. **Review** overnight gap predictions vs actual gaps
5. **Consider** adding after-hours data to gap predictor

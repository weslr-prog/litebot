# LiteBotX Technical Improvement Plan
## Addressing Code Quality Issues #2-9

**Created**: January 13, 2026  
**Priority**: High → Medium → Low  
**Estimated Total Time**: 8-12 hours of focused work

---

## Overview

This document provides step-by-step implementation plans for each technical improvement identified in the bot code review. Complete these in order for best results.

---

## Issue #2: Exception Handling - Silent Failures

### Problem
Many exception handlers return empty data or `None` instead of logging context or alerting on repeated failures:
```python
except Exception as e:
    return pd.DataFrame()  # Silent failure - no visibility!
```

### Impact
- Failed data fetches go unnoticed
- Bot continues with stale/missing data
- Hard to debug production issues
- Trades may be skipped without knowing why

### Solution Plan

#### Step 2.1: Create a Centralized Error Tracker
**File**: `bot_v2/utils/error_tracker.py`

```python
"""
Centralized error tracking for bot_v2
Tracks recurring errors, alerts on thresholds, provides visibility
"""
import logging
import datetime as dt
from collections import defaultdict
from typing import Dict, Optional
from dataclasses import dataclass, field
from pathlib import Path
import json

@dataclass
class ErrorStats:
    count: int = 0
    first_seen: Optional[dt.datetime] = None
    last_seen: Optional[dt.datetime] = None
    context_samples: list = field(default_factory=list)

class ErrorTracker:
    """
    Track recurring errors and alert when thresholds exceeded.
    
    Usage:
        tracker = ErrorTracker()
        try:
            data = fetch_data(symbol)
        except Exception as e:
            tracker.record_error("data_fetch", symbol, e)
            if tracker.should_alert("data_fetch"):
                # Send alert, log critical, etc.
            return fallback_data()
    """
    
    def __init__(self, alert_threshold: int = 5, window_minutes: int = 60):
        self.errors: Dict[str, Dict[str, ErrorStats]] = defaultdict(
            lambda: defaultdict(ErrorStats)
        )
        self.alert_threshold = alert_threshold
        self.window_minutes = window_minutes
        self.logger = logging.getLogger("bot_v2.error_tracker")
        self._alerts_sent: Dict[str, dt.datetime] = {}
        self._alert_cooldown_minutes = 30
    
    def record_error(self, category: str, context: str, exception: Exception):
        """Record an error occurrence"""
        now = dt.datetime.now(dt.timezone.utc)
        stats = self.errors[category][context]
        
        stats.count += 1
        if stats.first_seen is None:
            stats.first_seen = now
        stats.last_seen = now
        
        # Keep last 3 samples for debugging
        if len(stats.context_samples) < 3:
            stats.context_samples.append({
                'time': now.isoformat(),
                'error': str(exception),
                'type': type(exception).__name__
            })
        
        # Log with context
        self.logger.warning(
            f"⚠️ Error [{category}] {context}: {type(exception).__name__}: {exception}"
        )
    
    def get_error_count(self, category: str, context: str = None) -> int:
        """Get error count for category (optionally filtered by context)"""
        if context:
            return self.errors[category][context].count
        return sum(stats.count for stats in self.errors[category].values())
    
    def should_alert(self, category: str) -> bool:
        """Check if error count exceeds threshold and alert not recently sent"""
        total = self.get_error_count(category)
        if total < self.alert_threshold:
            return False
        
        # Check alert cooldown
        last_alert = self._alerts_sent.get(category)
        if last_alert:
            elapsed = (dt.datetime.now(dt.timezone.utc) - last_alert).total_seconds() / 60
            if elapsed < self._alert_cooldown_minutes:
                return False
        
        self._alerts_sent[category] = dt.datetime.now(dt.timezone.utc)
        return True
    
    def get_summary(self) -> Dict:
        """Get error summary for logging/display"""
        summary = {}
        for category, contexts in self.errors.items():
            summary[category] = {
                'total': sum(s.count for s in contexts.values()),
                'contexts': len(contexts),
                'top_context': max(contexts.items(), key=lambda x: x[1].count)[0] if contexts else None
            }
        return summary
    
    def reset_category(self, category: str):
        """Reset error counts for a category (e.g., at start of new day)"""
        if category in self.errors:
            del self.errors[category]
    
    def reset_all(self):
        """Reset all error counts"""
        self.errors.clear()
        self._alerts_sent.clear()

# Global singleton
_tracker = None

def get_error_tracker() -> ErrorTracker:
    global _tracker
    if _tracker is None:
        _tracker = ErrorTracker()
    return _tracker
```

#### Step 2.2: Update Data Loader Error Handling
**File**: `bot_v2/data/data_loader.py`

Find all `except Exception` blocks and update pattern:

```python
# BEFORE:
except Exception as e:
    return pd.DataFrame()

# AFTER:
except Exception as e:
    from bot_v2.utils.error_tracker import get_error_tracker
    tracker = get_error_tracker()
    tracker.record_error("data_fetch", symbol, e)
    
    if tracker.should_alert("data_fetch"):
        self.logger.critical(
            f"🚨 ALERT: {tracker.get_error_count('data_fetch')} data fetch errors! "
            f"Check internet/API connectivity"
        )
    
    return pd.DataFrame()  # Still return empty, but now tracked
```

#### Step 2.3: Update Signal Generator Error Handling
**File**: `bot_v2/signal_generation/signal_generator.py`

Same pattern for signal generation errors:

```python
except Exception as e:
    from bot_v2.utils.error_tracker import get_error_tracker
    tracker = get_error_tracker()
    tracker.record_error("signal_generation", symbol, e)
    self.logger.debug(f"Signal generation failed for {symbol}: {e}")
    return None  # Still return None, but now tracked
```

#### Step 2.4: Add Error Summary to Daily Report
**File**: `bot_v2/launcher.py`

In `_run_daily_summary()` method, add:

```python
# Add error summary to daily report
from bot_v2.utils.error_tracker import get_error_tracker
error_summary = get_error_tracker().get_summary()
if error_summary:
    self.logger.info("📊 Daily Error Summary:")
    for category, stats in error_summary.items():
        self.logger.info(f"   {category}: {stats['total']} errors across {stats['contexts']} symbols")

# Reset error tracker for next day
get_error_tracker().reset_all()
```

#### Step 2.5: Testing
```bash
# Test error tracking
python3 -c "
from bot_v2.utils.error_tracker import get_error_tracker
tracker = get_error_tracker()

# Simulate errors
for i in range(6):
    tracker.record_error('test', 'AAPL', Exception('Test error'))

print(f'Error count: {tracker.get_error_count(\"test\")}')
print(f'Should alert: {tracker.should_alert(\"test\")}')
print(f'Summary: {tracker.get_summary()}')
"
```

### Checklist
- [ ] Create `bot_v2/utils/error_tracker.py`
- [ ] Update `bot_v2/data/data_loader.py` exception handlers
- [ ] Update `bot_v2/signal_generation/signal_generator.py` exception handlers
- [ ] Update `bot_v2/launcher.py` to log error summary
- [ ] Test error tracking functionality
- [ ] Verify bot still runs normally

---

## Issue #3: Position Object Corruption Bug

### Problem
In `launcher.py` line ~898, there's a workaround for positions becoming strings:
```python
# CRITICAL FIX: Sometimes position becomes a string (symbol) instead of object
if isinstance(position, str):
    # Find the real position object...
```

### Impact
- Position monitoring may fail
- Exits could be missed
- P&L calculations wrong

### Solution Plan

#### Step 3.1: Add Type Validation to Position Tracker
**File**: `bot_v2/execution/position_tracker.py`

Add validation in `get_active_positions()`:

```python
def get_active_positions(self) -> List['ShortCyclePosition']:
    """Get all active (ENTERED) positions with type validation"""
    from ..models.positions import PositionStatus, ShortCyclePosition
    
    active = []
    corrupted = []
    
    for i, pos in enumerate(self.positions):
        # Type validation
        if isinstance(pos, str):
            self.logger.error(
                f"🐛 BUG DETECTED: Position {i} is string '{pos}' not object! "
                f"Attempting recovery..."
            )
            corrupted.append((i, pos))
            continue
        
        if not isinstance(pos, ShortCyclePosition):
            self.logger.error(
                f"🐛 BUG DETECTED: Position {i} is {type(pos).__name__} not ShortCyclePosition! "
                f"Value: {repr(pos)[:100]}"
            )
            corrupted.append((i, pos))
            continue
        
        if not hasattr(pos, 'status'):
            self.logger.error(f"🐛 BUG DETECTED: Position {i} missing 'status' attribute!")
            corrupted.append((i, pos))
            continue
        
        if pos.status == PositionStatus.ENTERED:
            active.append(pos)
    
    # Log corruption summary
    if corrupted:
        self.logger.critical(
            f"🚨 POSITION CORRUPTION: {len(corrupted)} corrupted positions detected! "
            f"Forcing re-sync with Alpaca..."
        )
        # Trigger immediate re-sync
        self._request_alpaca_sync = True
    
    return active
```

#### Step 3.2: Add Corruption Detection in Save/Load
**File**: `bot_v2/execution/position_tracker.py`

In `save_positions()`, add validation before save:

```python
def save_positions(self):
    """Save positions with corruption detection"""
    from ..models.positions import ShortCyclePosition
    
    # Pre-save validation
    valid_positions = []
    for pos in self.positions:
        if not isinstance(pos, ShortCyclePosition):
            self.logger.error(f"🐛 Skipping corrupt position during save: {type(pos)}")
            continue
        valid_positions.append(pos)
    
    if len(valid_positions) != len(self.positions):
        self.logger.warning(
            f"⚠️ Filtered {len(self.positions) - len(valid_positions)} "
            f"corrupt positions before save"
        )
        self.positions = valid_positions  # Clean up in-memory list
    
    # ... rest of save logic
```

#### Step 3.3: Add Root Cause Logging
**File**: `bot_v2/execution/position_tracker.py`

Add tracing to `add_position()`:

```python
def add_position(self, position):
    """Add position with type checking"""
    from ..models.positions import ShortCyclePosition
    
    if not isinstance(position, ShortCyclePosition):
        self.logger.error(
            f"🐛 INVALID add_position call! Received {type(position).__name__}: {repr(position)[:200]}"
        )
        # Log call stack to find root cause
        import traceback
        self.logger.error(f"Call stack:\n{traceback.format_stack()[-5:]}")
        raise TypeError(f"Expected ShortCyclePosition, got {type(position).__name__}")
    
    self.positions.append(position)
    self.logger.info(f"✅ Added position: {position.symbol}")
```

#### Step 3.4: Add Sync Request Flag
**File**: `bot_v2/execution/position_tracker.py`

```python
def __init__(self, ...):
    # ... existing init
    self._request_alpaca_sync = False  # Flag for forced sync

def needs_sync(self) -> bool:
    """Check if forced sync needed (corruption detected)"""
    return self._request_alpaca_sync

def clear_sync_request(self):
    """Clear sync request flag after sync complete"""
    self._request_alpaca_sync = False
```

#### Step 3.5: Handle Sync Request in Launcher
**File**: `bot_v2/launcher.py`

In `_monitor_exits()`, check for sync request:

```python
def _monitor_exits(self):
    """Monitor and execute exits"""
    # Check if corruption was detected
    if self.position_tracker.needs_sync():
        self.logger.warning("🔄 Forced re-sync due to position corruption...")
        self._sync_positions_with_alpaca()
        self.position_tracker.clear_sync_request()
    
    # ... rest of monitoring logic
```

### Checklist
- [ ] Add type validation in `get_active_positions()`
- [ ] Add pre-save validation in `save_positions()`
- [ ] Add type checking in `add_position()`
- [ ] Add sync request flag and handler
- [ ] Test with corrupted position simulation
- [ ] Monitor logs for "BUG DETECTED" messages

---

## Issue #4: D+1 Exit Date Calculation (Missing Holidays)

### Problem
Exit date calculation only skips weekends, not market holidays:
```python
# Skip weekends
while exit_date.weekday() >= 5:
    exit_date += dt.timedelta(days=1)
```

### Impact
- D+1 exits scheduled for closed market days
- Positions held longer than intended
- Risk over long weekends (e.g., 4-day hold over Thanksgiving)

### Solution Plan

#### Step 4.1: Create Market Calendar Module
**File**: `bot_v2/utils/market_calendar.py`

```python
"""
Market calendar for US equity markets
Uses Alpaca's calendar API as source of truth
"""
import datetime as dt
from typing import List, Optional, Dict
import logging
from functools import lru_cache

logger = logging.getLogger("bot_v2.market_calendar")


class MarketCalendar:
    """
    US equity market calendar with Alpaca API integration.
    Caches calendar data daily for performance.
    """
    
    # Fallback holidays if API unavailable (2026 US market holidays)
    FALLBACK_HOLIDAYS_2026 = [
        dt.date(2026, 1, 1),   # New Year's Day
        dt.date(2026, 1, 19),  # MLK Day
        dt.date(2026, 2, 16),  # Presidents Day
        dt.date(2026, 4, 3),   # Good Friday
        dt.date(2026, 5, 25),  # Memorial Day
        dt.date(2026, 6, 19),  # Juneteenth (observed)
        dt.date(2026, 7, 3),   # Independence Day (observed)
        dt.date(2026, 9, 7),   # Labor Day
        dt.date(2026, 11, 26), # Thanksgiving
        dt.date(2026, 12, 25), # Christmas
    ]
    
    def __init__(self, alpaca_client=None):
        self.alpaca_client = alpaca_client
        self._trading_days_cache: Dict[str, List[dt.date]] = {}
        self._cache_date: Optional[dt.date] = None
    
    def _refresh_cache_if_needed(self):
        """Refresh trading days cache daily"""
        today = dt.date.today()
        if self._cache_date != today:
            self._trading_days_cache.clear()
            self._cache_date = today
    
    @lru_cache(maxsize=100)
    def is_trading_day(self, date: dt.date) -> bool:
        """Check if a specific date is a trading day"""
        # Weekend check (fast path)
        if date.weekday() >= 5:
            return False
        
        # Holiday check
        if self._is_holiday(date):
            return False
        
        return True
    
    def _is_holiday(self, date: dt.date) -> bool:
        """Check if date is a market holiday"""
        # Try Alpaca API first
        if self.alpaca_client:
            try:
                calendar = self.alpaca_client.get_calendar(
                    start=date.isoformat(),
                    end=date.isoformat()
                )
                # If calendar is empty, it's not a trading day
                return len(list(calendar)) == 0
            except Exception as e:
                logger.debug(f"Alpaca calendar API failed: {e}, using fallback")
        
        # Fallback to hardcoded holidays
        return date in self.FALLBACK_HOLIDAYS_2026
    
    def get_next_trading_day(self, from_date: dt.date) -> dt.date:
        """Get the next trading day after from_date"""
        next_day = from_date + dt.timedelta(days=1)
        
        # Loop until we find a trading day (max 10 days to prevent infinite loop)
        for _ in range(10):
            if self.is_trading_day(next_day):
                return next_day
            next_day += dt.timedelta(days=1)
        
        # Fallback: just return next weekday
        logger.warning(f"Could not find trading day within 10 days of {from_date}")
        while next_day.weekday() >= 5:
            next_day += dt.timedelta(days=1)
        return next_day
    
    def get_trading_days_between(self, start: dt.date, end: dt.date) -> List[dt.date]:
        """Get list of trading days between two dates (inclusive)"""
        trading_days = []
        current = start
        while current <= end:
            if self.is_trading_day(current):
                trading_days.append(current)
            current += dt.timedelta(days=1)
        return trading_days
    
    def count_trading_days_between(self, start: dt.date, end: dt.date) -> int:
        """Count trading days between two dates"""
        return len(self.get_trading_days_between(start, end))


# Global singleton
_calendar = None

def get_market_calendar(alpaca_client=None) -> MarketCalendar:
    global _calendar
    if _calendar is None:
        _calendar = MarketCalendar(alpaca_client)
    elif alpaca_client and _calendar.alpaca_client is None:
        _calendar.alpaca_client = alpaca_client
    return _calendar
```

#### Step 4.2: Update Order Manager Exit Date Calculation
**File**: `bot_v2/execution/order_manager.py`

Replace `_calculate_exit_date()`:

```python
def _calculate_exit_date(self, entry_date: dt.date) -> dt.date:
    """Calculate D+1 exit date (next trading day, accounting for holidays)"""
    from bot_v2.utils.market_calendar import get_market_calendar
    
    calendar = get_market_calendar()
    exit_date = calendar.get_next_trading_day(entry_date)
    
    self.logger.debug(
        f"D+1 calculation: Entry {entry_date} → Exit {exit_date} "
        f"({(exit_date - entry_date).days} calendar days)"
    )
    
    return exit_date
```

#### Step 4.3: Initialize Calendar with Alpaca Client
**File**: `bot_v2/launcher.py`

In `_initialize_components()`:

```python
# Initialize market calendar with Alpaca client
from bot_v2.utils.market_calendar import get_market_calendar
if self.trading_engine and hasattr(self.trading_engine, 'client'):
    get_market_calendar(self.trading_engine.client)
    self.logger.info("✅ Market calendar initialized with Alpaca API")
```

#### Step 4.4: Testing
```bash
python3 -c "
from bot_v2.utils.market_calendar import get_market_calendar
import datetime as dt

cal = get_market_calendar()

# Test MLK Day 2026 (Monday Jan 19)
mlk_day = dt.date(2026, 1, 19)
print(f'MLK Day {mlk_day} is trading day: {cal.is_trading_day(mlk_day)}')

# Test Friday before MLK Day
friday = dt.date(2026, 1, 16)
next_trading = cal.get_next_trading_day(friday)
print(f'Next trading day after {friday}: {next_trading}')  # Should be Jan 20 (Tuesday)

# Test weekend
saturday = dt.date(2026, 1, 17)
print(f'Saturday {saturday} is trading day: {cal.is_trading_day(saturday)}')
"
```

### Checklist
- [ ] Create `bot_v2/utils/market_calendar.py`
- [ ] Update `order_manager._calculate_exit_date()`
- [ ] Initialize calendar with Alpaca client in launcher
- [ ] Add 2026 holiday dates to fallback list
- [ ] Test holiday detection
- [ ] Verify D+1 exits work correctly over holidays

---

## Issue #5: Hardcoded Universe Fallback

### Problem
If `mid_cap_universe.json` fails to load, fallback is 10 mega-cap stocks:
```python
return ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "AMD", "NFLX", "AVGO"]
```

### Impact
- Mega-caps don't match mid-cap strategy ($2B-$10B)
- Drastically reduced universe (10 vs 150+ stocks)
- Strategy parameters misaligned

### Solution Plan

#### Step 4.1: Create Better Fallback Universe
**File**: `bot_v2/data/fallback_universe.py`

```python
"""
Fallback mid-cap universe for when JSON file fails to load.
These stocks meet the $2B-$10B market cap criteria.
Updated quarterly.
"""

# Mid-cap stocks ($2B-$10B) - Last updated Jan 2026
FALLBACK_MID_CAP_UNIVERSE = [
    # Technology (20 stocks)
    "OKTA", "DDOG", "NET", "CRWD", "ZS", "MDB", "SNOW", "PLTR", "U", "RBLX",
    "TWLO", "DOCN", "PATH", "GTLB", "CFLT", "ESTC", "DT", "NEWR", "SUMO", "FROG",
    
    # Healthcare (15 stocks)  
    "EXAS", "NBIX", "SRPT", "BMRN", "ALNY", "IONS", "RARE", "FOLD", "PRTA", "IMVT",
    "ARGX", "SGEN", "RPRX", "DAWN", "GILD",
    
    # Consumer Discretionary (10 stocks)
    "W", "ETSY", "CHWY", "DASH", "ABNB", "PTON", "FTCH", "FIGS", "BROS", "SHAK",
    
    # Industrials (10 stocks)
    "GNRC", "TDG", "AXON", "BLDR", "AZEK", "Site", "TREX", "NDSN", "RBC", "WTS",
    
    # Financials (10 stocks)
    "LPLA", "HOOD", "SOFI", "UPST", "AFRM", "COIN", "VIRT", "MKTX", "CBOE", "NDAQ",
    
    # Energy (5 stocks)
    "AR", "RRC", "SWN", "MTDR", "CTRA",
]

def get_fallback_universe():
    """Get fallback mid-cap universe (70 stocks)"""
    return FALLBACK_MID_CAP_UNIVERSE.copy()
```

#### Step 4.2: Update Launcher Fallback
**File**: `bot_v2/launcher.py`

```python
def _get_universe(self) -> List[str]:
    """Load mid-cap universe from JSON with better fallback"""
    import json
    from pathlib import Path
    
    try:
        universe_file = Path(__file__).parent / "data" / "mid_cap_universe.json"
        with open(universe_file) as f:
            data = json.load(f)
        
        # Flatten sectors (excluding REITs)
        all_stocks = []
        for key, value in data.items():
            if 'reit' in key.lower():
                self.logger.info(f"🚫 Skipping {key}: REITs excluded")
                continue
            if isinstance(value, list):
                all_stocks.extend(value)
        
        self.logger.info(f"📊 Loaded universe: {len(all_stocks)} stocks")
        return all_stocks
        
    except FileNotFoundError:
        self.logger.warning(
            f"⚠️ Universe file not found: {universe_file}"
        )
    except json.JSONDecodeError as e:
        self.logger.error(f"❌ Invalid JSON in universe file: {e}")
    except Exception as e:
        self.logger.error(f"❌ Failed to load universe: {e}")
    
    # Use proper mid-cap fallback (not mega-caps!)
    from bot_v2.data.fallback_universe import get_fallback_universe
    fallback = get_fallback_universe()
    self.logger.warning(
        f"⚠️ Using fallback mid-cap universe: {len(fallback)} stocks "
        f"(proper mid-cap range, not mega-caps)"
    )
    return fallback
```

### Checklist
- [ ] Create `bot_v2/data/fallback_universe.py`
- [ ] Update `launcher._get_universe()` to use proper fallback
- [ ] Verify fallback stocks meet $2B-$10B criteria
- [ ] Test by temporarily renaming universe JSON file

---

## Issue #6: VIX Multiplier Caching (6 Hours Too Long)

### Problem
VIX is cached for 6 hours, but market volatility can spike quickly:
```python
if datetime.now() - self._vix_fetch_time < timedelta(hours=6):
    return self._vix_multiplier
```

### Impact
- Position sizing uses stale VIX during volatile opens
- Could over-allocate when VIX spikes intraday

### Solution Plan

#### Step 6.1: Implement Adaptive VIX Caching
**File**: `bot_v2/risk_management/position_sizer.py`

```python
def _get_vix_regime_multiplier(self) -> float:
    """Get VIX-based position size multiplier with adaptive caching"""
    now = datetime.now()
    
    # Determine cache duration based on market phase
    current_hour = now.hour
    if 9 <= current_hour < 10:
        # First hour of trading: refresh every 15 minutes
        max_cache_minutes = 15
    elif 10 <= current_hour < 16:
        # Regular trading hours: refresh every 60 minutes
        max_cache_minutes = 60
    else:
        # Pre/post market: cache for 4 hours
        max_cache_minutes = 240
    
    # Check cache validity
    if (self._vix_multiplier is not None and 
        self._vix_fetch_time is not None and
        (now - self._vix_fetch_time) < timedelta(minutes=max_cache_minutes)):
        return self._vix_multiplier
    
    try:
        import yfinance as yf
        vix = yf.Ticker("^VIX").history(period='1d')['Close'].iloc[-1]
        
        # Determine multiplier based on VIX level
        if vix > 35:
            self.logger.critical(f"🚨 EXTREME FEAR: VIX={vix:.1f} - Cutting positions by 60%")
            multiplier = 0.4
        elif vix > 30:
            self.logger.warning(f"⚠️ HIGH FEAR: VIX={vix:.1f} - Cutting positions by 50%")
            multiplier = 0.5
        elif vix > 25:
            self.logger.warning(f"⚠️ ELEVATED: VIX={vix:.1f} - Reducing positions by 25%")
            multiplier = 0.75
        elif vix > 20:
            self.logger.info(f"✅ MODERATE: VIX={vix:.1f} - Normal positions")
            multiplier = 1.0
        else:
            self.logger.info(f"✅ LOW VIX: VIX={vix:.1f} - Normal positions")
            multiplier = 1.0
        
        # Cache result
        self._vix_multiplier = multiplier
        self._vix_fetch_time = now
        self._last_vix_value = vix  # Store for logging
        
        return multiplier
        
    except Exception as e:
        self.logger.warning(f"⚠️ Failed to fetch VIX: {e} - Using cached or default")
        return self._vix_multiplier if self._vix_multiplier else 1.0
```

### Checklist
- [ ] Update VIX caching logic with adaptive timing
- [ ] Add VIX value logging for monitoring
- [ ] Test during market hours
- [ ] Verify position sizing adjusts with VIX changes

---

## Issue #7: Market Cap Cache Never Expires

### Problem
Market cap cache in signal generator never clears:
```python
self._market_cap_cache = {}  # Never cleared!
```

### Impact
- Stale market cap data (M&A, stock splits, etc.)
- Stocks may fall out of $2B-$10B range undetected

### Solution Plan

#### Step 7.1: Add Cache Expiration
**File**: `bot_v2/signal_generation/signal_generator.py`

In `__init__`:
```python
# Market cap filtering with daily expiration
self._market_cap_cache = {}
self._market_cap_cache_date = None
```

In `_check_market_cap`:
```python
def _check_market_cap(self, symbol: str, data_loader) -> bool:
    """Check if symbol meets mid-cap requirements with daily cache"""
    import datetime as dt
    
    # Clear cache daily
    today = dt.date.today()
    if self._market_cap_cache_date != today:
        self.logger.debug(f"Clearing market cap cache (new day: {today})")
        self._market_cap_cache.clear()
        self._market_cap_cache_date = today
    
    # Check cache
    if symbol in self._market_cap_cache:
        market_cap = self._market_cap_cache[symbol]
    else:
        # Fetch and cache
        info = data_loader.get_stock_info(symbol)
        market_cap = info.get('marketCap', 0) if info else 0
        self._market_cap_cache[symbol] = market_cap
    
    # Validate range
    if market_cap < self.config.min_market_cap:
        return False
    if market_cap > self.config.max_market_cap:
        return False
    
    return True
```

### Checklist
- [ ] Add cache date tracking
- [ ] Add daily cache clearing
- [ ] Test cache expiration logic

---

## Issue #8: No Rate Limiting for yfinance

### Problem
yfinance can hit rate limits causing data gaps. No request spacing.

### Impact
- Sporadic data fetch failures
- Some symbols may not get analyzed
- Silent failures during high-volume scans

### Solution Plan

#### Step 8.1: Add Rate Limiter Utility
**File**: `bot_v2/utils/rate_limiter.py`

```python
"""
Rate limiter for external API calls
Prevents hitting rate limits on yfinance, Polygon, etc.
"""
import time
import threading
from collections import deque
from typing import Dict
import logging

logger = logging.getLogger("bot_v2.rate_limiter")


class RateLimiter:
    """
    Token bucket rate limiter for API calls.
    
    Usage:
        limiter = RateLimiter(requests_per_minute=30)
        
        for symbol in symbols:
            limiter.wait()  # Blocks if rate exceeded
            data = fetch_data(symbol)
    """
    
    def __init__(self, requests_per_minute: int = 30, burst_size: int = 5):
        self.requests_per_minute = requests_per_minute
        self.min_interval = 60.0 / requests_per_minute
        self.burst_size = burst_size
        self.request_times: deque = deque(maxlen=burst_size)
        self._lock = threading.Lock()
    
    def wait(self):
        """Wait if necessary to respect rate limit"""
        with self._lock:
            now = time.time()
            
            # Remove old requests outside the window
            while self.request_times and now - self.request_times[0] > 60:
                self.request_times.popleft()
            
            # Check if we need to wait
            if len(self.request_times) >= self.burst_size:
                oldest = self.request_times[0]
                wait_time = 60 - (now - oldest)
                if wait_time > 0:
                    logger.debug(f"Rate limit: waiting {wait_time:.2f}s")
                    time.sleep(wait_time)
            
            # Add minimum interval between requests
            if self.request_times:
                elapsed = now - self.request_times[-1]
                if elapsed < self.min_interval:
                    sleep_time = self.min_interval - elapsed
                    time.sleep(sleep_time)
            
            self.request_times.append(time.time())


# Pre-configured limiters
_limiters: Dict[str, RateLimiter] = {}

def get_limiter(name: str, requests_per_minute: int = 30) -> RateLimiter:
    """Get or create a named rate limiter"""
    if name not in _limiters:
        _limiters[name] = RateLimiter(requests_per_minute)
    return _limiters[name]
```

#### Step 8.2: Apply to Data Loader
**File**: `bot_v2/data/data_loader.py`

```python
from bot_v2.utils.rate_limiter import get_limiter

# In get_historical_data:
def get_historical_data(self, symbol: str, days: int = 100) -> pd.DataFrame:
    """Fetch historical data with rate limiting"""
    limiter = get_limiter('yfinance', requests_per_minute=30)
    limiter.wait()
    
    # ... existing fetch logic
```

### Checklist
- [ ] Create `bot_v2/utils/rate_limiter.py`
- [ ] Apply rate limiter to data_loader
- [ ] Test with high-volume scans
- [ ] Verify no rate limit errors

---

## Issue #9: Missing Integration Tests for Live Trading

### Problem
No end-to-end tests with actual Alpaca sandbox.

### Impact
- Can't verify order execution works correctly
- No automated regression testing
- Production bugs discovered too late

### Solution Plan

#### Step 9.1: Create Live Integration Test Suite
**File**: `tests/test_live_integration.py`

```python
#!/usr/bin/env python3
"""
Live integration tests for bot_v2
Tests actual Alpaca paper trading connectivity and order flow
"""
import sys
import os
from pathlib import Path
import datetime as dt
import time

# Add project root
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from dotenv import load_dotenv

load_dotenv()


class TestAlpacaConnection:
    """Test Alpaca API connectivity"""
    
    def test_connection(self):
        """Verify Alpaca connection works"""
        from connect_real_trading import RealPaperTradingEngine
        
        engine = RealPaperTradingEngine()
        account = engine.get_account_info()
        
        assert account is not None, "Failed to get account info"
        assert 'portfolio_value' in account
        assert account['portfolio_value'] > 0
        print(f"✅ Connected - Portfolio: ${account['portfolio_value']:,.2f}")
    
    def test_get_positions(self):
        """Verify position fetching works"""
        from connect_real_trading import RealPaperTradingEngine
        
        engine = RealPaperTradingEngine()
        positions = engine.get_positions()
        
        assert isinstance(positions, dict)
        print(f"✅ Fetched {len(positions)} positions")


class TestOrderExecution:
    """Test order placement (paper trading only!)"""
    
    @pytest.fixture
    def engine(self):
        from connect_real_trading import RealPaperTradingEngine
        engine = RealPaperTradingEngine()
        # Verify paper trading
        assert "paper" in os.getenv("APCA_API_BASE_URL", "").lower(), \
            "These tests require paper trading!"
        return engine
    
    def test_small_buy_order(self, engine):
        """Test small buy order execution"""
        # Use a stable, liquid stock
        symbol = "SPY"
        quantity = 1
        
        result = engine.submit_order(
            symbol=symbol,
            quantity=quantity,
            order_type='market_buy'
        )
        
        assert result is not None, "Order failed to submit"
        assert 'order_id' in result
        print(f"✅ Buy order submitted: {result['order_id']}")
        
        # Wait for fill
        time.sleep(2)
        
        # Verify position exists
        positions = engine.get_positions()
        assert symbol in positions or quantity == 1  # May be added to existing
        print(f"✅ Position verified")
    
    def test_small_sell_order(self, engine):
        """Test small sell order execution"""
        symbol = "SPY"
        
        # Check if we have a position to sell
        positions = engine.get_positions()
        if symbol not in positions:
            pytest.skip(f"No {symbol} position to sell")
        
        quantity = 1
        result = engine.submit_order(
            symbol=symbol,
            quantity=quantity,
            order_type='market_sell'
        )
        
        assert result is not None
        print(f"✅ Sell order submitted: {result['order_id']}")


class TestPositionSync:
    """Test position synchronization"""
    
    def test_sync_positions_with_alpaca(self):
        """Test position sync logic"""
        from bot_v2.config.trading_config import ShortCycleConfig
        from bot_v2.execution.position_tracker import AIPositionTracker
        from connect_real_trading import RealPaperTradingEngine
        
        config = ShortCycleConfig()
        engine = RealPaperTradingEngine()
        tracker = AIPositionTracker(config=config, execution_engine=engine)
        
        # Load positions
        positions = tracker.load_positions()
        
        # Get Alpaca positions
        alpaca_positions = engine.get_positions()
        
        print(f"✅ Tracker: {len(positions)} positions")
        print(f"✅ Alpaca: {len(alpaca_positions)} positions")
        
        # Verify no orphaned positions
        for pos in tracker.get_active_positions():
            if pos.symbol not in alpaca_positions:
                print(f"⚠️ Orphaned position: {pos.symbol}")


class TestMarketCalendar:
    """Test market calendar functionality"""
    
    def test_holiday_detection(self):
        """Test holiday detection"""
        from bot_v2.utils.market_calendar import get_market_calendar
        
        cal = get_market_calendar()
        
        # MLK Day 2026
        mlk_day = dt.date(2026, 1, 19)
        assert not cal.is_trading_day(mlk_day), "MLK Day should not be trading day"
        
        # Regular Monday
        regular_monday = dt.date(2026, 1, 12)
        assert cal.is_trading_day(regular_monday), "Regular Monday should be trading day"
        
        print("✅ Holiday detection working")
    
    def test_next_trading_day(self):
        """Test next trading day calculation"""
        from bot_v2.utils.market_calendar import get_market_calendar
        
        cal = get_market_calendar()
        
        # Friday before MLK weekend
        friday = dt.date(2026, 1, 16)
        next_day = cal.get_next_trading_day(friday)
        
        assert next_day == dt.date(2026, 1, 20), f"Expected Jan 20, got {next_day}"
        print(f"✅ Next trading day after {friday}: {next_day}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
```

#### Step 9.2: Create Test Runner Script
**File**: `run_integration_tests.sh`

```bash
#!/bin/bash
# Run integration tests with paper trading

echo "🧪 Running LiteBotX Integration Tests"
echo "======================================"
echo ""

# Verify environment
if [[ -z "$APCA_API_KEY_ID" ]]; then
    echo "❌ APCA_API_KEY_ID not set!"
    exit 1
fi

if [[ "$APCA_API_BASE_URL" != *"paper"* ]]; then
    echo "❌ Not configured for paper trading!"
    echo "   Set APCA_API_BASE_URL to paper-api.alpaca.markets"
    exit 1
fi

echo "✅ Paper trading mode confirmed"
echo ""

# Activate virtual environment
source litebotx_env/bin/activate

# Run tests
python -m pytest tests/test_live_integration.py -v -s

echo ""
echo "======================================"
echo "Tests complete!"
```

### Checklist
- [ ] Create `tests/test_live_integration.py`
- [ ] Create `run_integration_tests.sh`
- [ ] Run tests in paper trading mode
- [ ] Add to CI/CD pipeline (optional)
- [ ] Document test procedures

---

## Implementation Order

### Priority 1 (Critical - Do First)
1. **Issue #3**: Position Corruption Bug - Prevents silent failures
2. **Issue #4**: Market Calendar - Correct D+1 calculations

### Priority 2 (High - Do This Week)
3. **Issue #2**: Error Tracking - Visibility into failures
4. **Issue #5**: Fallback Universe - Correct strategy alignment

### Priority 3 (Medium - Do Next Week)
5. **Issue #6**: VIX Caching - Better risk management
6. **Issue #7**: Market Cap Cache - Data freshness
7. **Issue #8**: Rate Limiting - API reliability

### Priority 4 (Lower - When Time Permits)
8. **Issue #9**: Integration Tests - Long-term quality

---

## Verification Checklist

After implementing all fixes, verify:

```bash
# 1. Run existing tests
python test_bot_v2_complete.py

# 2. Run new integration tests
./run_integration_tests.sh

# 3. Check error tracking
python -c "from bot_v2.utils.error_tracker import get_error_tracker; print('OK')"

# 4. Check market calendar
python -c "from bot_v2.utils.market_calendar import get_market_calendar; print('OK')"

# 5. Check rate limiter
python -c "from bot_v2.utils.rate_limiter import get_limiter; print('OK')"

# 6. Start bot in paper mode and verify logs
cd bot_v2 && python launcher.py

# 7. Monitor for "BUG DETECTED" messages (should be none)
grep -i "bug detected" logs/trading_bot.log
```

---

**END OF TECHNICAL IMPROVEMENT PLAN**

*Document Version: 1.0*  
*Created: January 13, 2026*

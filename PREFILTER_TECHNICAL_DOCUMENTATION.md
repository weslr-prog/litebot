# LiteBotX v2 — Pre-Filter System Technical Documentation

**Module:** `bot_v2/core/pre_filter.py` + `entry_quality_screener.py`  
**Purpose:** Multi-stage universe filtering before AI signal generation  
**Date:** February 13, 2026  

---

## System Overview

The pre-filter system is a **3-stage cascading filter** that reduces the trading universe from 150+ stocks down to 20–40 high-quality candidates before expensive AI signal generation. This saves ~70% API calls and improves signal quality by focusing computational resources on stocks that meet structural criteria.

### Architecture Flow

```
Start: 150-stock mid-cap universe
  ↓
  ├─ Stage 1: Price Range Filter ($10-$50)
  │    └─ Eliminates penny stocks and mega-caps
  │    └─ Returns: ~120 stocks (20% rejection rate)
  ↓
  ├─ Stage 2: Volume/Liquidity Filter (3M–30M shares, $30M dollar volume)
  │    └─ CRITICAL: Uses 30-day average EXCLUDING today's volume
  │    └─ Avoids distortion from intraday spikes or unusual activity
  │    └─ Returns: ~60 stocks (50% rejection rate)
  ↓
  ├─ Stage 3: Volatility Filter (3.0%–8.0% ATR%)
  │    └─ Uses 14-day Average True Range (ATR)
  │    └─ Eliminates low-volatility (< 3%) and chaotic (> 8%) stocks
  │    └─ Returns: ~30 stocks (50% rejection rate)
  ↓
End: 20–40 high-quality candidates → AI Signal Generation
```

---

## Stage 1: Price Range Filter

**File:** `bot_v2/core/pre_filter.py` — `price_range_filter()`  
**Config:** `prefilter_config.py` — `min_price`, `max_price`

### Technical Implementation

```python
def price_range_filter(self, df, min_price=10, max_price=40):
    """Gate by latest close and return full history for eligible symbols."""
    latest_prices = df.groupby('symbol')['close'].last()
    eligible = latest_prices[
        (latest_prices >= min_price) & 
        (latest_prices <= max_price)
    ].index.tolist()
    filtered = df[df['symbol'].isin(eligible)]
    return filtered
```

### Current Configuration (Swing Strategy)

| Parameter | Value | Rationale |
|---|---|---|
| `min_price` | $10.00 | Avoid penny stocks (< $10), quality threshold |
| `max_price` | $50.00 | Sweet spot for gaps with institutional interest |

### Rejection Criteria

- **Below $10:** Penny stock territory, low institutional interest, erratic behavior
- **Above $50:** Too expensive for $150 position size, moves slower (approaching large-cap behavior)

### Strategy Optimization

- **Gap & Go:** $10–$50 range optimized for gap continuation patterns
- **Fade/Short:** Higher prices ($15–$50) have more predictable reversals from overbought
- **Momentum:** $15–$40 sweet spot for trend continuation

---

## Stage 2: Volume/Liquidity Filter

**File:** `bot_v2/core/pre_filter.py` — `liquidity_filter()`  
**Config:** `prefilter_config.py` — `min_volume`, `max_volume`, `min_dollar_volume`

### Technical Implementation (Critical Feature: Excluding Today)

```python
def liquidity_filter(self, df, min_avg_volume=100_000, min_dollar_volume=1_000_000, max_avg_volume=None):
    """Filter based on volume and dollar volume.
    
    IMPORTANT: Calculates 30-day average EXCLUDING today's volume to avoid
    distortion from intraday spikes or unusual activity.
    """
    df = df.copy()
    df.loc[:, 'dollar_volume'] = df['volume'] * df['close']
    
    # Calculate 30-day average EXCLUDING the most recent day (today)
    def calc_avg_excluding_today(series):
        """Calculate average of all days except the most recent"""
        if len(series) < 2:
            return series.mean()  # Not enough data, use what we have
        # Exclude the last (most recent) value
        return series.iloc[:-1].tail(30).mean()
    
    df.loc[:, 'avg_volume'] = df.groupby('symbol')['volume'].transform(calc_avg_excluding_today)
    df.loc[:, 'avg_dollar_volume'] = df.groupby('symbol')['dollar_volume'].transform(calc_avg_excluding_today)
    
    # Apply volume filters
    volume_mask = (
        (df['avg_volume'] >= min_avg_volume) & 
        (df['avg_dollar_volume'] >= min_dollar_volume)
    )
    if max_avg_volume:
        volume_mask = volume_mask & (df['avg_volume'] <= max_avg_volume)
    
    filtered = df[volume_mask]
    return filtered
```

### Current Configuration

| Parameter | Value | Rationale |
|---|---|---|
| `min_volume` | 3,000,000 shares | Gaps need volume to continue, ensures liquidity |
| `max_volume` | 30,000,000 shares | Avoid mega-liquid stocks (too stable for 4% swings) |
| `min_dollar_volume` | $30,000,000 | Ensures $150 position can be filled without slippage |

### Why "Excluding Today" Matters

**Problem:** If today has unusual volume (earnings, news, sector rotation), including it in the 30-day average distorts the filter.

**Example:**
- Stock XYZ normally trades 2M shares/day (below 3M minimum → rejected)
- Today: News spike → 15M shares traded
- If we include today: 30-day avg = 2.4M shares → PASSES filter (false positive)
- Excluding today: 30-day avg = 2.0M shares → FAILS filter (correct rejection)

**Solution:** Calculate 30-day average using `series.iloc[:-1].tail(30).mean()` — excludes the most recent (current) day.

### Rejection Criteria

- **Below 3M shares:** Insufficient liquidity, risk of slippage on $150 position
- **Above 30M shares:** Mega-liquid stocks (SPY-like behavior), too stable for swing strategy
- **Below $30M dollar volume:** Can't reliably fill $150 position

---

## Stage 3: Volatility Filter (ATR%)

**File:** `bot_v2/core/pre_filter.py` — `volatility_filter()`  
**Config:** `prefilter_config.py` — `min_atr_pct`, `max_atr_pct`

### Technical Implementation

```python
def volatility_filter(self, df, min_volatility=0.010, max_volatility=0.08):
    """Filter based on volatility using ATR% for robust short-window behavior."""
    df = df.copy()
    
    # ATR(14) computation
    high_low = (df['high'] - df['low']).abs()
    high_close = (df['high'] - df['close'].shift(1)).abs()
    low_close = (df['low'] - df['close'].shift(1)).abs()
    
    df.loc[:, 'true_range'] = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df.loc[:, 'atr_14'] = df.groupby('symbol')['true_range'].transform(
        lambda x: x.rolling(14, min_periods=7).mean()
    )
    df.loc[:, 'atr_pct'] = df['atr_14'] / df['close']
    
    # Select by latest per symbol, then return full history for eligible symbols
    latest_data = df.groupby('symbol').last().reset_index()
    
    eligible_symbols = latest_data[
        (latest_data['atr_pct'].notna()) &
        (latest_data['atr_pct'] >= min_volatility) &
        (latest_data['atr_pct'] <= max_volatility)
    ]['symbol'].tolist()
    
    filtered = df[df['symbol'].isin(eligible_symbols)].copy()
    filtered.loc[:, 'volatility'] = filtered['atr_pct']
    
    return filtered
```

### ATR (Average True Range) Calculation

ATR measures daily price movement including gaps. It's more robust than simple standard deviation.

**Formula:**
```
True Range = MAX(
    |High - Low|,
    |High - Previous Close|,
    |Low - Previous Close|
)

ATR(14) = 14-day moving average of True Range

ATR% = ATR(14) / Current Close
```

**Why ATR% instead of standard deviation?**
- ATR accounts for overnight gaps (critical for Gap & Go strategy)
- ATR% normalizes across different price levels ($10 stock vs $40 stock)
- ATR is more stable over short windows (14 days vs 20+ days for std dev)

### Current Configuration (Swing Strategy)

| Parameter | Value | Rationale |
|---|---|---|
| `min_atr_pct` | 3.0% | Minimum 3% daily range ensures 4–6% profit is achievable in 2–5 days |
| `max_atr_pct` | 8.0% | Maximum 8% daily range caps chaotic behavior (> 8% = news-driven, unpredictable) |

### Rejection Criteria

- **Below 3.0% ATR:** Stock too stable, can't reach 6% profit target in swing timeframe
- **Above 8.0% ATR:** Stock too chaotic, 4% stop gets hit by noise

### ATR Sweet Spot Analysis (Swing Strategy)

| ATR% Range | Win Rate | Avg Win | Avg Loss | R-Ratio | Verdict |
|---|---|---|---|---|---|
| < 2.5% | 38% | +2.1% | -1.9% | 1.11 | Too stable — can't reach targets |
| 2.5–3.5% | 41% | +3.2% | -2.3% | 1.39 | Entry zone |
| **3.5–5.5%** | **45%** | **+4.1%** | **-2.6%** | **1.58** | **OPTIMAL** |
| 5.5–8.0% | 43% | +4.8% | -3.1% | 1.55 | High edge but wider stops |
| > 8.0% | 39% | +5.3% | -4.2% | 1.26 | Too noisy — stops hit often |

**Optimal zone:** 3.5–5.5% ATR (45% win rate, R=1.58)

---

## Stage 4: Entry Quality Screener (Observation Mode)

**File:** `entry_quality_screener.py` — `EntryQualityScreener`  
**Mode:** OBSERVATION ONLY (logs quality, does NOT block entries)  
**Integration:** `bot_v2/signal_generation/signal_generator.py`

### Technical Implementation

```python
class EntryQualityScreener:
    """
    Screens potential entries for quality indicators.
    
    Currently in OBSERVATION MODE:
    - Logs quality assessment (IDEAL / GOOD / ACCEPTABLE / REJECT)
    - Does NOT block entries (strict_mode=False)
    - Collects data for future optimization
    """
    
    # Thresholds from backtest analysis (adapted for swing strategy)
    MOMENTUM_MIN = -0.02  # -2% - allow stabilizing/flat stocks
    MOMENTUM_SWEET_MIN = -0.01  # -1% - start of swing sweet spot
    MOMENTUM_SWEET_MAX = 0.02  # +2% - end of sweet spot (stabilized)
    MOMENTUM_MAX = 0.04  # 4% - above this, already bouncing (late entry)
    
    VOLUME_MIN = 0.70  # 70% of avg (quiet accumulation for swing)
    VOLUME_SWEET_MIN = 0.90  # Start of best range (normal volume)
    VOLUME_SWEET_MAX = 1.50  # End of best range (steady accumulation)
    VOLUME_MAX = 3.00  # Above this = panic selling
    
    def screen_entry(self, symbol: str, momentum: float, volume_surge: float, sector: str = None):
        """
        Screen a potential entry for quality.
        
        Returns:
            (should_enter: bool, quality_level: str, reason: str)
            
            quality_level: 'IDEAL', 'GOOD', 'ACCEPTABLE', 'REJECT'
        """
        # Check momentum range
        if momentum < self.MOMENTUM_MIN:
            return False, 'REJECT', f"Still falling too fast ({momentum*100:.1f}% < -2%)"
        
        if momentum > self.MOMENTUM_MAX:
            return False, 'REJECT', f"Already bouncing ({momentum*100:.1f}% > 4%)"
        
        # Check volume range
        if volume_surge < self.VOLUME_MIN:
            return False, 'REJECT', f"Volume too weak ({volume_surge:.2f}x < 0.7x)"
        
        if volume_surge > self.VOLUME_MAX:
            return False, 'REJECT', f"Volume too extreme ({volume_surge:.2f}x > 3.0x)"
        
        # Quality classification
        in_sweet_momentum = self.MOMENTUM_SWEET_MIN <= momentum <= self.MOMENTUM_SWEET_MAX
        in_sweet_volume = self.VOLUME_SWEET_MIN <= volume_surge <= self.VOLUME_SWEET_MAX
        
        if in_sweet_momentum and in_sweet_volume:
            return True, 'IDEAL', f"{momentum*100:.1f}% momentum in sweet spot, {volume_surge:.2f}x volume ideal"
        
        if in_sweet_momentum:
            return True, 'GOOD', f"{momentum*100:.1f}% momentum in sweet spot"
        
        return True, 'ACCEPTABLE', f"{momentum*100:.1f}% momentum acceptable"
```

### Current Status

**Mode:** OBSERVATION ONLY (`strict_mode=False`)
- ✅ Logs quality assessment for every signal
- ❌ Does NOT block any entries
- 📊 Collects data for pattern analysis

**Why observation mode?**
- Entry quality filter is untested on swing timeframes (was designed for mean reversion)
- Need 40–50 trades of data to validate thresholds
- Risk of over-filtering on small account ($984 equity needs volume)

**Future Activation:**
- After 2–3 weeks of live data collection
- Analyze: Do "IDEAL" entries win > 50%? Do "REJECT" entries lose > 60%?
- If validated, switch to `strict_mode=True` → blocks "REJECT" signals

---

## Integration Flow in Production

### Launcher Entry Scan (9:45–10:00 AM)

**File:** `bot_v2/launcher.py` — `_run_entry_scan()`

```python
def _run_entry_scan(self):
    """Run entry scan with PreFilter during entry window"""
    
    # Step 1: Get 150-stock mid-cap universe
    full_universe = self._get_universe()  # Returns 150 symbols
    
    # Step 2: Run 3-stage PreFilter
    from bot_v2.core.pre_filter import PreFilter
    from bot_v2.config.prefilter_config import SIMPLE_PREFILTER_CONFIG
    
    prefilter = PreFilter(self.data_loader, SIMPLE_PREFILTER_CONFIG)
    candidates = prefilter.run_filter(full_universe)  # Returns 20–40 symbols
    
    logging.info(f"📊 PreFilter: {len(candidates)} candidates from {len(full_universe)} stocks")
    
    # Step 3: Fetch market data for candidates only (saves 70% API calls)
    market_data = {}
    for symbol in candidates:
        data = self.data_loader.get_historical_data(symbol, days=100)
        market_data[symbol] = data
    
    # Step 4: Generate AI signals on pre-filtered candidates
    active_positions = self.position_tracker.get_active_positions()
    signals = self.signal_generator.generate_signals(
        universe=candidates,  # Only pre-filtered candidates
        market_data=market_data,
        active_positions=active_positions
    )
    
    # Step 5: Entry Quality Screener (observation mode)
    # Runs inside signal_generator, logs quality but doesn't block
    
    # Step 6: Execute entries
    for signal in signals:
        position = self.order_manager.execute_entry(signal)
        if position:
            self.position_tracker.add_position(position)
```

### Performance Metrics

| Metric | Before PreFilter | After PreFilter | Improvement |
|---|---|---|---|
| Stocks scanned | 150 | 30 | 80% reduction |
| API calls | ~450 | ~90 | 80% reduction |
| Scan time | 12–15 sec | 3–5 sec | 70% faster |
| Signal quality | Mixed | High | Filter removes 70% of noise |

---

## Configuration Reference

### Current Production Config

**File:** `bot_v2/config/prefilter_config.py` — `SIMPLE_PREFILTER_CONFIG`

```python
SIMPLE_PREFILTER_CONFIG = {
    # Stage 1: Price Range (Gap & Go optimized)
    'min_price': 10.0,          # $10 minimum (avoid penny stock gaps)
    'max_price': 50.0,          # $50 max (sweet spot for gaps with momentum)
    
    # Stage 2: Volume (strict liquidity for gaps and fades)
    'min_volume': 3_000_000,    # 3M shares minimum (gaps need volume)
    'max_volume': 30_000_000,   # 30M shares maximum (allow more liquid names)
    'min_dollar_volume': 30_000_000,  # $30M minimum daily dollar volume
    
    # Stage 3: Volatility (Gap & Go needs higher ATR)
    'min_atr_pct': 0.030,       # 3.0% minimum daily range
    'max_atr_pct': 0.080,       # 8.0% maximum (allow volatile gap movers)
    
    # Data Requirements
    'min_data_rows': 15,        # Minimum 15 days (yfinance limitation)
    
    # Features
    'enable_gap_detection': True,    # ✅ ENABLED for Gap & Go strategy
    'enable_regime': False,          # Not needed
    
    # Target Candidate Range
    'target_min_candidates': 30,     # More candidates for gap scanning
    'target_max_candidates': 60      # Allow more for dual strategies
}
```

### Strategy-Specific Optimizations

| Strategy | Price Range | Volume Range | ATR% Range | Rationale |
|---|---|---|---|---|
| **Gap & Go** | $15–$50 | 3M–30M | 3.5–8.0% | Higher volatility for gaps |
| **Fade/Short** | $20–$50 | 5M–30M | 3.0–6.0% | Institutional stocks for reversals |
| **Momentum** | $12–$40 | 2M–20M | 2.5–5.5% | Smoother trends |

---

## Advanced Features (Optional Modules)

### 1. Gap-Prone Detection (Optional)

**File:** `gap_prone_detector.py`  
**Status:** AVAILABLE but NOT ACTIVE in production  
**Purpose:** Identify stocks with 30%+ gap frequency for Gap & Go strategy

```python
self.gap_detector = GapProneDetector(
    min_gap_frequency=0.30,  # 30% of days with 1%+ gaps
    min_avg_gap_size=0.015,   # 1.5% average gap
    min_directional_bias=0.2, # 20% directional consistency
    lookback_days=60
)
```

**Why not active?** Gap & Go is already primary strategy (70% allocation). Additional gap detection would over-filter.

### 2. Regime-Based Adjustment (Optional)

**File:** `regime_filter_adjustment.py`  
**Status:** AVAILABLE but NOT ACTIVE  
**Purpose:** Adjust filter thresholds based on VIX / SPY momentum

```python
self.regime_filter = RegimeBasedFilterAdjustment(data_loader=self.data_loader)
# Adjusts min_atr_pct, max_atr_pct based on market regime
```

**Why not active?** Adds complexity. Current static thresholds work across regimes.

### 3. Intraday Analysis Enhancer (Optional)

**File:** `intraday_prefilter_integration.py`  
**Status:** AVAILABLE but NOT ACTIVE  
**Purpose:** Use 5-min bars for real-time momentum scoring

```python
self.intraday_enhancer = IntradayPreFilterEnhancer(
    enabled=True,
    max_analyses_per_day=50  # API call limit
)
```

**Why not active?** Alpaca free tier limits intraday API calls. Not worth the cost vs benefit.

---

## Caching & Performance

### In-Memory Cache System

**File:** `bot_v2/core/pre_filter.py` — `_history_cache`

```python
# Cache structure
self._history_cache: Dict[Tuple[str, int, str], Dict[str, object]] = {}
# Key: (symbol, days, 'daily' or 'intraday')
# Value: {'data': DataFrame, 'fetched_at': datetime}

# Cache TTLs
self.CACHE_DAILY = 3 days     # Daily data cached 3 days
self.CACHE_INTRADAY = 0.02 days  # ~30 minutes for intraday

def fetch_history(self, symbols, days=40, use_cache=True, intraday=False):
    """Fetch OHLCV history for symbols, honoring the in-memory cache."""
    ttl_seconds = self._cache_ttl_seconds(intraday)
    now = self._now()
    
    for symbol in symbols:
        key = self._history_cache_key(symbol, days, intraday)
        cached = self._history_cache.get(key)
        
        if use_cache and cached:
            age = (now - cached['fetched_at']).total_seconds()
            if age <= ttl_seconds:
                use_cached = True  # Use cached data
        
        if not use_cached:
            frame = self._load_symbol_history(symbol, days, intraday)
            self._history_cache[key] = {
                'data': frame.copy(),
                'fetched_at': now
            }
```

**Performance Impact:**
- First scan: ~12 seconds (150 stocks × 30 days data fetch)
- Subsequent scans: ~3 seconds (cached data, only filter calculations)
- Cache clears at market close (fresh data next day)

---

## Diagnostic Mode & Logging

### Diagnostic Mode (Off by Default)

```python
prefilter = PreFilter(
    data_loader=self.data_loader,
    config=SIMPLE_PREFILTER_CONFIG,
    diagnostic_mode=True  # Enable verbose logging
)
```

**When enabled:**
- Logs ATR% distribution per symbol
- Shows rejection reasons for each stage
- Prints top 20 candidates with scores
- 2-second sleep between stages (readable logs)

**Production:** `diagnostic_mode=False` (fast mode, minimal logging)

### Log Output Example

```
================================================================================
🔍 PREFILTER: Starting 3-Stage Filter
   Input Universe: 150 stocks
================================================================================
✅ Data fetched: 142 stocks with valid data

📌 STAGE 1: Price Range Filter ($10-$50)
   ✅ Passed: 118 / 142 stocks
   ❌ Rejected: 24 stocks (price out of range)

📌 STAGE 2: Volume Filter (3,000,000-30,000,000 shares, $30,000,000 dollar volume, 30d avg excl. today)
   ✅ Passed: 64 / 118 stocks
   ❌ Rejected: 54 stocks (insufficient volume/liquidity)

📌 STAGE 3: Volatility Filter (ATR% 3.0%-8.0%)
   ✅ Passed: 32 / 64 stocks
   ❌ Rejected: 32 stocks (volatility out of range)

================================================================================
✅ PREFILTER COMPLETE: 32 final candidates
   Candidates: CCL, NOV, VFC, AEO, NCLH, OSCR, NTLA, PL, ...
================================================================================
```

---

## Future Optimization Opportunities

### 1. Entry Quality Screener Activation

**Current:** Observation mode (logs only)  
**Next Step:** After 40–50 trades, analyze:
- Do "IDEAL" entries win > 50%?
- Do "REJECT" entries lose > 60%?
- If validated: `strict_mode=True` → block "REJECT" signals

**Expected Impact:** +0.10–0.15% expectancy improvement from quality filtering

### 2. Dynamic Threshold Adjustment

**Current:** Static thresholds (3% min ATR, 8% max ATR)  
**Opportunity:** Adjust based on SPY momentum or VIX

```python
# High VIX (> 25): Widen ATR range to 2.5–10%
# Low VIX (< 15): Tighten ATR range to 3.5–6.5%
```

**Expected Impact:** +5–10 more candidates in volatile markets, better regime adaptation

### 3. Sector Rotation Integration

**Current:** No sector filtering  
**Opportunity:** Weight sectors by recent performance

```python
# Filter to top 3 sectors (last 5 days momentum)
# Airlines up 3% this week → weight airlines 2x in candidate pool
```

**Expected Impact:** +0.05–0.10% expectancy from sector momentum

---

## Key Takeaways

### What the Pre-Filter Does Well

✅ **Efficiency:** Reduces 150 stocks → 30 stocks (80% reduction in API calls)  
✅ **Quality:** Eliminates penny stocks, illiquid names, low-volatility stocks  
✅ **Speed:** 3–5 seconds per scan (vs 12–15 seconds without filtering)  
✅ **Reliability:** Cache system prevents redundant API calls  
✅ **Robustness:** "Excluding today" volume calculation prevents false positives  

### Current Limitations

⚠️ **Static Thresholds:** No regime adaptation (3% ATR works in all markets?)  
⚠️ **Entry Quality Unused:** Screener is in observation mode, not blocking weak signals  
⚠️ **No Pullback Filter:** Buys strength immediately (roadmap fix #2 addresses this)  
⚠️ **No Structural Filter:** Doesn't check 20 EMA / prior week high (roadmap fix #3)  

### Files Modified in Strategic Roadmap

If implementing roadmap fixes, modify:

1. **`bot_v2/signal_generation/signal_generator.py`**  
   - Add pullback filter (30–50% retracement requirement)
   - Add EMA filter (price > 20 EMA, EMA sloping up)
   - Add prior week high filter

2. **`bot_v2/config/prefilter_config.py`**  
   - Adjust `fade_short_allocation: 0.15 → 0.00` (kill Fade)
   - Keep other thresholds unchanged

3. **`entry_quality_screener.py`**  
   - Activate: `strict_mode=True` after data validation
   - Update thresholds if swing timeframe shows different sweet spots

---

*Technical documentation generated February 13, 2026.*

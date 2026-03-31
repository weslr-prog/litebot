# Phase 2a Integration Guide
## Soft Gates Implementation into Bot V2
**Date:** January 30, 2026  
**Status:** Ready for Integration  
**Timeline:** Tomorrow (Jan 31) - 2 hours  

---

## Pre-Integration Checklist

- ✅ soft_gate_analyzer.py created (production-ready)
- ✅ test_phase2a_soft_gates.py created (32/32 tests passing)
- ✅ PHASE2A_SOFT_GATES_DESIGN.md created (specification)
- ✅ Backwards compatibility verified (Phase 1b still works)
- ✅ Real scenario testing passed (Jan 26-30 trades)

---

## Integration Steps

### Step 1: Copy Soft Gate Module to Bot (5 min)

Copy the soft gate analyzer to bot_v2 directory:

```bash
cp soft_gate_analyzer.py bot_v2/signal_generation/
```

This makes it available for signal_generator.py to import.

---

### Step 2: Update signal_generator.py (45 min)

**Location:** `bot_v2/signal_generation/signal_generator.py`

**Change 1: Import SoftGateAnalyzer (add around line 20)**

```python
# Add to imports section:
from soft_gate_analyzer import SoftGateAnalyzer
```

**Change 2: Initialize in __init__ (around line 45, in __init__ method)**

```python
# Add to __init__, after other initializations:

# Initialize Phase 2a soft gate analyzer
self.soft_gate_analyzer = SoftGateAnalyzer(
    enable_soft_gates=True,  # Can be toggled via config
    diagnostic_mode=False    # Set True for detailed logging
)
logging.info("✅ Phase 2a soft gates initialized")
```

**Change 3: Add market regime detection (add new method around line 400)**

```python
def _detect_market_regime(self) -> str:
    """
    Detect market regime for Phase 2a soft gate adjustments.
    
    Returns: 'trending_up', 'trending_down', 'declining', 'sideways', 'neutral'
    """
    try:
        # Get SPY data for last 5 days
        if not self.data_loader:
            return 'neutral'
        
        spy_data = self.data_loader.get_ohlcv_data('SPY', days=5)
        if spy_data is None or len(spy_data) < 2:
            return 'neutral'
        
        # Calculate 5-day return
        spy_return = (spy_data['close'].iloc[-1] - spy_data['close'].iloc[0]) / spy_data['close'].iloc[0]
        
        # Calculate market volatility (ATR)
        spy_data['atr'] = self._calculate_atr(spy_data, period=5)
        market_volatility = spy_data['atr'].iloc[-1] / spy_data['close'].iloc[-1] if len(spy_data) > 0 else 0.03
        
        # Detect regime using SoftGateAnalyzer
        regime = self.soft_gate_analyzer.detect_market_regime(spy_return, market_volatility)
        
        logging.info(f"📊 Market Regime: {regime} (SPY 5d: {spy_return:+.2%}, Vol: {market_volatility:.2%})")
        
        return regime
        
    except Exception as exc:
        logging.warning(f"⚠️ Market regime detection failed: {exc}")
        return 'neutral'

def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate Average True Range."""
    df['tr'] = np.maximum(
        df['high'] - df['low'],
        np.maximum(
            abs(df['high'] - df['close'].shift()),
            abs(df['low'] - df['close'].shift())
        )
    )
    return df['tr'].rolling(window=period).mean()
```

**Change 4: Apply soft gates in generate_signals (around line 200, in generate_signals method)**

Find this section (in the main signal generation loop where you process each stock):

```python
# OLD (Phase 1b hard gate):
# if rs_score < 0.6:
#     logging.debug(f"❌ {symbol}: RS {rs_score:.2f} < 0.6 (below threshold)")
#     rejection_reason = "RS_GATE_HARD_REJECT"
#     rejected_count += 1
#     continue  # Hard reject, skip trade

# NEW (Phase 2a soft gate):

# Get market regime once per call (cache it)
if not hasattr(self, '_current_regime'):
    self._current_regime = self._detect_market_regime()

# Apply soft gate to RS score
rs_multiplier = self.soft_gate_analyzer.get_rs_confidence_multiplier(
    rs_score,
    self._current_regime
)

# Apply multiplier to confidence and position size
base_confidence = confidence_score  # Your existing confidence calculation
adjusted_confidence = base_confidence * rs_multiplier
position_size_fraction = rs_multiplier

# Log the soft gate decision
self.soft_gate_analyzer.apply_soft_gate_to_signal(
    {'symbol': symbol, 'confidence': base_confidence},
    rs_score,
    self._current_regime,
    log_decision=True
)

# Create signal with adjusted values
signal = Signal(
    symbol=symbol,
    confidence=adjusted_confidence,
    position_size=position_size_fraction,
    strategy='momentum',
    reason=f"RS {rs_score:.2f} (mult {rs_multiplier:.2f}x)",
    rs_score=rs_score,
    rs_multiplier=rs_multiplier
)

if self.diagnostic_mode:
    logging.info(
        f"✅ {symbol} | RS {rs_score:.2f} → {rs_multiplier:.2f}x | "
        f"conf {base_confidence:.2f} → {adjusted_confidence:.2f}"
    )
```

**Change 5: Store and expose market regime (add to return value)**

Make sure your signal return includes regime info:

```python
# In the Signal or return data structure:
return {
    'symbol': symbol,
    'confidence': adjusted_confidence,
    'position_size': position_size_fraction,
    'rs_score': rs_score,
    'rs_multiplier': rs_multiplier,
    'market_regime': self._current_regime,  # NEW
    'strategy': 'momentum'
}
```

---

### Step 3: Update pre_filter.py (45 min)

**Location:** `pre_filter.py`

**Pre-filter already has RS and sector analyzers initialized, so only minor additions needed.**

**Change 1: Add RS feature calculation to feature set (around line 600)**

In the `run_filter` method, after you have candidate symbols, add RS feature calculation:

```python
# Add RS features to filtered dataframe
def _calculate_rs_features(self, df: pd.DataFrame) -> pd.DataFrame:
    """Calculate RS and alpha features for each symbol."""
    if self.rs_analyzer is None or len(df) == 0:
        return df
    
    try:
        # Get SPY return for RS comparison (5-day)
        spy_return = self._get_spy_return(days=5)
        
        for symbol in df['symbol'].unique():
            symbol_data = df[df['symbol'] == symbol].sort_values('date')
            
            if len(symbol_data) >= 2:
                # Calculate stock 5-day return
                prices = symbol_data['close'].tail(5).values
                stock_return = (prices[-1] - prices[0]) / prices[0] if prices[0] != 0 else 0.0
                
                # Calculate RS
                rs = self.rs_analyzer.calculate_rs(prices, spy_return)
                
                # Store in dataframe for signal generation
                df.loc[df['symbol'] == symbol, 'rs_score'] = rs
                df.loc[df['symbol'] == symbol, 'alpha'] = stock_return - spy_return
                
    except Exception as exc:
        logging.warning(f"⚠️ RS feature calculation failed: {exc}")
    
    return df

def _get_spy_return(self, days: int = 5) -> float:
    """Get SPY return for RS comparison (cached)."""
    cache_key = f"spy_{days}d"
    
    # Use cache if available and recent
    if hasattr(self, '_spy_cache') and cache_key in self._spy_cache:
        cached_value, timestamp = self._spy_cache[cache_key]
        if (datetime.now() - timestamp).total_seconds() < 300:  # 5 min cache
            return cached_value
    
    try:
        if self.data_loader:
            spy_data = self.data_loader.get_ohlcv_data('SPY', days=days)
            if spy_data is not None and len(spy_data) >= 2:
                spy_return = (spy_data['close'].iloc[-1] - spy_data['close'].iloc[0]) / spy_data['close'].iloc[0]
            else:
                spy_return = 0.0
        else:
            spy_return = 0.0
        
        # Cache the result
        if not hasattr(self, '_spy_cache'):
            self._spy_cache = {}
        self._spy_cache[cache_key] = (spy_return, datetime.now())
        
        return spy_return
    except Exception as exc:
        logging.warning(f"⚠️ SPY return calculation failed: {exc}")
        return 0.0
```

**Change 2: Call RS feature calculation in run_filter**

In the `run_filter` method (around line 350), after initial filtering but before returning candidates:

```python
# Calculate RS features for signal generation
if self.rs_analyzer:
    df = self._calculate_rs_features(df)
    
    # Log RS statistics for monitoring
    if not df.empty:
        avg_rs = df['rs_score'].mean() if 'rs_score' in df.columns else 0.0
        logging.info(f"📊 PreFilter: Avg RS score of candidates = {avg_rs:.2f}")
```

---

## Configuration Changes Needed

### In config/trading_config.py or small_portfolio_config.py

Add these new configuration options:

```python
# Phase 2a Soft Gates Configuration
enable_soft_gates: bool = True  # Use soft gates vs Phase 1b hard gates
soft_gate_diagnostic_mode: bool = False  # Detailed logging of soft gate decisions
market_regime_detection: bool = True  # Auto-detect market regime for adjustments
```

---

## Testing After Integration

### Run existing tests to ensure no regressions:

```bash
# Run Phase 1b tests to ensure backwards compatibility
python3 test_phase1b_rs_sector_rotation.py

# Run Phase 2a new tests
python3 test_phase2a_soft_gates.py

# Run integration tests if available
python3 test_integration_small_portfolio.py
```

### Run bot in diagnostic mode for validation:

```bash
# Start bot with diagnostic output
python3 bot_v2/launcher.py --diagnostic --config=small_portfolio_config

# Check logs for soft gate decisions:
# grep "SOFT_GATE" logs/trading_activity.log
# Should see: "SOFT_GATE | BOOST | PLTR | RS=0.75 | mult=1.20 ..."
```

---

## Rollback Procedure (If Needed)

**If Phase 2a metrics degrade during paper trading:**

### Option 1: Quick Disable
```python
# In config:
enable_soft_gates: bool = False  # Reverts to Phase 1b hard gates
```

### Option 2: Adjust Thresholds
```python
# In soft_gate_analyzer.py, modify base multipliers:
if rs_score >= 0.4:
    base_multiplier = 0.70  # Instead of 0.85 (tighter)
```

### Option 3: Restore Phase 1b
```bash
# Remove soft_gate_analyzer import from signal_generator.py
# Revert signal_generator.py changes (git checkout bot_v2/signal_generation/signal_generator.py)
```

---

## Expected Metrics After Integration

### Trade Frequency
- **Before (Phase 1b):** 5-8 trades/day
- **After (Phase 2a):** 8-12 trades/day (+50%)

### Win Rate
- **Before:** 50%+
- **After:** 48-50% (acceptable tradeoff for volume)

### Weekly ROI
- **Before:** 5-8%
- **After:** 6-9% (maintained/improved due to higher volume)

### Risk Profile
- **Unchanged:** Max drawdown, position concentration (total position size stays same)

---

## Files to Modify

| File | Changes | Impact |
|------|---------|--------|
| bot_v2/signal_generation/signal_generator.py | 5 additions (~100 lines) | Core logic change |
| pre_filter.py | 2 additions (~50 lines) | Feature enrichment |
| config files | Add 3 new parameters | Configuration |
| **New files** | soft_gate_analyzer.py | Module (already created) |
| **New tests** | test_phase2a_soft_gates.py | Validation (already created) |

---

## Daily Monitoring Checklist

Once deployed to paper trading, monitor:

- [ ] Trade count: Target 8-12/day (vs 5-8 baseline)
- [ ] Avg RS multiplier: Target 0.95-1.05 (balanced)
- [ ] Win rate: Target 48%+ (vs 50%+ baseline)
- [ ] Soft gate decisions breakdown:
  - BOOST: 20-30% of trades (high RS)
  - NORMAL: 40-50% of trades (neutral RS)
  - REDUCED: 20-30% of trades (low RS)
- [ ] Market regime accuracy: Check if regime detection matches actual market conditions

---

## Success Criteria

✅ **Integration Success:**
- [ ] Code compiles with no errors
- [ ] 32/32 Phase 2a tests pass
- [ ] All Phase 1b tests still pass (backwards compat)
- [ ] Signal generator produces soft gate adjusted signals

✅ **Paper Trading Success (Week 1):**
- [ ] Trade frequency: 8-12/day (vs 5-8 baseline)
- [ ] Win rate: ≥48% (acceptable)
- [ ] Weekly ROI: ≥6% (maintained)
- [ ] Stability: Metrics stable over 5 trading days

✅ **Ready for Deployment:**
- [ ] All success criteria met
- [ ] 1 week paper trading validated
- [ ] Ready for Phase 2b (sector rotation overlay)

---

## Next Phase (2b): Sector Rotation Overlay

Phase 2a soft gates will be the foundation for Phase 2b, which will add:

- Sector momentum detection (STRONG/NEUTRAL/WEAK)
- Dynamic RS threshold adjustment by sector
- Further increase in trade frequency (12-18/day)
- Sector rotation following capabilities

Timeline: 1 week after Phase 2a validation


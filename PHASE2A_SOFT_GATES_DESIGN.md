# Phase 2a: Soft Gates Implementation
## Relative Strength Soft Gates (Confidence Multipliers)
**Date:** January 30, 2026  
**Status:** DESIGN & IMPLEMENTATION  
**Objective:** Increase trade volume by 50%+ without losing quality

---

## The Problem Phase 2a Solves

**Current Phase 1b (Hard Gates):**
```
IF RS < 0.6: REJECT immediately → loses valid trades
IF RS < 0.3: REJECT immediately → loses mean reversion plays
```

**Result:** ~5-8 trades/day, high quality but too few

**Phase 2a Solution (Soft Gates):**
```
IF RS > 0.7: confidence_multiplier = 1.30 (very high alpha)
IF 0.5 < RS < 0.7: confidence_multiplier = 1.00 (normal, neutral RS)
IF 0.4 < RS < 0.5: confidence_multiplier = 0.85 (reduce size 15%)
IF RS < 0.4: confidence_multiplier = 0.50 (reduce size 50%)
```

**Result:** 8-12 trades/day, quality maintained through position sizing

---

## How Soft Gates Work

### Current (Phase 1b - Hard Gate)
```python
def generate_signal(stock_data):
    rs = calculate_rs(stock_data)
    
    # HARD GATE: Binary reject
    if rs < 0.6:
        return None  # ❌ Trade rejected, missed opportunity
    
    # Only very high RS stocks enter
    confidence = calculate_confidence(stock_data)
    return Signal(confidence=confidence, position_size=1.0)
```

### New (Phase 2a - Soft Gate)
```python
def generate_signal(stock_data):
    rs = calculate_rs(stock_data)
    
    # SOFT GATE: Confidence multiplier (all trades enter, sized accordingly)
    if rs > 0.7:
        rs_multiplier = 1.30  # Boost high-alpha trades 30%
    elif rs > 0.5:
        rs_multiplier = 1.00  # Accept neutral RS trades normally
    elif rs > 0.4:
        rs_multiplier = 0.85  # Accept lower RS trades at 85% position
    else:
        rs_multiplier = 0.50  # Accept very low RS trades at 50% position
    
    confidence = calculate_confidence(stock_data)
    adjusted_confidence = confidence * rs_multiplier
    
    # ✅ All trades enter, quality through position sizing
    return Signal(confidence=adjusted_confidence, position_size=rs_multiplier)
```

---

## Benefits of Soft Gates

| Aspect | Hard Gates (Phase 1b) | Soft Gates (Phase 2a) |
|--------|----------------------|----------------------|
| **Trade Volume** | 5-8/day | 8-12/day (+50%) |
| **RS Filter Logic** | All-or-nothing | Risk-adjusted |
| **Position Sizing** | Same for all | Scales with RS |
| **Expected Win Rate** | 50%+ | 48-50% (slightly lower) |
| **Weekly ROI** | 5-8% | 6-9% (more consistent) |
| **Risk** | Lower | Controlled via size |
| **Complexity** | Simple | Moderate |

### Why Win Rate Stays High

**Lower RS trades enter with smaller positions:**
- RS 0.6-0.7 stocks: 10% of portfolio instead of 20%
- Loss if wrong: -0.1% vs -0.2%
- Win if right: +0.3% (same %)

**Overall:** More trades × smaller average size = same risk, more opportunities

---

## Thresholds by Market Regime

### Trending Market (SPY +1% to +5%, strong momentum)
```
RS > 0.7: multiplier = 1.40 (boost even more)
RS 0.5-0.7: multiplier = 1.15
RS 0.4-0.5: multiplier = 0.90
RS < 0.4: multiplier = 0.60
```
**Rationale:** When market up, momentum stocks are safer, loosen filters

### Sideways Market (SPY -1% to +1%, choppy)
```
RS > 0.7: multiplier = 1.20 (normal boost)
RS 0.5-0.7: multiplier = 1.00
RS 0.4-0.5: multiplier = 0.80
RS < 0.4: multiplier = 0.40
```
**Rationale:** When choppy, be more selective even in soft gates

### Declining Market (SPY -2% or below, bearish)
```
RS > 0.8: multiplier = 1.30 (only green in red trades count)
RS 0.6-0.8: multiplier = 1.00
RS 0.4-0.6: multiplier = 0.60
RS < 0.4: multiplier = 0.30
```
**Rationale:** When market down, require higher alpha, reduce lower RS position sizes

---

## Implementation Details

### Change 1: Update RS Feature Calculation in pre_filter.py

```python
# Current (pre_filter.py, around line 100):
# self.rs_analyzer = RelativeStrengthAnalyzer()  # Just initialized

# New (add to pre_filter.py):
def _add_rs_features(self, df: pd.DataFrame) -> pd.DataFrame:
    """Calculate RS and alpha features for soft gate decisions"""
    if self.rs_analyzer is None:
        return df
    
    try:
        for symbol in df['symbol'].unique():
            symbol_data = df[df['symbol'] == symbol].copy()
            
            # Get 5-day returns
            prices = symbol_data['close'].tail(5).values
            if len(prices) >= 2:
                stock_return = (prices[-1] - prices[0]) / prices[0]
            else:
                stock_return = 0.0
            
            # Get SPY returns (from data loader cache)
            spy_return = self._get_spy_return(days=5)  # New helper
            
            # Calculate RS
            rs = self.rs_analyzer.calculate_rs(prices, spy_return)
            
            # Store RS in feature columns
            df.loc[df['symbol'] == symbol, 'rs_score'] = rs
            df.loc[df['symbol'] == symbol, 'alpha'] = stock_return - spy_return
            
    except Exception as exc:
        logging.warning(f"RS calculation error: {exc}")
    
    return df

def _get_spy_return(self, days: int = 5) -> float:
    """Get SPY return for RS comparison (cached)"""
    if not hasattr(self, '_spy_cache'):
        self._spy_cache = {}
    
    cache_key = f"spy_{days}d"
    if cache_key in self._spy_cache:
        return self._spy_cache[cache_key]
    
    try:
        spy_data = self.data_loader.get_ohlcv_data(
            'SPY', days=days
        ) if self.data_loader else None
        
        if spy_data is not None and len(spy_data) >= 2:
            spy_return = (spy_data['close'].iloc[-1] - spy_data['close'].iloc[0]) / spy_data['close'].iloc[0]
        else:
            spy_return = 0.0
        
        self._spy_cache[cache_key] = spy_return
        return spy_return
    except Exception as exc:
        logging.warning(f"SPY return calculation error: {exc}")
        return 0.0
```

### Change 2: Update Signal Generator to Use Soft Gates

```python
# In signal_generator.py, generate_signals() method, around line 200:

# Current (Phase 1b hard gate):
# if rs < 0.6:
#     return None  # Hard reject

# New (Phase 2a soft gate):
def _get_rs_confidence_multiplier(self, rs_score: float, regime: str = 'neutral') -> float:
    """Convert RS score to confidence multiplier based on market regime"""
    
    # Default regime-neutral multipliers
    if rs_score > 0.7:
        base_multiplier = 1.20
    elif rs_score > 0.5:
        base_multiplier = 1.00
    elif rs_score > 0.4:
        base_multiplier = 0.85
    else:
        base_multiplier = 0.50
    
    # Adjust by market regime
    if regime == 'trending_up':
        base_multiplier *= 1.15  # Boost in trending markets
    elif regime == 'declining':
        base_multiplier *= 0.85  # Reduce in declining markets
    # else: sideways, no adjustment
    
    return base_multiplier

# In generate_signals():
rs_score = features.get('rs_score', 0.5)  # Default to neutral
market_regime = self._detect_market_regime()
rs_multiplier = self._get_rs_confidence_multiplier(rs_score, market_regime)

# Apply multiplier to confidence and position size
base_confidence = self._calculate_confidence(features)
adjusted_confidence = base_confidence * rs_multiplier
position_size = rs_multiplier  # Size scales with RS quality

signal = Signal(
    symbol=symbol,
    confidence=adjusted_confidence,
    position_size=position_size,
    rs_score=rs_score,
    rs_multiplier=rs_multiplier,
    regime=market_regime
)
```

### Change 3: Track and Log Soft Gate Decisions

```python
# In signal_generator.py, add logging:

def _log_soft_gate_decision(self, symbol: str, rs_score: float, 
                            multiplier: float, base_confidence: float, 
                            adjusted_confidence: float):
    """Log soft gate decision for analysis"""
    
    logging.info(
        f"SOFT_GATE | {symbol} | RS={rs_score:.2f} | "
        f"mult={multiplier:.2f} | conf={base_confidence:.2f}→{adjusted_confidence:.2f}"
    )
    
    # Also track in metrics for daily review
    if not hasattr(self, 'soft_gate_decisions'):
        self.soft_gate_decisions = []
    
    self.soft_gate_decisions.append({
        'symbol': symbol,
        'rs_score': rs_score,
        'multiplier': multiplier,
        'base_confidence': base_confidence,
        'adjusted_confidence': adjusted_confidence,
        'timestamp': datetime.now()
    })
```

---

## Integration Checklist

- [ ] **Add RS feature calculation to pre_filter.py**
  - [ ] Implement _add_rs_features() method
  - [ ] Implement _get_spy_return() helper
  - [ ] Store 'rs_score' and 'alpha' in features dataframe
  - [ ] Test SPY data caching

- [ ] **Update signal_generator.py for soft gates**
  - [ ] Implement _get_rs_confidence_multiplier()
  - [ ] Implement _detect_market_regime()
  - [ ] Apply multiplier to confidence calculation
  - [ ] Apply multiplier to position sizing
  - [ ] Implement _log_soft_gate_decision()

- [ ] **Backward compatibility checks**
  - [ ] Phase 1b hard gates still work if feature unavailable
  - [ ] Feature flag: `enable_soft_gates` (default=True)
  - [ ] Fallback to Phase 1b behavior if RS calculation fails

- [ ] **Testing**
  - [ ] Unit tests for multiplier calculation
  - [ ] Unit tests for regime detection
  - [ ] Integration tests with pre_filter + signal_generator
  - [ ] Real scenario tests (Jan 26-30 trades)

- [ ] **Documentation**
  - [ ] Log format for soft gate decisions
  - [ ] Metrics to monitor (daily trade counts, avg multiplier, etc.)
  - [ ] Threshold tuning guide

---

## Expected Impact

### Trade Volume
- **Current (Phase 1b):** 5-8 trades/day
- **With Phase 2a:** 8-12 trades/day (+50%)
- **Reason:** Lower RS stocks now enter with small positions

### Quality Metrics
- **Win Rate:** 50%+ → 48-50% (slightly lower due to more borderline trades)
- **Avg Return/Win:** 1.2% (unchanged)
- **Avg Return/Loss:** -0.8% (unchanged)
- **Weekly ROI:** 5-8% → 6-9% (more consistent due to higher volume)

### Risk Profile
- **Max Drawdown:** Unchanged (total position size still ~20% of capital)
- **Position Concentration:** Reduced (more positions, each smaller)
- **Expected Sharpe Ratio:** Improved (higher returns, same risk)

---

## Timeline

**Tomorrow (Jan 31):**
- Implement soft gates in pre_filter.py + signal_generator.py (2 hours)
- Create unit tests for soft gate logic (1 hour)
- Test with Phase 1b validation suite

**Weekend (Feb 1-2):**
- Run integration tests (Phase 1 volume features + Phase 1b RS + Phase 2a soft gates)
- Backtest on Jan 26-30 trades to confirm impact
- Verify logging and metrics

**Next Week (Feb 3-7):**
- Deploy to paper trading
- Monitor daily metrics: trade count, average multiplier, win rate
- Adjust thresholds if needed (market regime detection tuning)

---

## Success Criteria

- ✅ Soft gates implemented (all 3 changes)
- ✅ All new unit tests passing (100%)
- ✅ Phase 1b validation tests still passing (no regressions)
- ✅ Paper trading: 8-12 trades/day (vs 5-8 before)
- ✅ Paper trading: Win rate ≥48% (vs 50%+ before, acceptable)
- ✅ Paper trading: Weekly ROI ≥6-7% (vs 5-8% before)

---

## Rollback Plan

If metrics degrade during paper trading:

**Option 1:** Tighten multipliers
```python
# Instead of 0.50 for RS < 0.4, use 0.35
# Reduces lowest-RS trades further
```

**Option 2:** Restore Phase 1b hard gates
```python
# Set `enable_soft_gates = False` in config
# Falls back to RS < 0.6 hard rejection
```

**Option 3:** Hybrid approach
```python
# RS < 0.3: Hard reject (no position)
# RS 0.3-0.6: Soft gate with 0.40 multiplier
# RS 0.6+: Full multiplier
```

---

## Sector Rotation Fit (Phase 2b Preview)

Phase 2a soft gates work together with Phase 2b sector rotation:

**Phase 2b will add:**
- If sector STRONG (>+2%): Loosen RS requirement (lower multiplier threshold)
- If sector WEAK (<-2%): Tighten RS requirement (higher threshold to accept)

**Example:** 
- With Phase 2a alone: RS 0.45 stock gets 0.85 multiplier
- With Phase 2b added:
  - If sector STRONG: RS 0.45 stock gets 1.00 multiplier (tighter filtering ignored)
  - If sector WEAK: RS 0.45 stock gets 0.60 multiplier (tighter than soft gate)

This creates dynamic adaptation to market conditions while maintaining quality.


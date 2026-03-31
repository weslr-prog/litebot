## Phase 1b: Relative Strength & Sector Rotation Implementation

**Date**: January 30, 2026  
**Priority**: CRITICAL (fixes root cause of this week's underperformance)  
**Status**: Design Phase  
**Effort**: 2-3 hours coding + 1 week testing

---

## Overview

Phase 1b adds three critical filters to prevent false momentum entries:
1. **Relative Strength (RS)**: Stock must beat SPY over N days
2. **Sector Momentum**: Stock must beat or align with sector ETF
3. **Decoupling Score**: Measure of alpha vs beta movement

These filters will be integrated into:
- `pre_filter.py`: Feature calculation layer (new module)
- `signal_generator.py`: Confidence adjustment (exists, needs modification)
- Testing: `test_phase1b_rs_sector_rotation.py` (new)

---

## 1. Architecture Design

### Data Flow (Existing + New)

```
Pre-Filter (existing)
├─ Load universe (257 mid-caps)
├─ Apply volume/price filters
├─ Phase 1: Volume/momentum features (NEW - Jan 29)
├─ Phase 1b: RS + Sector features (NEW - Jan 30) ← YOU ARE HERE
└─ Pass filtered universe to Signal Generator

Signal Generator (existing)
├─ Analyze each candidate
├─ Calculate momentum/RSI scores
├─ Phase 1b: Apply RS gates (NEW)
├─ Apply sentiment filters (Jan 29)
├─ Calculate confidence score
└─ Return signals sorted by confidence
```

### New Module: `rs_sector_enhancement.py`

```python
class RelativeStrengthAnalyzer:
    """Calculate RS between stock and SPY"""
    
    Methods:
    - calculate_rs(stock_prices, spy_prices, lookback=5) → rs_score
    - is_outperforming(stock_return, spy_return, threshold=0.01) → bool
    - get_decoupling_score(stock_return, market_return) → 0-1 score

class SectorRotationAnalyzer:
    """Analyze sector momentum and stock alignment"""
    
    Methods:
    - identify_sector(symbol) → sector_ticker (XLK, XLV, etc.)
    - get_sector_return(sector_ticker, lookback=5) → return_pct
    - is_beating_sector(stock_return, sector_return, threshold=0.005) → bool
    - get_sector_momentum(sector_ticker) → STRONG/NEUTRAL/WEAK
```

### Integration Points

**In pre_filter.py**:
```python
# NEW: Initialize RS/Sector analyzers
self.rs_analyzer = RelativeStrengthAnalyzer(data_loader)
self.sector_analyzer = SectorRotationAnalyzer(data_loader)

# NEW: Calculate features for each symbol
for symbol in candidates:
    stock_data = market_data[symbol]
    spy_data = market_data['SPY']  # Load SPY reference
    
    rs_data = {
        'stock_5d_return': calculate_return(stock_data, 5),
        'spy_5d_return': calculate_return(spy_data, 5),
        'rs_score': self.rs_analyzer.calculate_rs(stock_data, spy_data),
        'sector': self.sector_analyzer.identify_sector(symbol),
        'sector_return': self.sector_analyzer.get_sector_return(symbol),
        'decoupling_score': self.rs_analyzer.get_decoupling_score(...)
    }
    
    candidate['rs_data'] = rs_data
```

**In signal_generator.py**:
```python
# NEW: Apply RS gates before confidence calculation
def _apply_rs_filters(self, symbol: str, signal: AISignal, rs_data: Dict) -> Tuple[AISignal, bool]:
    """
    Apply RS/sector filters. Returns modified signal and acceptance flag.
    """
    
    # Gate 1: Market regime check
    if rs_data['spy_5d_return'] < -0.02:  # Market down >2%
        # Require higher RS to enter during weakness
        if rs_data['stock_5d_return'] < rs_data['spy_5d_return']:
            # Stock worse than market = reject
            return signal, False
        elif rs_data['stock_5d_return'] > 0:
            # Green in red market = boost confidence
            signal.confidence *= 1.3
            return signal, True
    
    # Gate 2: Sector rotation check
    sector_momentum = self.sector_analyzer.get_sector_momentum(rs_data['sector'])
    if sector_momentum == 'WEAK':
        # Sector in rotation, require stronger RS
        if rs_data['decoupling_score'] < 0.4:
            return signal, False  # Not decoupled enough
        else:
            signal.confidence *= 1.15  # Boost for fighting sector headwinds
    
    # Gate 3: Decoupling verification
    if rs_data['decoupling_score'] > 0.7:
        # High alpha = highest conviction
        signal.confidence *= 1.25
    elif rs_data['decoupling_score'] < 0.3:
        # Low alpha = no conviction boost
        pass
    
    return signal, True
```

---

## 2. Implementation Details

### Module 1: `rs_sector_enhancement.py` (NEW)

```python
import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

SECTOR_MAPPING = {
    # Technology
    'MSFT': 'XLK', 'AAPL': 'XLK', 'NVDA': 'XLK', 'APP': 'XLK', 'MRNA': 'XLV',
    'GTLB': 'XLK', 'LCID': 'XLK', 'NIO': 'XLK', 'NTLA': 'XLV',
    
    # Healthcare
    'MRNA': 'XLV', 'JNJ': 'XLV', 'PFE': 'XLV', 'BEKE': 'XLRE',
    
    # Energy
    'XOM': 'XLE', 'CVX': 'XLE', 'COP': 'XLE', 'OXY': 'XLE', 'DVN': 'XLE',
    'CLF': 'XME', 'SLB': 'XLE',
    
    # Utilities
    'NEE': 'XLU', 'AES': 'XLU', 'PR': 'XLU',
    
    # Materials/Metals
    'CLF': 'XME', 'FCX': 'XME', 'RIO': 'XME',
    
    # Financials
    'JPM': 'XLF', 'BAC': 'XLF',
    
    # Consumer/Discretionary
    'BEKE': 'XLY', 'TAL': 'XLY', 'ALK': 'XLY',
    
    # Real Estate
    'IYR': 'XLRE',
}

class RelativeStrengthAnalyzer:
    """Calculate and analyze relative strength (RS)"""
    
    def __init__(self, data_loader=None):
        self.data_loader = data_loader
        self._spy_cache = None
        self._spy_cache_date = None
        logger.info("✅ RelativeStrengthAnalyzer initialized")
    
    def _get_spy_data(self, market_data: Dict) -> Optional[pd.DataFrame]:
        """Get SPY data from market_data or cache"""
        if 'SPY' in market_data:
            return market_data['SPY']
        return None
    
    def calculate_rs(self, stock_prices: pd.DataFrame, spy_prices: pd.DataFrame,
                    lookback: int = 5) -> float:
        """
        Calculate Relative Strength score (0-1, higher = stronger)
        
        RS = (stock_return - spy_return) / max(|stock_return|, |spy_return|)
        Range: -1 (worst) to +1 (best)
        Normalized to 0-1 range
        """
        try:
            if len(stock_prices) < lookback or len(spy_prices) < lookback:
                return 0.5  # Neutral if insufficient data
            
            stock_return = (stock_prices['close'].iloc[-1] - stock_prices['close'].iloc[-lookback]) / stock_prices['close'].iloc[-lookback]
            spy_return = (spy_prices['close'].iloc[-1] - spy_prices['close'].iloc[-lookback]) / spy_prices['close'].iloc[-lookback]
            
            diff = stock_return - spy_return
            max_val = max(abs(stock_return), abs(spy_return), 0.01)
            
            # Normalize to 0-1 range
            rs_score = (diff / max_val + 1) / 2  # Maps [-1, 1] to [0, 1]
            return max(0, min(1, rs_score))  # Clamp to [0, 1]
        
        except Exception as e:
            logger.warning(f"Error calculating RS: {e}")
            return 0.5
    
    def get_decoupling_score(self, stock_return: float, market_return: float,
                            sector_return: float) -> float:
        """
        Calculate decoupling score (how independent the move is)
        
        High (0.7-1.0): Stock moving independently (high alpha)
        Medium (0.4-0.6): Stock moving with sector
        Low (0.0-0.3): Stock just following market/sector (low alpha)
        """
        try:
            # If stock return sign differs from market, it's decoupled
            if (stock_return > 0) and (market_return < 0):
                # "Green in red market" = maximum decoupling
                decoupling = 0.9 + (stock_return / 0.1) * 0.1  # Up to 1.0
            elif (stock_return < 0) and (market_return > 0):
                # "Red in green market" = anti-correlation
                decoupling = 0.1
            else:
                # Same direction: measure independence
                if abs(market_return) > 0.001:
                    decoupling = 1 - (abs(sector_return - stock_return) / abs(market_return))
                else:
                    decoupling = 0.5
            
            return max(0, min(1, decoupling))
        
        except Exception as e:
            logger.warning(f"Error calculating decoupling score: {e}")
            return 0.5


class SectorRotationAnalyzer:
    """Analyze sector momentum and alignment"""
    
    def __init__(self, data_loader=None):
        self.data_loader = data_loader
        self._sector_cache = {}
        logger.info("✅ SectorRotationAnalyzer initialized")
    
    def identify_sector(self, symbol: str) -> str:
        """Map stock symbol to sector ETF ticker"""
        return SECTOR_MAPPING.get(symbol.upper(), 'SPY')  # Default to broad market
    
    def get_sector_return(self, stock_symbol: str, sector_prices: Optional[pd.DataFrame] = None,
                         lookback: int = 5) -> float:
        """Calculate sector ETF return over lookback period"""
        try:
            if sector_prices is None or len(sector_prices) < lookback:
                return 0.0
            
            return (sector_prices['close'].iloc[-1] - sector_prices['close'].iloc[-lookback]) / sector_prices['close'].iloc[-lookback]
        
        except Exception as e:
            logger.warning(f"Error calculating sector return: {e}")
            return 0.0
    
    def get_sector_momentum(self, sector_return: float) -> str:
        """Classify sector momentum"""
        if sector_return > 0.03:
            return 'STRONG'
        elif sector_return > 0.01:
            return 'NEUTRAL'
        else:
            return 'WEAK'
    
    def is_beating_sector(self, stock_return: float, sector_return: float,
                         threshold: float = 0.005) -> bool:
        """Check if stock is outperforming its sector"""
        return (stock_return - sector_return) > threshold


def calculate_return(prices: pd.DataFrame, lookback: int) -> float:
    """Helper: Calculate simple return over N periods"""
    if len(prices) < lookback:
        return 0.0
    return (prices['close'].iloc[-1] - prices['close'].iloc[-lookback]) / prices['close'].iloc[-lookback]
```

### Module 2: Modifications to `pre_filter.py`

**Add to `__init__`**:
```python
# NEW: Initialize RS/Sector analyzers (Phase 1b)
try:
    from rs_sector_enhancement import RelativeStrengthAnalyzer, SectorRotationAnalyzer
    self.rs_analyzer = RelativeStrengthAnalyzer(data_loader=self.data_loader)
    self.sector_analyzer = SectorRotationAnalyzer(data_loader=self.data_loader)
    self.rs_sector_enabled = True
    logging.info("✅ RS/Sector enhancement enabled (Phase 1b)")
except ImportError:
    self.rs_sector_enabled = False
    logging.warning("⚠️ RS/Sector enhancement not available (Phase 1b disabled)")
```

**Add new method to `PreFilter` class**:
```python
def _calculate_rs_features(self, symbol: str, market_data: Dict) -> Dict:
    """
    Calculate RS and sector features for a symbol (Phase 1b)
    
    Returns dict with:
    - stock_5d_return: 5-day return
    - spy_5d_return: SPY 5-day return
    - rs_score: Relative strength score (0-1)
    - sector: Identified sector ETF
    - sector_return: Sector 5-day return
    - decoupling_score: Independence score (0-1)
    - gates_passed: List of passed RS gates
    """
    
    rs_features = {
        'stock_5d_return': 0.0,
        'spy_5d_return': 0.0,
        'rs_score': 0.5,
        'sector': 'SPY',
        'sector_return': 0.0,
        'decoupling_score': 0.5,
        'gates_passed': []
    }
    
    if not self.rs_sector_enabled:
        return rs_features
    
    try:
        stock_data = market_data.get(symbol)
        spy_data = market_data.get('SPY')
        sector_ticker = self.sector_analyzer.identify_sector(symbol)
        sector_data = market_data.get(sector_ticker)
        
        if stock_data is None or spy_data is None:
            return rs_features
        
        # Calculate returns
        stock_return = (stock_data['close'].iloc[-1] - stock_data['close'].iloc[-6]) / stock_data['close'].iloc[-6]
        spy_return = (spy_data['close'].iloc[-1] - spy_data['close'].iloc[-6]) / spy_data['close'].iloc[-6]
        sector_return = (sector_data['close'].iloc[-1] - sector_data['close'].iloc[-6]) / sector_data['close'].iloc[-6] if sector_data is not None else 0
        
        # RS calculation
        rs_score = self.rs_analyzer.calculate_rs(stock_data, spy_data)
        decoupling = self.rs_analyzer.get_decoupling_score(stock_return, spy_return, sector_return)
        
        rs_features.update({
            'stock_5d_return': stock_return,
            'spy_5d_return': spy_return,
            'rs_score': rs_score,
            'sector': sector_ticker,
            'sector_return': sector_return,
            'decoupling_score': decoupling,
            'gates_passed': []
        })
        
        # Determine which gates passed
        if rs_score > 0.5:
            rs_features['gates_passed'].append('RS_POSITIVE')
        if stock_return > spy_return:
            rs_features['gates_passed'].append('BEATING_SPY')
        if sector_data is not None and stock_return > sector_return:
            rs_features['gates_passed'].append('BEATING_SECTOR')
        if decoupling > 0.6:
            rs_features['gates_passed'].append('HIGH_ALPHA')
        
        return rs_features
    
    except Exception as e:
        logging.warning(f"Error calculating RS features for {symbol}: {e}")
        return rs_features
```

### Module 3: Modifications to `signal_generator.py`

**Modify `_analyze_symbol_with_reason` method** (around line 400):

```python
def _analyze_symbol_with_reason(self, symbol: str, data: pd.DataFrame) -> Tuple[Optional[AISignal], str, float]:
    """
    Analyze symbol for entry signals with RS/Sector gates (Phase 1b)
    """
    
    # ... existing analysis code ...
    
    # NEW: Apply RS/Sector gates (Phase 1b) BEFORE confidence scoring
    if hasattr(self, 'rs_data') and symbol in self.rs_data:
        rs_data = self.rs_data[symbol]
        signal, should_continue = self._apply_rs_gates(symbol, signal, rs_data)
        
        if not should_continue:
            confidence = signal.confidence if signal else 0.5
            return None, f"RS_GATE_FAILED: {rs_data.get('gate_reason', 'No alpha detected')}", confidence
        
        if signal:
            # Apply confidence multipliers based on RS strength
            signal.confidence = self._adjust_confidence_for_rs(signal.confidence, rs_data)
    
    # ... rest of existing analysis ...
    
    return signal, "", signal.confidence if signal else 0.0

def _apply_rs_gates(self, symbol: str, signal: Optional[AISignal], rs_data: Dict) -> Tuple[Optional[AISignal], bool]:
    """
    Apply hard gates and confidence adjustments based on RS/Sector data
    
    Hard gates (rejection):
    - If market down >2% and stock not green in red: REJECT
    - If sector weak and stock not beating sector: REJECT
    
    Confidence adjustments:
    - Green in red market: +30%
    - Beating sector during weakness: +15%
    - High decoupling (>0.7): +25%
    """
    
    if not signal:
        return None, False
    
    stock_return = rs_data.get('stock_5d_return', 0)
    spy_return = rs_data.get('spy_5d_return', 0)
    sector_return = rs_data.get('sector_return', 0)
    decoupling = rs_data.get('decoupling_score', 0.5)
    
    # HARD GATE 1: Market down significantly
    if spy_return < -0.02:  # SPY down >2%
        # Require stock to be green in red market or strong RS
        if stock_return <= 0 and rs_data.get('rs_score', 0) < 0.55:
            rs_data['gate_reason'] = f"Market down {spy_return:.2%}, stock down {stock_return:.2%}, RS weak"
            return signal, False
    
    # HARD GATE 2: Sector weakness
    sector_momentum = 'WEAK' if sector_return < 0.01 else 'STRONG' if sector_return > 0.03 else 'NEUTRAL'
    if sector_momentum == 'WEAK':
        # Require high decoupling to trade through sector headwinds
        if decoupling < 0.45:
            rs_data['gate_reason'] = f"Sector weak ({sector_return:.2%}), stock not decoupled (score: {decoupling:.2f})"
            return signal, False
    
    # Apply confidence multipliers
    if stock_return > 0 and spy_return < 0:
        # Green in red market = strongest signal
        signal.confidence *= 1.3
        rs_data['confidence_boost'] = 1.3
    elif rs_data.get('rs_score', 0) > 0.6:
        # Beating SPY
        signal.confidence *= 1.15
        rs_data['confidence_boost'] = 1.15
    elif decoupling > 0.7:
        # High alpha
        signal.confidence *= 1.25
        rs_data['confidence_boost'] = 1.25
    
    rs_data['gate_passed'] = True
    return signal, True

def _adjust_confidence_for_rs(self, base_confidence: float, rs_data: Dict) -> float:
    """Apply final confidence adjustment based on RS metrics"""
    
    multiplier = rs_data.get('confidence_boost', 1.0)
    adjusted = base_confidence * multiplier
    
    # Apply hard ceiling/floor for sanity
    return max(0.3, min(0.95, adjusted))
```

---

## 3. Testing Strategy

### Test File: `test_phase1b_rs_sector_rotation.py`

```python
import unittest
import pandas as pd
import numpy as np
from rs_sector_enhancement import RelativeStrengthAnalyzer, SectorRotationAnalyzer
from signal_generator import AISignalGenerator
from pre_filter import PreFilter

class TestPhase1bRS(unittest.TestCase):
    """Test RS and Sector Rotation filters (Phase 1b)"""
    
    def setUp(self):
        self.rs_analyzer = RelativeStrengthAnalyzer()
        self.sector_analyzer = SectorRotationAnalyzer()
    
    def test_rs_calculation_green_in_red(self):
        """Test RS calculation when stock green and market red"""
        # Stock up 2%, SPY down 1% → High RS
        stock_data = pd.DataFrame({'close': [100, 101, 102]})
        spy_data = pd.DataFrame({'close': [100, 99, 99]})
        
        rs = self.rs_analyzer.calculate_rs(stock_data, spy_data, lookback=1)
        self.assertGreater(rs, 0.7, "Green in red should give high RS")
    
    def test_rs_calculation_red_in_green(self):
        """Test RS calculation when stock red and market green"""
        stock_data = pd.DataFrame({'close': [100, 99, 98]})
        spy_data = pd.DataFrame({'close': [100, 101, 102]})
        
        rs = self.rs_analyzer.calculate_rs(stock_data, spy_data, lookback=1)
        self.assertLess(rs, 0.3, "Red in green should give low RS")
    
    def test_decoupling_high_alpha(self):
        """Test decoupling score for high alpha moves"""
        # Stock +2%, market +0.5% → High alpha
        decoupling = self.rs_analyzer.get_decoupling_score(0.02, 0.005, 0.006)
        self.assertGreater(decoupling, 0.6, "Stock outperforming should show high decoupling")
    
    def test_decoupling_low_alpha(self):
        """Test decoupling score for low alpha moves"""
        # Stock +1%, market +0.9% → Low alpha
        decoupling = self.rs_analyzer.get_decoupling_score(0.01, 0.009, 0.008)
        self.assertLess(decoupling, 0.4, "Stock following market should show low decoupling")
    
    def test_sector_momentum_classification(self):
        """Test sector momentum classification"""
        self.assertEqual(self.sector_analyzer.get_sector_momentum(0.05), 'STRONG')
        self.assertEqual(self.sector_analyzer.get_sector_momentum(0.02), 'NEUTRAL')
        self.assertEqual(self.sector_analyzer.get_sector_momentum(0.00), 'WEAK')
    
    def test_sector_identification(self):
        """Test that stocks map to correct sectors"""
        self.assertEqual(self.sector_analyzer.identify_sector('MRNA'), 'XLV')
        self.assertEqual(self.sector_analyzer.identify_sector('DVN'), 'XLE')
        self.assertEqual(self.sector_analyzer.identify_sector('CLF'), 'XME')
    
    def test_hard_gate_market_down(self):
        """Test hard gate: Market down >2%, stock not green in red"""
        # SPY down 2.5%, stock down 2% → Should be rejected
        rs_data = {
            'stock_5d_return': -0.02,
            'spy_5d_return': -0.025,
            'rs_score': 0.45,
            'sector_return': -0.02,
            'decoupling_score': 0.3
        }
        
        # This should be rejected by _apply_rs_gates
        # (test in integration test below)
    
    def test_gate_green_in_red_boosted(self):
        """Test that green-in-red moves get confidence boost"""
        rs_data = {
            'stock_5d_return': 0.01,  # +1%
            'spy_5d_return': -0.01,   # -1%
            'rs_score': 0.8,
            'decoupling_score': 0.95
        }
        
        # Signal should get +30% confidence boost
        # (test in integration test below)


class TestPhase1bIntegration(unittest.TestCase):
    """Integration tests with signal generator"""
    
    def setUp(self):
        self.config = ShortCycleConfig()
        self.generator = AISignalGenerator(config=self.config)
    
    def test_jan26_scenario_rejected(self):
        """
        Scenario: Jan 26 MRNA entry
        Market: SPY -0.5%, Tech -1.2%
        Stock: MRNA -0.3% (lagging market)
        Expected: REJECT due to no alpha
        """
        # Test data for Jan 26
        rs_data = {
            'stock_5d_return': -0.003,
            'spy_5d_return': -0.005,
            'rs_score': 0.48,
            'sector': 'XLV',
            'sector_return': -0.012,
            'decoupling_score': 0.2
        }
        
        # Should be rejected
        should_enter = rs_data['decoupling_score'] > 0.4 and rs_data['rs_score'] > 0.5
        self.assertFalse(should_enter, "Lagging stock should be rejected")
    
    def test_jan27_oxy_accepted_boosted(self):
        """
        Scenario: Jan 27 OXY entry
        Market: SPY +0.3%, Energy +0.8%
        Stock: OXY +1.2% (beating sector)
        Expected: ACCEPT with +15% confidence boost
        """
        rs_data = {
            'stock_5d_return': 0.012,
            'spy_5d_return': 0.003,
            'rs_score': 0.65,
            'sector': 'XLE',
            'sector_return': 0.008,
            'decoupling_score': 0.75
        }
        
        # Should be accepted
        should_enter = rs_data['decoupling_score'] > 0.4 and rs_data['rs_score'] > 0.5
        self.assertTrue(should_enter, "Beating sector should be accepted")
        
        # Confidence boost calculation
        if rs_data['rs_score'] > 0.6:
            boost = 1.15
        self.assertEqual(boost, 1.15)


if __name__ == '__main__':
    unittest.main()
```

---

## 4. Integration Checklist

- [ ] Create `rs_sector_enhancement.py` with RS and Sector analyzers
- [ ] Add imports and initialization to `pre_filter.py`
- [ ] Add `_calculate_rs_features()` method to PreFilter
- [ ] Add feature calculation loop in `PreFilter.filter()` method
- [ ] Modify `signal_generator.py` to import RS data
- [ ] Add `_apply_rs_gates()` method to AISignalGenerator
- [ ] Modify `_analyze_symbol_with_reason()` to call RS gates
- [ ] Create feature flag: `enable_rs_sector_filters` (default: True)
- [ ] Create `test_phase1b_rs_sector_rotation.py`
- [ ] Run unit tests (target: 10/10 pass)
- [ ] Run integration with Phase 1 tests
- [ ] Paper trading validation (1 week)

---

## 5. Rollback Plan

If Phase 1b causes issues:

```python
# Feature flag in config:
enable_rs_sector_filters: false  # Disables all RS/Sector checking

# When disabled:
- RS gates still calculated (for logging)
- But not used for entry decisions
- Signal generation reverts to Phase 1 behavior
- Zero impact on existing trading
```

---

## 6. Success Criteria

### Immediate (First Week):
- ✅ All 10/10 unit tests pass
- ✅ Phase 1 tests still pass
- ✅ Integration tests pass (no regressions)
- ✅ Log analysis shows RS gates working
- ✅ Trade count stable (-5% to +5%)

### Results-Based (2-4 Weeks):
- ✅ Win rate increase: 40% → 50%+
- ✅ Average trade return: -0.99% → +0.5-1.0%
- ✅ Reduced whipsaws: 60% fewer day-holds with losses
- ✅ Sector alignment: 80%+ of entries in favored sectors

### Performance Gates:
```
Weekly ROI Target Progression:
- Baseline (no Phase 1b): 0% to 2%
- Phase 1b active: +3% to +5%
- Combined Phase 1+1b: +5% to +7%

Auto-Rollback Triggers:
- If weekly ROI < baseline - 2% for 2 weeks: rollback
- If win rate drops below 35%: rollback
- If capital utilization < 40%: investigate, don't auto-rollback
```

---

## 7. Timeline

**Day 1 (Jan 30)**: Design + initial implementation
- Create `rs_sector_enhancement.py`
- Integrate into `pre_filter.py`
- Create test file

**Day 2 (Jan 31)**: Integration + testing
- Integrate RS gates into `signal_generator.py`
- Run full test suite
- Fix any regressions

**Week of Feb 3**: Paper trading
- Monitor live performance
- Tune sensitivity thresholds
- Verify gate effectiveness

**Week of Feb 10**: Validation
- Analyze win rate and capital efficiency
- Compare to baseline
- Approve for production or iterate


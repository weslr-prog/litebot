#!/usr/bin/env python3
"""
Regime-Aware Strategy Controller
Controls overall strategy execution based on market regime detection
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import numpy as np
import pandas as pd

@dataclass
class RegimeConfig:
    """Configuration for regime-based strategy control"""
    # Portfolio exposure limits by regime
    exposure_limits: Dict[str, float]
    
    # Minimum confidence thresholds by regime  
    confidence_thresholds: Dict[str, float]
    
    # Momentum lookback adjustments by regime
    lookback_multipliers: Dict[str, float]
    
    # Maximum positions by regime
    max_positions: Dict[str, int]


class RegimeAwareController:
    """
    Controls strategy execution based on market regime
    
    Key Functions:
    - Detects current market regime
    - Adjusts portfolio exposure based on regime
    - Modifies position sizing and selection criteria
    - Implements regime-specific risk controls
    """
    
    def __init__(self):
        # Regime-based configuration
        self.regime_config = RegimeConfig(
            
            # Portfolio exposure limits (% of capital deployed)
            exposure_limits={
                'UP_LOWVOL': 0.95,     # Bull market - almost fully invested
                'bull': 0.90,          # Strong uptrend - high exposure
                'UP_HIGHVOL': 0.75,    # Volatile uptrend - moderate caution
                'sideways': 0.60,      # Range-bound - moderate exposure
                'volatile': 0.45,      # High volatility - defensive
                'DOWN_LOWVOL': 0.30,   # Weak decline - very defensive
                'bear': 0.20,          # Bear market - minimal exposure
                'DOWN_HIGHVOL': 0.10   # Volatile decline - cash mode
            },
            
            # Signal confidence thresholds (only trade high-confidence signals in bad regimes)
            confidence_thresholds={
                'UP_LOWVOL': 0.3,      # Low bar in good markets
                'bull': 0.4,           # Moderate bar in uptrends
                'UP_HIGHVOL': 0.5,     # Higher bar in volatile uptrends
                'sideways': 0.6,       # Picky in sideways markets
                'volatile': 0.7,       # Very picky in volatility
                'DOWN_LOWVOL': 0.8,    # Only best signals in declines
                'bear': 0.85,          # Only exceptional signals in bear
                'DOWN_HIGHVOL': 0.95   # Essentially no trading in crashes
            },
            
            # Momentum lookback period adjustments
            lookback_multipliers={
                'UP_LOWVOL': 1.0,      # Standard lookbacks in stable up
                'bull': 0.8,           # Shorter lookbacks in strong trends
                'UP_HIGHVOL': 1.2,     # Longer lookbacks in volatile up
                'sideways': 1.5,       # Much longer lookbacks in chop
                'volatile': 1.3,       # Longer lookbacks for stability
                'DOWN_LOWVOL': 1.4,    # Longer lookbacks in decline
                'bear': 1.6,           # Longest lookbacks in bear
                'DOWN_HIGHVOL': 2.0    # Maximum lookbacks in crashes
            },
            
            # Maximum positions for weekly ROI focus
            max_positions={
                'UP_LOWVOL': 25,       # Maximum diversification for weekly ROI
                'bull': 20,            # High diversification in bull markets
                'UP_HIGHVOL': 15,      # Moderate diversification with volatility
                'sideways': 12,        # Balanced approach in sideways markets
                'volatile': 10,        # Some concentration with volatility
                'DOWN_LOWVOL': 8,      # Defensive but still diversified
                'bear': 5,             # Concentrated defensive positions
                'DOWN_HIGHVOL': 3      # Minimal positions in crisis
            }
        )
        
        self.current_regime = 'sideways'  # Default to neutral
        self.regime_confidence = 0.5
        self.regime_history = []
        
        logging.info("🎛️ Regime-Aware Strategy Controller initialized")
    
    def detect_market_regime(self, market_data: Dict) -> Tuple[str, float]:
        """
        Detect current market regime based on multiple indicators
        
        Returns:
            Tuple of (regime_name, confidence_score)
        """
        try:
            spy_data = market_data.get('SPY', pd.DataFrame())
            if spy_data.empty:
                logging.warning("No SPY data for regime detection, using default")
                return 'sideways', 0.5
            
            # Calculate key regime indicators
            prices = spy_data['close']
            volumes = spy_data['volume']
            
            # Trend indicators
            sma_20 = prices.rolling(20).mean().iloc[-1]
            sma_50 = prices.rolling(50).mean().iloc[-1] 
            current_price = prices.iloc[-1]
            
            # Volatility indicators
            returns = prices.pct_change().dropna()
            vol_20d = returns.rolling(20).std().iloc[-1] * np.sqrt(252)
            vol_50d = returns.rolling(50).std().iloc[-1] * np.sqrt(252)
            
            # Volume indicators
            avg_volume = volumes.rolling(20).mean().iloc[-1]
            recent_volume = volumes.rolling(5).mean().iloc[-1]
            
            # Price momentum
            returns_1m = (current_price / prices.iloc[-21] - 1) if len(prices) >= 21 else 0
            returns_3m = (current_price / prices.iloc[-63] - 1) if len(prices) >= 63 else 0
            
            # Regime classification logic
            is_uptrend = current_price > sma_20 > sma_50 and returns_1m > 0
            is_downtrend = current_price < sma_20 < sma_50 and returns_1m < 0
            is_high_vol = vol_20d > vol_50d * 1.5
            is_strong_momentum = abs(returns_1m) > 0.05
            
            # Classify regime
            regime, confidence = self._classify_regime(
                is_uptrend, is_downtrend, is_high_vol, 
                is_strong_momentum, returns_1m, vol_20d
            )
            
            # Update regime tracking
            self.current_regime = regime
            self.regime_confidence = confidence
            self.regime_history.append({
                'timestamp': datetime.now(),
                'regime': regime,
                'confidence': confidence,
                'price': current_price,
                'volatility': vol_20d
            })
            
            # Keep only last 100 regime observations
            if len(self.regime_history) > 100:
                self.regime_history = self.regime_history[-100:]
            
            return regime, confidence
            
        except Exception as e:
            logging.error(f"Error in regime detection: {e}")
            return 'sideways', 0.5
    
    def _classify_regime(self, is_uptrend: bool, is_downtrend: bool, 
                        is_high_vol: bool, is_strong_momentum: bool,
                        returns_1m: float, volatility: float) -> Tuple[str, float]:
        """Classify the specific regime based on indicators"""
        
        # High confidence thresholds
        confidence = 0.8
        
        # Primary classification
        if is_uptrend and is_strong_momentum:
            if is_high_vol:
                return 'UP_HIGHVOL', confidence
            else:
                return 'UP_LOWVOL', confidence
                
        elif is_downtrend and is_strong_momentum:
            if is_high_vol:
                return 'DOWN_HIGHVOL', confidence
            else:
                return 'DOWN_LOWVOL', confidence
                
        elif is_uptrend:
            return 'bull', confidence * 0.7
            
        elif is_downtrend:
            return 'bear', confidence * 0.7
            
        elif is_high_vol:
            return 'volatile', confidence * 0.6
            
        else:
            return 'sideways', confidence * 0.5
    
    def get_regime_adjusted_exposure(self, current_portfolio_value: float) -> float:
        """Get maximum portfolio exposure for current regime"""
        max_exposure_pct = self.regime_config.exposure_limits[self.current_regime]
        max_exposure_dollars = current_portfolio_value * max_exposure_pct
        
        logging.info(f"📊 Regime {self.current_regime}: Max exposure {max_exposure_pct:.0%} (${max_exposure_dollars:,.0f})")
        return max_exposure_dollars
    
    def get_regime_adjusted_confidence_threshold(self) -> float:
        """Get minimum confidence threshold for current regime"""
        threshold = self.regime_config.confidence_thresholds[self.current_regime]
        logging.info(f"🎯 Regime {self.current_regime}: Min confidence {threshold:.1%}")
        return threshold
    
    def get_regime_adjusted_lookback(self, base_lookback: int) -> int:
        """Get adjusted momentum lookback period for current regime"""
        multiplier = self.regime_config.lookback_multipliers[self.current_regime]
        adjusted_lookback = int(base_lookback * multiplier)
        logging.info(f"📈 Regime {self.current_regime}: Lookback {base_lookback}d → {adjusted_lookback}d")
        return adjusted_lookback
    
    def get_regime_adjusted_max_positions(self) -> int:
        """Get maximum positions allowed for current regime"""
        max_pos = self.regime_config.max_positions[self.current_regime]
        logging.info(f"🎲 Regime {self.current_regime}: Max positions {max_pos}")
        return max_pos
    
    def should_trade_in_regime(self, signal_confidence: float) -> bool:
        """Determine if trading should proceed given regime and signal quality"""
        required_confidence = self.get_regime_adjusted_confidence_threshold()
        should_trade = signal_confidence >= required_confidence
        
        if not should_trade:
            logging.info(f"🛑 Trading blocked: Signal confidence {signal_confidence:.1%} < required {required_confidence:.1%}")
        
        return should_trade
    
    def filter_signals_by_regime(self, signals: List[Dict]) -> List[Dict]:
        """Filter and adjust signals based on current regime"""
        if not signals:
            return signals
        
        # Get regime parameters
        min_confidence = self.get_regime_adjusted_confidence_threshold()
        max_positions = self.get_regime_adjusted_max_positions()
        
        # Filter by confidence
        filtered_signals = [
            signal for signal in signals 
            if signal.get('confidence', 0) >= min_confidence
        ]
        
        # Sort by confidence and take top N
        filtered_signals.sort(key=lambda x: x.get('confidence', 0), reverse=True)
        final_signals = filtered_signals[:max_positions]
        
        logging.info(f"🔍 Regime filter: {len(signals)} → {len(final_signals)} signals")
        return final_signals
    
    def get_regime_summary(self) -> Dict:
        """Get current regime status summary"""
        return {
            'current_regime': self.current_regime,
            'confidence': self.regime_confidence,
            'max_exposure_pct': self.regime_config.exposure_limits[self.current_regime],
            'min_signal_confidence': self.regime_config.confidence_thresholds[self.current_regime],
            'max_positions': self.regime_config.max_positions[self.current_regime],
            'lookback_multiplier': self.regime_config.lookback_multipliers[self.current_regime]
        }


# Test the regime controller
if __name__ == "__main__":
    import pandas as pd
    
    # Create test controller
    controller = RegimeAwareController()
    
    # Test regime detection with mock data
    mock_spy_data = pd.DataFrame({
        'close': [400 + i + np.random.normal(0, 2) for i in range(100)],
        'volume': [50000000 + np.random.normal(0, 5000000) for _ in range(100)]
    })
    
    regime, confidence = controller.detect_market_regime({'SPY': mock_spy_data})
    print(f"Detected regime: {regime} (confidence: {confidence:.1%})")
    print("Regime configuration:", controller.get_regime_summary())

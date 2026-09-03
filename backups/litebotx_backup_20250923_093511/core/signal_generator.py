"""
ML-Enhanced Signal Generator for LiteBotX - Phase 3
Purpose: Generate high-confidence trading signals using multiple strategies and ML scoring
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone
import warnings
warnings.filterwarnings('ignore')

try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.preprocessing import StandardScaler
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    logging.warning("⚠️ ML libraries not available, using traditional signals only")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

class SignalGenerator:
    """
    Multi-strategy signal generator with ML enhancement
    
    Features:
    - Traditional technical indicators (RSI, MACD, Bollinger Bands)
    - Breakout detection for high-return opportunities
    - ML ensemble scoring (when available)
    - Regime-aware signal strength adjustment
    - Confidence scoring for risk management integration
    """
    
    def __init__(self):
        self.ml_enabled = ML_AVAILABLE
        self.scaler = StandardScaler() if ML_AVAILABLE else None
        self.ml_model = None
        self.signal_history = []
        
        # Strategy weights for ensemble
        self.strategy_weights = {
            'rsi': 0.20,
            'macd': 0.25,
            'bollinger': 0.20,
            'breakout': 0.35  # Higher weight for breakout (5% weekly target)
        }
        
        logging.info(f"�� SignalGenerator initialized (ML: {'✅' if self.ml_enabled else '❌'})")

    def generate_signal(self, symbol: str, price_data: pd.DataFrame, 
                       regime: str, volume_data: Optional[pd.DataFrame] = None) -> Dict:
        """
        Generate comprehensive trading signal with confidence score
        
        Args:
            symbol: Stock symbol
            price_data: OHLCV DataFrame
            regime: Current market regime
            volume_data: Optional volume profile data
            
        Returns:
            Dict with signal, confidence, and strategy details
        """
        if len(price_data) < 50:
            return {
                'signal': 'hold',
                'confidence': 0.0,
                'reason': 'insufficient_data',
                'strategies': {}
            }
        
        # Calculate all technical indicators
        indicators = self._calculate_indicators(price_data)
        
        # Generate signals from each strategy
        strategy_signals = {
            'rsi': self._rsi_signal(indicators),
            'macd': self._macd_signal(indicators),
            'bollinger': self._bollinger_signal(indicators),
            'breakout': self._breakout_signal(price_data, volume_data)
        }
        
        # Apply regime adjustments
        adjusted_signals = self._apply_regime_adjustments(strategy_signals, regime)
        
        # Calculate ensemble signal
        ensemble_result = self._calculate_ensemble_signal(adjusted_signals)
        
        # Final signal decision
        final_signal = self._make_final_decision(ensemble_result, regime)
        
        # Log signal generation
        logging.info(f"📡 {symbol} signal: {final_signal['signal']} "
                    f"(confidence: {final_signal['confidence']:.2f}, regime: {regime})")
        
        return final_signal

    def _calculate_indicators(self, data: pd.DataFrame) -> Dict:
        """Calculate all technical indicators"""
        close = data['close']
        high = data['high']
        low = data['low']
        volume = data['volume']
        
        # RSI
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        # MACD
        ema12 = close.ewm(span=12).mean()
        ema26 = close.ewm(span=26).mean()
        macd = ema12 - ema26
        macd_signal = macd.ewm(span=9).mean()
        macd_histogram = macd - macd_signal
        
        # Bollinger Bands
        sma20 = close.rolling(20).mean()
        std20 = close.rolling(20).std()
        bb_upper = sma20 + (std20 * 2)
        bb_lower = sma20 - (std20 * 2)
        bb_position = (close - bb_lower) / (bb_upper - bb_lower)
        
        # Price momentum
        price_momentum_5 = (close / close.shift(5) - 1)
        price_momentum_20 = (close / close.shift(20) - 1)
        
        # Volume indicators
        volume_sma = volume.rolling(20).mean()
        volume_ratio = volume / volume_sma
        
        # Volatility (for breakout detection)
        returns = close.pct_change()
        volatility = returns.rolling(20).std()
        
        return {
            'rsi': rsi.iloc[-1] if not rsi.empty else 50,
            'macd': macd.iloc[-1] if not macd.empty else 0,
            'macd_signal': macd_signal.iloc[-1] if not macd_signal.empty else 0,
            'macd_histogram': macd_histogram.iloc[-1] if not macd_histogram.empty else 0,
            'bb_position': bb_position.iloc[-1] if not bb_position.empty else 0.5,
            'price_momentum_5': price_momentum_5.iloc[-1] if not price_momentum_5.empty else 0,
            'price_momentum_20': price_momentum_20.iloc[-1] if not price_momentum_20.empty else 0,
            'volume_ratio': volume_ratio.iloc[-1] if not volume_ratio.empty else 1.0,
            'volatility': volatility.iloc[-1] if not volatility.empty else 0.02,
            'close': close.iloc[-1],
            'high_20': high.rolling(20).max().iloc[-1] if len(high) >= 20 else high.iloc[-1],
            'low_20': low.rolling(20).min().iloc[-1] if len(low) >= 20 else low.iloc[-1]
        }

    def _rsi_signal(self, indicators: Dict) -> Dict:
        """RSI-based signal generation"""
        rsi = indicators['rsi']
        
        if rsi < 30:
            return {'signal': 'buy', 'strength': (30 - rsi) / 30, 'reason': 'oversold'}
        elif rsi > 70:
            return {'signal': 'sell', 'strength': (rsi - 70) / 30, 'reason': 'overbought'}
        else:
            return {'signal': 'hold', 'strength': 0.0, 'reason': 'neutral'}

    def _macd_signal(self, indicators: Dict) -> Dict:
        """MACD-based signal generation"""
        macd = indicators['macd']
        macd_signal = indicators['macd_signal']
        histogram = indicators['macd_histogram']
        
        # MACD crossover signals
        if macd > macd_signal and histogram > 0:
            strength = min(1.0, abs(histogram) * 10)  # Scale histogram
            return {'signal': 'buy', 'strength': strength, 'reason': 'bullish_crossover'}
        elif macd < macd_signal and histogram < 0:
            strength = min(1.0, abs(histogram) * 10)
            return {'signal': 'sell', 'strength': strength, 'reason': 'bearish_crossover'}
        else:
            return {'signal': 'hold', 'strength': 0.0, 'reason': 'no_crossover'}

    def _bollinger_signal(self, indicators: Dict) -> Dict:
        """Bollinger Bands signal generation"""
        bb_position = indicators['bb_position']
        
        if bb_position < 0.1:  # Near lower band
            return {'signal': 'buy', 'strength': (0.1 - bb_position) * 10, 'reason': 'lower_band_bounce'}
        elif bb_position > 0.9:  # Near upper band
            return {'signal': 'sell', 'strength': (bb_position - 0.9) * 10, 'reason': 'upper_band_rejection'}
        else:
            return {'signal': 'hold', 'strength': 0.0, 'reason': 'middle_range'}

    def _breakout_signal(self, price_data: pd.DataFrame, volume_data: Optional[pd.DataFrame] = None) -> Dict:
        """Enhanced breakout detection for high-return opportunities"""
        close = price_data['close']
        high = price_data['high']
        low = price_data['low']
        volume = price_data['volume']
        
        if len(price_data) < 20:
            return {'signal': 'hold', 'strength': 0.0, 'reason': 'insufficient_data'}
        
        # Calculate breakout levels
        high_20 = high.rolling(20).max().iloc[-2]  # Previous high (exclude current)
        low_20 = low.rolling(20).min().iloc[-2]    # Previous low
        current_price = close.iloc[-1]
        
        # Volume confirmation
        avg_volume = volume.rolling(20).mean().iloc[-1]
        current_volume = volume.iloc[-1]
        volume_surge = current_volume > (avg_volume * 1.5)
        
        # Volatility for breakout strength
        returns = close.pct_change()
        volatility = returns.rolling(10).std().iloc[-1]
        
        # Upside breakout
        if current_price > high_20:
            breakout_strength = (current_price - high_20) / high_20
            volume_boost = 1.5 if volume_surge else 1.0
            volatility_boost = min(2.0, volatility / 0.02)  # Scale by 2% base vol
            
            strength = min(1.0, breakout_strength * 20 * volume_boost * volatility_boost)
            return {'signal': 'buy', 'strength': strength, 'reason': 'upside_breakout'}
        
        # Downside breakdown
        elif current_price < low_20:
            breakdown_strength = (low_20 - current_price) / low_20
            volume_boost = 1.5 if volume_surge else 1.0
            volatility_boost = min(2.0, volatility / 0.02)
            
            strength = min(1.0, breakdown_strength * 20 * volume_boost * volatility_boost)
            return {'signal': 'sell', 'strength': strength, 'reason': 'downside_breakdown'}
        
        else:
            return {'signal': 'hold', 'strength': 0.0, 'reason': 'no_breakout'}

    def _apply_regime_adjustments(self, signals: Dict, regime: str) -> Dict:
        """Adjust signal strengths based on market regime"""
        regime_adjustments = {
            'UP_LOWVOL': {'buy': 1.2, 'sell': 0.8, 'hold': 1.0},    # Favor bullish signals
            'UP_HIGHVOL': {'buy': 1.0, 'sell': 0.9, 'hold': 1.0},   # Neutral with slight bull bias
            'DOWN_LOWVOL': {'buy': 0.8, 'sell': 1.2, 'hold': 1.0},  # Favor bearish signals
            'DOWN_HIGHVOL': {'buy': 0.5, 'sell': 1.5, 'hold': 1.0}, # Strong bear bias
            'SIDEWAYS': {'buy': 0.9, 'sell': 0.9, 'hold': 1.1}      # Prefer range trading
        }
        
        adjustments = regime_adjustments.get(regime, {'buy': 1.0, 'sell': 1.0, 'hold': 1.0})
        
        adjusted_signals = {}
        for strategy, signal_data in signals.items():
            signal_type = signal_data['signal']
            adjusted_strength = signal_data['strength'] * adjustments[signal_type]
            
            adjusted_signals[strategy] = {
                'signal': signal_type,
                'strength': min(1.0, adjusted_strength),  # Cap at 1.0
                'reason': signal_data['reason'],
                'regime_adjusted': True
            }
        
        return adjusted_signals

    def _calculate_ensemble_signal(self, signals: Dict) -> Dict:
        """Calculate weighted ensemble signal from all strategies"""
        buy_score = 0.0
        sell_score = 0.0
        total_weight = 0.0
        
        strategy_details = {}
        
        for strategy, signal_data in signals.items():
            weight = self.strategy_weights.get(strategy, 0.1)
            strength = signal_data['strength']
            
            strategy_details[strategy] = signal_data
            
            if signal_data['signal'] == 'buy':
                buy_score += weight * strength
            elif signal_data['signal'] == 'sell':
                sell_score += weight * strength
            
            total_weight += weight
        
        # Normalize scores
        buy_score /= total_weight
        sell_score /= total_weight
        
        # Determine final signal
        if buy_score > sell_score and buy_score > 0.3:
            signal = 'buy'
            confidence = buy_score
        elif sell_score > buy_score and sell_score > 0.3:
            signal = 'sell'
            confidence = sell_score
        else:
            signal = 'hold'
            confidence = max(buy_score, sell_score)
        
        return {
            'signal': signal,
            'confidence': confidence,
            'buy_score': buy_score,
            'sell_score': sell_score,
            'strategies': strategy_details
        }

    def _make_final_decision(self, ensemble_result: Dict, regime: str) -> Dict:
        """Make final signal decision with regime-specific thresholds"""
        signal = ensemble_result['signal']
        confidence = ensemble_result['confidence']
        
        # Regime-specific confidence thresholds
        confidence_thresholds = {
            'UP_LOWVOL': 0.4,     # Lower threshold in favorable conditions
            'UP_HIGHVOL': 0.5,    # Standard threshold
            'DOWN_LOWVOL': 0.6,   # Higher threshold in uncertain conditions
            'DOWN_HIGHVOL': 0.7,  # Very high threshold in adverse conditions
            'SIDEWAYS': 0.5
        }
        
        threshold = confidence_thresholds.get(regime, 0.5)
        
        # Override to hold if confidence too low
        if confidence < threshold:
            signal = 'hold'
            confidence = confidence * 0.5  # Reduce confidence for hold
        
        return {
            'signal': signal,
            'confidence': min(1.0, confidence),
            'regime': regime,
            'threshold_used': threshold,
            'strategies': ensemble_result['strategies'],
            'scores': {
                'buy_score': ensemble_result['buy_score'],
                'sell_score': ensemble_result['sell_score']
            },
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

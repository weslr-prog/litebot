"""
Enhanced Regime Detector - Phase 3A ML Enhancement
Purpose: Advanced market regime classification with ML features
Integration: Works with existing regime_detector.py and signal_confidence.py
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import logging
from datetime import datetime, timedelta

# Import existing components
from .regime_detector import RegimeDetector
from .signal_confidence import SignalFeatures

logger = logging.getLogger("LiteBot")

@dataclass
class RegimeFeatures:
    """Enhanced feature set for regime classification"""
    # Trend features
    sma_slope_10d: float
    sma_slope_20d: float
    sma_slope_50d: float
    price_vs_sma20: float
    price_vs_sma50: float
    
    # Volatility features  
    volatility_10d: float
    volatility_20d: float
    volatility_ratio: float  # current vs historical
    
    # Volume features
    volume_trend: float
    volume_spike: float
    
    # Market structure
    higher_highs: int  # count in lookback
    higher_lows: int
    support_resistance_strength: float
    
    # Cross-market
    spy_correlation: float
    sector_divergence: float

@dataclass
class RegimeClassification:
    """Enhanced regime classification output"""
    primary_regime: str  # BULL_TREND, BEAR_TREND, BULL_VOLATILE, BEAR_VOLATILE, SIDEWAYS
    confidence: float   # 0-1 scale
    volatility_regime: str  # LOW, NORMAL, HIGH, EXTREME
    trend_strength: float  # -1 to 1
    market_stress: float   # 0-1 scale
    regime_stability: float  # how stable is this regime
    transition_probability: float  # likelihood of regime change
    
    # Sub-regimes
    momentum_regime: str
    volatility_cluster: bool
    support_resistance: str

class EnhancedRegimeDetector:
    """ML-Enhanced Regime Detection with multi-timeframe analysis"""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.base_detector = RegimeDetector(config)  # Use existing detector
        self.regime_history = []
        self.feature_history = []
        
        # Enhanced parameters
        self.lookback_short = 10
        self.lookback_medium = 20
        self.lookback_long = 50
        self.volatility_threshold = 0.02  # 2% daily volatility threshold
        
    def extract_regime_features(self, df: pd.DataFrame) -> RegimeFeatures:
        """Extract comprehensive features for regime classification"""
        try:
            if len(df) < self.lookback_long:
                return self._default_features()
            
            close_prices = df['close'].dropna()
            
            # Trend features
            sma_10 = close_prices.rolling(10).mean()
            sma_20 = close_prices.rolling(20).mean()
            sma_50 = close_prices.rolling(50).mean()
            
            sma_slope_10d = self._calculate_slope(sma_10.tail(10))
            sma_slope_20d = self._calculate_slope(sma_20.tail(20))
            sma_slope_50d = self._calculate_slope(sma_50.tail(50))
            
            current_price = close_prices.iloc[-1]
            price_vs_sma20 = (current_price / sma_20.iloc[-1] - 1) if not pd.isna(sma_20.iloc[-1]) else 0
            price_vs_sma50 = (current_price / sma_50.iloc[-1] - 1) if not pd.isna(sma_50.iloc[-1]) else 0
            
            # Volatility features
            returns = close_prices.pct_change().dropna()
            volatility_10d = returns.tail(10).std() * np.sqrt(252)
            volatility_20d = returns.tail(20).std() * np.sqrt(252)
            volatility_50d = returns.tail(50).std() * np.sqrt(252)
            volatility_ratio = volatility_10d / volatility_50d if volatility_50d > 0 else 1.0
            
            # Volume features (if available)
            volume_trend, volume_spike = self._analyze_volume(df)
            
            # Market structure
            higher_highs, higher_lows = self._count_higher_patterns(close_prices.tail(20))
            support_resistance_strength = self._calculate_sr_strength(close_prices.tail(50))
            
            # Cross-market (simplified for now)
            spy_correlation = 0.7  # Default - can be enhanced with actual SPY data
            sector_divergence = 0.1  # Default - can be enhanced with sector data
            
            return RegimeFeatures(
                sma_slope_10d=sma_slope_10d, sma_slope_20d=sma_slope_20d, sma_slope_50d=sma_slope_50d,
                price_vs_sma20=price_vs_sma20, price_vs_sma50=price_vs_sma50,
                volatility_10d=volatility_10d, volatility_20d=volatility_20d, volatility_ratio=volatility_ratio,
                volume_trend=volume_trend, volume_spike=volume_spike,
                higher_highs=higher_highs, higher_lows=higher_lows, support_resistance_strength=support_resistance_strength,
                spy_correlation=spy_correlation, sector_divergence=sector_divergence
            )
            
        except Exception as e:
            logger.warning(f"Feature extraction failed: {e}")
            return self._default_features()
    
    def _default_features(self) -> RegimeFeatures:
        """Return default features when calculation fails"""
        return RegimeFeatures(
            sma_slope_10d=0.0, sma_slope_20d=0.0, sma_slope_50d=0.0,
            price_vs_sma20=0.0, price_vs_sma50=0.0,
            volatility_10d=0.2, volatility_20d=0.2, volatility_ratio=1.0,
            volume_trend=0.0, volume_spike=1.0,
            higher_highs=0, higher_lows=0, support_resistance_strength=0.5,
            spy_correlation=0.7, sector_divergence=0.1
        )
    
    def _calculate_slope(self, series: pd.Series) -> float:
        """Calculate slope of a price series"""
        try:
            if len(series) < 2:
                return 0.0
            x = np.arange(len(series))
            y = series.values
            slope = np.polyfit(x, y, 1)[0]
            return slope / series.iloc[-1] if series.iloc[-1] != 0 else 0.0  # Normalize by price
        except:
            return 0.0
    
    def _analyze_volume(self, df: pd.DataFrame) -> Tuple[float, float]:
        """Analyze volume patterns"""
        try:
            if 'volume' not in df.columns:
                return 0.0, 1.0
            
            volume = df['volume'].dropna()
            if len(volume) < 20:
                return 0.0, 1.0
            
            # Volume trend (slope of 20-day volume SMA)
            volume_sma = volume.rolling(20).mean()
            volume_trend = self._calculate_slope(volume_sma.tail(20))
            
            # Volume spike (current vs 20-day average)
            avg_volume = volume.tail(20).mean()
            current_volume = volume.iloc[-1]
            volume_spike = current_volume / avg_volume if avg_volume > 0 else 1.0
            
            return volume_trend, volume_spike
            
        except:
            return 0.0, 1.0
    
    def _count_higher_patterns(self, series: pd.Series) -> Tuple[int, int]:
        """Count higher highs and higher lows"""
        try:
            if len(series) < 10:
                return 0, 0
            
            higher_highs = 0
            higher_lows = 0
            
            # Look for local peaks and troughs
            for i in range(2, len(series)-2):
                # Check for local high
                if (series.iloc[i] > series.iloc[i-1] and series.iloc[i] > series.iloc[i+1] and
                    series.iloc[i] > series.iloc[i-2] and series.iloc[i] > series.iloc[i+2]):
                    # Check if it's higher than previous high
                    for j in range(i-1, -1, -1):
                        if (series.iloc[j] > series.iloc[j-1] if j > 0 else False and 
                            series.iloc[j] > series.iloc[j+1] if j < len(series)-1 else False):
                            if series.iloc[i] > series.iloc[j]:
                                higher_highs += 1
                            break
                
                # Check for local low
                if (series.iloc[i] < series.iloc[i-1] and series.iloc[i] < series.iloc[i+1] and
                    series.iloc[i] < series.iloc[i-2] and series.iloc[i] < series.iloc[i+2]):
                    # Check if it's higher than previous low
                    for j in range(i-1, -1, -1):
                        if (series.iloc[j] < series.iloc[j-1] if j > 0 else False and 
                            series.iloc[j] < series.iloc[j+1] if j < len(series)-1 else False):
                            if series.iloc[i] > series.iloc[j]:
                                higher_lows += 1
                            break
            
            return higher_highs, higher_lows
            
        except:
            return 0, 0
    
    def _calculate_sr_strength(self, series: pd.Series) -> float:
        """Calculate support/resistance strength"""
        try:
            if len(series) < 20:
                return 0.5
            
            # Simple implementation: how often price bounces off levels
            price_levels = np.percentile(series, [10, 25, 50, 75, 90])
            touches = 0
            total_opportunities = 0
            
            for level in price_levels:
                tolerance = level * 0.02  # 2% tolerance
                for price in series:
                    if abs(price - level) <= tolerance:
                        touches += 1
                    total_opportunities += 1
            
            strength = touches / total_opportunities if total_opportunities > 0 else 0.5
            return np.clip(strength, 0.0, 1.0)
            
        except:
            return 0.5
    
    def classify_regime(self, features: RegimeFeatures) -> RegimeClassification:
        """Classify market regime using enhanced ML-based rules"""
        
        # Primary regime classification
        primary_regime = self._classify_primary_regime(features)
        confidence = self._calculate_regime_confidence(features, primary_regime)
        
        # Volatility regime
        volatility_regime = self._classify_volatility_regime(features)
        
        # Trend strength (-1 bearish to 1 bullish)
        trend_strength = self._calculate_trend_strength(features)
        
        # Market stress indicator
        market_stress = self._calculate_market_stress(features)
        
        # Regime stability
        regime_stability = self._calculate_stability(features)
        
        # Transition probability
        transition_probability = self._calculate_transition_probability(features)
        
        # Sub-regimes
        momentum_regime = self._classify_momentum_regime(features)
        volatility_cluster = features.volatility_ratio > 1.5
        support_resistance = self._classify_sr_regime(features)
        
        return RegimeClassification(
            primary_regime=primary_regime, confidence=confidence,
            volatility_regime=volatility_regime, trend_strength=trend_strength,
            market_stress=market_stress, regime_stability=regime_stability,
            transition_probability=transition_probability,
            momentum_regime=momentum_regime, volatility_cluster=volatility_cluster,
            support_resistance=support_resistance
        )
    
    def _classify_primary_regime(self, features: RegimeFeatures) -> str:
        """Classify primary market regime"""
        
        # Trend indicators
        trend_score = (features.sma_slope_20d + features.sma_slope_50d) / 2
        price_position = (features.price_vs_sma20 + features.price_vs_sma50) / 2
        
        # Volatility indicators
        vol_high = features.volatility_20d > self.volatility_threshold * 1.5
        
        # Classification logic
        if trend_score > 0.001 and price_position > 0.02:  # Strong uptrend
            return "BULL_TREND" if not vol_high else "BULL_VOLATILE"
        elif trend_score < -0.001 and price_position < -0.02:  # Strong downtrend
            return "BEAR_TREND" if not vol_high else "BEAR_VOLATILE"
        else:
            return "SIDEWAYS"
    
    def _calculate_regime_confidence(self, features: RegimeFeatures, regime: str) -> float:
        """Calculate confidence in regime classification"""
        confidence = 0.5  # Base confidence
        
        # Trend consistency
        trend_consistency = abs(features.sma_slope_10d - features.sma_slope_50d)
        if trend_consistency < 0.001:  # Consistent trend
            confidence += 0.2
        
        # Price position consistency
        price_consistency = abs(features.price_vs_sma20 - features.price_vs_sma50)
        if price_consistency < 0.05:  # Consistent position
            confidence += 0.1
        
        # Volume confirmation
        if features.volume_spike > 1.2 and features.volume_trend > 0:
            confidence += 0.1
        
        # Market structure
        if features.higher_highs > 0 and features.higher_lows > 0 and "BULL" in regime:
            confidence += 0.1
        
        return np.clip(confidence, 0.0, 1.0)
    
    def _classify_volatility_regime(self, features: RegimeFeatures) -> str:
        """Classify volatility regime"""
        vol = features.volatility_20d
        
        if vol < 0.15:
            return "LOW"
        elif vol < 0.25:
            return "NORMAL"  
        elif vol < 0.40:
            return "HIGH"
        else:
            return "EXTREME"
    
    def _calculate_trend_strength(self, features: RegimeFeatures) -> float:
        """Calculate trend strength from -1 (bearish) to 1 (bullish)"""
        trend_components = [
            features.sma_slope_20d * 1000,  # Scale up small slopes
            features.price_vs_sma20 * 2,     # Price vs moving average
            (features.higher_highs - features.higher_lows) * 0.1  # Market structure
        ]
        
        trend_strength = np.mean(trend_components)
        return np.clip(trend_strength, -1.0, 1.0)
    
    def _calculate_market_stress(self, features: RegimeFeatures) -> float:
        """Calculate market stress indicator"""
        stress_factors = [
            features.volatility_ratio - 1.0,  # Volatility spike
            abs(features.sector_divergence),   # Sector divergence
            1.0 - features.support_resistance_strength  # Weak S/R
        ]
        
        stress = np.mean([max(0, factor) for factor in stress_factors])
        return np.clip(stress, 0.0, 1.0)
    
    def _calculate_stability(self, features: RegimeFeatures) -> float:
        """Calculate regime stability"""
        stability_factors = [
            1.0 - abs(features.volatility_ratio - 1.0),  # Stable volatility
            features.support_resistance_strength,        # Strong S/R
            1.0 - abs(features.sma_slope_10d - features.sma_slope_50d) * 1000  # Consistent trends
        ]
        
        stability = np.mean([max(0, factor) for factor in stability_factors])
        return np.clip(stability, 0.0, 1.0)
    
    def _calculate_transition_probability(self, features: RegimeFeatures) -> float:
        """Calculate probability of regime transition"""
        transition_signals = [
            abs(features.sma_slope_10d - features.sma_slope_50d) * 1000,  # Diverging trends
            features.volatility_ratio - 1.0,  # Volatility spike
            abs(features.sector_divergence)   # Market divergence
        ]
        
        transition_prob = np.mean([max(0, signal) for signal in transition_signals])
        return np.clip(transition_prob, 0.0, 1.0)
    
    def _classify_momentum_regime(self, features: RegimeFeatures) -> str:
        """Classify momentum regime"""
        momentum_score = features.sma_slope_10d * 1000
        
        if momentum_score > 2:
            return "STRONG_MOMENTUM"
        elif momentum_score > 0.5:
            return "MOMENTUM" 
        elif momentum_score > -0.5:
            return "NEUTRAL"
        elif momentum_score > -2:
            return "WEAK"
        else:
            return "DECLINING"
    
    def _classify_sr_regime(self, features: RegimeFeatures) -> str:
        """Classify support/resistance regime"""
        sr_strength = features.support_resistance_strength
        
        if sr_strength > 0.7:
            return "STRONG_LEVELS"
        elif sr_strength > 0.4:
            return "MODERATE_LEVELS"
        else:
            return "WEAK_LEVELS"
    
    def detect_enhanced_regime(self, df: pd.DataFrame, symbol: str = "UNKNOWN") -> RegimeClassification:
        """Main method: Detect enhanced regime for given data"""
        try:
            # Extract features
            features = self.extract_regime_features(df)
            
            # Classify regime
            classification = self.classify_regime(features)
            
            # Store history
            self.regime_history.append({
                'timestamp': datetime.now(),
                'symbol': symbol,
                'classification': classification,
                'features': features
            })
            
            # Log results
            logger.info(f"{symbol}: Regime={classification.primary_regime}, "
                       f"Confidence={classification.confidence:.3f}, "
                       f"TrendStrength={classification.trend_strength:.3f}")
            
            return classification
            
        except Exception as e:
            logger.error(f"Enhanced regime detection failed for {symbol}: {e}")
            # Return default classification
            return RegimeClassification(
                primary_regime="SIDEWAYS", confidence=0.5,
                volatility_regime="NORMAL", trend_strength=0.0,
                market_stress=0.5, regime_stability=0.5,
                transition_probability=0.5,
                momentum_regime="NEUTRAL", volatility_cluster=False,
                support_resistance="MODERATE_LEVELS"
            )

if __name__ == "__main__":
    print("Testing Enhanced Regime Detector...")
    
    # Create sample data for testing
    dates = pd.date_range(start='2024-01-01', end='2024-12-31', freq='D')
    np.random.seed(42)
    
    # Simulate bullish trend with volatility
    price = 100
    prices = []
    volumes = []
    
    for i in range(len(dates)):
        # Add trend + noise
        trend = 0.0008  # Slight uptrend
        noise = np.random.normal(0, 0.02)
        price *= (1 + trend + noise)
        prices.append(price)
        volumes.append(np.random.randint(1000000, 5000000))
    
    test_data = pd.DataFrame({
        'date': dates,
        'close': prices,
        'high': [p * 1.01 for p in prices],
        'low': [p * 0.99 for p in prices],
        'volume': volumes
    })
    
    # Test enhanced regime detector
    detector = EnhancedRegimeDetector()
    classification = detector.detect_enhanced_regime(test_data, "TEST")
    
    print(f"Primary Regime: {classification.primary_regime}")
    print(f"Confidence: {classification.confidence:.3f}")
    print(f"Volatility Regime: {classification.volatility_regime}")
    print(f"Trend Strength: {classification.trend_strength:.3f}")
    print(f"Market Stress: {classification.market_stress:.3f}")
    print(f"Regime Stability: {classification.regime_stability:.3f}")
    print("Enhanced Regime Detector ready!")

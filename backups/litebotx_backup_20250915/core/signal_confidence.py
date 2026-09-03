"""
Signal Confidence Scoring Module
Purpose: ML-enhanced confidence scoring for momentum signals
Phase 3A Enhancement - Immediate Implementation
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger("LiteBot")

@dataclass
class SignalFeatures:
    """Feature set for signal confidence scoring"""
    momentum_21d: float
    momentum_42d: float
    sector_momentum: float
    volatility_21d: float
    volume_ratio: float
    price_vs_52w_high: float
    rsi_14d: float
    regime_score: float
    correlation_to_spy: float

@dataclass
class ConfidenceScore:
    """Output confidence score with breakdown"""
    overall_confidence: float  # 0-1 scale
    momentum_strength: float
    regime_alignment: float
    technical_quality: float
    risk_assessment: float
    recommendation: str

class SignalConfidenceScorer:
    """ML-enhanced signal confidence scoring"""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.feature_history = []
        self.performance_history = []
        
    def extract_features(self, stock_data: pd.DataFrame, 
                        sector_momentum: float, regime_score: float) -> SignalFeatures:
        """Extract features for confidence scoring"""
        try:
            if len(stock_data) < 22:
                return self._default_features(sector_momentum, regime_score)
            
            # Basic momentum
            returns_21d = (stock_data['close'].iloc[-1] / stock_data['close'].iloc[-22] - 1)
            returns_42d = (stock_data['close'].iloc[-1] / stock_data['close'].iloc[-43] - 1) if len(stock_data) >= 43 else returns_21d
            
            # Volatility
            volatility_21d = stock_data['close'].pct_change().rolling(21).std().iloc[-1] * np.sqrt(252)
            if pd.isna(volatility_21d):
                volatility_21d = 0.2
                
            # Volume
            if 'volume' in stock_data.columns:
                avg_volume = stock_data['volume'].rolling(21).mean().iloc[-1]
                volume_ratio = stock_data['volume'].iloc[-1] / avg_volume if avg_volume > 0 else 1.0
            else:
                volume_ratio = 1.0
            
            # Price position
            high_52w = stock_data['high'].rolling(252).max().iloc[-1] if len(stock_data) >= 252 else stock_data['high'].max()
            price_vs_52w_high = stock_data['close'].iloc[-1] / high_52w if high_52w > 0 else 1.0
            
            # RSI
            rsi_14d = self._calculate_rsi(stock_data['close'], 14)
            
            return SignalFeatures(
                momentum_21d=returns_21d, momentum_42d=returns_42d,
                sector_momentum=sector_momentum, volatility_21d=volatility_21d,
                volume_ratio=volume_ratio, price_vs_52w_high=price_vs_52w_high,
                rsi_14d=rsi_14d, regime_score=regime_score, correlation_to_spy=0.5
            )
            
        except Exception as e:
            logger.warning(f"Feature extraction failed: {e}")
            return self._default_features(sector_momentum, regime_score)
    
    def _default_features(self, sector_momentum: float, regime_score: float) -> SignalFeatures:
        return SignalFeatures(
            momentum_21d=0.0, momentum_42d=0.0, sector_momentum=sector_momentum,
            volatility_21d=0.2, volume_ratio=1.0, price_vs_52w_high=0.8,
            rsi_14d=50.0, regime_score=regime_score, correlation_to_spy=0.5
        )
    
    def _calculate_rsi(self, prices: pd.Series, window: int = 14) -> float:
        try:
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50.0
        except:
            return 50.0
    
    def calculate_confidence(self, features: SignalFeatures) -> ConfidenceScore:
        """Calculate confidence score for a signal"""
        momentum_conf = self._rule_based_momentum_score(features)
        regime_conf = self._rule_based_regime_score(features)
        technical_conf = self._rule_based_technical_score(features)
        risk_score = self._calculate_risk_score(features)
        
        overall_confidence = (
            0.4 * momentum_conf + 0.25 * regime_conf + 
            0.25 * technical_conf + 0.1 * risk_score
        )
        
        recommendation = self._generate_recommendation(overall_confidence, features)
        
        return ConfidenceScore(
            overall_confidence=np.clip(overall_confidence, 0.0, 1.0),
            momentum_strength=momentum_conf, regime_alignment=regime_conf,
            technical_quality=technical_conf, risk_assessment=risk_score,
            recommendation=recommendation
        )
    
    def _rule_based_momentum_score(self, features: SignalFeatures) -> float:
        score = 0.0
        if features.momentum_21d > 0.05: score += 0.25
        elif features.momentum_21d > 0.02: score += 0.15
        elif features.momentum_21d > 0: score += 0.05
        
        if features.momentum_42d > 0.10: score += 0.35
        elif features.momentum_42d > 0.05: score += 0.25
        elif features.momentum_42d > 0: score += 0.10
        
        if features.sector_momentum > 0.02: score += 0.20
        elif features.sector_momentum > 0: score += 0.10
        
        if features.volume_ratio > 1.5: score += 0.15
        elif features.volume_ratio > 1.0: score += 0.05
        
        return np.clip(score, 0.0, 1.0)
    
    def _rule_based_regime_score(self, features: SignalFeatures) -> float:
        score = 0.5
        if features.regime_score > 0.5: score += 0.3
        elif features.regime_score > 0: score += 0.1
        elif features.regime_score < -0.3: score -= 0.2
        
        if features.price_vs_52w_high > 0.8: score += 0.2
        elif features.price_vs_52w_high > 0.6: score += 0.1
        elif features.price_vs_52w_high < 0.3: score -= 0.1
        
        return np.clip(score, 0.0, 1.0)
    
    def _rule_based_technical_score(self, features: SignalFeatures) -> float:
        score = 0.5
        if 40 <= features.rsi_14d <= 70: score += 0.2
        elif 30 <= features.rsi_14d <= 80: score += 0.1
        elif features.rsi_14d > 80: score -= 0.1
        elif features.rsi_14d < 20: score -= 0.1
        
        if features.volume_ratio > 2.0: score += 0.2
        elif features.volume_ratio > 1.5: score += 0.15
        elif features.volume_ratio > 1.0: score += 0.05
        elif features.volume_ratio < 0.5: score -= 0.1
        
        return np.clip(score, 0.0, 1.0)
    
    def _calculate_risk_score(self, features: SignalFeatures) -> float:
        risk_score = 1.0
        if features.volatility_21d > 0.5: risk_score -= 0.4
        elif features.volatility_21d > 0.4: risk_score -= 0.2
        elif features.volatility_21d > 0.3: risk_score -= 0.1
        
        if abs(features.correlation_to_spy) > 0.9: risk_score -= 0.2
        elif abs(features.correlation_to_spy) > 0.8: risk_score -= 0.1
        
        return np.clip(risk_score, 0.0, 1.0)
    
    def _generate_recommendation(self, confidence: float, features: SignalFeatures) -> str:
        if (confidence >= 0.8 and features.momentum_21d > 0.02 and 
            features.momentum_42d > 0.05 and features.sector_momentum > 0):
            return "STRONG_BUY"
        elif (confidence >= 0.6 and features.momentum_21d > 0.0 and 
              features.momentum_42d > 0.0):
            return "BUY"
        elif confidence >= 0.4:
            return "HOLD"
        else:
            return "WEAK"

if __name__ == "__main__":
    print("Testing Signal Confidence Scorer...")
    scorer = SignalConfidenceScorer()
    
    # Test with sample data
    test_features = SignalFeatures(
        momentum_21d=0.08, momentum_42d=0.15, sector_momentum=0.05,
        volatility_21d=0.25, volume_ratio=1.8, price_vs_52w_high=0.85,
        rsi_14d=65.0, regime_score=0.7, correlation_to_spy=0.6
    )
    
    confidence = scorer.calculate_confidence(test_features)
    print(f"Overall Confidence: {confidence.overall_confidence:.3f}")
    print(f"Recommendation: {confidence.recommendation}")
    print("Signal Confidence Scorer ready!")

"""
Multi-Timeframe Analyzer - Phase 3A Enhancement
Analyze multiple timeframes for enhanced regime detection
"""

import pandas as pd
import numpy as np
from typing import Dict, List
from dataclasses import dataclass
import logging

logger = logging.getLogger("LiteBot")

@dataclass
class TimeframeAnalysis:
    """Results for a specific timeframe"""
    timeframe: str
    regime: str
    confidence: float
    trend_strength: float
    volatility: float
    momentum: float

class MultiTimeframeAnalyzer:
    """Analyze multiple timeframes for enhanced decision making"""
    
    def __init__(self):
        self.timeframes = {
            'daily': 1,
            'weekly': 5, 
            'monthly': 22
        }
        
    def analyze_all_timeframes(self, data: pd.DataFrame, 
                             regime_detector, confidence_scorer) -> Dict[str, TimeframeAnalysis]:
        """Analyze all timeframes and return comprehensive view"""
        
        results = {}
        
        for tf_name, days in self.timeframes.items():
            try:
                # Resample data for timeframe
                tf_data = self._resample_data(data, days)
                
                if len(tf_data) < 50:  # Need minimum data
                    continue
                
                # Run regime detection
                regime = regime_detector.detect_regime(tf_data)
                regime_score = 0.8 if regime == 'bullish' else (0.7 if regime == 'volatile' else 0.3)
                
                # Calculate features
                features = confidence_scorer.extract_features(tf_data, 0.02, regime_score)
                confidence = confidence_scorer.calculate_confidence(features)
                
                # Create analysis
                analysis = TimeframeAnalysis(
                    timeframe=tf_name,
                    regime=regime,
                    confidence=confidence.overall_confidence,
                    trend_strength=confidence.momentum_strength,
                    volatility=features.volatility_21d,
                    momentum=features.momentum_21d
                )
                
                results[tf_name] = analysis
                
                logger.info(f"{tf_name.upper()}: {regime} regime, "
                           f"{confidence.overall_confidence:.1%} confidence")
                
            except Exception as e:
                logger.warning(f"Failed to analyze {tf_name} timeframe: {e}")
                continue
                
        return results
    
    def _resample_data(self, data: pd.DataFrame, days: int) -> pd.DataFrame:
        """Resample data to specified timeframe"""
        if days == 1:
            return data  # Daily data as-is
        
        # Group by periods and aggregate
        resampled = data.groupby(data.index // days).agg({
            'close': 'last',
            'high': 'max',
            'low': 'min', 
            'volume': 'sum'
        })
        
        return resampled
    
    def get_consensus_signal(self, analyses: Dict[str, TimeframeAnalysis]) -> Dict:
        """Get consensus signal across all timeframes"""
        
        if not analyses:
            return {'signal': 'HOLD', 'confidence': 0.5, 'reason': 'No data'}
        
        # Weight timeframes (longer = more weight)
        weights = {'daily': 0.3, 'weekly': 0.4, 'monthly': 0.3}
        
        weighted_confidence = 0
        bullish_signals = 0
        bearish_signals = 0
        total_weight = 0
        
        for tf_name, analysis in analyses.items():
            weight = weights.get(tf_name, 0.33)
            weighted_confidence += analysis.confidence * weight
            total_weight += weight
            
            if analysis.regime in ['bullish'] or analysis.momentum > 0.02:
                bullish_signals += weight
            elif analysis.regime in ['bearish'] or analysis.momentum < -0.02:
                bearish_signals += weight
        
        if total_weight > 0:
            weighted_confidence /= total_weight
        
        # Determine consensus
        if bullish_signals > bearish_signals * 1.5:
            signal = 'BUY'
        elif bearish_signals > bullish_signals * 1.5:
            signal = 'SELL'
        else:
            signal = 'HOLD'
        
        return {
            'signal': signal,
            'confidence': weighted_confidence,
            'bullish_weight': bullish_signals,
            'bearish_weight': bearish_signals,
            'timeframe_count': len(analyses)
        }

if __name__ == "__main__":
    print("Multi-Timeframe Analyzer ready!")
    print("Enhances regime detection with multiple time horizons")

"""
Smart Threshold Strategy - Cascading Filter Approach
Implements the user's strategic insight: wide early screening with progressively tighter thresholds
"""

import logging
from typing import Dict, List, Any, Optional
import numpy as np
import pandas as pd

from .phase3a_enhanced_strategy import Phase3AEnhancedStrategy

logger = logging.getLogger(__name__)

class SmartThresholdStrategy(Phase3AEnhancedStrategy):
    """
    Smart cascading threshold strategy that maximizes candidate pool while maintaining quality
    
    Levels:
    1. Screening: Wide criteria to catch all potential candidates
    2. Basic Quality: Moderate filtering for basic requirements  
    3. Enhanced Filter: Stricter selection for quality signals
    4. Final Selection: Tightest criteria for best signals only
    """
    
    def __init__(self, alpha_vantage_key: str, min_confidence: float = 0.6, **kwargs):
        super().__init__(alpha_vantage_key, min_confidence, **kwargs)
        
        # Cascading threshold levels - each level gets progressively stricter
        self.thresholds = {
            # Level 1: Initial Screening (WIDE - catch candidates)
            'screening': {
                'min_data_points': 50,          # Basic data requirement
                'min_momentum_21d': -0.05,      # Even small declines allowed initially
                'min_volume_ratio': 0.3,        # Very low volume filter
                'max_volatility': 1.0           # Very permissive volatility
            },
            
            # Level 2: Basic Quality (MODERATE - basic quality check)
            'basic_quality': {
                'min_confidence': 0.4,          # Lower than final threshold
                'min_momentum_21d': 0.005,      # Slight positive momentum
                'min_regime_score': 0.3,        # Basic regime alignment
                'max_volatility': 0.6           # Moderate volatility filter
            },
            
            # Level 3: Enhanced Filtering (STRICTER - getting selective)
            'enhanced_filter': {
                'min_confidence': 0.45,         # Higher confidence required
                'min_enhanced_score': 0.4,      # Basic enhanced score
                'min_momentum_21d': 0.01,       # 1% minimum momentum
                'min_regime_score': 0.4,        # Better regime alignment
                'max_volatility': 0.4           # Lower volatility tolerance
            },
            
            # Level 4: Final Selection (TIGHTEST - only the best)
            'final_selection': {
                'min_confidence': 0.65,         # High confidence required
                'min_enhanced_score': 0.6,      # Strong enhanced score
                'min_momentum_21d': 0.02,       # 2% minimum momentum
                'min_regime_score': 0.5,        # Strong regime alignment
                'max_volatility': 0.3,          # Low volatility preferred
                'min_signal_strength': 0.7      # Strong signal required
            }
        }
        
        # Track filtering statistics
        self.filter_stats = {}
        
        logger.info("🎯 Smart Threshold Strategy initialized with cascading filters")
    
    def generate_smart_threshold_signals(self, market_data: Dict[str, pd.DataFrame], 
                                       portfolio_value: float, max_positions: int = 5) -> List[Dict]:
        """Generate signals using smart cascading threshold approach"""
        
        all_candidates = list(market_data.keys())
        self.filter_stats = {
            'initial_candidates': len(all_candidates),
            'after_screening': 0,
            'after_basic_quality': 0,
            'after_enhanced_filter': 0,
            'final_signals': 0
        }
        
        logger.info(f"🔍 Smart Threshold Analysis: {len(all_candidates)} initial candidates")
        
        # Level 1: Screening Filter (WIDE)
        screening_candidates = self._apply_screening_filter(market_data)
        self.filter_stats['after_screening'] = len(screening_candidates)
        logger.info(f"📊 After Screening: {len(screening_candidates)} candidates "
                   f"({len(screening_candidates)/len(all_candidates)*100:.1f}% passed)")
        
        # Level 2: Basic Quality Filter (MODERATE)
        quality_candidates = self._apply_quality_filter(screening_candidates, market_data)
        self.filter_stats['after_basic_quality'] = len(quality_candidates)
        logger.info(f"🔍 After Basic Quality: {len(quality_candidates)} candidates "
                   f"({len(quality_candidates)/len(screening_candidates)*100 if len(screening_candidates) > 0 else 0:.1f}% passed)")
        
        # Level 3: Enhanced Filter (STRICTER)
        enhanced_candidates = self._apply_enhanced_filter(quality_candidates, market_data)
        self.filter_stats['after_enhanced_filter'] = len(enhanced_candidates)
        logger.info(f"⚡ After Enhanced Filter: {len(enhanced_candidates)} candidates "
                   f"({len(enhanced_candidates)/len(quality_candidates)*100 if len(quality_candidates) > 0 else 0:.1f}% passed)")
        
        # Level 4: Final Selection (TIGHTEST)
        final_signals = self._apply_final_selection(enhanced_candidates, market_data, portfolio_value, max_positions)
        self.filter_stats['final_signals'] = len(final_signals)
        logger.info(f"🎯 Final Signals: {len(final_signals)} signals "
                   f"({len(final_signals)/len(enhanced_candidates)*100 if len(enhanced_candidates) > 0 else 0:.1f}% passed)")
        
        return final_signals
    
    def _apply_screening_filter(self, market_data: Dict[str, pd.DataFrame]) -> List[str]:
        """Level 1: Wide screening to catch all potential candidates"""
        candidates = []
        thresholds = self.thresholds['screening']
        
        for symbol, data in market_data.items():
            # Basic data quality check
            if len(data) < thresholds['min_data_points']:
                continue
                
            # Calculate basic metrics
            recent_momentum = (data['close'].iloc[-1] / data['close'].iloc[-22] - 1) if len(data) >= 22 else 0
            avg_volume = data['volume'].mean()
            volatility = data['close'].pct_change().std() * np.sqrt(252)
            
            # Wide screening criteria
            if (recent_momentum >= thresholds['min_momentum_21d'] and
                avg_volume >= thresholds['min_volume_ratio'] * 1000000 and  # Base volume check
                volatility <= thresholds['max_volatility']):
                candidates.append(symbol)
        
        return candidates
    
    def _apply_quality_filter(self, candidates: List[str], market_data: Dict[str, pd.DataFrame]) -> List[str]:
        """Level 2: Basic quality filtering"""
        quality_candidates = []
        thresholds = self.thresholds['basic_quality']
        
        for symbol in candidates:
            data = market_data[symbol]
            
            # Get confidence analysis
            # Extract features for confidence scoring
            features = self.confidence_scorer.extract_features(
                stock_data=data,
                
                sector_momentum=0.05,  # Default sector momentum
                regime_score=0.5       # Default regime score
            )
            
            # Calculate confidence
            confidence_result = self.confidence_scorer.calculate_confidence(features)
            confidence_analysis = {
                'overall_confidence': confidence_result.overall_confidence,
                'regime_alignment': confidence_result.regime_alignment
            }
            
            # Get regime analysis
            regime_result = self.regime_detector.detect_regime(data)
            regime_score = confidence_analysis.get('regime_alignment', 0.5)
            
            # Calculate metrics
            recent_momentum = (data['close'].iloc[-1] / data['close'].iloc[-22] - 1) if len(data) >= 22 else 0
            volatility = data['close'].pct_change().std() * np.sqrt(252)
            
            # Basic quality criteria
            if (confidence_analysis['overall_confidence'] >= thresholds['min_confidence'] and
                recent_momentum >= thresholds['min_momentum_21d'] and
                regime_score >= thresholds['min_regime_score'] and
                volatility <= thresholds['max_volatility']):
                quality_candidates.append(symbol)
        
        return quality_candidates
    
    def _apply_enhanced_filter(self, candidates: List[str], market_data: Dict[str, pd.DataFrame]) -> List[str]:
        """Level 3: Enhanced filtering for higher quality signals"""
        enhanced_candidates = []
        thresholds = self.thresholds['enhanced_filter']
        
        for symbol in candidates:
            data = market_data[symbol]
            
            # Generate enhanced signal
            # Get regime analysis
            regime_result = self.regime_detector.detect_regime(data)
            regime_analysis = {'regime': regime_result}
            
            # Get confidence analysis (already calculated above)
            confidence_dict = {
                'overall_confidence': confidence_analysis['overall_confidence'],
                'regime_alignment': confidence_analysis['regime_alignment']
            }
            
            enhanced_signal = self._generate_enhanced_signal(
                symbol, data, regime_analysis, confidence_dict, 1000000)
            
            if enhanced_signal:
                # Enhanced criteria
                recent_momentum = (data['close'].iloc[-1] / data['close'].iloc[-22] - 1) if len(data) >= 22 else 0
                volatility = data['close'].pct_change().std() * np.sqrt(252)
                
                if (enhanced_signal['confidence'] >= thresholds['min_confidence'] and
                    enhanced_signal.get('enhanced_score', 0) >= thresholds['min_enhanced_score'] and
                    recent_momentum >= thresholds['min_momentum_21d'] and
                    volatility <= thresholds['max_volatility']):
                    enhanced_candidates.append(symbol)
        
        return enhanced_candidates
    
    def _apply_final_selection(self, candidates: List[str], market_data: Dict[str, pd.DataFrame], 
                             portfolio_value: float, max_positions: int) -> List[Dict]:
        """Level 4: Final selection with tightest criteria"""
        final_signals = []
        thresholds = self.thresholds['final_selection']
        
        for symbol in candidates:
            data = market_data[symbol]
            
            # Generate enhanced signal with full analysis
            # Get regime analysis
            regime_result = self.regime_detector.detect_regime(data)
            regime_analysis = {'regime': regime_result}
            
            # Get confidence analysis
            features = self.confidence_scorer.extract_features(
                stock_data=data,
                sector_momentum=0.05,
                regime_score=0.5
            )
            confidence_result = self.confidence_scorer.calculate_confidence(features)
            confidence_dict = {
                'overall_confidence': confidence_result.overall_confidence,
                'regime_alignment': confidence_result.regime_alignment
            }
            
            enhanced_signal = self._generate_enhanced_signal(
                symbol, data, regime_analysis, confidence_dict, portfolio_value)
            
            if enhanced_signal:
                # Final selection criteria (tightest)
                recent_momentum = (data['close'].iloc[-1] / data['close'].iloc[-22] - 1) if len(data) >= 22 else 0
                volatility = data['close'].pct_change().std() * np.sqrt(252)
                
                if (enhanced_signal['confidence'] >= thresholds['min_confidence'] and
                    enhanced_signal.get('enhanced_score', 0) >= thresholds['min_enhanced_score'] and
                    recent_momentum >= thresholds['min_momentum_21d'] and
                    volatility <= thresholds['max_volatility']):
                    
                    # Add filtering metadata
                    enhanced_signal['filter_path'] = 'screening→quality→enhanced→final'
                    enhanced_signal['momentum_21d'] = recent_momentum
                    enhanced_signal['volatility'] = volatility
                    
                    final_signals.append(enhanced_signal)
        
        # Sort by confidence and limit to max positions
        final_signals.sort(key=lambda x: x['confidence'], reverse=True)
        return final_signals[:max_positions]
    
    def get_threshold_analysis(self) -> Dict[str, Any]:
        """Get analysis of threshold filtering effectiveness"""
        
        stats = self.filter_stats
        
        # Calculate efficiency metrics
        efficiency_metrics = {}
        if stats['initial_candidates'] > 0:
            efficiency_metrics['screening_efficiency'] = (stats['after_screening'] / stats['initial_candidates']) * 100
        if stats['after_screening'] > 0:
            efficiency_metrics['quality_efficiency'] = (stats['after_basic_quality'] / stats['after_screening']) * 100
        if stats['after_basic_quality'] > 0:
            efficiency_metrics['enhanced_efficiency'] = (stats['after_enhanced_filter'] / stats['after_basic_quality']) * 100
        if stats['after_enhanced_filter'] > 0:
            efficiency_metrics['final_efficiency'] = (stats['final_signals'] / stats['after_enhanced_filter']) * 100
        if stats['initial_candidates'] > 0:
            efficiency_metrics['overall_efficiency'] = (stats['final_signals'] / stats['initial_candidates']) * 100
        
        return {
            'filter_stats': stats,
            'efficiency_metrics': efficiency_metrics,
            'threshold_levels': len(self.thresholds),
            'strategy_type': 'cascading_smart_thresholds'
        }

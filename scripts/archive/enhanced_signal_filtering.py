#!/usr/bin/env python3
"""
Enhanced Signal Filtering Implementation
Implements statistical signal filtering (Option 1C) for Signal Quality Improvement Plan
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone
import logging
from pathlib import Path
import json

# Import base signal generator
from signal_generator import SignalGenerator

class EnhancedSignalFilter:
    """
    Enhanced statistical signal filtering system
    
    Implements:
    - Volume validation with statistical thresholds
    - Price momentum confirmation using multiple timeframes
    - Market condition filters (volatility, trend strength)
    - Signal quality scoring with statistical confidence
    """
    
    def __init__(self, config=None):
        self.config = config or self._get_default_config()
        self.signal_history = []
        self.filter_stats = {
            'total_signals': 0,
            'filtered_signals': 0,
            'volume_filtered': 0,
            'momentum_filtered': 0,
            'volatility_filtered': 0,
            'quality_filtered': 0
        }
        
        logging.info("🔍 Enhanced Signal Filter initialized")
    
    def _get_default_config(self):
        """Default configuration for signal filtering"""
        return {
            'volume_filter': {
                'enabled': True,
                'min_volume_ratio': 1.2,  # Minimum 20% above average
                'volume_lookback': 20,
                'volume_percentile_threshold': 60  # Must be above 60th percentile
            },
            'momentum_filter': {
                'enabled': True,
                'min_momentum_5d': 0.02,   # Minimum 2% momentum over 5 days
                'min_momentum_20d': 0.05,  # Minimum 5% momentum over 20 days
                'momentum_consistency': True,  # Require consistent direction
                'momentum_acceleration': True  # Prefer accelerating momentum
            },
            'volatility_filter': {
                'enabled': True,
                'max_volatility_ratio': 2.0,  # Max 2x normal volatility
                'min_volatility_ratio': 0.5,  # Min 0.5x normal volatility
                'volatility_lookback': 20
            },
            'quality_filter': {
                'enabled': True,
                'min_signal_confidence': 0.6,  # Minimum 60% confidence
                'require_multiple_confirmations': True,  # Need multiple indicators
                'max_conflicting_signals': 1  # Max 1 conflicting signal
            },
            'statistical_thresholds': {
                'price_z_score_max': 3.0,     # Max 3 standard deviations
                'volume_z_score_min': 1.0,    # Min 1 standard deviation above mean
                'momentum_percentile_min': 70  # Top 30% of momentum readings
            }
        }
    
    def apply_enhanced_filtering(self, signal: Dict, price_data: pd.DataFrame, 
                               volume_data: Optional[pd.DataFrame] = None) -> Dict:
        """
        Apply comprehensive signal filtering
        
        Args:
            signal: Original signal from signal generator
            price_data: Price/volume DataFrame
            volume_data: Optional additional volume data
            
        Returns:
            Enhanced signal with filtering results
        """
        self.filter_stats['total_signals'] += 1
        
        # Skip filtering for hold signals
        if signal.get('signal') == 'hold':
            return signal
        
        # Initialize filter results
        filter_results = {
            'volume_filter': True,
            'momentum_filter': True,
            'volatility_filter': True,
            'quality_filter': True,
            'statistical_filter': True
        }
        
        filter_details = {}
        
        # 1. Volume Validation Filter
        if self.config['volume_filter']['enabled']:
            volume_result = self._apply_volume_filter(price_data)
            filter_results['volume_filter'] = volume_result['passed']
            filter_details['volume'] = volume_result
            
            if not volume_result['passed']:
                self.filter_stats['volume_filtered'] += 1
        
        # 2. Price Momentum Filter  
        if self.config['momentum_filter']['enabled']:
            momentum_result = self._apply_momentum_filter(price_data)
            filter_results['momentum_filter'] = momentum_result['passed']
            filter_details['momentum'] = momentum_result
            
            if not momentum_result['passed']:
                self.filter_stats['momentum_filtered'] += 1
        
        # 3. Market Condition (Volatility) Filter
        if self.config['volatility_filter']['enabled']:
            volatility_result = self._apply_volatility_filter(price_data)
            filter_results['volatility_filter'] = volatility_result['passed']
            filter_details['volatility'] = volatility_result
            
            if not volatility_result['passed']:
                self.filter_stats['volatility_filtered'] += 1
        
        # 4. Signal Quality Filter
        if self.config['quality_filter']['enabled']:
            quality_result = self._apply_quality_filter(signal, filter_details)
            filter_results['quality_filter'] = quality_result['passed']
            filter_details['quality'] = quality_result
            
            if not quality_result['passed']:
                self.filter_stats['quality_filtered'] += 1
        
        # 5. Statistical Confidence Filter
        statistical_result = self._apply_statistical_filter(price_data, signal)
        filter_results['statistical_filter'] = statistical_result['passed']
        filter_details['statistical'] = statistical_result
        
        # Determine if signal passes all filters
        all_filters_passed = all(filter_results.values())
        
        if not all_filters_passed:
            self.filter_stats['filtered_signals'] += 1
        
        # Create enhanced signal
        enhanced_signal = signal.copy()
        enhanced_signal.update({
            'filtered': not all_filters_passed,
            'filter_results': filter_results,
            'filter_details': filter_details,
            'original_confidence': signal.get('confidence', 0.0),
            'enhanced_confidence': self._calculate_enhanced_confidence(signal, filter_details, all_filters_passed)
        })
        
        # Override signal if filtered
        if not all_filters_passed:
            enhanced_signal['signal'] = 'hold'
            enhanced_signal['reason'] = f"filtered: {self._get_filter_failure_reason(filter_results)}"
        
        return enhanced_signal
    
    def _apply_volume_filter(self, price_data: pd.DataFrame) -> Dict:
        """Apply volume-based signal filtering"""
        try:
            volume = price_data['volume']
            lookback = self.config['volume_filter']['volume_lookback']
            
            if len(volume) < lookback:
                return {'passed': True, 'reason': 'insufficient_data'}
            
            # Calculate volume statistics
            current_volume = volume.iloc[-1]
            avg_volume = volume.rolling(lookback).mean().iloc[-1]
            volume_std = volume.rolling(lookback).std().iloc[-1]
            
            # Volume ratio test
            volume_ratio = current_volume / avg_volume
            min_ratio = self.config['volume_filter']['min_volume_ratio']
            
            # Volume percentile test
            volume_percentile = (volume.iloc[-lookback:] <= current_volume).mean() * 100
            min_percentile = self.config['volume_filter']['volume_percentile_threshold']
            
            # Volume Z-score
            volume_z_score = (current_volume - avg_volume) / volume_std if volume_std > 0 else 0
            
            # Pass conditions
            ratio_passed = volume_ratio >= min_ratio
            percentile_passed = volume_percentile >= min_percentile
            
            passed = ratio_passed and percentile_passed
            
            return {
                'passed': passed,
                'volume_ratio': volume_ratio,
                'volume_percentile': volume_percentile,
                'volume_z_score': volume_z_score,
                'current_volume': current_volume,
                'avg_volume': avg_volume,
                'reason': 'volume_validated' if passed else 'insufficient_volume'
            }
            
        except Exception as e:
            logging.warning(f"Volume filter error: {e}")
            return {'passed': True, 'reason': 'filter_error'}
    
    def _apply_momentum_filter(self, price_data: pd.DataFrame) -> Dict:
        """Apply price momentum filtering"""
        try:
            close = price_data['close']
            
            if len(close) < 21:
                return {'passed': True, 'reason': 'insufficient_data'}
            
            # Calculate momentum over different periods
            momentum_5d = (close.iloc[-1] / close.iloc[-6] - 1) if len(close) >= 6 else 0
            momentum_20d = (close.iloc[-1] / close.iloc[-21] - 1) if len(close) >= 21 else 0
            
            # Momentum acceleration (recent vs older momentum)
            momentum_recent = (close.iloc[-1] / close.iloc[-3] - 1) if len(close) >= 3 else 0
            momentum_older = (close.iloc[-6] / close.iloc[-11] - 1) if len(close) >= 11 else 0
            
            # Consistency check (direction alignment)
            momentum_consistent = (momentum_5d > 0) == (momentum_20d > 0)
            
            # Acceleration check  
            momentum_accelerating = abs(momentum_recent) > abs(momentum_older)
            
            # Apply thresholds
            min_5d = self.config['momentum_filter']['min_momentum_5d']
            min_20d = self.config['momentum_filter']['min_momentum_20d']
            
            momentum_5d_passed = abs(momentum_5d) >= min_5d
            momentum_20d_passed = abs(momentum_20d) >= min_20d
            
            # Overall momentum score
            momentum_score = (abs(momentum_5d) + abs(momentum_20d)) / 2
            
            # Pass conditions
            conditions = []
            if self.config['momentum_filter']['momentum_consistency']:
                conditions.append(momentum_consistent)
            if self.config['momentum_filter']['momentum_acceleration']:
                conditions.append(momentum_accelerating)
            
            conditions.extend([momentum_5d_passed, momentum_20d_passed])
            passed = all(conditions)
            
            return {
                'passed': passed,
                'momentum_5d': momentum_5d,
                'momentum_20d': momentum_20d,
                'momentum_score': momentum_score,
                'momentum_consistent': momentum_consistent,
                'momentum_accelerating': momentum_accelerating,
                'reason': 'momentum_validated' if passed else 'insufficient_momentum'
            }
            
        except Exception as e:
            logging.warning(f"Momentum filter error: {e}")
            return {'passed': True, 'reason': 'filter_error'}
    
    def _apply_volatility_filter(self, price_data: pd.DataFrame) -> Dict:
        """Apply market condition volatility filtering"""
        try:
            close = price_data['close']
            lookback = self.config['volatility_filter']['volatility_lookback']
            
            if len(close) < lookback + 1:
                return {'passed': True, 'reason': 'insufficient_data'}
            
            # Calculate returns and volatility
            returns = close.pct_change().dropna()
            current_volatility = returns.rolling(5).std().iloc[-1]  # 5-day volatility
            avg_volatility = returns.rolling(lookback).std().mean()
            
            # Volatility ratio
            volatility_ratio = current_volatility / avg_volatility if avg_volatility > 0 else 1.0
            
            # Check thresholds
            max_ratio = self.config['volatility_filter']['max_volatility_ratio']
            min_ratio = self.config['volatility_filter']['min_volatility_ratio']
            
            volatility_acceptable = min_ratio <= volatility_ratio <= max_ratio
            
            return {
                'passed': volatility_acceptable,
                'volatility_ratio': volatility_ratio,
                'current_volatility': current_volatility,
                'avg_volatility': avg_volatility,
                'reason': 'volatility_acceptable' if volatility_acceptable else 'volatility_extreme'
            }
            
        except Exception as e:
            logging.warning(f"Volatility filter error: {e}")
            return {'passed': True, 'reason': 'filter_error'}
    
    def _apply_quality_filter(self, signal: Dict, filter_details: Dict) -> Dict:
        """Apply signal quality filtering"""
        try:
            original_confidence = signal.get('confidence', 0.0)
            min_confidence = self.config['quality_filter']['min_signal_confidence']
            
            # Count confirmations from other filters
            confirmations = sum([
                filter_details.get('volume', {}).get('passed', False),
                filter_details.get('momentum', {}).get('passed', False),
                filter_details.get('volatility', {}).get('passed', False)
            ])
            
            # Check for conflicting signals in strategy details
            strategies = signal.get('strategies', {})
            conflicting_count = 0
            signal_direction = signal.get('signal', 'hold')
            
            for strategy, strategy_signal in strategies.items():
                if isinstance(strategy_signal, dict):
                    strategy_direction = strategy_signal.get('signal', 'hold')
                    if strategy_direction != 'hold' and strategy_direction != signal_direction:
                        conflicting_count += 1
            
            max_conflicts = self.config['quality_filter']['max_conflicting_signals']
            
            # Pass conditions
            confidence_passed = original_confidence >= min_confidence
            confirmations_passed = confirmations >= 2 if self.config['quality_filter']['require_multiple_confirmations'] else True
            conflicts_passed = conflicting_count <= max_conflicts
            
            passed = confidence_passed and confirmations_passed and conflicts_passed
            
            return {
                'passed': passed,
                'original_confidence': original_confidence,
                'confirmations': confirmations,
                'conflicting_signals': conflicting_count,
                'reason': 'quality_validated' if passed else 'quality_insufficient'
            }
            
        except Exception as e:
            logging.warning(f"Quality filter error: {e}")
            return {'passed': True, 'reason': 'filter_error'}
    
    def _apply_statistical_filter(self, price_data: pd.DataFrame, signal: Dict) -> Dict:
        """Apply statistical confidence filtering"""
        try:
            close = price_data['close']
            volume = price_data['volume']
            
            if len(close) < 21:
                return {'passed': True, 'reason': 'insufficient_data'}
            
            # Price Z-score (deviation from mean)
            price_mean = close.rolling(20).mean().iloc[-1]
            price_std = close.rolling(20).std().iloc[-1]
            price_z_score = abs((close.iloc[-1] - price_mean) / price_std) if price_std > 0 else 0
            
            # Volume Z-score
            volume_mean = volume.rolling(20).mean().iloc[-1]
            volume_std = volume.rolling(20).std().iloc[-1]
            volume_z_score = (volume.iloc[-1] - volume_mean) / volume_std if volume_std > 0 else 0
            
            # Momentum percentile
            returns = close.pct_change()
            recent_momentum = returns.rolling(5).mean().iloc[-1]
            momentum_percentile = (returns.rolling(20).mean().iloc[-20:] <= recent_momentum).mean() * 100
            
            # Apply statistical thresholds
            thresholds = self.config['statistical_thresholds']
            
            price_z_acceptable = price_z_score <= thresholds['price_z_score_max']
            volume_z_acceptable = volume_z_score >= thresholds['volume_z_score_min']
            momentum_percentile_acceptable = momentum_percentile >= thresholds['momentum_percentile_min']
            
            passed = price_z_acceptable and volume_z_acceptable and momentum_percentile_acceptable
            
            return {
                'passed': passed,
                'price_z_score': price_z_score,
                'volume_z_score': volume_z_score,
                'momentum_percentile': momentum_percentile,
                'reason': 'statistical_validated' if passed else 'statistical_outlier'
            }
            
        except Exception as e:
            logging.warning(f"Statistical filter error: {e}")
            return {'passed': True, 'reason': 'filter_error'}
    
    def _calculate_enhanced_confidence(self, signal: Dict, filter_details: Dict, passed_filters: bool) -> float:
        """Calculate enhanced confidence score based on filter results"""
        base_confidence = signal.get('confidence', 0.0)
        
        if not passed_filters:
            return 0.0
        
        # Boost confidence based on filter strengths
        confidence_boost = 0.0
        
        # Volume boost
        volume_info = filter_details.get('volume', {})
        if volume_info.get('passed'):
            volume_ratio = volume_info.get('volume_ratio', 1.0)
            confidence_boost += min(0.2, (volume_ratio - 1.0) * 0.5)
        
        # Momentum boost
        momentum_info = filter_details.get('momentum', {})
        if momentum_info.get('passed'):
            momentum_score = momentum_info.get('momentum_score', 0.0)
            confidence_boost += min(0.2, momentum_score * 2.0)
        
        # Quality boost
        quality_info = filter_details.get('quality', {})
        if quality_info.get('passed'):
            confirmations = quality_info.get('confirmations', 0)
            confidence_boost += min(0.1, confirmations * 0.05)
        
        enhanced_confidence = min(1.0, base_confidence + confidence_boost)
        return enhanced_confidence
    
    def _get_filter_failure_reason(self, filter_results: Dict) -> str:
        """Get human-readable reason for filter failure"""
        failed_filters = [name for name, passed in filter_results.items() if not passed]
        return ', '.join(failed_filters)
    
    def get_filter_statistics(self) -> Dict:
        """Get filtering performance statistics"""
        total = self.filter_stats['total_signals']
        if total == 0:
            return self.filter_stats
        
        stats = self.filter_stats.copy()
        stats['filter_rate'] = stats['filtered_signals'] / total
        stats['volume_filter_rate'] = stats['volume_filtered'] / total
        stats['momentum_filter_rate'] = stats['momentum_filtered'] / total
        stats['volatility_filter_rate'] = stats['volatility_filtered'] / total
        stats['quality_filter_rate'] = stats['quality_filtered'] / total
        
        return stats
    
    def reset_statistics(self):
        """Reset filtering statistics"""
        for key in self.filter_stats:
            self.filter_stats[key] = 0


class EnhancedSignalGenerator(SignalGenerator):
    """
    Enhanced Signal Generator with statistical filtering
    Extends the base SignalGenerator with enhanced filtering capabilities
    """
    
    def __init__(self):
        super().__init__()
        self.signal_filter = EnhancedSignalFilter()
        self.enhanced_signals_generated = 0
        self.enhanced_signals_filtered = 0
        
        logging.info("🚀 Enhanced Signal Generator with filtering initialized")
    
    def generate_signal(self, symbol: str, price_data: pd.DataFrame, 
                       regime: str, volume_data: Optional[pd.DataFrame] = None) -> Dict:
        """
        Generate enhanced signal with statistical filtering
        
        Overrides base method to add filtering layer
        """
        # Generate base signal using parent method
        base_signal = super().generate_signal(symbol, price_data, regime, volume_data)
        
        # Apply enhanced filtering
        enhanced_signal = self.signal_filter.apply_enhanced_filtering(
            base_signal, price_data, volume_data
        )
        
        # Track statistics
        self.enhanced_signals_generated += 1
        if enhanced_signal.get('filtered', False):
            self.enhanced_signals_filtered += 1
        
        # Log enhanced signal
        if enhanced_signal.get('filtered', False):
            logging.info(f"🔍 {symbol} signal FILTERED: {enhanced_signal.get('reason', 'unknown')}")
        else:
            logging.info(f"✅ {symbol} enhanced signal: {enhanced_signal['signal']} "
                        f"(confidence: {enhanced_signal.get('enhanced_confidence', 0):.2f})")
        
        return enhanced_signal
    
    def get_enhancement_statistics(self) -> Dict:
        """Get enhancement performance statistics"""
        filter_stats = self.signal_filter.get_filter_statistics()
        
        enhancement_stats = {
            'total_enhanced_signals': self.enhanced_signals_generated,
            'total_filtered_signals': self.enhanced_signals_filtered,
            'enhancement_filter_rate': (
                self.enhanced_signals_filtered / self.enhanced_signals_generated 
                if self.enhanced_signals_generated > 0 else 0
            ),
            'filter_breakdown': filter_stats
        }
        
        return enhancement_stats


def main():
    """Test the enhanced signal filtering"""
    print("🔍 Testing Enhanced Signal Filtering")
    print("=" * 50)
    
    # Create test signal generator
    enhanced_generator = EnhancedSignalGenerator()
    
    # Create sample price data for testing
    dates = pd.date_range('2025-10-01', periods=30, freq='D')
    np.random.seed(42)
    
    price_data = pd.DataFrame({
        'close': 100 + np.cumsum(np.random.randn(30) * 0.02),
        'high': 0,
        'low': 0,
        'volume': np.random.randint(100000, 1000000, 30)
    })
    
    # Add high/low based on close
    price_data['high'] = price_data['close'] * (1 + np.random.rand(30) * 0.01)
    price_data['low'] = price_data['close'] * (1 - np.random.rand(30) * 0.01)
    
    # Test signal generation
    test_signal = enhanced_generator.generate_signal('TEST', price_data, 'UP_LOWVOL')
    
    print("Test Signal Results:")
    print(f"Signal: {test_signal.get('signal')}")
    print(f"Confidence: {test_signal.get('confidence', 0):.2f}")
    print(f"Enhanced Confidence: {test_signal.get('enhanced_confidence', 0):.2f}")
    print(f"Filtered: {test_signal.get('filtered', False)}")
    
    if test_signal.get('filtered'):
        print(f"Filter Reason: {test_signal.get('reason')}")
    
    # Print statistics
    stats = enhanced_generator.get_enhancement_statistics()
    print(f"\nEnhancement Statistics:")
    print(f"Total Signals: {stats['total_enhanced_signals']}")
    print(f"Filtered Signals: {stats['total_filtered_signals']}")
    print(f"Filter Rate: {stats['enhancement_filter_rate']:.1%}")
    
    print("\n✅ Enhanced Signal Filtering test completed!")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Test Enhanced Signal Filtering
Comprehensive testing of the enhanced signal filtering implementation
"""

import unittest
import pandas as pd
import numpy as np
import sys
from pathlib import Path

# Add current directory to path for imports
sys.path.append(str(Path(__file__).parent))

from enhanced_signal_filtering import EnhancedSignalFilter, EnhancedSignalGenerator

class TestEnhancedSignalFiltering(unittest.TestCase):
    """Test suite for Enhanced Signal Filtering"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.filter = EnhancedSignalFilter()
        self.generator = EnhancedSignalGenerator()
        
        # Create test data
        np.random.seed(42)
        self.dates = pd.date_range('2025-10-01', periods=50, freq='D')
        
        # Base price data
        base_price = 100
        returns = np.random.randn(50) * 0.02
        prices = base_price * np.exp(np.cumsum(returns))
        
        self.price_data = pd.DataFrame({
            'close': prices,
            'high': prices * (1 + np.random.rand(50) * 0.01),
            'low': prices * (1 - np.random.rand(50) * 0.01),
            'volume': np.random.randint(100000, 1000000, 50)
        }, index=self.dates)
        
        # Sample signal
        self.sample_signal = {
            'signal': 'buy',
            'confidence': 0.75,
            'reason': 'test_signal',
            'strategies': {
                'rsi': {'signal': 'buy', 'strength': 0.8},
                'macd': {'signal': 'buy', 'strength': 0.7}
            }
        }
    
    def test_volume_filter_high_volume(self):
        """Test volume filter with high volume scenario"""
        # Create high volume scenario
        test_data = self.price_data.copy()
        test_data.iloc[-1, test_data.columns.get_loc('volume')] = 2000000  # High volume
        
        result = self.filter._apply_volume_filter(test_data)
        
        self.assertTrue(result['passed'], "High volume should pass filter")
        self.assertGreater(result['volume_ratio'], 1.2, "Volume ratio should be above threshold")
    
    def test_volume_filter_low_volume(self):
        """Test volume filter with low volume scenario"""
        # Create low volume scenario
        test_data = self.price_data.copy()
        test_data.iloc[-1, test_data.columns.get_loc('volume')] = 50000  # Low volume
        
        result = self.filter._apply_volume_filter(test_data)
        
        self.assertFalse(result['passed'], "Low volume should fail filter")
        self.assertLess(result['volume_ratio'], 1.2, "Volume ratio should be below threshold")
    
    def test_momentum_filter_strong_momentum(self):
        """Test momentum filter with strong momentum"""
        # Create strong upward momentum
        test_data = self.price_data.copy()
        test_data['close'].iloc[-20:] = test_data['close'].iloc[-20] * np.linspace(1.0, 1.15, 20)
        
        result = self.filter._apply_momentum_filter(test_data)
        
        self.assertTrue(result['passed'], "Strong momentum should pass filter")
        self.assertGreater(result['momentum_5d'], 0.02, "5-day momentum should exceed threshold")
    
    def test_momentum_filter_weak_momentum(self):
        """Test momentum filter with weak momentum"""
        # Create sideways movement (weak momentum)
        test_data = self.price_data.copy()
        test_data['close'].iloc[-20:] = test_data['close'].iloc[-20] * (1 + np.random.randn(20) * 0.005)
        
        result = self.filter._apply_momentum_filter(test_data)
        
        # May pass or fail depending on random data, but should have low momentum
        self.assertLess(abs(result['momentum_5d']), 0.05, "Weak momentum should be small")
    
    def test_volatility_filter_normal_volatility(self):
        """Test volatility filter with normal volatility"""
        result = self.filter._apply_volatility_filter(self.price_data)
        
        # Should typically pass with normal test data
        self.assertIsInstance(result['passed'], bool)
        self.assertGreater(result['volatility_ratio'], 0, "Volatility ratio should be positive")
    
    def test_volatility_filter_extreme_volatility(self):
        """Test volatility filter with extreme volatility"""
        # Create extreme volatility
        test_data = self.price_data.copy()
        extreme_returns = np.random.randn(5) * 0.1  # 10% daily moves
        test_data['close'].iloc[-5:] = test_data['close'].iloc[-6] * np.exp(np.cumsum(extreme_returns))
        
        result = self.filter._apply_volatility_filter(test_data)
        
        # High volatility should often fail the filter
        if result['volatility_ratio'] > 2.0:
            self.assertFalse(result['passed'], "Extreme volatility should fail filter")
    
    def test_quality_filter_high_confidence(self):
        """Test quality filter with high confidence signal"""
        high_confidence_signal = self.sample_signal.copy()
        high_confidence_signal['confidence'] = 0.85
        
        # Create filter details that would pass
        filter_details = {
            'volume': {'passed': True},
            'momentum': {'passed': True},
            'volatility': {'passed': True}
        }
        
        result = self.filter._apply_quality_filter(high_confidence_signal, filter_details)
        
        self.assertTrue(result['passed'], "High confidence with confirmations should pass")
        self.assertEqual(result['confirmations'], 3, "Should count all confirmations")
    
    def test_quality_filter_low_confidence(self):
        """Test quality filter with low confidence signal"""
        low_confidence_signal = self.sample_signal.copy()
        low_confidence_signal['confidence'] = 0.4  # Below 0.6 threshold
        
        filter_details = {
            'volume': {'passed': True},
            'momentum': {'passed': True},
            'volatility': {'passed': True}
        }
        
        result = self.filter._apply_quality_filter(low_confidence_signal, filter_details)
        
        self.assertFalse(result['passed'], "Low confidence should fail filter")
    
    def test_statistical_filter(self):
        """Test statistical confidence filter"""
        result = self.filter._apply_statistical_filter(self.price_data, self.sample_signal)
        
        self.assertIsInstance(result['passed'], bool)
        self.assertIn('price_z_score', result)
        self.assertIn('volume_z_score', result)
        self.assertIn('momentum_percentile', result)
    
    def test_complete_filtering_pipeline(self):
        """Test complete filtering pipeline"""
        # Test with original signal
        enhanced_signal = self.filter.apply_enhanced_filtering(
            self.sample_signal, self.price_data
        )
        
        self.assertIn('filtered', enhanced_signal)
        self.assertIn('filter_results', enhanced_signal)
        self.assertIn('enhanced_confidence', enhanced_signal)
        
        # Verify filter results structure
        filter_results = enhanced_signal['filter_results']
        expected_filters = ['volume_filter', 'momentum_filter', 'volatility_filter', 
                          'quality_filter', 'statistical_filter']
        
        for filter_name in expected_filters:
            self.assertIn(filter_name, filter_results)
            self.assertIsInstance(filter_results[filter_name], bool)
    
    def test_hold_signal_bypass(self):
        """Test that hold signals bypass filtering"""
        hold_signal = {'signal': 'hold', 'confidence': 0.5}
        
        enhanced_signal = self.filter.apply_enhanced_filtering(
            hold_signal, self.price_data
        )
        
        # Hold signals should not be filtered
        self.assertEqual(enhanced_signal['signal'], 'hold')
        self.assertNotIn('filtered', enhanced_signal)
    
    def test_enhanced_signal_generator(self):
        """Test the complete enhanced signal generator"""
        signal = self.generator.generate_signal(
            'TEST', self.price_data, 'UP_LOWVOL'
        )
        
        # Should have enhanced properties
        self.assertIn('signal', signal)
        self.assertIn('confidence', signal)
        
        # If not a hold signal, should have filter information
        if signal['signal'] != 'hold':
            self.assertIn('enhanced_confidence', signal)
    
    def test_filter_statistics(self):
        """Test filter statistics tracking"""
        # Reset statistics
        self.filter.reset_statistics()
        
        # Apply filtering multiple times
        for i in range(5):
            test_signal = {
                'signal': 'buy' if i % 2 == 0 else 'sell',
                'confidence': 0.5 + (i * 0.1)
            }
            self.filter.apply_enhanced_filtering(test_signal, self.price_data)
        
        stats = self.filter.get_filter_statistics()
        
        self.assertEqual(stats['total_signals'], 5)
        self.assertGreaterEqual(stats['filtered_signals'], 0)
        self.assertLessEqual(stats['filtered_signals'], 5)
    
    def test_enhanced_confidence_calculation(self):
        """Test enhanced confidence calculation"""
        # Create favorable filter details
        filter_details = {
            'volume': {'passed': True, 'volume_ratio': 2.0},
            'momentum': {'passed': True, 'momentum_score': 0.08},
            'quality': {'passed': True, 'confirmations': 3}
        }
        
        enhanced_confidence = self.filter._calculate_enhanced_confidence(
            self.sample_signal, filter_details, True
        )
        
        # Enhanced confidence should be higher than original
        self.assertGreater(enhanced_confidence, self.sample_signal['confidence'])
        self.assertLessEqual(enhanced_confidence, 1.0)
    
    def test_filter_failure_reasons(self):
        """Test filter failure reason reporting"""
        filter_results = {
            'volume_filter': False,
            'momentum_filter': True,
            'volatility_filter': False,
            'quality_filter': True,
            'statistical_filter': True
        }
        
        reason = self.filter._get_filter_failure_reason(filter_results)
        
        self.assertIn('volume_filter', reason)
        self.assertIn('volatility_filter', reason)
        self.assertNotIn('momentum_filter', reason)


def run_comprehensive_test():
    """Run comprehensive test suite"""
    print("🧪 Running Enhanced Signal Filtering Test Suite")
    print("=" * 60)
    
    # Run unit tests
    unittest.main(argv=[''], exit=False, verbosity=2)
    
    print("\n🔬 Additional Integration Tests")
    print("-" * 40)
    
    # Create test instance
    generator = EnhancedSignalGenerator()
    
    # Test with various market conditions
    test_scenarios = [
        ('Trending Up', create_trending_data(1.05)),
        ('Trending Down', create_trending_data(0.95)),
        ('High Volatility', create_volatile_data()),
        ('Low Volume', create_low_volume_data()),
        ('Sideways', create_sideways_data())
    ]
    
    for scenario_name, test_data in test_scenarios:
        print(f"\nTesting {scenario_name}:")
        
        signal = generator.generate_signal('TEST', test_data, 'UP_LOWVOL')
        
        print(f"  Signal: {signal.get('signal')}")
        print(f"  Confidence: {signal.get('confidence', 0):.2f}")
        print(f"  Enhanced: {signal.get('enhanced_confidence', 0):.2f}")
        print(f"  Filtered: {signal.get('filtered', False)}")
    
    # Print final statistics
    stats = generator.get_enhancement_statistics()
    print(f"\nFinal Test Statistics:")
    print(f"Total Signals Generated: {stats['total_enhanced_signals']}")
    print(f"Signals Filtered: {stats['total_filtered_signals']}")
    print(f"Filter Rate: {stats['enhancement_filter_rate']:.1%}")
    
    print("\n✅ Comprehensive testing completed!")


def create_trending_data(trend_factor):
    """Create trending price data for testing"""
    np.random.seed(42)
    dates = pd.date_range('2025-10-01', periods=30, freq='D')
    base_price = 100
    
    # Create trending prices
    trend_component = np.linspace(1.0, trend_factor, 30)
    noise = np.random.randn(30) * 0.01
    prices = base_price * trend_component * (1 + noise)
    
    return pd.DataFrame({
        'close': prices,
        'high': prices * 1.01,
        'low': prices * 0.99,
        'volume': np.random.randint(200000, 800000, 30)
    }, index=dates)


def create_volatile_data():
    """Create high volatility price data"""
    np.random.seed(42)
    dates = pd.date_range('2025-10-01', periods=30, freq='D')
    base_price = 100
    
    # High volatility returns
    returns = np.random.randn(30) * 0.05  # 5% daily volatility
    prices = base_price * np.exp(np.cumsum(returns))
    
    return pd.DataFrame({
        'close': prices,
        'high': prices * 1.02,
        'low': prices * 0.98,
        'volume': np.random.randint(300000, 1200000, 30)
    }, index=dates)


def create_low_volume_data():
    """Create low volume price data"""
    np.random.seed(42)
    dates = pd.date_range('2025-10-01', periods=30, freq='D')
    base_price = 100
    
    returns = np.random.randn(30) * 0.015
    prices = base_price * np.exp(np.cumsum(returns))
    
    return pd.DataFrame({
        'close': prices,
        'high': prices * 1.005,
        'low': prices * 0.995,
        'volume': np.random.randint(50000, 150000, 30)  # Low volume
    }, index=dates)


def create_sideways_data():
    """Create sideways/range-bound price data"""
    np.random.seed(42)
    dates = pd.date_range('2025-10-01', periods=30, freq='D')
    base_price = 100
    
    # Sideways movement with small oscillations
    oscillation = np.sin(np.arange(30) * 0.5) * 0.02
    noise = np.random.randn(30) * 0.005
    prices = base_price * (1 + oscillation + noise)
    
    return pd.DataFrame({
        'close': prices,
        'high': prices * 1.005,
        'low': prices * 0.995,
        'volume': np.random.randint(150000, 500000, 30)
    }, index=dates)


if __name__ == "__main__":
    run_comprehensive_test()
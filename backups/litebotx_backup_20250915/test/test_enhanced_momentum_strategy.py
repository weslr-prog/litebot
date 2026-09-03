"""
Unit tests for EnhancedMomentumStrategy - Multi-sector momentum with rotation
Tests enhanced signal generation and composite scoring
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
import numpy as np
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.enhanced_momentum_strategy import EnhancedMomentumStrategy

class TestEnhancedMomentumStrategy(unittest.TestCase):
    """Test cases for EnhancedMomentumStrategy functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_api_key = "TEST_API_KEY"
        self.strategy = EnhancedMomentumStrategy(self.test_api_key)
        
        # Sample market data
        dates = pd.date_range('2024-01-01', periods=50, freq='D')
        self.sample_market_data = {}
        
        # Create sample price data for different stocks
        for symbol in ['AAPL', 'MSFT', 'JPM', 'XOM', 'JNJ']:
            prices = 100 + np.cumsum(np.random.randn(50) * 0.02)  # Random walk
            self.sample_market_data[symbol] = pd.DataFrame({
                'close': prices,
                'volume': np.random.randint(1000000, 10000000, 50)
            }, index=dates)
        
        # Sample individual momentum signals
        self.sample_individual_signals = [
            {'symbol': 'AAPL', 'momentum_score': 0.85, 'shares': 100, 'position_value': 18000},
            {'symbol': 'MSFT', 'momentum_score': 0.78, 'shares': 80, 'position_value': 15000},
            {'symbol': 'JPM', 'momentum_score': 0.65, 'shares': 120, 'position_value': 12000},
            {'symbol': 'XOM', 'momentum_score': 0.45, 'shares': 150, 'position_value': 8000},
            {'symbol': 'JNJ', 'momentum_score': 0.72, 'shares': 90, 'position_value': 14000}
        ]
        
        # Sample sector weights
        self.sample_sector_weights = {
            'Technology': 0.25,
            'Financials': 0.15,
            'Energy': 0.08,
            'Health Care': 0.18,
            'Industrials': 0.12
        }
    
    def test_initialization(self):
        """Test EnhancedMomentumStrategy initialization"""
        self.assertIsNotNone(self.strategy.sector_analyzer)
        self.assertEqual(self.strategy.sector_lookback, 21)
        self.assertIn('individual_momentum', self.strategy.weights)
        self.assertIn('sector_momentum', self.strategy.weights)
        self.assertIn('relative_strength', self.strategy.weights)
        
        # Check weight normalization
        total_weights = sum(self.strategy.weights.values())
        self.assertAlmostEqual(total_weights, 1.0, places=2)
    
    @patch('core.enhanced_momentum_strategy.MomentumStrategy.generate_signals')
    @patch.object(EnhancedMomentumStrategy, '_calculate_relative_strength')
    @patch.object(EnhancedMomentumStrategy, '_apply_sector_diversification')
    @patch.object(EnhancedMomentumStrategy, '_calculate_composite_scores')
    def test_generate_enhanced_signals_success(self, mock_composite, mock_diversify, 
                                             mock_relative, mock_basic_signals):
        """Test successful enhanced signal generation"""
        # Setup mocks
        mock_basic_signals.return_value = self.sample_individual_signals
        mock_relative.return_value = self.sample_individual_signals
        mock_diversify.return_value = self.sample_individual_signals
        mock_composite.return_value = self.sample_individual_signals
        
        # Mock sector analyzer
        self.strategy.sector_analyzer.get_sector_allocation_weights = Mock(
            return_value=self.sample_sector_weights
        )
        self.strategy.sector_analyzer.filter_stocks_by_sector_momentum = Mock(
            return_value=self.sample_individual_signals
        )
        
        # Test enhanced signal generation
        enhanced_signals = self.strategy.generate_enhanced_signals(
            self.sample_market_data, 100000
        )
        
        self.assertIsInstance(enhanced_signals, list)
        self.assertTrue(len(enhanced_signals) > 0)
        
        # Verify all processing steps were called
        mock_basic_signals.assert_called_once()
        mock_relative.assert_called_once()
        mock_diversify.assert_called_once()
        mock_composite.assert_called_once()
    
    @patch('core.enhanced_momentum_strategy.MomentumStrategy.generate_signals')
    def test_generate_enhanced_signals_no_basic_signals(self, mock_basic_signals):
        """Test enhanced signal generation with no basic signals"""
        mock_basic_signals.return_value = []
        
        enhanced_signals = self.strategy.generate_enhanced_signals(
            self.sample_market_data, 100000
        )
        
        self.assertEqual(enhanced_signals, [])
    
    def test_calculate_relative_strength(self):
        """Test relative strength calculation"""
        # Prepare signals with sector information
        signals_with_sector = []
        for signal in self.sample_individual_signals:
            enhanced_signal = signal.copy()
            enhanced_signal['sector_etf'] = 'XLK'  # Assume all tech for testing
            enhanced_signal['sector_weight'] = 0.15
            signals_with_sector.append(enhanced_signal)
        
        # Calculate relative strength
        enhanced_signals = self.strategy._calculate_relative_strength(
            signals_with_sector, self.sample_market_data
        )
        
        self.assertEqual(len(enhanced_signals), len(signals_with_sector))
        
        # Check that relative strength fields are added
        for signal in enhanced_signals:
            if signal['symbol'] in self.sample_market_data:
                self.assertIn('relative_strength', signal)
                self.assertIn('stock_momentum', signal)
                self.assertIn('sector_momentum', signal)
    
    def test_apply_sector_diversification(self):
        """Test sector diversification limits"""
        # Create signals with sector information
        signals_with_sectors = []
        sectors = ['Technology', 'Technology', 'Technology', 'Technology', 'Financials']
        
        for i, signal in enumerate(self.sample_individual_signals):
            enhanced_signal = signal.copy()
            enhanced_signal['sector'] = sectors[i]
            signals_with_sectors.append(enhanced_signal)
        
        # Apply diversification with max 2 per sector
        diversified_signals = self.strategy._apply_sector_diversification(
            signals_with_sectors, max_per_sector=2
        )
        
        # Count technology stocks (should be limited to 2)
        tech_count = sum(1 for s in diversified_signals if s.get('sector') == 'Technology')
        self.assertLessEqual(tech_count, 2)
        
        # Should still have the financial stock
        financial_count = sum(1 for s in diversified_signals if s.get('sector') == 'Financials')
        self.assertEqual(financial_count, 1)
    
    def test_calculate_composite_scores(self):
        """Test composite score calculation"""
        # Prepare signals with required fields
        signals_with_components = []
        for signal in self.sample_individual_signals:
            enhanced_signal = signal.copy()
            enhanced_signal['sector_weight'] = 0.15
            enhanced_signal['relative_strength'] = 0.05
            signals_with_components.append(enhanced_signal)
        
        # Calculate composite scores
        final_signals = self.strategy._calculate_composite_scores(signals_with_components)
        
        self.assertEqual(len(final_signals), len(signals_with_components))
        
        # Check that composite scores are added and signals are sorted
        for signal in final_signals:
            self.assertIn('composite_score', signal)
            self.assertIn('individual_momentum', signal)
            self.assertIn('sector_momentum_score', signal)
        
        # Check sorting (first should have highest composite score)
        if len(final_signals) > 1:
            self.assertGreaterEqual(
                final_signals[0]['composite_score'],
                final_signals[1]['composite_score']
            )
    
    def test_weight_configuration(self):
        """Test that signal weights are properly configured"""
        weights = self.strategy.weights
        
        # Check all required components are present
        required_weights = ['individual_momentum', 'sector_momentum', 'relative_strength']
        for weight_type in required_weights:
            self.assertIn(weight_type, weights)
            self.assertGreater(weights[weight_type], 0)
        
        # Check that individual momentum has significant weight
        self.assertGreater(weights['individual_momentum'], 0.3)
        
        # Check that sector components are meaningful
        sector_total = weights['sector_momentum'] + weights.get('sector_rotation', 0)
        self.assertGreater(sector_total, 0.4)
    
    def test_edge_cases_empty_signals(self):
        """Test handling of edge cases with empty signals"""
        # Test with empty signals
        empty_result = self.strategy._calculate_relative_strength([], self.sample_market_data)
        self.assertEqual(empty_result, [])
        
        empty_diversified = self.strategy._apply_sector_diversification([])
        self.assertEqual(empty_diversified, [])
        
        empty_composite = self.strategy._calculate_composite_scores([])
        self.assertEqual(empty_composite, [])
    
    def test_missing_market_data_handling(self):
        """Test handling of missing market data"""
        # Signal for stock not in market data
        signals_missing_data = [
            {'symbol': 'MISSING', 'momentum_score': 0.5, 'sector_etf': 'XLK'}
        ]
        
        # Should handle gracefully without crashing
        enhanced_signals = self.strategy._calculate_relative_strength(
            signals_missing_data, self.sample_market_data
        )
        
        self.assertEqual(len(enhanced_signals), 1)
        # Should pass through original signal
        self.assertEqual(enhanced_signals[0]['symbol'], 'MISSING')


if __name__ == '__main__':
    unittest.main()

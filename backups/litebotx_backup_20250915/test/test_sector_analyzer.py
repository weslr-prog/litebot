"""
Unit tests for SectorAnalyzer - Multi-sector momentum analysis
Tests Alpha Vantage integration and sector rotation logic
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
import numpy as np
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.sector_analyzer import SectorAnalyzer

class TestSectorAnalyzer(unittest.TestCase):
    """Test cases for SectorAnalyzer functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_api_key = "TEST_API_KEY"
        self.analyzer = SectorAnalyzer(self.test_api_key)
        
        # Sample sector performance data
        self.sample_sector_data = {
            'XLK': {'momentum': 0.15, 'volatility': 0.25},  # Technology
            'XLF': {'momentum': 0.08, 'volatility': 0.20},  # Financial
            'XLE': {'momentum': -0.05, 'volatility': 0.35}, # Energy
            'XLV': {'momentum': 0.12, 'volatility': 0.18},  # Healthcare
            'XLI': {'momentum': 0.06, 'volatility': 0.22}   # Industrial
        }
        
        # Sample stock signals
        self.sample_signals = [
            {'symbol': 'AAPL', 'momentum_score': 0.85, 'sector': 'Technology'},
            {'symbol': 'MSFT', 'momentum_score': 0.78, 'sector': 'Technology'},
            {'symbol': 'JPM', 'momentum_score': 0.65, 'sector': 'Financials'},
            {'symbol': 'XOM', 'momentum_score': 0.45, 'sector': 'Energy'},
            {'symbol': 'JNJ', 'momentum_score': 0.72, 'sector': 'Health Care'}
        ]
    
    def test_initialization(self):
        """Test SectorAnalyzer initialization"""
        self.assertEqual(self.analyzer.api_key, self.test_api_key)
        self.assertIsNotNone(self.analyzer.sector_etfs)
        self.assertIsNotNone(self.analyzer.stock_to_sector)
        self.assertEqual(len(self.analyzer.sector_etfs), 11)  # 11 GICS sectors
    
    def test_sector_etf_mapping(self):
        """Test sector ETF mapping completeness"""
        expected_etfs = ['XLK', 'XLF', 'XLE', 'XLV', 'XLI', 'XLY', 'XLP', 'XLB', 'XLRE', 'XLU', 'SPY']
        
        for etf in expected_etfs:
            self.assertIn(etf, self.analyzer.sector_etfs.values())
    
    def test_stock_to_sector_mapping(self):
        """Test stock to sector classification"""
        # Test known mappings
        self.assertEqual(self.analyzer.stock_to_sector.get('AAPL'), 'Technology')
        self.assertEqual(self.analyzer.stock_to_sector.get('MSFT'), 'Technology')
        self.assertEqual(self.analyzer.stock_to_sector.get('JPM'), 'Financials')
        self.assertEqual(self.analyzer.stock_to_sector.get('XOM'), 'Energy')
    
    @patch('core.sector_analyzer.requests.get')
    def test_get_sector_performance_success(self, mock_get):
        """Test successful sector performance data retrieval"""
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'Time Series (Daily)': {
                '2024-01-15': {'4. close': '100.0'},
                '2024-01-14': {'4. close': '99.0'},
                '2024-01-13': {'4. close': '98.0'},
                '2024-01-12': {'4. close': '97.0'}
            }
        }
        mock_get.return_value = mock_response
        
        performance = self.analyzer.get_sector_performance('XLK')
        
        self.assertIsNotNone(performance)
        self.assertIn('momentum', performance)
        self.assertIn('volatility', performance)
        self.assertIsInstance(performance['momentum'], float)
        self.assertIsInstance(performance['volatility'], float)
    
    @patch('core.sector_analyzer.requests.get')
    def test_get_sector_performance_api_error(self, mock_get):
        """Test sector performance with API error"""
        # Mock API error
        mock_response = Mock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response
        
        performance = self.analyzer.get_sector_performance('XLK')
        
        # Should return default values on error
        self.assertEqual(performance['momentum'], 0.0)
        self.assertEqual(performance['volatility'], 0.2)
    
    @patch.object(SectorAnalyzer, 'get_sector_performance')
    def test_get_sector_allocation_weights(self, mock_get_performance):
        """Test sector allocation weight calculation"""
        # Mock sector performance data
        def mock_performance_side_effect(sector_etf):
            return self.sample_sector_data.get(sector_etf, {'momentum': 0.0, 'volatility': 0.2})
        
        mock_get_performance.side_effect = mock_performance_side_effect
        
        weights = self.analyzer.get_sector_allocation_weights()
        
        self.assertIsInstance(weights, dict)
        self.assertTrue(len(weights) > 0)
        
        # Check that weights sum approximately to 1.0
        total_weight = sum(weights.values())
        self.assertAlmostEqual(total_weight, 1.0, places=1)
        
        # Check that high momentum sectors get higher weights
        if 'Technology' in weights and 'Energy' in weights:
            self.assertGreater(weights['Technology'], weights['Energy'])
    
    @patch.object(SectorAnalyzer, 'get_sector_allocation_weights')
    def test_filter_stocks_by_sector_momentum(self, mock_get_weights):
        """Test filtering stocks by sector momentum"""
        # Mock sector weights (high tech, low energy)
        mock_weights = {
            'Technology': 0.25,
            'Financials': 0.15,
            'Energy': 0.05,
            'Health Care': 0.20,
            'Industrials': 0.10
        }
        mock_get_weights.return_value = mock_weights
        
        filtered_signals = self.analyzer.filter_stocks_by_sector_momentum(
            self.sample_signals, mock_weights
        )
        
        self.assertIsInstance(filtered_signals, list)
        self.assertTrue(len(filtered_signals) > 0)
        
        # Check that signals have sector information added
        for signal in filtered_signals:
            self.assertIn('sector_weight', signal)
            self.assertIn('sector_etf', signal)
            
        # Technology stocks should have higher sector weights
        tech_signals = [s for s in filtered_signals if s.get('sector') == 'Technology']
        energy_signals = [s for s in filtered_signals if s.get('sector') == 'Energy']
        
        if tech_signals and energy_signals:
            self.assertGreater(tech_signals[0]['sector_weight'], 
                             energy_signals[0]['sector_weight'])


if __name__ == '__main__':
    unittest.main()

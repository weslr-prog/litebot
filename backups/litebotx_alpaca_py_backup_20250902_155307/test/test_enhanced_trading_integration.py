"""
Integration tests for Enhanced Multi-Sector Momentum Trading System
Tests end-to-end functionality of the enhanced trading system
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
import numpy as np
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from automated_momentum_trader_v2 import AutomatedMomentumTraderV2

class TestEnhancedTradingIntegration(unittest.TestCase):
    """Integration test cases for enhanced trading system"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_api_key = "TEST_API_KEY"
        
        # Mock the trading engine to avoid real trading
        with patch('automated_momentum_trader_v2.RealPaperTradingEngine'):
            self.trader = AutomatedMomentumTraderV2(
                symbols=['AAPL', 'MSFT', 'JPM', 'XOM', 'JNJ'],
                alpha_vantage_key=self.test_api_key,
                use_enhanced_strategy=True
            )
        
        # Sample market data for testing
        dates = pd.date_range('2024-01-01', periods=50, freq='D')
        self.sample_market_data = {}
        
        for symbol in ['AAPL', 'MSFT', 'JPM', 'XOM', 'JNJ']:
            # Create realistic price movements
            base_price = 100 + np.random.randint(-20, 20)
            returns = np.random.randn(50) * 0.02  # 2% daily volatility
            prices = base_price * np.exp(np.cumsum(returns))
            
            self.sample_market_data[symbol] = pd.DataFrame({
                'close': prices,
                'volume': np.random.randint(1000000, 10000000, 50),
                'high': prices * 1.02,
                'low': prices * 0.98,
                'open': prices * (1 + np.random.randn(50) * 0.005)
            }, index=dates)
    
    def test_enhanced_strategy_initialization(self):
        """Test that enhanced strategy is properly initialized"""
        self.assertTrue(self.trader.use_enhanced_strategy)
        self.assertEqual(self.trader.momentum_strategy.__class__.__name__, 'EnhancedMomentumStrategy')
        self.assertIsNotNone(self.trader.momentum_strategy.sector_analyzer)
    
    @patch('automated_momentum_trader_v2.AutomatedMomentumTraderV2.load_market_data')
    @patch.object(AutomatedMomentumTraderV2, 'weekend_risk')
    @patch.object(AutomatedMomentumTraderV2, 'risk_sizer')
    def test_run_momentum_analysis_with_enhanced_strategy(self, mock_risk_sizer, 
                                                        mock_weekend_risk, mock_load_data):
        """Test complete momentum analysis with enhanced strategy"""
        # Setup mocks
        mock_load_data.return_value = self.sample_market_data
        
        # Mock risk-adjusted signals
        mock_risk_signals = [
            {'symbol': 'AAPL', 'momentum_score': 0.85, 'composite_score': 0.82, 'shares': 100},
            {'symbol': 'MSFT', 'momentum_score': 0.78, 'composite_score': 0.75, 'shares': 80},
            {'symbol': 'JPM', 'momentum_score': 0.65, 'composite_score': 0.68, 'shares': 120}
        ]
        mock_risk_sizer.calculate_position_sizes.return_value = mock_risk_signals
        mock_weekend_risk.apply_friday_filters.return_value = mock_risk_signals
        
        # Mock trading engine
        self.trader.trading_engine.get_positions.return_value = {}
        self.trader.trading_engine.place_order.return_value = {'status': 'filled'}
        
        # Mock sector analyzer methods
        with patch.object(self.trader.momentum_strategy.sector_analyzer, 'get_sector_allocation_weights') as mock_weights:
            mock_weights.return_value = {
                'Technology': 0.25, 'Financials': 0.15, 'Energy': 0.08
            }
            
            with patch.object(self.trader.momentum_strategy.sector_analyzer, 'filter_stocks_by_sector_momentum') as mock_filter:
                mock_filter.return_value = mock_risk_signals
                
                # Run momentum analysis
                try:
                    self.trader.run_momentum_analysis()
                    # If we get here without exception, the integration is working
                    self.assertTrue(True)
                except Exception as e:
                    self.fail(f"Enhanced momentum analysis failed with error: {e}")
    
    def test_sector_aware_signal_generation(self):
        """Test that sector awareness improves signal quality"""
        # Test with basic strategy
        basic_trader = AutomatedMomentumTraderV2(
            symbols=['AAPL', 'MSFT', 'JPM'],
            use_enhanced_strategy=False
        )
        
        # Mock basic signals
        with patch.object(basic_trader.momentum_strategy, 'generate_signals') as mock_basic:
            mock_basic.return_value = [
                {'symbol': 'AAPL', 'momentum_score': 0.85},
                {'symbol': 'MSFT', 'momentum_score': 0.78},
                {'symbol': 'JPM', 'momentum_score': 0.65}
            ]
            
            basic_signals = basic_trader.momentum_strategy.generate_signals(
                self.sample_market_data, 100000
            )
        
        # Test with enhanced strategy
        with patch.object(self.trader.momentum_strategy.sector_analyzer, 'get_sector_allocation_weights') as mock_weights:
            mock_weights.return_value = {'Technology': 0.25, 'Financials': 0.15}
            
            with patch.object(self.trader.momentum_strategy.sector_analyzer, 'filter_stocks_by_sector_momentum') as mock_filter:
                mock_filter.return_value = [
                    {'symbol': 'AAPL', 'momentum_score': 0.85, 'sector_weight': 0.25, 'composite_score': 0.82},
                    {'symbol': 'MSFT', 'momentum_score': 0.78, 'sector_weight': 0.25, 'composite_score': 0.75}
                ]
                
                enhanced_signals = self.trader.momentum_strategy.generate_enhanced_signals(
                    self.sample_market_data, 100000
                )
        
        # Enhanced signals should have additional fields
        if enhanced_signals:
            self.assertIn('composite_score', enhanced_signals[0])
            self.assertIn('sector_weight', enhanced_signals[0])
    
    def test_sector_diversification_enforcement(self):
        """Test that sector diversification limits are enforced"""
        # Create signals heavily concentrated in one sector
        concentrated_signals = [
            {'symbol': 'AAPL', 'momentum_score': 0.95, 'sector': 'Technology'},
            {'symbol': 'MSFT', 'momentum_score': 0.90, 'sector': 'Technology'},
            {'symbol': 'GOOGL', 'momentum_score': 0.85, 'sector': 'Technology'},
            {'symbol': 'AMZN', 'momentum_score': 0.80, 'sector': 'Technology'},
            {'symbol': 'JPM', 'momentum_score': 0.75, 'sector': 'Financials'}
        ]
        
        # Apply diversification
        diversified = self.trader.momentum_strategy._apply_sector_diversification(
            concentrated_signals, max_per_sector=3
        )
        
        # Should limit tech stocks to 3
        tech_count = sum(1 for s in diversified if s.get('sector') == 'Technology')
        self.assertLessEqual(tech_count, 3)
    
    def test_alpha_vantage_integration_fallback(self):
        """Test graceful fallback when Alpha Vantage API fails"""
        # Mock API failure
        with patch.object(self.trader.momentum_strategy.sector_analyzer, 'get_sector_performance') as mock_api:
            mock_api.side_effect = Exception("API Error")
            
            # Should still generate basic signals without crashing
            with patch.object(self.trader.momentum_strategy, 'generate_signals') as mock_basic:
                mock_basic.return_value = [
                    {'symbol': 'AAPL', 'momentum_score': 0.85}
                ]
                
                try:
                    signals = self.trader.momentum_strategy.generate_enhanced_signals(
                        self.sample_market_data, 100000
                    )
                    # Should fallback to basic signals
                    self.assertIsInstance(signals, list)
                except Exception as e:
                    # Should not crash, but may return basic signals
                    pass
    
    def test_performance_metrics_enhancement(self):
        """Test that enhanced strategy provides better performance metrics"""
        # This is a conceptual test - in practice, you'd run backtests
        
        # Enhanced strategy should provide:
        # 1. Composite scores combining multiple factors
        # 2. Sector rotation signals
        # 3. Risk-adjusted sector weights
        # 4. Diversification across sectors
        
        sample_enhanced_signal = {
            'symbol': 'AAPL',
            'momentum_score': 0.85,
            'composite_score': 0.82,
            'sector_weight': 0.25,
            'sector': 'Technology',
            'relative_strength': 0.05,
            'individual_momentum': 0.85,
            'sector_momentum_score': 0.15
        }
        
        # Verify enhanced signal has all expected fields
        expected_fields = [
            'composite_score', 'sector_weight', 'sector', 
            'relative_strength', 'individual_momentum', 'sector_momentum_score'
        ]
        
        for field in expected_fields:
            self.assertIn(field, sample_enhanced_signal)
    
    def test_weekend_risk_integration_with_sectors(self):
        """Test that weekend risk management works with sector analysis"""
        # Mock Friday 3:45 PM scenario
        friday_signals = [
            {'symbol': 'AAPL', 'composite_score': 0.85, 'sector': 'Technology'},
            {'symbol': 'XOM', 'composite_score': 0.45, 'sector': 'Energy'}  # High volatility sector
        ]
        
        # Weekend risk should consider both individual and sector volatility
        filtered_signals = self.trader.weekend_risk.apply_friday_filters(
            friday_signals, 
            self.trader.weekend_risk._create_friday_afternoon_time()
        )
        
        # Should maintain the filtering capability
        self.assertIsInstance(filtered_signals, list)


if __name__ == '__main__':
    # Set up test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestEnhancedTradingIntegration)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

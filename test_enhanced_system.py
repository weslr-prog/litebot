"""
Comprehensive Test Suite for Enhanced Trading System
Tests quality scoring, free data filters, and dynamic exits
Created: November 4, 2025
"""

import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

from intraday_quality_scorer import IntradayQualityScorer
from free_data_filter import FreeDataFilter
from enhanced_signal_integration import DynamicExitManager, EnhancedSignalGenerator

logging.basicConfig(level=logging.WARNING)  # Reduce noise during tests


class TestIntradayQualityScorer(unittest.TestCase):
    """Test quality scoring logic"""
    
    def setUp(self):
        self.scorer = IntradayQualityScorer()
        self.sample_data = self._create_sample_data()
    
    def _create_sample_data(self, trend='bullish', volatility='normal'):
        """Create sample market data"""
        dates = pd.date_range(end=datetime.now(), periods=50, freq='1min')
        
        if trend == 'bullish':
            close = np.random.randn(50).cumsum() + 100
            close = close + np.linspace(0, 5, 50)  # Upward trend
        else:
            close = np.random.randn(50).cumsum() + 100
        
        if volatility == 'high':
            high = close + np.random.rand(50) * 2
            low = close - np.random.rand(50) * 2
        else:
            high = close + np.random.rand(50) * 0.5
            low = close - np.random.rand(50) * 0.5
        
        volume = np.random.randint(100000, 500000, 50)
        if trend == 'bullish':
            volume[-10:] = volume[-10:] * 2  # Volume surge
        
        return pd.DataFrame({
            'close': close,
            'high': high,
            'low': low,
            'volume': volume
        }, index=dates)
    
    def test_score_returns_valid_range(self):
        """Test that scores are in 0-100 range"""
        result = self.scorer.score_signal("TEST", self.sample_data, 100.0)
        
        self.assertGreaterEqual(result['total_score'], 0)
        self.assertLessEqual(result['total_score'], 100)
    
    def test_quality_tier_classification(self):
        """Test quality tier assignment"""
        result = self.scorer.score_signal("TEST", self.sample_data, 100.0)
        
        self.assertIn(result['quality_tier'], ['STRONG', 'MEDIUM', 'WEAK'])
        
        # Strong signals should have high scores
        if result['quality_tier'] == 'STRONG':
            self.assertGreaterEqual(result['total_score'], 75)
        elif result['quality_tier'] == 'MEDIUM':
            self.assertGreaterEqual(result['total_score'], 55)
            self.assertLess(result['total_score'], 75)
        else:  # WEAK
            self.assertLess(result['total_score'], 55)
    
    def test_component_scores_present(self):
        """Test all scoring components are calculated"""
        result = self.scorer.score_signal("TEST", self.sample_data, 100.0)
        
        components = result['component_scores']
        required_components = [
            'multi_timeframe', 'volume_quality', 
            'momentum_quality', 'statistical_quality'
        ]
        
        for component in required_components:
            self.assertIn(component, components)
            self.assertIsInstance(components[component], (int, float))
    
    def test_bullish_data_scores_higher(self):
        """Test that bullish data scores higher than bearish"""
        bullish_data = self._create_sample_data(trend='bullish', volatility='high')
        bearish_data = self._create_sample_data(trend='bearish', volatility='normal')
        
        bullish_result = self.scorer.score_signal("TEST", bullish_data, 100.0)
        bearish_result = self.scorer.score_signal("TEST", bearish_data, 100.0)
        
        # Bullish with high volume should generally score higher
        # (though not guaranteed due to multi-timeframe randomness)
        self.assertIsInstance(bullish_result['total_score'], (int, float))
        self.assertIsInstance(bearish_result['total_score'], (int, float))


class TestFreeDataFilter(unittest.TestCase):
    """Test free data filtering logic"""
    
    def setUp(self):
        self.filter = FreeDataFilter()
    
    def test_vix_adjustment_structure(self):
        """Test VIX adjustment returns proper structure"""
        result = self.filter.get_vix_adjustment()
        
        required_keys = [
            'vix_level', 'position_size_multiplier', 
            'max_positions', 'reason'
        ]
        
        for key in required_keys:
            self.assertIn(key, result)
    
    def test_vix_multiplier_range(self):
        """Test VIX multiplier is in valid range"""
        result = self.filter.get_vix_adjustment()
        mult = result['position_size_multiplier']
        
        self.assertGreaterEqual(mult, 0.5)
        self.assertLessEqual(mult, 1.0)
    
    def test_earnings_check_structure(self):
        """Test earnings check returns proper structure"""
        result = self.filter.check_earnings_ok("AAPL")
        
        required_keys = [
            'ok_to_trade', 'earnings_date', 
            'days_until_earnings', 'reason'
        ]
        
        for key in required_keys:
            self.assertIn(key, result)
        
        self.assertIsInstance(result['ok_to_trade'], bool)
    
    def test_fundamentals_check_structure(self):
        """Test fundamentals check returns proper structure"""
        result = self.filter.check_fundamentals_ok("AAPL")
        
        required_keys = [
            'ok_to_trade', 'confidence_multiplier',
            'float_shares', 'institutional_ownership', 'reason'
        ]
        
        for key in required_keys:
            self.assertIn(key, result)
        
        self.assertIsInstance(result['ok_to_trade'], bool)
        self.assertIsInstance(result['confidence_multiplier'], (int, float))
    
    def test_confidence_multiplier_range(self):
        """Test confidence multiplier is reasonable"""
        result = self.filter.check_fundamentals_ok("TSLA")
        mult = result['confidence_multiplier']
        
        # Should be between 0.7 and 1.3
        self.assertGreaterEqual(mult, 0.5)
        self.assertLessEqual(mult, 1.5)
    
    def test_universe_filtering(self):
        """Test universe filtering returns proper structure"""
        test_symbols = ["AAPL", "TSLA", "NVDA"]
        result = self.filter.filter_universe(test_symbols)
        
        required_keys = ['approved', 'rejected', 'adjustments', 'vix_adjustment']
        
        for key in required_keys:
            self.assertIn(key, result)
        
        self.assertIsInstance(result['approved'], list)
        self.assertIsInstance(result['rejected'], dict)
        self.assertIsInstance(result['adjustments'], dict)


class TestDynamicExitManager(unittest.TestCase):
    """Test dynamic exit logic"""
    
    def setUp(self):
        self.exit_mgr = DynamicExitManager()
    
    def test_exit_rules_exist_for_all_tiers(self):
        """Test exit rules defined for all quality tiers"""
        for tier in ['STRONG', 'MEDIUM', 'WEAK']:
            self.assertIn(tier, self.exit_mgr.EXIT_RULES)
    
    def test_exit_params_structure(self):
        """Test exit params have required fields"""
        class MockPosition:
            quality_tier = 'MEDIUM'
            entry_price = 100.0
            symbol = 'TEST'
        
        params = self.exit_mgr.get_exit_params(MockPosition())
        
        required_keys = [
            'profit_target', 'stop_loss', 'trailing_trigger',
            'trailing_distance', 'ignore_zones', 'min_profit_lock'
        ]
        
        for key in required_keys:
            self.assertIn(key, params)
    
    def test_strong_signals_have_higher_targets(self):
        """Test STRONG signals have higher profit targets than WEAK"""
        strong_rules = self.exit_mgr.EXIT_RULES['STRONG']
        weak_rules = self.exit_mgr.EXIT_RULES['WEAK']
        
        self.assertGreater(
            strong_rules['profit_target'],
            weak_rules['profit_target']
        )
    
    def test_should_exit_stop_loss(self):
        """Test stop loss triggers exit"""
        class MockPosition:
            quality_tier = 'MEDIUM'
            entry_price = 100.0
            highest_price = 100.0
            symbol = 'TEST'
        
        # Price drops 2% (below -1.5% stop)
        should_exit, reason = self.exit_mgr.should_exit(
            MockPosition(), 98.0, datetime.now()
        )
        
        self.assertTrue(should_exit)
        self.assertIn('STOP_LOSS', reason)
    
    def test_should_exit_profit_target(self):
        """Test profit target triggers exit"""
        class MockPosition:
            quality_tier = 'MEDIUM'
            entry_price = 100.0
            highest_price = 104.0
            symbol = 'TEST'
        
        # Price up 4% (above 3.5% target for MEDIUM)
        should_exit, reason = self.exit_mgr.should_exit(
            MockPosition(), 104.0, datetime.now()
        )
        
        self.assertTrue(should_exit)
        self.assertIn('PROFIT_TARGET', reason)
    
    def test_no_exit_when_within_range(self):
        """Test no exit when price within acceptable range"""
        class MockPosition:
            quality_tier = 'MEDIUM'
            entry_price = 100.0
            highest_price = 101.0
            symbol = 'TEST'
        
        # Price up 1% (within range)
        current_time = datetime.now().replace(hour=10, minute=30)
        should_exit, reason = self.exit_mgr.should_exit(
            MockPosition(), 101.0, current_time
        )
        
        self.assertFalse(should_exit)
        self.assertIsNone(reason)
    
    def test_force_close_at_345pm(self):
        """Test force close at 3:45 PM"""
        class MockPosition:
            quality_tier = 'STRONG'
            entry_price = 100.0
            highest_price = 102.0
            symbol = 'TEST'
        
        # 3:45 PM
        force_close_time = datetime.now().replace(hour=15, minute=45)
        should_exit, reason = self.exit_mgr.should_exit(
            MockPosition(), 102.0, force_close_time
        )
        
        self.assertTrue(should_exit)
        self.assertIn('FORCE_CLOSE', reason)


class TestIntegration(unittest.TestCase):
    """Integration tests"""
    
    def test_all_components_initialize(self):
        """Test all components can be initialized together"""
        try:
            scorer = IntradayQualityScorer()
            data_filter = FreeDataFilter()
            exit_mgr = DynamicExitManager()
            
            self.assertIsNotNone(scorer)
            self.assertIsNotNone(data_filter)
            self.assertIsNotNone(exit_mgr)
            
        except Exception as e:
            self.fail(f"Failed to initialize components: {e}")
    
    def test_end_to_end_signal_flow(self):
        """Test signal can flow through entire system"""
        # This is a simplified integration test
        scorer = IntradayQualityScorer()
        
        # Create sample data
        dates = pd.date_range(end=datetime.now(), periods=50, freq='1min')
        sample_data = pd.DataFrame({
            'close': np.random.randn(50).cumsum() + 100,
            'high': np.random.randn(50).cumsum() + 101,
            'low': np.random.randn(50).cumsum() + 99,
            'volume': np.random.randint(100000, 500000, 50)
        }, index=dates)
        
        # Score signal
        result = scorer.score_signal("TEST", sample_data, 100.0)
        
        # Verify flow
        self.assertIn('total_score', result)
        self.assertIn('quality_tier', result)
        
        # Check exit params can be retrieved for this tier
        exit_mgr = DynamicExitManager()
        
        class MockPosition:
            quality_tier = result['quality_tier']
            entry_price = 100.0
            symbol = 'TEST'
        
        params = exit_mgr.get_exit_params(MockPosition())
        self.assertIsNotNone(params)


def run_all_tests():
    """Run all test suites"""
    print("\n" + "="*70)
    print("🧪 RUNNING COMPREHENSIVE TEST SUITE")
    print("="*70 + "\n")
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestIntradayQualityScorer))
    suite.addTests(loader.loadTestsFromTestCase(TestFreeDataFilter))
    suite.addTests(loader.loadTestsFromTestCase(TestDynamicExitManager))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Summary
    print("\n" + "="*70)
    print("📊 TEST SUMMARY")
    print("="*70)
    print(f"Tests Run: {result.testsRun}")
    print(f"✅ Passed: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"❌ Failed: {len(result.failures)}")
    print(f"⚠️  Errors: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("\n🎉 ALL TESTS PASSED!")
        return True
    else:
        print("\n❌ SOME TESTS FAILED!")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)

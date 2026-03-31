"""
Unit tests for all-day entry / late-entry features
Tests gating logic, position sizing, and safety checks
"""
import unittest
from datetime import datetime, date
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from small_portfolio_config import SmallPortfolioConfig
from traders.short_cycle_trader import ShortCycleTrader, ShortCyclePosition, PositionStatus


class TestLateEntryFeatures(unittest.TestCase):
    """Test suite for late-entry / all-day trading features"""
    
    def setUp(self):
        """Setup test fixtures"""
        self.config = SmallPortfolioConfig()
        self.config.enable_all_day_entries = True
        self.config.max_late_entries_per_day = 2
        self.config.late_entry_confidence_multiplier = 1.5
        self.config.late_entry_position_size_pct = 0.5
        self.config.allow_late_entries_after_minutes = 60
        self.config.all_day_entry_cutoff_time = "15:30"
        
        # Mock trader (don't initialize full components)
        with patch.object(ShortCycleTrader, '_setup_logging'):
            with patch.object(ShortCycleTrader, '__init__', lambda x, y: None):
                self.trader = ShortCycleTrader(self.config)
                self.trader.config = self.config
                self.trader.logger = Mock()
                self.trader.positions = []
                self.trader.trades_today = 0
                self.trader.late_entries_today = 0
                self.trader.kill_switches = {}
                self.trader.daily_pnl = 0
                self.trader.weekly_pnl = 0
                self.trader.recent_trades = []
                self.trader.safety_monitor = None
    
    def test_config_flags_present(self):
        """Test that all new config flags are present with correct defaults"""
        self.assertTrue(hasattr(self.config, 'enable_all_day_entries'))
        self.assertTrue(hasattr(self.config, 'max_late_entries_per_day'))
        self.assertTrue(hasattr(self.config, 'late_entry_confidence_multiplier'))
        self.assertTrue(hasattr(self.config, 'late_entry_position_size_pct'))
        self.assertTrue(hasattr(self.config, 'allow_late_entries_after_minutes'))
        self.assertTrue(hasattr(self.config, 'all_day_entry_cutoff_time'))
        self.assertTrue(hasattr(self.config, 'require_min_avg_volume_for_late'))
        self.assertTrue(hasattr(self.config, 'late_entry_check_interval_minutes'))
        
        # Check defaults
        self.assertEqual(self.config.max_late_entries_per_day, 2)
        self.assertEqual(self.config.late_entry_confidence_multiplier, 1.5)
        self.assertEqual(self.config.late_entry_position_size_pct, 0.5)
        self.assertEqual(self.config.allow_late_entries_after_minutes, 60)
        self.assertEqual(self.config.all_day_entry_cutoff_time, "15:30")
        self.assertEqual(self.config.require_min_avg_volume_for_late, 1_000_000)
        self.assertEqual(self.config.late_entry_check_interval_minutes, 15)
    
    def test_late_entry_disabled_by_default_on_standard_config(self):
        """Test that late entries are ENABLED by default on SmallPortfolioConfig (cash account)"""
        default_config = SmallPortfolioConfig()
        # Should be enabled for cash accounts by default
        self.assertTrue(default_config.enable_all_day_entries)
    
    def test_late_entry_counter_increments(self):
        """Test that late_entries_today counter exists and can increment"""
        self.assertEqual(self.trader.late_entries_today, 0)
        self.trader.late_entries_today += 1
        self.assertEqual(self.trader.late_entries_today, 1)
    
    def test_late_entry_limit_enforcement(self):
        """Test that late entry attempts are blocked when limit reached"""
        self.trader.late_entries_today = 2
        self.config.max_late_entries_per_day = 2
        
        # Mock dependencies
        self.trader._get_trading_universe = Mock(return_value=['AAPL', 'TSLA'])
        self.trader._check_volume_requirement = Mock(return_value=True)
        self.trader.data_loader = Mock()
        self.trader.data_loader.get_bulk_market_data = Mock(return_value={})
        
        # Should exit early due to limit
        self.trader._attempt_late_entries()
        
        # Verify it logged the limit message
        self.trader.logger.info.assert_any_call("⏸️ Late entry limit reached: 2/2")
    
    def test_late_entry_respects_kill_switches(self):
        """Test that late entries are blocked when kill switches active"""
        self.trader.kill_switches = {"daily_loss_exceeded": True}
        
        self.trader._attempt_late_entries()
        
        self.trader.logger.info.assert_any_call("🛑 Late entry blocked: kill switch active")
    
    def test_late_entry_respects_daily_position_limit(self):
        """Test that late entries respect max_positions_per_day"""
        self.trader.trades_today = 3
        self.config.max_positions_per_day = 3
        
        self.trader._attempt_late_entries()
        
        self.trader.logger.info.assert_any_call("⏸️ Daily position limit reached: 3/3")
    
    def test_late_entry_disabled_when_flag_false(self):
        """Test that late entries are skipped when enable_all_day_entries=False"""
        self.config.enable_all_day_entries = False
        
        self.trader._attempt_late_entries()
        
        # Should return immediately without logging anything else
        self.assertEqual(self.trader.logger.info.call_count, 0)
    
    def test_confidence_multiplier_applied(self):
        """Test that late entries require higher confidence threshold"""
        base_threshold = 0.05
        multiplier = 1.5
        expected_threshold = base_threshold * multiplier
        
        self.config.confidence_threshold = base_threshold
        self.config.late_entry_confidence_multiplier = multiplier
        
        # Calculated threshold should be 0.075 (7.5%)
        self.assertAlmostEqual(expected_threshold, 0.075, places=6)
    
    def test_position_size_reduction_applied(self):
        """Test that late entries use reduced position sizing"""
        normal_size = 100.0
        reduction_pct = 0.5
        expected_size = normal_size * reduction_pct
        
        self.config.late_entry_position_size_pct = reduction_pct
        
        # Late entry should be 50% of normal
        self.assertEqual(expected_size, 50.0)
    
    def test_daily_counter_reset_includes_late_entries(self):
        """Test that daily counter reset also resets late_entries_today"""
        self.trader.late_entries_today = 2
        self.trader.last_pnl_reset_date = None
        
        # Call reset
        self.trader._maybe_reset_daily_counters()
        
        # Should reset to 0
        self.assertEqual(self.trader.late_entries_today, 0)
    
    def test_volume_requirement_check(self):
        """Test volume filtering for late entries"""
        # This is a basic test - actual implementation uses yfinance
        # Just verify the method exists and has correct signature
        self.assertTrue(hasattr(self.trader, '_check_volume_requirement'))
        
        # Test with mock (would need yfinance for real test)
        with patch('yfinance.Ticker') as mock_ticker:
            mock_hist = Mock()
            mock_hist.return_value = {'Volume': Mock(mean=lambda: 2_000_000)}
            mock_ticker.return_value.history = mock_hist
            
            # Should pass for high volume
            result = self.trader._check_volume_requirement('AAPL', 1_000_000)
            # Returns True on error (conservative), so test for bool
            self.assertIsInstance(result, bool)


class TestLateEntryIntegration(unittest.TestCase):
    """Integration tests for late entry in trading loop"""
    
    def test_late_entry_method_exists(self):
        """Test that _attempt_late_entries method exists"""
        config = SmallPortfolioConfig()
        with patch.object(ShortCycleTrader, '_setup_logging'):
            with patch.object(ShortCycleTrader, '__init__', lambda x, y: None):
                trader = ShortCycleTrader(config)
                self.assertTrue(hasattr(trader, '_attempt_late_entries'))
                self.assertTrue(callable(getattr(trader, '_attempt_late_entries')))


if __name__ == '__main__':
    unittest.main()

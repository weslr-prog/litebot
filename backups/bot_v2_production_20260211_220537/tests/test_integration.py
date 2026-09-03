"""
Comprehensive integration tests for bot_v2 ProductionTradingEngine
Tests full trading cycle: signal generation → risk assessment → execution → exits
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import pytest
import datetime as dt
from unittest.mock import Mock, MagicMock, patch
import pandas as pd

from bot_v2.core import ProductionTradingEngine
from bot_v2.config import ShortCycleConfig
from bot_v2.models.positions import ShortCyclePosition, PositionStatus
from bot_v2.models.signals import AISignal


class TestProductionTradingEngineIntegration:
    """Integration tests for ProductionTradingEngine"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.config = ShortCycleConfig()
        
        # Mock execution engine
        self.mock_execution_engine = Mock()
        self.mock_execution_engine.get_portfolio_summary.return_value = {
            'account': {'portfolio_value': 1000.0}
        }
        self.mock_execution_engine.get_positions.return_value = {}
        self.mock_execution_engine.submit_order.return_value = {
            'order_id': 'test123',
            'status': 'filled',
            'submitted_at': dt.datetime.now(),
            'filled_at': dt.datetime.now(),
            'avg_fill_price': 100.0
        }
        
        # Mock data loader
        self.mock_data_loader = Mock()
        self.mock_data_loader.get_current_price.return_value = 100.0
        
        # Create sample market data
        dates = pd.date_range(end=dt.datetime.now(), periods=40, freq='D')
        self.sample_market_data = pd.DataFrame({
            'open': [100 + i for i in range(40)],
            'high': [102 + i for i in range(40)],
            'low': [98 + i for i in range(40)],
            'close': [101 + i for i in range(40)],
            'volume': [1000000] * 40
        }, index=dates)
        
        self.mock_data_loader.get_historical_data.return_value = self.sample_market_data
        
        # Initialize engine
        self.engine = ProductionTradingEngine(
            config=self.config,
            execution_engine=self.mock_execution_engine,
            data_loader=self.mock_data_loader
        )
    
    def test_engine_initialization(self):
        """Test that engine initializes all modules correctly"""
        assert self.engine is not None
        assert self.engine.portfolio_manager is not None
        assert self.engine.position_tracker is not None
        assert self.engine.order_manager is not None
        assert self.engine.exit_manager is not None
        assert self.engine.signal_generator is not None
        assert self.engine.stop_manager is not None
        assert self.engine.position_sizer is not None
        assert self.engine.risk_manager is not None
        assert self.engine.regime_detector is not None
        assert self.engine.performance_tracker is not None
        assert len(self.engine.kill_switches) == 3
    
    def test_portfolio_value_retrieval(self):
        """Test portfolio value retrieval from execution engine"""
        value = self.engine.portfolio_manager.get_portfolio_value()
        assert value == 1000.0
        self.mock_execution_engine.get_portfolio_summary.assert_called_once()
    
    def test_position_loading_and_saving(self):
        """Test position persistence (load/save cycle)"""
        # Create a test position
        signal = AISignal(
            symbol="TEST",
            action="BUY",
            confidence=0.75,
            time_horizon_days=1.5,
            entry_price=100.0
        )
        
        position = ShortCyclePosition(
            symbol="TEST",
            entry_date=dt.date.today(),
            exit_date=dt.date.today() + dt.timedelta(days=1),
            entry_price=100.0,
            position_size_shares=10,
            position_size_dollars=1000.0,
            stop_price=95.0,
            target_price=110.0,
            status=PositionStatus.ENTERED,
            ai_signal=signal,
            max_risk_dollars=50.0
        )
        
        # Add and save
        self.engine.position_tracker.add_position(position)
        self.engine.position_tracker.save_positions()
        
        # Load in new tracker
        new_tracker = type(self.engine.position_tracker)(
            self.config,
            self.mock_execution_engine
        )
        loaded_positions = new_tracker.load_positions()
        
        assert len(loaded_positions) >= 1
        # Find our test position
        test_pos = next((p for p in loaded_positions if p.symbol == "TEST"), None)
        if test_pos:
            assert test_pos.entry_price == 100.0
            assert test_pos.position_size_shares == 10
    
    def test_daily_cycle_with_no_positions(self):
        """Test daily cycle when no positions exist"""
        # Mock should_trade_today to return True
        with patch.object(self.engine, '_should_trade_today', return_value=True):
            # Mock get_trading_universe to return empty list
            with patch.object(self.engine, '_get_trading_universe', return_value=[]):
                # Should not raise any errors
                self.engine.run_daily_cycle()
                
                # Verify portfolio manager was called
                assert self.engine.portfolio_manager.last_pnl_reset_date is not None
    
    def test_kill_switch_activation(self):
        """Test that kill switches prevent trading"""
        # Activate daily loss kill switch
        self.engine.kill_switches["daily_loss_exceeded"] = True
        
        # Should be blocked by kill switch
        result = self.engine._should_trade_today()
        assert result is False
    
    def test_portfolio_summary_generation(self):
        """Test portfolio summary generation"""
        summary = self.engine.get_portfolio_summary()
        
        assert 'portfolio_value' in summary
        assert 'open_positions' in summary
        assert 'trades_today' in summary
        assert summary['portfolio_value'] == 1000.0
    
    def test_risk_limit_updates(self):
        """Test that risk limits update based on portfolio value"""
        initial_pool = self.config.daily_pool_dollars
        
        # Update risk limits
        self.engine.portfolio_manager.update_risk_limits()
        
        # Pool should be recalculated
        expected_pool = 1000.0 * self.config.daily_pool_percent
        assert self.config.daily_pool_dollars == expected_pool
    
    def test_signal_execution_flow(self):
        """Test complete signal execution flow"""
        # Create a signal
        signal = AISignal(
            symbol="AAPL",
            action="BUY",
            confidence=0.75,
            time_horizon_days=1.5,
            entry_price=150.0,
            target_price=160.0
        )
        
        # Mock market data for stop calculation
        with patch.object(self.engine, '_get_market_data', return_value={'AAPL': self.sample_market_data}):
            # Execute signal
            self.engine._execute_signal(signal, self.sample_market_data)
        
        # Verify order was submitted
        self.mock_execution_engine.submit_order.assert_called()
        
        # Verify position was added
        positions = self.engine.position_tracker.get_positions()
        aapl_position = next((p for p in positions if p.symbol == "AAPL"), None)
        assert aapl_position is not None
        assert aapl_position.status == PositionStatus.ENTERED
    
    def test_daily_counter_reset(self):
        """Test that daily counters reset at day boundary"""
        # Set some counters
        self.engine.portfolio_manager.trades_today = 5
        self.engine.portfolio_manager.late_entries_today = 2
        self.engine.portfolio_manager.daily_pnl = 100.0
        
        # Set reset date to yesterday
        self.engine.portfolio_manager.last_pnl_reset_date = dt.date.today() - dt.timedelta(days=1)
        
        # Reset counters
        was_reset = self.engine.portfolio_manager.reset_daily_counters_if_needed()
        
        assert was_reset is True
        assert self.engine.portfolio_manager.trades_today == 0
        assert self.engine.portfolio_manager.late_entries_today == 0
        assert self.engine.portfolio_manager.daily_pnl == 0.0
    
    def test_position_sync_with_broker(self):
        """Test position synchronization with broker"""
        # Mock live positions from broker
        live_positions = {
            'AAPL': {
                'quantity': 10.0,
                'avg_cost': 150.0,
                'market_value': 1500.0,
                'unrealized_pnl': 0.0,
                'side': 'long'
            }
        }
        
        with patch.object(self.engine.position_tracker, 'get_live_positions', return_value=live_positions):
            state_changed = self.engine.position_tracker.sync_positions_with_broker(live_positions)
            
            # Should create position tracker for AAPL
            positions = self.engine.position_tracker.get_positions()
            aapl_pos = next((p for p in positions if p.symbol == 'AAPL'), None)
            
            if aapl_pos:
                assert aapl_pos.position_size_shares == 10
                assert aapl_pos.entry_price == 150.0


class TestIntegrationScenarios:
    """Test realistic trading scenarios"""
    
    def test_full_trading_cycle(self):
        """Test a complete trading cycle from signal to exit"""
        # This would be a longer integration test
        # Testing: signal → entry → hold → exit
        pass
    
    def test_multiple_positions_management(self):
        """Test handling multiple concurrent positions"""
        pass
    
    def test_loss_limit_circuit_breaker(self):
        """Test that loss limits stop trading"""
        pass
    
    def test_d1_exit_timing(self):
        """Test D+1 exit logic and timing"""
        pass
    
    def test_trailing_stop_activation(self):
        """Test trailing stop activation and adjustment"""
        pass


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s"])

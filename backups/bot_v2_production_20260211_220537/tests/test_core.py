"""
Unit tests for core trading engine
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from bot_v2.config.trading_config import ShortCycleConfig
from bot_v2.core.trader import SimplifiedTrader


class TestSimplifiedTrader:
    """Test SimplifiedTrader"""
    
    def test_initialization(self):
        """Test trader initialization"""
        trader = SimplifiedTrader()
        
        assert trader.config is not None
        assert trader.signal_generator is not None
        assert trader.stop_manager is not None
        assert trader.position_sizer is not None
        assert trader.risk_manager is not None
        assert trader.regime_detector is not None
        assert len(trader.positions) == 0
        assert trader.daily_pnl == 0.0
        assert trader.trades_today == 0
    
    def test_initialization_with_custom_config(self):
        """Test initialization with custom config"""
        config = ShortCycleConfig(
            portfolio_value=5000.0,
            max_positions_per_day=8
        )
        
        trader = SimplifiedTrader(config)
        
        assert trader.config.portfolio_value == 5000.0
        assert trader.config.max_positions_per_day == 8
    
    def test_get_portfolio_summary_empty(self):
        """Test portfolio summary with no positions"""
        trader = SimplifiedTrader()
        
        summary = trader.get_portfolio_summary()
        
        assert summary["open_positions"] == 0
        assert summary["closed_positions"] == 0
        assert summary["total_positions"] == 0
        assert summary["realized_pnl"] == 0.0
        assert summary["unrealized_pnl"] == 0.0
        assert summary["total_pnl"] == 0.0
        assert summary["trades_today"] == 0
    
    def test_run_trading_cycle_basic(self):
        """Test basic trading cycle execution"""
        config = ShortCycleConfig(
            portfolio_value=1000.0,
            confidence_threshold=0.50,
            max_positions_per_day=5
        )
        trader = SimplifiedTrader(config)
        
        # Create minimal market data
        universe = ["AAPL", "MSFT"]
        market_data = {}
        
        for symbol in universe:
            # Create oversold RSI scenario for signal generation
            dates = pd.date_range(end=datetime.now(), periods=30, freq='D')
            
            # Declining prices to create oversold RSI
            prices = np.linspace(110, 100, 30)  # -9% drop
            
            market_data[symbol] = pd.DataFrame({
                'close': prices,
                'high': prices * 1.01,
                'low': prices * 0.99,
                'volume': [2000000] * 30  # High volume
            }, index=dates)
        
        # Run cycle
        trader.run_trading_cycle(universe, market_data)
        
        # Check that trader attempted to process signals
        # (may or may not generate actual positions depending on signal criteria)
        assert trader.trades_today >= 0
        assert trader.trades_today <= config.max_positions_per_day
    
    def test_process_exits_empty(self):
        """Test process exits with no positions"""
        trader = SimplifiedTrader()
        
        current_prices = {"AAPL": 150.0, "MSFT": 350.0}
        
        # Should not crash with no positions
        trader.process_exits(current_prices)
        
        assert len(trader.positions) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

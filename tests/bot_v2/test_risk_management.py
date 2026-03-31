"""
Unit tests for risk management modules
"""

import pytest
import pandas as pd
from datetime import datetime

from bot_v2.config.trading_config import ShortCycleConfig
from bot_v2.models.signals import AISignal
from bot_v2.models.positions import ShortCyclePosition, PositionStatus
from bot_v2.risk_management import (
    AIStopLossManager,
    AIConfidencePositionSizer,
    AIPredictiveRiskManager
)


class TestAIStopLossManager:
    """Test AIStopLossManager"""
    
    def test_initialization(self):
        """Test stop loss manager initialization"""
        config = ShortCycleConfig(portfolio_value=1000.0)
        manager = AIStopLossManager(config)
        
        assert manager.config == config
        assert manager.max_stop_percent == 0.06
        assert manager.fast_exit_threshold == 0.015
        assert manager.atr_multiplier == 2.0
    
    def test_calculate_optimal_stop_fallback(self):
        """Test stop calculation with empty market data (fallback)"""
        config = ShortCycleConfig(portfolio_value=1000.0)
        manager = AIStopLossManager(config)
        
        signal = AISignal(
            symbol="AAPL",
            action="BUY",
            confidence=0.75,
            time_horizon_days=3.0,
            entry_price=100.0,
            signal_timestamp=datetime.now()
        )
        
        # Empty DataFrame should trigger fallback
        market_data = pd.DataFrame()
        stop_price, stop_pct = manager.calculate_optimal_stop(signal, market_data)
        
        assert stop_pct == 0.04  # default stop_loss_pct
        assert stop_price == 96.0  # 100 * (1 - 0.04)
    
    def test_should_fast_exit_loss_limit(self):
        """Test fast exit when max loss limit is hit"""
        config = ShortCycleConfig(portfolio_value=1000.0, max_loss_per_trade_dollars=20.0)
        manager = AIStopLossManager(config)
        
        position = ShortCyclePosition(
            symbol="AAPL",
            entry_date=datetime.now().date(),
            exit_date=(datetime.now().date()),
            entry_price=100.0,
            position_size_shares=10,
            position_size_dollars=1000.0,
            stop_price=98.0,
            target_price=None,
            status=PositionStatus.ENTERED,
            ai_signal=AISignal(
                symbol="AAPL",
                action="BUY",
                confidence=0.75,
                time_horizon_days=3.0,
                entry_price=100.0,
                signal_timestamp=datetime.now()
            )
        )
        
        # Current price down $2.50/share = $25 loss (exceeds $20 limit)
        current_price = 97.5
        
        assert manager.should_fast_exit(position, current_price) is True
    
    def test_should_fast_exit_threshold(self):
        """Test fast exit when threshold is exceeded"""
        config = ShortCycleConfig(portfolio_value=1000.0)
        manager = AIStopLossManager(config)
        
        position = ShortCyclePosition(
            symbol="AAPL",
            entry_date=datetime.now().date(),
            exit_date=(datetime.now().date()),
            entry_price=100.0,
            position_size_shares=1,
            position_size_dollars=100.0,
            stop_price=98.0,
            target_price=None,
            status=PositionStatus.ENTERED,
            ai_signal=AISignal(
                symbol="AAPL",
                action="BUY",
                confidence=0.75,
                time_horizon_days=3.0,
                entry_price=100.0,
                signal_timestamp=datetime.now()
            )
        )
        
        # Price down 1.6% (exceeds 1.5% threshold)
        current_price = 98.4
        
        assert manager.should_fast_exit(position, current_price) is True
    
    def test_should_not_fast_exit_small_loss(self):
        """Test no fast exit for small loss"""
        config = ShortCycleConfig(portfolio_value=1000.0)
        manager = AIStopLossManager(config)
        
        position = ShortCyclePosition(
            symbol="AAPL",
            entry_date=datetime.now().date(),
            exit_date=(datetime.now().date()),
            entry_price=100.0,
            position_size_shares=1,
            position_size_dollars=100.0,
            stop_price=98.0,
            target_price=None,
            status=PositionStatus.ENTERED,
            ai_signal=AISignal(
                symbol="AAPL",
                action="BUY",
                confidence=0.75,
                time_horizon_days=3.0,
                entry_price=100.0,
                signal_timestamp=datetime.now()
            )
        )
        
        # Price down 1.0% (below 1.5% threshold)
        current_price = 99.0
        
        assert manager.should_fast_exit(position, current_price) is False


class TestAIConfidencePositionSizer:
    """Test AIConfidencePositionSizer"""
    
    def test_initialization(self):
        """Test position sizer initialization"""
        config = ShortCycleConfig(portfolio_value=1000.0)
        sizer = AIConfidencePositionSizer(config)
        
        assert sizer.config == config
        assert sizer._vix_multiplier is None
        assert sizer._vix_fetch_time is None
    
    def test_calculate_position_size_high_confidence(self):
        """Test position sizing with high confidence signal"""
        config = ShortCycleConfig(portfolio_value=1000.0, max_risk_per_trade_dollars=20.0)
        sizer = AIConfidencePositionSizer(config)
        
        signal = AISignal(
            symbol="AAPL",
            action="BUY",
            confidence=0.80,  # High confidence
            time_horizon_days=3.0,
            entry_price=100.0,
            signal_timestamp=datetime.now()
        )
        
        stop_price = 97.5  # 2.5% stop
        portfolio_value = 1000.0
        
        shares, position_value = sizer.calculate_position_size(
            signal, stop_price, portfolio_value
        )
        
        # High confidence should result in larger position
        assert shares > 0
        assert position_value > 0
        assert position_value <= config.max_position_dollars
    
    def test_calculate_position_size_invalid_prices(self):
        """Test position sizing rejects invalid prices"""
        config = ShortCycleConfig(portfolio_value=1000.0)
        sizer = AIConfidencePositionSizer(config)
        
        signal = AISignal(
            symbol="AAPL",
            action="BUY",
            confidence=0.75,
            time_horizon_days=3.0,
            entry_price=100.0,
            signal_timestamp=datetime.now()
        )
        
        # Stop price higher than entry (invalid)
        stop_price = 105.0
        portfolio_value = 1000.0
        
        shares, position_value = sizer.calculate_position_size(
            signal, stop_price, portfolio_value
        )
        
        assert shares == 0
        assert position_value == 0.0


class TestAIPredictiveRiskManager:
    """Test AIPredictiveRiskManager"""
    
    def test_initialization(self):
        """Test risk manager initialization"""
        config = ShortCycleConfig(portfolio_value=1000.0)
        manager = AIPredictiveRiskManager(config)
        
        assert manager.config == config
        assert manager.max_correlation == 0.7
        assert manager.volatility_spike_threshold == 1.5
    
    def test_assess_portfolio_risk_approved(self):
        """Test portfolio risk assessment approves valid trades"""
        config = ShortCycleConfig(portfolio_value=1000.0)
        manager = AIPredictiveRiskManager(config)
        
        signals = [
            AISignal(
                symbol="AAPL",
                action="BUY",
                confidence=0.75,
                time_horizon_days=3.0,
                entry_price=100.0,
                signal_timestamp=datetime.now()
            )
        ]
        positions = []
        market_data = {}
        
        assessment = manager.assess_portfolio_risk(signals, positions, market_data)
        
        assert assessment["approved"] is True
        assert assessment["risk_score"] >= 0.0
        assert isinstance(assessment["warnings"], list)
        assert isinstance(assessment["vetoed_signals"], list)
    
    def test_assess_portfolio_risk_high_concentration(self):
        """Test portfolio risk warns on high sector concentration"""
        config = ShortCycleConfig(portfolio_value=1000.0)
        manager = AIPredictiveRiskManager(config)
        
        # All tech stocks (high concentration)
        signals = [
            AISignal(
                symbol="AAPL",
                action="BUY",
                confidence=0.75,
                time_horizon_days=3.0,
                entry_price=100.0,
                signal_timestamp=datetime.now()
            ),
            AISignal(
                symbol="MSFT",
                action="BUY",
                confidence=0.75,
                time_horizon_days=3.0,
                entry_price=100.0,
                signal_timestamp=datetime.now()
            )
        ]
        positions = []
        market_data = {}
        
        assessment = manager.assess_portfolio_risk(signals, positions, market_data)
        
        # Should have concentration warning
        assert len(assessment["warnings"]) > 0
        assert assessment["risk_score"] > 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

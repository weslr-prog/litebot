"""
Unit tests for data models
"""

import pytest
from datetime import datetime
import pytz

from bot_v2.models.enums import TradingDay, PositionStatus
from bot_v2.models.signals import AISignal


class TestEnums:
    """Test enum types"""
    
    def test_trading_day_enum(self):
        assert TradingDay.MONDAY.value == "monday"
        assert TradingDay.FRIDAY.value == "friday"
    
    def test_position_status_enum(self):
        assert PositionStatus.PENDING.value == "pending"
        assert PositionStatus.EXITED.value == "exited"


class TestAISignal:
    """Test AISignal model"""
    
    def test_signal_creation(self):
        signal = AISignal(
            symbol="AAPL",
            action="BUY",
            confidence=0.75,
            time_horizon_days=1.0,
            entry_price=150.0
        )
        
        assert signal.symbol == "AAPL"
        assert signal.action == "BUY"
        assert signal.confidence == 0.75
        assert signal.entry_price == 150.0
    
    def test_signal_defaults(self):
        signal = AISignal(
            symbol="MSFT",
            action="BUY",
            confidence=0.60,
            time_horizon_days=2.0
        )
        
        # Should auto-set timestamp
        assert signal.signal_timestamp is not None
        assert signal.features_used == {}
        assert signal.risk_score == 0.5
    
    def test_signal_with_features(self):
        signal = AISignal(
            symbol="TSLA",
            action="BUY",
            confidence=0.80,
            time_horizon_days=1.0,
            features_used={"rsi": 65.0, "volume_surge": 1.5}
        )
        
        assert signal.features_used["rsi"] == 65.0
        assert signal.features_used["volume_surge"] == 1.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

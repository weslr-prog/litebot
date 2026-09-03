"""
Unit tests for configuration module
"""

import pytest
from bot_v2.config.trading_config import ShortCycleConfig


class TestShortCycleConfig:
    """Test ShortCycleConfig model"""
    
    def test_default_config(self):
        """Test default configuration values"""
        config = ShortCycleConfig(portfolio_value=1000.0)
        
        # Portfolio parameters
        assert config.portfolio_value == 1000.0
        assert config.daily_pool_percent == 0.30
        assert config.max_position_dollars == 150.0
        assert config.confidence_threshold == 0.25
        
        # Verify derived values calculated
        assert config.daily_pool_dollars == 300.0  # 1000 * 0.30
        assert config.max_daily_loss_dollars == 80.0  # 1000 * 0.08
        assert config.max_weekly_loss_dollars == 150.0  # 1000 * 0.15
    
    def test_custom_config(self):
        """Test custom configuration"""
        config = ShortCycleConfig(
            portfolio_value=5000.0,
            daily_pool_percent=0.30,
            confidence_threshold=0.50
        )
        
        assert config.portfolio_value == 5000.0
        assert config.daily_pool_percent == 0.30
        assert config.confidence_threshold == 0.50
        
        # Check derived values
        assert config.daily_pool_dollars == 1500.0  # 5000 * 0.30
    
    def test_trading_days_default(self):
        """Test that trading_days gets populated in __post_init__"""
        config = ShortCycleConfig(portfolio_value=1000.0)
        
        assert config.trading_days is not None
        assert len(config.trading_days) == 4
        assert "monday" in config.trading_days
        assert "thursday" in config.trading_days
        assert "friday" not in config.trading_days  # Friday is exit-only
    
    def test_validation_valid_config(self):
        """Test validation passes for valid config"""
        config = ShortCycleConfig(portfolio_value=1000.0)
        assert config.validate() is True
    
    def test_validation_invalid_portfolio(self):
        """Test validation fails for invalid portfolio value"""
        config = ShortCycleConfig(portfolio_value=-100)
        
        with pytest.raises(ValueError, match="portfolio_value must be positive"):
            config.validate()
    
    def test_validation_invalid_confidence(self):
        """Test validation fails for invalid confidence threshold"""
        config = ShortCycleConfig(portfolio_value=1000.0, confidence_threshold=1.5)
        
        with pytest.raises(ValueError, match="confidence_threshold must be between 0 and 1"):
            config.validate()
    
    def test_validation_invalid_position_size(self):
        """Test validation fails when min > max position size"""
        config = ShortCycleConfig(
            portfolio_value=1000.0,
            min_position_size_dollars=300.0,
            max_position_dollars=200.0
        )
        
        with pytest.raises(ValueError, match="min_position_size_dollars cannot exceed max_position_dollars"):
            config.validate()
    
    def test_option3_parameters(self):
        """Test Option 3 specific parameters are set correctly"""
        config = ShortCycleConfig(portfolio_value=1000.0)
        
        # Option 3: Triple frequency + 60% win rate
        assert config.max_positions_per_day == 5
        assert config.confidence_threshold == 0.25
        assert config.portfolio_value == 1000.0
        assert config.max_position_dollars == 150.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

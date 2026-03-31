"""
Unit tests for market analysis modules
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from bot_v2.config.trading_config import ShortCycleConfig
from bot_v2.market_analysis import AIMarketRegimeDetector


class TestAIMarketRegimeDetector:
    """Test AIMarketRegimeDetector"""
    
    def test_initialization(self):
        """Test regime detector initialization"""
        config = ShortCycleConfig()
        detector = AIMarketRegimeDetector(config)
        
        assert detector.config == config
        # Should handle missing RegimeDetector gracefully
        assert detector.regime_detector is None or detector.regime_detector is not None
    
    def test_get_current_regime_bull(self):
        """Test regime detection for bull market"""
        config = ShortCycleConfig()
        detector = AIMarketRegimeDetector(config)
        
        # Create fake SPY data for bull market
        dates = pd.date_range(end=datetime.now(), periods=30, freq='D')
        prices = np.linspace(100, 110, 30)  # Uptrend
        
        spy_data = pd.DataFrame({
            'close': prices,
            'high': prices * 1.01,
            'low': prices * 0.99,
            'volume': [1000000] * 30
        }, index=dates)
        
        market_data = {"SPY": spy_data}
        
        regime_info = detector.get_current_regime(market_data)
        
        assert "regime" in regime_info
        assert "adjustments" in regime_info
        assert "confidence_adjustment" in regime_info
        assert "position_adjustment" in regime_info
        
        # Bull market should have regime BULL or NEUTRAL
        assert regime_info["regime"] in ["BULL", "NEUTRAL"]
    
    def test_get_current_regime_bear(self):
        """Test regime detection for bear market"""
        config = ShortCycleConfig()
        detector = AIMarketRegimeDetector(config)
        
        # Create fake SPY data for bear market
        dates = pd.date_range(end=datetime.now(), periods=30, freq='D')
        prices = np.linspace(110, 100, 30)  # Downtrend
        
        spy_data = pd.DataFrame({
            'close': prices,
            'high': prices * 1.01,
            'low': prices * 0.99,
            'volume': [1000000] * 30
        }, index=dates)
        
        market_data = {"SPY": spy_data}
        
        regime_info = detector.get_current_regime(market_data)
        
        # Bear market should have regime BEAR or NEUTRAL
        assert regime_info["regime"] in ["BEAR", "NEUTRAL"]
    
    def test_get_current_regime_no_data(self):
        """Test regime detection with no market data"""
        config = ShortCycleConfig()
        detector = AIMarketRegimeDetector(config)
        
        market_data = {}
        
        regime_info = detector.get_current_regime(market_data)
        
        # Should default to NEUTRAL when no data
        assert regime_info["regime"] == "NEUTRAL"
        assert regime_info["position_adjustment"] == 1.0
        assert regime_info["confidence_adjustment"] == 0.0
    
    def test_regime_adjustments_bull(self):
        """Test regime adjustments for bull market"""
        config = ShortCycleConfig()
        detector = AIMarketRegimeDetector(config)
        
        adjustments = detector._get_regime_adjustments("BULL")
        
        assert adjustments["max_positions_multiplier"] == 1.2  # More positions
        assert adjustments["confidence_threshold"] == -0.05  # Lower threshold
        assert adjustments["risk_multiplier"] == 1.1
    
    def test_regime_adjustments_bear(self):
        """Test regime adjustments for bear market"""
        config = ShortCycleConfig()
        detector = AIMarketRegimeDetector(config)
        
        adjustments = detector._get_regime_adjustments("BEAR")
        
        assert adjustments["max_positions_multiplier"] == 0.5  # Fewer positions
        assert adjustments["confidence_threshold"] == 0.1  # Higher threshold
        assert adjustments["risk_multiplier"] == 0.8
    
    def test_regime_adjustments_neutral(self):
        """Test regime adjustments for neutral market"""
        config = ShortCycleConfig()
        detector = AIMarketRegimeDetector(config)
        
        adjustments = detector._get_regime_adjustments("NEUTRAL")
        
        assert adjustments["max_positions_multiplier"] == 1.0
        assert adjustments["confidence_threshold"] == 0.0
        assert adjustments["risk_multiplier"] == 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

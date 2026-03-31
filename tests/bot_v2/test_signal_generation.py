"""
Unit tests for signal generation modules
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from bot_v2.config.trading_config import ShortCycleConfig
from bot_v2.models.signals import AISignal
from bot_v2.models.positions import ShortCyclePosition, PositionStatus
from bot_v2.signal_generation import AISignalGenerator


class TestAISignalGenerator:
    """Test AISignalGenerator"""
    
    def test_initialization(self):
        """Test signal generator initialization"""
        config = ShortCycleConfig(portfolio_value=1000.0)
        generator = AISignalGenerator(config)
        
        assert generator.config == config
        assert generator.momentum_lookback == 4
        assert generator.volume_threshold == 1.0
        assert generator.model is None  # Sprint 0 placeholder
        assert generator.feature_pipeline is None  # Sprint 0 placeholder
    
    def test_initialization_with_price_fetcher(self):
        """Test initialization with custom price fetcher"""
        config = ShortCycleConfig(portfolio_value=1000.0)
        
        def mock_price_fetcher(symbol):
            return 100.0
        
        generator = AISignalGenerator(config, price_fetcher=mock_price_fetcher)
        
        assert generator.price_fetcher is not None
        assert generator.price_fetcher("AAPL") == 100.0
    
    def test_validate_entry_candidates_filters_active_positions(self):
        """Test that active positions are filtered from candidates"""
        config = ShortCycleConfig(portfolio_value=1000.0)
        generator = AISignalGenerator(config)
        
        # Active position in AAPL
        test_signal = AISignal(
            symbol="AAPL",
            action="BUY", 
            confidence=0.75,
            time_horizon_days=3.0,
            entry_price=100.0,
            signal_timestamp=datetime.now()
        )
        
        active_positions = [
            ShortCyclePosition(
                symbol="AAPL",
                entry_date=datetime.now().date(),
                exit_date=(datetime.now() + timedelta(days=3)).date(),
                entry_price=100.0,
                position_size_shares=10,
                position_size_dollars=1000.0,
                stop_price=95.0,
                target_price=105.0,
                ai_signal=test_signal,
                status=PositionStatus.ENTERED
            )
        ]
        
        candidates = ["AAPL", "MSFT", "GOOGL"]
        
        validated = generator._validate_entry_candidates(candidates, active_positions)
        
        # AAPL should be filtered out (D+1 rule)
        assert "AAPL" not in validated
        assert "MSFT" in validated
        assert "GOOGL" in validated
    
    def test_validate_entry_candidates_case_insensitive(self):
        """Test that validation is case-insensitive"""
        config = ShortCycleConfig(portfolio_value=1000.0)
        generator = AISignalGenerator(config)
        
        test_signal = AISignal(
            symbol="aapl",
            action="BUY",
            confidence=0.75,
            time_horizon_days=3.0,
            entry_price=100.0,
            signal_timestamp=datetime.now()
        )
        
        active_positions = [
            ShortCyclePosition(
                symbol="aapl",  # lowercase
                entry_date=datetime.now().date(),
                exit_date=(datetime.now() + timedelta(days=3)).date(),
                entry_price=100.0,
                position_size_shares=10,
                position_size_dollars=1000.0,
                stop_price=95.0,
                target_price=105.0,
                ai_signal=test_signal,
                status=PositionStatus.ENTERED
            )
        ]
        
        candidates = ["AAPL", "MSFT"]  # uppercase
        
        validated = generator._validate_entry_candidates(candidates, active_positions)
        
        # AAPL should still be filtered (case-insensitive)
        assert "AAPL" not in validated
        assert "MSFT" in validated
    
    def test_generate_signal_skips_active_positions(self):
        """Test that generate_signal skips symbols with active positions"""
        config = ShortCycleConfig(portfolio_value=1000.0)
        generator = AISignalGenerator(config)
        
        test_signal = AISignal(
            symbol="AAPL",
            action="BUY",
            confidence=0.75,
            time_horizon_days=3.0,
            entry_price=100.0,
            signal_timestamp=datetime.now()
        )
        
        # Active position
        current_positions = [
            ShortCyclePosition(
                symbol="AAPL",
                entry_date=datetime.now().date(),
                exit_date=(datetime.now() + timedelta(days=3)).date(),
                entry_price=100.0,
                position_size_shares=10,
                position_size_dollars=1000.0,
                stop_price=95.0,
                target_price=105.0,
                ai_signal=test_signal,
                status=PositionStatus.ENTERED
            )
        ]
        
        # Try to generate signal for AAPL (should be skipped)
        market_data = pd.DataFrame({
            'close': [100.0] * 30,
            'high': [101.0] * 30,
            'low': [99.0] * 30,
            'volume': [1000000] * 30
        })
        
        signal = generator.generate_signal("AAPL", market_data, current_positions)
        
        # Should return None (active position exists)
        assert signal is None
    
    def test_analyze_symbol_insufficient_data(self):
        """Test that analyze_symbol returns None with insufficient data"""
        config = ShortCycleConfig(portfolio_value=1000.0)
        generator = AISignalGenerator(config)
        
        # Only 3 rows (need at least momentum_lookback + 1 = 5)
        short_data = pd.DataFrame({
            'close': [100.0, 101.0, 102.0],
            'high': [101.0, 102.0, 103.0],
            'low': [99.0, 100.0, 101.0],
            'volume': [1000000, 1100000, 1200000]
        })
        
        signal = generator._analyze_symbol("AAPL", short_data)
        
        assert signal is None
    
    def test_analyze_symbol_none_data(self):
        """Test that analyze_symbol handles None data gracefully"""
        config = ShortCycleConfig(portfolio_value=1000.0)
        generator = AISignalGenerator(config)
        
        signal = generator._analyze_symbol("AAPL", None)
        
        assert signal is None
    
    def test_generate_signals_sorts_by_confidence(self):
        """Test that generate_signals sorts by confidence and limits results"""
        config = ShortCycleConfig(portfolio_value=1000.0, max_positions_per_day=2, confidence_threshold=0.50)
        generator = AISignalGenerator(config)
        
        # Mock _analyze_symbol_with_reason to return signals with different confidence
        def mock_analyze(symbol, data):
            if symbol == "AAPL":
                signal = AISignal("AAPL", "BUY", 0.90, 3.0, entry_price=100.0, signal_timestamp=datetime.now())
                return (signal, None, signal.confidence)
            if symbol == "MSFT":
                signal = AISignal("MSFT", "BUY", 0.80, 3.0, entry_price=200.0, signal_timestamp=datetime.now())
                return (signal, None, signal.confidence)
            if symbol == "GOOGL":
                signal = AISignal("GOOGL", "BUY", 0.70, 3.0, entry_price=150.0, signal_timestamp=datetime.now())
                return (signal, None, signal.confidence)
            return (None, "No signal", 0.0)
        
        generator._analyze_symbol_with_reason = mock_analyze
        
        universe = ["AAPL", "MSFT", "GOOGL"]
        market_data = {sym: pd.DataFrame() for sym in universe}
        
        signals = generator.generate_signals(universe, market_data, [])
        
        # Should return top 2 by confidence
        assert len(signals) == 2
        assert signals[0].symbol == "AAPL"  # Highest confidence (0.90)
        assert signals[1].symbol == "MSFT"  # Second highest (0.80)
    
    def test_generate_signals_filters_low_confidence(self):
        """Test that signals below confidence threshold are filtered"""
        config = ShortCycleConfig(portfolio_value=1000.0, confidence_threshold=0.80)
        generator = AISignalGenerator(config)
        
        # Mock _analyze_symbol_with_reason
        def mock_analyze(symbol, data):
            if symbol == "AAPL":
                signal = AISignal("AAPL", "BUY", 0.85, 3.0, entry_price=100.0, signal_timestamp=datetime.now())
                return (signal, None, signal.confidence)  # Above threshold
            if symbol == "MSFT":
                signal = AISignal("MSFT", "BUY", 0.75, 3.0, entry_price=200.0, signal_timestamp=datetime.now())
                return (signal, None, signal.confidence)  # Below threshold
            return (None, "No signal", 0.0)
        
        generator._analyze_symbol_with_reason = mock_analyze
        
        universe = ["AAPL", "MSFT"]
        market_data = {sym: pd.DataFrame() for sym in universe}
        
        signals = generator.generate_signals(universe, market_data, [])
        
        # Only AAPL should pass (0.85 >= 0.80)
        assert len(signals) == 1
        assert signals[0].symbol == "AAPL"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

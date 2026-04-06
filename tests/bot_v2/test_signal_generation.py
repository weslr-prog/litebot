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
import bot_v2.signal_generation.signal_generator as signal_generator_module


class FixedDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 3, 31, 11, 0, 0)


class FixedDateTime1015(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 3, 31, 10, 15, 0)


class FixedDateTime0950(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 3, 31, 9, 50, 0)


class FixedDateTime0934(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 3, 31, 9, 34, 0)


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

    def test_check_momentum_requires_support_reversal_and_volume_confirmation(self, monkeypatch):
        config = ShortCycleConfig(portfolio_value=1000.0, confidence_threshold=0.35)
        generator = AISignalGenerator(config)
        monkeypatch.setattr(signal_generator_module, "datetime", FixedDateTime)

        close = [100.0, 100.4, 100.8, 101.3, 101.9, 102.5, 103.1, 103.7, 104.2, 104.8,
                 105.3, 105.8, 106.2, 106.7, 107.1, 107.6, 108.0, 108.4, 108.9, 109.3,
                 106.4, 107.2, 106.8, 108.4, 109.0]
        open_ = [price - 0.2 for price in close]
        high = [price + 1.0 for price in close]
        low = [price - 1.8 for price in close]
        volume = [1_000_000] * 20 + [760_000, 700_000, 650_000, 1_120_000, 1_180_000]
        data = pd.DataFrame({"open": open_, "high": high, "low": low, "close": close, "volume": volume})

        result = generator._check_momentum("AAPL", data, current_rsi=56.0)

        assert result is not None
        assert result["support_name"] in {"ema9", "ema20", "sma20", "swing_low"}
        assert result["pullback_volume_ratio"] < 1.0
        assert result["bounce_volume_ratio"] >= config.momentum_bounce_volume_min_ratio
        assert result["extension_pct"] <= config.momentum_extension_reject_pct

    def test_check_swing_pullback_rejects_missing_bounce_volume(self, monkeypatch):
        config = ShortCycleConfig(portfolio_value=1000.0, confidence_threshold=0.35)
        generator = AISignalGenerator(config)
        monkeypatch.setattr(signal_generator_module, "datetime", FixedDateTime)

        close = [100.0, 100.2, 100.1, 100.3, 100.0, 100.1, 99.9, 100.0, 99.8, 100.1,
                 99.9, 100.0, 100.2, 99.8, 100.0, 99.7, 99.8, 99.4, 99.1, 98.8,
                 98.4, 98.0, 97.7, 97.9, 98.2]
        open_ = [price - 0.1 for price in close]
        high = [price + 1.0 for price in close]
        low = [price - 1.8 for price in close]
        volume = [900_000] * 20 + [820_000, 780_000, 740_000, 760_000, 780_000]
        data = pd.DataFrame({"open": open_, "high": high, "low": low, "close": close, "volume": volume})

        result = generator._check_swing_pullback("AAPL", data, current_rsi=45.0)

        assert result is None

    def test_momentum_signal_uses_support_aware_stop(self, monkeypatch):
        """
        Phase 2: when a support level is identified at entry, the signal stop_price
        should be placed just below that support level rather than a flat percentage.
        """
        config = ShortCycleConfig(portfolio_value=1000.0, confidence_threshold=0.35)
        generator = AISignalGenerator(config)
        monkeypatch.setattr(signal_generator_module, "datetime", FixedDateTime)

        close = [100.0, 100.4, 100.8, 101.3, 101.9, 102.5, 103.1, 103.7, 104.2, 104.8,
                 105.3, 105.8, 106.2, 106.7, 107.1, 107.6, 108.0, 108.4, 108.9, 109.3,
                 106.4, 107.2, 106.8, 108.4, 109.0]
        open_ = [price - 0.2 for price in close]
        high = [price + 1.0 for price in close]
        low = [price - 1.8 for price in close]
        volume = [1_000_000] * 20 + [760_000, 700_000, 650_000, 1_120_000, 1_180_000]
        data = pd.DataFrame({"open": open_, "high": high, "low": low, "close": close, "volume": volume})

        result = generator._check_momentum("AAPL", data, current_rsi=56.0)
        assert result is not None, "Fixture must produce a valid momentum signal"
        assert 'support_price' in result
        sp = result['support_price']
        assert sp > 0

        # Verify the support_price produces a tighter stop than the flat % stop
        entry_price = close[-1]  # 109.0
        buffer = getattr(config, 'support_stop_buffer_pct', 0.01)
        support_stop = sp * (1 - buffer)
        flat_stop = entry_price * (1 - config.stop_loss_pct)

        # Support-aware stop should be above the flat-% floor when near support
        # (it provides a tighter, more precise stop placement)
        assert support_stop > flat_stop, (
            f"Support stop {support_stop:.2f} should be above flat stop {flat_stop:.2f} "
            f"when entry is near support (support={sp:.2f}, entry={entry_price:.2f})"
        )
        assert support_stop < entry_price, (
            f"Support stop {support_stop:.2f} must be below entry {entry_price:.2f}"
        )

    def test_check_momentum_uses_configured_scan_window(self, monkeypatch):
        config = ShortCycleConfig(portfolio_value=1000.0, confidence_threshold=0.35)
        generator = AISignalGenerator(config)
        monkeypatch.setattr(signal_generator_module, "datetime", FixedDateTime1015)

        close = [100.0, 100.4, 100.8, 101.3, 101.9, 102.5, 103.1, 103.7, 104.2, 104.8,
                 105.3, 105.8, 106.2, 106.7, 107.1, 107.6, 108.0, 108.4, 108.9, 109.3,
                 106.4, 107.2, 106.8, 108.4, 109.0]
        open_ = [price - 0.2 for price in close]
        high = [price + 1.0 for price in close]
        low = [price - 1.8 for price in close]
        volume = [1_000_000] * 20 + [760_000, 700_000, 650_000, 1_120_000, 1_180_000]
        data = pd.DataFrame({"open": open_, "high": high, "low": low, "close": close, "volume": volume})

        config.momentum_scan_start = "10:30"
        config.momentum_scan_end = "14:30"
        result_blocked = generator._check_momentum("AAPL", data, current_rsi=56.0)
        assert result_blocked is None

        config.momentum_scan_start = "09:35"
        result_allowed = generator._check_momentum("AAPL", data, current_rsi=56.0)
        assert result_allowed is not None

    def test_check_momentum_applies_ema_tolerance_in_trend_structure(self, monkeypatch):
        config = ShortCycleConfig(portfolio_value=1000.0, confidence_threshold=0.35)
        config.momentum_scan_start = "09:35"
        config.momentum_scan_end = "14:30"
        config.momentum_sma_period = 1
        config.momentum_min_volume_ratio = 1.0
        config.momentum_min_adr_pct = 0.01
        config.momentum_min_5d_return = -0.10
        config.momentum_max_5d_return = 0.20
        generator = AISignalGenerator(config)
        monkeypatch.setattr(signal_generator_module, "datetime", FixedDateTime1015)

        # Isolate trend_structure gate behavior.
        monkeypatch.setattr(generator, "_build_support_context", lambda *_args, **_kwargs: {
            "near_support": True,
            "near_ema": True,
            "support_price": 120.0,
            "support_distance": 0.01,
            "support_name": "ema20",
            "sma20": 112.0,
        })
        monkeypatch.setattr(generator, "_check_pullback_volume_contraction", lambda *_args, **_kwargs: {"passed": True, "ratio": 0.9})
        monkeypatch.setattr(generator, "_check_reversal_confirmation", lambda *_args, **_kwargs: {"passed": True, "close_location": 0.65})
        monkeypatch.setattr(generator, "_check_bounce_volume_expansion", lambda *_args, **_kwargs: {"passed": True, "ratio": 1.2})
        monkeypatch.setattr(generator, "_check_extension_from_support", lambda *_args, **_kwargs: {"passed": True, "extension_pct": 0.01})

        close = [145, 145, 145, 145, 145, 145, 145, 145, 145, 145,
             145, 145, 145, 145, 145, 145, 145, 145, 145, 145,
             146, 147, 148, 149, 144]
        open_ = [c - 0.3 for c in close]
        high = [c + 1.0 for c in close]
        low = [c - 1.0 for c in close]
        volume = [1_200_000] * len(close)
        data = pd.DataFrame({"open": open_, "high": high, "low": low, "close": close, "volume": volume})

        config.momentum_ema_break_tolerance_pct = 0.0
        rejected = generator._check_momentum("AAPL", data, current_rsi=56.0)
        assert rejected is None

        config.momentum_ema_break_tolerance_pct = 0.02
        accepted = generator._check_momentum("AAPL", data, current_rsi=56.0)
        assert accepted is not None

    def test_check_swing_pullback_uses_configured_scan_window(self, monkeypatch):
        config = ShortCycleConfig(portfolio_value=1000.0, confidence_threshold=0.35)
        generator = AISignalGenerator(config)

        close = [100.0, 100.2, 100.1, 100.3, 100.0, 100.1, 99.9, 100.0, 99.8, 100.1,
                 99.9, 100.0, 100.2, 99.8, 100.0, 99.7, 99.8, 99.4, 99.1, 98.8,
                 98.4, 98.0, 97.7, 97.9, 98.2]
        open_ = [price - 0.1 for price in close]
        high = [price + 1.0 for price in close]
        low = [price - 1.8 for price in close]
        volume = [900_000] * 20 + [820_000, 780_000, 740_000, 760_000, 780_000]
        data = pd.DataFrame({"open": open_, "high": high, "low": low, "close": close, "volume": volume})

        config.swing_pullback_scan_start = "09:35"
        config.swing_pullback_scan_end = "14:30"

        monkeypatch.setattr(signal_generator_module, "datetime", FixedDateTime0934)
        generator._current_rejection = None
        outside = generator._check_swing_pullback("AAPL", data, current_rsi=45.0)
        assert outside is None
        assert "time_window" in (generator._current_rejection or "")

        monkeypatch.setattr(signal_generator_module, "datetime", FixedDateTime0950)
        generator._current_rejection = None
        inside = generator._check_swing_pullback("AAPL", data, current_rsi=45.0)
        assert inside is None
        assert "time_window" not in (generator._current_rejection or "")

    def test_check_swing_pullback_scan_window_fallback_when_fields_absent(self, monkeypatch):
        config = ShortCycleConfig(portfolio_value=1000.0, confidence_threshold=0.35)
        generator = AISignalGenerator(config)
        monkeypatch.setattr(signal_generator_module, "datetime", FixedDateTime0934)

        monkeypatch.delattr(config, "swing_pullback_scan_start", raising=False)
        monkeypatch.delattr(config, "swing_pullback_scan_end", raising=False)

        close = [100.0, 100.2, 100.1, 100.3, 100.0, 100.1, 99.9, 100.0, 99.8, 100.1,
                 99.9, 100.0, 100.2, 99.8, 100.0, 99.7, 99.8, 99.4, 99.1, 98.8,
                 98.4, 98.0, 97.7, 97.9, 98.2]
        open_ = [price - 0.1 for price in close]
        high = [price + 1.0 for price in close]
        low = [price - 1.8 for price in close]
        volume = [900_000] * 20 + [820_000, 780_000, 740_000, 760_000, 780_000]
        data = pd.DataFrame({"open": open_, "high": high, "low": low, "close": close, "volume": volume})

        generator._current_rejection = None
        result = generator._check_swing_pullback("AAPL", data, current_rsi=45.0)
        assert result is None
        assert "time_window" in (generator._current_rejection or "")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

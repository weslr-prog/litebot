"""Phase A observability regression tests.

These tests verify rejection telemetry and daily stats hygiene.
"""

import json
from pathlib import Path

import pandas as pd

from bot_v2.config.trading_config import ShortCycleConfig
from bot_v2.core.pre_filter import PreFilter
from bot_v2.launcher import BotV2Launcher
from bot_v2.reporting.daily_summary import DailySummary
from bot_v2.signal_generation.signal_generator import AISignalGenerator


class _DummyDataLoader:
    pass


class _DummyPositionTracker:
    pass


def test_prefilter_last_run_stats_tracks_stage_rejections(monkeypatch):
    """PreFilter should expose per-stage rejection counts for summary logging."""
    prefilter = PreFilter(simulation_mode=True, config={})

    df = pd.DataFrame(
        {
            "symbol": ["A", "B", "C", "D", "E"],
            "date": pd.date_range("2026-03-01", periods=5, freq="D"),
            "open": [10, 10, 10, 10, 10],
            "high": [11, 11, 11, 11, 11],
            "low": [9, 9, 9, 9, 9],
            "close": [10, 10, 10, 10, 10],
            "volume": [1_000_000] * 5,
        }
    )

    monkeypatch.setattr(prefilter, "fetch_history", lambda *args, **kwargs: df)
    monkeypatch.setattr(
        prefilter,
        "price_range_filter",
        lambda frame, **kwargs: frame[frame["symbol"].isin(["A", "B", "C", "D"])],
    )
    monkeypatch.setattr(
        prefilter,
        "liquidity_filter",
        lambda frame, **kwargs: frame[frame["symbol"].isin(["A", "B", "C"])],
    )
    monkeypatch.setattr(
        prefilter,
        "volatility_filter",
        lambda frame, **kwargs: frame[frame["symbol"].isin(["A", "B"])],
    )

    candidates = prefilter.run_filter(["A", "B", "C", "D", "E", "F"])
    stats = prefilter.get_last_run_stats()

    assert candidates == ["A", "B"]
    assert stats["input_count"] == 6
    assert stats["data_loaded_count"] == 5
    assert stats["passed_count"] == 2
    assert stats["rejection_reasons"]["data_unavailable"] == 1
    assert stats["rejection_reasons"]["price_range_reject"] == 1
    assert stats["rejection_reasons"]["volume_liquidity_reject"] == 1
    assert stats["rejection_reasons"]["volatility_reject"] == 1


def test_signal_generator_exposes_rejection_stats():
    """AISignalGenerator should persist per-run rejection counts for launcher reporting."""
    config = ShortCycleConfig(confidence_threshold=0.35)
    generator = AISignalGenerator(config=config, adaptive_params=False)

    generator._validate_entry_candidates = lambda universe, active: universe

    def _fake_analyze(symbol, _data):
        if symbol == "AAA":
            return (None, "Low confidence (0.20 < 0.35)", 0.2)
        return (None, "Insufficient liquidity ($100,000)", 0.1)

    generator._analyze_symbol_with_reason = _fake_analyze

    result = generator.generate_signals(
        universe=["AAA", "BBB"],
        market_data={"AAA": object(), "BBB": object()},
        active_positions=[],
    )
    stats = generator.get_last_rejection_stats()

    assert result == []
    assert stats["counts"]["confidence_low"] == 1
    assert stats["counts"]["liquidity_low"] == 1
    assert stats["total_rejected"] == 2


def test_daily_stats_save_dedupes_same_day(tmp_path):
    """Daily stats writer should replace existing same-day records instead of appending duplicates."""
    summary = DailySummary(_DummyDataLoader(), _DummyPositionTracker())
    summary.stats_file = tmp_path / "daily_stats.json"

    day_summary_v1 = {
        "date": "Saturday, March 14, 2026",
        "date_iso": "2026-03-14",
        "activity": {"entries_executed": 1, "signals_generated": 3, "candidates_reviewed": 20},
        "pnl": {"total": 1.23},
        "week_stats": {"win_rate": 50.0},
        "market": {"setup_quality": 3},
        "rejections": {"confidence_low": 2},
        "exit_reason_distribution": {"STOP_LOSS": 1},
    }
    day_summary_v2 = {
        **day_summary_v1,
        "pnl": {"total": 4.56},
        "rejections": {"confidence_low": 5, "liquidity_low": 2},
    }

    summary._save_daily_stats(day_summary_v1)
    summary._save_daily_stats(day_summary_v2)

    records = json.loads(Path(summary.stats_file).read_text())

    assert len(records) == 1
    assert records[0]["date_iso"] == "2026-03-14"
    assert records[0]["pnl"] == 4.56
    assert records[0]["rejection_total"] == 7


def test_launcher_rejection_and_exit_reason_helpers():
    """Launcher helpers should keep rejection counts numeric and exit tags normalized."""
    launcher = BotV2Launcher.__new__(BotV2Launcher)
    launcher.session_data = launcher._new_session_data()

    launcher._record_rejection("sector_cap", "ABC")
    launcher._record_rejection_counts({"confidence_low": 3, "liquidity_low": 2})
    tag = launcher._record_exit_reason("Smart Exit: trailing stop locked")

    assert launcher.session_data["rejections"]["sector_cap"] == 1
    assert launcher.session_data["rejections"]["confidence_low"] == 3
    assert launcher.session_data["rejections"]["liquidity_low"] == 2
    assert tag == "TRAILING_STOP"
    assert launcher.session_data["exit_reasons"]["TRAILING_STOP"] == 1

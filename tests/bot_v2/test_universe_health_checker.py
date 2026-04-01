"""Tests for UniverseHealthChecker data-source compatibility.

These tests ensure the checker works with bot_v2 DataLoader-style sources
that expose get_historical_data() but not get_bars().
"""

import json
from pathlib import Path

import pandas as pd

from bot_v2.config.trading_config import ShortCycleConfig
from bot_v2.maintenance.universe_health_checker import UniverseHealthChecker


class _HistoricalOnlyDataSource:
    """Mimics DataLoader: has get_historical_data, no get_bars."""

    def get_historical_data(self, symbol: str, days: int = 10):
        rows = [
            {"open": 10.0, "high": 10.5, "low": 9.8, "close": 10.1, "volume": 200_000},
            {"open": 10.1, "high": 10.6, "low": 9.9, "close": 10.2, "volume": 210_000},
            {"open": 10.2, "high": 10.7, "low": 10.0, "close": 10.3, "volume": 220_000},
            {"open": 10.3, "high": 10.8, "low": 10.1, "close": 10.4, "volume": 230_000},
            {"open": 10.4, "high": 10.9, "low": 10.2, "close": 10.5, "volume": 240_000},
        ]
        return pd.DataFrame(rows)


def _make_checker(tmp_path: Path) -> UniverseHealthChecker:
    cfg = ShortCycleConfig(portfolio_value=1000.0)
    checker = UniverseHealthChecker(config=cfg, data_source=_HistoricalOnlyDataSource())

    # Point checker at a tiny temp universe for fast deterministic tests.
    universe_path = tmp_path / "mid_cap_universe.json"
    universe_path.write_text(json.dumps({"core": ["AAPL", "MSFT"]}))
    checker.universe_file = universe_path
    checker.last_check_file = tmp_path / ".last_universe_check"
    return checker


def test_fetch_recent_bars_falls_back_to_historical_data(tmp_path):
    checker = _make_checker(tmp_path)
    bars = checker._fetch_recent_bars("AAPL", limit=3)

    assert isinstance(bars, list)
    assert len(bars) == 3
    assert all("close" in row for row in bars)
    assert all("volume" in row for row in bars)


def test_run_health_check_with_historical_only_source_has_no_attribute_errors(tmp_path):
    checker = _make_checker(tmp_path)
    results = checker.run_health_check()

    # Core regression: should no longer emit get_bars attribute errors for every symbol.
    assert results["total_stocks"] == 2
    assert not any("get_bars" in err for err in results["data_errors"])

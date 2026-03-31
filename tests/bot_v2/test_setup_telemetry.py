"""Phase 3 telemetry tests.

Verify that setup_telemetry.jsonl records are written for both entry and exit
events, and that critical fields (setup label, confidence tier, stop type,
support metadata) are present and correct.
"""

import json
import datetime as dt
import tempfile
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from bot_v2.config.trading_config import ShortCycleConfig
from bot_v2.execution.order_manager import AIOrderManager
from bot_v2.models.signals import AISignal


def _make_position(
    symbol="AAPL",
    entry_price=100.0,
    stop_price=97.0,
    confidence=0.72,
    strategy="momentum",
    support_stop_used=True,
    support_price=98.0,
    support_name="ema20",
    support_distance=0.020,
):
    """Build a minimal position-like namespace for telemetry tests."""
    signal = AISignal(
        symbol=symbol,
        action="BUY",
        confidence=confidence,
        time_horizon_days=1.5,
        entry_price=entry_price,
        stop_price=stop_price,
        target_price=entry_price * 1.06,
        position_size_dollars=1000.0,
        signal_timestamp=dt.datetime(2026, 3, 1, 11, 0, 0),
        features_used={
            "strategy": strategy,
            "support_stop_used": support_stop_used,
            "support_price_at_entry": support_price,
            "support_name": support_name,
            "support_distance": support_distance,
            "pullback_volume_ratio": 0.82,
            "bounce_volume_ratio": 1.12,
            "extension_pct": 0.03,
        },
    )

    pos = SimpleNamespace(
        symbol=symbol,
        entry_date=dt.date(2026, 3, 1),
        exit_date=dt.date(2026, 3, 4),
        entry_price=entry_price,
        stop_price=stop_price,
        target_price=signal.target_price,
        position_size_shares=10,
        position_size_dollars=1000.0,
        max_risk_dollars=(entry_price - stop_price) * 10,
        ai_signal=signal,
        # exit fields — populated when testing exit telemetry
        exit_price=None,
        exit_reason=None,
        realized_pnl=None,
        hold_days=None,
    )
    return pos


class TestSetupTelemetry:
    """Tests for Phase 3 proof-of-edge telemetry."""

    def _make_manager(self, tmpdir):
        config = ShortCycleConfig(portfolio_value=5000.0)
        mgr = AIOrderManager(config=config, execution_engine=None)
        # Redirect log writes to tmpdir so tests don't pollute the workspace.
        original_save = mgr._save_telemetry_record

        records = []

        def capture(record):
            records.append(record)
            # Also write to the temp file for round-trip validation.
            tfile = os.path.join(tmpdir, "setup_telemetry.jsonl")
            with open(tfile, "a") as f:
                f.write(json.dumps(record) + "\n")

        mgr._save_telemetry_record = capture
        return mgr, records

    def test_entry_telemetry_written_with_correct_fields(self, tmp_path):
        mgr, records = self._make_manager(tmp_path)
        pos = _make_position()

        mgr._log_setup_telemetry_entry(pos)

        assert len(records) == 1
        rec = records[0]
        assert rec["event"] == "ENTRY"
        assert rec["symbol"] == "AAPL"
        assert rec["setup_label"] == "momentum"
        assert rec["confidence_tier"] == "TIER_B"  # 0.72 → TIER_B
        assert rec["stop_type"] == "support_aware"
        assert rec["support_name"] == "ema20"
        assert rec["support_distance"] == pytest.approx(0.020)
        assert rec["pullback_volume_ratio"] == pytest.approx(0.82)
        assert rec["bounce_volume_ratio"] == pytest.approx(1.12)
        assert rec["stop_distance_pct"] == pytest.approx(0.03)  # (100-97)/100

    def test_exit_telemetry_written_with_correct_fields(self, tmp_path):
        mgr, records = self._make_manager(tmp_path)
        pos = _make_position()
        pos.exit_price = 106.0
        pos.exit_reason = "Profit target hit: +6.0%"
        pos.realized_pnl = (106.0 - 100.0) * 10
        pos.hold_days = 3

        mgr._log_setup_telemetry_exit(pos)

        assert len(records) == 1
        rec = records[0]
        assert rec["event"] == "EXIT"
        assert rec["symbol"] == "AAPL"
        assert rec["setup_label"] == "momentum"
        assert rec["confidence_tier"] == "TIER_B"
        assert rec["return_pct"] == pytest.approx(0.06)
        assert rec["realized_pnl"] == pytest.approx(60.0)
        assert rec["hold_days"] == 3
        assert rec["stop_type"] == "support_aware"

    def test_confidence_tiers_are_assigned_correctly(self, tmp_path):
        config = ShortCycleConfig(portfolio_value=5000.0)
        mgr = AIOrderManager(config=config, execution_engine=None)
        assert mgr._confidence_tier(0.85) == "TIER_A"
        assert mgr._confidence_tier(0.80) == "TIER_A"
        assert mgr._confidence_tier(0.79) == "TIER_B"
        assert mgr._confidence_tier(0.65) == "TIER_B"
        assert mgr._confidence_tier(0.64) == "TIER_C"
        assert mgr._confidence_tier(0.50) == "TIER_C"
        assert mgr._confidence_tier(0.49) == "TIER_D"
        assert mgr._confidence_tier(0.30) == "TIER_D"

    def test_flat_stop_type_recorded_when_support_stop_not_used(self, tmp_path):
        mgr, records = self._make_manager(tmp_path)
        pos = _make_position(support_stop_used=False)

        mgr._log_setup_telemetry_entry(pos)

        assert records[0]["stop_type"] == "flat_pct"

    def test_telemetry_survives_missing_optional_fields(self, tmp_path):
        """Telemetry must not raise even if features_used is empty."""
        mgr, records = self._make_manager(tmp_path)
        pos = _make_position()
        pos.ai_signal.features_used = {}  # strip all optional fields

        mgr._log_setup_telemetry_entry(pos)

        # Should write a record without errors; setup_label falls back to 'unknown'
        assert len(records) == 1
        assert records[0]["setup_label"] == "unknown"
        assert records[0]["stop_type"] == "flat_pct"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

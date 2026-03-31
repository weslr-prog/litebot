import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from pre_filter import PreFilter


def _make_test_df(symbol: str, start_date: datetime, days: int = 25) -> pd.DataFrame:
    dates = [start_date + timedelta(days=i) for i in range(days)]
    base_price = 10.0
    prices = [base_price + i * 0.05 for i in range(days)]
    # Force breakout on last day
    prices[-1] = max(prices[:-1]) * 1.05

    volumes = [100_000 + i * 2_000 for i in range(days)]
    # Volume spike on last day
    volumes[-1] = int(np.mean(volumes[-6:-1]) * 2.2)

    df = pd.DataFrame({
        "date": dates,
        "open": [p * 0.995 for p in prices],
        "high": [p * 1.01 for p in prices],
        "low": [p * 0.99 for p in prices],
        "close": prices,
        "volume": volumes,
        "symbol": symbol,
    })
    return df


def test_phase1_volume_features():
    start = datetime(2025, 1, 1)
    df_a = _make_test_df("AAA", start)
    df_b = _make_test_df("BBB", start)
    df = pd.concat([df_a, df_b], ignore_index=True)

    pf = PreFilter(simulation_mode=True, fast_mode=True)
    result = pf.breakout_filter(
        df,
        volume_spike_min=1.0,
        price_breakout_min=0.001,
        prior_high_window=10,
        avg_volume_window=10,
        min_periods_frac=0.5,
    )

    assert not result.empty, "Expected breakout_filter to return candidates"

    expected_cols = [
        "rvol_5d",
        "rvol_15d",
        "vol_roc_1",
        "vol_roc_3",
        "vol_zscore_20",
        "volume_accel",
        "climax_flag",
    ]

    for col in expected_cols:
        assert col in result.columns, f"Missing column: {col}"

    latest = result.groupby("symbol").tail(1)
    assert latest["rvol_5d"].notna().all(), "rvol_5d should be computed for latest rows"
    assert latest["vol_zscore_20"].notna().all(), "vol_zscore_20 should be computed for latest rows"
    assert latest["volume_accel"].notna().all(), "volume_accel should be computed for latest rows"
    assert latest["climax_flag"].isin([True, False]).all(), "climax_flag should be boolean"

    # Sanity: volume spike on last day should produce rvol_5d > 1
    assert (latest["rvol_5d"] > 1.0).all(), "Expected rvol_5d > 1 for latest rows"


if __name__ == "__main__":
    test_phase1_volume_features()
    print("✅ Phase 1 volume feature tests passed")

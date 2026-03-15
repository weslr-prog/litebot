# LiteBot V2

`bot_v2` is the current modular strategy engine used in this repository.
It includes signal generation, risk management, execution, reporting, and
continuous-session orchestration.

## Major Components

- `launcher.py`
    - Primary continuous loop with market-phase scheduling.
    - Runs prefilter, signal generation, entry/exit execution, and reporting.
- `signal_generation/`
    - Strategy signal logic and rejection diagnostics.
- `core/pre_filter.py`
    - Multi-stage candidate filtering with pass/rejection telemetry.
- `execution/`
    - Order placement and exit handling.
- `risk_management/`
    - Stop logic, position sizing, and portfolio safety controls.
- `reporting/`
    - Daily summaries and PnL tracking artifacts.
- `utils/enhanced_logger.py`
    - Structured operational logs and daily JSON summaries.

## Running V2

From repository root:

```bash
python3 bot_v2/launcher.py
```

Other supported runners:

```bash
python3 run_bot_v2.py
python3 run_bot_v2_continuous.py
```

## Configuration

- Runtime credentials are loaded from `.env`.
- Strategy/risk config lives in `bot_v2/config/trading_config.py`.
- Pre-filter config is in `bot_v2/config/prefilter_config.py`.

## Observability

- Daily summary files: `logs/daily_summary_YYYYMMDD.json`
- Activity and debug logs: `logs/`
- Historical daily stats: `bot_v2/data/daily_stats.json`

Recent telemetry hardening includes:

- Reason-level rejection tracking in session summaries.
- Normalized exit reason tags (`FAST_EXIT`, `STOP_LOSS`, `TRAILING_STOP`, `TARGET`, `TIME_EXIT`).
- Daily stats dedupe by `date_iso` to reduce duplicate/noisy records.

## Testing

Run focused observability regression tests:

```bash
pytest -q tests/bot_v2/test_phase_a_observability.py
```

Run package-level integration checks:

```bash
pytest -q bot_v2/tests
```

## Safety Notes

- Prefer Alpaca paper mode while tuning.
- Do not commit `.env` or API keys.
- Validate telemetry quality before making parameter changes.

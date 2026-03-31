# Bot Performance Research and Tuning Plan

Date: 2026-03-14
Scope: Live paper account performance review before parameter tuning

## Executive Summary

The bot is currently close to break-even but slightly negative over the last 3 weeks.

- Account equity: `$967.06`
- Last 3 weeks: `10` completed trades, `40.0%` win rate, realized P&L `-$2.01`
- Profit factor: `0.93x`
- Average win/loss: `+$6.99 / -$4.99`
- Expectancy per trade: `-$0.198`
- Break-even win rate at current payoff ratio: `41.65%`

Conclusion: The system is not fundamentally broken, but it is operating just below break-even with low signal throughput and likely over-sensitive exits.

## What I Ran

1. `scripts/analyze_current_performance.py`
2. `analyze_trading_performance.py`
3. `view_reports.py daily -d`
4. Additional JSON/log diagnostics on:
- `logs/daily_summary_20260305.json`
- `logs/daily_summary_20260310.json`
- `logs/trade_explanations_2026-03-*.json`
- `bot_v2/config/trading_config.py`
- `bot_v2/signal_generation/signal_generator.py`
- `bot_v2/risk_management/stop_loss_manager.py`

## Findings

### 1) Performance is near break-even but under target

From `analyze_trading_performance.py`:

- Completed trades: `10`
- Wins/Losses: `4W / 6L`
- Win rate: `40.0%`
- Realized P&L: `-$2.01`
- Profit factor: `0.93x`
- Avg hold: `32.7h` (winners `49.5h`, losers `21.6h`)

Interpretation:

- Winners are bigger than losers, which is good.
- But win rate is slightly below break-even threshold.
- A small lift in entry quality or a modest reduction in premature exits should move expectancy positive.

### 2) Signal funnel is very tight after prefilter

From `logs/daily_summary_20260305.json` and `logs/daily_summary_20260310.json`:

- 2026-03-05:
  - `45` prefilter runs
  - avg pass rate `8.68%`
  - avg candidates/scan `20.41`
  - total signals out `2`
  - signal conversion `0.16%`
- 2026-03-10:
  - `43` prefilter runs
  - avg pass rate `8.11%`
  - avg candidates/scan `19.15`
  - total signals out `1`
  - signal conversion `0.09%`

Interpretation:

- PreFilter is producing candidates, but signal generation rarely confirms them.
- This can lead to undertrading and inconsistent sampling of the strategy edge.

### 3) Accepted entries include weaker volume confirmations

From recent March entry explanations (`logs/trade_explanations_2026-03-*.json`):

- Entries analyzed: `8`
- Avg confidence: `0.751`
- Avg RSI: `57.98`
- Avg volume_ratio: `1.07`
- Entries with `volume_ratio < 1.0`: `3/8` (37.5%)

Interpretation:

- Momentum entries are sometimes accepted with below-average volume.
- This can increase false positives and lower win rate in chop.

### 4) Exit logic appears internally inconsistent with swing intent

Config and risk manager review:

- `bot_v2/config/trading_config.py` sets swing-style wider bands:
  - `stop_loss_pct = 0.04`
  - `profit_target_pct = 0.06`
- But `bot_v2/risk_management/stop_loss_manager.py` also has:
  - `fast_exit_threshold = 0.008` (0.8%)

Interpretation:

- A 0.8% fast-exit can conflict with the wider 4% swing stop framework.
- This can cut positions before the intended trade thesis has time to play out.

### 5) Reporting/telemetry quality issues are reducing diagnosability

- `rejection_reasons` fields in recent daily summaries are consistently empty (`{}`), even when `signals_out = 0`.
- `bot_v2/data/daily_stats.json` appears duplicated/noisy and not reliable for clean trend analysis.

Interpretation:

- Harder to tune accurately because we are missing clean reason-level rejection metrics over recent days.

## Root-Cause Hypothesis (Most Likely)

Primary bottleneck is a combination of:

1. Too few confirmed signals (very low conversion after prefilter)
2. Entry acceptance not strict enough on volume quality in momentum mode
3. Exit layer cutting some trades too early via 0.8% fast-exit threshold

These three together can produce exactly what we see:

- Low trade count
- Some strong winners
- Too many small/medium losses
- Slightly negative expectancy

## Proposed Adjustments (Before Full Tune Sweep)

Order is intentional: fix observability and coherence first, then tighten selection, then optimize exits.

### Phase A: Instrumentation hardening (do first)

1. Ensure rejection reasons are always populated in daily summaries.
2. Clean `daily_stats` writing logic to avoid duplicate/noisy records.
3. Add explicit exit reason tags for every close (`FAST_EXIT`, `STOP_LOSS`, `TRAILING_STOP`, `TARGET`, `TIME_EXIT`).

Expected effect:

- No direct P&L gain, but much higher confidence tuning and faster iteration.

### Phase B: Entry quality tightening (small, targeted)

1. Raise base `confidence_threshold` from `0.25` to `0.35`.
2. For momentum entries, require `volume_ratio >= 1.0` (or apply a penalty below 1.0).
3. Keep RSI band as-is initially (`45-65`) to avoid overconstraining.

Expected effect:

- Win rate improvement: roughly `+3% to +8%` absolute.
- Trade count reduction: roughly `-10% to -25%`.
- Net expectancy likely improves if throughput remains adequate.

### Phase C: Exit coherence with swing framework

1. Relax fast-exit threshold from `0.8%` to `1.5%` (stepwise), or gate fast-exit to first N hours only.
2. Keep global hard-risk controls unchanged (`$30 max loss per trade`, daily/weekly loss limits).
3. Keep trailing stops enabled, but verify activation and lock-in behavior with explicit logs.

Expected effect:

- Fewer premature stop-outs.
- Better capture of intended 2-5 day swing behavior.
- Potential improvement in win rate and average win size.

### Phase D: Throughput guardrail (only if undertrading persists)

If entries drop too low after Phase B/C:

1. Introduce conditional threshold by regime/time window (not blanket loosening).
2. Keep quality constraints but permit slightly lower confidence in favorable regimes.

Expected effect:

- Restores opportunity flow without fully reverting to low-quality entries.

## Expected Outcome After Staged Tuning

If Phases A-C are implemented and validated correctly, a realistic near-term target is:

- Win rate: `43% to 48%` (up from `40%`)
- Profit factor: `1.05x to 1.25x` (up from `0.93x`)
- Expectancy: move from slightly negative to modestly positive
- Weekly behavior: fewer random scratches, more consistency

## Validation Plan (Do Not Skip)

1. Run unchanged baseline for 5 trading days (already partly done).
2. Apply Phase A only, verify logging quality for 2 sessions.
3. Apply Phase B, run for 10-15 completed trades minimum.
4. Apply Phase C, run for another 10-15 completed trades.
5. Compare against baseline on:
- Win rate
- Profit factor
- Expectancy/trade
- Median hold time
- Exit reason distribution

Success criteria:

- Profit factor >= `1.05`
- Win rate >= `43%`
- Positive expectancy over at least `20+` completed trades

## Risks

1. Over-tightening entries may starve trade count.
2. Loosening exits too much can increase tail losses if not paired with hard risk limits.
3. Without telemetry fixes, optimization may chase noise.

## Recommendation

Proceed with a staged tune beginning with instrumentation (Phase A), then small entry-quality adjustment (Phase B), then exit coherence update (Phase C). This is the highest-probability path to move the bot from slightly negative expectancy to sustainable positive expectancy without overfitting.

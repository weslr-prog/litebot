# Bot State, Changes, Expected Behavior, and Logical Next Steps

Date: 2026-03-31
Repo: litebotx-usb-deployment
Branch: main

## 1) Bot State Before Autopilot Work

Before the Autopilot pass, the bot had already moved toward a momentum-first posture, but entry logic was still partially implicit.

Practical pre-state:

- Momentum and Swing Pullback existed, but setup quality checks were not fully mechanical end-to-end.
- Entry stops were flat-percent based from entry price, not anchored to support context.
- Telemetry existed for general explainability but did not yet provide a dedicated setup-expectancy ledger by setup type and confidence tier.
- Risk framework (account-level protections and stop discipline) was already in place and was intentionally preserved.

Checkpointing and safety actions completed first:

- Local backup created: /home/wes/Desktop/local_backups/litebotx-usb-deployment_20260331_161440.tar.gz
- Checkpoint pushed: 0e09481 (Checkpoint current bot_v2 workspace state)

## 2) Changes Made (Autopilot Phases 1-3)

### Phase 1: Explicit setup definition in signal layer

Commit: 3323743

Files changed:

- bot_v2/config/trading_config.py
- bot_v2/signal_generation/signal_generator.py
- tests/bot_v2/test_signal_generation.py

What was implemented:

- Added explicit support-context detection.
- Added pullback-volume contraction check.
- Added bounce-volume expansion check.
- Added reversal confirmation check near support.
- Added extension rejection from support.
- Reworked Momentum and Swing Pullback checks to require explicit setup-quality gates.
- Expanded signal metadata (support name/distance, pullback/bounce ratios, extension).

Validation:

- Targeted tests passed for Phase 1 behavior.

### Phase 2: Exit/risk alignment with support-aware entries

Commit: 6288672

Files changed:

- bot_v2/config/trading_config.py
- bot_v2/signal_generation/signal_generator.py
- tests/bot_v2/test_signal_generation.py

What was implemented:

- Added config: support_stop_buffer_pct (default 1%).
- Passed support_price through strategy results.
- At signal creation, stop placement now prefers support-aware stop:
  - support_stop = support_price \* (1 - support_stop_buffer_pct)
- Added guardrail: support-aware stop is capped by the hard stop-loss floor so account risk limits are not exceeded.
- Added metadata fields: support_stop_used, support_price_at_entry.

Validation:

- Added/updated tests verifying support-aware stop logic.

### Phase 3: Proof-of-edge telemetry

Commit: 2d27417

Files changed:

- bot_v2/execution/order_manager.py
- tests/bot_v2/test_setup_telemetry.py

What was implemented:

- Added confidence tier bucketing:
  - TIER_A >= 0.80
  - TIER_B >= 0.65
  - TIER_C >= 0.50
  - TIER_D < 0.50
- Added structured setup telemetry log writer to:
  - logs/setup_telemetry.jsonl
- Added ENTRY telemetry fields:
  - setup label, confidence, confidence tier
  - intended/signal entry vs actual entry
  - slippage
  - stop type (support_aware vs flat_pct)
  - stop distance
  - support context and pullback/bounce metrics
- Added EXIT telemetry fields:
  - return_pct, realized_pnl, hold_days, exit_reason
  - setup label and confidence tier
- Hooked telemetry into normal entry and exit explanation flow so each trade is recorded automatically.

Validation:

- Targeted suite passed:
  - 18 passed, 1 warning (websockets.legacy deprecation warning)

## 3) Current Bot State (After Changes)

Current commit stack (latest first):

- 2d27417 Autopilot phase 3: proof-of-edge telemetry
- 6288672 Autopilot phase 2: support-aware stop placement
- 3323743 Autopilot phase 1: explicit setup definitions
- 0e09481 Checkpoint current bot_v2 workspace state

Operationally, the bot is now:

- More explicit and selective about valid pullback setup quality.
- More coherent in stop placement for support-based entries.
- Instrumented to measure expectancy by setup type and confidence tier.

Repo note:

- Untracked archive/backup/runtime artifacts remain in the working tree and were intentionally not included in the autopilot code commits.

## 4) Expected Behavior Changes

### Expected positive shifts

- Better entry quality: fewer ambiguous pullback entries, more structure-confirmed entries.
- Better stop coherence: stops should align better with setup invalidation levels (support break) instead of only flat percent distance.
- Better diagnostics: per-trade telemetry now supports setup-level and confidence-tier expectancy analysis.

### Tradeoffs to watch

- Throughput may remain moderate if setup quality gates are strict in low-quality tapes.
- Support-aware stops can be tighter on some names; this may increase small stopouts if support identification is noisy.
- Performance should now be judged with telemetry, not just headline trade count.

## 5) Logical Next Steps (Ordered)

### Step 1: Verify telemetry capture in live/paper runtime

- Run the bot for several sessions.
- Confirm logs/setup_telemetry.jsonl is being appended on both entries and exits.
- Spot-check fields for correctness (setup_label, confidence_tier, stop_type, return_pct).

### Step 2: Build a first-pass expectancy readout

- Aggregate setup telemetry by:
  - setup_label
  - confidence_tier
- Compute per bucket:
  - trade count
  - win rate
  - average return_pct
  - median return_pct
  - expectancy

Companion script (added):

- analyze_setup_telemetry.py
- Default input file: logs/setup_telemetry.jsonl
- One-command run:
  - python analyze_setup_telemetry.py
- Useful options:
  - python analyze_setup_telemetry.py --min-trades 3
  - python analyze_setup_telemetry.py --file logs/setup_telemetry.jsonl --min-trades 5

What it prints:

- Overall expectancy summary
- Expectancy by setup_label + confidence_tier
- Expectancy by setup_label + confidence_tier + stop_type

### Step 3: Execution quality review

- Compare intended signal entry vs filled entry (slippage distribution).
- Compare stop_distance_pct by setup and confidence tier.
- Identify whether slippage or stop placement is the larger drag.

### Step 4: Throughput vs quality audit

- Track funnel counts per day:
  - prefilter passed
  - setup-qualified
  - signals emitted
  - entries executed
- Diagnose no-trade days:
  - true absence of valid setups vs over-strict gate interactions.

### Step 5: Filter efficacy decisions (data-driven only)

- Using telemetry results, classify filters as:
  - expectancy-protective
  - neutral
  - throughput-reducing without expectancy benefit
- Only then loosen, remove, or retune filters.

### Step 6: Controlled retuning pass

- If needed, adjust the smallest set of thresholds first (one at a time), then re-measure.
- Keep account-risk hard limits intact while tuning entry selectivity.

## 6) Suggested Success Criteria for the Next Review

A solid next review should be able to answer:

- Which setup is producing better expectancy: momentum vs swing pullback?
- Which confidence tier is truly tradable for this account profile?
- Are support-aware stops improving outcome distribution and reducing poor invalidation exits?
- Are no-trade days mostly market-structure driven or logic-driven?

If those answers are available from telemetry, the system is ready for disciplined filter optimization rather than guesswork.

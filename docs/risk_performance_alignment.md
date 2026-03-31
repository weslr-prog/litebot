# Risk & Performance Controller Alignment

## Current Responsibilities

- **`AIStopLossManager`** – Calculates position-level stops and fast exit triggers using ATR-derived bands and fixed ROI thresholds.
- **`AIPredictiveRiskManager`** – Screens proposed trades for portfolio-level constraints (duplicate symbols, sector concentration, daily loss limits) and can veto signals.
- **`PerformanceController`** – Monitors Sprint 2 metrics and mutates trader configuration (confidence threshold, risk per trade, max positions, etc.) to chase weekly ROI targets.

## Observed Overlap & Gaps

1. **Config Mutation Overlap** – The performance controller adjusts the same knobs (`confidence_threshold`, `max_risk_per_trade_dollars`, `max_positions_per_day`) that the risk manager implicitly protects, but without sharing state. There is no guard preventing the performance loop from loosening constraints immediately after the risk manager tightened them during the same session.
2. **Missing Risk Feedback Loop** – Portfolio risk assessments (warnings, vetoed symbols) are not surfaced to the performance controller, so systemic risk spikes do not inform its adaptive knobs.
3. **Stop Loss Isolation** – The stop manager handles fast exits in isolation; its outcomes (e.g., repeated forced exits) are not fed back into either the portfolio risk manager or the performance controller to reduce subsequent exposure.
4. **No Persistent Risk Context** – Kill switches and cumulative drawdown live inside the trader, but neither manager has a shared `RiskContext` snapshot to coordinate decisions. Each component recomputes partial metrics on the fly.

## Recommendations

1. **Introduce a `RiskContext` Dataclass**
   - Capture daily/weekly realized P&L, open risk, kill-switch status, consecutive losses, sector exposure, and PreFilter universe stats in a single snapshot.
   - Populate it inside `_process_existing_positions` and reuse across `AIPredictiveRiskManager.assess_portfolio_risk` and `PerformanceController.evaluate_and_adjust`.

2. **Centralize Config Adjustments**
   - Move all mutating logic into a `RiskAdjustmentCoordinator` helper that the performance controller calls. The coordinator should enforce monotonic throttling (e.g., if risk manager tightened limits, performance controller can only maintain or tighten further until a cool-down expires).

3. **Risk Manager ↔ Performance Controller Feedback**
   - Extend `assess_portfolio_risk` to return structured signals (`risk_level`, `sector_heat`, `loss_velocity`). Feed these into the performance controller’s `runtime_state` so it reacts to hard-risk indicators instead of only ROI pacing.
   - When the risk manager vetoes trades, inject that info into metrics logging so the controller does not interpret the absence of trades as a signal scarcity issue.

4. **Unify Fast-Exit Telemetry**
   - Emit events from `AIStopLossManager.should_fast_exit` and `execute_exit` paths. Aggregate in the shared `RiskContext` to curb future position sizes or tighten stop multipliers when repeated fast exits occur.

5. **Versioned Configuration Changes**
   - Track a revision number on the trader config. Each adjustment should include `source` metadata (`risk_manager` vs `performance_controller`) to audit conflicting changes and roll back if needed.

## Quick Wins

- Add a lightweight `RiskSnapshot` structure and pass it to both managers before opening new trades.
- Surface `risk_assessment["warnings"]` inside the performance controller metrics to prevent it from loosening rules when the risk manager is raising flags.
- Log performance adjustments alongside veto counts to identify when the two systems disagree.

## Future Enhancements

- Replace the sector stub with real sector data from the PreFilter cache or `stock_metrics` module to reduce duplicate symbol heuristics.
- Consider migrating both controllers to a shared rules engine where strategy-level objectives and risk tolerance are declarative and testable.

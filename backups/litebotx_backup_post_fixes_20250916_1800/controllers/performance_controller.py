#!/usr/bin/env python3
"""
PerformanceController - Sprint 2 Metrics Auto-Adjust Loop

Focuses on 3 Sprint 2 targets (excluding strategies):
- Achieve 15+ symbol portfolio coverage
- Launch paper trading with live signals
- Demonstrate 3%+ weekly ROI potential (progress proxy)

Approach:
- Track simple metrics daily/weekly and log progress
- Adjust safe knobs in bounded steps: universe size target, confidence threshold,
  max positions per day, and per-trade risk (within conservative caps)
- Respect safety kill switches; never exceed caps

This controller is intentionally simple and conservative for initial deployment.
"""

from dataclasses import dataclass
from typing import Dict, Any, List
import datetime as dt
import json
import os
import logging

@dataclass
class Sprint2Targets:
    min_strategies: int = 3             # Not enforced here per request
    min_symbols: int = 15               # Portfolio coverage
    paper_trading_required: bool = True # Paper trading mode on
    weekly_roi_goal: float = 0.03       # 3% weekly ROI potential


class PerformanceController:
    def __init__(self,
                 logger: logging.Logger = None,
                 metrics_log_path: str = "logs/short_cycle_metrics.jsonl"):
        self.logger = logger or logging.getLogger("PerformanceController")
        if not self.logger.handlers:
            ch = logging.StreamHandler()
            ch.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
            self.logger.addHandler(ch)
            self.logger.setLevel(logging.INFO)

        self.targets = Sprint2Targets()
        self.metrics_log_path = metrics_log_path
        os.makedirs(os.path.dirname(metrics_log_path), exist_ok=True)

    def record_metrics(self, metrics: Dict[str, Any]):
        """Persist a single metrics snapshot to JSONL for auditing."""
        entry = {
            "timestamp": dt.datetime.now().isoformat(),
            **metrics
        }
        with open(self.metrics_log_path, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def evaluate_and_adjust(self,
                            trader_config,
                            runtime_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Read current metrics and nudge config towards Sprint 2 targets.

        Inputs:
        - trader_config: object with attributes used by short_cycle_trader
          (confidence_threshold, max_positions_per_day, daily_pool_percent,
           max_risk_per_trade_dollars, trading_universe length)
        - runtime_state: dict with keys like
          {
            "mode": "paper"|"live",
            "weekly_return": float,
            "drawdown": float,
            "win_rate": float,
            "consecutive_losses": int,
            "symbols_covered": int,
            "signals_today": int
          }

        Output: dict with adjustments and rationale.
        """
        changes: List[str] = []

        # 1) Ensure paper trading is active
        if self.targets.paper_trading_required and runtime_state.get("mode") != "paper":
            changes.append("Switch to paper trading mode for Sprint 2.")

        # 2) Nudge symbol coverage towards 15+
        symbols = runtime_state.get("symbols_covered", 0)
        if symbols < self.targets.min_symbols:
            # We don't mutate universe here; we just recommend and set a target the caller can use.
            shortfall = self.targets.min_symbols - symbols
            changes.append(f"Increase universe size by {shortfall} to reach {self.targets.min_symbols} symbols.")

        # 3) Promote live signal generation (not execution logic here)
        signals_today = runtime_state.get("signals_today", 0)
        trades_today = runtime_state.get("trades_today", 0)
        
        if signals_today == 0:
            # Slightly lower confidence threshold to encourage signal flow, within bounds
            old = getattr(trader_config, "confidence_threshold", 0.75)
            new = max(0.65, old - 0.02)
            if new < old:
                setattr(trader_config, "confidence_threshold", new)
                changes.append(f"Lowered confidence_threshold from {old:.2f} to {new:.2f} to increase signals.")
        
        # 3.5) Handle signals without trades (position sizing issue)
        if signals_today > 0 and trades_today == 0:
            # Increase risk budget to help with position sizing
            old_risk = getattr(trader_config, "max_risk_per_trade_dollars", 15.0)
            new_risk = min(35.0, old_risk * 1.25)  # Cap at $35
            if new_risk > old_risk:
                setattr(trader_config, "max_risk_per_trade_dollars", new_risk)
                changes.append(f"Increased risk per trade from ${old_risk:.0f} to ${new_risk:.0f} - signals detected but no trades executed.")
            
            # Lower minimum position size to help execution
            old_min = getattr(trader_config, "min_position_size_dollars", 50.0)
            new_min = max(15.0, old_min * 0.75)  # Minimum $15
            if new_min < old_min:
                setattr(trader_config, "min_position_size_dollars", new_min)
                changes.append(f"Lowered min position size from ${old_min:.0f} to ${new_min:.0f} to help trade execution.")

        # 4) Weekly ROI pacing (very conservative):
        # If far below 3% pace midweek, allow +1 max position (cap 4). If drawdown rising, tighten.
        weekly_return = runtime_state.get("weekly_return", 0.0)
        drawdown = runtime_state.get("drawdown", 0.0)

        # Tighten if drawdown > 4%
        if drawdown > 0.04:
            # Reduce risk per trade by up to 20%
            old_risk = getattr(trader_config, "max_risk_per_trade_dollars", 6.0)
            new_risk = max(2.0, round(old_risk * 0.9, 2))
            if new_risk < old_risk:
                setattr(trader_config, "max_risk_per_trade_dollars", new_risk)
                changes.append(f"Tightened risk per trade from ${old_risk:.2f} to ${new_risk:.2f} due to drawdown {drawdown:.1%}.")
            # Raise confidence a bit
            old_ct = getattr(trader_config, "confidence_threshold", 0.75)
            new_ct = min(0.90, round(old_ct + 0.03, 2))
            if new_ct > old_ct:
                setattr(trader_config, "confidence_threshold", new_ct)
                changes.append(f"Raised confidence_threshold from {old_ct:.2f} to {new_ct:.2f} due to drawdown.")
        else:
            # If weekly return < goal/2 by Thu, try allowing one extra position (cap 4)
            today = dt.datetime.now().weekday()  # 0=Mon ... 4=Fri
            if today >= 3 and weekly_return < self.targets.weekly_roi_goal * 0.5:
                old_max = getattr(trader_config, "max_positions_per_day", 3)
                new_max = min(4, old_max + 1)
                if new_max > old_max:
                    setattr(trader_config, "max_positions_per_day", new_max)
                    changes.append(f"Increased max_positions_per_day from {old_max} to {new_max} to improve weekly pacing.")

        # 5) Consecutive loss cool-down (not a kill switch, just throttle)
        if runtime_state.get("consecutive_losses", 0) >= 3:
            old_max = getattr(trader_config, "max_positions_per_day", 3)
            new_max = max(1, old_max - 1)
            if new_max < old_max:
                setattr(trader_config, "max_positions_per_day", new_max)
                changes.append(f"Loss streak detected: reduced max_positions_per_day from {old_max} to {new_max}.")
            old_ct = getattr(trader_config, "confidence_threshold", 0.75)
            new_ct = min(0.9, old_ct + 0.05)
            if new_ct > old_ct:
                setattr(trader_config, "confidence_threshold", new_ct)
                changes.append(f"Loss streak detected: raised confidence_threshold from {old_ct:.2f} to {new_ct:.2f}.")

        result = {
            "changes": changes,
            "targets": {
                "min_symbols": self.targets.min_symbols,
                "weekly_roi_goal": self.targets.weekly_roi_goal,
                "paper_trading_required": self.targets.paper_trading_required
            }
        }

        # Log and persist
        self.logger.info(f"PerformanceController adjustments: {changes}")
        self.record_metrics({
            "weekly_return": weekly_return,
            "drawdown": drawdown,
            "symbols_covered": symbols,
            "signals_today": runtime_state.get("signals_today", 0),
            "changes": changes
        })

        return result

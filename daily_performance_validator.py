#!/usr/bin/env python3
"""Integrated daily performance validation helpers.

This module is imported by `test/bot_integration.py` and can also be called
from runtime routines to produce a lightweight health recommendation.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

from core.adaptive_threshold_manager import AdaptiveThresholdManager


logger = logging.getLogger(__name__)
REPO_ROOT = Path(__file__).resolve().parent
LOG_FILE = REPO_ROOT / "logs" / "daily_validation.json"


class DailyPerformanceValidator:
    """Lightweight daily validation integrated into the bot routine."""

    def __init__(self):
        self.adaptive_manager = AdaptiveThresholdManager()
        self.alert_thresholds = {
            "min_win_rate": 0.50,
            "min_sharpe": 1.5,
            "max_drawdown": 0.15,
            "min_trades": 5,
        }

    def run_daily_validation(self) -> dict:
        """Analyze recent performance and return alerts + recommendation."""
        results = {
            "timestamp": datetime.now().isoformat(),
            "validation_type": "daily_routine",
            "alerts": [],
            "performance_summary": {},
            "recommendation": "continue",
        }

        try:
            recent_metrics = self.adaptive_manager.analyze_trade_logs(days=7)
            monthly_metrics = self.adaptive_manager.analyze_trade_logs(days=30)

            results["performance_summary"] = {
                "recent_7d": {
                    "win_rate": recent_metrics.win_rate,
                    "total_trades": recent_metrics.total_trades,
                    "sharpe_ratio": recent_metrics.sharpe_ratio,
                    "avg_return": recent_metrics.avg_return,
                    "max_drawdown": recent_metrics.max_drawdown,
                },
                "monthly_30d": {
                    "win_rate": monthly_metrics.win_rate,
                    "total_trades": monthly_metrics.total_trades,
                    "sharpe_ratio": monthly_metrics.sharpe_ratio,
                    "avg_return": monthly_metrics.avg_return,
                    "max_drawdown": monthly_metrics.max_drawdown,
                },
            }

            self._check_alert_conditions(recent_metrics, monthly_metrics, results)
            results["recommendation"] = self._generate_recommendation(recent_metrics, results)
            return results
        except Exception as exc:
            logger.exception("Daily validation failed")
            results["error"] = str(exc)
            results["recommendation"] = "investigate"
            return results

    def _check_alert_conditions(self, recent_metrics, monthly_metrics, results: dict):
        alerts: list[dict] = []

        if recent_metrics.total_trades >= self.alert_thresholds["min_trades"]:
            if recent_metrics.win_rate < self.alert_thresholds["min_win_rate"]:
                alerts.append(
                    {
                        "type": "win_rate_low",
                        "severity": "warning",
                        "message": (
                            f"Recent win rate {recent_metrics.win_rate:.1%} below "
                            f"{self.alert_thresholds['min_win_rate']:.1%}"
                        ),
                    }
                )
            if recent_metrics.sharpe_ratio < self.alert_thresholds["min_sharpe"]:
                alerts.append(
                    {
                        "type": "sharpe_low",
                        "severity": "warning",
                        "message": (
                            f"Recent Sharpe ratio {recent_metrics.sharpe_ratio:.2f} below "
                            f"{self.alert_thresholds['min_sharpe']:.2f}"
                        ),
                    }
                )

        if monthly_metrics.max_drawdown > self.alert_thresholds["max_drawdown"]:
            alerts.append(
                {
                    "type": "drawdown_high",
                    "severity": "critical",
                    "message": (
                        f"Monthly drawdown {monthly_metrics.max_drawdown:.1%} exceeds "
                        f"{self.alert_thresholds['max_drawdown']:.1%}"
                    ),
                }
            )

        if recent_metrics.total_trades == 0:
            alerts.append(
                {
                    "type": "no_trades",
                    "severity": "info",
                    "message": "No trades in last 7 days",
                }
            )

        results["alerts"] = alerts

    def _generate_recommendation(self, recent_metrics, results: dict) -> str:
        critical_alerts = [a for a in results.get("alerts", []) if a.get("severity") == "critical"]
        warning_alerts = [a for a in results.get("alerts", []) if a.get("severity") == "warning"]

        if critical_alerts:
            return "review_immediately"
        if len(warning_alerts) >= 2:
            return "review_within_24h"
        if warning_alerts:
            return "monitor_closely"
        if recent_metrics.total_trades > 0 and recent_metrics.win_rate > 0.55:
            return "continue_excellent"
        if recent_metrics.total_trades > 0:
            return "continue_monitor"
        return "continue_low_activity"

    def save_validation_results(self, results: dict):
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

        if LOG_FILE.exists():
            with LOG_FILE.open("r", encoding="utf-8") as handle:
                try:
                    logs = json.load(handle)
                except json.JSONDecodeError:
                    logs = []
        else:
            logs = []

        logs.append(results)
        cutoff_date = datetime.now() - timedelta(days=30)
        logs = [
            log
            for log in logs
            if datetime.fromisoformat(log["timestamp"].replace("Z", "+00:00")).replace(tzinfo=None)
            > cutoff_date
        ]

        with LOG_FILE.open("w", encoding="utf-8") as handle:
            json.dump(logs, handle, indent=2)


def run_integrated_validation() -> dict:
    """Run validation and return a compact summary for caller integrations."""
    validator = DailyPerformanceValidator()
    results = validator.run_daily_validation()
    validator.save_validation_results(results)

    alerts = results.get("alerts", [])
    critical_alerts = [a for a in alerts if a.get("severity") == "critical"]
    recommendation = results.get("recommendation", "investigate")

    return {
        "status": "completed",
        "recommendation": recommendation,
        "alert_count": len(alerts),
        "critical_alerts": len(critical_alerts),
        "performance_ok": recommendation in {
            "continue_excellent",
            "continue_monitor",
            "continue_low_activity",
        },
    }

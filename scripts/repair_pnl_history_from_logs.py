#!/usr/bin/env python3
"""
Repair bot_v2/data/pnl_history.json using logs/daily_summary_*.json as source of truth.

Fixes:
- wins/losses based on exit PnL sign
- exits/entries/trades alignment
- realized_pnl recalculated from position_exit events
"""

from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple


def _load_exit_metrics_from_logs(log_glob: str) -> Dict[str, Dict[str, float]]:
    metrics: Dict[str, Dict[str, float]] = defaultdict(lambda: {
        "entries": 0,
        "exits": 0,
        "wins": 0,
        "losses": 0,
        "realized_pnl": 0.0,
    })

    for path in sorted(glob.glob(log_glob)):
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)

        date_str = payload.get("date")
        if not date_str:
            continue

        for event in payload.get("events", []):
            event_type = event.get("type")
            data = event.get("data", {}) or {}

            if event_type == "position_entry":
                metrics[date_str]["entries"] += 1
                continue

            if event_type != "position_exit":
                continue

            pnl = float(data.get("pnl", 0.0) or 0.0)
            metrics[date_str]["exits"] += 1
            metrics[date_str]["realized_pnl"] += pnl

            if pnl > 0:
                metrics[date_str]["wins"] += 1
            else:
                metrics[date_str]["losses"] += 1

    return metrics


def _repair_history(history: List[Dict], log_metrics: Dict[str, Dict[str, float]]) -> Tuple[List[Dict], int]:
    updates = 0

    for row in history:
        date_str = row.get("date")
        if not date_str or date_str not in log_metrics:
            continue

        day = log_metrics[date_str]
        exits = int(day["exits"])
        wins = int(day["wins"])
        losses = int(day["losses"])
        entries = int(day["entries"])
        realized_pnl = round(float(day["realized_pnl"]), 2)
        trades = entries + exits
        win_rate = round((wins / exits * 100.0) if exits > 0 else 0.0, 1)

        changed = False
        target_values = {
            "entries": entries,
            "exits": exits,
            "trades": trades,
            "wins": wins,
            "losses": losses,
            "win_rate": win_rate,
            "realized_pnl": realized_pnl,
        }

        for key, value in target_values.items():
            if row.get(key) != value:
                row[key] = value
                changed = True

        if changed:
            updates += 1

    return history, updates


def _backup_file(path: Path) -> Path:
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = path.with_suffix(path.suffix + f".bak_{stamp}")
    backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    return backup


def main() -> None:
    parser = argparse.ArgumentParser(description="Repair pnl_history.json from daily_summary logs")
    parser.add_argument("--history", default="bot_v2/data/pnl_history.json", help="Path to pnl_history.json")
    parser.add_argument("--logs", default="logs/daily_summary_*.json", help="Glob for daily summary logs")
    args = parser.parse_args()

    history_path = Path(args.history)
    if not history_path.exists():
        raise FileNotFoundError(f"History file not found: {history_path}")

    log_metrics = _load_exit_metrics_from_logs(args.logs)
    if not log_metrics:
        print("No daily summary log metrics found; nothing to repair.")
        return

    history_data = json.loads(history_path.read_text(encoding="utf-8"))
    repaired, updated_rows = _repair_history(history_data, log_metrics)

    backup_path = _backup_file(history_path)
    history_path.write_text(json.dumps(repaired, indent=2), encoding="utf-8")

    print(f"Backup created: {backup_path}")
    print(f"Rows updated: {updated_rows}")
    print(f"Dates covered by logs: {len(log_metrics)}")


if __name__ == "__main__":
    main()

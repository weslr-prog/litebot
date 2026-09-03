#!/usr/bin/env python3
"""Analyze setup telemetry and print expectancy by setup + confidence tier.

Default input: logs/setup_telemetry.jsonl

Example:
    python analyze_setup_telemetry.py
    python analyze_setup_telemetry.py --file logs/setup_telemetry.jsonl --min-trades 3
"""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, median
from typing import Dict, Iterable, List, Optional, Tuple


@dataclass
class BucketStats:
    trades: int
    win_rate: float
    avg_return_pct: float
    median_return_pct: float
    avg_win_pct: float
    avg_loss_pct: float
    expectancy_pct: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize setup telemetry expectancy by setup_label and confidence_tier"
    )
    parser.add_argument(
        "--file",
        default="logs/setup_telemetry.jsonl",
        help="Path to setup telemetry jsonl file (default: logs/setup_telemetry.jsonl)",
    )
    parser.add_argument(
        "--min-trades",
        type=int,
        default=1,
        help="Minimum trades required to display a bucket (default: 1)",
    )
    parser.add_argument(
        "--event",
        choices=["EXIT", "ENTRY"],
        default="EXIT",
        help="Telemetry event type to analyze. Use EXIT for realized expectancy (default: EXIT)",
    )
    return parser.parse_args()


def safe_float(value) -> Optional[float]:
    if value is None:
        return None
    try:
        val = float(value)
        if math.isnan(val) or math.isinf(val):
            return None
        return val
    except (TypeError, ValueError):
        return None


def load_jsonl(path: Path) -> Iterable[dict]:
    with path.open("r", encoding="utf-8") as f:
        for idx, line in enumerate(f, start=1):
            text = line.strip()
            if not text:
                continue
            try:
                yield json.loads(text)
            except json.JSONDecodeError:
                print(f"WARN: Skipping malformed JSON at line {idx}")


def compute_bucket_stats(returns: List[float]) -> BucketStats:
    trades = len(returns)
    wins = [r for r in returns if r > 0]
    losses = [r for r in returns if r <= 0]

    win_rate = (len(wins) / trades) if trades else 0.0
    avg_return = mean(returns) if trades else 0.0
    med_return = median(returns) if trades else 0.0
    avg_win = mean(wins) if wins else 0.0
    avg_loss = mean(losses) if losses else 0.0
    expectancy = (win_rate * avg_win) + ((1.0 - win_rate) * avg_loss)

    return BucketStats(
        trades=trades,
        win_rate=win_rate,
        avg_return_pct=avg_return,
        median_return_pct=med_return,
        avg_win_pct=avg_win,
        avg_loss_pct=avg_loss,
        expectancy_pct=expectancy,
    )


def format_pct(value: float) -> str:
    return f"{value:+.2%}"


def print_table(title: str, rows: List[Tuple[str, BucketStats]]) -> None:
    print(f"\n{title}")
    print("-" * len(title))
    header = (
        f"{'Bucket':35} {'Trades':>6} {'WinRate':>8} {'AvgRet':>9} "
        f"{'MedRet':>9} {'AvgWin':>9} {'AvgLoss':>9} {'Expect':>9}"
    )
    print(header)
    print("-" * len(header))

    for bucket, st in rows:
        print(
            f"{bucket:35} {st.trades:>6d} {st.win_rate:>8.1%} "
            f"{format_pct(st.avg_return_pct):>9} {format_pct(st.median_return_pct):>9} "
            f"{format_pct(st.avg_win_pct):>9} {format_pct(st.avg_loss_pct):>9} "
            f"{format_pct(st.expectancy_pct):>9}"
        )


def main() -> int:
    args = parse_args()
    telemetry_path = Path(args.file)

    if not telemetry_path.exists():
        print(f"No telemetry file found at: {telemetry_path}")
        print("Run the bot first to generate logs/setup_telemetry.jsonl.")
        return 1

    grouped_returns: Dict[Tuple[str, str], List[float]] = defaultdict(list)
    grouped_stop_type: Dict[Tuple[str, str, str], List[float]] = defaultdict(list)
    all_returns: List[float] = []
    rows_read = 0

    for rec in load_jsonl(telemetry_path):
        rows_read += 1
        if rec.get("event") != args.event:
            continue

        setup = str(rec.get("setup_label", "unknown") or "unknown")
        tier = str(rec.get("confidence_tier", "UNKNOWN") or "UNKNOWN")
        stop_type = str(rec.get("stop_type", "unknown") or "unknown")

        if args.event == "EXIT":
            ret = safe_float(rec.get("return_pct"))
        else:
            # ENTRY events do not have realized returns; this mode is mostly for quick QA.
            ret = safe_float(rec.get("entry_slippage_pct"))

        if ret is None:
            continue

        grouped_returns[(setup, tier)].append(ret)
        grouped_stop_type[(setup, tier, stop_type)].append(ret)
        all_returns.append(ret)

    if not all_returns:
        metric_name = "return_pct" if args.event == "EXIT" else "entry_slippage_pct"
        print(
            f"No analyzable {args.event} rows with numeric {metric_name} in {telemetry_path} "
            f"(read {rows_read} rows)."
        )
        return 1

    filtered_rows: List[Tuple[str, BucketStats]] = []
    for (setup, tier), values in sorted(grouped_returns.items(), key=lambda x: (x[0][0], x[0][1])):
        st = compute_bucket_stats(values)
        if st.trades >= args.min_trades:
            filtered_rows.append((f"{setup} | {tier}", st))

    filtered_stop_rows: List[Tuple[str, BucketStats]] = []
    for (setup, tier, stop_type), values in sorted(
        grouped_stop_type.items(), key=lambda x: (x[0][0], x[0][1], x[0][2])
    ):
        st = compute_bucket_stats(values)
        if st.trades >= args.min_trades:
            filtered_stop_rows.append((f"{setup} | {tier} | {stop_type}", st))

    overall = compute_bucket_stats(all_returns)

    metric_label = "Realized Return" if args.event == "EXIT" else "Entry Slippage"
    print(f"Telemetry file: {telemetry_path}")
    print(f"Rows read: {rows_read}")
    print(f"Analyzed event: {args.event} ({metric_label})")
    print(f"Minimum trades per bucket: {args.min_trades}")

    print_table("Overall", [("ALL", overall)])

    if filtered_rows:
        print_table("By Setup + Confidence Tier", filtered_rows)
    else:
        print("\nNo setup/tier buckets met --min-trades threshold.")

    if filtered_stop_rows:
        print_table("By Setup + Tier + Stop Type", filtered_stop_rows)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

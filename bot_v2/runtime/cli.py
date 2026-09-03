"""Command-line interface for bot_v2 runtime."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from bot_v2.runtime.bootstrap import RuntimeOptions, resolve_paper_trading
from bot_v2.runtime.service import BotRuntimeService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run LiteBotX bot_v2 through the clean runtime entrypoint.")
    parser.add_argument(
        "mode",
        nargs="?",
        default="launcher",
        choices=["launcher", "daily-engine", "continuous-engine"],
        help="Runtime mode to execute.",
    )
    broker_group = parser.add_mutually_exclusive_group()
    broker_group.add_argument("--paper", action="store_true", help="Force Alpaca paper trading mode.")
    broker_group.add_argument("--live", action="store_true", help="Force Alpaca live trading mode.")
    parser.add_argument("--env-file", type=Path, help="Optional path to a .env file to load before startup.")
    parser.add_argument("--dry-run", action="store_true", help="Print the resolved runtime summary without starting the bot.")
    return parser


def parse_args(argv: Sequence[str] | None = None) -> RuntimeOptions:
    args = build_parser().parse_args(argv)
    return RuntimeOptions(
        mode=args.mode,
        paper_trading=resolve_paper_trading(force_paper=args.paper, force_live=args.live),
        env_file=args.env_file,
        dry_run=args.dry_run,
    )


def main(argv: Sequence[str] | None = None) -> int:
    options = parse_args(argv)
    service = BotRuntimeService()
    return service.run(options)
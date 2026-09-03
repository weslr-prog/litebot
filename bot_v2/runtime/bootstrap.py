"""Bootstrap helpers for bot_v2 runtime modes."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from bot_v2.config import ShortCycleConfig


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ENV_FILE = REPO_ROOT / ".env"


@dataclass(frozen=True)
class RuntimeOptions:
    """Normalized runtime settings used by the CLI and service layer."""

    mode: str = "launcher"
    paper_trading: bool = True
    env_file: Optional[Path] = None
    dry_run: bool = False


@dataclass(frozen=True)
class RuntimeContext:
    """Fully prepared runtime context for a bot_v2 run."""

    options: RuntimeOptions
    config: ShortCycleConfig
    env_file_loaded: Optional[Path]
    active_strategies: tuple[str, ...]


def load_runtime_environment(env_file: Optional[str | Path] = None) -> Optional[Path]:
    """Load runtime environment variables if an env file exists."""
    candidate = Path(env_file) if env_file else DEFAULT_ENV_FILE
    if candidate.exists():
        load_dotenv(candidate, override=False)
        return candidate
    return None


def resolve_paper_trading(force_paper: bool = False, force_live: bool = False) -> bool:
    """Resolve broker mode from flags first, then environment."""
    if force_live:
        return False
    if force_paper:
        return True

    base_url = os.getenv("APCA_API_BASE_URL")
    if base_url:
        return "paper" in base_url.lower()

    return os.getenv("ALPACA_PAPER", "true").lower() == "true"


def build_runtime_config(fetch_account_equity: bool = True) -> ShortCycleConfig:
    """Create a config with optional Alpaca equity lookup."""
    portfolio_value = None if fetch_account_equity else 1000.0
    return ShortCycleConfig(portfolio_value=portfolio_value)


def get_active_strategies(config: ShortCycleConfig) -> tuple[str, ...]:
    """Return human-readable strategy labels for enabled strategies."""
    strategies: list[str] = []
    if config.enable_gap_and_go:
        strategies.append("Gap & Go")
    if config.enable_fade_short:
        strategies.append("Fade/Short")
    if getattr(config, "enable_momentum", True):
        strategies.append("Momentum")
    return tuple(strategies)


def build_runtime_context(options: RuntimeOptions) -> RuntimeContext:
    """Build a runtime context suitable for running or dry-running the bot."""
    env_path = load_runtime_environment(options.env_file)
    config = build_runtime_config(fetch_account_equity=not options.dry_run)
    return RuntimeContext(
        options=options,
        config=config,
        env_file_loaded=env_path,
        active_strategies=get_active_strategies(config),
    )
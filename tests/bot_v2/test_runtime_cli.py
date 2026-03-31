"""Tests for the clean bot_v2 runtime CLI."""

from pathlib import Path

from bot_v2.runtime import cli
from bot_v2.runtime.bootstrap import RuntimeOptions


def test_parse_args_defaults_to_launcher_paper_mode(monkeypatch):
    monkeypatch.setattr(cli, "resolve_paper_trading", lambda force_paper, force_live: True)

    options = cli.parse_args([])

    assert options.mode == "launcher"
    assert options.paper_trading is True
    assert options.env_file is None
    assert options.dry_run is False


def test_parse_args_supports_live_and_env_file(monkeypatch, tmp_path):
    monkeypatch.setattr(cli, "resolve_paper_trading", lambda force_paper, force_live: not force_live)
    env_file = tmp_path / ".env.custom"

    options = cli.parse_args(["daily-engine", "--live", "--env-file", str(env_file), "--dry-run"])

    assert options.mode == "daily-engine"
    assert options.paper_trading is False
    assert options.env_file == Path(env_file)
    assert options.dry_run is True


def test_main_dispatches_to_runtime_service(monkeypatch):
    captured = {}

    class _FakeService:
        def run(self, options):
            captured["options"] = options
            return 7

    monkeypatch.setattr(cli, "BotRuntimeService", _FakeService)
    monkeypatch.setattr(
        cli,
        "parse_args",
        lambda argv=None: RuntimeOptions(mode="continuous-engine", paper_trading=True, dry_run=True),
    )

    result = cli.main(["continuous-engine", "--dry-run"])

    assert result == 7
    assert captured["options"].mode == "continuous-engine"
    assert captured["options"].dry_run is True
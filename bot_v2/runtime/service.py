"""Service layer for bot_v2 runtime orchestration."""

from __future__ import annotations

from typing import Callable, Dict

from bot_v2.runtime.bootstrap import RuntimeContext, RuntimeOptions, build_runtime_context


class BotRuntimeService:
    """Run bot_v2 through a single clean entry surface."""

    def __init__(self):
        self._runners: Dict[str, Callable[[RuntimeContext], int]] = {
            "launcher": self._run_launcher,
            "daily-engine": self._run_daily_engine,
            "continuous-engine": self._run_continuous_engine,
        }

    def build_context(self, options: RuntimeOptions) -> RuntimeContext:
        return build_runtime_context(options)

    def run(self, options: RuntimeOptions) -> int:
        context = self.build_context(options)
        self.print_summary(context)
        if context.options.dry_run:
            return 0
        return self._runners[context.options.mode](context)

    def print_summary(self, context: RuntimeContext):
        mode = context.options.mode
        paper_text = "PAPER" if context.options.paper_trading else "LIVE"
        strategies = ", ".join(context.active_strategies) if context.active_strategies else "None"
        env_loaded = str(context.env_file_loaded) if context.env_file_loaded else "not found"

        print("=" * 80)
        print(f"LiteBotX bot_v2 Runtime | mode={mode} | broker={paper_text}")
        print("=" * 80)
        print(f"Active Strategies: {strategies}")
        print(f"Env File: {env_loaded}")
        print(f"Portfolio Value: ${context.config.portfolio_value:,.2f}")
        print(f"Max Positions/Day: {context.config.max_positions_per_day}")
        print(f"Confidence Threshold: {context.config.confidence_threshold:.0%}")
        print(f"Friday Loser Threshold: {context.config.friday_loser_threshold:.1%}")
        print(f"Fast Exit Threshold: {context.config.fast_exit_threshold_pct:.1%}")
        if context.options.dry_run:
            print("Dry Run: no trading components started")
        print("")

    def _run_launcher(self, context: RuntimeContext) -> int:
        from bot_v2.launcher import BotV2Launcher

        launcher = BotV2Launcher(
            config=context.config,
            paper_trading=context.options.paper_trading,
        )
        launcher.run_continuous_loop()
        return 0

    def _run_daily_engine(self, _context: RuntimeContext) -> int:
        import run_bot_v2

        return int(run_bot_v2.main() or 0)

    def _run_continuous_engine(self, _context: RuntimeContext) -> int:
        import run_bot_v2_continuous

        return int(run_bot_v2_continuous.main() or 0)
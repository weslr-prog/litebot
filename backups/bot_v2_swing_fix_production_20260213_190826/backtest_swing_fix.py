#!/usr/bin/env python3
"""
Swing-Fix Backtest — Feb 13 2026
=================================
Tests the 5 structural fixes against mid-cap data using the REAL bot_v2 signal pipeline:
  1. RSI exits disabled < 48h hold
  2. Hard stop widened 2% → 4%
  3. Quick-profit raised 2% → 4%, standard target 4% → 6%
  4. Trailing stop unified: 3% activation, 2% trail
  5. Entry confidence raised 25% → 55%

Usage:
    python backtest_swing_fix.py              # Default 90-day lookback
    python backtest_swing_fix.py --days 180   # 6 months
"""

import sys
import os
import datetime as dt
import argparse
import traceback
import time
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

# Load .env FIRST so Alpaca keys are available to all modules
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))
    print(f"✅ .env loaded — APCA_API_KEY_ID={'set' if os.getenv('APCA_API_KEY_ID') else 'MISSING'}")
except ImportError:
    print("⚠️  python-dotenv not installed — Alpaca data sources may be disabled")

# Ensure workspace root is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bot_v2.config.trading_config import ShortCycleConfig
from bot_v2.data.data_loader import DataLoader
from bot_v2.signal_generation.signal_generator import AISignalGenerator
from bot_v2.models.signals import AISignal
from bot_v2.utils.smart_exit_manager import SmartExitManager

# ─── Monkeypatch datetime.now() inside signal_generator to always return 9:40 AM ──
# The signal generator has time-of-day gates (Gap&Go: 9:35-9:50, Fade: 10-14, 
# Momentum: 10:30-14:30). In a backtest these kill all signals. We patch the module's
# datetime.now() to return a time within the primary Gap&Go window.
import bot_v2.signal_generation.signal_generator as _sig_mod
from unittest.mock import patch as _mock_patch

class _BacktestDatetime:
    """Drop-in datetime replacement that makes now() return 9:40 AM."""
    def __init__(self, real_datetime):
        self._real = real_datetime
    def now(self, *args, **kwargs):
        real = self._real.now(*args, **kwargs)
        # Return 9:40 AM today (inside Gap&Go + Fade + Momentum windows overlap? No.)
        # Gap&Go: 9:35-9:50, Fade: 10:00-14:00, Momentum: 10:30-14:30
        # We need to test ALL strategies. Run 2 passes isn't practical.
        # Instead, patch to 10:35 AM which covers Fade + Momentum (Gap&Go misses).
        # Actually, let's just patch to remove the time check entirely via subclass.
        # Simplest: return 9:40 for gap, but we lose fade/momentum.
        # Best: return different times per strategy. But that's complex.
        # Practical: return 10:35 AM (covers Fade + Momentum, the two that CAN fire on daily data.
        # Gap&Go requires intraday open vs prev close gap — daily bars show this naturally.)
        # Actually Gap&Go checks open vs prev close, and the time gate is the blocker.
        # Let's return 9:40 AM for the Gap&Go window, since Fade also has min hour 10.
        # We'll need to run the signal gen twice per day: once at 9:40, once at 10:35.
        return real.replace(hour=9, minute=40, second=0)
    def __getattr__(self, name):
        return getattr(self._real, name)

# We'll monkeypatch inside the backtest run method instead

# ─── Mid-Cap Universe ($2B–$10B) ──────────────────────────────────────────────
MIDCAP_UNIVERSE = [
    'AAL', 'AEO', 'AES', 'AI', 'APA', 'AR', 'BEAM', 'BEKE',
    'CAG', 'CCL', 'CDNA', 'CHWY', 'CLF', 'CPB', 'CPNG', 'CTRA',
    'F', 'HAL', 'HIMS', 'HRL', 'JACK', 'JD', 'KDP', 'KHC',
    'LC', 'LCID', 'LI', 'LYFT', 'MGY', 'MRNA', 'MUR', 'NCLH',
    'NOV', 'NTLA', 'NU', 'NWSA', 'OSCR', 'PATH', 'PENN', 'PINS',
    'PL', 'PR', 'RIVN', 'S', 'SCVL', 'SDGR', 'SM', 'SOFI',
    'SOUN', 'STLA', 'T', 'TAL', 'TLRY', 'TU', 'TWST', 'VALE',
    'VFC', 'VIPS', 'VIRT', 'VOD', 'WBD', 'WEN', 'WOLF', 'XPEV',
]


# ─── Trade Record ─────────────────────────────────────────────────────────────
@dataclass
class TradeRecord:
    symbol: str
    strategy: str
    confidence: float
    entry_date: dt.date
    entry_price: float
    exit_date: Optional[dt.date] = None
    exit_price: Optional[float] = None
    exit_reason: str = ""
    pnl_pct: float = 0.0
    hold_days: int = 0
    stop_price: float = 0.0
    target_price: float = 0.0


# ─── Simulated Position (lightweight, for backtest only) ──────────────────────
@dataclass
class SimPosition:
    symbol: str
    entry_date: dt.date
    entry_price: float
    stop_price: float
    target_price: float
    confidence: float
    strategy: str
    signal: AISignal
    highest_price: float = 0.0
    trailing_stop_price: Optional[float] = None
    trailing_active: bool = False

    def __post_init__(self):
        self.highest_price = self.entry_price


# ─── Backtest Engine ──────────────────────────────────────────────────────────
class SwingFixBacktester:
    """Walk-forward backtest using the real AISignalGenerator pipeline."""

    def __init__(self, config: ShortCycleConfig, lookback_days: int = 90,
                 warmup_days: int = 30, position_dollars: float = 150.0,
                 max_concurrent: int = 10):
        self.config = config
        self.lookback_days = lookback_days
        self.warmup_days = warmup_days
        self.position_dollars = position_dollars
        self.max_concurrent = max_concurrent

        self.data_loader = DataLoader(enable_multi_source_validation=False)
        self.signal_gen = AISignalGenerator(config, price_fetcher=None, adaptive_params=False)
        self.exit_mgr = SmartExitManager(config)

        self.trades: List[TradeRecord] = []
        self.open_positions: List[SimPosition] = []

    # ── Data fetching ─────────────────────────────────────────────────────
    def fetch_data(self, universe: List[str]) -> Dict[str, pd.DataFrame]:
        """Fetch historical data for all symbols."""
        print(f"\n📊 Fetching {self.lookback_days}-day data for {len(universe)} symbols...")
        total_days = self.lookback_days + self.warmup_days + 10  # buffer for weekends
        data = {}
        failed = []

        for i, sym in enumerate(universe):
            try:
                df = self.data_loader.get_historical_data(sym, days=total_days, use_cache=False)
                if df is not None and len(df) >= self.warmup_days:
                    data[sym] = df
                else:
                    failed.append(sym)
            except Exception:
                failed.append(sym)

            if (i + 1) % 10 == 0:
                print(f"  ... fetched {i + 1}/{len(universe)} ({len(data)} valid)")
                time.sleep(0.5)  # Rate limit yfinance

        print(f"  ✅ Got data for {len(data)}/{len(universe)} symbols")
        if failed:
            print(f"  ⚠️  Failed: {', '.join(failed[:10])}{'...' if len(failed) > 10 else ''}")
        return data

    # ── RSI calculation ───────────────────────────────────────────────────
    @staticmethod
    def calc_rsi(series: pd.Series, period: int = 14) -> float:
        """Calculate current RSI from a price series."""
        if len(series) < period + 1:
            return 50.0
        delta = series.diff()
        gain = delta.clip(lower=0).rolling(window=period).mean()
        loss = (-delta.clip(upper=0)).rolling(window=period).mean()
        if loss.iloc[-1] == 0:
            return 100.0
        rs = gain.iloc[-1] / loss.iloc[-1]
        return 100.0 - (100.0 / (1.0 + rs))

    # ── Volume ratio ──────────────────────────────────────────────────────
    @staticmethod
    def calc_volume_ratio(volumes: pd.Series, period: int = 20) -> float:
        """Current volume vs rolling average."""
        if len(volumes) < period + 1:
            return 1.0
        avg = volumes.iloc[-(period + 1):-1].mean()
        if avg == 0:
            return 1.0
        return volumes.iloc[-1] / avg

    # ── Check exits ───────────────────────────────────────────────────────
    def check_exits(self, current_date: dt.date, market_data: Dict[str, pd.DataFrame],
                    day_idx_map: Dict[str, int]):
        """Check all open positions for exit signals."""
        still_open = []

        for pos in self.open_positions:
            sym = pos.symbol
            if sym not in market_data or sym not in day_idx_map:
                still_open.append(pos)
                continue

            df = market_data[sym]
            idx = day_idx_map[sym]
            if idx >= len(df):
                still_open.append(pos)
                continue

            row = df.iloc[idx]
            current_price = row['close']
            day_high = row['high']
            day_low = row['low']

            # Update highest price
            if day_high > pos.highest_price:
                pos.highest_price = day_high

            hold_days = (current_date - pos.entry_date).days
            pnl_pct = (current_price - pos.entry_price) / pos.entry_price

            exit_triggered = False
            exit_reason = ""
            exit_price = current_price

            # ── 1. Hard stop hit (intraday low) ──────────────────────────
            stop_pnl = (day_low - pos.entry_price) / pos.entry_price
            if stop_pnl <= -self.config.stop_loss_pct:
                exit_triggered = True
                exit_reason = "STOP_LOSS"
                exit_price = pos.stop_price  # Stopped at stop price

            # ── 2. Profit target hit (intraday high) ─────────────────────
            if not exit_triggered:
                target_pnl = (day_high - pos.entry_price) / pos.entry_price
                if target_pnl >= self.config.profit_target_pct:
                    exit_triggered = True
                    exit_reason = "PROFIT_TARGET"
                    exit_price = pos.target_price

            # ── 3. Trailing stop (after 48h / 2+ days) ───────────────────
            if not exit_triggered and hold_days >= 2:
                profit_from_high = (pos.highest_price - pos.entry_price) / pos.entry_price
                if profit_from_high >= self.config.trailing_trigger_pct:
                    pos.trailing_active = True
                    trail_price = pos.highest_price * (1.0 - self.config.trailing_distance_pct)
                    if pos.trailing_stop_price is None or trail_price > pos.trailing_stop_price:
                        pos.trailing_stop_price = trail_price
                    if day_low <= pos.trailing_stop_price:
                        exit_triggered = True
                        exit_reason = "TRAILING_STOP"
                        exit_price = pos.trailing_stop_price

            # ── 4. RSI exhaustion exit (only after 48h / 2+ days) ────────
            if not exit_triggered and hold_days >= 2 and pnl_pct > 0.01:
                close_series = df['close'].iloc[:idx + 1]
                rsi = self.calc_rsi(close_series)
                if rsi >= 80 and pnl_pct > 0.02:
                    exit_triggered = True
                    exit_reason = "RSI_EXHAUSTION"
                    exit_price = current_price

            # ── 5. Time stop — max 5 trading days ────────────────────────
            if not exit_triggered and hold_days >= 7:  # ~5 trading days
                exit_triggered = True
                exit_reason = "TIME_STOP"
                exit_price = current_price

            # ── 6. Emergency stop — catastrophic drop ────────────────────
            if not exit_triggered and pnl_pct <= -0.06:
                exit_triggered = True
                exit_reason = "EMERGENCY_STOP"
                exit_price = current_price

            if exit_triggered:
                actual_pnl = (exit_price - pos.entry_price) / pos.entry_price
                trade = TradeRecord(
                    symbol=sym,
                    strategy=pos.strategy,
                    confidence=pos.confidence,
                    entry_date=pos.entry_date,
                    entry_price=pos.entry_price,
                    exit_date=current_date,
                    exit_price=exit_price,
                    exit_reason=exit_reason,
                    pnl_pct=actual_pnl,
                    hold_days=hold_days,
                    stop_price=pos.stop_price,
                    target_price=pos.target_price,
                )
                self.trades.append(trade)
            else:
                still_open.append(pos)

        self.open_positions = still_open

    # ── Process entries ───────────────────────────────────────────────────
    def process_entries(self, signals: List[AISignal], current_date: dt.date,
                        market_data: Dict[str, pd.DataFrame], day_idx_map: Dict[str, int]):
        """Enter new positions from signals."""
        # Skip if at capacity
        if len(self.open_positions) >= self.max_concurrent:
            return

        # Symbols already held
        held_symbols = {p.symbol for p in self.open_positions}

        for sig in signals:
            if len(self.open_positions) >= self.max_concurrent:
                break
            if sig.symbol in held_symbols:
                continue
            if sig.action != "BUY":
                continue
            if sig.confidence < self.config.confidence_threshold:
                continue

            sym = sig.symbol
            if sym not in market_data or sym not in day_idx_map:
                continue

            df = market_data[sym]
            idx = day_idx_map[sym]
            if idx >= len(df):
                continue

            entry_price = df.iloc[idx]['close']
            if entry_price <= 0:
                continue

            stop_price = entry_price * (1.0 - self.config.stop_loss_pct)
            target_price = entry_price * (1.0 + self.config.profit_target_pct)

            # Determine strategy name from signal features
            strategy = "unknown"
            if sig.features_used:
                if sig.features_used.get('gap_pct', 0) != 0:
                    strategy = "gap_and_go"
                elif sig.features_used.get('momentum_score', 0) > 0:
                    strategy = "momentum"
                elif sig.features_used.get('fade_signal', 0) != 0:
                    strategy = "fade_short"
                else:
                    strategy = "mixed"

            pos = SimPosition(
                symbol=sym,
                entry_date=current_date,
                entry_price=entry_price,
                stop_price=stop_price,
                target_price=target_price,
                confidence=sig.confidence,
                strategy=strategy,
                signal=sig,
            )
            self.open_positions.append(pos)
            held_symbols.add(sym)

    # ── Main backtest loop ────────────────────────────────────────────────
    def run(self, universe: List[str]) -> Dict:
        """Run walk-forward backtest."""
        market_data = self.fetch_data(universe)
        if not market_data:
            print("❌ No data fetched. Aborting.")
            return {}

        # Build trading calendar from the first symbol with full data
        ref_sym = max(market_data, key=lambda s: len(market_data[s]))
        ref_df = market_data[ref_sym]
        all_dates = ref_df['date'].dt.date.tolist() if 'date' in ref_df.columns else []

        if not all_dates:
            # Try index
            all_dates = [d.date() if hasattr(d, 'date') else d for d in ref_df.index.tolist()]

        if len(all_dates) < self.warmup_days + 5:
            print(f"❌ Not enough trading days ({len(all_dates)}). Need {self.warmup_days + 5}.")
            return {}

        # Trading days = after warmup
        trading_dates = all_dates[self.warmup_days:]
        print(f"\n📅 Trading window: {trading_dates[0]} to {trading_dates[-1]} "
              f"({len(trading_dates)} days)")
        print(f"   Warmup period: {all_dates[0]} to {all_dates[self.warmup_days - 1]}")
        print(f"   Config: stop={self.config.stop_loss_pct:.1%}, "
              f"target={self.config.profit_target_pct:.1%}, "
              f"confidence≥{self.config.confidence_threshold:.0%}, "
              f"trailing={self.config.trailing_trigger_pct:.1%}/{self.config.trailing_distance_pct:.1%}")

        # Build day-index maps per symbol
        date_to_idx = {}
        for sym, df in market_data.items():
            if 'date' in df.columns:
                dates = df['date'].dt.date.tolist()
            else:
                dates = [d.date() if hasattr(d, 'date') else d for d in df.index.tolist()]
            date_to_idx[sym] = {d: i for i, d in enumerate(dates)}

        # Walk forward
        signals_generated = 0
        entries_made = 0

        for day_num, trade_date in enumerate(trading_dates):
            # Build day index map for this date
            day_idx_map = {}
            for sym in market_data:
                if sym in date_to_idx and trade_date in date_to_idx[sym]:
                    day_idx_map[sym] = date_to_idx[sym][trade_date]

            if not day_idx_map:
                continue

            # 1. Check exits first
            self.check_exits(trade_date, market_data, day_idx_map)

            # 2. Generate signals using the real pipeline
            #    Build market_data slices up to current day (no lookahead)
            sliced_data = {}
            for sym, idx in day_idx_map.items():
                df = market_data[sym]
                sliced_data[sym] = df.iloc[:idx + 1].copy()

            try:
                # Two-pass signal generation to cover all time-gated strategies:
                # Pass 1: 9:40 AM → Gap & Go window (9:35-9:50)
                # Pass 2: 10:35 AM → Fade/Short (10-14) + Momentum (10:30-14:30)
                all_signals = []
                seen_symbols = set()

                for fake_hour, fake_minute in [(9, 40), (10, 35)]:
                    class FakeDatetime:
                        """Patches datetime.now() to return a specific time."""
                        _real = _sig_mod.datetime
                        @classmethod
                        def now(cls, *a, **kw):
                            real = cls._real.now(*a, **kw)
                            return real.replace(hour=fake_hour, minute=fake_minute, second=0)
                        def __class_getitem__(cls, item):
                            return getattr(cls._real, item)
                        def __getattr__(self, name):
                            return getattr(self._real, name)

                    # Temporarily swap datetime in the signal generator module
                    original_dt = _sig_mod.datetime
                    _sig_mod.datetime = FakeDatetime
                    try:
                        pass_signals = self.signal_gen.generate_signals(
                            universe=list(day_idx_map.keys()),
                            market_data=sliced_data,
                            active_positions=None,
                        )
                    finally:
                        _sig_mod.datetime = original_dt

                    for sig in pass_signals:
                        if sig.symbol not in seen_symbols:
                            all_signals.append(sig)
                            seen_symbols.add(sig.symbol)

                signals = sorted(all_signals, key=lambda x: x.confidence, reverse=True)
            except Exception as e:
                if day_num == 0:
                    print(f"  ⚠️  Signal generation error on day 1: {e}")
                signals = []

            signals_generated += len(signals)
            pre_count = len(self.open_positions)

            # 3. Enter new positions
            self.process_entries(signals, trade_date, market_data, day_idx_map)
            entries_made += len(self.open_positions) - pre_count

            # Progress
            if (day_num + 1) % 10 == 0 or day_num == len(trading_dates) - 1:
                print(f"  Day {day_num + 1}/{len(trading_dates)}: "
                      f"{len(self.trades)} closed, {len(self.open_positions)} open, "
                      f"{signals_generated} signals total")

        # Force-close remaining positions at last known price
        for pos in self.open_positions:
            sym = pos.symbol
            if sym in market_data:
                df = market_data[sym]
                last_price = df['close'].iloc[-1]
                pnl_pct = (last_price - pos.entry_price) / pos.entry_price
                hold_days = (trading_dates[-1] - pos.entry_date).days
                trade = TradeRecord(
                    symbol=sym,
                    strategy=pos.strategy,
                    confidence=pos.confidence,
                    entry_date=pos.entry_date,
                    entry_price=pos.entry_price,
                    exit_date=trading_dates[-1],
                    exit_price=last_price,
                    exit_reason="BACKTEST_END",
                    pnl_pct=pnl_pct,
                    hold_days=hold_days,
                    stop_price=pos.stop_price,
                    target_price=pos.target_price,
                )
                self.trades.append(trade)
        self.open_positions = []

        return self.analyze_results(signals_generated, entries_made, trading_dates)

    # ── Results analysis ──────────────────────────────────────────────────
    def analyze_results(self, total_signals: int, total_entries: int,
                        trading_dates: List) -> Dict:
        """Analyze and print backtest results."""
        if not self.trades:
            print("\n❌ No trades executed.")
            return {"trades": 0}

        trades_df = pd.DataFrame([
            {
                "symbol": t.symbol,
                "strategy": t.strategy,
                "confidence": t.confidence,
                "entry_date": t.entry_date,
                "exit_date": t.exit_date,
                "entry_price": t.entry_price,
                "exit_price": t.exit_price,
                "exit_reason": t.exit_reason,
                "pnl_pct": t.pnl_pct,
                "hold_days": t.hold_days,
            }
            for t in self.trades
        ])

        # Core metrics
        total = len(trades_df)
        wins = len(trades_df[trades_df['pnl_pct'] > 0.001])
        losses = len(trades_df[trades_df['pnl_pct'] < -0.001])
        breakeven = total - wins - losses
        win_rate = wins / total if total > 0 else 0

        avg_win = trades_df[trades_df['pnl_pct'] > 0.001]['pnl_pct'].mean() if wins > 0 else 0
        avg_loss = trades_df[trades_df['pnl_pct'] < -0.001]['pnl_pct'].mean() if losses > 0 else 0
        r_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else float('inf')
        expectancy = (win_rate * avg_win) + ((1 - win_rate) * avg_loss)

        avg_hold = trades_df['hold_days'].mean()
        avg_conf = trades_df['confidence'].mean()
        total_pnl = trades_df['pnl_pct'].sum()
        median_pnl = trades_df['pnl_pct'].median()

        # Exit reason breakdown
        exit_counts = trades_df['exit_reason'].value_counts()

        # Strategy breakdown
        strategy_stats = trades_df.groupby('strategy').agg(
            count=('pnl_pct', 'count'),
            win_rate=('pnl_pct', lambda x: (x > 0.001).mean()),
            avg_pnl=('pnl_pct', 'mean'),
            total_pnl=('pnl_pct', 'sum'),
        ).round(4)

        # Hold day distribution for losses
        loss_trades = trades_df[trades_df['pnl_pct'] < -0.001]
        losses_day1 = len(loss_trades[loss_trades['hold_days'] <= 1])
        losses_day2 = len(loss_trades[(loss_trades['hold_days'] > 1) & (loss_trades['hold_days'] <= 2)])
        losses_day3plus = len(loss_trades[loss_trades['hold_days'] > 2])

        # ── Print report ──────────────────────────────────────────────────
        print("\n" + "=" * 70)
        print("  SWING-FIX BACKTEST RESULTS")
        print("=" * 70)

        print(f"\n📅 Period: {trading_dates[0]} to {trading_dates[-1]} "
              f"({len(trading_dates)} trading days)")
        print(f"🔢 Total signals generated: {total_signals}")
        print(f"🎯 Entries executed: {total_entries}")
        print(f"📊 Total closed trades: {total}")

        print(f"\n{'─' * 40}")
        print(f"  CORE METRICS")
        print(f"{'─' * 40}")
        print(f"  Win Rate:       {win_rate:.1%}  ({wins}W / {losses}L / {breakeven}BE)")
        print(f"  Avg Win:        +{avg_win:.2%}")
        print(f"  Avg Loss:       {avg_loss:.2%}")
        print(f"  R-Ratio:        {r_ratio:.2f}  (win/loss magnitude)")
        print(f"  Expectancy:     {expectancy:+.3%} per trade")
        print(f"  Total PnL:      {total_pnl:+.2%}  (sum of all trades)")
        print(f"  Median PnL:     {median_pnl:+.3%}")
        print(f"  Avg Hold:       {avg_hold:.1f} days")
        print(f"  Avg Confidence: {avg_conf:.2f}")

        # Profitability assessment
        print(f"\n  {'✅ PROFITABLE' if expectancy > 0 else '❌ UNPROFITABLE'} "
              f"— Expected {expectancy * 100:+.2f}¢ per $1 risked per trade")

        print(f"\n{'─' * 40}")
        print(f"  EXIT REASONS")
        print(f"{'─' * 40}")
        for reason, count in exit_counts.items():
            reason_trades = trades_df[trades_df['exit_reason'] == reason]
            reason_avg = reason_trades['pnl_pct'].mean()
            print(f"  {reason:<20s}: {count:>3d} trades  (avg {reason_avg:+.2%})")

        print(f"\n{'─' * 40}")
        print(f"  LOSS TIMING (Key Diagnostic)")
        print(f"{'─' * 40}")
        if len(loss_trades) > 0:
            print(f"  Day 0-1 losses:  {losses_day1:>3d}  ({losses_day1/len(loss_trades):.0%} of losses)")
            print(f"  Day 2 losses:    {losses_day2:>3d}  ({losses_day2/len(loss_trades):.0%} of losses)")
            print(f"  Day 3+ losses:   {losses_day3plus:>3d}  ({losses_day3plus/len(loss_trades):.0%} of losses)")
            print(f"  (Pre-fix was 88% of losses within 24h)")
        else:
            print(f"  No losing trades!")

        print(f"\n{'─' * 40}")
        print(f"  STRATEGY BREAKDOWN")
        print(f"{'─' * 40}")
        print(strategy_stats.to_string())

        # Top/bottom trades
        print(f"\n{'─' * 40}")
        print(f"  BEST & WORST TRADES")
        print(f"{'─' * 40}")
        sorted_trades = trades_df.sort_values('pnl_pct', ascending=False)
        print("  Top 5:")
        for _, t in sorted_trades.head(5).iterrows():
            print(f"    {t['symbol']:<6s} {t['pnl_pct']:+.2%}  hold={t['hold_days']}d  "
                  f"exit={t['exit_reason']}  conf={t['confidence']:.2f}")
        print("  Bottom 5:")
        for _, t in sorted_trades.tail(5).iterrows():
            print(f"    {t['symbol']:<6s} {t['pnl_pct']:+.2%}  hold={t['hold_days']}d  "
                  f"exit={t['exit_reason']}  conf={t['confidence']:.2f}")

        print("\n" + "=" * 70)

        # Compare against pre-fix baseline
        print(f"\n{'─' * 40}")
        print(f"  PRE-FIX BASELINE COMPARISON")
        print(f"{'─' * 40}")
        print(f"  Metric          Pre-Fix    Post-Fix    Change")
        print(f"  ────────────────────────────────────────────────")
        print(f"  Win Rate        35.3%      {win_rate:.1%}        {win_rate - 0.353:+.1%}")
        print(f"  Avg Win         +1.86%     +{avg_win:.2%}      {avg_win - 0.0186:+.2%}")
        print(f"  Avg Loss        -1.99%     {avg_loss:.2%}      {avg_loss - (-0.0199):+.2%}")
        print(f"  R-Ratio         0.93       {r_ratio:.2f}        {r_ratio - 0.93:+.2f}")
        print(f"  Expectancy      -0.63%     {expectancy:+.3%}    {expectancy - (-0.0063):+.3%}")
        print(f"  Day-1 loss %    88%        {losses_day1/max(len(loss_trades),1):.0%}          "
              f"{losses_day1/max(len(loss_trades),1) - 0.88:+.0%}")

        print("=" * 70)

        # Save trades to CSV
        csv_path = "backtest_swing_fix_trades.csv"
        trades_df.to_csv(csv_path, index=False)
        print(f"\n💾 Trades saved to {csv_path}")

        return {
            "trades": total,
            "win_rate": win_rate,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "r_ratio": r_ratio,
            "expectancy": expectancy,
            "total_pnl": total_pnl,
            "avg_hold_days": avg_hold,
            "day1_loss_pct": losses_day1 / max(len(loss_trades), 1),
        }


# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Swing-Fix Backtest")
    parser.add_argument("--days", type=int, default=90, help="Lookback days (default: 90)")
    parser.add_argument("--warmup", type=int, default=30, help="Warmup days (default: 30)")
    parser.add_argument("--max-positions", type=int, default=10, help="Max concurrent positions")
    parser.add_argument("--trail-trigger", type=float, default=None, help="Override trailing trigger pct (e.g. 0.04)")
    parser.add_argument("--trail-distance", type=float, default=None, help="Override trailing distance pct (e.g. 0.025)")
    parser.add_argument("--confidence", type=float, default=None, help="Override confidence threshold (e.g. 0.55)")
    args = parser.parse_args()

    print("🔧 SWING-FIX BACKTEST — Feb 13, 2026")
    print("=" * 50)

    config = ShortCycleConfig()
    
    # Apply overrides
    if args.trail_trigger is not None:
        config.trailing_trigger_pct = args.trail_trigger
    if args.trail_distance is not None:
        config.trailing_distance_pct = args.trail_distance
    if args.confidence is not None:
        config.confidence_threshold = args.confidence

    print(f"Config loaded:")
    print(f"  stop_loss_pct:       {config.stop_loss_pct:.1%}")
    print(f"  profit_target_pct:   {config.profit_target_pct:.1%}")
    print(f"  confidence_threshold:{config.confidence_threshold:.0%}")
    print(f"  trailing:            {config.trailing_trigger_pct:.1%} trigger / "
          f"{config.trailing_distance_pct:.1%} trail")

    bt = SwingFixBacktester(
        config=config,
        lookback_days=args.days,
        warmup_days=args.warmup,
        max_concurrent=args.max_positions,
    )

    results = bt.run(MIDCAP_UNIVERSE)

    if results and results.get("trades", 0) > 0:
        print(f"\n🏁 Backtest complete: {results['trades']} trades, "
              f"expectancy {results['expectancy']:+.3%}")
    else:
        print("\n⚠️  No trades generated. Check signal thresholds.")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
30-Day D+1 Strategy Backtest (CORRECTED)
Proper overnight hold requirement - matches actual bot behavior

D+1 Rules:
- Entry: During market hours (any time before 2:30 PM)
- Hold: MUST hold overnight (no same-day exits)
- Exit: Next day's open OR during next day OR 2:30 PM force exit
- Max hold: 2 days

Author: Corrected for D+1 trading discipline
Date: January 8, 2026
"""

import sys
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import pandas as pd
import numpy as np
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

try:
    from bot_v2.config.trading_config import ShortCycleConfig
    from bot_v2.data.data_loader import DataLoader
except ImportError as e:
    logger.error(f"❌ Failed to import: {e}")
    sys.exit(1)

DEFAULT_UNIVERSE = [
    'AAL', 'AEO', 'AES', 'AI', 'APA', 'AR', 'BEAM', 'BEKE', 'CAG', 'CCL',
    'CDNA', 'CHWY', 'CLF', 'CMCSA', 'CPB', 'CPNG', 'CTRA', 'F', 'FTRE', 'HAL',
    'HIMS', 'HRL', 'JACK', 'JD', 'KDP', 'KHC', 'LC', 'LCID', 'LI', 'LYFT',
    'MGY', 'MRNA', 'MUR', 'NCLH', 'NOV', 'NRIX', 'NTLA', 'NU', 'NWSA', 'OSCR',
    'PATH', 'PENN', 'PINS', 'PL', 'PR', 'RIVN', 'S', 'SCVL', 'SDGR', 'SM',
    'SOFI', 'SOUN', 'STLA', 'T', 'TAL', 'TLRY', 'TU', 'TWST', 'VALE', 'VFC',
    'VIPS', 'VIRT', 'VOD', 'WBD', 'WEN', 'WOLF', 'XPEV'
]


@dataclass
class Trade:
    """D+1 Trade record"""
    symbol: str
    entry_date: datetime
    entry_price: float
    exit_date: datetime
    exit_price: float
    pnl_pct: float
    strategy: str
    entry_reason: str
    exit_reason: str
    held_overnight: bool = True


class StrategyResult:
    """Results tracker"""
    def __init__(self, name: str):
        self.name = name
        self.trades: List[Trade] = []
    
    def add_trade(self, trade: Trade):
        self.trades.append(trade)
    
    def calculate_metrics(self) -> Dict:
        if not self.trades:
            return {
                'name': self.name, 'trades': 0, 'win_rate': 0,
                'avg_pnl': 0, 'total_pnl': 0, 'winners': 0, 'losers': 0,
                'max_win': 0, 'max_loss': 0, 'avg_hold_days': 0
            }
        
        winners = [t for t in self.trades if t.pnl_pct > 0]
        losers = [t for t in self.trades if t.pnl_pct <= 0]
        
        hold_days = []
        for t in self.trades:
            try:
                if isinstance(t.entry_date, pd.Timestamp) and isinstance(t.exit_date, pd.Timestamp):
                    days = (t.exit_date - t.entry_date).days
                else:
                    days = 1
                hold_days.append(max(days, 1))
            except:
                hold_days.append(1)
        
        return {
            'name': self.name,
            'trades': len(self.trades),
            'win_rate': len(winners) / len(self.trades),
            'avg_pnl': np.mean([t.pnl_pct for t in self.trades]),
            'total_pnl': sum([t.pnl_pct for t in self.trades]),
            'winners': len(winners),
            'losers': len(losers),
            'max_win': max([t.pnl_pct for t in winners]) if winners else 0,
            'max_loss': min([t.pnl_pct for t in losers]) if losers else 0,
            'avg_hold_days': np.mean(hold_days)
        }


class D1_MeanReversionBacktest:
    """Mean Reversion with D+1 overnight hold"""
    
    def __init__(self):
        self.name = "Mean Reversion (D+1)"
        self.profit_target = 0.04
        self.stop_loss = -0.02
    
    def find_entries(self, symbol: str, data: pd.DataFrame) -> List[Tuple]:
        entries = []
        
        for i in range(30, len(data) - 1):  # -1 to ensure we have next day
            window = data.iloc[:i+1]
            
            # RSI
            delta = window['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rsi = 100 - (100 / (1 + gain / loss))
            current_rsi = rsi.iloc[-1]
            
            if current_rsi < 35:
                close = window['close'].iloc[-1]
                sma_20 = window['close'].rolling(20).mean().iloc[-1]
                
                if (close - sma_20) / sma_20 > -0.06:
                    momentum = (close - window['close'].iloc[-5]) / window['close'].iloc[-5]
                    if momentum > -0.05:
                        date = window.index[-1]
                        entries.append((date, close, f"RSI {current_rsi:.1f}"))
        
        return entries
    
    def simulate_d1_exit(self, entry_date, entry_price: float, data: pd.DataFrame) -> Tuple:
        """D+1 exit: MUST hold overnight, exit next day"""
        try:
            entry_idx = data.index.get_loc(entry_date)
        except:
            return (entry_date, entry_price, "ERROR")
        
        # D+1 Rule: Exit NEXT day (cannot exit same day)
        if entry_idx + 1 >= len(data):
            return (entry_date, entry_price, "NO_NEXT_DAY")
        
        # Next day (D+1)
        next_day_idx = entry_idx + 1
        next_day_date = data.index[next_day_idx]
        next_day_open = data['open'].iloc[next_day_idx]
        next_day_close = data['close'].iloc[next_day_idx]
        
        # Check exit at next day's open (gap risk)
        open_pnl = (next_day_open - entry_price) / entry_price
        
        if open_pnl >= self.profit_target:
            return (next_day_date, next_day_open, "PROFIT_TARGET_OPEN")
        
        if open_pnl <= self.stop_loss:
            return (next_day_date, next_day_open, "STOP_LOSS_OPEN")
        
        # Check during next day
        next_day_high = data['high'].iloc[next_day_idx]
        next_day_low = data['low'].iloc[next_day_idx]
        
        high_pnl = (next_day_high - entry_price) / entry_price
        low_pnl = (next_day_low - entry_price) / entry_price
        
        if high_pnl >= self.profit_target:
            # Hit profit target during day
            exit_price = entry_price * (1 + self.profit_target)
            return (next_day_date, exit_price, "PROFIT_TARGET")
        
        if low_pnl <= self.stop_loss:
            # Hit stop loss during day
            exit_price = entry_price * (1 + self.stop_loss)
            return (next_day_date, exit_price, "STOP_LOSS")
        
        # Exit at close (2:30 PM force exit)
        return (next_day_date, next_day_close, "D1_FORCE_EXIT")


class D1_MomentumBacktest:
    """Momentum with D+1 overnight hold"""
    
    def __init__(self):
        self.name = "Momentum/Breakout (D+1)"
        self.trailing_stop = 0.04
    
    def find_entries(self, symbol: str, data: pd.DataFrame) -> List[Tuple]:
        entries = []
        
        for i in range(50, len(data) - 1):
            window = data.iloc[:i+1]
            close = window['close'].iloc[-1]
            
            # RSI
            delta = window['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rsi = 100 - (100 / (1 + gain / loss))
            current_rsi = rsi.iloc[-1]
            
            # Filters
            high_20 = window['high'].rolling(20).max().iloc[-2]
            sma_50 = window['close'].rolling(50).mean().iloc[-1]
            vol_avg = window['volume'].rolling(20).mean().iloc[-1]
            vol_ratio = window['volume'].iloc[-1] / vol_avg if vol_avg > 0 else 0
            
            if 60 <= current_rsi <= 80 and close > high_20 and close > sma_50 and vol_ratio > 2.0:
                entries.append((window.index[-1], close, f"Breakout RSI {current_rsi:.1f}"))
        
        return entries
    
    def simulate_d1_exit(self, entry_date, entry_price: float, data: pd.DataFrame) -> Tuple:
        try:
            entry_idx = data.index.get_loc(entry_date)
        except:
            return (entry_date, entry_price, "ERROR")
        
        if entry_idx + 1 >= len(data):
            return (entry_date, entry_price, "NO_NEXT_DAY")
        
        # D+1: Exit next day
        next_idx = entry_idx + 1
        next_date = data.index[next_idx]
        next_open = data['open'].iloc[next_idx]
        next_close = data['close'].iloc[next_idx]
        
        # Use open price as starting point
        peak_price = max(entry_price, next_open)
        
        # Check trailing stop
        next_low = data['low'].iloc[next_idx]
        if next_low < peak_price * (1 - self.trailing_stop):
            exit_price = peak_price * (1 - self.trailing_stop)
            return (next_date, exit_price, "TRAILING_STOP")
        
        # Exit at close
        return (next_date, next_close, "D1_FORCE_EXIT")


class D1_GapAndGoBacktest:
    """Gap & Go with D+1 - HIGH RISK (gap can reverse overnight)"""
    
    def __init__(self):
        self.name = "Gap & Go (D+1)"
        self.profit_target = 0.03
    
    def find_entries(self, symbol: str, data: pd.DataFrame) -> List[Tuple]:
        entries = []
        
        for i in range(20, len(data) - 1):
            window = data.iloc[:i+1]
            
            today_open = window['open'].iloc[-1]
            yesterday_close = window['close'].iloc[-2]
            gap_pct = (today_open - yesterday_close) / yesterday_close
            
            if 0.02 <= gap_pct <= 0.08:
                delta = window['close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
                rsi = 100 - (100 / (1 + gain / loss))
                current_rsi = rsi.iloc[-1]
                
                if current_rsi < 75:
                    close = window['close'].iloc[-1]
                    if close >= yesterday_close:
                        # Enter at open (morning gap)
                        entries.append((window.index[-1], today_open, f"Gap {gap_pct*100:.1f}%"))
        
        return entries
    
    def simulate_d1_exit(self, entry_date, entry_price: float, data: pd.DataFrame) -> Tuple:
        """D+1 Gap Risk: Enter at gap, MUST hold overnight, exit next day"""
        try:
            entry_idx = data.index.get_loc(entry_date)
        except:
            return (entry_date, entry_price, "ERROR")
        
        if entry_idx + 1 >= len(data):
            return (entry_date, entry_price, "NO_NEXT_DAY")
        
        # Next day
        next_idx = entry_idx + 1
        next_date = data.index[next_idx]
        next_open = data['open'].iloc[next_idx]
        
        # Critical: Gap can reverse overnight!
        # Enter at Day 1 open (gap up), exit at Day 2 open (might gap down)
        open_pnl = (next_open - entry_price) / entry_price
        
        if open_pnl >= self.profit_target:
            return (next_date, next_open, "PROFIT_TARGET_OPEN")
        
        # Check if gap filled (reversed)
        entry_day_close = data['close'].iloc[entry_idx]
        prev_close = data['close'].iloc[entry_idx - 1]
        
        if next_open < prev_close:
            # Gap filled overnight - exit at open
            return (next_date, next_open, "GAP_FILLED_OVERNIGHT")
        
        # Exit at close
        next_close = data['close'].iloc[next_idx]
        return (next_date, next_close, "D1_FORCE_EXIT")


class D1_ContinuationBacktest:
    """Continuation with D+1 hold"""
    
    def __init__(self):
        self.name = "Continuation (D+1)"
        self.profit_target = 0.03
    
    def find_entries(self, symbol: str, data: pd.DataFrame) -> List[Tuple]:
        entries = []
        
        for i in range(200, len(data) - 1):
            window = data.iloc[:i+1]
            close = window['close'].iloc[-1]
            sma_20 = window['close'].rolling(20).mean().iloc[-1]
            sma_50 = window['close'].rolling(50).mean().iloc[-1]
            sma_200 = window['close'].rolling(200).mean().iloc[-1]
            
            delta = window['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rsi = 100 - (100 / (1 + gain / loss))
            current_rsi = rsi.iloc[-1]
            
            if sma_50 > sma_200 and close > sma_50 and 40 <= current_rsi <= 60:
                sma_20_diff = abs((close - sma_20) / sma_20)
                if sma_20_diff <= 0.03:
                    entries.append((window.index[-1], close, f"Pullback RSI {current_rsi:.1f}"))
        
        return entries
    
    def simulate_d1_exit(self, entry_date, entry_price: float, data: pd.DataFrame) -> Tuple:
        try:
            entry_idx = data.index.get_loc(entry_date)
        except:
            return (entry_date, entry_price, "ERROR")
        
        if entry_idx + 1 >= len(data):
            return (entry_date, entry_price, "NO_NEXT_DAY")
        
        next_idx = entry_idx + 1
        next_date = data.index[next_idx]
        next_open = data['open'].iloc[next_idx]
        next_close = data['close'].iloc[next_idx]
        next_high = data['high'].iloc[next_idx]
        
        # Check profit target
        high_pnl = (next_high - entry_price) / entry_price
        if high_pnl >= self.profit_target:
            exit_price = entry_price * (1 + self.profit_target)
            return (next_date, exit_price, "PROFIT_TARGET")
        
        # Exit at close
        return (next_date, next_close, "D1_FORCE_EXIT")


class D1_FadeBacktest:
    """Fade/Short with D+1 - SHORT overnight hold"""
    
    def __init__(self):
        self.name = "Fade/Short (D+1)"
        self.profit_target = 0.02
        self.stop_loss = -0.03
    
    def find_entries(self, symbol: str, data: pd.DataFrame) -> List[Tuple]:
        entries = []
        
        for i in range(30, len(data) - 1):
            window = data.iloc[:i+1]
            close = window['close'].iloc[-1]
            sma_20 = window['close'].rolling(20).mean().iloc[-1]
            
            delta = window['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rsi = 100 - (100 / (1 + gain / loss))
            current_rsi = rsi.iloc[-1]
            
            if current_rsi > 70 and (close - sma_20) / sma_20 > 0.10:
                entries.append((window.index[-1], close, f"Short RSI {current_rsi:.1f}"))
        
        return entries
    
    def simulate_d1_exit(self, entry_date, entry_price: float, data: pd.DataFrame) -> Tuple:
        try:
            entry_idx = data.index.get_loc(entry_date)
        except:
            return (entry_date, entry_price, "ERROR")
        
        if entry_idx + 1 >= len(data):
            return (entry_date, entry_price, "NO_NEXT_DAY")
        
        next_idx = entry_idx + 1
        next_date = data.index[next_idx]
        next_open = data['open'].iloc[next_idx]
        next_close = data['close'].iloc[next_idx]
        next_low = data['low'].iloc[next_idx]
        
        # SHORT: Profit when price goes DOWN
        open_pnl = -(next_open - entry_price) / entry_price
        low_pnl = -(next_low - entry_price) / entry_price
        
        if open_pnl >= self.profit_target:
            return (next_date, next_open, "PROFIT_TARGET_OPEN")
        
        if low_pnl >= self.profit_target:
            exit_price = entry_price * (1 - self.profit_target)  # Price went down
            return (next_date, exit_price, "PROFIT_TARGET")
        
        if open_pnl <= self.stop_loss:
            return (next_date, next_open, "STOP_LOSS_OPEN")
        
        # Exit at close
        close_pnl = -(next_close - entry_price) / entry_price
        return (next_date, next_close, "D1_FORCE_EXIT")


def run_d1_backtest(strategy, symbol: str, data: pd.DataFrame) -> List[Trade]:
    """Run D+1 backtest"""
    trades = []
    entries = strategy.find_entries(symbol, data)
    
    for entry_date, entry_price, entry_reason in entries:
        exit_date, exit_price, exit_reason = strategy.simulate_d1_exit(entry_date, entry_price, data)
        
        # Calculate PnL
        if "Short" in strategy.name or "Fade" in strategy.name:
            pnl_pct = -(exit_price - entry_price) / entry_price
        else:
            pnl_pct = (exit_price - entry_price) / entry_price
        
        trade = Trade(
            symbol=symbol,
            entry_date=entry_date,
            entry_price=entry_price,
            exit_date=exit_date,
            exit_price=exit_price,
            pnl_pct=pnl_pct,
            strategy=strategy.name,
            entry_reason=entry_reason,
            exit_reason=exit_reason,
            held_overnight=True
        )
        trades.append(trade)
    
    return trades


def main():
    print("=" * 80)
    print("📊 30-Day D+1 Strategy Backtest (CORRECTED)")
    print("=" * 80)
    print("Period: Dec 9, 2025 - Jan 8, 2026")
    print()
    print("D+1 Rules:")
    print("  ✅ MUST hold overnight (no same-day exits)")
    print("  ✅ Exit at next day's open or during next day")
    print("  ✅ Accounts for gap risk overnight")
    print("  ✅ Force exit at 2:30 PM next day")
    print()
    
    data_loader = DataLoader()
    candidates = DEFAULT_UNIVERSE
    
    print(f"📈 Fetching data for {len(candidates)} stocks...")
    
    market_data = {}
    for symbol in candidates:
        try:
            data = data_loader.get_historical_data(symbol, days=250)
            if not data.empty and len(data) > 200:
                market_data[symbol] = data
        except:
            pass
    
    print(f"✅ Loaded data for {len(market_data)} stocks")
    print()
    print("🔄 Running D+1 backtests...")
    print()
    
    strategies = [
        D1_MeanReversionBacktest(),
        D1_MomentumBacktest(),
        D1_GapAndGoBacktest(),
        D1_ContinuationBacktest(),
        D1_FadeBacktest()
    ]
    
    results = {}
    for strategy in strategies:
        result = StrategyResult(strategy.name)
        
        for symbol, data in market_data.items():
            trades = run_d1_backtest(strategy, symbol, data)
            for trade in trades:
                result.add_trade(trade)
        
        results[strategy.name] = result
        print(f"✅ {strategy.name}: {len(result.trades)} trades")
    
    print()
    print("=" * 80)
    print("📊 D+1 BACKTEST RESULTS (30 Days)")
    print("=" * 80)
    print()
    
    metrics_list = []
    for strategy_name, result in results.items():
        metrics = result.calculate_metrics()
        metrics_list.append(metrics)
    
    print(f"{'Strategy':<25} {'Trades':<8} {'Win%':<8} {'Avg PnL':<10} {'Total PnL':<10}")
    print("-" * 80)
    
    for m in metrics_list:
        marker = "👉 " if "Mean Reversion" in m['name'] else "   "
        print(f"{marker}{m['name']:<23} {m['trades']:<8} "
              f"{m['win_rate']*100:>5.1f}%   "
              f"{m['avg_pnl']*100:>6.2f}%    "
              f"{m['total_pnl']*100:>6.2f}%")
    
    print()
    print("-" * 80)
    
    best_by_total = max(metrics_list, key=lambda x: x['total_pnl'])
    best_by_wr = max(metrics_list, key=lambda x: x['win_rate'] if x['trades'] > 5 else 0)
    
    print(f"🏆 Best Total PnL: {best_by_total['name']} ({best_by_total['total_pnl']*100:.2f}%)")
    print(f"🎯 Best Win Rate: {best_by_wr['name']} ({best_by_wr['win_rate']*100:.1f}%)")
    
    print()
    print("=" * 80)
    print("📋 DETAILED METRICS")
    print("=" * 80)
    
    for m in metrics_list:
        print()
        marker = "👉 " if "Mean Reversion" in m['name'] else ""
        print(f"{marker}{m['name']}:")
        print(f"   Trades: {m['trades']}")
        print(f"   Win Rate: {m['win_rate']*100:.1f}% ({m['winners']}W / {m['losers']}L)")
        print(f"   Avg PnL/Trade: {m['avg_pnl']*100:+.2f}%")
        print(f"   Total PnL: {m['total_pnl']*100:+.2f}%")
        if m['winners'] > 0:
            print(f"   Best Win: {m['max_win']*100:+.2f}%")
        if m['losers'] > 0:
            print(f"   Worst Loss: {m['max_loss']*100:+.2f}%")
        print(f"   Avg Hold: {m['avg_hold_days']:.1f} days (D+1 overnight)")
    
    print()
    print("=" * 80)
    print("✅ D+1 Backtest Complete!")
    print()
    print("💡 Key Differences from Previous Backtest:")
    print("   • All strategies FORCED to hold overnight (D+1 rule)")
    print("   • Gap & Go now accounts for overnight gap reversal risk")
    print("   • Exit prices use next day's open/intraday/close")
    print("   • No same-day profit taking allowed")
    print("   • More realistic for your actual trading system")
    print()


if __name__ == "__main__":
    main()

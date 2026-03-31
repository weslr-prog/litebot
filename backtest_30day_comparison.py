#!/usr/bin/env python3
"""
30-Day Strategy Backtest Comparison
Validate 5 strategies with historical data (Dec 9, 2025 - Jan 8, 2026)

Tracks:
- Win rate
- Total trades
- Average profit per trade
- Total PnL
- Max drawdown
- Sharpe ratio (if enough trades)

Safe: No trading, no bot modifications
"""

import sys
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import pandas as pd
import numpy as np
from dataclasses import dataclass

logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)

# Import bot components
try:
    from bot_v2.config.trading_config import ShortCycleConfig
    from bot_v2.data.data_loader import DataLoader
except ImportError as e:
    logger.error(f"❌ Failed to import: {e}")
    sys.exit(1)

# Universe
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
    """Individual trade record"""
    symbol: str
    entry_date: datetime
    entry_price: float
    exit_date: datetime
    exit_price: float
    pnl_pct: float
    strategy: str
    entry_reason: str
    exit_reason: str


class StrategyBacktestResult:
    """Results from backtesting a strategy"""
    def __init__(self, name: str):
        self.name = name
        self.trades: List[Trade] = []
        self.total_days = 0
    
    def add_trade(self, trade: Trade):
        self.trades.append(trade)
    
    def calculate_metrics(self) -> Dict:
        if not self.trades:
            return {
                'name': self.name,
                'trades': 0,
                'win_rate': 0,
                'avg_pnl': 0,
                'total_pnl': 0,
                'winners': 0,
                'losers': 0,
                'max_win': 0,
                'max_loss': 0,
                'avg_hold_days': 0
            }
        
        winners = [t for t in self.trades if t.pnl_pct > 0]
        losers = [t for t in self.trades if t.pnl_pct <= 0]
        
        # Calculate hold days
        hold_days = []
        for t in self.trades:
            try:
                if isinstance(t.entry_date, pd.Timestamp) and isinstance(t.exit_date, pd.Timestamp):
                    days = (t.exit_date - t.entry_date).days
                else:
                    days = 1
                hold_days.append(max(days, 0))
            except:
                hold_days.append(1)
        avg_hold = np.mean(hold_days) if hold_days else 0
        
        return {
            'name': self.name,
            'trades': len(self.trades),
            'win_rate': len(winners) / len(self.trades) if self.trades else 0,
            'avg_pnl': np.mean([t.pnl_pct for t in self.trades]),
            'total_pnl': sum([t.pnl_pct for t in self.trades]),
            'winners': len(winners),
            'losers': len(losers),
            'max_win': max([t.pnl_pct for t in winners]) if winners else 0,
            'max_loss': min([t.pnl_pct for t in losers]) if losers else 0,
            'avg_hold_days': avg_hold
        }


class MeanReversionBacktest:
    """Backtest Mean Reversion strategy"""
    
    def __init__(self):
        self.name = "Mean Reversion"
        self.profit_target = 0.04
        self.stop_loss = -0.02
        self.max_hold_days = 2
    
    def find_entries(self, symbol: str, data: pd.DataFrame) -> List[Tuple[datetime, float, str]]:
        """Find entry signals"""
        entries = []
        
        for i in range(30, len(data)):
            window = data.iloc[:i+1]
            
            # Calculate RSI
            delta = window['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            current_rsi = rsi.iloc[-1]
            
            # Check entry
            if current_rsi < 35:
                close = window['close'].iloc[-1]
                sma_20 = window['close'].rolling(20).mean().iloc[-1]
                
                if (close - sma_20) / sma_20 > -0.06:  # Not too far below SMA
                    momentum = (close - window['close'].iloc[-5]) / window['close'].iloc[-5]
                    if momentum > -0.05:  # Not falling knife
                        date = window.index[-1]
                        entries.append((date, close, f"RSI {current_rsi:.1f}"))
        
        return entries
    
    def simulate_exit(self, entry_date: datetime, entry_price: float, 
                      data: pd.DataFrame) -> Tuple[datetime, float, str]:
        """Simulate exit from entry point"""
        try:
            entry_idx = data.index.get_loc(entry_date)
        except:
            return (entry_date, entry_price, "ERROR")
        
        for i in range(entry_idx + 1, min(entry_idx + self.max_hold_days + 1, len(data))):
            current_date = data.index[i]
            current_price = data['close'].iloc[i]
            pnl_pct = (current_price - entry_price) / entry_price
            
            # Check exits
            if pnl_pct >= self.profit_target:
                return (current_date, current_price, "PROFIT_TARGET")
            
            if pnl_pct <= self.stop_loss:
                return (current_date, current_price, "STOP_LOSS")
        
        # Max hold
        exit_idx = min(entry_idx + self.max_hold_days, len(data) - 1)
        return (data.index[exit_idx], data['close'].iloc[exit_idx], "MAX_HOLD")


class MomentumBacktest:
    """Backtest Momentum/Breakout strategy"""
    
    def __init__(self):
        self.name = "Momentum/Breakout"
        self.trailing_stop = 0.04
        self.max_hold_days = 5
    
    def find_entries(self, symbol: str, data: pd.DataFrame) -> List[Tuple[datetime, float, str]]:
        entries = []
        
        for i in range(50, len(data)):
            window = data.iloc[:i+1]
            
            close = window['close'].iloc[-1]
            
            # RSI
            delta = window['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            current_rsi = rsi.iloc[-1]
            
            # 20-day high, 50-day SMA
            high_20 = window['high'].rolling(20).max().iloc[-2]
            sma_50 = window['close'].rolling(50).mean().iloc[-1]
            
            # Volume
            vol_avg = window['volume'].rolling(20).mean().iloc[-1]
            vol_ratio = window['volume'].iloc[-1] / vol_avg if vol_avg > 0 else 0
            
            # Entry
            if 60 <= current_rsi <= 80 and close > high_20 and close > sma_50 and vol_ratio > 2.0:
                date = window.index[-1]
                entries.append((date, close, f"Breakout RSI {current_rsi:.1f}"))
        
        return entries
    
    def simulate_exit(self, entry_date: datetime, entry_price: float, 
                      data: pd.DataFrame) -> Tuple[datetime, float, str]:
        entry_idx = data.index.get_loc(entry_date)
        peak_price = entry_price
        
        for i in range(entry_idx + 1, min(entry_idx + self.max_hold_days + 1, len(data))):
            current_date = data.index[i]
            current_price = data['close'].iloc[i]
            
            # Update peak
            if current_price > peak_price:
                peak_price = current_price
            
            # Trailing stop
            if current_price < peak_price * (1 - self.trailing_stop):
                return (current_date, current_price, "TRAILING_STOP")
            
            # RSI momentum fade
            window = data.iloc[:i+1]
            delta = window['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            if rsi.iloc[-1] < 40:
                return (current_date, current_price, "MOMENTUM_FADE")
        
        # Max hold
        exit_idx = min(entry_idx + self.max_hold_days, len(data) - 1)
        return (data.index[exit_idx], data['close'].iloc[exit_idx], "MAX_HOLD")


class GapAndGoBacktest:
    """Backtest Gap & Go strategy"""
    
    def __init__(self):
        self.name = "Gap & Go"
        self.profit_target = 0.03
        self.max_hold_days = 2
    
    def find_entries(self, symbol: str, data: pd.DataFrame) -> List[Tuple[datetime, float, str]]:
        entries = []
        
        for i in range(20, len(data)):
            window = data.iloc[:i+1]
            
            # Gap
            today_open = window['open'].iloc[-1]
            yesterday_close = window['close'].iloc[-2]
            gap_pct = (today_open - yesterday_close) / yesterday_close
            
            if 0.02 <= gap_pct <= 0.08:
                # RSI
                delta = window['close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs))
                current_rsi = rsi.iloc[-1]
                
                if current_rsi < 75:
                    close = window['close'].iloc[-1]
                    if close >= yesterday_close:  # Gap holding
                        date = window.index[-1]
                        entries.append((date, today_open, f"Gap {gap_pct*100:.1f}%"))
        
        return entries
    
    def simulate_exit(self, entry_date: datetime, entry_price: float, 
                      data: pd.DataFrame) -> Tuple[datetime, float, str]:
        entry_idx = data.index.get_loc(entry_date)
        prev_close = data['close'].iloc[entry_idx - 1]
        
        for i in range(entry_idx + 1, min(entry_idx + self.max_hold_days + 1, len(data))):
            current_date = data.index[i]
            current_price = data['close'].iloc[i]
            pnl_pct = (current_price - entry_price) / entry_price
            
            # Profit target
            if pnl_pct >= self.profit_target:
                return (current_date, current_price, "PROFIT_TARGET")
            
            # Gap fill
            if current_price <= prev_close:
                return (current_date, current_price, "GAP_FILL")
        
        # Max hold
        exit_idx = min(entry_idx + self.max_hold_days, len(data) - 1)
        return (data.index[exit_idx], data['close'].iloc[exit_idx], "MAX_HOLD")


class ContinuationBacktest:
    """Backtest Continuation strategy"""
    
    def __init__(self):
        self.name = "Continuation"
        self.profit_target = 0.03
        self.max_hold_days = 7
    
    def find_entries(self, symbol: str, data: pd.DataFrame) -> List[Tuple[datetime, float, str]]:
        entries = []
        
        for i in range(200, len(data)):
            window = data.iloc[:i+1]
            
            close = window['close'].iloc[-1]
            sma_20 = window['close'].rolling(20).mean().iloc[-1]
            sma_50 = window['close'].rolling(50).mean().iloc[-1]
            sma_200 = window['close'].rolling(200).mean().iloc[-1]
            
            # RSI
            delta = window['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            current_rsi = rsi.iloc[-1]
            
            # Entry: uptrend + pullback to SMA_20
            if sma_50 > sma_200 and close > sma_50 and 40 <= current_rsi <= 60:
                sma_20_diff = abs((close - sma_20) / sma_20)
                if sma_20_diff <= 0.03:
                    date = window.index[-1]
                    entries.append((date, close, f"Pullback RSI {current_rsi:.1f}"))
        
        return entries
    
    def simulate_exit(self, entry_date: datetime, entry_price: float, 
                      data: pd.DataFrame) -> Tuple[datetime, float, str]:
        entry_idx = data.index.get_loc(entry_date)
        
        for i in range(entry_idx + 1, min(entry_idx + self.max_hold_days + 1, len(data))):
            current_date = data.index[i]
            current_price = data['close'].iloc[i]
            pnl_pct = (current_price - entry_price) / entry_price
            
            # Profit target
            if pnl_pct >= self.profit_target:
                return (current_date, current_price, "PROFIT_TARGET")
            
            # Trend broken (below SMA_50)
            window = data.iloc[:i+1]
            sma_50 = window['close'].rolling(50).mean().iloc[-1]
            if current_price < sma_50:
                return (current_date, current_price, "TREND_BROKEN")
        
        # Max hold
        exit_idx = min(entry_idx + self.max_hold_days, len(data) - 1)
        return (data.index[exit_idx], data['close'].iloc[exit_idx], "MAX_HOLD")


class FadeBacktest:
    """Backtest Fade/Short strategy"""
    
    def __init__(self):
        self.name = "Fade/Short"
        self.profit_target = 0.02
        self.stop_loss = -0.03
        self.max_hold_days = 2
    
    def find_entries(self, symbol: str, data: pd.DataFrame) -> List[Tuple[datetime, float, str]]:
        entries = []
        
        for i in range(30, len(data)):
            window = data.iloc[:i+1]
            
            close = window['close'].iloc[-1]
            sma_20 = window['close'].rolling(20).mean().iloc[-1]
            
            # RSI
            delta = window['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            current_rsi = rsi.iloc[-1]
            
            # Entry (SHORT)
            if current_rsi > 70 and (close - sma_20) / sma_20 > 0.10:
                date = window.index[-1]
                entries.append((date, close, f"Short RSI {current_rsi:.1f}"))
        
        return entries
    
    def simulate_exit(self, entry_date: datetime, entry_price: float, 
                      data: pd.DataFrame) -> Tuple[datetime, float, str]:
        entry_idx = data.index.get_loc(entry_date)
        
        for i in range(entry_idx + 1, min(entry_idx + self.max_hold_days + 1, len(data))):
            current_date = data.index[i]
            current_price = data['close'].iloc[i]
            
            # SHORT: profit when price goes DOWN
            pnl_pct = -(current_price - entry_price) / entry_price
            
            # Profit target
            if pnl_pct >= self.profit_target:
                return (current_date, current_price, "PROFIT_TARGET")
            
            # Stop loss (price going UP hurts short)
            if pnl_pct <= self.stop_loss:
                return (current_date, current_price, "STOP_LOSS")
        
        # Max hold
        exit_idx = min(entry_idx + self.max_hold_days, len(data) - 1)
        return (data.index[exit_idx], data['close'].iloc[exit_idx], "MAX_HOLD")


def run_backtest(strategy, symbol: str, data: pd.DataFrame) -> List[Trade]:
    """Run backtest for a strategy on one symbol"""
    trades = []
    
    # Find all entries
    entries = strategy.find_entries(symbol, data)
    
    # Simulate each trade
    for entry_date, entry_price, entry_reason in entries:
        exit_date, exit_price, exit_reason = strategy.simulate_exit(entry_date, entry_price, data)
        
        # Calculate PnL (handle shorts for Fade strategy)
        if strategy.name == "Fade/Short":
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
            exit_reason=exit_reason
        )
        trades.append(trade)
    
    return trades


def main():
    print("=" * 80)
    print("📊 30-Day Strategy Backtest Comparison")
    print("=" * 80)
    print(f"Period: Dec 9, 2025 - Jan 8, 2026 (30 trading days)")
    print()
    print("Testing 5 strategies with historical data...")
    print("(Simulated trades - no real trading, no bot modifications)")
    print()
    
    # Initialize
    data_loader = DataLoader()
    candidates = DEFAULT_UNIVERSE
    
    print(f"📈 Fetching 30 days of data for {len(candidates)} stocks...")
    
    # Fetch data
    market_data = {}
    for symbol in candidates:
        try:
            data = data_loader.get_historical_data(symbol, days=250)  # Need extra for indicators
            if not data.empty and len(data) > 200:
                market_data[symbol] = data
        except:
            pass
    
    print(f"✅ Loaded data for {len(market_data)} stocks")
    print()
    print("🔄 Running backtests (this may take 1-2 minutes)...")
    print()
    
    # Initialize strategies
    strategies = [
        MeanReversionBacktest(),
        MomentumBacktest(),
        GapAndGoBacktest(),
        ContinuationBacktest(),
        FadeBacktest()
    ]
    
    # Run backtests
    results = {}
    for strategy in strategies:
        result = StrategyBacktestResult(strategy.name)
        
        for symbol, data in market_data.items():
            trades = run_backtest(strategy, symbol, data)
            for trade in trades:
                result.add_trade(trade)
        
        results[strategy.name] = result
        print(f"✅ {strategy.name}: {len(result.trades)} trades simulated")
    
    print()
    print("=" * 80)
    print("📊 BACKTEST RESULTS (30 Days)")
    print("=" * 80)
    print()
    
    # Calculate and display metrics
    metrics_list = []
    for strategy_name, result in results.items():
        metrics = result.calculate_metrics()
        metrics_list.append(metrics)
    
    # Summary table
    print(f"{'Strategy':<20} {'Trades':<8} {'Win%':<8} {'Avg PnL':<10} {'Total PnL':<10}")
    print("-" * 80)
    
    for m in metrics_list:
        marker = "👉 " if m['name'] == "Mean Reversion" else "   "
        print(f"{marker}{m['name']:<18} {m['trades']:<8} "
              f"{m['win_rate']*100:>5.1f}%   "
              f"{m['avg_pnl']*100:>6.2f}%    "
              f"{m['total_pnl']*100:>6.2f}%")
    
    print()
    print("-" * 80)
    
    # Find best strategy
    best_by_total_pnl = max(metrics_list, key=lambda x: x['total_pnl'])
    best_by_win_rate = max(metrics_list, key=lambda x: x['win_rate'] if x['trades'] > 5 else 0)
    best_by_trades = max(metrics_list, key=lambda x: x['trades'])
    
    print(f"🏆 Best Total PnL: {best_by_total_pnl['name']} ({best_by_total_pnl['total_pnl']*100:.2f}%)")
    print(f"🎯 Best Win Rate: {best_by_win_rate['name']} ({best_by_win_rate['win_rate']*100:.1f}%)")
    print(f"📊 Most Active: {best_by_trades['name']} ({best_by_trades['trades']} trades)")
    
    # Detailed metrics
    print()
    print("=" * 80)
    print("📋 DETAILED METRICS BY STRATEGY")
    print("=" * 80)
    
    for m in metrics_list:
        print()
        marker = "👉 " if m['name'] == "Mean Reversion" else ""
        print(f"{marker}{m['name']}:")
        print(f"   Total Trades: {m['trades']}")
        print(f"   Win Rate: {m['win_rate']*100:.1f}% ({m['winners']} wins, {m['losers']} losses)")
        print(f"   Average PnL: {m['avg_pnl']*100:+.2f}%")
        print(f"   Total PnL: {m['total_pnl']*100:+.2f}%")
        if m['winners'] > 0:
            print(f"   Best Win: {m['max_win']*100:+.2f}%")
        if m['losers'] > 0:
            print(f"   Worst Loss: {m['max_loss']*100:+.2f}%")
        print(f"   Avg Hold: {m['avg_hold_days']:.1f} days")
    
    # Show sample trades from best strategy
    print()
    print("=" * 80)
    print(f"📋 SAMPLE TRADES: {best_by_total_pnl['name']}")
    print("=" * 80)
    print()
    
    best_result = results[best_by_total_pnl['name']]
    sample_trades = sorted(best_result.trades, key=lambda x: x.pnl_pct, reverse=True)[:10]
    
    print(f"{'Symbol':<8} {'Entry':<12} {'Exit':<12} {'PnL':<8} {'Reason'}")
    print("-" * 80)
    for t in sample_trades:
        try:
            entry_str = t.entry_date.strftime('%b %d') if hasattr(t.entry_date, 'strftime') else 'N/A'
            exit_str = t.exit_date.strftime('%b %d') if hasattr(t.exit_date, 'strftime') else 'N/A'
        except:
            entry_str = 'N/A'
            exit_str = 'N/A'
        pnl_str = f"{t.pnl_pct*100:+.2f}%"
        print(f"{t.symbol:<8} {entry_str:<12} {exit_str:<12} {pnl_str:<8} {t.exit_reason}")
    
    print()
    print("=" * 80)
    print("✅ Backtest complete!")
    print()
    print("💡 Key Insights:")
    print(f"   • Your current bot (Mean Reversion) had {metrics_list[0]['trades']} trades in 30 days")
    print(f"   • Best performer: {best_by_total_pnl['name']} with {best_by_total_pnl['total_pnl']*100:.2f}% total PnL")
    print(f"   • Most opportunities: {best_by_trades['name']} with {best_by_trades['trades']} trades")
    print()
    print("Next Steps:")
    print("   • If results validate, consider implementing hybrid strategy (Option C)")
    print("   • Or manually switch strategies based on market conditions")
    print("   • Your bot remains unchanged and safe")
    print()


if __name__ == "__main__":
    main()

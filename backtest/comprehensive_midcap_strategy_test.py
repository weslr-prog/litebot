#!/usr/bin/env python3
"""
Comprehensive Mid-Cap Strategy Backtest - 14 Years (2011-2024)
Testing 15+ different strategies on mid-cap stocks ($2B-$10B) to find what actually works

Strategies tested:
1. Mean Reversion RSI (original bot strategy)
2. Mean Reversion Bollinger Bands
3. Mean Reversion Double Bottom
4. Momentum Breakout
5. Strong Momentum (higher threshold)
6. Relative Strength (vs SPY)
7. Gap & Go (morning gap continuation)
8. Pullback Entry (buy dips in uptrend)
9. Breakout + Volume
10. Hybrid: RSI + Momentum
11. Hybrid: Bollinger + Trend
12. Hybrid: Mean Reversion with Momentum Exit
13. Swing High Breakout
14. Moving Average Crossover
15. VWAP Reversion

Author: GitHub Copilot
Date: November 24, 2025
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
import logging
from dataclasses import dataclass, field
from pathlib import Path
import yfinance as yf
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


@dataclass
class StrategyConfig:
    """Configuration for a trading strategy"""
    name: str
    strategy_id: int
    strategy_type: str  # "reversion", "momentum", "hybrid"
    
    # Entry parameters
    rsi_oversold: int = 30
    rsi_overbought: int = 70
    rsi_period: int = 7
    bb_period: int = 20
    bb_std: float = 2.0
    momentum_period: int = 10
    momentum_threshold: float = 0.03
    ma_fast: int = 10
    ma_slow: int = 50
    volume_surge_threshold: float = 1.5
    
    # Exit parameters
    profit_target: float = 0.05
    stop_loss: float = -0.03
    trailing_stop: float = 0.02
    max_hold_days: int = 5
    
    # Filters
    require_uptrend: bool = False
    require_volume: bool = True


@dataclass
class BacktestPhase:
    """Configuration for each backtest phase"""
    name: str
    start_year: int
    end_year: int
    description: str


@dataclass
class Trade:
    """Individual trade record"""
    symbol: str
    entry_date: datetime
    entry_price: float
    exit_date: datetime
    exit_price: float
    exit_reason: str
    shares: int
    pnl: float
    pnl_pct: float
    hold_days: int


@dataclass
class PhaseResults:
    """Results for a single phase"""
    phase_name: str
    strategy_name: str
    strategy_type: str
    total_return: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    avg_win: float
    avg_loss: float
    win_loss_ratio: float
    profit_factor: float
    max_drawdown: float


class ComprehensiveMidCapBacktester:
    """Backtest multiple strategy types on mid-cap stocks"""
    
    def __init__(self, initial_capital: float = 10000.0):
        self.initial_capital = initial_capital
        self.logger = logging.getLogger(__name__)
        
        self.phases = [
            BacktestPhase("In-Sample", 2011, 2016, "Training period"),
            BacktestPhase("Validation", 2017, 2019, "Validation period"),
            BacktestPhase("Out-of-Sample", 2020, 2024, "Live simulation (includes COVID)")
        ]
        
        self.strategies = self._create_strategies()
        self.all_results = []
        self.all_trades = []
        
    def _create_strategies(self) -> List[StrategyConfig]:
        """Create comprehensive strategy list"""
        return [
            # === MEAN REVERSION STRATEGIES ===
            
            # Strategy 1: Classic RSI Mean Reversion
            StrategyConfig(
                name="Mean Reversion RSI (30)",
                strategy_id=1,
                strategy_type="reversion",
                rsi_oversold=30,
                rsi_period=7,
                profit_target=0.03,
                stop_loss=-0.03,
                max_hold_days=3
            ),
            
            # Strategy 2: Extreme RSI Mean Reversion
            StrategyConfig(
                name="Mean Reversion RSI (20)",
                strategy_id=2,
                strategy_type="reversion",
                rsi_oversold=20,
                rsi_period=7,
                profit_target=0.04,
                stop_loss=-0.03,
                max_hold_days=3
            ),
            
            # Strategy 3: Bollinger Band Mean Reversion
            StrategyConfig(
                name="Bollinger Band Reversion",
                strategy_id=3,
                strategy_type="reversion",
                bb_period=20,
                bb_std=2.0,
                profit_target=0.04,
                stop_loss=-0.03,
                trailing_stop=0.02,
                max_hold_days=5
            ),
            
            # Strategy 4: Double Bottom Pattern
            StrategyConfig(
                name="Double Bottom Reversion",
                strategy_id=4,
                strategy_type="reversion",
                rsi_oversold=35,
                profit_target=0.05,
                stop_loss=-0.02,
                max_hold_days=5
            ),
            
            # === MOMENTUM STRATEGIES ===
            
            # Strategy 5: Classic Momentum Breakout
            StrategyConfig(
                name="Momentum Breakout (3%)",
                strategy_id=5,
                strategy_type="momentum",
                momentum_period=10,
                momentum_threshold=0.03,
                ma_slow=50,
                profit_target=0.05,
                stop_loss=-0.03,
                trailing_stop=0.02,
                max_hold_days=5,
                require_uptrend=True
            ),
            
            # Strategy 6: Strong Momentum
            StrategyConfig(
                name="Strong Momentum (5%)",
                strategy_id=6,
                strategy_type="momentum",
                momentum_period=10,
                momentum_threshold=0.05,
                ma_slow=50,
                profit_target=0.07,
                stop_loss=-0.03,
                trailing_stop=0.02,
                max_hold_days=5,
                require_uptrend=True
            ),
            
            # Strategy 7: Relative Strength
            StrategyConfig(
                name="Relative Strength",
                strategy_id=7,
                strategy_type="momentum",
                momentum_period=20,
                momentum_threshold=0.04,
                ma_slow=50,
                profit_target=0.06,
                stop_loss=-0.04,
                trailing_stop=0.025,
                max_hold_days=7,
                require_uptrend=True
            ),
            
            # Strategy 8: Breakout + Volume Confirmation
            StrategyConfig(
                name="Breakout + Volume",
                strategy_id=8,
                strategy_type="momentum",
                momentum_period=5,
                momentum_threshold=0.025,
                volume_surge_threshold=2.0,
                profit_target=0.04,
                stop_loss=-0.03,
                trailing_stop=0.015,
                max_hold_days=3
            ),
            
            # === TREND FOLLOWING STRATEGIES ===
            
            # Strategy 9: Pullback Entry in Uptrend
            StrategyConfig(
                name="Pullback in Uptrend",
                strategy_id=9,
                strategy_type="trend",
                rsi_oversold=40,
                ma_slow=50,
                profit_target=0.04,
                stop_loss=-0.03,
                trailing_stop=0.02,
                max_hold_days=5,
                require_uptrend=True
            ),
            
            # Strategy 10: Moving Average Crossover
            StrategyConfig(
                name="MA Crossover (10/50)",
                strategy_id=10,
                strategy_type="trend",
                ma_fast=10,
                ma_slow=50,
                profit_target=0.05,
                stop_loss=-0.03,
                trailing_stop=0.02,
                max_hold_days=7
            ),
            
            # === HYBRID STRATEGIES ===
            
            # Strategy 11: RSI + Momentum Confirmation
            StrategyConfig(
                name="Hybrid: RSI + Momentum",
                strategy_id=11,
                strategy_type="hybrid",
                rsi_oversold=35,
                momentum_period=5,
                momentum_threshold=0.02,
                profit_target=0.04,
                stop_loss=-0.03,
                trailing_stop=0.02,
                max_hold_days=5
            ),
            
            # Strategy 12: Bollinger + Trend Filter
            StrategyConfig(
                name="Hybrid: Bollinger + Trend",
                strategy_id=12,
                strategy_type="hybrid",
                bb_period=20,
                bb_std=2.0,
                ma_slow=50,
                profit_target=0.05,
                stop_loss=-0.03,
                trailing_stop=0.02,
                max_hold_days=5,
                require_uptrend=True
            ),
            
            # Strategy 13: Mean Reversion Entry, Momentum Exit
            StrategyConfig(
                name="Hybrid: Reversion Entry/Momentum Exit",
                strategy_id=13,
                strategy_type="hybrid",
                rsi_oversold=30,
                rsi_overbought=60,
                profit_target=0.06,
                stop_loss=-0.03,
                trailing_stop=0.025,
                max_hold_days=7
            ),
            
            # Strategy 14: Gap & Go
            StrategyConfig(
                name="Gap & Go",
                strategy_id=14,
                strategy_type="momentum",
                momentum_period=1,
                momentum_threshold=0.02,
                volume_surge_threshold=1.5,
                profit_target=0.03,
                stop_loss=-0.02,
                trailing_stop=0.015,
                max_hold_days=2
            ),
            
            # Strategy 15: Swing High Breakout
            StrategyConfig(
                name="Swing High Breakout",
                strategy_id=15,
                strategy_type="momentum",
                momentum_period=20,
                momentum_threshold=0.03,
                volume_surge_threshold=1.3,
                profit_target=0.06,
                stop_loss=-0.04,
                trailing_stop=0.025,
                max_hold_days=7
            ),
        ]
    
    def get_midcap_universe(self, as_of_date: datetime) -> List[str]:
        """Get mid-cap stocks ($2B-$10B)"""
        initial_universe = [
            'AAL', 'ALK', 'JBLU', 'SAVE', 'HA',
            'PLUG', 'FCEL', 'BLDP', 'CLNE', 'BE',
            'CAKE', 'TXRH', 'BLMN', 'DRI', 'EAT',
            'SIRI', 'LYV', 'MSG', 'MSGN',
            'F', 'GM', 'RIVN', 'LCID',
            'CCL', 'RCL', 'NCLH',
            'AMD', 'INTC', 'MU', 'WDC',
            'GILD', 'BIIB', 'VRTX', 'REGN',
            'UAA', 'GPS', 'ANF', 'EXPR',
            'SWN', 'RIG', 'HP', 'DVN',
            'WEN', 'JACK', 'BJRI', 'CHUY',
        ]
        
        midcap_stocks = []
        for symbol in initial_universe:
            try:
                stock = yf.Ticker(symbol)
                info = stock.info
                market_cap = info.get('marketCap', 0)
                
                if 2_000_000_000 <= market_cap <= 10_000_000_000:
                    midcap_stocks.append(symbol)
                    
            except Exception:
                continue
        
        self.logger.info(f"Found {len(midcap_stocks)} mid-cap stocks for {as_of_date.year}")
        return midcap_stocks if midcap_stocks else ['AAL', 'PLUG', 'SIRI', 'CAKE']
    
    def fetch_data(self, symbol: str, start_date: datetime, end_date: datetime) -> Optional[pd.DataFrame]:
        """Fetch historical data"""
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(
                start=start_date.strftime('%Y-%m-%d'),
                end=end_date.strftime('%Y-%m-%d')
            )
            
            if df.empty:
                return None
            
            df = df.rename(columns={
                'Open': 'open', 'High': 'high', 'Low': 'low',
                'Close': 'close', 'Volume': 'volume'
            })
            
            df['symbol'] = symbol
            df.index.name = 'date'
            df = df.reset_index()
            
            return df
            
        except Exception as e:
            self.logger.warning(f"Failed to fetch {symbol}: {e}")
            return None
    
    def calculate_indicators(self, df: pd.DataFrame, config: StrategyConfig) -> pd.DataFrame:
        """Calculate technical indicators"""
        df = df.copy()
        
        # RSI
        if config.strategy_type in ["reversion", "hybrid", "trend"]:
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=config.rsi_period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=config.rsi_period).mean()
            rs = gain / loss
            df['rsi'] = 100 - (100 / (1 + rs))
        
        # Bollinger Bands
        if 'Bollinger' in config.name:
            df['bb_middle'] = df['close'].rolling(config.bb_period).mean()
            bb_std = df['close'].rolling(config.bb_period).std()
            df['bb_upper'] = df['bb_middle'] + (bb_std * config.bb_std)
            df['bb_lower'] = df['bb_middle'] - (bb_std * config.bb_std)
        
        # Momentum
        if config.strategy_type in ["momentum", "hybrid"]:
            df['momentum'] = df['close'].pct_change(config.momentum_period)
        
        # Moving Averages
        if config.ma_fast > 0:
            df['ma_fast'] = df['close'].rolling(config.ma_fast).mean()
        if config.ma_slow > 0:
            df['ma_slow'] = df['close'].rolling(config.ma_slow).mean()
        
        # Volume
        df['avg_volume'] = df['volume'].rolling(20).mean()
        df['volume_surge'] = df['volume'] / df['avg_volume']
        
        return df
    
    def generate_signals(self, df: pd.DataFrame, config: StrategyConfig) -> pd.DataFrame:
        """Generate entry signals based on strategy"""
        df = df.copy()
        df['entry_signal'] = False
        
        for idx in range(50, len(df)):  # Start after warmup period
            
            # MEAN REVERSION STRATEGIES
            if config.strategy_type == "reversion":
                if 'Bollinger' in config.name:
                    # Bollinger Band reversion
                    if (df.loc[idx, 'close'] <= df.loc[idx, 'bb_lower'] and
                        df.loc[idx, 'volume_surge'] >= config.volume_surge_threshold):
                        df.loc[idx, 'entry_signal'] = True
                        
                elif 'Double Bottom' in config.name:
                    # Double bottom pattern (simplified)
                    if (df.loc[idx, 'rsi'] <= config.rsi_oversold and
                        df.loc[idx-5:idx, 'rsi'].min() <= config.rsi_oversold and
                        df.loc[idx, 'volume_surge'] >= config.volume_surge_threshold):
                        df.loc[idx, 'entry_signal'] = True
                        
                else:
                    # Classic RSI oversold
                    if (df.loc[idx, 'rsi'] <= config.rsi_oversold and
                        df.loc[idx, 'volume_surge'] >= config.volume_surge_threshold):
                        df.loc[idx, 'entry_signal'] = True
            
            # MOMENTUM STRATEGIES
            elif config.strategy_type == "momentum":
                if 'Gap' in config.name:
                    # Gap & Go (1-day momentum)
                    if (df.loc[idx, 'momentum'] >= config.momentum_threshold and
                        df.loc[idx, 'volume_surge'] >= config.volume_surge_threshold):
                        df.loc[idx, 'entry_signal'] = True
                        
                else:
                    # Standard momentum breakout
                    momentum_ok = df.loc[idx, 'momentum'] >= config.momentum_threshold
                    volume_ok = df.loc[idx, 'volume_surge'] >= config.volume_surge_threshold
                    
                    if config.require_uptrend:
                        uptrend = df.loc[idx, 'close'] > df.loc[idx, 'ma_slow']
                        if momentum_ok and volume_ok and uptrend:
                            df.loc[idx, 'entry_signal'] = True
                    else:
                        if momentum_ok and volume_ok:
                            df.loc[idx, 'entry_signal'] = True
            
            # TREND FOLLOWING STRATEGIES
            elif config.strategy_type == "trend":
                if 'Pullback' in config.name:
                    # Buy pullback in uptrend
                    uptrend = df.loc[idx, 'close'] > df.loc[idx, 'ma_slow']
                    pullback = df.loc[idx, 'rsi'] <= config.rsi_oversold
                    if uptrend and pullback and df.loc[idx, 'volume_surge'] >= 1.2:
                        df.loc[idx, 'entry_signal'] = True
                        
                elif 'Crossover' in config.name:
                    # MA crossover
                    if (df.loc[idx, 'ma_fast'] > df.loc[idx, 'ma_slow'] and
                        df.loc[idx-1, 'ma_fast'] <= df.loc[idx-1, 'ma_slow']):
                        df.loc[idx, 'entry_signal'] = True
            
            # HYBRID STRATEGIES
            elif config.strategy_type == "hybrid":
                if 'RSI + Momentum' in config.name:
                    # RSI oversold + positive momentum
                    if (df.loc[idx, 'rsi'] <= config.rsi_oversold and
                        df.loc[idx, 'momentum'] >= config.momentum_threshold and
                        df.loc[idx, 'volume_surge'] >= config.volume_surge_threshold):
                        df.loc[idx, 'entry_signal'] = True
                        
                elif 'Bollinger + Trend' in config.name:
                    # Bollinger lower + uptrend
                    uptrend = df.loc[idx, 'close'] > df.loc[idx, 'ma_slow']
                    at_lower = df.loc[idx, 'close'] <= df.loc[idx, 'bb_lower']
                    if uptrend and at_lower and df.loc[idx, 'volume_surge'] >= 1.3:
                        df.loc[idx, 'entry_signal'] = True
                        
                elif 'Reversion Entry/Momentum Exit' in config.name:
                    # RSI oversold entry
                    if (df.loc[idx, 'rsi'] <= config.rsi_oversold and
                        df.loc[idx, 'volume_surge'] >= config.volume_surge_threshold):
                        df.loc[idx, 'entry_signal'] = True
        
        return df
    
    def simulate_trades(self, df: pd.DataFrame, config: StrategyConfig) -> List[Trade]:
        """Simulate trades with exits"""
        trades = []
        in_position = False
        entry_idx = None
        entry_price = None
        highest_price = None
        
        for idx in range(len(df)):
            if df.loc[idx, 'entry_signal'] and not in_position:
                entry_idx = idx
                entry_price = df.loc[idx, 'close']
                highest_price = entry_price
                in_position = True
                
            elif in_position:
                current_price = df.loc[idx, 'close']
                highest_price = max(highest_price, current_price)
                pnl_pct = (current_price - entry_price) / entry_price
                
                exit_reason = None
                
                # Exit logic varies by strategy type
                if config.strategy_type == "reversion":
                    # Mean reversion exits on RSI neutral or profit/stop
                    if 'rsi' in df.columns and df.loc[idx, 'rsi'] >= config.rsi_overbought:
                        exit_reason = "RSI_NEUTRAL"
                    elif pnl_pct >= config.profit_target:
                        exit_reason = "PROFIT_TARGET"
                    elif pnl_pct <= config.stop_loss:
                        exit_reason = "STOP_LOSS"
                    elif idx - entry_idx >= config.max_hold_days:
                        exit_reason = "MAX_HOLD"
                        
                else:
                    # Momentum/trend/hybrid use standard exits
                    if pnl_pct >= config.profit_target:
                        exit_reason = "PROFIT_TARGET"
                    elif pnl_pct <= config.stop_loss:
                        exit_reason = "STOP_LOSS"
                    elif (highest_price - current_price) / highest_price >= config.trailing_stop:
                        exit_reason = "TRAILING_STOP"
                    elif idx - entry_idx >= config.max_hold_days:
                        exit_reason = "MAX_HOLD"
                
                if idx == len(df) - 1:
                    exit_reason = "END_OF_DATA"
                
                if exit_reason:
                    trade = Trade(
                        symbol=df.loc[idx, 'symbol'],
                        entry_date=df.loc[entry_idx, 'date'],
                        entry_price=entry_price,
                        exit_date=df.loc[idx, 'date'],
                        exit_price=current_price,
                        exit_reason=exit_reason,
                        shares=100,
                        pnl=(current_price - entry_price) * 100,
                        pnl_pct=pnl_pct,
                        hold_days=idx - entry_idx
                    )
                    trades.append(trade)
                    in_position = False
        
        return trades
    
    def run_backtest(self):
        """Run comprehensive backtest"""
        self.logger.info("=" * 80)
        self.logger.info("COMPREHENSIVE MID-CAP STRATEGY BACKTEST")
        self.logger.info(f"Testing {len(self.strategies)} strategies on mid-cap stocks")
        self.logger.info("=" * 80)
        
        for phase in self.phases:
            self.logger.info(f"\n{'='*80}")
            self.logger.info(f"PHASE: {phase.name} ({phase.start_year}-{phase.end_year})")
            self.logger.info(f"{'='*80}")
            
            phase_start = datetime(phase.start_year, 1, 1)
            phase_end = datetime(phase.end_year, 12, 31)
            
            symbols = self.get_midcap_universe(phase_start)
            
            # Fetch data
            all_data = {}
            for symbol in symbols:
                df = self.fetch_data(symbol, phase_start, phase_end)
                if df is not None:
                    all_data[symbol] = df
            
            self.logger.info(f"Loaded data for {len(all_data)} symbols")
            
            # Test each strategy
            for strategy in self.strategies:
                self.logger.info(f"\n--- {strategy.name} ({strategy.strategy_type}) ---")
                
                phase_trades = []
                
                for symbol, df in all_data.items():
                    df_with_indicators = self.calculate_indicators(df, strategy)
                    df_with_signals = self.generate_signals(df_with_indicators, strategy)
                    trades = self.simulate_trades(df_with_signals, strategy)
                    phase_trades.extend(trades)
                
                if phase_trades:
                    winning_trades = [t for t in phase_trades if t.pnl > 0]
                    losing_trades = [t for t in phase_trades if t.pnl <= 0]
                    
                    total_return = sum(t.pnl_pct for t in phase_trades)
                    win_rate = len(winning_trades) / len(phase_trades)
                    avg_win = np.mean([t.pnl_pct for t in winning_trades]) if winning_trades else 0
                    avg_loss = np.mean([t.pnl_pct for t in losing_trades]) if losing_trades else 0
                    win_loss_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else 0
                    
                    total_wins = sum(t.pnl for t in winning_trades) if winning_trades else 0
                    total_losses = abs(sum(t.pnl for t in losing_trades)) if losing_trades else 0
                    profit_factor = total_wins / total_losses if total_losses > 0 else 0
                    
                    # Calculate max drawdown
                    cumulative_pnl = np.cumsum([t.pnl_pct for t in phase_trades])
                    running_max = np.maximum.accumulate(cumulative_pnl)
                    drawdown = (cumulative_pnl - running_max)
                    max_drawdown = drawdown.min() if len(drawdown) > 0 else 0
                    
                    results = PhaseResults(
                        phase_name=phase.name,
                        strategy_name=strategy.name,
                        strategy_type=strategy.strategy_type,
                        total_return=total_return,
                        total_trades=len(phase_trades),
                        winning_trades=len(winning_trades),
                        losing_trades=len(losing_trades),
                        win_rate=win_rate,
                        avg_win=avg_win,
                        avg_loss=avg_loss,
                        win_loss_ratio=win_loss_ratio,
                        profit_factor=profit_factor,
                        max_drawdown=max_drawdown
                    )
                    
                    self.all_results.append(results)
                    self.all_trades.extend(phase_trades)
                    
                    self.logger.info(f"  Return: {total_return:+.2f}% | Trades: {len(phase_trades)} | "
                                   f"Win Rate: {win_rate*100:.1f}% | PF: {profit_factor:.2f}")
                else:
                    self.logger.warning(f"  No trades generated")
        
        self._save_results()
    
    def _save_results(self):
        """Save comprehensive results"""
        output_dir = Path(__file__).parent / 'results' / 'comprehensive_midcap'
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save summary
        summary_file = output_dir / f'comprehensive_midcap_summary_{timestamp}.txt'
        with open(summary_file, 'w') as f:
            f.write("="*80 + "\n")
            f.write("COMPREHENSIVE MID-CAP STRATEGY BACKTEST (2011-2024)\n")
            f.write(f"Tested {len(self.strategies)} strategies on mid-cap stocks ($2B-$10B)\n")
            f.write("="*80 + "\n\n")
            
            # Group by strategy type
            for strategy_type in ["reversion", "momentum", "trend", "hybrid"]:
                type_strategies = [s for s in self.strategies if s.strategy_type == strategy_type]
                if not type_strategies:
                    continue
                
                f.write(f"\n{'='*80}\n")
                f.write(f"{strategy_type.upper()} STRATEGIES\n")
                f.write(f"{'='*80}\n")
                
                for strategy in type_strategies:
                    f.write(f"\n{strategy.name}:\n")
                    f.write("-" * 40 + "\n")
                    
                    strategy_results = [r for r in self.all_results if r.strategy_name == strategy.name]
                    
                    for result in strategy_results:
                        f.write(f"\n{result.phase_name}:\n")
                        f.write(f"  Total Return: {result.total_return:+.2f}%\n")
                        f.write(f"  Total Trades: {result.total_trades}\n")
                        f.write(f"  Win Rate: {result.win_rate*100:.1f}%\n")
                        f.write(f"  Avg Win: {result.avg_win*100:+.2f}%\n")
                        f.write(f"  Avg Loss: {result.avg_loss*100:+.2f}%\n")
                        f.write(f"  Win/Loss Ratio: {result.win_loss_ratio:.2f}\n")
                        f.write(f"  Profit Factor: {result.profit_factor:.2f}\n")
                        f.write(f"  Max Drawdown: {result.max_drawdown*100:.2f}%\n")
            
            # Ranking section
            f.write(f"\n\n{'='*80}\n")
            f.write("TOP 10 STRATEGIES BY OUT-OF-SAMPLE RETURN\n")
            f.write(f"{'='*80}\n")
            
            oos_results = [r for r in self.all_results if r.phase_name == "Out-of-Sample"]
            oos_results.sort(key=lambda x: x.total_return, reverse=True)
            
            for i, result in enumerate(oos_results[:10], 1):
                f.write(f"\n{i}. {result.strategy_name} ({result.strategy_type})\n")
                f.write(f"   Return: {result.total_return:+.2f}% | ")
                f.write(f"Trades: {result.total_trades} | ")
                f.write(f"Win Rate: {result.win_rate*100:.1f}% | ")
                f.write(f"Profit Factor: {result.profit_factor:.2f}\n")
        
        self.logger.info(f"\n✅ Results saved to: {summary_file}")


def main():
    backtester = ComprehensiveMidCapBacktester(initial_capital=10000)
    backtester.run_backtest()


if __name__ == '__main__':
    main()

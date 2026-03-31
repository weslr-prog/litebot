#!/usr/bin/env python3
"""
Comprehensive Multi-Strategy Backtest
Tests 5 core strategies + combinations
Runs with and without 2020 to isolate crash impact

Strategies:
1. Momentum Breakout
2. Gap Fade  
3. Bollinger Squeeze
4. Connors RSI
5. MA Crossover

Author: GitHub Copilot
Date: November 22, 2025
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
import logging
from dataclasses import dataclass
import json
from pathlib import Path
import yfinance as yf

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


@dataclass
class BacktestConfig:
    """Configuration for backtest"""
    symbols: List[str]
    start_year: int
    end_year: int
    initial_capital: float = 10000.0
    position_size_pct: float = 0.33
    max_positions: int = 3
    exclude_2020: bool = False
    cache_dir: str = 'backtest/cache'
    results_dir: str = 'backtest/results/all_strategies'


class Indicators:
    """Calculate technical indicators"""
    
    @staticmethod
    def rsi(prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    @staticmethod
    def connors_rsi(df: pd.DataFrame, rsi_period: int = 3, 
                    streak_period: int = 2, rank_period: int = 100) -> pd.Series:
        """Calculate Connors RSI (3 components)"""
        # Component 1: Standard RSI
        rsi_component = Indicators.rsi(df['Close'], rsi_period)
        
        # Component 2: Up/Down Streak RSI
        streak = (df['Close'].diff() > 0).astype(int) * 2 - 1
        streak_cumsum = streak.groupby((streak != streak.shift()).cumsum()).cumsum()
        streak_rsi = Indicators.rsi(streak_cumsum, streak_period)
        
        # Component 3: Percent Rank of Daily Returns
        returns = df['Close'].pct_change()
        rank = returns.rolling(rank_period).apply(
            lambda x: (x.rank()[-1] / len(x)) * 100, raw=False
        )
        
        # Average of 3 components
        connors = (rsi_component + streak_rsi + rank) / 3
        return connors
    
    @staticmethod
    def bollinger_bands(prices: pd.Series, period: int = 20, 
                       std_dev: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate Bollinger Bands"""
        sma = prices.rolling(period).mean()
        std = prices.rolling(period).std()
        upper = sma + (std * std_dev)
        lower = sma - (std * std_dev)
        return upper, sma, lower
    
    @staticmethod
    def vwap(df: pd.DataFrame) -> pd.Series:
        """Calculate VWAP (Volume Weighted Average Price)"""
        typical_price = (df['High'] + df['Low'] + df['Close']) / 3
        return (typical_price * df['Volume']).cumsum() / df['Volume'].cumsum()


class DataFetcher:
    """Fetch historical data with caching"""
    
    def __init__(self, cache_dir: str):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)
    
    def get_data(self, symbol: str, start_year: int, end_year: int) -> pd.DataFrame:
        """Get historical data with caching"""
        cache_file = self.cache_dir / f"{symbol}_{start_year}_{end_year}.csv"
        
        if cache_file.exists():
            return pd.read_csv(cache_file, index_col=0, parse_dates=True)
        
        self.logger.info(f"Downloading {symbol} ({start_year}-{end_year})")
        start_date = f"{start_year}-01-01"
        end_date = f"{end_year + 1}-01-01"
        
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(start=start_date, end=end_date)
            
            if df.empty:
                return pd.DataFrame()
            
            df.to_csv(cache_file)
            return df
        except Exception as e:
            self.logger.error(f"Error fetching {symbol}: {e}")
            return pd.DataFrame()


class Strategy:
    """Base strategy class"""
    
    def __init__(self, name: str):
        self.name = name
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Override in subclass"""
        raise NotImplementedError
    
    def should_exit(self, entry_price: float, current_price: float, 
                   entry_date: datetime, current_date: datetime, 
                   entry_data: dict, current_data: dict) -> Tuple[bool, str]:
        """Override in subclass"""
        raise NotImplementedError


class MomentumBreakout(Strategy):
    """Strategy #1: Momentum Breakout"""
    
    def __init__(self):
        super().__init__("Momentum Breakout")
        self.lookback = 20
        self.volume_mult = 2.0
        self.rsi_threshold = 60
        self.ma_period = 50
        self.trailing_stop_pct = 0.04
        self.max_hold_days = 5
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        
        # Calculate indicators
        df['high_20'] = df['High'].rolling(self.lookback).max()
        df['vol_avg'] = df['Volume'].rolling(20).mean()
        df['rsi'] = Indicators.rsi(df['Close'], 14)
        df['ma_50'] = df['Close'].rolling(self.ma_period).mean()
        
        # Entry: Breakout above 20-day high with confirmation
        df['entry_signal'] = (
            (df['Close'] > df['high_20'].shift(1)) &
            (df['Volume'] > df['vol_avg'] * self.volume_mult) &
            (df['rsi'] > self.rsi_threshold) &
            (df['Close'] > df['ma_50'])
        )
        
        return df
    
    def should_exit(self, entry_price, current_price, entry_date, 
                   current_date, entry_data, current_data) -> Tuple[bool, str]:
        # Trailing stop from peak
        peak_price = current_data.get('peak_price', entry_price)
        if current_price > peak_price:
            peak_price = current_price
            current_data['peak_price'] = peak_price
        
        if current_price < peak_price * (1 - self.trailing_stop_pct):
            return True, "TRAILING_STOP"
        
        # RSI momentum fade
        if current_data.get('rsi', 100) < 40:
            return True, "MOMENTUM_FADE"
        
        # Max hold
        if (current_date - entry_date).days >= self.max_hold_days:
            return True, "MAX_HOLD"
        
        return False, ""


class GapFade(Strategy):
    """Strategy #2: Gap Fade (short gap-ups)"""
    
    def __init__(self):
        super().__init__("Gap Fade")
        self.min_gap = 0.02
        self.max_gap = 0.05
        self.rsi_threshold = 70
        self.volume_mult = 1.5
        self.profit_target = 0.02
        self.stop_loss = 0.03
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        
        # Calculate gap
        df['prev_close'] = df['Close'].shift(1)
        df['gap_pct'] = (df['Open'] - df['prev_close']) / df['prev_close']
        df['rsi'] = Indicators.rsi(df['Close'], 14)
        df['vol_avg'] = df['Volume'].rolling(20).mean()
        
        # Entry: Gap up that's overbought
        df['entry_signal'] = (
            (df['gap_pct'] >= self.min_gap) &
            (df['gap_pct'] <= self.max_gap) &
            (df['rsi'] > self.rsi_threshold) &
            (df['Volume'] > df['vol_avg'] * self.volume_mult)
        )
        
        return df
    
    def should_exit(self, entry_price, current_price, entry_date, 
                   current_date, entry_data, current_data) -> Tuple[bool, str]:
        pnl_pct = (current_price - entry_price) / entry_price
        
        # Gap fill (price returns to previous close)
        prev_close = entry_data.get('prev_close', entry_price)
        if current_price <= prev_close:
            return True, "GAP_FILL"
        
        # Profit target
        if pnl_pct >= self.profit_target:
            return True, f"PROFIT_{pnl_pct*100:.1f}%"
        
        # Stop loss (gap extends)
        if pnl_pct <= -self.stop_loss:
            return True, "STOP_LOSS"
        
        # Max 2 days
        if (current_date - entry_date).days >= 2:
            return True, "MAX_HOLD"
        
        return False, ""


class BollingerSqueeze(Strategy):
    """Strategy #3: Bollinger Band Squeeze Breakout"""
    
    def __init__(self):
        super().__init__("Bollinger Squeeze")
        self.bb_period = 20
        self.squeeze_threshold = 0.05  # BB width as % of price
        self.volume_mult = 1.5
        self.profit_target = 0.04
        self.stop_loss = 0.02
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        
        # Calculate Bollinger Bands
        upper, middle, lower = Indicators.bollinger_bands(df['Close'], self.bb_period)
        df['bb_upper'] = upper
        df['bb_middle'] = middle
        df['bb_lower'] = lower
        df['bb_width'] = (upper - lower) / middle
        
        # Find squeeze (narrowest BB in 20 days)
        df['bb_width_min'] = df['bb_width'].rolling(20).min()
        df['is_squeeze'] = df['bb_width'] == df['bb_width_min']
        
        df['vol_avg'] = df['Volume'].rolling(20).mean()
        
        # Entry: Breakout from squeeze
        df['entry_signal'] = (
            df['is_squeeze'].shift(1) &
            (df['Close'] > df['bb_upper'].shift(1)) &
            (df['Volume'] > df['vol_avg'] * self.volume_mult)
        )
        
        return df
    
    def should_exit(self, entry_price, current_price, entry_date, 
                   current_date, entry_data, current_data) -> Tuple[bool, str]:
        pnl_pct = (current_price - entry_price) / entry_price
        
        # Opposite band touch
        bb_lower = current_data.get('bb_lower', 0)
        if current_price <= bb_lower and pnl_pct < 0:
            return True, "BB_OPPOSITE"
        
        # Profit target
        if pnl_pct >= self.profit_target:
            return True, f"PROFIT_{pnl_pct*100:.1f}%"
        
        # Stop loss
        if pnl_pct <= -self.stop_loss:
            return True, "STOP_LOSS"
        
        # Max 5 days
        if (current_date - entry_date).days >= 5:
            return True, "MAX_HOLD"
        
        return False, ""


class ConnorsRSI(Strategy):
    """Strategy #4: Connors RSI with trend filter"""
    
    def __init__(self):
        super().__init__("Connors RSI")
        self.crsi_threshold = 10
        self.ma_period = 200
        self.volume_mult = 1.5
        self.profit_target = 0.03
        self.stop_loss = 0.03
        self.max_hold_days = 5
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        
        # Calculate Connors RSI
        df['crsi'] = Indicators.connors_rsi(df)
        df['ma_200'] = df['Close'].rolling(self.ma_period).mean()
        df['vol_avg'] = df['Volume'].rolling(20).mean()
        
        # Count consecutive down days
        df['is_down'] = (df['Close'] < df['Close'].shift(1)).astype(int)
        df['down_streak'] = df['is_down'].groupby((df['is_down'] != df['is_down'].shift()).cumsum()).cumsum()
        
        # Entry: Extreme CRSI + uptrend + volume
        df['entry_signal'] = (
            (df['crsi'] < self.crsi_threshold) &
            (df['down_streak'] >= 2) &
            (df['Close'] > df['ma_200']) &
            (df['Volume'] > df['vol_avg'] * self.volume_mult)
        )
        
        return df
    
    def should_exit(self, entry_price, current_price, entry_date, 
                   current_date, entry_data, current_data) -> Tuple[bool, str]:
        pnl_pct = (current_price - entry_price) / entry_price
        
        # CRSI recovers
        crsi = current_data.get('crsi', 50)
        if crsi > 50:
            return True, f"CRSI_NEUTRAL_{crsi:.1f}"
        
        # Profit target
        if pnl_pct >= self.profit_target:
            return True, f"PROFIT_{pnl_pct*100:.1f}%"
        
        # Stop loss
        if pnl_pct <= -self.stop_loss:
            return True, "STOP_LOSS"
        
        # Max hold
        if (current_date - entry_date).days >= self.max_hold_days:
            return True, "MAX_HOLD"
        
        return False, ""


class MovingAverageCrossover(Strategy):
    """Strategy #8: Simple MA Crossover"""
    
    def __init__(self):
        super().__init__("MA Crossover")
        self.fast_ma = 10
        self.slow_ma = 30
        self.trend_ma = 200
        self.stop_loss = 0.05
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        
        df['ma_fast'] = df['Close'].rolling(self.fast_ma).mean()
        df['ma_slow'] = df['Close'].rolling(self.slow_ma).mean()
        df['ma_trend'] = df['Close'].rolling(self.trend_ma).mean()
        
        # Entry: Fast crosses above slow, price above trend
        df['entry_signal'] = (
            (df['ma_fast'] > df['ma_slow']) &
            (df['ma_fast'].shift(1) <= df['ma_slow'].shift(1)) &
            (df['Close'] > df['ma_trend'])
        )
        
        return df
    
    def should_exit(self, entry_price, current_price, entry_date, 
                   current_date, entry_data, current_data) -> Tuple[bool, str]:
        pnl_pct = (current_price - entry_price) / entry_price
        
        # Fast crosses below slow
        ma_fast = current_data.get('ma_fast', 0)
        ma_slow = current_data.get('ma_slow', 0)
        if ma_fast < ma_slow:
            return True, "MA_CROSS_EXIT"
        
        # Stop loss
        if pnl_pct <= -self.stop_loss:
            return True, "STOP_LOSS"
        
        return False, ""


class StrategyBacktester:
    """Backtest individual strategies"""
    
    def __init__(self, config: BacktestConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.data_fetcher = DataFetcher(config.cache_dir)
    
    def run_strategy(self, strategy: Strategy) -> Dict:
        """Run backtest for a single strategy"""
        self.logger.info(f"Testing {strategy.name}...")
        
        all_trades = []
        equity_curve = []
        current_capital = self.config.initial_capital
        
        for symbol in self.config.symbols:
            df = self.data_fetcher.get_data(symbol, self.config.start_year, self.config.end_year)
            if df.empty:
                continue
            
            # Exclude 2020 if requested
            if self.config.exclude_2020:
                if hasattr(df.index, 'year'):
                    df = df[df.index.year != 2020]
                else:
                    # Convert to datetime index first
                    df.index = pd.to_datetime(df.index, utc=True)
                    df = df[df.index.year != 2020]
            
            # Generate signals
            df = strategy.generate_signals(df)
            
            # Simulate trading
            position = None
            
            for i in range(len(df)):
                current_date = df.index[i]
                current_price = df['Close'].iloc[i]
                
                # Check exit if in position
                if position is not None:
                    hold_days = (current_date - position['entry_date']).days
                    pnl_pct = (current_price - position['entry_price']) / position['entry_price']
                    
                    # Prepare current data
                    current_data = {
                        'rsi': df['rsi'].iloc[i] if 'rsi' in df.columns else None,
                        'crsi': df['crsi'].iloc[i] if 'crsi' in df.columns else None,
                        'bb_lower': df['bb_lower'].iloc[i] if 'bb_lower' in df.columns else None,
                        'ma_fast': df['ma_fast'].iloc[i] if 'ma_fast' in df.columns else None,
                        'ma_slow': df['ma_slow'].iloc[i] if 'ma_slow' in df.columns else None,
                        'peak_price': position.get('peak_price', position['entry_price'])
                    }
                    
                    should_exit, exit_reason = strategy.should_exit(
                        position['entry_price'], current_price,
                        position['entry_date'], current_date,
                        position['entry_data'], current_data
                    )
                    
                    if should_exit or i == len(df) - 1:
                        # Close position
                        pnl = (current_price - position['entry_price']) * position['shares']
                        
                        all_trades.append({
                            'symbol': symbol,
                            'entry_date': position['entry_date'],
                            'entry_price': position['entry_price'],
                            'exit_date': current_date,
                            'exit_price': current_price,
                            'exit_reason': exit_reason if exit_reason else 'END_DATA',
                            'shares': position['shares'],
                            'pnl': pnl,
                            'pnl_pct': pnl_pct,
                            'hold_days': hold_days
                        })
                        
                        current_capital += pnl
                        equity_curve.append({
                            'date': current_date,
                            'equity': current_capital
                        })
                        
                        position = None
                
                # Check entry if not in position
                if position is None and df['entry_signal'].iloc[i]:
                    position_size = current_capital * self.config.position_size_pct
                    shares = int(position_size / current_price)
                    
                    if shares > 0:
                        position = {
                            'entry_date': current_date,
                            'entry_price': current_price,
                            'shares': shares,
                            'entry_data': {
                                'prev_close': df['prev_close'].iloc[i] if 'prev_close' in df.columns else current_price
                            },
                            'peak_price': current_price
                        }
        
        # Calculate results
        return self._calculate_results(strategy.name, all_trades, current_capital)
    
    def _calculate_results(self, strategy_name: str, trades: List[Dict], 
                          final_capital: float) -> Dict:
        """Calculate performance metrics"""
        if not trades:
            return {
                'strategy': strategy_name,
                'total_return': 0,
                'total_trades': 0,
                'win_rate': 0,
                'avg_trade': 0,
                'sharpe': 0,
                'final_capital': self.config.initial_capital
            }
        
        df = pd.DataFrame(trades)
        total_return = (final_capital - self.config.initial_capital) / self.config.initial_capital
        winning = df[df['pnl'] > 0]
        win_rate = len(winning) / len(df) if len(df) > 0 else 0
        avg_trade = df['pnl_pct'].mean()
        sharpe = (df['pnl_pct'].mean() / df['pnl_pct'].std() * np.sqrt(252)) if len(df) > 1 else 0
        
        return {
            'strategy': strategy_name,
            'total_return': total_return * 100,
            'total_trades': len(df),
            'win_rate': win_rate * 100,
            'avg_trade': avg_trade * 100,
            'avg_win': winning['pnl_pct'].mean() * 100 if len(winning) > 0 else 0,
            'avg_loss': df[df['pnl'] <= 0]['pnl_pct'].mean() * 100,
            'sharpe': sharpe,
            'final_capital': final_capital,
            'trades': trades
        }


def main():
    """Run comprehensive backtest"""
    
    # Configuration
    symbols = ['JBLU', 'AAL', 'CCL', 'RCL', 'F', 'GEVO', 'PLUG', 'FCEL', 'SBUX', 'SIRI', 'CAKE']
    
    # Define strategies
    strategies = [
        MomentumBreakout(),
        GapFade(),
        BollingerSqueeze(),
        ConnorsRSI(),
        MovingAverageCrossover()
    ]
    
    # Results storage
    all_results = {
        'with_2020': {},
        'without_2020': {}
    }
    
    print("="*80)
    print("COMPREHENSIVE STRATEGY BACKTEST")
    print("="*80)
    print(f"\nTesting {len(strategies)} strategies")
    print(f"Symbols: {', '.join(symbols)}")
    print(f"Period: 2011-2024 (14 years)")
    print()
    
    # Test WITH 2020
    print("\n" + "="*80)
    print("PHASE 1: WITH 2020 (Full 2011-2024)")
    print("="*80)
    
    config_with = BacktestConfig(
        symbols=symbols,
        start_year=2011,
        end_year=2024,
        exclude_2020=False,
        results_dir='backtest/results/all_strategies'
    )
    
    backtester_with = StrategyBacktester(config_with)
    
    for strategy in strategies:
        result = backtester_with.run_strategy(strategy)
        all_results['with_2020'][strategy.name] = result
        print(f"\n{strategy.name}:")
        print(f"  Return: {result['total_return']:+.2f}% | Trades: {result['total_trades']} | "
              f"Win Rate: {result['win_rate']:.1f}% | Sharpe: {result['sharpe']:.2f}")
    
    # Test WITHOUT 2020
    print("\n" + "="*80)
    print("PHASE 2: WITHOUT 2020 (Excluding crash year)")
    print("="*80)
    
    config_without = BacktestConfig(
        symbols=symbols,
        start_year=2011,
        end_year=2024,
        exclude_2020=True,
        results_dir='backtest/results/all_strategies'
    )
    
    backtester_without = StrategyBacktester(config_without)
    
    for strategy in strategies:
        result = backtester_without.run_strategy(strategy)
        all_results['without_2020'][strategy.name] = result
        print(f"\n{strategy.name}:")
        print(f"  Return: {result['total_return']:+.2f}% | Trades: {result['total_trades']} | "
              f"Win Rate: {result['win_rate']:.1f}% | Sharpe: {result['sharpe']:.2f}")
    
    # Comparative Analysis
    print("\n" + "="*80)
    print("COMPARATIVE ANALYSIS")
    print("="*80)
    
    print(f"\n{'Strategy':<25} {'With 2020':>12} {'Without 2020':>15} {'2020 Impact':>15}")
    print("-"*80)
    
    for strategy_name in all_results['with_2020'].keys():
        with_2020 = all_results['with_2020'][strategy_name]['total_return']
        without_2020 = all_results['without_2020'][strategy_name]['total_return']
        impact = without_2020 - with_2020
        print(f"{strategy_name:<25} {with_2020:>11.2f}% {without_2020:>14.2f}% {impact:>14.2f}%")
    
    # Rankings
    print("\n" + "="*80)
    print("STRATEGY RANKINGS")
    print("="*80)
    
    # Rank WITHOUT 2020 (more realistic)
    ranked = sorted(all_results['without_2020'].items(), 
                   key=lambda x: x[1]['total_return'], reverse=True)
    
    print("\nBest Performers (Without 2020 - Most Realistic):")
    for i, (name, result) in enumerate(ranked, 1):
        print(f"\n#{i} {name}")
        print(f"   Return: {result['total_return']:+.2f}%")
        print(f"   Win Rate: {result['win_rate']:.1f}%")
        print(f"   Avg Trade: {result['avg_trade']:+.2f}%")
        print(f"   Sharpe: {result['sharpe']:.2f}")
        print(f"   Trades: {result['total_trades']}")
    
    # Save results
    results_dir = Path('backtest/results/all_strategies')
    results_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    results_file = results_dir / f"all_strategies_comparison_{timestamp}.json"
    
    with open(results_file, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    print(f"\n\nResults saved to: {results_file}")
    print("="*80)


if __name__ == '__main__':
    main()

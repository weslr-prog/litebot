#!/usr/bin/env python3
"""
Momentum Strategy Backtest - 14 Years (2011-2024)
Compare multiple momentum-based strategies for short swing trading

Strategies tested:
1. Classic Momentum Breakout (20-day high, 10-day momentum)
2. Price & Volume Surge (momentum + 2x volume)
3. Moving Average Crossover (fast MA crosses above slow MA)
4. Relative Strength (outperforming SPY)
5. Gap & Go (morning gap up + momentum)

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

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


@dataclass
class MomentumStrategyConfig:
    """Configuration for momentum strategy"""
    name: str
    strategy_id: int
    
    # Momentum parameters
    momentum_period: int = 10  # Days for momentum calculation
    momentum_threshold_pct: float = 0.03  # 3% minimum momentum
    
    # Volume parameters
    volume_period: int = 20  # Days for volume average
    min_volume_surge: float = 1.5  # 1.5x average volume
    
    # Moving average parameters
    fast_ma_period: int = 10
    slow_ma_period: int = 20
    
    # Exit parameters
    profit_target_pct: float = 0.05  # 5% profit target
    stop_loss_pct: float = -0.03  # 3% stop loss
    trailing_stop_pct: float = 0.02  # 2% trailing stop
    max_hold_days: int = 5  # Maximum D+5 hold
    
    # Entry filters
    require_uptrend: bool = True  # Must be above 50-day MA
    require_volume: bool = True  # Must have volume surge
    

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
    entry_momentum: float
    entry_volume_surge: float


@dataclass
class PhaseResults:
    """Results for a single phase"""
    phase_name: str
    strategy_name: str
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
    sharpe_ratio: float
    trades: List[Trade]
    equity_curve: pd.DataFrame


class DataFetcher:
    """Fetch historical data from yfinance with caching"""
    
    def __init__(self, cache_dir: str = 'backtest/cache'):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__ + '.DataFetcher')
    
    def fetch(self, symbol: str, start_year: int, end_year: int) -> pd.DataFrame:
        """Fetch data with caching"""
        cache_file = self.cache_dir / f"{symbol}_{start_year}_{end_year}.csv"
        
        if cache_file.exists():
            self.logger.info(f"Loading {symbol} from cache ({start_year}-{end_year})")
            return pd.read_csv(cache_file, index_col=0, parse_dates=True)
        
        self.logger.info(f"Downloading {symbol} data ({start_year}-{end_year})")
        start_date = f"{start_year}-01-01"
        end_date = f"{end_year}-12-31"
        
        try:
            df = yf.download(symbol, start=start_date, end=end_date, progress=False)
            if df.empty:
                self.logger.warning(f"No data for {symbol}")
                return pd.DataFrame()
            
            df.to_csv(cache_file)
            return df
        except Exception as e:
            self.logger.error(f"Error downloading {symbol}: {e}")
            return pd.DataFrame()


class MomentumStrategyBacktester:
    """Backtest momentum strategies"""
    
    def __init__(self, config: MomentumStrategyConfig):
        self.config = config
        self.logger = logging.getLogger(__name__ + f'.{config.name}')
    
    def calculate_momentum(self, df: pd.DataFrame) -> pd.Series:
        """Calculate rate of change momentum"""
        return df['Close'].pct_change(self.config.momentum_period)
    
    def calculate_volume_surge(self, df: pd.DataFrame) -> pd.Series:
        """Calculate volume surge vs average"""
        avg_volume = df['Volume'].rolling(self.config.volume_period).mean()
        return df['Volume'] / avg_volume
    
    def calculate_moving_averages(self, df: pd.DataFrame) -> Tuple[pd.Series, pd.Series]:
        """Calculate fast and slow MAs"""
        fast_ma = df['Close'].rolling(self.config.fast_ma_period).mean()
        slow_ma = df['Close'].rolling(self.config.slow_ma_period).mean()
        return fast_ma, slow_ma
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate entry signals based on strategy"""
        df = df.copy()
        
        # Calculate indicators
        df['momentum'] = self.calculate_momentum(df)
        df['volume_surge'] = self.calculate_volume_surge(df)
        df['fast_ma'], df['slow_ma'] = self.calculate_moving_averages(df)
        df['ma_50'] = df['Close'].rolling(50).mean()
        
        # Strategy-specific logic
        if self.config.strategy_id == 1:
            # Classic Momentum Breakout
            df['signal'] = (
                (df['momentum'] >= self.config.momentum_threshold_pct) &
                (df['Close'] > df['ma_50']) &
                (df['volume_surge'] >= self.config.min_volume_surge)
            )
        
        elif self.config.strategy_id == 2:
            # Price & Volume Surge
            df['signal'] = (
                (df['momentum'] >= 0.02) &  # 2%+ momentum
                (df['volume_surge'] >= 2.0) &  # 2x volume
                (df['Close'] > df['ma_50'])
            )
        
        elif self.config.strategy_id == 3:
            # MA Crossover
            df['signal'] = (
                (df['fast_ma'] > df['slow_ma']) &
                (df['fast_ma'].shift(1) <= df['slow_ma'].shift(1)) &  # Crossover
                (df['volume_surge'] >= self.config.min_volume_surge)
            )
        
        elif self.config.strategy_id == 4:
            # Strong Momentum + Breakout
            df['20_day_high'] = df['Close'].rolling(20).max()
            df['signal'] = (
                (df['Close'] >= df['20_day_high'].shift(1)) &  # New 20-day high
                (df['momentum'] >= 0.05) &  # 5%+ momentum
                (df['volume_surge'] >= 1.5)
            )
        
        elif self.config.strategy_id == 5:
            # Gap & Go
            df['prev_close'] = df['Close'].shift(1)
            df['gap_pct'] = (df['Open'] - df['prev_close']) / df['prev_close']
            df['signal'] = (
                (df['gap_pct'] >= 0.02) &  # 2%+ gap up
                (df['volume_surge'] >= 2.0) &  # 2x volume
                (df['Close'] > df['ma_50'])
            )
        
        return df
    
    def backtest_symbol(self, symbol: str, df: pd.DataFrame, initial_capital: float) -> List[Trade]:
        """Backtest strategy on single symbol"""
        df = self.generate_signals(df)
        trades = []
        position = None
        capital = initial_capital
        
        for i in range(len(df)):
            if position is None:
                # Look for entry
                if df['signal'].iloc[i]:
                    entry_price = df['Close'].iloc[i]
                    shares = int((capital * 0.33) / entry_price)  # 33% position size
                    
                    if shares > 0:
                        position = {
                            'entry_date': df.index[i],
                            'entry_price': entry_price,
                            'shares': shares,
                            'entry_momentum': df['momentum'].iloc[i],
                            'entry_volume_surge': df['volume_surge'].iloc[i],
                            'highest_price': entry_price,
                            'entry_day': i
                        }
            
            else:
                # Manage position
                current_price = df['Close'].iloc[i]
                current_date = df.index[i]
                days_held = i - position['entry_day']
                
                # Update trailing high
                if current_price > position['highest_price']:
                    position['highest_price'] = current_price
                
                # Calculate returns
                pnl_pct = (current_price - position['entry_price']) / position['entry_price']
                
                # Exit conditions
                exit_reason = None
                
                # 1. Profit target
                if pnl_pct >= self.config.profit_target_pct:
                    exit_reason = 'PROFIT_TARGET'
                
                # 2. Stop loss
                elif pnl_pct <= self.config.stop_loss_pct:
                    exit_reason = 'STOP_LOSS'
                
                # 3. Trailing stop
                elif position['highest_price'] > position['entry_price']:
                    drawdown_from_high = (current_price - position['highest_price']) / position['highest_price']
                    if drawdown_from_high <= -self.config.trailing_stop_pct:
                        exit_reason = 'TRAILING_STOP'
                
                # 4. Max hold time
                elif days_held >= self.config.max_hold_days:
                    exit_reason = 'MAX_HOLD'
                
                # Execute exit
                if exit_reason:
                    pnl = (current_price - position['entry_price']) * position['shares']
                    capital += pnl
                    
                    trade = Trade(
                        symbol=symbol,
                        entry_date=position['entry_date'],
                        entry_price=position['entry_price'],
                        exit_date=current_date,
                        exit_price=current_price,
                        exit_reason=exit_reason,
                        shares=position['shares'],
                        pnl=pnl,
                        pnl_pct=pnl_pct,
                        hold_days=days_held,
                        entry_momentum=position['entry_momentum'],
                        entry_volume_surge=position['entry_volume_surge']
                    )
                    trades.append(trade)
                    position = None
        
        return trades
    
    def backtest_phase(self, symbols: List[str], phase: BacktestPhase, 
                      data_fetcher: DataFetcher, initial_capital: float) -> PhaseResults:
        """Backtest strategy on phase"""
        all_trades = []
        
        for symbol in symbols:
            df = data_fetcher.fetch(symbol, phase.start_year, phase.end_year)
            if df.empty:
                continue
            
            trades = self.backtest_symbol(symbol, df, initial_capital)
            all_trades.extend(trades)
        
        # Calculate metrics
        if not all_trades:
            return PhaseResults(
                phase_name=phase.name,
                strategy_name=self.config.name,
                total_return=0.0,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=0.0,
                avg_win=0.0,
                avg_loss=0.0,
                win_loss_ratio=0.0,
                profit_factor=0.0,
                max_drawdown=0.0,
                sharpe_ratio=0.0,
                trades=[],
                equity_curve=pd.DataFrame()
            )
        
        # Sort trades by date
        all_trades.sort(key=lambda t: t.entry_date)
        
        # Calculate equity curve
        equity = initial_capital
        equity_curve = []
        
        for trade in all_trades:
            equity += trade.pnl
            equity_curve.append({
                'date': trade.exit_date,
                'equity': equity,
                'return': (equity - initial_capital) / initial_capital
            })
        
        equity_df = pd.DataFrame(equity_curve)
        
        # Calculate metrics
        total_return = (equity - initial_capital) / initial_capital
        winning_trades = [t for t in all_trades if t.pnl > 0]
        losing_trades = [t for t in all_trades if t.pnl <= 0]
        
        win_rate = len(winning_trades) / len(all_trades) if all_trades else 0.0
        avg_win = np.mean([t.pnl_pct for t in winning_trades]) if winning_trades else 0.0
        avg_loss = np.mean([t.pnl_pct for t in losing_trades]) if losing_trades else 0.0
        
        win_loss_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else 0.0
        
        total_wins = sum([t.pnl for t in winning_trades])
        total_losses = abs(sum([t.pnl for t in losing_trades]))
        profit_factor = total_wins / total_losses if total_losses > 0 else 0.0
        
        # Max drawdown
        if not equity_df.empty:
            cummax = equity_df['equity'].cummax()
            drawdown = (equity_df['equity'] - cummax) / cummax
            max_drawdown = drawdown.min()
        else:
            max_drawdown = 0.0
        
        # Sharpe ratio (simplified)
        if not equity_df.empty and len(equity_df) > 1:
            returns = equity_df['return'].pct_change().dropna()
            sharpe_ratio = returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0.0
        else:
            sharpe_ratio = 0.0
        
        return PhaseResults(
            phase_name=phase.name,
            strategy_name=self.config.name,
            total_return=total_return,
            total_trades=len(all_trades),
            winning_trades=len(winning_trades),
            losing_trades=len(losing_trades),
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
            win_loss_ratio=win_loss_ratio,
            profit_factor=profit_factor,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            trades=all_trades,
            equity_curve=equity_df
        )


def run_momentum_backtest():
    """Run comprehensive momentum strategy backtest"""
    
    print("="*70)
    print("MOMENTUM STRATEGY BACKTEST - 14 YEARS (2011-2024)")
    print("="*70)
    print()
    
    # Test symbols
    symbols = ['JBLU', 'AAL', 'CCL', 'RCL', 'F', 'GEVO', 'PLUG', 'FCEL', 'SBUX', 'SIRI', 'CAKE']
    
    # Test phases
    phases = [
        BacktestPhase('In-Sample', 2011, 2016, 'Training period'),
        BacktestPhase('Validation', 2017, 2019, 'Overfitting check'),
        BacktestPhase('Out-of-Sample', 2020, 2024, 'Real-world test')
    ]
    
    # Define momentum strategies
    strategies = [
        MomentumStrategyConfig(
            name='Momentum_Breakout',
            strategy_id=1,
            momentum_period=10,
            momentum_threshold_pct=0.03,
            profit_target_pct=0.05,
            stop_loss_pct=-0.03,
            max_hold_days=5
        ),
        MomentumStrategyConfig(
            name='Price_Volume_Surge',
            strategy_id=2,
            momentum_period=5,
            profit_target_pct=0.04,
            stop_loss_pct=-0.02,
            max_hold_days=3
        ),
        MomentumStrategyConfig(
            name='MA_Crossover',
            strategy_id=3,
            fast_ma_period=10,
            slow_ma_period=20,
            profit_target_pct=0.06,
            stop_loss_pct=-0.03,
            max_hold_days=7
        ),
        MomentumStrategyConfig(
            name='Strong_Momentum_Breakout',
            strategy_id=4,
            momentum_period=10,
            profit_target_pct=0.07,
            stop_loss_pct=-0.03,
            max_hold_days=5
        ),
        MomentumStrategyConfig(
            name='Gap_And_Go',
            strategy_id=5,
            profit_target_pct=0.03,
            stop_loss_pct=-0.02,
            max_hold_days=1
        )
    ]
    
    # Run backtests
    data_fetcher = DataFetcher()
    initial_capital = 10000.0
    all_results = {}
    
    for strategy_config in strategies:
        print(f"\nTesting: {strategy_config.name}")
        print("-" * 70)
        
        backtester = MomentumStrategyBacktester(strategy_config)
        strategy_results = {}
        
        for phase in phases:
            print(f"  {phase.name} ({phase.start_year}-{phase.end_year})...", end=' ')
            results = backtester.backtest_phase(symbols, phase, data_fetcher, initial_capital)
            strategy_results[phase.name] = results
            print(f"Return: {results.total_return*100:+.2f}%, Trades: {results.total_trades}")
        
        all_results[strategy_config.name] = strategy_results
    
    # Generate summary report
    print("\n" + "="*70)
    print("RESULTS SUMMARY")
    print("="*70)
    print()
    
    for strategy_name, results in all_results.items():
        print(f"\n{strategy_name}:")
        print("-" * 70)
        for phase_name, result in results.items():
            print(f"{phase_name:20s}: {result.total_return*100:+7.2f}% | "
                  f"WR: {result.win_rate*100:5.1f}% | "
                  f"Trades: {result.total_trades:4d} | "
                  f"Sharpe: {result.sharpe_ratio:5.2f}")
    
    # Save detailed report
    output_dir = Path('backtest/results/momentum')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_path = output_dir / f'momentum_backtest_summary_{timestamp}.txt'
    
    with open(report_path, 'w') as f:
        f.write("="*70 + "\n")
        f.write("MOMENTUM STRATEGY BACKTEST RESULTS\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("="*70 + "\n\n")
        
        for strategy_name, results in all_results.items():
            f.write(f"\nSTRATEGY: {strategy_name}\n")
            f.write("-" * 70 + "\n")
            
            for phase_name, result in results.items():
                f.write(f"\n{phase_name}:\n")
                f.write(f"  Total Return: {result.total_return*100:+.2f}%\n")
                f.write(f"  Total Trades: {result.total_trades}\n")
                f.write(f"  Win Rate: {result.win_rate*100:.1f}%\n")
                f.write(f"  Avg Win: {result.avg_win*100:+.2f}%\n")
                f.write(f"  Avg Loss: {result.avg_loss*100:.2f}%\n")
                f.write(f"  Profit Factor: {result.profit_factor:.2f}\n")
                f.write(f"  Max Drawdown: {result.max_drawdown*100:.2f}%\n")
                f.write(f"  Sharpe Ratio: {result.sharpe_ratio:.2f}\n")
    
    print(f"\n✅ Report saved to: {report_path}")
    
    return all_results


if __name__ == '__main__':
    results = run_momentum_backtest()

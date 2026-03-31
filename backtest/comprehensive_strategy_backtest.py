#!/usr/bin/env python3
"""
Comprehensive 3-Phase Backtest for Top 3 Strategies
Implements in-sample, validation, and out-of-sample testing

Phase 1: In-Sample Training (2011-2016) - Parameter validation
Phase 2: Validation (2017-2019) - Overfitting check  
Phase 3: Out-of-Sample (2020-2024) - Real-world performance

Top 3 Strategies from Optimization:
1. Mean Reversion RSI (Test #2852): RSI(7) < 20, exit RSI > 50, 2% target
2. Mean Reversion RSI (Test #3831): RSI(21) < 25, exit RSI > 80, 3% target
3. Hybrid (Test #4872): Combines momentum + mean reversion signals

Author: GitHub Copilot
Date: November 22, 2025
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
import logging
from dataclasses import dataclass, field
import json
from pathlib import Path
import yfinance as yf

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


@dataclass
class StrategyConfig:
    """Configuration for individual strategy"""
    name: str
    test_id: int
    strategy_type: str  # 'mean_reversion_rsi' or 'hybrid'
    
    # RSI parameters
    rsi_period: int = 7
    oversold_threshold: float = 20.0
    overbought_threshold: float = 80.0
    exit_rsi_level: Optional[float] = 50.0  # For rsi_neutral exit
    
    # Exit strategy
    exit_strategy: str = 'rsi_neutral'  # 'rsi_neutral', 'rsi_opposite', 'profit_target', 'time_based'
    profit_target_pct: float = 0.02
    stop_loss_pct: float = -0.02
    max_hold_days: int = 5
    
    # Volume/momentum filters
    min_volume_surge: float = 1.5
    min_momentum_pct: float = 0.0


@dataclass
class BacktestPhase:
    """Configuration for each backtest phase"""
    name: str
    start_year: int
    end_year: int
    description: str


@dataclass
class BacktestConfig:
    """Configuration for comprehensive backtest"""
    # Test stocks (high liquidity, gap-prone)
    symbols: List[str] = field(default_factory=lambda: [
        'JBLU', 'AAL', 'CCL', 'RCL',  # Travel/Cruise
        'F',                            # Automotive
        'GEVO', 'PLUG', 'FCEL',        # Green Energy
        'SBUX', 'SIRI', 'CAKE'         # Consumer
    ])
    
    # 3-Phase Testing
    phases: List[BacktestPhase] = field(default_factory=lambda: [
        BacktestPhase('In-Sample', 2011, 2016, 'Training period for parameter validation'),
        BacktestPhase('Validation', 2017, 2019, 'Overfitting check'),
        BacktestPhase('Out-of-Sample', 2020, 2024, 'Real-world performance test')
    ])
    
    # Position sizing
    initial_capital: float = 10000.0
    position_size_pct: float = 0.33  # 33% per position
    max_positions: int = 3
    
    # Output
    results_dir: str = 'backtest/results/comprehensive'
    cache_dir: str = 'backtest/cache'


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
    entry_rsi: float
    exit_rsi: float


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
    

class RSICalculator:
    """Calculate RSI indicator"""
    
    @staticmethod
    def calculate(prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI using standard formula"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi


class DataFetcher:
    """Fetch historical data from yfinance with caching"""
    
    def __init__(self, cache_dir: str):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)
    
    def get_data(self, symbol: str, start_year: int, end_year: int) -> pd.DataFrame:
        """Get historical data with caching"""
        cache_file = self.cache_dir / f"{symbol}_{start_year}_{end_year}.csv"
        
        # Check cache
        if cache_file.exists():
            self.logger.info(f"Loading {symbol} from cache ({start_year}-{end_year})")
            df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
            return df
        
        # Fetch from yfinance
        self.logger.info(f"Downloading {symbol} from yfinance ({start_year}-{end_year})")
        start_date = f"{start_year}-01-01"
        end_date = f"{end_year + 1}-01-01"
        
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(start=start_date, end=end_date)
            
            if df.empty:
                self.logger.warning(f"No data for {symbol} in {start_year}-{end_year}")
                return pd.DataFrame()
            
            # Save to cache
            df.to_csv(cache_file)
            self.logger.info(f"Cached {len(df)} bars for {symbol}")
            return df
            
        except Exception as e:
            self.logger.error(f"Error fetching {symbol}: {e}")
            return pd.DataFrame()


class StrategyBacktester:
    """Backtest individual strategies across multiple phases"""
    
    def __init__(self, strategy_config: StrategyConfig, backtest_config: BacktestConfig):
        self.strategy = strategy_config
        self.config = backtest_config
        self.logger = logging.getLogger(__name__)
        self.data_fetcher = DataFetcher(backtest_config.cache_dir)
    
    def calculate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate entry/exit signals based on strategy"""
        df = df.copy()
        
        # Calculate RSI
        df['rsi'] = RSICalculator.calculate(df['Close'], self.strategy.rsi_period)
        
        # Calculate volume surge
        df['vol_avg_20'] = df['Volume'].rolling(20).mean()
        df['volume_surge'] = df['Volume'] / df['vol_avg_20']
        
        # Calculate momentum
        df['momentum'] = df['Close'].pct_change()
        
        # Entry signal: RSI oversold + volume confirmation
        if self.strategy.strategy_type == 'mean_reversion_rsi':
            df['entry_signal'] = (
                (df['rsi'] < self.strategy.oversold_threshold) &
                (df['volume_surge'] >= self.strategy.min_volume_surge)
            )
        elif self.strategy.strategy_type == 'hybrid':
            # Hybrid: Either momentum OR mean reversion
            df['entry_signal'] = (
                ((df['rsi'] < self.strategy.oversold_threshold) |
                 (df['momentum'] >= self.strategy.min_momentum_pct)) &
                (df['volume_surge'] >= self.strategy.min_volume_surge)
            )
        
        return df
    
    def check_exit(self, entry_rsi: float, current_rsi: float, pnl_pct: float, hold_days: int) -> Tuple[bool, str]:
        """Check if position should be exited"""
        # Emergency stop loss
        if pnl_pct <= self.strategy.stop_loss_pct:
            return True, "STOP_LOSS"
        
        # Strategy-specific exit
        if self.strategy.exit_strategy == 'rsi_neutral':
            if current_rsi >= self.strategy.exit_rsi_level:
                return True, f"RSI_NEUTRAL_{current_rsi:.1f}"
        
        elif self.strategy.exit_strategy == 'rsi_opposite':
            if current_rsi >= self.strategy.overbought_threshold:
                return True, f"RSI_OVERBOUGHT_{current_rsi:.1f}"
        
        elif self.strategy.exit_strategy == 'profit_target':
            if pnl_pct >= self.strategy.profit_target_pct:
                return True, f"PROFIT_TARGET_{pnl_pct*100:.1f}%"
        
        elif self.strategy.exit_strategy == 'time_based':
            if hold_days >= self.strategy.max_hold_days:
                return True, f"MAX_HOLD_{hold_days}d"
        
        # Always check profit target as secondary exit
        if pnl_pct >= self.strategy.profit_target_pct:
            return True, f"PROFIT_TARGET_{pnl_pct*100:.1f}%"
        
        # Max hold days (universal)
        if hold_days >= self.strategy.max_hold_days:
            return True, f"MAX_HOLD_{hold_days}d"
        
        return False, ""
    
    def run_backtest_phase(self, phase: BacktestPhase) -> PhaseResults:
        """Run backtest for a single phase"""
        self.logger.info(f"\n{'='*75}")
        self.logger.info(f"Running {self.strategy.name} on {phase.name} ({phase.start_year}-{phase.end_year})")
        self.logger.info(f"{'='*75}")
        
        all_trades = []
        equity_curve = []
        current_capital = self.config.initial_capital
        peak_capital = current_capital
        max_drawdown = 0.0
        
        for symbol in self.config.symbols:
            # Get data
            df = self.data_fetcher.get_data(symbol, phase.start_year, phase.end_year)
            if df.empty:
                continue
            
            # Calculate signals
            df = self.calculate_signals(df)
            
            # Simulate trading
            position = None
            
            for i in range(len(df)):
                current_date = df.index[i]
                current_price = df['Close'].iloc[i]
                current_rsi = df['rsi'].iloc[i]
                
                # Skip if RSI not calculated yet
                if pd.isna(current_rsi):
                    continue
                
                # Check exit if in position
                if position is not None:
                    hold_days = (current_date - position['entry_date']).days
                    pnl_pct = (current_price - position['entry_price']) / position['entry_price']
                    
                    should_exit, exit_reason = self.check_exit(
                        position['entry_rsi'], current_rsi, pnl_pct, hold_days
                    )
                    
                    if should_exit or i == len(df) - 1:  # Exit on signal or end of data
                        # Close position
                        shares = position['shares']
                        pnl = (current_price - position['entry_price']) * shares
                        
                        trade = Trade(
                            symbol=symbol,
                            entry_date=position['entry_date'],
                            entry_price=position['entry_price'],
                            exit_date=current_date,
                            exit_price=current_price,
                            exit_reason=exit_reason if exit_reason else "END_OF_DATA",
                            shares=shares,
                            pnl=pnl,
                            pnl_pct=pnl_pct,
                            hold_days=hold_days,
                            entry_rsi=position['entry_rsi'],
                            exit_rsi=current_rsi
                        )
                        all_trades.append(trade)
                        
                        # Update capital
                        current_capital += pnl
                        
                        # Track drawdown
                        if current_capital > peak_capital:
                            peak_capital = current_capital
                        drawdown = (peak_capital - current_capital) / peak_capital
                        max_drawdown = max(max_drawdown, drawdown)
                        
                        # Record equity
                        equity_curve.append({
                            'date': current_date,
                            'equity': current_capital,
                            'symbol': symbol,
                            'trade_type': 'EXIT'
                        })
                        
                        position = None
                
                # Check entry if not in position
                if position is None and df['entry_signal'].iloc[i]:
                    # Enter position
                    position_size = current_capital * self.config.position_size_pct
                    shares = int(position_size / current_price)
                    
                    if shares > 0:
                        position = {
                            'entry_date': current_date,
                            'entry_price': current_price,
                            'entry_rsi': current_rsi,
                            'shares': shares
                        }
                        
                        equity_curve.append({
                            'date': current_date,
                            'equity': current_capital,
                            'symbol': symbol,
                            'trade_type': 'ENTRY'
                        })
        
        # Calculate results
        return self._calculate_phase_results(phase, all_trades, equity_curve, current_capital)
    
    def _calculate_phase_results(self, phase: BacktestPhase, trades: List[Trade], 
                                 equity_curve: list, final_capital: float) -> PhaseResults:
        """Calculate performance metrics for phase"""
        if not trades:
            self.logger.warning(f"No trades for {phase.name}")
            return PhaseResults(
                phase_name=phase.name,
                strategy_name=self.strategy.name,
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
        
        total_return = (final_capital - self.config.initial_capital) / self.config.initial_capital
        winning_trades = [t for t in trades if t.pnl > 0]
        losing_trades = [t for t in trades if t.pnl <= 0]
        
        win_rate = len(winning_trades) / len(trades) if trades else 0
        avg_win = np.mean([t.pnl_pct for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t.pnl_pct for t in losing_trades]) if losing_trades else 0
        win_loss_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else 0
        
        gross_profit = sum(t.pnl for t in winning_trades) if winning_trades else 0
        gross_loss = abs(sum(t.pnl for t in losing_trades)) if losing_trades else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        # Sharpe ratio
        returns = [t.pnl_pct for t in trades]
        sharpe = (np.mean(returns) / np.std(returns) * np.sqrt(252)) if len(returns) > 1 else 0
        
        # Max drawdown
        equity_df = pd.DataFrame(equity_curve)
        if not equity_df.empty:
            equity_df['peak'] = equity_df['equity'].cummax()
            equity_df['drawdown'] = (equity_df['peak'] - equity_df['equity']) / equity_df['peak']
            max_drawdown = equity_df['drawdown'].max()
        else:
            max_drawdown = 0.0
        
        return PhaseResults(
            phase_name=phase.name,
            strategy_name=self.strategy.name,
            total_return=total_return,
            total_trades=len(trades),
            winning_trades=len(winning_trades),
            losing_trades=len(losing_trades),
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
            win_loss_ratio=win_loss_ratio,
            profit_factor=profit_factor,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe,
            trades=trades,
            equity_curve=equity_df if not equity_df.empty else pd.DataFrame()
        )


class ComprehensiveBacktestRunner:
    """Run comprehensive 3-phase backtest for multiple strategies"""
    
    def __init__(self, config: BacktestConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.results_dir = Path(config.results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)
    
    def run_all_strategies(self, strategies: List[StrategyConfig]) -> Dict[str, Dict[str, PhaseResults]]:
        """Run all strategies across all phases"""
        all_results = {}
        
        for strategy in strategies:
            self.logger.info(f"\n{'='*80}")
            self.logger.info(f"Testing Strategy: {strategy.name}")
            self.logger.info(f"{'='*80}")
            
            backtester = StrategyBacktester(strategy, self.config)
            strategy_results = {}
            
            for phase in self.config.phases:
                phase_results = backtester.run_backtest_phase(phase)
                strategy_results[phase.name] = phase_results
                
                # Print phase summary
                self.logger.info(f"\n{phase.name} Results:")
                self.logger.info(f"  Total Return: {phase_results.total_return*100:+.2f}%")
                self.logger.info(f"  Total Trades: {phase_results.total_trades}")
                self.logger.info(f"  Win Rate: {phase_results.win_rate*100:.1f}%")
                self.logger.info(f"  Sharpe Ratio: {phase_results.sharpe_ratio:.2f}")
            
            all_results[strategy.name] = strategy_results
        
        return all_results
    
    def save_results(self, results: Dict[str, Dict[str, PhaseResults]]):
        """Save comprehensive results to files"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save detailed trade logs
        for strategy_name, phases in results.items():
            for phase_name, phase_results in phases.items():
                # Save trades CSV
                if phase_results.trades:
                    trades_df = pd.DataFrame([{
                        'symbol': t.symbol,
                        'entry_date': t.entry_date,
                        'entry_price': t.entry_price,
                        'entry_rsi': t.entry_rsi,
                        'exit_date': t.exit_date,
                        'exit_price': t.exit_price,
                        'exit_rsi': t.exit_rsi,
                        'exit_reason': t.exit_reason,
                        'shares': t.shares,
                        'pnl': t.pnl,
                        'pnl_pct': t.pnl_pct,
                        'hold_days': t.hold_days
                    } for t in phase_results.trades])
                    
                    safe_strategy = strategy_name.replace(' ', '_').replace('#', '')
                    safe_phase = phase_name.replace(' ', '_').replace('-', '_')
                    trades_file = self.results_dir / f"{safe_strategy}_{safe_phase}_trades_{timestamp}.csv"
                    trades_df.to_csv(trades_file, index=False)
                    self.logger.info(f"Saved {len(trades_df)} trades to {trades_file}")
        
        # Save summary report
        self._generate_summary_report(results, timestamp)
    
    def _generate_summary_report(self, results: Dict[str, Dict[str, PhaseResults]], timestamp: str):
        """Generate comprehensive summary report"""
        report_file = self.results_dir / f"comprehensive_backtest_summary_{timestamp}.txt"
        
        with open(report_file, 'w') as f:
            f.write("="*80 + "\n")
            f.write("COMPREHENSIVE 3-PHASE BACKTEST RESULTS\n")
            f.write("="*80 + "\n\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Symbols: {', '.join(self.config.symbols)}\n\n")
            
            # Phase descriptions
            f.write("Test Phases:\n")
            for phase in self.config.phases:
                f.write(f"  {phase.name} ({phase.start_year}-{phase.end_year}): {phase.description}\n")
            f.write("\n" + "="*80 + "\n\n")
            
            # Strategy results
            for strategy_name, phases in results.items():
                f.write(f"\nSTRATEGY: {strategy_name}\n")
                f.write("-"*80 + "\n\n")
                
                for phase_name, res in phases.items():
                    f.write(f"{phase_name}:\n")
                    f.write(f"  Total Return: {res.total_return*100:+.2f}%\n")
                    f.write(f"  Total Trades: {res.total_trades}\n")
                    f.write(f"  Winning Trades: {res.winning_trades}\n")
                    f.write(f"  Losing Trades: {res.losing_trades}\n")
                    f.write(f"  Win Rate: {res.win_rate*100:.1f}%\n")
                    f.write(f"  Average Win: {res.avg_win*100:+.2f}%\n")
                    f.write(f"  Average Loss: {res.avg_loss*100:+.2f}%\n")
                    f.write(f"  Win/Loss Ratio: {res.win_loss_ratio:.2f}:1\n")
                    f.write(f"  Profit Factor: {res.profit_factor:.2f}\n")
                    f.write(f"  Max Drawdown: {res.max_drawdown*100:.2f}%\n")
                    f.write(f"  Sharpe Ratio: {res.sharpe_ratio:.2f}\n\n")
            
            # Comparison table
            f.write("\n" + "="*80 + "\n")
            f.write("CROSS-STRATEGY COMPARISON\n")
            f.write("="*80 + "\n\n")
            
            for phase in self.config.phases:
                f.write(f"\n{phase.name} ({phase.start_year}-{phase.end_year}):\n")
                f.write(f"{'Strategy':<40} {'Return':>10} {'Trades':>8} {'Win Rate':>10} {'Sharpe':>8}\n")
                f.write("-"*80 + "\n")
                
                for strategy_name, phases_dict in results.items():
                    res = phases_dict[phase.name]
                    f.write(f"{strategy_name:<40} {res.total_return*100:>9.2f}% {res.total_trades:>8} "
                           f"{res.win_rate*100:>9.1f}% {res.sharpe_ratio:>8.2f}\n")
                f.write("\n")
            
            # Key insights
            f.write("\n" + "="*80 + "\n")
            f.write("KEY INSIGHTS\n")
            f.write("="*80 + "\n\n")
            
            f.write("1. CONSISTENCY CHECK:\n")
            f.write("   - Compare In-Sample vs Out-of-Sample returns\n")
            f.write("   - If Out-of-Sample < 50% of In-Sample, strategy may be overfit\n\n")
            
            f.write("2. VALIDATION PHASE:\n")
            f.write("   - Should show similar performance to In-Sample\n")
            f.write("   - Large degradation indicates overfitting\n\n")
            
            f.write("3. WIN RATE STABILITY:\n")
            f.write("   - Win rate should remain 45%+ across all phases\n")
            f.write("   - Sharp drops indicate regime changes or overfitting\n\n")
            
            f.write("4. SHARPE RATIO:\n")
            f.write("   - Target: 1.5+ for all phases\n")
            f.write("   - Below 1.0 = poor risk-adjusted returns\n\n")
        
        self.logger.info(f"Saved comprehensive report to {report_file}")


def main():
    """Run comprehensive 3-phase backtest"""
    
    # Define top 3 strategies from optimization results
    strategies = [
        StrategyConfig(
            name="Mean Reversion RSI #2852",
            test_id=2852,
            strategy_type='mean_reversion_rsi',
            rsi_period=7,
            oversold_threshold=20.0,
            overbought_threshold=80.0,
            exit_strategy='rsi_neutral',
            exit_rsi_level=50.0,
            profit_target_pct=0.02,
            stop_loss_pct=-0.02,
            max_hold_days=5,
            min_volume_surge=1.5,
            min_momentum_pct=0.0
        ),
        StrategyConfig(
            name="Mean Reversion RSI #3831",
            test_id=3831,
            strategy_type='mean_reversion_rsi',
            rsi_period=21,
            oversold_threshold=25.0,
            overbought_threshold=80.0,
            exit_strategy='rsi_opposite',
            exit_rsi_level=None,
            profit_target_pct=0.03,
            stop_loss_pct=-0.02,
            max_hold_days=5,
            min_volume_surge=1.5,
            min_momentum_pct=0.0
        ),
        StrategyConfig(
            name="Hybrid #4872",
            test_id=4872,
            strategy_type='hybrid',
            rsi_period=14,
            oversold_threshold=30.0,
            overbought_threshold=70.0,
            exit_strategy='profit_target',
            exit_rsi_level=None,
            profit_target_pct=0.025,
            stop_loss_pct=-0.02,
            max_hold_days=3,
            min_volume_surge=1.3,
            min_momentum_pct=0.03  # 3% momentum for hybrid
        )
    ]
    
    # Backtest configuration
    config = BacktestConfig(
        symbols=['JBLU', 'AAL', 'CCL', 'RCL', 'F', 'GEVO', 'PLUG', 'FCEL', 'SBUX', 'SIRI', 'CAKE'],
        phases=[
            BacktestPhase('In-Sample', 2011, 2016, 'Training period for parameter validation'),
            BacktestPhase('Validation', 2017, 2019, 'Overfitting check'),
            BacktestPhase('Out-of-Sample', 2020, 2024, 'Real-world performance test')
        ],
        initial_capital=10000.0,
        position_size_pct=0.33,
        max_positions=3,
        results_dir='backtest/results/comprehensive',
        cache_dir='backtest/cache'
    )
    
    # Run backtest
    print("\n" + "="*80)
    print("COMPREHENSIVE 3-PHASE BACKTEST")
    print("="*80)
    print(f"\nStrategies: {len(strategies)}")
    for s in strategies:
        print(f"  - {s.name}")
    print(f"\nPhases:")
    for p in config.phases:
        print(f"  - {p.name} ({p.start_year}-{p.end_year})")
    print(f"\nSymbols: {', '.join(config.symbols)}")
    print(f"Initial Capital: ${config.initial_capital:,.2f}")
    print()
    
    runner = ComprehensiveBacktestRunner(config)
    results = runner.run_all_strategies(strategies)
    
    # Save results
    runner.save_results(results)
    
    # Print final summary
    print("\n" + "="*80)
    print("BACKTEST COMPLETE")
    print("="*80)
    print(f"\nResults saved to: {config.results_dir}")
    print("\nQuick Summary:")
    print(f"{'Strategy':<40} {'In-Sample':>12} {'Validation':>12} {'Out-of-Sample':>15}")
    print("-"*80)
    
    for strategy_name, phases in results.items():
        in_sample = phases['In-Sample'].total_return * 100
        validation = phases['Validation'].total_return * 100
        out_sample = phases['Out-of-Sample'].total_return * 100
        print(f"{strategy_name:<40} {in_sample:>11.2f}% {validation:>11.2f}% {out_sample:>14.2f}%")
    
    print("\n" + "="*80)


if __name__ == '__main__':
    main()

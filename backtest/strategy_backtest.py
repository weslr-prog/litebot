#!/usr/bin/env python3
"""
Enhanced Backtester for Short-Cycle D+1 Strategy
Tests the updated momentum (5%) + volume (1.5x) filters on historical data

Backtest Plan:
1. Daily bars: 5-year backtest (2017, 2018, 2020, 2021, 2022)
2. Intraday (1-minute): Recent 1-3 months for micro-testing
3. Compare performance between configurations
4. Tune strategy parameters

Test Stocks:
- Travel: JBLU, AAL, CCL, RCL
- Automotive: F (Ford)
- Energy/Green: GEVO, PLUG, FCEL
- Consumer: SBUX, SIRI, CAKE

Author: GitHub Copilot
Date: November 14, 2025
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
import logging
from dataclasses import dataclass, field, asdict
import json
import os
from pathlib import Path

# Try importing Alpaca, fallback to yfinance
try:
    from alpaca_trade_api.rest import REST, TimeFrame
    ALPACA_AVAILABLE = True
except ImportError:
    ALPACA_AVAILABLE = False

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

@dataclass
class BacktestConfig:
    """Configuration for backtest runs"""
    # Stocks to test
    symbols: List[str] = field(default_factory=lambda: [
        'JBLU', 'AAL', 'CCL', 'RCL',  # Travel/Cruise
        'F',                            # Automotive
        'GEVO', 'PLUG', 'FCEL',        # Green Energy
        'SBUX', 'SIRI', 'CAKE'         # Consumer
    ])
    
    # Time periods
    years: List[int] = field(default_factory=lambda: [2017, 2018, 2020, 2021, 2022])
    
    # Strategy parameters (BEFORE FIXES)
    baseline_min_momentum: float = 0.035  # 3.5% (old filter)
    baseline_min_volume: float = 1.0      # No filter (old)
    
    # Strategy parameters (AFTER FIXES)
    improved_min_momentum: float = 0.050  # 5.0% (new filter)
    improved_min_volume: float = 1.50     # 1.5x (new filter)
    
    # Entry/Exit rules
    hold_days: int = 1  # D+1 strategy
    profit_target: float = 0.03  # 3% profit target
    stop_loss: float = -0.05  # -5% emergency stop
    
    # Position sizing
    initial_capital: float = 10000.0
    position_size_pct: float = 0.33  # 33% per position (3 max concurrent)
    max_positions: int = 3
    
    # Data source
    data_source: str = 'alpaca'  # 'alpaca' or 'yfinance'
    alpaca_key: Optional[str] = None
    alpaca_secret: Optional[str] = None
    
    # Output
    results_dir: str = 'backtest/results'
    cache_dir: str = 'backtest/cache'


@dataclass
class Trade:
    """Individual trade record"""
    symbol: str
    entry_date: datetime
    entry_price: float
    exit_date: datetime
    exit_price: float
    shares: int
    pnl: float
    pnl_pct: float
    exit_reason: str  # 'PROFIT_TARGET', 'STOP_LOSS', 'TIME_EXIT'
    momentum_at_entry: float
    volume_surge_at_entry: float
    days_held: int


@dataclass
class BacktestResults:
    """Aggregated backtest results"""
    config_name: str
    start_date: datetime
    end_date: datetime
    initial_capital: float
    final_capital: float
    total_return: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    avg_win: float
    avg_loss: float
    win_loss_ratio: float
    max_drawdown: float
    sharpe_ratio: float
    trades: List[Trade] = field(default_factory=list)
    daily_equity: pd.DataFrame = field(default_factory=pd.DataFrame)
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        result = asdict(self)
        # Convert datetime objects
        result['start_date'] = self.start_date.isoformat()
        result['end_date'] = self.end_date.isoformat()
        # Convert trades
        result['trades'] = [
            {
                **asdict(t),
                'entry_date': t.entry_date.isoformat(),
                'exit_date': t.exit_date.isoformat()
            }
            for t in self.trades
        ]
        # Convert DataFrame to dict
        if not self.daily_equity.empty:
            result['daily_equity'] = self.daily_equity.to_dict(orient='records')
        return result


class DataFetcher:
    """Fetch historical price data from Alpaca or yFinance"""
    
    def __init__(self, config: BacktestConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Debug: Check availability flags
        self.logger.info(f"Alpaca available: {ALPACA_AVAILABLE}, yFinance available: {YFINANCE_AVAILABLE}")
        
        if config.data_source == 'alpaca' and ALPACA_AVAILABLE:
            # Only initialize API if we have credentials
            if config.alpaca_key or os.getenv('APCA_API_KEY_ID'):
                self.api = REST(
                    config.alpaca_key or os.getenv('APCA_API_KEY_ID'),
                    config.alpaca_secret or os.getenv('APCA_API_SECRET_KEY'),
                    base_url='https://paper-api.alpaca.markets'
                )
                self.use_alpaca = True
                self.logger.info("Using Alpaca for data")
            else:
                self.api = None
                self.use_alpaca = False
                self.logger.info("Using cached data (Alpaca credentials not available)")
        elif YFINANCE_AVAILABLE:
            self.api = None
            self.use_alpaca = False
            self.logger.info("Using yFinance for data")
        else:
            self.api = None
            self.use_alpaca = False
            self.logger.info("Using cached data only")
    
    def fetch_daily_bars(self, symbol: str, start: datetime, end: datetime) -> pd.DataFrame:
        """Fetch daily bars for a symbol"""
        cache_file = Path(self.config.cache_dir) / f"{symbol}_daily_{start.strftime('%Y%m%d')}_{end.strftime('%Y%m%d')}.csv"
        
        # Check cache first
        if cache_file.exists():
            self.logger.info(f"Loading {symbol} daily data from cache")
            df = pd.read_csv(cache_file, index_col=0)
            df.index = pd.to_datetime(df.index, utc=True).tz_localize(None)
            return df
        
        self.logger.info(f"Fetching {symbol} daily data from {start.date()} to {end.date()}")
        
        if self.use_alpaca:
            df = self._fetch_alpaca_daily(symbol, start, end)
        else:
            df = self._fetch_yfinance_daily(symbol, start, end)
        
        if not df.empty:
            # Ensure timezone-naive before caching
            if hasattr(df.index, 'tz') and df.index.tz is not None:
                df.index = df.index.tz_localize(None)
            # Cache the data
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(cache_file)
        
        return df
    
    def _fetch_alpaca_daily(self, symbol: str, start: datetime, end: datetime) -> pd.DataFrame:
        """Fetch from Alpaca"""
        try:
            bars = self.api.get_bars(
                symbol,
                TimeFrame.Day,
                start=start.isoformat(),
                end=end.isoformat(),
                adjustment='all'
            ).df
            
            if bars.empty:
                return pd.DataFrame()
            
            # Rename columns to standard format
            bars = bars.rename(columns={
                'open': 'Open',
                'high': 'High',
                'low': 'Low',
                'close': 'Close',
                'volume': 'Volume'
            })
            
            return bars
        except Exception as e:
            self.logger.error(f"Error fetching {symbol} from Alpaca: {e}")
            return pd.DataFrame()
    
    def _fetch_yfinance_daily(self, symbol: str, start: datetime, end: datetime) -> pd.DataFrame:
        """Fetch from yFinance"""
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(start=start, end=end)
            return df
        except Exception as e:
            self.logger.error(f"Error fetching {symbol} from yFinance: {e}")
            return pd.DataFrame()
    
    def fetch_minute_bars(self, symbol: str, start: datetime, end: datetime) -> pd.DataFrame:
        """Fetch 1-minute bars (Alpaca only)"""
        if not self.use_alpaca:
            raise ValueError("Minute data only available with Alpaca")
        
        cache_file = Path(self.config.cache_dir) / f"{symbol}_1min_{start.strftime('%Y%m%d')}_{end.strftime('%Y%m%d')}.parquet"
        
        if cache_file.exists():
            self.logger.info(f"Loading {symbol} minute data from cache")
            return pd.read_parquet(cache_file)
        
        self.logger.info(f"Fetching {symbol} minute data from {start.date()} to {end.date()}")
        
        try:
            bars = self.api.get_bars(
                symbol,
                TimeFrame.Minute,
                start=start.isoformat(),
                end=end.isoformat(),
                adjustment='all'
            ).df
            
            if not bars.empty:
                bars = bars.rename(columns={
                    'open': 'Open',
                    'high': 'High',
                    'low': 'Low',
                    'close': 'Close',
                    'volume': 'Volume'
                })
                
                # Cache the data
                cache_file.parent.mkdir(parents=True, exist_ok=True)
                bars.to_parquet(cache_file)
            
            return bars
        except Exception as e:
            self.logger.error(f"Error fetching minute bars for {symbol}: {e}")
            return pd.DataFrame()


class StrategyBacktester:
    """Backtest the short-cycle D+1 strategy with momentum + volume filters"""
    
    def __init__(self, config: BacktestConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.data_fetcher = DataFetcher(config)
    
    def calculate_signals(self, df: pd.DataFrame, min_momentum: float, min_volume: float) -> pd.DataFrame:
        """
        Calculate entry signals based on momentum and volume surge
        
        Mimics the bot's signal generation:
        1. Calculate momentum (daily % change)
        2. Calculate volume surge (current / 20-day avg)
        3. Filter: momentum >= min_momentum AND volume_surge >= min_volume
        """
        df = df.copy()
        
        # Calculate momentum (daily return)
        df['momentum'] = df['Close'].pct_change()
        
        # Calculate volume surge (current vs 20-day average)
        df['vol_avg_20'] = df['Volume'].rolling(20).mean()
        df['volume_surge'] = df['Volume'] / df['vol_avg_20']
        
        # Entry signal: momentum and volume both meet criteria
        df['signal'] = (
            (df['momentum'] >= min_momentum) & 
            (df['volume_surge'] >= min_volume)
        ).astype(int)
        
        return df
    
    def run_backtest_year(
        self,
        symbol: str,
        year: int,
        min_momentum: float,
        min_volume: float
    ) -> List[Trade]:
        """Run backtest for a single symbol for one year"""
        start = datetime(year, 1, 1)
        end = datetime(year, 12, 31)
        
        # Fetch data (need extra days for indicators)
        data_start = start - timedelta(days=60)
        df = self.data_fetcher.fetch_daily_bars(symbol, data_start, end)
        
        if df.empty or len(df) < 30:
            self.logger.warning(f"Insufficient data for {symbol} in {year}")
            return []
        
        # Calculate signals
        df = self.calculate_signals(df, min_momentum, min_volume)
        
        # Filter to actual backtest period
        df = df[df.index >= start]
        
        # Run trades
        trades = []
        in_position = False
        entry_date = None
        entry_price = None
        entry_momentum = None
        entry_volume = None
        shares = 0
        
        for date, row in df.iterrows():
            if not in_position and row['signal'] == 1:
                # Enter position
                in_position = True
                entry_date = date
                entry_price = row['Close']
                entry_momentum = row['momentum']
                entry_volume = row['volume_surge']
                
                # Calculate shares based on position size
                position_value = self.config.initial_capital * self.config.position_size_pct
                shares = int(position_value / entry_price)
                
                self.logger.debug(f"BUY {symbol} on {date.date()}: ${entry_price:.2f}, {shares} shares")
            
            elif in_position:
                # Check exit conditions
                days_held = (date - entry_date).days
                current_return = (row['Close'] - entry_price) / entry_price
                
                exit_reason = None
                
                # D+1 mandatory exit (after 1 day)
                if days_held >= self.config.hold_days:
                    # Check if profit target hit
                    if current_return >= self.config.profit_target:
                        exit_reason = 'PROFIT_TARGET'
                    # Check if stop loss hit
                    elif current_return <= self.config.stop_loss:
                        exit_reason = 'STOP_LOSS'
                    else:
                        exit_reason = 'TIME_EXIT'
                
                # Emergency stop loss (can trigger same day)
                elif current_return <= self.config.stop_loss:
                    exit_reason = 'EMERGENCY_STOP'
                
                if exit_reason:
                    # Exit position
                    exit_price = row['Close']
                    pnl = (exit_price - entry_price) * shares
                    pnl_pct = (exit_price - entry_price) / entry_price
                    
                    trade = Trade(
                        symbol=symbol,
                        entry_date=entry_date,
                        entry_price=entry_price,
                        exit_date=date,
                        exit_price=exit_price,
                        shares=shares,
                        pnl=pnl,
                        pnl_pct=pnl_pct,
                        exit_reason=exit_reason,
                        momentum_at_entry=entry_momentum,
                        volume_surge_at_entry=entry_volume,
                        days_held=days_held
                    )
                    
                    trades.append(trade)
                    self.logger.debug(f"SELL {symbol} on {date.date()}: ${exit_price:.2f}, P&L: ${pnl:.2f} ({pnl_pct*100:.1f}%), Reason: {exit_reason}")
                    
                    in_position = False
        
        return trades
    
    def run_full_backtest(
        self,
        config_name: str,
        min_momentum: float,
        min_volume: float
    ) -> BacktestResults:
        """Run backtest across all symbols and years"""
        self.logger.info(f"Running backtest: {config_name}")
        self.logger.info(f"  Momentum filter: {min_momentum*100:.1f}%")
        self.logger.info(f"  Volume filter: {min_volume:.2f}x")
        
        all_trades = []
        
        for symbol in self.config.symbols:
            for year in self.config.years:
                trades = self.run_backtest_year(symbol, year, min_momentum, min_volume)
                all_trades.extend(trades)
                self.logger.info(f"  {symbol} {year}: {len(trades)} trades")
        
        # Calculate aggregate metrics
        results = self._calculate_results(config_name, all_trades)
        
        return results
    
    def _calculate_results(self, config_name: str, trades: List[Trade]) -> BacktestResults:
        """Calculate aggregate backtest metrics"""
        if not trades:
            return BacktestResults(
                config_name=config_name,
                start_date=datetime.now(),
                end_date=datetime.now(),
                initial_capital=self.config.initial_capital,
                final_capital=self.config.initial_capital,
                total_return=0.0,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=0.0,
                avg_win=0.0,
                avg_loss=0.0,
                win_loss_ratio=0.0,
                max_drawdown=0.0,
                sharpe_ratio=0.0,
                trades=[]
            )
        
        # Basic stats
        total_pnl = sum(t.pnl for t in trades)
        winners = [t for t in trades if t.pnl > 0]
        losers = [t for t in trades if t.pnl < 0]
        
        win_rate = len(winners) / len(trades) if trades else 0
        avg_win = sum(t.pnl for t in winners) / len(winners) if winners else 0
        avg_loss = sum(t.pnl for t in losers) / len(losers) if losers else 0
        win_loss_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else 0
        
        final_capital = self.config.initial_capital + total_pnl
        total_return = total_pnl / self.config.initial_capital
        
        # Calculate equity curve
        equity_curve = [self.config.initial_capital]
        dates = [trades[0].entry_date]
        
        for trade in sorted(trades, key=lambda t: t.exit_date):
            equity_curve.append(equity_curve[-1] + trade.pnl)
            dates.append(trade.exit_date)
        
        daily_equity = pd.DataFrame({
            'date': dates,
            'equity': equity_curve
        }).set_index('date')
        
        # Calculate max drawdown
        running_max = daily_equity['equity'].expanding().max()
        drawdown = (daily_equity['equity'] - running_max) / running_max
        max_drawdown = drawdown.min()
        
        # Calculate Sharpe ratio (simplified)
        if len(trades) > 1:
            returns = [t.pnl_pct for t in trades]
            sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252) if np.std(returns) > 0 else 0
        else:
            sharpe_ratio = 0
        
        return BacktestResults(
            config_name=config_name,
            start_date=min(t.entry_date for t in trades),
            end_date=max(t.exit_date for t in trades),
            initial_capital=self.config.initial_capital,
            final_capital=final_capital,
            total_return=total_return,
            total_trades=len(trades),
            winning_trades=len(winners),
            losing_trades=len(losers),
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
            win_loss_ratio=win_loss_ratio,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            trades=trades,
            daily_equity=daily_equity
        )
    
    def compare_configurations(self) -> Dict[str, BacktestResults]:
        """Run and compare baseline vs improved filters"""
        results = {}
        
        # Run baseline (old filters)
        self.logger.info("\n" + "="*75)
        self.logger.info("BASELINE CONFIGURATION (Old Filters)")
        self.logger.info("="*75)
        results['baseline'] = self.run_full_backtest(
            'Baseline (3.5% momentum, 1.0x volume)',
            self.config.baseline_min_momentum,
            self.config.baseline_min_volume
        )
        
        # Run improved (new filters)
        self.logger.info("\n" + "="*75)
        self.logger.info("IMPROVED CONFIGURATION (New Filters)")
        self.logger.info("="*75)
        results['improved'] = self.run_full_backtest(
            'Improved (5.0% momentum, 1.5x volume)',
            self.config.improved_min_momentum,
            self.config.improved_min_volume
        )
        
        return results
    
    def save_results(self, results: Dict[str, BacktestResults]):
        """Save backtest results to files"""
        results_dir = Path(self.config.results_dir)
        results_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save summary JSON
        summary_file = results_dir / f'backtest_summary_{timestamp}.json'
        summary = {
            name: res.to_dict()
            for name, res in results.items()
        }
        
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        self.logger.info(f"Saved summary to {summary_file}")
        
        # Save detailed trade logs
        for name, res in results.items():
            trade_file = results_dir / f'trades_{name}_{timestamp}.csv'
            trades_df = pd.DataFrame([asdict(t) for t in res.trades])
            if not trades_df.empty:
                trades_df.to_csv(trade_file, index=False)
                self.logger.info(f"Saved {name} trades to {trade_file}")
        
        # Save comparison report
        self._generate_comparison_report(results, results_dir / f'comparison_{timestamp}.txt')
    
    def _generate_comparison_report(self, results: Dict[str, BacktestResults], filepath: Path):
        """Generate human-readable comparison report"""
        with open(filepath, 'w') as f:
            f.write("="*75 + "\n")
            f.write("BACKTEST COMPARISON REPORT\n")
            f.write("="*75 + "\n\n")
            
            for name, res in results.items():
                f.write(f"\n{res.config_name}\n")
                f.write("-"*75 + "\n")
                f.write(f"Period: {res.start_date.date()} to {res.end_date.date()}\n")
                f.write(f"Initial Capital: ${res.initial_capital:,.2f}\n")
                f.write(f"Final Capital: ${res.final_capital:,.2f}\n")
                f.write(f"Total Return: {res.total_return*100:+.2f}%\n\n")
                
                f.write(f"Total Trades: {res.total_trades}\n")
                f.write(f"Winning Trades: {res.winning_trades} ({res.win_rate*100:.1f}%)\n")
                f.write(f"Losing Trades: {res.losing_trades}\n")
                f.write(f"Average Win: ${res.avg_win:+.2f}\n")
                f.write(f"Average Loss: ${res.avg_loss:+.2f}\n")
                f.write(f"Win/Loss Ratio: {res.win_loss_ratio:.2f}:1\n\n")
                
                f.write(f"Max Drawdown: {res.max_drawdown*100:.2f}%\n")
                f.write(f"Sharpe Ratio: {res.sharpe_ratio:.2f}\n")
                f.write("\n")
            
            # Comparison
            if 'baseline' in results and 'improved' in results:
                baseline = results['baseline']
                improved = results['improved']
                
                f.write("\n" + "="*75 + "\n")
                f.write("IMPROVEMENT ANALYSIS\n")
                f.write("="*75 + "\n\n")
                
                return_improvement = (improved.total_return - baseline.total_return) / abs(baseline.total_return) * 100 if baseline.total_return != 0 else 0
                trades_reduction = ((baseline.total_trades - improved.total_trades) / baseline.total_trades * 100) if baseline.total_trades > 0 else 0
                win_rate_change = (improved.win_rate - baseline.win_rate) * 100
                
                f.write(f"Total Return Change: {return_improvement:+.1f}%\n")
                f.write(f"Trade Count Change: {trades_reduction:+.1f}% ({baseline.total_trades} → {improved.total_trades})\n")
                f.write(f"Win Rate Change: {win_rate_change:+.1f}% ({baseline.win_rate*100:.1f}% → {improved.win_rate*100:.1f}%)\n")
                f.write(f"Win/Loss Ratio: {baseline.win_loss_ratio:.2f}:1 → {improved.win_loss_ratio:.2f}:1\n")
                f.write(f"Sharpe Ratio: {baseline.sharpe_ratio:.2f} → {improved.sharpe_ratio:.2f}\n")
        
        self.logger.info(f"Saved comparison report to {filepath}")


def main():
    """Run the backtest"""
    # Configuration
    config = BacktestConfig(
        data_source='yfinance',  # Use yfinance for easier setup
        symbols=['JBLU', 'AAL', 'CCL', 'RCL', 'F', 'GEVO', 'PLUG', 'FCEL', 'SBUX', 'SIRI', 'CAKE'],
        years=[2017, 2018, 2020, 2021, 2022],
        results_dir='backtest/results',
        cache_dir='backtest/cache'
    )
    
    # Initialize backtester
    backtester = StrategyBacktester(config)
    
    # Run comparison
    print("\n" + "="*75)
    print("STARTING BACKTEST COMPARISON")
    print("="*75)
    print(f"Symbols: {', '.join(config.symbols)}")
    print(f"Years: {', '.join(map(str, config.years))}")
    print(f"Data Source: {config.data_source}")
    print()
    
    results = backtester.compare_configurations()
    
    # Print summary
    print("\n" + "="*75)
    print("RESULTS SUMMARY")
    print("="*75)
    
    for name, res in results.items():
        print(f"\n{res.config_name}:")
        print(f"  Total Return: {res.total_return*100:+.2f}%")
        print(f"  Total Trades: {res.total_trades}")
        print(f"  Win Rate: {res.win_rate*100:.1f}%")
        print(f"  Win/Loss Ratio: {res.win_loss_ratio:.2f}:1")
        print(f"  Max Drawdown: {res.max_drawdown*100:.2f}%")
        print(f"  Sharpe Ratio: {res.sharpe_ratio:.2f}")
    
    # Save results
    backtester.save_results(results)
    
    print("\n" + "="*75)
    print("BACKTEST COMPLETE")
    print("="*75)


if __name__ == '__main__':
    main()

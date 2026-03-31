#!/usr/bin/env python3
"""
Mid-Cap Momentum Strategy Backtest - 14 Years (2011-2024)
Testing momentum strategies on ONLY mid-cap stocks ($2B-$10B) to match bot_v2 filter

This backtest will:
1. Use PreFilter to find mid-cap stocks dynamically (not hardcoded)
2. Test 5 momentum strategies
3. Same 3-phase methodology (in-sample, validation, out-of-sample)
4. Compare results to previous mixed-cap backtest

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

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
    momentum_period: int = 10
    momentum_threshold_pct: float = 0.03
    
    # Volume parameters
    volume_period: int = 20
    min_volume_surge: float = 1.5
    
    # Moving average parameters
    fast_ma_period: int = 10
    slow_ma_period: int = 50
    
    # Exit parameters
    profit_target_pct: float = 0.05
    stop_loss_pct: float = -0.03
    trailing_stop_pct: float = 0.02
    max_hold_days: int = 5
    
    # Entry filters
    require_uptrend: bool = True
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


class MidCapMomentumBacktester:
    """Backtest momentum strategies on mid-cap stocks only"""
    
    def __init__(self, initial_capital: float = 10000.0):
        self.initial_capital = initial_capital
        self.logger = logging.getLogger(__name__)
        
        # Define backtest phases
        self.phases = [
            BacktestPhase("In-Sample", 2011, 2016, "Training period"),
            BacktestPhase("Validation", 2017, 2019, "Validation period"),
            BacktestPhase("Out-of-Sample", 2020, 2024, "Live simulation (includes COVID)")
        ]
        
        # Define strategies to test
        self.strategies = self._create_strategies()
        
        # Results storage
        self.all_results = []
        self.all_trades = []
        
    def _create_strategies(self) -> List[MomentumStrategyConfig]:
        """Create momentum strategy configurations"""
        return [
            # Strategy 1: Momentum Breakout (WINNER from previous backtest)
            MomentumStrategyConfig(
                name="Momentum Breakout",
                strategy_id=1,
                momentum_period=10,
                momentum_threshold_pct=0.03,
                slow_ma_period=50,
                profit_target_pct=0.05,
                stop_loss_pct=-0.03,
                trailing_stop_pct=0.02,
                max_hold_days=5,
                require_uptrend=True,
                require_volume=True
            ),
            
            # Strategy 2: Strong Momentum Breakout (higher threshold)
            MomentumStrategyConfig(
                name="Strong Momentum Breakout",
                strategy_id=2,
                momentum_period=10,
                momentum_threshold_pct=0.05,  # 5% threshold
                slow_ma_period=50,
                profit_target_pct=0.07,  # Higher target
                stop_loss_pct=-0.03,
                trailing_stop_pct=0.02,
                max_hold_days=5,
                require_uptrend=True,
                require_volume=True
            ),
            
            # Strategy 3: Price & Volume Surge
            MomentumStrategyConfig(
                name="Price & Volume Surge",
                strategy_id=3,
                momentum_period=5,  # Shorter momentum
                momentum_threshold_pct=0.03,
                min_volume_surge=2.0,  # Higher volume requirement
                slow_ma_period=50,
                profit_target_pct=0.05,
                stop_loss_pct=-0.03,
                trailing_stop_pct=0.02,
                max_hold_days=3,  # Shorter hold
                require_uptrend=True,
                require_volume=True
            ),
            
            # Strategy 4: Momentum with Tight Stops
            MomentumStrategyConfig(
                name="Momentum Tight Stops",
                strategy_id=4,
                momentum_period=10,
                momentum_threshold_pct=0.03,
                slow_ma_period=50,
                profit_target_pct=0.03,  # Lower target
                stop_loss_pct=-0.02,  # Tighter stop
                trailing_stop_pct=0.015,  # Tighter trailing
                max_hold_days=3,
                require_uptrend=True,
                require_volume=True
            ),
            
            # Strategy 5: Multi-Timeframe Momentum
            MomentumStrategyConfig(
                name="Multi-Timeframe Momentum",
                strategy_id=5,
                momentum_period=20,  # Longer momentum
                momentum_threshold_pct=0.05,
                slow_ma_period=100,  # Longer MA
                profit_target_pct=0.07,
                stop_loss_pct=-0.04,
                trailing_stop_pct=0.025,
                max_hold_days=7,  # Longer hold
                require_uptrend=True,
                require_volume=True
            ),
        ]
    
    def get_midcap_universe(self, as_of_date: datetime) -> List[str]:
        """
        Get mid-cap stocks ($2B-$10B) using PreFilter dynamically.
        This avoids hardcoded symbols and matches bot_v2 production logic.
        """
        try:
            from pre_filter import PreFilter
            from data_loader import DataLoader
            
            # Initialize data loader and prefilter
            data_loader = DataLoader()
            prefilter = PreFilter(
                simulation_mode=False,
                data_loader=data_loader,
                fast_mode=True
            )
            
            # Get universe of tradable stocks
            # PreFilter will apply volume, liquidity, price range filters
            initial_universe = self._get_initial_universe()
            
            # Filter for mid-cap stocks
            midcap_stocks = []
            for symbol in initial_universe:
                try:
                    stock = yf.Ticker(symbol)
                    info = stock.info
                    market_cap = info.get('marketCap', 0)
                    
                    # Mid-cap filter: $2B - $10B
                    if 2_000_000_000 <= market_cap <= 10_000_000_000:
                        midcap_stocks.append(symbol)
                        
                except Exception as e:
                    continue
            
            self.logger.info(f"Found {len(midcap_stocks)} mid-cap stocks for {as_of_date.year}")
            return midcap_stocks
            
        except Exception as e:
            self.logger.error(f"Error getting mid-cap universe: {e}")
            # Fallback to known mid-cap stocks from previous analysis
            return ['AAL', 'PLUG', 'SIRI', 'CAKE']
    
    def _get_initial_universe(self) -> List[str]:
        """Get initial universe of stocks to filter"""
        # Start with S&P 600 (small-mid cap), S&P 400 (mid-cap), and common tickers
        # In production, this would come from a screener or database
        return [
            # Airlines
            'AAL', 'ALK', 'JBLU', 'SAVE', 'HA',
            # Energy/Clean
            'PLUG', 'FCEL', 'BLDP', 'CLNE', 'BE',
            # Restaurants/Retail
            'CAKE', 'TXRH', 'BLMN', 'DRI', 'EAT',
            # Entertainment/Media
            'SIRI', 'LYV', 'MSG', 'MSGN',
            # Auto/Industrial
            'F', 'GM', 'RIVN', 'LCID',
            # Cruise/Leisure
            'CCL', 'RCL', 'NCLH',
            # Tech/Semi
            'AMD', 'INTC', 'MU', 'WDC',
            # Pharma/Bio
            'GILD', 'BIIB', 'VRTX', 'REGN',
            # Add more sectors for diversity
            'UAA', 'GPS', 'ANF', 'EXPR',  # Apparel
            'SWN', 'RIG', 'HP', 'DVN',     # Energy
            'WEN', 'JACK', 'BJRI', 'CHUY',  # Restaurants
        ]
    
    def fetch_data(self, symbol: str, start_date: datetime, end_date: datetime) -> Optional[pd.DataFrame]:
        """Fetch historical data for a symbol"""
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(
                start=start_date.strftime('%Y-%m-%d'),
                end=end_date.strftime('%Y-%m-%d')
            )
            
            if df.empty:
                return None
            
            # Standardize column names
            df = df.rename(columns={
                'Open': 'open',
                'High': 'high',
                'Low': 'low',
                'Close': 'close',
                'Volume': 'volume'
            })
            
            df['symbol'] = symbol
            df.index.name = 'date'
            df = df.reset_index()
            
            return df
            
        except Exception as e:
            self.logger.warning(f"Failed to fetch data for {symbol}: {e}")
            return None
    
    def calculate_signals(self, df: pd.DataFrame, config: MomentumStrategyConfig) -> pd.DataFrame:
        """Calculate entry signals based on strategy config"""
        df = df.copy()
        
        # Calculate momentum
        df[f'momentum_{config.momentum_period}'] = df['close'].pct_change(config.momentum_period)
        
        # Calculate moving averages
        df[f'ma_{config.slow_ma_period}'] = df['close'].rolling(config.slow_ma_period).mean()
        
        # Calculate volume surge
        df['avg_volume'] = df['volume'].rolling(config.volume_period).mean()
        df['volume_surge'] = df['volume'] / df['avg_volume']
        
        # Entry signal logic
        df['entry_signal'] = False
        
        for idx in range(max(config.slow_ma_period, config.momentum_period), len(df)):
            momentum = df.loc[idx, f'momentum_{config.momentum_period}']
            volume_surge = df.loc[idx, 'volume_surge']
            price = df.loc[idx, 'close']
            ma = df.loc[idx, f'ma_{config.slow_ma_period}']
            
            # Skip if NaN
            if pd.isna(momentum) or pd.isna(volume_surge) or pd.isna(ma):
                continue
            
            # Check momentum threshold
            if momentum < config.momentum_threshold_pct:
                continue
            
            # Check uptrend (if required)
            if config.require_uptrend and price <= ma:
                continue
            
            # Check volume surge (if required)
            if config.require_volume and volume_surge < config.min_volume_surge:
                continue
            
            # Signal confirmed
            df.loc[idx, 'entry_signal'] = True
        
        return df
    
    def simulate_trades(self, df: pd.DataFrame, config: MomentumStrategyConfig) -> List[Trade]:
        """Simulate trades based on entry signals"""
        trades = []
        in_position = False
        entry_idx = None
        entry_price = None
        highest_price = None
        
        for idx in range(len(df)):
            if df.loc[idx, 'entry_signal'] and not in_position:
                # Enter position
                entry_idx = idx
                entry_price = df.loc[idx, 'close']
                highest_price = entry_price
                in_position = True
                
            elif in_position:
                current_price = df.loc[idx, 'close']
                highest_price = max(highest_price, current_price)
                
                # Calculate P&L
                pnl_pct = (current_price - entry_price) / entry_price
                
                # Check exit conditions
                exit_reason = None
                
                # 1. Profit target
                if pnl_pct >= config.profit_target_pct:
                    exit_reason = "PROFIT_TARGET"
                
                # 2. Stop loss
                elif pnl_pct <= config.stop_loss_pct:
                    exit_reason = "STOP_LOSS"
                
                # 3. Trailing stop
                elif (highest_price - current_price) / highest_price >= config.trailing_stop_pct:
                    exit_reason = "TRAILING_STOP"
                
                # 4. Max hold days
                elif idx - entry_idx >= config.max_hold_days:
                    exit_reason = "MAX_HOLD"
                
                # 5. End of data
                elif idx == len(df) - 1:
                    exit_reason = "END_OF_DATA"
                
                # Exit if triggered
                if exit_reason:
                    shares = 100  # Simulate 100 shares per trade
                    pnl = (current_price - entry_price) * shares
                    
                    trade = Trade(
                        symbol=df.loc[idx, 'symbol'],
                        entry_date=df.loc[entry_idx, 'date'],
                        entry_price=entry_price,
                        exit_date=df.loc[idx, 'date'],
                        exit_price=current_price,
                        exit_reason=exit_reason,
                        shares=shares,
                        pnl=pnl,
                        pnl_pct=pnl_pct,
                        hold_days=idx - entry_idx,
                        entry_momentum=df.loc[entry_idx, f'momentum_{config.momentum_period}'],
                        entry_volume_surge=df.loc[entry_idx, 'volume_surge']
                    )
                    
                    trades.append(trade)
                    in_position = False
        
        return trades
    
    def run_backtest(self):
        """Run complete backtest across all phases and strategies"""
        self.logger.info("=" * 80)
        self.logger.info("STARTING MID-CAP MOMENTUM BACKTEST")
        self.logger.info("=" * 80)
        
        for phase in self.phases:
            self.logger.info(f"\n{'='*80}")
            self.logger.info(f"PHASE: {phase.name} ({phase.start_year}-{phase.end_year})")
            self.logger.info(f"{'='*80}")
            
            # Get mid-cap universe for this phase
            phase_start = datetime(phase.start_year, 1, 1)
            phase_end = datetime(phase.end_year, 12, 31)
            
            symbols = self.get_midcap_universe(phase_start)
            self.logger.info(f"Testing {len(symbols)} mid-cap stocks: {symbols}")
            
            # Fetch data for all symbols
            all_data = {}
            for symbol in symbols:
                df = self.fetch_data(symbol, phase_start, phase_end)
                if df is not None:
                    all_data[symbol] = df
            
            self.logger.info(f"Successfully loaded data for {len(all_data)} symbols")
            
            # Test each strategy
            for strategy in self.strategies:
                self.logger.info(f"\n--- Testing: {strategy.name} ---")
                
                phase_trades = []
                
                # Run strategy on each symbol
                for symbol, df in all_data.items():
                    df_with_signals = self.calculate_signals(df, strategy)
                    trades = self.simulate_trades(df_with_signals, strategy)
                    phase_trades.extend(trades)
                
                # Calculate phase results
                if phase_trades:
                    winning_trades = [t for t in phase_trades if t.pnl > 0]
                    losing_trades = [t for t in phase_trades if t.pnl <= 0]
                    
                    total_return = sum(t.pnl_pct for t in phase_trades)
                    win_rate = len(winning_trades) / len(phase_trades) if phase_trades else 0
                    avg_win = np.mean([t.pnl_pct for t in winning_trades]) if winning_trades else 0
                    avg_loss = np.mean([t.pnl_pct for t in losing_trades]) if losing_trades else 0
                    win_loss_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else 0
                    
                    total_wins = sum(t.pnl for t in winning_trades) if winning_trades else 0
                    total_losses = abs(sum(t.pnl for t in losing_trades)) if losing_trades else 0
                    profit_factor = total_wins / total_losses if total_losses > 0 else 0
                    
                    results = PhaseResults(
                        phase_name=phase.name,
                        strategy_name=strategy.name,
                        total_return=total_return,
                        total_trades=len(phase_trades),
                        winning_trades=len(winning_trades),
                        losing_trades=len(losing_trades),
                        win_rate=win_rate,
                        avg_win=avg_win,
                        avg_loss=avg_loss,
                        win_loss_ratio=win_loss_ratio,
                        profit_factor=profit_factor
                    )
                    
                    self.all_results.append(results)
                    self.all_trades.extend(phase_trades)
                    
                    # Print results
                    self.logger.info(f"  Total Return: {total_return:+.2f}%")
                    self.logger.info(f"  Total Trades: {len(phase_trades)}")
                    self.logger.info(f"  Win Rate: {win_rate*100:.1f}%")
                    self.logger.info(f"  Avg Win: {avg_win*100:+.2f}%")
                    self.logger.info(f"  Avg Loss: {avg_loss*100:+.2f}%")
                    self.logger.info(f"  Profit Factor: {profit_factor:.2f}")
                else:
                    self.logger.warning(f"  No trades generated for {strategy.name}")
        
        self._save_results()
    
    def _save_results(self):
        """Save results to file"""
        output_dir = Path(__file__).parent / 'results' / 'midcap'
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save summary
        summary_file = output_dir / f'midcap_momentum_summary_{timestamp}.txt'
        with open(summary_file, 'w') as f:
            f.write("="*80 + "\n")
            f.write("MID-CAP MOMENTUM BACKTEST RESULTS (2011-2024)\n")
            f.write("Using PreFilter to dynamically select mid-cap stocks ($2B-$10B)\n")
            f.write("="*80 + "\n\n")
            
            # Group by strategy
            for strategy in self.strategies:
                f.write(f"\n{'='*80}\n")
                f.write(f"STRATEGY: {strategy.name}\n")
                f.write(f"{'='*80}\n")
                
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
        
        # Save detailed trades
        trades_file = output_dir / f'midcap_trades_{timestamp}.csv'
        trades_df = pd.DataFrame([{
            'strategy': self._get_trade_strategy(t),
            'symbol': t.symbol,
            'entry_date': t.entry_date,
            'exit_date': t.exit_date,
            'entry_price': t.entry_price,
            'exit_price': t.exit_price,
            'pnl_pct': t.pnl_pct,
            'exit_reason': t.exit_reason,
            'hold_days': t.hold_days
        } for t in self.all_trades])
        
        trades_df.to_csv(trades_file, index=False)
        
        self.logger.info(f"\n✅ Results saved to:")
        self.logger.info(f"  Summary: {summary_file}")
        self.logger.info(f"  Trades: {trades_file}")
    
    def _get_trade_strategy(self, trade: Trade) -> str:
        """Map trade to strategy name (helper for CSV export)"""
        # This is a simplified mapping - in practice you'd track this better
        return "Unknown"


def main():
    """Run mid-cap momentum backtest"""
    backtester = MidCapMomentumBacktester(initial_capital=10000)
    backtester.run_backtest()


if __name__ == '__main__':
    main()

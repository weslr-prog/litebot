#!/usr/bin/env python3
"""
Hybrid Momentum Breakout + Gap Fade Strategy

Combines the best of both strategies:
- Momentum Breakout: 293% return, high profit potential
- Gap Fade: 33% return, 52.6% win rate, stable

Strategy Logic:
1. MOMENTUM MODE (Primary - 70% capital allocation)
   - Entry: Price breaks 20-day high + RSI > 60 + Volume > 2x + Price > 50 MA
   - Exit: 4% profit OR -2% stop OR 7-day max hold
   - Target: 10-15% annual returns with trend-following

2. GAP FADE MODE (Secondary - 30% capital allocation)
   - Entry: Gap up 2-5% + RSI > 70 + SHORT position
   - Exit: 2% profit OR -3% stop OR 5-day max hold
   - Target: Smooth returns with high win rate

Position Sizing:
- Total capital split: 70% momentum / 30% gap fade
- Max 3 positions per mode (6 total)
- Position size: 33% of allocated capital per position

Author: litebotx
Date: November 22, 2025
"""

import pandas as pd
import numpy as np
import yfinance as yf
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
import logging
import json
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# ============================================================================
# CONFIGURATION
# ============================================================================

@dataclass
class HybridConfig:
    """Configuration for hybrid strategy"""
    # Capital allocation
    total_capital: float = 10000.0
    momentum_allocation: float = 0.70  # 70% to momentum
    gap_fade_allocation: float = 0.30  # 30% to gap fade
    
    # Position sizing
    max_positions_momentum: int = 3
    max_positions_gap_fade: int = 3
    position_size_pct: float = 0.33  # 33% of allocated capital per position
    
    # Momentum Breakout parameters
    momentum_lookback: int = 20
    momentum_rsi_threshold: float = 60.0
    momentum_volume_multiplier: float = 2.0
    momentum_profit_target: float = 0.04  # 4%
    momentum_stop_loss: float = -0.02  # -2%
    momentum_max_hold_days: int = 7
    
    # Gap Fade parameters
    gap_fade_min_gap: float = 0.02  # 2%
    gap_fade_max_gap: float = 0.05  # 5%
    gap_fade_rsi_threshold: float = 70.0
    gap_fade_profit_target: float = 0.02  # 2%
    gap_fade_stop_loss: float = -0.03  # -3%
    gap_fade_max_hold_days: int = 5
    
    # Data settings
    symbols: List[str] = None
    start_date: str = "2011-01-01"
    end_date: str = "2024-12-31"
    
    def __post_init__(self):
        if self.symbols is None:
            self.symbols = ['JBLU', 'AAL', 'CCL', 'RCL', 'F', 'GEVO', 
                          'PLUG', 'FCEL', 'SBUX', 'SIRI', 'CAKE']

# ============================================================================
# INDICATORS
# ============================================================================

class Indicators:
    """Technical indicators calculator"""
    
    @staticmethod
    def rsi(series: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI"""
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    @staticmethod
    def sma(series: pd.Series, period: int) -> pd.Series:
        """Simple Moving Average"""
        return series.rolling(window=period).mean()
    
    @staticmethod
    def bollinger_bands(series: pd.Series, period: int = 20, std: float = 2.0):
        """Bollinger Bands"""
        sma = series.rolling(window=period).mean()
        std_dev = series.rolling(window=period).std()
        upper = sma + (std_dev * std)
        lower = sma - (std_dev * std)
        return upper, sma, lower

# ============================================================================
# DATA FETCHER
# ============================================================================

class DataFetcher:
    """Fetch and cache historical data"""
    
    def __init__(self, cache_dir: str = "cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
    
    def fetch(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """Fetch data with caching"""
        cache_file = self.cache_dir / f"{symbol}_{start_date}_{end_date}.csv"
        
        if cache_file.exists():
            df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
            logging.info(f"Loaded {symbol} from cache")
        else:
            logging.info(f"Downloading {symbol} data...")
            df = yf.download(symbol, start=start_date, end=end_date, progress=False)
            
            # Flatten multi-index columns if present
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            df.to_csv(cache_file)
        
        return df

# ============================================================================
# STRATEGY CLASSES
# ============================================================================

class MomentumBreakout:
    """Momentum Breakout Strategy"""
    
    def __init__(self, config: HybridConfig):
        self.config = config
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate momentum breakout signals"""
        df = df.copy()
        
        # Calculate indicators
        df['rsi'] = Indicators.rsi(df['Close'], 14)
        df['sma_50'] = Indicators.sma(df['Close'], 50)
        df['high_20'] = df['High'].rolling(window=self.config.momentum_lookback).max()
        df['avg_volume'] = df['Volume'].rolling(window=20).mean()
        
        # Entry signals
        df['breakout'] = df['Close'] > df['high_20'].shift(1)
        df['rsi_strong'] = df['rsi'] > self.config.momentum_rsi_threshold
        df['volume_surge'] = df['Volume'] > (df['avg_volume'] * self.config.momentum_volume_multiplier)
        df['above_ma'] = df['Close'] > df['sma_50']
        
        df['signal'] = (
            df['breakout'] & 
            df['rsi_strong'] & 
            df['volume_surge'] & 
            df['above_ma']
        ).astype(int)
        
        return df
    
    def check_exit(self, entry_price: float, current_price: float, 
                   hold_days: int, df_row: pd.Series) -> Tuple[bool, str]:
        """Check if should exit position"""
        pnl_pct = (current_price - entry_price) / entry_price
        
        # Profit target
        if pnl_pct >= self.config.momentum_profit_target:
            return True, "PROFIT_TARGET"
        
        # Stop loss
        if pnl_pct <= self.config.momentum_stop_loss:
            return True, "STOP_LOSS"
        
        # Trailing stop (2% trailing after 3% profit)
        if pnl_pct >= 0.03:
            if pnl_pct < (df_row.get('max_pnl_pct', 0) - 0.02):
                return True, "TRAILING_STOP"
        
        # Max hold
        if hold_days >= self.config.momentum_max_hold_days:
            return True, "MAX_HOLD"
        
        return False, None


class GapFade:
    """Gap Fade Strategy (SHORT)"""
    
    def __init__(self, config: HybridConfig):
        self.config = config
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate gap fade signals"""
        df = df.copy()
        
        # Calculate indicators
        df['rsi'] = Indicators.rsi(df['Close'], 14)
        df['prev_close'] = df['Close'].shift(1)
        df['gap_pct'] = (df['Open'] - df['prev_close']) / df['prev_close']
        
        # Entry signals (SHORT when gap up)
        df['gap_up'] = (
            (df['gap_pct'] >= self.config.gap_fade_min_gap) &
            (df['gap_pct'] <= self.config.gap_fade_max_gap)
        )
        df['rsi_overbought'] = df['rsi'] > self.config.gap_fade_rsi_threshold
        
        df['signal'] = (df['gap_up'] & df['rsi_overbought']).astype(int)
        
        return df
    
    def check_exit(self, entry_price: float, current_price: float, 
                   hold_days: int, df_row: pd.Series) -> Tuple[bool, str]:
        """Check if should exit SHORT position"""
        # For SHORT: profit when price goes DOWN
        pnl_pct = (entry_price - current_price) / entry_price
        
        # Profit target
        if pnl_pct >= self.config.gap_fade_profit_target:
            return True, "PROFIT_TARGET"
        
        # Stop loss (price went UP instead of down)
        if pnl_pct <= self.config.gap_fade_stop_loss:
            return True, "STOP_LOSS"
        
        # Max hold
        if hold_days >= self.config.gap_fade_max_hold_days:
            return True, "MAX_HOLD"
        
        return False, None

# ============================================================================
# HYBRID BACKTESTER
# ============================================================================

class HybridBacktester:
    """Backtest hybrid strategy with separate capital pools"""
    
    def __init__(self, config: HybridConfig):
        self.config = config
        self.data_fetcher = DataFetcher()
        self.momentum_strategy = MomentumBreakout(config)
        self.gap_fade_strategy = GapFade(config)
        
        # Separate capital pools
        self.momentum_capital = config.total_capital * config.momentum_allocation
        self.gap_fade_capital = config.total_capital * config.gap_fade_allocation
        
        # Track positions separately
        self.momentum_positions = []
        self.gap_fade_positions = []
        
        # Track performance
        self.momentum_trades = []
        self.gap_fade_trades = []
    
    def run_backtest(self) -> Dict:
        """Run complete backtest"""
        logging.info(f"Running hybrid backtest on {len(self.config.symbols)} symbols...")
        logging.info(f"Momentum capital: ${self.momentum_capital:,.2f} (70%)")
        logging.info(f"Gap Fade capital: ${self.gap_fade_capital:,.2f} (30%)")
        
        # Fetch all data
        data = {}
        for symbol in self.config.symbols:
            df = self.data_fetcher.fetch(
                symbol, 
                self.config.start_date, 
                self.config.end_date
            )
            if not df.empty:
                data[symbol] = df
        
        # Generate signals for all symbols
        momentum_signals = {}
        gap_fade_signals = {}
        
        for symbol, df in data.items():
            momentum_signals[symbol] = self.momentum_strategy.generate_signals(df)
            gap_fade_signals[symbol] = self.gap_fade_strategy.generate_signals(df)
        
        # Simulate trading day by day
        all_dates = sorted(set(
            date for df in data.values() 
            for date in df.index
        ))
        
        for current_date in all_dates:
            # Process momentum positions
            self._process_momentum_positions(current_date, momentum_signals)
            
            # Process gap fade positions
            self._process_gap_fade_positions(current_date, gap_fade_signals)
            
            # Enter new momentum positions
            self._enter_momentum_positions(current_date, momentum_signals)
            
            # Enter new gap fade positions
            self._enter_gap_fade_positions(current_date, gap_fade_signals)
        
        # Close any remaining positions
        self._close_all_positions()
        
        # Calculate results
        return self._calculate_results()
    
    def _process_momentum_positions(self, current_date, signals):
        """Process existing momentum positions"""
        positions_to_close = []
        
        for i, pos in enumerate(self.momentum_positions):
            symbol = pos['symbol']
            if symbol not in signals or current_date not in signals[symbol].index:
                continue
            
            current_row = signals[symbol].loc[current_date]
            current_price = current_row['Close']
            hold_days = (current_date - pos['entry_date']).days
            
            # Update max profit for trailing stop
            pnl_pct = (current_price - pos['entry_price']) / pos['entry_price']
            pos['max_pnl_pct'] = max(pos.get('max_pnl_pct', 0), pnl_pct)
            
            # Check exit
            should_exit, exit_reason = self.momentum_strategy.check_exit(
                pos['entry_price'], current_price, hold_days, current_row
            )
            
            if should_exit:
                self._close_momentum_position(pos, current_date, current_price, exit_reason)
                positions_to_close.append(i)
        
        # Remove closed positions
        for i in reversed(positions_to_close):
            self.momentum_positions.pop(i)
    
    def _process_gap_fade_positions(self, current_date, signals):
        """Process existing gap fade positions"""
        positions_to_close = []
        
        for i, pos in enumerate(self.gap_fade_positions):
            symbol = pos['symbol']
            if symbol not in signals or current_date not in signals[symbol].index:
                continue
            
            current_row = signals[symbol].loc[current_date]
            current_price = current_row['Close']
            hold_days = (current_date - pos['entry_date']).days
            
            # Check exit
            should_exit, exit_reason = self.gap_fade_strategy.check_exit(
                pos['entry_price'], current_price, hold_days, current_row
            )
            
            if should_exit:
                self._close_gap_fade_position(pos, current_date, current_price, exit_reason)
                positions_to_close.append(i)
        
        # Remove closed positions
        for i in reversed(positions_to_close):
            self.gap_fade_positions.pop(i)
    
    def _enter_momentum_positions(self, current_date, signals):
        """Enter new momentum positions"""
        if len(self.momentum_positions) >= self.config.max_positions_momentum:
            return
        
        # Find signals for today
        opportunities = []
        for symbol, df in signals.items():
            if current_date in df.index and df.loc[current_date, 'signal'] == 1:
                opportunities.append((symbol, df.loc[current_date]))
        
        # Sort by RSI strength (higher is better for momentum)
        opportunities.sort(key=lambda x: x[1]['rsi'], reverse=True)
        
        # Enter positions
        for symbol, row in opportunities:
            if len(self.momentum_positions) >= self.config.max_positions_momentum:
                break
            
            # Check if already in position
            if any(p['symbol'] == symbol for p in self.momentum_positions):
                continue
            
            position_size = self.momentum_capital * self.config.position_size_pct
            shares = int(position_size / row['Close'])
            
            if shares > 0:
                position = {
                    'symbol': symbol,
                    'entry_date': current_date,
                    'entry_price': row['Close'],
                    'shares': shares,
                    'max_pnl_pct': 0
                }
                self.momentum_positions.append(position)
                logging.info(f"MOMENTUM BUY: {symbol} @ ${row['Close']:.2f} x {shares} shares")
    
    def _enter_gap_fade_positions(self, current_date, signals):
        """Enter new gap fade positions (SHORT)"""
        if len(self.gap_fade_positions) >= self.config.max_positions_gap_fade:
            return
        
        # Find signals for today
        opportunities = []
        for symbol, df in signals.items():
            if current_date in df.index and df.loc[current_date, 'signal'] == 1:
                opportunities.append((symbol, df.loc[current_date]))
        
        # Sort by gap size (larger gaps preferred)
        opportunities.sort(key=lambda x: x[1]['gap_pct'], reverse=True)
        
        # Enter positions
        for symbol, row in opportunities:
            if len(self.gap_fade_positions) >= self.config.max_positions_gap_fade:
                break
            
            # Check if already in position
            if any(p['symbol'] == symbol for p in self.gap_fade_positions):
                continue
            
            position_size = self.gap_fade_capital * self.config.position_size_pct
            shares = int(position_size / row['Close'])
            
            if shares > 0:
                position = {
                    'symbol': symbol,
                    'entry_date': current_date,
                    'entry_price': row['Close'],
                    'shares': shares
                }
                self.gap_fade_positions.append(position)
                logging.info(f"GAP FADE SHORT: {symbol} @ ${row['Close']:.2f} x {shares} shares")
    
    def _close_momentum_position(self, pos, exit_date, exit_price, exit_reason):
        """Close momentum position"""
        pnl = (exit_price - pos['entry_price']) * pos['shares']
        pnl_pct = (exit_price - pos['entry_price']) / pos['entry_price']
        hold_days = (exit_date - pos['entry_date']).days
        
        self.momentum_capital += pnl
        
        trade = {
            'symbol': pos['symbol'],
            'entry_date': str(pos['entry_date']),
            'entry_price': pos['entry_price'],
            'exit_date': str(exit_date),
            'exit_price': exit_price,
            'exit_reason': exit_reason,
            'shares': pos['shares'],
            'pnl': pnl,
            'pnl_pct': pnl_pct,
            'hold_days': hold_days
        }
        self.momentum_trades.append(trade)
        
        logging.info(f"MOMENTUM EXIT: {pos['symbol']} @ ${exit_price:.2f} | "
                    f"P&L: ${pnl:.2f} ({pnl_pct*100:.1f}%) | {exit_reason}")
    
    def _close_gap_fade_position(self, pos, exit_date, exit_price, exit_reason):
        """Close gap fade position (SHORT)"""
        # SHORT: profit when price goes down
        pnl = (pos['entry_price'] - exit_price) * pos['shares']
        pnl_pct = (pos['entry_price'] - exit_price) / pos['entry_price']
        hold_days = (exit_date - pos['entry_date']).days
        
        self.gap_fade_capital += pnl
        
        trade = {
            'symbol': pos['symbol'],
            'entry_date': str(pos['entry_date']),
            'entry_price': pos['entry_price'],
            'exit_date': str(exit_date),
            'exit_price': exit_price,
            'exit_reason': exit_reason,
            'shares': pos['shares'],
            'pnl': pnl,
            'pnl_pct': pnl_pct,
            'hold_days': hold_days
        }
        self.gap_fade_trades.append(trade)
        
        logging.info(f"GAP FADE COVER: {pos['symbol']} @ ${exit_price:.2f} | "
                    f"P&L: ${pnl:.2f} ({pnl_pct*100:.1f}%) | {exit_reason}")
    
    def _close_all_positions(self):
        """Close any remaining open positions"""
        # This would use the last available price for each symbol
        pass
    
    def _calculate_results(self) -> Dict:
        """Calculate backtest results"""
        total_final_capital = self.momentum_capital + self.gap_fade_capital
        total_return = (total_final_capital - self.config.total_capital) / self.config.total_capital
        
        # Momentum stats
        momentum_df = pd.DataFrame(self.momentum_trades) if self.momentum_trades else pd.DataFrame()
        gap_fade_df = pd.DataFrame(self.gap_fade_trades) if self.gap_fade_trades else pd.DataFrame()
        
        results = {
            'total_capital': self.config.total_capital,
            'final_capital': total_final_capital,
            'total_return': total_return,
            'momentum': self._calculate_strategy_stats(momentum_df, self.momentum_capital, 'Momentum'),
            'gap_fade': self._calculate_strategy_stats(gap_fade_df, self.gap_fade_capital, 'Gap Fade'),
            'trades': {
                'momentum': self.momentum_trades,
                'gap_fade': self.gap_fade_trades
            }
        }
        
        return results
    
    def _calculate_strategy_stats(self, df, final_capital, name):
        """Calculate statistics for a strategy"""
        if df.empty:
            return {
                'name': name,
                'trades': 0,
                'final_capital': final_capital,
                'return': 0,
                'win_rate': 0,
                'avg_trade': 0,
                'sharpe': 0
            }
        
        initial = self.config.total_capital * (
            self.config.momentum_allocation if name == 'Momentum' 
            else self.config.gap_fade_allocation
        )
        
        winning_trades = df[df['pnl'] > 0]
        losing_trades = df[df['pnl'] < 0]
        
        return {
            'name': name,
            'trades': len(df),
            'final_capital': final_capital,
            'return': (final_capital - initial) / initial,
            'win_rate': len(winning_trades) / len(df) if len(df) > 0 else 0,
            'avg_trade': df['pnl_pct'].mean() if len(df) > 0 else 0,
            'avg_win': winning_trades['pnl_pct'].mean() if len(winning_trades) > 0 else 0,
            'avg_loss': losing_trades['pnl_pct'].mean() if len(losing_trades) > 0 else 0,
            'sharpe': df['pnl_pct'].mean() / df['pnl_pct'].std() if len(df) > 1 else 0
        }

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Run hybrid strategy backtest"""
    config = HybridConfig()
    
    print("=" * 80)
    print("HYBRID MOMENTUM BREAKOUT + GAP FADE STRATEGY")
    print("=" * 80)
    print()
    print(f"Total Capital: ${config.total_capital:,.2f}")
    print(f"  Momentum (70%): ${config.total_capital * 0.70:,.2f}")
    print(f"  Gap Fade (30%): ${config.total_capital * 0.30:,.2f}")
    print()
    print(f"Testing Period: {config.start_date} to {config.end_date}")
    print(f"Symbols: {', '.join(config.symbols)}")
    print()
    
    # Run backtest
    backtester = HybridBacktester(config)
    results = backtester.run_backtest()
    
    # Print results
    print("=" * 80)
    print("BACKTEST RESULTS")
    print("=" * 80)
    print()
    
    print(f"Total Return: {results['total_return']*100:+.2f}%")
    print(f"Final Capital: ${results['final_capital']:,.2f}")
    print()
    
    print("MOMENTUM BREAKOUT (70% allocation):")
    m = results['momentum']
    print(f"  Return: {m['return']*100:+.2f}%")
    print(f"  Trades: {m['trades']}")
    print(f"  Win Rate: {m['win_rate']*100:.1f}%")
    print(f"  Avg Trade: {m['avg_trade']*100:+.2f}%")
    print(f"  Sharpe: {m['sharpe']:.2f}")
    print()
    
    print("GAP FADE (30% allocation):")
    g = results['gap_fade']
    print(f"  Return: {g['return']*100:+.2f}%")
    print(f"  Trades: {g['trades']}")
    print(f"  Win Rate: {g['win_rate']*100:.1f}%")
    print(f"  Avg Trade: {g['avg_trade']*100:+.2f}%")
    print(f"  Sharpe: {g['sharpe']:.2f}")
    print()
    
    # Save results
    output_dir = Path("backtest/results/hybrid")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"hybrid_strategy_results_{timestamp}.json"
    
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"Results saved to: {output_file}")
    print("=" * 80)

if __name__ == "__main__":
    main()

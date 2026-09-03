#!/usr/bin/env python3
"""
Adaptive Risk Manager - Dynamic risk parameter adjustment based on bot performance
Automatically optimizes stop-loss, profit targets, and time stops based on:
- Win rate trends
- Average P&L per trade
- Drawdown patterns
- Market volatility regime
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import numpy as np
from dataclasses import dataclass, asdict


@dataclass
class RiskParameters:
    """Aggressive swing trading risk parameters"""
    stop_loss_pct: float = 0.025            # 2.5% stop-loss (was 0.03)
    profit_target_pct: float = 0.15          # 15% profit target (was 0.06)
    time_stop_days: int = 45                 # 45 days for momentum development (was 10)
    confidence_threshold: float = 0.6        # Lower threshold for more opportunities (was 0.7)
    
    # NEW: Trailing stop parameters for swing trading
    trailing_stop_pct: float = 0.08          # 8% trailing stop from peak
    breakout_profit_target: float = 0.25     # 25% target for strong breakouts
    momentum_extension_days: int = 60        # Extend to 60 days for strong momentum


@dataclass
class PerformanceMetrics:
    """Performance tracking metrics"""
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_pnl: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    max_consecutive_losses: int = 0
    current_consecutive_losses: int = 0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0


class AdaptiveRiskManager:
    """
    Dynamic risk management that adapts to bot performance
    
    Features:
    - Performance-based parameter adjustment
    - Regime detection (bull/bear/sideways)
    - Drawdown protection
    - Win rate optimization
    """
    
    def __init__(self, initial_equity: float = 1000000.0, 
                 performance_file: str = "performance_history.json"):
        self.initial_equity = initial_equity
        self.performance_file = performance_file
        
        # Current parameters (will be adjusted dynamically)
        self.params = RiskParameters()
        
        # Performance tracking
        self.metrics = PerformanceMetrics()
        self.trade_history: List[Dict] = []
        
        # Parameter ranges for AGGRESSIVE SWING TRADING (updated safety bounds)
        self.min_stop_loss = 0.015      # 1.5% minimum
        self.max_stop_loss = 0.05       # 5% maximum (reduced from 8% for swing trading)
        self.min_profit_target = 0.10   # 10% minimum (increased from 3%)
        self.max_profit_target = 0.50   # 50% maximum (increased from 20%)
        self.min_time_stop = 30         # 30 days minimum (increased from 3)
        self.max_time_stop = 90         # 90 days maximum (increased from 20)
        
        # Adaptation settings
        self.adaptation_window = 20     # Look at last 20 trades
        self.adjustment_sensitivity = 0.1  # 10% max adjustment per update
        
        # Load historical performance
        self.load_performance_history()
        
        logging.info("🧠 Adaptive Risk Manager initialized")
        logging.info(f"   📊 Current params: {self.params.stop_loss_pct:.1%} stop, {self.params.profit_target_pct:.1%} target, {self.params.time_stop_days}d time")
    
    def record_trade(self, symbol: str, entry_price: float, exit_price: float, 
                    shares: int, entry_date: str, exit_date: str, exit_reason: str):
        """Record a completed trade for performance analysis"""
        
        pnl = (exit_price - entry_price) * shares
        pnl_pct = (exit_price - entry_price) / entry_price
        is_winner = pnl > 0
        
        trade = {
            'symbol': symbol,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'shares': shares,
            'pnl': pnl,
            'pnl_pct': pnl_pct,
            'entry_date': entry_date,
            'exit_date': exit_date,
            'exit_reason': exit_reason,
            'is_winner': is_winner,
            'timestamp': datetime.now().isoformat()
        }
        
        self.trade_history.append(trade)
        self.update_metrics(trade)
        self.save_performance_history()
        
        # Trigger adaptation every 5 trades
        if len(self.trade_history) % 5 == 0:
            self.adapt_parameters()
        
        logging.info(f"📝 Trade recorded: {symbol} {exit_reason} P&L: ${pnl:.2f} ({pnl_pct:.1%})")
    
    def update_metrics(self, trade: Dict):
        """Update performance metrics with new trade"""
        self.metrics.total_trades += 1
        self.metrics.total_pnl += trade['pnl']
        
        if trade['is_winner']:
            self.metrics.winning_trades += 1
            self.metrics.current_consecutive_losses = 0
            if self.metrics.winning_trades > 0:
                wins = [t['pnl'] for t in self.trade_history if t['is_winner']]
                self.metrics.avg_win = np.mean(wins)
        else:
            self.metrics.losing_trades += 1
            self.metrics.current_consecutive_losses += 1
            self.metrics.max_consecutive_losses = max(
                self.metrics.max_consecutive_losses, 
                self.metrics.current_consecutive_losses
            )
            if self.metrics.losing_trades > 0:
                losses = [t['pnl'] for t in self.trade_history if not t['is_winner']]
                self.metrics.avg_loss = np.mean(losses)
    
    def adapt_parameters(self):
        """Adapt risk parameters based on recent performance"""
        if len(self.trade_history) < 10:
            return  # Need minimum sample size
        
        recent_trades = self.trade_history[-self.adaptation_window:]
        
        # Calculate recent performance metrics
        win_rate = sum(1 for t in recent_trades if t['is_winner']) / len(recent_trades)
        avg_return = np.mean([t['pnl_pct'] for t in recent_trades])
        volatility = np.std([t['pnl_pct'] for t in recent_trades])
        
        # Get current parameters
        old_params = RiskParameters(
            self.params.stop_loss_pct,
            self.params.profit_target_pct,
            self.params.time_stop_days,
            self.params.confidence_threshold
        )
        
        # Adaptation logic
        self._adapt_stop_loss(win_rate, avg_return, volatility)
        self._adapt_profit_target(win_rate, avg_return)
        self._adapt_time_stop(avg_return, volatility)
        
        # Log changes if significant
        if (abs(old_params.stop_loss_pct - self.params.stop_loss_pct) > 0.002 or
            abs(old_params.profit_target_pct - self.params.profit_target_pct) > 0.005 or
            abs(old_params.time_stop_days - self.params.time_stop_days) > 1):
            
            logging.info("🔄 Risk parameters adapted:")
            logging.info(f"   Stop Loss: {old_params.stop_loss_pct:.1%} → {self.params.stop_loss_pct:.1%}")
            logging.info(f"   Profit Target: {old_params.profit_target_pct:.1%} → {self.params.profit_target_pct:.1%}")
            logging.info(f"   Time Stop: {old_params.time_stop_days}d → {self.params.time_stop_days}d")
            logging.info(f"   Trigger: Win Rate {win_rate:.1%}, Avg Return {avg_return:.1%}")
    
    def _adapt_stop_loss(self, win_rate: float, avg_return: float, volatility: float):
        """Adapt stop-loss based on performance"""
        # If win rate is low, tighten stops
        if win_rate < 0.4:
            adjustment = -0.005  # Tighten by 0.5%
        # If win rate is high but avg return is low, might be cutting winners short
        elif win_rate > 0.7 and avg_return < 0.02:
            adjustment = 0.005   # Loosen by 0.5%
        # If volatility is high, loosen stops
        elif volatility > 0.15:
            adjustment = 0.003   # Loosen by 0.3%
        else:
            adjustment = 0
        
        new_stop = self.params.stop_loss_pct + adjustment
        self.params.stop_loss_pct = max(self.min_stop_loss, min(self.max_stop_loss, new_stop))
    
    def _adapt_profit_target(self, win_rate: float, avg_return: float):
        """Adapt profit target based on performance"""
        # If avg return is high, can afford to let winners run longer
        if avg_return > 0.04 and win_rate > 0.5:
            adjustment = 0.01    # Increase target by 1%
        # If win rate is low, might need to take profits sooner
        elif win_rate < 0.4:
            adjustment = -0.01   # Decrease target by 1%
        else:
            adjustment = 0
        
        new_target = self.params.profit_target_pct + adjustment
        self.params.profit_target_pct = max(self.min_profit_target, min(self.max_profit_target, new_target))
    
    def _adapt_time_stop(self, avg_return: float, volatility: float):
        """Adapt time stop based on momentum persistence"""
        # If returns are consistently positive, extend holding period
        if avg_return > 0.03:
            adjustment = 2       # Add 2 days
        # If returns are poor, reduce holding period
        elif avg_return < -0.01:
            adjustment = -2      # Remove 2 days
        # If high volatility, reduce holding period
        elif volatility > 0.20:
            adjustment = -1      # Remove 1 day
        else:
            adjustment = 0
        
        new_time_stop = self.params.time_stop_days + adjustment
        self.params.time_stop_days = max(self.min_time_stop, min(self.max_time_stop, new_time_stop))
    
    def get_current_parameters(self) -> RiskParameters:
        """Get current risk parameters"""
        return self.params
    
    def get_performance_summary(self) -> Dict:
        """Get performance summary"""
        win_rate = self.metrics.winning_trades / max(1, self.metrics.total_trades)
        avg_trade = self.metrics.total_pnl / max(1, self.metrics.total_trades)
        
        return {
            'total_trades': self.metrics.total_trades,
            'win_rate': win_rate,
            'total_pnl': self.metrics.total_pnl,
            'avg_trade_pnl': avg_trade,
            'avg_win': self.metrics.avg_win,
            'avg_loss': self.metrics.avg_loss,
            'max_consecutive_losses': self.metrics.max_consecutive_losses,
            'current_params': asdict(self.params)
        }
    
    def save_performance_history(self):
        """Save performance history to file"""
        try:
            data = {
                'metrics': asdict(self.metrics),
                'parameters': asdict(self.params),
                'trade_history': self.trade_history[-100:],  # Keep last 100 trades
                'last_updated': datetime.now().isoformat()
            }
            
            with open(self.performance_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logging.warning(f"Could not save performance history: {e}")
    
    def load_performance_history(self):
        """Load performance history from file"""
        try:
            with open(self.performance_file, 'r') as f:
                data = json.load(f)
            
            # Restore metrics
            if 'metrics' in data:
                for key, value in data['metrics'].items():
                    if hasattr(self.metrics, key):
                        setattr(self.metrics, key, value)
            
            # Restore parameters
            if 'parameters' in data:
                for key, value in data['parameters'].items():
                    if hasattr(self.params, key):
                        setattr(self.params, key, value)
            
            # Restore recent trade history
            if 'trade_history' in data:
                self.trade_history = data['trade_history']
            
            logging.info(f"📊 Loaded {len(self.trade_history)} historical trades")
            
        except FileNotFoundError:
            logging.info("📊 No performance history found - starting fresh")
        except Exception as e:
            logging.warning(f"Could not load performance history: {e}")


# Example usage and testing
if __name__ == "__main__":
    # Test the adaptive risk manager
    adaptive_rm = AdaptiveRiskManager()
    
    # Simulate some trades
    import random
    for i in range(25):
        entry_price = 100 + random.uniform(-10, 10)
        exit_price = entry_price * (1 + random.uniform(-0.08, 0.12))
        adaptive_rm.record_trade(
            symbol=f"TEST{i%5}",
            entry_price=entry_price,
            exit_price=exit_price,
            shares=100,
            entry_date="2025-09-01",
            exit_date="2025-09-03", 
            exit_reason="test"
        )
    
    print("Performance Summary:", adaptive_rm.get_performance_summary())

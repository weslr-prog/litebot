"""
AI-powered dynamic stop loss and fast-exit management
Extracted from traders/short_cycle_trader.py
"""

import logging
import pandas as pd
from typing import Tuple

from bot_v2.config.trading_config import ShortCycleConfig
from bot_v2.models.signals import AISignal
from bot_v2.models.positions import ShortCyclePosition, PositionStatus


class AIStopLossManager:
    """AI-powered dynamic stop loss and fast-exit management"""
    
    def __init__(self, config: ShortCycleConfig):
        self.config = config
        self.logger = logging.getLogger(__name__ + ".AIStopLossManager")
        
        # Issue 4.1: ATR-based dynamic stops with floor/ceiling (Jan 13, 2026)
        # These replace fixed percentages with volatility-adaptive stops
        self.min_stop_percent = 0.01  # 1% floor (too tight = noise stops)
        self.max_stop_percent = 0.04  # 4% ceiling (too wide = big losses)
        self.atr_multiplier = 1.5  # 1.5x ATR = covers ~1 standard deviation
        
        # Fast exit for small position protection
        self.fast_exit_threshold = 0.008  # 0.8% fast exit threshold
    
    def calculate_optimal_stop(self, signal: AISignal, market_data: pd.DataFrame) -> Tuple[float, float]:
        """
        Issue 4.1: Calculate ATR-based dynamic stop price.
        
        Volatile stocks get wider stops (won't get stopped out by noise).
        Stable stocks get tighter stops (less loss when wrong).
        
        Returns:
            (stop_price, stop_percentage)
        """
        try:
            entry_price = signal.entry_price
            if entry_price is None or market_data.empty or len(market_data) < 14:
                # Fallback to strategy-specific stop
                strategy = signal.features_used.get('strategy', 'default') if hasattr(signal, 'features_used') else 'default'
                stop_pct = self._get_strategy_default_stop(strategy)
                stop_price = entry_price * (1 - stop_pct)
                return stop_price, stop_pct
            
            # Normalize column names
            data = market_data.copy()
            data.columns = [col.lower() for col in data.columns]
            
            # Calculate ATR (Average True Range) - 14-day standard
            high_low = data['high'] - data['low']
            high_close = abs(data['high'] - data['close'].shift(1))
            low_close = abs(data['low'] - data['close'].shift(1))
            true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            atr_14 = true_range.tail(14).mean()
            
            # Convert ATR to percentage of current price
            atr_pct = atr_14 / entry_price
            
            # Stop distance = 1.5x ATR, capped between floor and ceiling
            raw_stop_pct = atr_pct * self.atr_multiplier
            stop_pct = max(self.min_stop_percent, min(raw_stop_pct, self.max_stop_percent))
            
            # Calculate actual stop price
            stop_price = entry_price * (1 - stop_pct)
            
            # Log the dynamic calculation
            self.logger.debug(
                f"{signal.symbol}: ATR={atr_pct:.2%}, raw={raw_stop_pct:.2%}, "
                f"final={stop_pct:.2%} (floor={self.min_stop_percent:.0%}, ceil={self.max_stop_percent:.0%})"
            )
            
            return stop_price, stop_pct
            
        except Exception as e:
            self.logger.error(f"Error calculating stop for {signal.symbol}: {e}")
            # Fallback to config default
            stop_pct = self.config.stop_loss_pct
            stop_price = signal.entry_price * (1 - stop_pct)
            return stop_price, stop_pct
    
    def _get_strategy_default_stop(self, strategy: str) -> float:
        """Get default stop percentage based on strategy"""
        if strategy == 'gap_and_go':
            return self.config.gap_and_go_stop_loss_pct  # 2%
        elif strategy == 'fade_short':
            return self.config.fade_short_stop_loss_pct  # 1.5%
        else:
            return self.config.stop_loss_pct  # Default 2%
    
    def calculate_dynamic_profit_target(self, signal: AISignal, market_data: pd.DataFrame) -> Tuple[float, float]:
        """
        Issue 4.2: Calculate ATR-based dynamic profit target.
        
        Volatile stocks (high ATR) get higher targets - they can move more.
        Stable stocks (low ATR) get lower targets - realistic expectations.
        
        Returns:
            (target_price, target_percentage)
        """
        try:
            entry_price = signal.entry_price
            strategy = signal.features_used.get('strategy', 'default') if hasattr(signal, 'features_used') else 'default'
            
            if entry_price is None or market_data.empty or len(market_data) < 14:
                # Fallback to strategy-specific target
                target_pct = self._get_strategy_default_target(strategy)
                target_price = entry_price * (1 + target_pct)
                return target_price, target_pct
            
            # Normalize column names
            data = market_data.copy()
            data.columns = [col.lower() for col in data.columns]
            
            # Calculate ATR (Average True Range) - 14-day standard
            high_low = data['high'] - data['low']
            high_close = abs(data['high'] - data['close'].shift(1))
            low_close = abs(data['low'] - data['close'].shift(1))
            true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            atr_14 = true_range.tail(14).mean()
            
            # Convert ATR to percentage of current price
            atr_pct = atr_14 / entry_price
            
            # Profit target = 1.5x ATR, capped between 1.5% and 8%
            # Higher multiplier for targets (we want to capture moves, not just breakeven)
            min_target = 0.015  # 1.5% floor
            max_target = 0.08   # 8% ceiling
            
            raw_target_pct = atr_pct * 1.5
            target_pct = max(min_target, min(raw_target_pct, max_target))
            
            # Calculate actual target price
            target_price = entry_price * (1 + target_pct)
            
            # Log the dynamic calculation
            self.logger.debug(
                f"{signal.symbol}: ATR={atr_pct:.2%}, raw_target={raw_target_pct:.2%}, "
                f"final={target_pct:.2%} (floor={min_target:.1%}, ceil={max_target:.0%})"
            )
            
            return target_price, target_pct
            
        except Exception as e:
            self.logger.error(f"Error calculating profit target for {signal.symbol}: {e}")
            # Fallback to config default
            strategy = signal.features_used.get('strategy', 'default') if hasattr(signal, 'features_used') else 'default'
            target_pct = self._get_strategy_default_target(strategy)
            target_price = signal.entry_price * (1 + target_pct)
            return target_price, target_pct
    
    def _get_strategy_default_target(self, strategy: str) -> float:
        """Get default profit target percentage based on strategy"""
        if strategy == 'gap_and_go':
            return self.config.gap_and_go_profit_target_pct  # 3%
        elif strategy == 'fade_short':
            return self.config.fade_short_profit_target_pct  # 2%
        else:
            return self.config.profit_target_pct  # Default 2%
    
    def should_fast_exit(self, position: ShortCyclePosition, current_price: float) -> bool:
        """Check if position should fast-exit for capital recycling"""
        if position.status != PositionStatus.ENTERED:
            return False
        
        # Handle None values gracefully
        if current_price is None or position.entry_price is None:
            return False
        
        unrealized_pnl_pct = (current_price - position.entry_price) / position.entry_price
        unrealized_pnl_dollars = (current_price - position.entry_price) * position.position_size_shares
        
        # CRITICAL: Check max loss limit first (prevents $739 losses)
        if abs(unrealized_pnl_dollars) >= self.config.max_loss_per_trade_dollars:
            self.logger.warning(f"MAX LOSS LIMIT HIT: ${abs(unrealized_pnl_dollars):.2f} >= ${self.config.max_loss_per_trade_dollars}")
            return True
        
        return unrealized_pnl_pct <= -self.fast_exit_threshold

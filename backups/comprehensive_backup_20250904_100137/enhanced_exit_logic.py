#!/usr/bin/env python3
"""
Enhanced Exit Logic Manager
Implements comprehensive exit strategy with ATR-based stops, scaled profit targets, and refined time stops
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import yfinance as yf


@dataclass
class ExitParameters:
    """Complete exit logic parameters"""
    # Stop-Loss Options
    use_atr_stops: bool = True                # Use ATR-based stops vs fixed percentage
    atr_stop_multiplier: float = 2.0          # 2× ATR below entry
    fixed_stop_pct: float = 0.025             # 2.5% fixed cap as fallback
    
    # Profit Targets with Scaling
    initial_profit_target: float = 0.15       # 15% minimum profit target
    atr_profit_multiplier: float = 4.0        # 4× ATR above entry for initial target
    scale_out_levels: List[float] = None       # Scale out at multiple levels
    
    # Time Stops
    base_time_stop_days: int = 12              # 10-15 trading days (12 compromise)
    max_time_stop_days: int = 15               # Maximum time before forced exit
    profitable_extension_days: int = 5        # Extra days if profitable
    
    # Trailing Stops for Extended Winners
    trailing_stop_pct: float = 0.08           # 8% trailing stop
    trailing_activation_gain: float = 0.10    # Start trailing at 10% gain
    extended_hold_days: int = 45               # Extended timeframe for strong winners
    momentum_extension_threshold: float = 0.20 # 20% gain for extended holding
    
    def __post_init__(self):
        if self.scale_out_levels is None:
            self.scale_out_levels = [0.15, 0.25, 0.35]  # Scale out at 15%, 25%, 35%


@dataclass
class PositionExit:
    """Track exit conditions for a position"""
    symbol: str
    entry_price: float
    entry_date: datetime
    shares: int
    
    # ATR-based levels
    atr_value: float = 0.0
    atr_stop_price: float = 0.0
    atr_profit_target: float = 0.0
    
    # Fixed percentage levels
    fixed_stop_price: float = 0.0
    fixed_profit_target: float = 0.0
    
    # Trailing stop tracking
    peak_price: float = 0.0
    trailing_stop_price: float = 0.0
    trailing_active: bool = False
    
    # Scaling tracking
    remaining_shares: int = 0
    scale_out_completed: List[float] = None
    
    # Time tracking
    days_held: int = 0
    trading_days_held: int = 0
    time_stop_date: datetime = None
    
    def __post_init__(self):
        if self.scale_out_completed is None:
            self.scale_out_completed = []
        if self.remaining_shares == 0:
            self.remaining_shares = self.shares
        if self.peak_price == 0.0:
            self.peak_price = self.entry_price


class EnhancedExitLogicManager:
    """
    Advanced exit logic manager implementing:
    1. ATR-based stop-losses (2× ATR below entry)
    2. ATR-based profit targets (4× ATR above entry) 
    3. Scaled profit taking (15%, 25%, 35% levels)
    4. Refined time stops (10-15 trading days)
    5. Trailing stops for extended winners (45-60 days)
    """
    
    def __init__(self, parameters: ExitParameters = None):
        self.params = parameters or ExitParameters()
        self.positions: Dict[str, PositionExit] = {}
        self.logger = logging.getLogger(__name__)
        
        self.logger.info("🎯 Enhanced Exit Logic Manager initialized")
        self.logger.info(f"   🛑 Stop Logic: {'ATR-based' if self.params.use_atr_stops else 'Fixed %'}")
        self.logger.info(f"   📈 Profit Targets: {self.params.scale_out_levels}")
        self.logger.info(f"   ⏰ Time Stops: {self.params.base_time_stop_days}-{self.params.max_time_stop_days} days")
        self.logger.info(f"   🔄 Trailing: {self.params.trailing_stop_pct:.0%} at {self.params.trailing_activation_gain:.0%} gain")
    
    def add_position(self, symbol: str, entry_price: float, shares: int, 
                    entry_date: datetime = None) -> PositionExit:
        """Add new position with complete exit logic setup"""
        
        if entry_date is None:
            entry_date = datetime.now()
        
        # Calculate ATR for the symbol
        atr_value = self._calculate_atr(symbol)
        
        # Create position exit tracker
        position = PositionExit(
            symbol=symbol,
            entry_price=entry_price,
            entry_date=entry_date,
            shares=shares,
            atr_value=atr_value
        )
        
        # Calculate exit levels
        self._calculate_exit_levels(position)
        
        self.positions[symbol] = position
        
        self.logger.info(f"🎯 Position added: {symbol} @ ${entry_price:.2f}")
        self.logger.info(f"   🛑 ATR Stop: ${position.atr_stop_price:.2f} | Fixed Stop: ${position.fixed_stop_price:.2f}")
        self.logger.info(f"   📈 ATR Target: ${position.atr_profit_target:.2f} | Scale Levels: {self.params.scale_out_levels}")
        self.logger.info(f"   ⏰ Time Stop: {self.params.base_time_stop_days} days | ATR: {atr_value:.3f}")
        
        return position
    
    def update_position(self, symbol: str, current_price: float) -> Dict[str, any]:
        """
        Update position and check all exit conditions
        
        Returns:
            Dict with exit_signal, exit_type, reason, shares_to_exit, etc.
        """
        if symbol not in self.positions:
            return {'exit_signal': False, 'reason': 'Position not found'}
        
        position = self.positions[symbol]
        
        # Update position metrics
        self._update_position_metrics(position, current_price)
        
        # Check all exit conditions in priority order
        exit_result = self._check_all_exit_conditions(position, current_price)
        
        # Log position status
        if not exit_result['exit_signal']:
            self._log_position_status(position, current_price)
        
        return exit_result
    
    def _calculate_atr(self, symbol: str, period: int = 14) -> float:
        """Calculate Average True Range for ATR-based stops"""
        try:
            # Get recent price data
            ticker = yf.Ticker(symbol)
            data = ticker.history(period="1mo", interval="1d")
            
            if len(data) < period:
                self.logger.warning(f"⚠️ Insufficient data for ATR calculation: {symbol}")
                return 0.02  # Default 2% ATR fallback
            
            # Calculate True Range
            high_low = data['High'] - data['Low']
            high_close_prev = abs(data['High'] - data['Close'].shift(1))
            low_close_prev = abs(data['Low'] - data['Close'].shift(1))
            
            true_range = pd.concat([high_low, high_close_prev, low_close_prev], axis=1).max(axis=1)
            
            # Calculate ATR as percentage of closing price
            atr_absolute = true_range.rolling(window=period).mean().iloc[-1]
            current_close = data['Close'].iloc[-1]
            atr_percentage = atr_absolute / current_close
            
            return atr_percentage
            
        except Exception as e:
            self.logger.error(f"❌ Error calculating ATR for {symbol}: {e}")
            return 0.02  # Default 2% fallback
    
    def _calculate_exit_levels(self, position: PositionExit):
        """Calculate all exit levels for a position"""
        
        # ATR-based levels
        if self.params.use_atr_stops and position.atr_value > 0:
            position.atr_stop_price = position.entry_price * (1 - self.params.atr_stop_multiplier * position.atr_value)
            position.atr_profit_target = position.entry_price * (1 + self.params.atr_profit_multiplier * position.atr_value)
        else:
            position.atr_stop_price = 0.0
            position.atr_profit_target = 0.0
        
        # Fixed percentage levels (always calculated as backup)
        position.fixed_stop_price = position.entry_price * (1 - self.params.fixed_stop_pct)
        position.fixed_profit_target = position.entry_price * (1 + self.params.initial_profit_target)
        
        # Initial trailing stop (starts at stop-loss level)
        position.trailing_stop_price = max(position.atr_stop_price, position.fixed_stop_price)
        
        # Time stop date
        position.time_stop_date = position.entry_date + timedelta(days=self.params.base_time_stop_days)
    
    def _update_position_metrics(self, position: PositionExit, current_price: float):
        """Update position metrics and trailing stops"""
        
        # Update time metrics
        position.days_held = (datetime.now() - position.entry_date).days
        position.trading_days_held = int(position.days_held * (5/7))  # Approximate trading days
        
        # Update peak price and trailing stop
        if current_price > position.peak_price:
            position.peak_price = current_price
            
            # Activate trailing stop if gain threshold reached
            current_gain = (current_price / position.entry_price) - 1
            if current_gain >= self.params.trailing_activation_gain:
                position.trailing_active = True
                
                # Update trailing stop from new peak
                new_trailing_stop = position.peak_price * (1 - self.params.trailing_stop_pct)
                position.trailing_stop_price = max(position.trailing_stop_price, new_trailing_stop)
    
    def _check_all_exit_conditions(self, position: PositionExit, current_price: float) -> Dict[str, any]:
        """Check all exit conditions in priority order"""
        
        current_gain = (current_price / position.entry_price) - 1
        
        # 1. HIGHEST PRIORITY: Stop-Loss (ATR or Fixed)
        active_stop_price = position.atr_stop_price if (self.params.use_atr_stops and position.atr_stop_price > 0) else position.fixed_stop_price
        
        if current_price <= active_stop_price:
            stop_type = "ATR" if self.params.use_atr_stops and position.atr_stop_price > 0 else "FIXED"
            return {
                'exit_signal': True,
                'exit_type': 'stop_loss',
                'reason': f'{stop_type}-STOP (${current_price:.2f} <= ${active_stop_price:.2f})',
                'shares_to_exit': position.remaining_shares,
                'priority': 1
            }
        
        # 2. Trailing stop (only if active and position is profitable)
        if position.trailing_active and current_price <= position.trailing_stop_price:
            return {
                'exit_signal': True,
                'exit_type': 'trailing_stop',
                'reason': f'TRAILING-STOP (${current_price:.2f} <= ${position.trailing_stop_price:.2f}, peak: ${position.peak_price:.2f})',
                'shares_to_exit': position.remaining_shares,
                'priority': 2
            }
        
        # 3. Scaled profit taking
        for level in self.params.scale_out_levels:
            if level not in position.scale_out_completed and current_gain >= level:
                shares_to_exit = int(position.shares * 0.33)  # Exit 1/3 at each level
                if shares_to_exit > 0 and shares_to_exit <= position.remaining_shares:
                    return {
                        'exit_signal': True,
                        'exit_type': 'scale_out',
                        'reason': f'SCALE-OUT at {level:.0%} gain (${current_price:.2f})',
                        'shares_to_exit': shares_to_exit,
                        'scale_level': level,
                        'priority': 3
                    }
        
        # 4. Time stops (refined logic)
        time_stop_triggered = self._check_time_stops(position, current_gain)
        if time_stop_triggered:
            return {
                'exit_signal': True,
                'exit_type': 'time_stop',
                'reason': f'TIME-STOP ({position.trading_days_held} trading days, gain: {current_gain:+.1%})',
                'shares_to_exit': position.remaining_shares,
                'priority': 4
            }
        
        # 5. Extended momentum breakdown (for long-term winners)
        if (position.trading_days_held >= self.params.extended_hold_days and 
            current_gain > 0.15 and  # At least 15% gain
            self._detect_momentum_breakdown(position, current_price)):
            return {
                'exit_signal': True,
                'exit_type': 'momentum_breakdown',
                'reason': f'MOMENTUM-BREAKDOWN after {position.trading_days_held} days (+{current_gain:.1%})',
                'shares_to_exit': position.remaining_shares,
                'priority': 5
            }
        
        return {'exit_signal': False, 'reason': 'Holding position'}
    
    def _check_time_stops(self, position: PositionExit, current_gain: float) -> bool:
        """Refined time stop logic"""
        
        # Base time stop
        if position.trading_days_held >= self.params.base_time_stop_days:
            
            # Extend time for profitable positions
            if current_gain > 0.05:  # 5%+ gain gets extension
                extended_days = self.params.base_time_stop_days + self.params.profitable_extension_days
                if position.trading_days_held < extended_days:
                    return False  # Still within extended time
            
            # Extend further for strong momentum
            if current_gain >= self.params.momentum_extension_threshold:
                if position.trading_days_held < self.params.extended_hold_days:
                    return False  # Strong momentum gets long extension
            
            # Maximum time stop override
            if position.trading_days_held >= self.params.max_time_stop_days:
                return True
            
            # Exit unprofitable positions at base time stop
            if current_gain < 0.03:  # Less than 3% gain
                return True
        
        return False
    
    def _detect_momentum_breakdown(self, position: PositionExit, current_price: float) -> bool:
        """Detect momentum breakdown for extended positions"""
        # Price declined more than 8% from peak
        peak_decline = (position.peak_price - current_price) / position.peak_price
        return peak_decline > 0.08
    
    def _log_position_status(self, position: PositionExit, current_price: float):
        """Log detailed position status"""
        current_gain = (current_price / position.entry_price) - 1
        
        # Determine active stop
        active_stop = position.trailing_stop_price if position.trailing_active else (
            position.atr_stop_price if self.params.use_atr_stops and position.atr_stop_price > 0 
            else position.fixed_stop_price
        )
        
        trailing_status = "ACTIVE" if position.trailing_active else "INACTIVE"
        
        self.logger.info(
            f"📊 {position.symbol}: ${current_price:.2f} "
            f"({current_gain:+.1%}, {position.trading_days_held}d) | "
            f"Stop: ${active_stop:.2f} | "
            f"Peak: ${position.peak_price:.2f} | "
            f"Trail: {trailing_status} | "
            f"Shares: {position.remaining_shares}/{position.shares}"
        )
    
    def execute_partial_exit(self, symbol: str, shares_exited: int, scale_level: float = None):
        """Record partial exit (for scaling out)"""
        if symbol in self.positions:
            position = self.positions[symbol]
            position.remaining_shares = max(0, position.remaining_shares - shares_exited)
            
            if scale_level:
                position.scale_out_completed.append(scale_level)
                self.logger.info(f"✅ {symbol}: Scaled out {shares_exited} shares at {scale_level:.0%} level")
    
    def remove_position(self, symbol: str) -> Optional[PositionExit]:
        """Remove position after complete exit"""
        return self.positions.pop(symbol, None)
    
    def get_exit_summary(self) -> Dict[str, any]:
        """Get summary of all position exit statuses"""
        summary = {
            'total_positions': len(self.positions),
            'trailing_active': sum(1 for p in self.positions.values() if p.trailing_active),
            'scaled_positions': sum(1 for p in self.positions.values() if p.scale_out_completed),
            'extended_holds': sum(1 for p in self.positions.values() if p.trading_days_held >= self.params.base_time_stop_days)
        }
        
        return summary


# Example usage and testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Test the enhanced exit logic
    exit_manager = EnhancedExitLogicManager()
    
    # Add test position
    position = exit_manager.add_position("AAPL", 150.0, 100)
    
    # Simulate price movements
    test_prices = [148.0, 152.0, 165.0, 172.5, 168.0]
    
    for price in test_prices:
        result = exit_manager.update_position("AAPL", price)
        if result['exit_signal']:
            print(f"EXIT SIGNAL: {result}")
            break
    
    print("✅ Enhanced Exit Logic Manager test complete")

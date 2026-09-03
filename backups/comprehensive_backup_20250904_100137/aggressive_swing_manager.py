#!/usr/bin/env python3
"""
Aggressive Swing Trading Manager
Implements trailing stops and let-winners-run logic for high ROI swing trading
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import numpy as np
from dataclasses import dataclass


@dataclass
class SwingTradePosition:
    """Track swing trade position with trailing stops"""
    symbol: str
    entry_price: float
    entry_date: datetime
    shares: int
    stop_loss_price: float
    
    # Trailing stop tracking
    peak_price: float = 0.0
    trailing_stop_price: float = 0.0
    profit_target_hit: bool = False
    breakout_trade: bool = False
    
    # Performance tracking
    current_gain_pct: float = 0.0
    days_held: int = 0
    momentum_score: float = 0.0


class AggressiveSwingManager:
    """
    Manages aggressive swing trading positions with:
    - Trailing stops that let winners run
    - Dynamic profit targets (15% minimum, 25% for breakouts)
    - Extended time horizons (45-60 days)
    - Momentum-based position extensions
    """
    
    def __init__(self):
        self.positions: Dict[str, SwingTradePosition] = {}
        self.logger = logging.getLogger(__name__)
        
        # Aggressive swing trading parameters
        self.initial_profit_target = 0.15      # 15% minimum profit target
        self.trailing_stop_pct = 0.08          # 8% trailing stop from peak
        self.breakout_profit_target = 0.25     # 25% for strong breakouts
        self.max_hold_days = 45                # 45 days base, 60 for strong momentum
        self.momentum_extension_threshold = 0.20  # 20% gain triggers extension
        
        self.logger.info("🚀 Aggressive Swing Trading Manager initialized")
        self.logger.info(f"   Initial Target: {self.initial_profit_target:.0%}")
        self.logger.info(f"   Trailing Stop: {self.trailing_stop_pct:.0%}")
        self.logger.info(f"   Breakout Target: {self.breakout_profit_target:.0%}")
    
    def add_position(self, symbol: str, entry_price: float, shares: int, 
                    stop_loss_price: float, momentum_score: float = 0.0,
                    is_breakout: bool = False) -> SwingTradePosition:
        """Add new swing trading position with aggressive parameters"""
        
        position = SwingTradePosition(
            symbol=symbol,
            entry_price=entry_price,
            entry_date=datetime.now(),
            shares=shares,
            stop_loss_price=stop_loss_price,
            peak_price=entry_price,
            trailing_stop_price=stop_loss_price,
            breakout_trade=is_breakout,
            momentum_score=momentum_score
        )
        
        self.positions[symbol] = position
        
        target_pct = self.breakout_profit_target if is_breakout else self.initial_profit_target
        self.logger.info(f"🎯 New swing position: {symbol} @ ${entry_price:.2f}")
        self.logger.info(f"   Target: {target_pct:.0%} | Stop: ${stop_loss_price:.2f}")
        self.logger.info(f"   Breakout: {is_breakout} | Momentum: {momentum_score:.2f}")
        
        return position
    
    def update_position(self, symbol: str, current_price: float) -> Dict[str, any]:
        """
        Update position with trailing stop logic and swing trade management
        
        Returns:
            Dict with exit_signal, reason, trailing_stop_price, profit_target_hit
        """
        if symbol not in self.positions:
            return {'exit_signal': False, 'reason': 'Position not found'}
        
        position = self.positions[symbol]
        
        # Update basic metrics
        position.current_gain_pct = (current_price / position.entry_price) - 1
        position.days_held = (datetime.now() - position.entry_date).days
        
        # Update peak price for trailing stop
        if current_price > position.peak_price:
            position.peak_price = current_price
            
            # Update trailing stop from new peak
            position.trailing_stop_price = max(
                position.stop_loss_price,  # Never below original stop
                position.peak_price * (1 - self.trailing_stop_pct)
            )
        
        # Determine profit target based on position type
        profit_target = (self.breakout_profit_target if position.breakout_trade 
                        else self.initial_profit_target)
        
        # Check exit conditions
        exit_result = self._check_exit_conditions(position, current_price, profit_target)
        
        # Log position status
        self._log_position_status(position, current_price, profit_target)
        
        return exit_result
    
    def _check_exit_conditions(self, position: SwingTradePosition, 
                             current_price: float, profit_target: float) -> Dict[str, any]:
        """Check all exit conditions for aggressive swing trading"""
        
        # 1. Stop-loss or trailing stop hit
        if current_price <= position.trailing_stop_price:
            if position.current_gain_pct > 0:
                return {
                    'exit_signal': True,
                    'reason': f'TRAILING-STOP (${current_price:.2f} <= ${position.trailing_stop_price:.2f})',
                    'exit_type': 'trailing_stop',
                    'profit_protected': True
                }
            else:
                return {
                    'exit_signal': True,
                    'reason': f'STOP-LOSS (${current_price:.2f} <= ${position.stop_loss_price:.2f})',
                    'exit_type': 'stop_loss',
                    'profit_protected': False
                }
        
        # 2. Initial profit target hit - switch to trailing stops
        if not position.profit_target_hit and position.current_gain_pct >= profit_target:
            position.profit_target_hit = True
            self.logger.info(f"🎯 {position.symbol}: Initial target {profit_target:.0%} hit! Switching to trailing stops")
            # Don't exit, let it run with trailing stops
        
        # 3. Extended time stop (only if not profitable)
        max_days = 60 if position.current_gain_pct > self.momentum_extension_threshold else self.max_hold_days
        
        if position.days_held >= max_days and position.current_gain_pct < 0.05:  # Less than 5% gain
            return {
                'exit_signal': True,
                'reason': f'TIME-STOP ({position.days_held} days, gain: {position.current_gain_pct:.1%})',
                'exit_type': 'time_stop',
                'profit_protected': False
            }
        
        # 4. Momentum breakdown (only for profitable positions)
        if (position.profit_target_hit and 
            position.current_gain_pct > 0.10 and  # At least 10% gain
            self._detect_momentum_breakdown(position, current_price)):
            return {
                'exit_signal': True,
                'reason': 'MOMENTUM-BREAKDOWN (taking profits on weakness)',
                'exit_type': 'momentum_breakdown',
                'profit_protected': True
            }
        
        return {'exit_signal': False, 'reason': 'Holding position'}
    
    def _detect_momentum_breakdown(self, position: SwingTradePosition, 
                                 current_price: float) -> bool:
        """Detect momentum breakdown for profitable positions"""
        # Simple momentum breakdown: price dropped more than 5% from peak
        peak_decline = (position.peak_price - current_price) / position.peak_price
        return peak_decline > 0.05  # 5% decline from peak
    
    def _log_position_status(self, position: SwingTradePosition, 
                           current_price: float, profit_target: float):
        """Log detailed position status for monitoring"""
        target_status = "HIT ✅" if position.profit_target_hit else f"{profit_target:.0%}"
        
        self.logger.info(
            f"📊 {position.symbol}: ${current_price:.2f} "
            f"(+{position.current_gain_pct:+.1%}, {position.days_held}d) "
            f"Peak: ${position.peak_price:.2f} | "
            f"Trail: ${position.trailing_stop_price:.2f} | "
            f"Target: {target_status}"
        )
    
    def remove_position(self, symbol: str) -> Optional[SwingTradePosition]:
        """Remove position after exit"""
        return self.positions.pop(symbol, None)
    
    def get_position_summary(self) -> Dict[str, any]:
        """Get summary of all swing trading positions"""
        if not self.positions:
            return {'total_positions': 0, 'avg_gain': 0, 'positions_at_target': 0}
        
        total_gain = sum(pos.current_gain_pct for pos in self.positions.values())
        avg_gain = total_gain / len(self.positions)
        targets_hit = sum(1 for pos in self.positions.values() if pos.profit_target_hit)
        
        return {
            'total_positions': len(self.positions),
            'avg_gain_pct': avg_gain,
            'positions_at_target': targets_hit,
            'avg_days_held': np.mean([pos.days_held for pos in self.positions.values()]),
            'max_gain_pct': max(pos.current_gain_pct for pos in self.positions.values()),
            'min_gain_pct': min(pos.current_gain_pct for pos in self.positions.values())
        }
    
    def suggest_position_adjustments(self) -> List[Dict[str, any]]:
        """Suggest position adjustments for aggressive swing trading"""
        suggestions = []
        
        for symbol, position in self.positions.items():
            # Suggest adding to winners
            if (position.current_gain_pct > 0.08 and  # 8% gain
                not position.profit_target_hit and
                position.days_held < 30):
                suggestions.append({
                    'symbol': symbol,
                    'action': 'consider_adding',
                    'reason': f'Strong momentum (+{position.current_gain_pct:.1%}) under 30 days',
                    'current_gain': position.current_gain_pct
                })
            
            # Suggest reviewing laggards
            elif (position.current_gain_pct < -0.01 and  # Down 1%
                  position.days_held > 14):
                suggestions.append({
                    'symbol': symbol,
                    'action': 'review_position',
                    'reason': f'Lagging after {position.days_held} days ({position.current_gain_pct:+.1%})',
                    'current_gain': position.current_gain_pct
                })
        
        return suggestions


def demo_aggressive_swing_manager():
    """Demonstrate aggressive swing trading manager"""
    manager = AggressiveSwingManager()
    
    # Add sample positions
    print("\n=== ADDING SWING POSITIONS ===")
    manager.add_position("TSLA", 250.0, 40, 237.5, momentum_score=0.25, is_breakout=True)
    manager.add_position("NVDA", 450.0, 22, 427.5, momentum_score=0.18, is_breakout=False)
    manager.add_position("AMZN", 180.0, 55, 171.0, momentum_score=0.12, is_breakout=False)
    
    # Simulate price movements
    print("\n=== SIMULATING PRICE MOVEMENTS ===")
    
    # Day 5: Mixed performance
    print("\n--- Day 5 ---")
    print(manager.update_position("TSLA", 265.0))  # +6% gain
    print(manager.update_position("NVDA", 460.0))  # +2.2% gain
    print(manager.update_position("AMZN", 175.0))  # -2.8% loss
    
    # Day 15: TSLA breaking out
    print("\n--- Day 15 ---")
    print(manager.update_position("TSLA", 290.0))  # +16% gain - target hit!
    print(manager.update_position("NVDA", 470.0))  # +4.4% gain
    print(manager.update_position("AMZN", 185.0))  # +2.8% gain
    
    # Day 25: Peak and pullback
    print("\n--- Day 25 ---")
    print(manager.update_position("TSLA", 310.0))  # +24% gain - new peak
    print(manager.update_position("NVDA", 485.0))  # +7.8% gain
    print(manager.update_position("AMZN", 190.0))  # +5.6% gain
    
    # Day 30: Pullback triggers trailing stop
    print("\n--- Day 30 ---")
    print(manager.update_position("TSLA", 285.0))  # Still up 14% but down from peak
    print(manager.update_position("NVDA", 495.0))  # +10% gain
    print(manager.update_position("AMZN", 188.0))  # +4.4% gain
    
    # Summary
    print("\n=== POSITION SUMMARY ===")
    summary = manager.get_position_summary()
    for key, value in summary.items():
        print(f"{key}: {value}")
    
    # Suggestions
    print("\n=== POSITION SUGGESTIONS ===")
    suggestions = manager.suggest_position_adjustments()
    for suggestion in suggestions:
        print(f"({suggestion['symbol']}) {suggestion['action']}: {suggestion['reason']}")


if __name__ == "__main__":
    demo_aggressive_swing_manager()

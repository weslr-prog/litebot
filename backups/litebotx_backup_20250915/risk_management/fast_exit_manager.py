"""
Fast Exit Manager - Weekly ROI Focus with Quick Profit Recycling
Optimized for 3-7 day cycles and maximum weekly ROI compounding
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
import logging
from typing import Dict, List, Tuple, Optional, Union
from dataclasses import dataclass, asdict
from enum import Enum
import json

logger = logging.getLogger(__name__)

class ExitReason(Enum):
    """Enumeration of exit reasons for tracking"""
    PROFIT_TARGET = "profit_target"
    TRAILING_STOP = "trailing_stop"
    TIME_STOP = "time_stop" 
    STOP_LOSS = "stop_loss"
    MOMENTUM_BREAKDOWN = "momentum_breakdown"
    VOLUME_EXHAUSTION = "volume_exhaustion"
    FAST_PROFIT = "fast_profit"
    REGIME_CHANGE = "regime_change"
    RISK_MANAGEMENT = "risk_management"

@dataclass
class FastExitConfig:
    """Configuration for fast exit management"""
    
    # Quick profit targets (for fast recycling)
    quick_profit_targets: Dict[str, float] = None  # Strategy-specific targets
    fast_exit_threshold: float = 0.03  # 3% for immediate profit taking
    
    # Time-based exits
    max_hold_hours: Dict[str, int] = None  # Strategy-specific max hold times
    intraday_exit_time: str = "15:45"  # EST exit time for day trades
    
    # Trailing stop configuration
    trailing_stop_activation: float = 0.02  # Activate trailing stop at 2% profit
    trailing_stop_distance: Dict[str, float] = None  # Strategy-specific distances
    
    # Risk management exits
    position_heat_threshold: float = -0.015  # Exit at 1.5% loss
    portfolio_heat_threshold: float = -0.03  # Exit all at 3% portfolio loss
    
    # Volume and momentum exits
    volume_exhaustion_threshold: float = 0.3  # 30% of avg volume
    momentum_breakdown_threshold: float = -0.01  # 1% momentum reversal
    
    # Capital recycling
    enable_fast_recycling: bool = True
    recycling_cooldown_minutes: int = 30  # Wait before redeploying capital
    max_recycling_per_day: int = 3  # Max times to recycle same capital
    
    def __post_init__(self):
        """Initialize default values for strategy-specific configs"""
        if self.quick_profit_targets is None:
            self.quick_profit_targets = {
                'scalping': 0.015,      # 1.5% for scalps
                'momentum': 0.05,       # 5% for momentum  
                'mean_reversion': 0.03, # 3% for mean reversion
                'breakout': 0.08,       # 8% for breakouts
                'swing': 0.15           # 15% for swing trades
            }
        
        if self.max_hold_hours is None:
            self.max_hold_hours = {
                'scalping': 4,          # 4 hours max
                'momentum': 48,         # 2 days max
                'mean_reversion': 72,   # 3 days max
                'breakout': 120,        # 5 days max
                'swing': 1440           # 60 days max
            }
        
        if self.trailing_stop_distance is None:
            self.trailing_stop_distance = {
                'scalping': 0.005,      # 0.5% trailing stop
                'momentum': 0.02,       # 2% trailing stop
                'mean_reversion': 0.015, # 1.5% trailing stop
                'breakout': 0.03,       # 3% trailing stop
                'swing': 0.08           # 8% trailing stop
            }

@dataclass
class Position:
    """Represents a trading position with exit tracking"""
    symbol: str
    strategy: str
    entry_price: float
    entry_time: datetime
    shares: int
    position_value: float
    
    # Exit parameters
    profit_target: float
    stop_loss: float
    trailing_stop_price: Optional[float] = None
    peak_price: float = 0.0
    
    # Tracking
    exit_alerts: List[str] = None
    last_update: datetime = None
    
    def __post_init__(self):
        if self.exit_alerts is None:
            self.exit_alerts = []
        if self.last_update is None:
            self.last_update = self.entry_time
        if self.peak_price == 0.0:
            self.peak_price = self.entry_price

@dataclass 
class ExitSignal:
    """Exit signal with reasoning and urgency"""
    symbol: str
    exit_reason: ExitReason
    current_price: float
    recommended_exit_pct: float  # 0.0 to 1.0 (partial to full exit)
    urgency: str  # 'low', 'medium', 'high', 'critical'
    message: str
    profit_loss: float
    exit_time: datetime = None
    
    def __post_init__(self):
        if self.exit_time is None:
            self.exit_time = datetime.now()

class FastExitManager:
    """Manages fast exits and profit recycling for weekly ROI optimization"""
    
    def __init__(self, config: FastExitConfig = None):
        self.config = config or FastExitConfig()
        self.positions: Dict[str, Position] = {}
        self.exit_history: List[Dict] = []
        self.capital_recycling_log: List[Dict] = []
        self.daily_recycling_count: Dict[str, int] = {}  # symbol -> count
        
        logger.info("Fast Exit Manager initialized")
        logger.info(f"  Quick profit targets: {self.config.quick_profit_targets}")
        logger.info(f"  Fast exit threshold: {self.config.fast_exit_threshold:.1%}")
        logger.info(f"  Portfolio heat threshold: {self.config.portfolio_heat_threshold:.1%}")
    
    def add_position(self, symbol: str, strategy: str, entry_price: float, 
                    shares: int, profit_target: float = None, stop_loss: float = None) -> None:
        """Add a new position to track"""
        
        # Use strategy-specific defaults if not provided
        if profit_target is None:
            profit_target = self.config.quick_profit_targets.get(strategy, 0.05)
        if stop_loss is None:
            stop_loss = self.config.position_heat_threshold
        
        position = Position(
            symbol=symbol,
            strategy=strategy,
            entry_price=entry_price,
            entry_time=datetime.now(),
            shares=shares,
            position_value=entry_price * shares,
            profit_target=profit_target,
            stop_loss=stop_loss
        )
        
        self.positions[symbol] = position
        logger.info(f"Added position: {symbol} @ ${entry_price:.2f} ({strategy} strategy)")
        logger.info(f"  Target: {profit_target:.1%}, Stop: {stop_loss:.1%}")
    
    def update_position(self, symbol: str, current_price: float, 
                       current_volume: int = None) -> List[ExitSignal]:
        """Update position and check for exit conditions"""
        
        if symbol not in self.positions:
            return []
        
        position = self.positions[symbol]
        exit_signals = []
        
        # Update position tracking
        if current_price > position.peak_price:
            position.peak_price = current_price
        position.last_update = datetime.now()
        
        # Calculate current P&L
        current_pnl = (current_price - position.entry_price) / position.entry_price
        current_value = current_price * position.shares
        profit_loss = current_value - position.position_value
        
        # 1. Check for fast profit exit
        if current_pnl >= self.config.fast_exit_threshold:
            exit_signals.append(ExitSignal(
                symbol=symbol,
                exit_reason=ExitReason.FAST_PROFIT,
                current_price=current_price,
                recommended_exit_pct=0.5,  # Take 50% profit
                urgency='medium',
                message=f"Fast profit available: {current_pnl:.1%} (target: {self.config.fast_exit_threshold:.1%})",
                profit_loss=profit_loss
            ))
        
        # 2. Check for profit target hit
        if current_pnl >= position.profit_target:
            exit_signals.append(ExitSignal(
                symbol=symbol,
                exit_reason=ExitReason.PROFIT_TARGET,
                current_price=current_price,
                recommended_exit_pct=1.0,
                urgency='high',
                message=f"Profit target hit: {current_pnl:.1%} (target: {position.profit_target:.1%})",
                profit_loss=profit_loss
            ))
        
        # 3. Check for stop loss
        if current_pnl <= position.stop_loss:
            exit_signals.append(ExitSignal(
                symbol=symbol,
                exit_reason=ExitReason.STOP_LOSS,
                current_price=current_price,
                recommended_exit_pct=1.0,
                urgency='critical',
                message=f"Stop loss hit: {current_pnl:.1%} (stop: {position.stop_loss:.1%})",
                profit_loss=profit_loss
            ))
        
        # 4. Check for trailing stop
        trailing_distance = self.config.trailing_stop_distance.get(position.strategy, 0.02)
        if current_pnl >= self.config.trailing_stop_activation:
            trailing_stop_price = position.peak_price * (1 - trailing_distance)
            position.trailing_stop_price = trailing_stop_price
            
            if current_price <= trailing_stop_price:
                exit_signals.append(ExitSignal(
                    symbol=symbol,
                    exit_reason=ExitReason.TRAILING_STOP,
                    current_price=current_price,
                    recommended_exit_pct=1.0,
                    urgency='high',
                    message=f"Trailing stop hit: ${current_price:.2f} <= ${trailing_stop_price:.2f}",
                    profit_loss=profit_loss
                ))
        
        # 5. Check for time-based exit
        max_hours = self.config.max_hold_hours.get(position.strategy, 48)
        hours_held = (datetime.now() - position.entry_time).total_seconds() / 3600
        
        if hours_held >= max_hours:
            exit_signals.append(ExitSignal(
                symbol=symbol,
                exit_reason=ExitReason.TIME_STOP,
                current_price=current_price,
                recommended_exit_pct=1.0,
                urgency='medium',
                message=f"Max hold time reached: {hours_held:.1f}h (max: {max_hours}h)",
                profit_loss=profit_loss
            ))
        
        # 6. Check for momentum breakdown (if we have recent prices)
        momentum_breakdown = self._check_momentum_breakdown(symbol, current_price)
        if momentum_breakdown:
            exit_signals.append(ExitSignal(
                symbol=symbol,
                exit_reason=ExitReason.MOMENTUM_BREAKDOWN,
                current_price=current_price,
                recommended_exit_pct=0.75,  # Exit 75%
                urgency='medium',
                message="Momentum breakdown detected",
                profit_loss=profit_loss
            ))
        
        # 7. Intraday exit for day trades
        if position.strategy in ['scalping', 'day_trading']:
            if self._is_intraday_exit_time():
                exit_signals.append(ExitSignal(
                    symbol=symbol,
                    exit_reason=ExitReason.TIME_STOP,
                    current_price=current_price,
                    recommended_exit_pct=1.0,
                    urgency='high',
                    message=f"Intraday exit time reached: {self.config.intraday_exit_time}",
                    profit_loss=profit_loss
                ))
        
        return exit_signals
    
    def check_exit_signals(self, positions: Dict) -> List[ExitSignal]:
        """Check for exit signals from position dictionary format (for testing)"""
        exit_signals = []
        
        for symbol, pos_data in positions.items():
            # Convert dict format to our position tracking format
            if symbol not in self.positions:
                # Add temporary position for checking
                self.add_position(
                    symbol=symbol,
                    strategy=pos_data.get('strategy', 'unknown'),
                    entry_price=pos_data['entry_price'],
                    shares=pos_data['quantity']
                )
            
            # Use existing update_position logic
            signals = self.update_position(symbol, pos_data['current_price'])
            exit_signals.extend(signals)
        
        return exit_signals
    
    def execute_exit(self, symbol: str, exit_signal: ExitSignal, 
                    actual_exit_price: float = None) -> Dict:
        """Execute exit and log for capital recycling"""
        
        if symbol not in self.positions:
            return {}
        
        position = self.positions[symbol]
        exit_price = actual_exit_price or exit_signal.current_price
        
        # Calculate final P&L
        total_pnl = (exit_price - position.entry_price) / position.entry_price
        dollar_pnl = (exit_price - position.entry_price) * position.shares
        
        # Create exit record
        exit_record = {
            'symbol': symbol,
            'strategy': position.strategy,
            'entry_price': position.entry_price,
            'exit_price': exit_price,
            'entry_time': position.entry_time,
            'exit_time': datetime.now(),
            'hold_time_hours': (datetime.now() - position.entry_time).total_seconds() / 3600,
            'shares': position.shares,
            'pnl_pct': total_pnl,
            'pnl_dollars': dollar_pnl,
            'exit_reason': exit_signal.exit_reason.value,
            'exit_message': exit_signal.message,
            'position_value': position.position_value,
            'peak_price': position.peak_price,
            'max_gain_pct': (position.peak_price - position.entry_price) / position.entry_price
        }
        
        self.exit_history.append(exit_record)
        
        # Log for capital recycling if profitable and fast
        if (total_pnl > 0 and 
            exit_record['hold_time_hours'] <= 24 and 
            self.config.enable_fast_recycling):
            
            self._log_capital_recycling(exit_record)
        
        # Remove position
        del self.positions[symbol]
        
        logger.info(f"Exited {symbol}: {total_pnl:.1%} P&L in {exit_record['hold_time_hours']:.1f}h")
        logger.info(f"  Reason: {exit_signal.message}")
        
        return exit_record
    
    def get_portfolio_heat(self) -> float:
        """Calculate current portfolio heat (unrealized loss)"""
        if not self.positions:
            return 0.0
        
        total_unrealized_loss = 0.0
        total_position_value = 0.0
        
        for position in self.positions.values():
            # This would need current price - simplified for now
            total_position_value += position.position_value
        
        if total_position_value == 0:
            return 0.0
        
        return total_unrealized_loss / total_position_value
    
    def should_halt_new_positions(self) -> Tuple[bool, str]:
        """Check if new positions should be halted due to risk"""
        
        portfolio_heat = self.get_portfolio_heat()
        
        if portfolio_heat <= self.config.portfolio_heat_threshold:
            return True, f"Portfolio heat too high: {portfolio_heat:.1%}"
        
        # Check recent exit performance
        recent_exits = [e for e in self.exit_history 
                       if (datetime.now() - e['exit_time']).total_seconds() < 3600]  # Last hour
        
        if len(recent_exits) >= 3:
            recent_losses = [e for e in recent_exits if e['pnl_pct'] < 0]
            if len(recent_losses) >= 2:
                return True, f"Too many recent losses: {len(recent_losses)}/3 in last hour"
        
        return False, ""
    
    def get_recycling_opportunities(self) -> List[Dict]:
        """Get capital available for recycling from recent exits"""
        
        opportunities = []
        current_date = datetime.now().date()
        
        for recycling_record in self.capital_recycling_log:
            if recycling_record['date'] == current_date:
                symbol = recycling_record['symbol']
                recycling_count = self.daily_recycling_count.get(symbol, 0)
                
                if recycling_count < self.config.max_recycling_per_day:
                    # Check cooldown
                    time_since_exit = (datetime.now() - recycling_record['exit_time']).total_seconds() / 60
                    if time_since_exit >= self.config.recycling_cooldown_minutes:
                        opportunities.append({
                            'symbol': symbol,
                            'available_capital': recycling_record['freed_capital'],
                            'profit_from_last': recycling_record['profit'],
                            'recycling_count': recycling_count,
                            'time_since_exit': time_since_exit
                        })
        
        return opportunities
    
    def get_exit_statistics(self, days: int = 7) -> Dict:
        """Get exit statistics for performance analysis"""
        
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_exits = [e for e in self.exit_history if e['exit_time'] >= cutoff_date]
        
        if not recent_exits:
            return {'period_days': days, 'total_exits': 0}
        
        # Calculate statistics
        total_exits = len(recent_exits)
        profitable_exits = [e for e in recent_exits if e['pnl_pct'] > 0]
        fast_exits = [e for e in recent_exits if e['hold_time_hours'] <= 24]
        
        avg_hold_time = np.mean([e['hold_time_hours'] for e in recent_exits])
        avg_pnl = np.mean([e['pnl_pct'] for e in recent_exits])
        
        # Exit reasons breakdown
        exit_reasons = {}
        for exit in recent_exits:
            reason = exit['exit_reason']
            exit_reasons[reason] = exit_reasons.get(reason, 0) + 1
        
        return {
            'period_days': days,
            'total_exits': total_exits,
            'profitable_exits': len(profitable_exits),
            'win_rate': len(profitable_exits) / total_exits if total_exits > 0 else 0,
            'fast_exits': len(fast_exits),
            'fast_exit_rate': len(fast_exits) / total_exits if total_exits > 0 else 0,
            'avg_hold_time_hours': avg_hold_time,
            'avg_pnl_pct': avg_pnl,
            'total_pnl_dollars': sum(e['pnl_dollars'] for e in recent_exits),
            'exit_reasons': exit_reasons,
            'capital_recycled': len(self.capital_recycling_log)
        }
    
    def _check_momentum_breakdown(self, symbol: str, current_price: float) -> bool:
        """Check if momentum is breaking down (simplified)"""
        # This would need price history - simplified for now
        return False
    
    def _is_intraday_exit_time(self) -> bool:
        """Check if it's time for intraday exits"""
        now = datetime.now()
        exit_time = datetime.strptime(self.config.intraday_exit_time, "%H:%M").time()
        return now.time() >= exit_time
    
    def _log_capital_recycling(self, exit_record: Dict) -> None:
        """Log successful exit for capital recycling"""
        
        recycling_record = {
            'symbol': exit_record['symbol'],
            'exit_time': exit_record['exit_time'],
            'date': exit_record['exit_time'].date(),
            'freed_capital': exit_record['position_value'] + exit_record['pnl_dollars'],
            'profit': exit_record['pnl_dollars'],
            'hold_time_hours': exit_record['hold_time_hours']
        }
        
        self.capital_recycling_log.append(recycling_record)
        
        # Update daily recycling count
        symbol = exit_record['symbol']
        date_key = exit_record['exit_time'].strftime('%Y-%m-%d')
        self.daily_recycling_count[f"{symbol}_{date_key}"] = \
            self.daily_recycling_count.get(f"{symbol}_{date_key}", 0) + 1

def main():
    """Test the fast exit manager"""
    
    # Initialize fast exit manager
    config = FastExitConfig()
    exit_manager = FastExitManager(config)
    
    print("⚡ Fast Exit Manager Test")
    print("=" * 50)
    
    # Add test positions
    exit_manager.add_position('AAPL', 'momentum', 150.0, 100, profit_target=0.06, stop_loss=-0.02)
    exit_manager.add_position('TSLA', 'scalping', 250.0, 50, profit_target=0.015, stop_loss=-0.015)
    exit_manager.add_position('MSFT', 'mean_reversion', 300.0, 75, profit_target=0.04, stop_loss=-0.02)
    
    print(f"\n📊 Added {len(exit_manager.positions)} test positions")
    
    # Test exit signals with different price scenarios
    test_scenarios = [
        ('AAPL', 154.5, "Small profit"),      # 3% gain
        ('TSLA', 246.0, "Small loss"),        # 1.6% loss  
        ('MSFT', 312.0, "Target hit"),       # 4% gain
    ]
    
    print(f"\n🚨 Testing exit signals:")
    
    for symbol, price, scenario in test_scenarios:
        print(f"\n{scenario}: {symbol} @ ${price:.2f}")
        exit_signals = exit_manager.update_position(symbol, price)
        
        for signal in exit_signals:
            print(f"  ⚠️  {signal.exit_reason.value.title()}: {signal.message}")
            print(f"      Urgency: {signal.urgency}, Exit: {signal.recommended_exit_pct:.0%}")
    
    # Test configuration display
    print(f"\n⚙️ Fast Exit Configuration:")
    print(f"   Quick profit targets: {config.quick_profit_targets}")
    print(f"   Fast exit threshold: {config.fast_exit_threshold:.1%}")
    print(f"   Max hold times: {config.max_hold_hours}")
    print(f"   Trailing stops: {config.trailing_stop_distance}")
    
    # Get statistics
    stats = exit_manager.get_exit_statistics()
    print(f"\n📈 Exit Statistics (last 7 days):")
    print(f"   Total exits: {stats['total_exits']}")
    print(f"   Win rate: {stats['win_rate']:.1%}")
    print(f"   Fast exits: {stats['fast_exit_rate']:.1%}")
    
    print(f"\n✅ Fast Exit Manager operational - ready for quick profit recycling")

if __name__ == "__main__":
    main()

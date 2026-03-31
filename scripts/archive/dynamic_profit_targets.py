#!/usr/bin/env python3
"""
Dynamic Multi-Level Profit Targets Implementation
Implements dynamic multi-level profit targets (Option 2A) for Signal Quality Improvement Plan
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone
import logging
from dataclasses import dataclass
import json

@dataclass
class ProfitTarget:
    """Data class for profit target configuration"""
    level: int
    percentage: float
    quantity_fraction: float
    trigger_price: float
    status: str = 'active'  # active, triggered, expired
    created_at: str = None

class DynamicProfitTargetManager:
    """
    Dynamic Multi-Level Profit Target System
    
    Implements:
    - 25%/50%/75% position scaling with dynamic targets
    - Adaptive target adjustment based on volatility and momentum
    - Market condition-aware target spacing
    - Risk-adjusted profit maximization
    """
    
    def __init__(self, config=None):
        self.config = config or self._get_default_config()
        self.active_targets = {}  # symbol -> list of targets
        self.target_history = []
        self.performance_stats = {
            'targets_created': 0,
            'targets_hit': 0,
            'total_profit_captured': 0.0,
            'avg_target_hit_time': 0.0
        }
        
        logging.info("🎯 Dynamic Profit Target Manager initialized")
    
    def _get_default_config(self):
        """Default configuration for profit targets"""
        return {
            'target_levels': [
                {'level': 1, 'base_percentage': 0.025, 'quantity_fraction': 0.25},  # 25% at 2.5%
                {'level': 2, 'base_percentage': 0.05, 'quantity_fraction': 0.5},   # 50% at 5%
                {'level': 3, 'base_percentage': 0.075, 'quantity_fraction': 1.0}   # 100% at 7.5%
            ],
            'volatility_adjustment': {
                'enabled': True,
                'low_vol_multiplier': 0.7,    # Tighter targets in low volatility
                'high_vol_multiplier': 1.5,   # Wider targets in high volatility
                'vol_threshold_low': 0.015,   # 1.5% daily volatility
                'vol_threshold_high': 0.04    # 4% daily volatility
            },
            'momentum_adjustment': {
                'enabled': True,
                'strong_momentum_multiplier': 1.3,  # Higher targets with strong momentum
                'weak_momentum_multiplier': 0.8,    # Lower targets with weak momentum
                'momentum_threshold': 0.03          # 3% momentum threshold
            },
            'market_condition_adjustment': {
                'enabled': True,
                'bull_market_multiplier': 1.2,
                'bear_market_multiplier': 0.8,
                'sideways_multiplier': 0.9
            },
            'risk_management': {
                'max_target_percentage': 0.15,     # Maximum 15% target
                'min_target_percentage': 0.01,     # Minimum 1% target
                'target_timeout_hours': 24,        # Expire targets after 24 hours
                'trailing_adjustment': True        # Adjust targets based on price movement
            }
        }
    
    def create_profit_targets(self, symbol: str, entry_price: float, position_size: float,
                            market_data: pd.DataFrame, regime: str = 'NEUTRAL') -> List[ProfitTarget]:
        """
        Create dynamic profit targets for a position
        
        Args:
            symbol: Stock symbol
            entry_price: Position entry price
            position_size: Position size in shares
            market_data: Price/volume data for analysis
            regime: Current market regime
            
        Returns:
            List of ProfitTarget objects
        """
        self.performance_stats['targets_created'] += 1
        
        # Calculate market adjustments
        volatility_mult = self._calculate_volatility_adjustment(market_data)
        momentum_mult = self._calculate_momentum_adjustment(market_data)
        regime_mult = self._calculate_regime_adjustment(regime)
        
        # Create targets
        targets = []
        remaining_quantity = position_size
        
        for level_config in self.config['target_levels']:
            # Calculate adjusted target percentage
            base_pct = level_config['base_percentage']
            adjusted_pct = base_pct * volatility_mult * momentum_mult * regime_mult
            
            # Apply risk management bounds
            adjusted_pct = max(
                self.config['risk_management']['min_target_percentage'],
                min(self.config['risk_management']['max_target_percentage'], adjusted_pct)
            )
            
            # Calculate target price and quantity
            target_price = entry_price * (1 + adjusted_pct)
            
            if level_config['quantity_fraction'] < 1.0:
                target_quantity = position_size * level_config['quantity_fraction']
            else:
                target_quantity = remaining_quantity
            
            remaining_quantity -= target_quantity
            
            # Create target
            target = ProfitTarget(
                level=level_config['level'],
                percentage=adjusted_pct,
                quantity_fraction=level_config['quantity_fraction'],
                trigger_price=target_price,
                status='active',
                created_at=datetime.now().isoformat()
            )
            
            targets.append(target)
            
            logging.info(f"🎯 Created target L{target.level} for {symbol}: "
                        f"${target_price:.2f} ({adjusted_pct:.1%}) - {target_quantity:.0f} shares")
        
        # Store active targets
        self.active_targets[symbol] = targets
        
        return targets
    
    def _calculate_volatility_adjustment(self, market_data: pd.DataFrame) -> float:
        """Calculate volatility-based target adjustment"""
        if not self.config['volatility_adjustment']['enabled'] or len(market_data) < 20:
            return 1.0
        
        try:
            # Calculate recent volatility
            returns = market_data['close'].pct_change().dropna()
            current_volatility = returns.rolling(10).std().iloc[-1]
            
            vol_config = self.config['volatility_adjustment']
            
            if current_volatility < vol_config['vol_threshold_low']:
                return vol_config['low_vol_multiplier']
            elif current_volatility > vol_config['vol_threshold_high']:
                return vol_config['high_vol_multiplier']
            else:
                # Linear interpolation between thresholds
                low_thresh = vol_config['vol_threshold_low']
                high_thresh = vol_config['vol_threshold_high']
                low_mult = vol_config['low_vol_multiplier']
                high_mult = vol_config['high_vol_multiplier']
                
                ratio = (current_volatility - low_thresh) / (high_thresh - low_thresh)
                return low_mult + ratio * (high_mult - low_mult)
                
        except Exception as e:
            logging.warning(f"Volatility adjustment error: {e}")
            return 1.0
    
    def _calculate_momentum_adjustment(self, market_data: pd.DataFrame) -> float:
        """Calculate momentum-based target adjustment"""
        if not self.config['momentum_adjustment']['enabled'] or len(market_data) < 10:
            return 1.0
        
        try:
            # Calculate recent momentum
            close = market_data['close']
            momentum_5d = (close.iloc[-1] / close.iloc[-6] - 1) if len(close) >= 6 else 0
            momentum_10d = (close.iloc[-1] / close.iloc[-11] - 1) if len(close) >= 11 else 0
            
            avg_momentum = (momentum_5d + momentum_10d) / 2
            threshold = self.config['momentum_adjustment']['momentum_threshold']
            
            if avg_momentum > threshold:
                return self.config['momentum_adjustment']['strong_momentum_multiplier']
            elif avg_momentum < -threshold:
                return self.config['momentum_adjustment']['weak_momentum_multiplier']
            else:
                return 1.0
                
        except Exception as e:
            logging.warning(f"Momentum adjustment error: {e}")
            return 1.0
    
    def _calculate_regime_adjustment(self, regime: str) -> float:
        """Calculate market regime-based target adjustment"""
        if not self.config['market_condition_adjustment']['enabled']:
            return 1.0
        
        regime_multipliers = {
            'UP_LOWVOL': self.config['market_condition_adjustment']['bull_market_multiplier'],
            'UP_HIGHVOL': self.config['market_condition_adjustment']['bull_market_multiplier'] * 0.9,
            'DOWN_LOWVOL': self.config['market_condition_adjustment']['bear_market_multiplier'],
            'DOWN_HIGHVOL': self.config['market_condition_adjustment']['bear_market_multiplier'] * 0.8,
            'SIDEWAYS': self.config['market_condition_adjustment']['sideways_multiplier']
        }
        
        return regime_multipliers.get(regime, 1.0)
    
    def check_target_hits(self, symbol: str, current_price: float) -> List[Dict]:
        """
        Check if any targets have been hit and generate exit signals
        
        Args:
            symbol: Stock symbol
            current_price: Current market price
            
        Returns:
            List of exit signal dictionaries
        """
        if symbol not in self.active_targets:
            return []
        
        exit_signals = []
        targets = self.active_targets[symbol]
        
        for target in targets:
            if target.status == 'active' and current_price >= target.trigger_price:
                # Target hit!
                target.status = 'triggered'
                self.performance_stats['targets_hit'] += 1
                
                exit_signal = {
                    'symbol': symbol,
                    'action': 'partial_exit',
                    'target_level': target.level,
                    'trigger_price': target.trigger_price,
                    'current_price': current_price,
                    'quantity_fraction': target.quantity_fraction,
                    'profit_percentage': target.percentage,
                    'timestamp': datetime.now().isoformat()
                }
                
                exit_signals.append(exit_signal)
                
                # Calculate profit captured
                profit_captured = (current_price - target.trigger_price / (1 + target.percentage)) * target.quantity_fraction
                self.performance_stats['total_profit_captured'] += profit_captured
                
                logging.info(f"🎯 Target HIT! {symbol} L{target.level}: "
                           f"${current_price:.2f} (target: ${target.trigger_price:.2f})")
        
        return exit_signals
    
    def update_trailing_targets(self, symbol: str, current_price: float, 
                               entry_price: float, market_data: pd.DataFrame) -> bool:
        """
        Update targets with trailing adjustment logic
        
        Args:
            symbol: Stock symbol
            current_price: Current market price
            entry_price: Original entry price
            market_data: Recent market data
            
        Returns:
            True if targets were updated
        """
        if not self.config['risk_management']['trailing_adjustment']:
            return False
        
        if symbol not in self.active_targets:
            return False
        
        targets = self.active_targets[symbol]
        current_gain = (current_price / entry_price - 1)
        
        # Only adjust if we have significant unrealized gains
        if current_gain < 0.03:  # Less than 3% gain
            return False
        
        updated = False
        
        for target in targets:
            if target.status == 'active':
                # Calculate new target based on current price
                original_target_gain = target.percentage
                
                # If current price is significantly above target, raise the target
                current_target_gain = (target.trigger_price / entry_price - 1)
                
                if current_gain > current_target_gain * 1.5:  # 50% above target
                    # Raise target to capture more upside
                    new_target_percentage = current_gain * 0.9  # 90% of current gain
                    new_target_price = entry_price * (1 + new_target_percentage)
                    
                    if new_target_price > target.trigger_price:
                        target.trigger_price = new_target_price
                        target.percentage = new_target_percentage
                        updated = True
                        
                        logging.info(f"🔄 Trailing target updated {symbol} L{target.level}: "
                                   f"${new_target_price:.2f} ({new_target_percentage:.1%})")
        
        return updated
    
    def expire_old_targets(self, symbol: str) -> int:
        """
        Expire targets that are too old
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Number of targets expired
        """
        if symbol not in self.active_targets:
            return 0
        
        timeout_hours = self.config['risk_management']['target_timeout_hours']
        current_time = datetime.now()
        expired_count = 0
        
        for target in self.active_targets[symbol]:
            if target.status == 'active' and target.created_at:
                created_time = datetime.fromisoformat(target.created_at)
                hours_elapsed = (current_time - created_time).total_seconds() / 3600
                
                if hours_elapsed > timeout_hours:
                    target.status = 'expired'
                    expired_count += 1
                    
                    logging.info(f"⏰ Target expired {symbol} L{target.level} after {hours_elapsed:.1f}h")
        
        return expired_count
    
    def get_active_targets(self, symbol: str) -> List[ProfitTarget]:
        """Get active targets for a symbol"""
        if symbol not in self.active_targets:
            return []
        
        return [t for t in self.active_targets[symbol] if t.status == 'active']
    
    def get_performance_statistics(self) -> Dict:
        """Get performance statistics for profit targets"""
        stats = self.performance_stats.copy()
        
        if stats['targets_created'] > 0:
            stats['target_hit_rate'] = stats['targets_hit'] / stats['targets_created']
        else:
            stats['target_hit_rate'] = 0.0
        
        return stats
    
    def clear_targets(self, symbol: str):
        """Clear all targets for a symbol (e.g., when position is fully closed)"""
        if symbol in self.active_targets:
            logging.info(f"🧹 Clearing all targets for {symbol}")
            del self.active_targets[symbol]
    
    def save_target_state(self, filepath: str):
        """Save current target state to file"""
        state = {
            'active_targets': {},
            'performance_stats': self.performance_stats,
            'timestamp': datetime.now().isoformat()
        }
        
        # Convert targets to serializable format
        for symbol, targets in self.active_targets.items():
            state['active_targets'][symbol] = [
                {
                    'level': t.level,
                    'percentage': t.percentage,
                    'quantity_fraction': t.quantity_fraction,
                    'trigger_price': t.trigger_price,
                    'status': t.status,
                    'created_at': t.created_at
                }
                for t in targets
            ]
        
        with open(filepath, 'w') as f:
            json.dump(state, f, indent=2)
        
        logging.info(f"💾 Target state saved to {filepath}")
    
    def load_target_state(self, filepath: str):
        """Load target state from file"""
        try:
            with open(filepath, 'r') as f:
                state = json.load(f)
            
            self.performance_stats = state.get('performance_stats', self.performance_stats)
            
            # Restore targets
            for symbol, target_data in state.get('active_targets', {}).items():
                targets = []
                for t_data in target_data:
                    target = ProfitTarget(
                        level=t_data['level'],
                        percentage=t_data['percentage'],
                        quantity_fraction=t_data['quantity_fraction'],
                        trigger_price=t_data['trigger_price'],
                        status=t_data['status'],
                        created_at=t_data['created_at']
                    )
                    targets.append(target)
                
                self.active_targets[symbol] = targets
            
            logging.info(f"📂 Target state loaded from {filepath}")
            
        except Exception as e:
            logging.warning(f"Failed to load target state: {e}")


class EnhancedExitManager:
    """
    Enhanced Exit Manager with Dynamic Profit Targets
    Integrates with existing exit logic to add multi-level profit taking
    """
    
    def __init__(self):
        self.profit_target_manager = DynamicProfitTargetManager()
        self.position_tracker = {}  # Track position details
        
        logging.info("🚪 Enhanced Exit Manager initialized")
    
    def register_position(self, symbol: str, entry_price: float, position_size: float,
                         market_data: pd.DataFrame, regime: str = 'NEUTRAL'):
        """Register a new position and create profit targets"""
        
        # Create profit targets
        targets = self.profit_target_manager.create_profit_targets(
            symbol, entry_price, position_size, market_data, regime
        )
        
        # Track position details
        self.position_tracker[symbol] = {
            'entry_price': entry_price,
            'original_size': position_size,
            'current_size': position_size,
            'entry_time': datetime.now().isoformat(),
            'targets_created': len(targets)
        }
        
        logging.info(f"📈 Position registered: {symbol} - {position_size:.0f} shares @ ${entry_price:.2f}")
        
        return targets
    
    def check_exit_signals(self, symbol: str, current_price: float, 
                          market_data: pd.DataFrame) -> List[Dict]:
        """
        Check for exit signals from profit targets and other exit logic
        
        Returns list of exit signals with details
        """
        exit_signals = []
        
        if symbol not in self.position_tracker:
            return exit_signals
        
        position = self.position_tracker[symbol]
        
        # Check profit target hits
        target_signals = self.profit_target_manager.check_target_hits(symbol, current_price)
        exit_signals.extend(target_signals)
        
        # Update position size for any partial exits
        for signal in target_signals:
            quantity_exited = position['original_size'] * signal['quantity_fraction']
            position['current_size'] -= quantity_exited
            
            logging.info(f"📉 Partial exit: {symbol} - {quantity_exited:.0f} shares @ ${current_price:.2f}")
        
        # Update trailing targets
        if len(market_data) >= 20:
            self.profit_target_manager.update_trailing_targets(
                symbol, current_price, position['entry_price'], market_data
            )
        
        # Expire old targets
        self.profit_target_manager.expire_old_targets(symbol)
        
        return exit_signals
    
    def close_position(self, symbol: str, exit_price: float, reason: str = 'manual'):
        """Close a position completely"""
        if symbol in self.position_tracker:
            position = self.position_tracker[symbol]
            
            # Calculate final P&L
            total_pnl = (exit_price - position['entry_price']) * position['current_size']
            
            logging.info(f"🔚 Position closed: {symbol} @ ${exit_price:.2f} - "
                        f"P&L: ${total_pnl:.2f} ({reason})")
            
            # Clear targets and position
            self.profit_target_manager.clear_targets(symbol)
            del self.position_tracker[symbol]
            
            return {
                'symbol': symbol,
                'exit_price': exit_price,
                'final_pnl': total_pnl,
                'reason': reason,
                'timestamp': datetime.now().isoformat()
            }
        
        return None
    
    def get_position_status(self, symbol: str) -> Dict:
        """Get current position status and targets"""
        if symbol not in self.position_tracker:
            return {}
        
        position = self.position_tracker[symbol]
        active_targets = self.profit_target_manager.get_active_targets(symbol)
        
        return {
            'position': position,
            'active_targets': len(active_targets),
            'targets': [
                {
                    'level': t.level,
                    'price': t.trigger_price,
                    'percentage': t.percentage,
                    'status': t.status
                }
                for t in active_targets
            ]
        }
    
    def get_system_statistics(self) -> Dict:
        """Get comprehensive system statistics"""
        target_stats = self.profit_target_manager.get_performance_statistics()
        
        system_stats = {
            'active_positions': len(self.position_tracker),
            'total_targets': sum(
                len(self.profit_target_manager.get_active_targets(symbol))
                for symbol in self.position_tracker.keys()
            ),
            'profit_target_performance': target_stats
        }
        
        return system_stats


def main():
    """Test the dynamic profit target system"""
    print("🎯 Testing Dynamic Multi-Level Profit Targets")
    print("=" * 60)
    
    # Create test manager
    exit_manager = EnhancedExitManager()
    
    # Create sample market data
    dates = pd.date_range('2025-10-01', periods=30, freq='D')
    np.random.seed(42)
    
    market_data = pd.DataFrame({
        'close': 100 + np.cumsum(np.random.randn(30) * 0.02),
        'high': 0,
        'low': 0,
        'volume': np.random.randint(100000, 1000000, 30)
    })
    
    # Add high/low
    market_data['high'] = market_data['close'] * 1.01
    market_data['low'] = market_data['close'] * 0.99
    
    # Test position registration
    symbol = 'TEST'
    entry_price = 100.0
    position_size = 1000
    
    targets = exit_manager.register_position(
        symbol, entry_price, position_size, market_data, 'UP_LOWVOL'
    )
    
    print(f"\nCreated {len(targets)} profit targets:")
    for target in targets:
        print(f"  Level {target.level}: ${target.trigger_price:.2f} "
              f"({target.percentage:.1%}) - {target.quantity_fraction:.0%} of position")
    
    # Test target checking with price movement
    test_prices = [102.5, 105.0, 107.5, 110.0]
    
    for price in test_prices:
        print(f"\nTesting price: ${price:.2f}")
        exit_signals = exit_manager.check_exit_signals(symbol, price, market_data)
        
        if exit_signals:
            for signal in exit_signals:
                print(f"  🎯 Target hit! Level {signal['target_level']}: "
                      f"{signal['quantity_fraction']:.0%} exit @ ${signal['current_price']:.2f}")
        else:
            print("  No targets hit")
    
    # Show final status
    status = exit_manager.get_position_status(symbol)
    print(f"\nFinal Position Status:")
    print(f"  Current size: {status['position']['current_size']:.0f} shares")
    print(f"  Active targets: {status['active_targets']}")
    
    # Show system statistics
    stats = exit_manager.get_system_statistics()
    print(f"\nSystem Statistics:")
    print(f"  Active positions: {stats['active_positions']}")
    print(f"  Total active targets: {stats['total_targets']}")
    print(f"  Targets created: {stats['profit_target_performance']['targets_created']}")
    print(f"  Targets hit: {stats['profit_target_performance']['targets_hit']}")
    print(f"  Hit rate: {stats['profit_target_performance']['target_hit_rate']:.1%}")
    
    print("\n✅ Dynamic Profit Target testing completed!")

if __name__ == "__main__":
    main()
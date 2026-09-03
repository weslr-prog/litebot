"""
Enhanced Risk Management for LiteBotX - Phase 2 Implementation
Purpose: Centralized risk management for achieving 5% weekly ROI safely
"""

import logging
import pandas as pd
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
import json
import os

# Configure logging for Risk Management
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

class RiskManager:
    """
    Enhanced Risk Management System for 5% Weekly ROI Targets
    
    Key Features:
    - Dynamic position sizing: Risk$ = 0.005 × β_regime × Equity × confidence
    - Portfolio caps: Max 3 positions (start), 5 (later), ≤2 per sector
    - Loss limits: -1.5% daily, -3% weekly (auto-halt)
    - Regime-aware risk scaling
    """
    
    def __init__(self, initial_equity=10000.0, max_risk_per_trade=0.005):
        # Core settings for 5% weekly ROI
        self.initial_equity = initial_equity
        self.current_equity = initial_equity
        self.max_risk_per_trade = max_risk_per_trade  # 0.5% per trade
        
        # Portfolio tracking
        self.positions = {}  # {symbol: position_info}
        self.daily_pnl = 0.0
        self.weekly_pnl = 0.0
        self.max_positions = 3  # Conservative start, increase to 5 later
        
        # Loss limits (CRITICAL for risk management)
        self.daily_loss_limit = -0.015    # -1.5% daily
        self.weekly_loss_limit = -0.03    # -3% weekly  
        self.is_trading_halted = False
        
        # Sector exposure limits
        self.max_positions_per_sector = 2
        self.sector_positions = {}  # {sector: count}
        
        # Performance tracking
        self.trade_history = []
        self.risk_metrics = {
            'total_trades': 0,
            'winning_trades': 0,
            'avg_win': 0.0,
            'avg_loss': 0.0,
            'current_drawdown': 0.0,
            'max_drawdown': 0.0,
            'sharpe_ratio': 0.0
        }
        
        # Regime-based risk multipliers (β_regime)
        self.regime_multipliers = {
            'bull': 1.2,        # Higher risk in trending up markets
            'bear': 0.6,        # Lower risk in downtrending markets  
            'sideways': 0.8,    # Moderate risk in range-bound markets
            'volatile': 1.0,    # Standard risk in volatile breakout markets
            'UP_LOWVOL': 1.1,   # Slightly higher risk in stable uptrends
            'DOWN_HIGHVOL': 0.5 # Very low risk in volatile downtrends
        }
        
        # Legacy compatibility (keep existing interface)
        self.max_drawdown_pct = 0.2
        self.stop_loss_pct = 0.03
        self.take_profit_pct = 0.06
        self.trailing_stop_pct = 0.03
        self.trading_hours = (9, 16)
        self.daily_loss = 0.0
        self.weekly_loss = 0.0
        self.last_reset_date = None
        self.last_reset_week = None
        
        logging.info(f"🛡️ Enhanced RiskManager initialized: ${initial_equity:,.2f} equity, {self.max_risk_per_trade:.1%} max risk per trade")
        logging.info(f"📊 Portfolio limits: {self.max_positions} max positions, {self.max_positions_per_sector} per sector")
        logging.info(f"🚨 Loss limits: {self.daily_loss_limit:.1%} daily, {self.weekly_loss_limit:.1%} weekly")

    def calculate_position_size(self, signal_confidence: float, stop_distance: float, 
                              regime: str = 'sideways', current_price: float = 100.0,
                              account_equity: Optional[float] = None) -> Dict:
        """
        Calculate optimal position size for 5% weekly ROI targets
        
        Formula: Risk$ = 0.005 × β_regime × Equity × confidence
        Qty = Risk$ / Stop_Distance, rounded down to 2 decimals
        
        Args:
            signal_confidence: 0.0-1.0 confidence in the signal (from ML/strategy)
            stop_distance: Distance to stop loss ($ per share)
            regime: Market regime (bull/bear/sideways/volatile/UP_LOWVOL/DOWN_HIGHVOL)
            current_price: Current stock price
            account_equity: Override equity (for legacy compatibility)
            
        Returns:
            Dict with position size details or legacy int for compatibility
        """
        # Use current equity or override
        equity = account_equity if account_equity is not None else self.current_equity
        
        if self.is_trading_halted:
            logging.warning("🚨 Trading halted due to loss limits")
            return {'quantity': 0, 'risk_dollars': 0, 'reason': 'trading_halted'}
        
        # Get regime multiplier (β_regime)
        beta_regime = self.regime_multipliers.get(regime, 1.0)
        
        # Calculate risk amount: Risk$ = 0.005 × β_regime × Equity × confidence
        base_risk = self.max_risk_per_trade * equity
        risk_dollars = base_risk * beta_regime * signal_confidence
        
        # Calculate quantity: Qty = Risk$ / Stop_Distance
        if stop_distance <= 0:
            logging.error(f"❌ Invalid stop distance: {stop_distance}")
            return {'quantity': 0, 'risk_dollars': 0, 'reason': 'invalid_stop_distance'}
        
        raw_quantity = risk_dollars / stop_distance
        quantity = round(raw_quantity, 2)  # Round down to 2 decimals as specified
        
        # Portfolio limit checks
        if len(self.positions) >= self.max_positions:
            logging.warning(f"⚠️ Max positions reached: {len(self.positions)}/{self.max_positions}")
            return {'quantity': 0, 'risk_dollars': 0, 'reason': 'max_positions_reached'}
        
        # Position value limit (max 30% of equity per position)
        position_value = quantity * current_price
        max_position_value = equity * 0.3
        
        if position_value > max_position_value:
            quantity = max_position_value / current_price
            quantity = round(quantity, 2)
            risk_dollars = quantity * stop_distance
            logging.warning(f"⚠️ Position size reduced due to 30% limit: {quantity} shares")
        
        # Ensure minimum position size
        if quantity < 1:
            logging.warning(f"⚠️ Position size too small: {quantity} shares")
            return {'quantity': 0, 'risk_dollars': 0, 'reason': 'position_too_small'}
        
        position_info = {
            'quantity': quantity,
            'risk_dollars': risk_dollars,
            'position_value': quantity * current_price,
            'stop_distance': stop_distance,
            'confidence': signal_confidence,
            'regime': regime,
            'beta_regime': beta_regime,
            'risk_percent': risk_dollars / equity,
            'reason': 'approved'
        }
        
        logging.info(f"📏 Position size: {quantity} shares, ${risk_dollars:.2f} risk ({position_info['risk_percent']:.2%}) in {regime} regime")
        
        # Legacy compatibility: return just the quantity as int if called with old parameters
        if account_equity is not None:
            return max(int(quantity), 1)
        
        return position_info

    def compute_risk_dollars(self, equity: float, beta_regime: float = 1.0) -> float:
        """
        Compute risk dollars for regime-based position sizing
        Used by attach_regime_and_size in backtester
        """
        return self.max_risk_per_trade * beta_regime * equity

    def check_sector_exposure(self, symbol: str, sector: str = 'Unknown') -> bool:
        """
        Check if adding this position would exceed sector exposure limits
        Max 2 positions per GICS sector
        """
        current_sector_count = self.sector_positions.get(sector, 0)
        
        if current_sector_count >= self.max_positions_per_sector:
            logging.warning(f"🚫 Sector exposure limit: {sector} has {current_sector_count}/{self.max_positions_per_sector} positions")
            return False
        
        return True

    def check_loss_limits(self) -> bool:
        """
        Check daily and weekly loss limits
        Daily: -1.5%, Weekly: -3%
        """
        daily_loss_pct = self.daily_pnl / self.current_equity
        weekly_loss_pct = self.weekly_pnl / self.current_equity
        
        if daily_loss_pct <= self.daily_loss_limit:
            logging.error(f"🚨 DAILY LOSS LIMIT HIT: {daily_loss_pct:.2%} <= {self.daily_loss_limit:.2%}")
            self.is_trading_halted = True
            return False
        
        if weekly_loss_pct <= self.weekly_loss_limit:
            logging.error(f"🚨 WEEKLY LOSS LIMIT HIT: {weekly_loss_pct:.2%} <= {self.weekly_loss_limit:.2%}")
            self.is_trading_halted = True
            return False
        
        return True

    def should_trade(self, symbol: str, action: str, portfolio: List, account_equity: float, 
                    price: float, peak_equity: float, start_equity: Optional[float] = None, 
                    expected_price: Optional[float] = None, actual_price: Optional[float] = None,
                    signal_confidence: float = 0.5, regime: str = 'sideways', 
                    sector: str = 'Unknown') -> bool:
        """
        Enhanced trade approval system - ALL trades must pass through this
        Combines legacy interface with new 5% weekly ROI logic
        """
        if action == 'hold':
            logging.info(f"ℹ️ No trade for {symbol}: action is 'hold'")
            return False
        
        # Update current equity
        self.current_equity = account_equity
        
        # New loss limit checks (more strict)
        if not self.check_loss_limits():
            logging.warning(f"🚫 Trade blocked: loss limits exceeded")
            return False
        
        # New sector exposure check
        if not self.check_sector_exposure(symbol, sector):
            logging.warning(f"🚫 Trade blocked: sector exposure limit for {sector}")
            return False
        
        # Legacy checks (keep for compatibility)
        if not self.check_max_positions(portfolio):
            logging.warning(f"🚫 Trade blocked: max positions reached ({len(portfolio)}/{self.max_positions})")
            return False
        
        if not self.check_max_drawdown(account_equity, peak_equity):
            logging.warning(f"🚫 Trade blocked: max drawdown exceeded")
            return False
        
        if not self.check_trading_hours():
            logging.warning(f"🚫 Trade blocked: outside trading hours")
            return False
        
        if expected_price is not None and actual_price is not None:
            if not self.check_slippage(expected_price, actual_price):
                logging.warning(f"🚫 Trade blocked: slippage too high")
                return False
        
        # Calculate position size with new formula
        stop_distance = abs(price * self.stop_loss_pct)  # Default stop distance
        position_info = self.calculate_position_size(
            signal_confidence=signal_confidence,
            stop_distance=stop_distance,
            regime=regime,
            current_price=price
        )
        
        if isinstance(position_info, dict) and position_info['quantity'] <= 0:
            logging.warning(f"🚫 Trade blocked: {position_info['reason']}")
            return False
        
        logging.info(f"✅ Trade APPROVED: {symbol} {action} @ ${price:.2f}")
        return True

    def approve_trade(self, symbol: str, signal_type: str, signal_confidence: float,
                     entry_price: float, stop_loss: float, sector: str = 'Unknown',
                     regime: str = 'sideways') -> Dict:
        """
        Central trade approval for new interface
        """
        logging.info(f"🔍 Trade approval: {symbol} {signal_type} @ ${entry_price:.2f}, confidence={signal_confidence:.2f}")
        
        if not self.check_loss_limits():
            return {'approved': False, 'reason': 'loss_limits_exceeded', 'quantity': 0}
        
        if symbol in self.positions:
            return {'approved': False, 'reason': 'position_already_exists', 'quantity': 0}
        
        if not self.check_sector_exposure(symbol, sector):
            return {'approved': False, 'reason': 'sector_exposure_limit', 'quantity': 0}
        
        # Calculate position size
        stop_distance = abs(entry_price - stop_loss)
        position_info = self.calculate_position_size(
            signal_confidence=signal_confidence,
            stop_distance=stop_distance,
            regime=regime,
            current_price=entry_price
        )
        
        if position_info['quantity'] <= 0:
            return {'approved': False, 'reason': position_info['reason'], 'quantity': 0}
        
        # Approval details
        trade_approval = {
            'approved': True,
            'symbol': symbol,
            'signal_type': signal_type,
            'quantity': position_info['quantity'],
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'risk_dollars': position_info['risk_dollars'],
            'position_value': position_info['position_value'],
            'confidence': signal_confidence,
            'regime': regime,
            'sector': sector,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'reason': 'approved'
        }
        
        logging.info(f"✅ Trade APPROVED: {symbol} {position_info['quantity']} shares, ${position_info['risk_dollars']:.2f} risk")
        return trade_approval

    # Legacy methods (keep for compatibility)
    def get_stop_loss_price(self, entry_price):
        return round(entry_price * (1 - self.stop_loss_pct), 2)

    def get_take_profit_price(self, entry_price):
        return round(entry_price * (1 + self.take_profit_pct), 2)

    def get_trailing_stop_price(self, highest_price):
        return round(highest_price * (1 - self.trailing_stop_pct), 2)

    def check_max_positions(self, portfolio):
        return len(portfolio) < self.max_positions

    def check_max_drawdown(self, account_equity, peak_equity):
        drawdown = (peak_equity - account_equity) / peak_equity if peak_equity > 0 else 0
        return drawdown < self.max_drawdown_pct

    def check_daily_loss_limit(self, account_equity, start_equity):
        import datetime
        today = datetime.date.today()
        if self.last_reset_date != today:
            self.daily_loss = 0.0
            self.last_reset_date = today
        loss = start_equity - account_equity
        self.daily_loss = loss
        return (loss / start_equity) < self.daily_loss_limit_pct if start_equity > 0 else True

    def check_weekly_loss_limit(self, account_equity, start_equity):
        import datetime
        week = datetime.date.today().isocalendar()[1]
        if self.last_reset_week != week:
            self.weekly_loss = 0.0
            self.last_reset_week = week
        loss = start_equity - account_equity
        self.weekly_loss = loss
        return (loss / start_equity) < self.weekly_loss_limit_pct if start_equity > 0 else True

    def check_trading_hours(self):
        import datetime
        now = datetime.datetime.now().hour
        return self.trading_hours[0] <= now < self.trading_hours[1]

    def check_slippage(self, expected_price, actual_price, max_slippage_pct=0.01):
        slippage = abs(actual_price - expected_price) / expected_price
        return slippage <= max_slippage_pct

    def get_portfolio_summary(self) -> Dict:
        """Get current portfolio status for monitoring"""
        return {
            'current_equity': self.current_equity,
            'daily_pnl': self.daily_pnl,
            'weekly_pnl': self.weekly_pnl,
            'active_positions': len(self.positions),
            'max_positions': self.max_positions,
            'is_trading_halted': self.is_trading_halted,
            'sector_breakdown': self.sector_positions.copy(),
            'risk_metrics': self.risk_metrics.copy(),
            'daily_return': self.daily_pnl / self.current_equity if self.current_equity > 0 else 0,
            'weekly_return': self.weekly_pnl / self.current_equity if self.current_equity > 0 else 0,
            'weekly_target': 0.05,  # 5% weekly target
            'progress_to_target': (self.weekly_pnl / self.current_equity) / 0.05 if self.current_equity > 0 else 0
        }

# Enhanced RiskManager for 5% weekly ROI targets is now ready!
# Key features: 0.5% risk per trade, regime-aware scaling, sector limits, loss breakers

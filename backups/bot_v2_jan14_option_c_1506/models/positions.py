"""
Data models: ShortCyclePosition
Extracted from traders/short_cycle_trader.py
"""

import datetime as dt
import pytz
import pandas as pd
from typing import Optional
from dataclasses import dataclass

from bot_v2.models.enums import PositionStatus
from bot_v2.models.signals import AISignal


@dataclass
class ShortCyclePosition:
    """Position tracking for short-cycle system"""
    symbol: str
    entry_date: dt.date
    exit_date: dt.date  # Scheduled exit date (D+1)
    entry_price: float
    position_size_shares: int
    position_size_dollars: float
    stop_price: float
    target_price: Optional[float]
    status: PositionStatus
    ai_signal: AISignal
    
    # Metadata (NEW NOV 12: sector tracking for diversification)
    sector: Optional[str] = None  # Stock sector (Energy, Tech, etc.)
    
    # Timestamp tracking (NEW - for accurate D+1 calculation)
    entry_timestamp: Optional[dt.datetime] = None  # When order was filled by broker
    filled_at: Optional[dt.datetime] = None  # Alpaca fill timestamp
    order_id: Optional[str] = None  # Broker order ID for tracking
    
    # Exit tracking
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None
    exit_timestamp: Optional[dt.datetime] = None  # When position was actually exited
    realized_pnl: Optional[float] = None
    hold_days: Optional[int] = None
    
    # Risk tracking
    max_risk_dollars: float = 0.0
    current_price: Optional[float] = None
    unrealized_pnl: Optional[float] = None
    
    # Trailing stop tracking (NEW)
    trailing_stop_enabled: bool = False
    trailing_stop_price: Optional[float] = None
    highest_price_since_entry: Optional[float] = None
    trailing_stop_activated_at: Optional[dt.datetime] = None
    
    @property
    def days_held(self) -> int:
        """Calculate days held since entry"""
        if self.exit_timestamp:
            return (self.exit_timestamp.date() - self.entry_date).days
        return (dt.date.today() - self.entry_date).days
    
    def update_current_price(self, price: float):
        """Update current price and unrealized P&L"""
        self.current_price = price
        if self.status == PositionStatus.ENTERED:
            self.unrealized_pnl = (price - self.entry_price) * self.position_size_shares
    
    def should_force_exit(self, current_date: dt.date) -> bool:
        """Check if position should be force-exited due to D+1 rule"""
        return current_date >= self.exit_date
    
    def is_d1_eligible(self, current_datetime: dt.datetime, cash_account_mode: bool = False) -> bool:
        """
        Check if position is eligible for exit on current trading day.
        
        Rules:
        - Margin/PDT Account: If bought before close on Day T, eligible for exit on Day T+1 (next trading day)
        - Cash Account: Can exit same day (no PDT restrictions)
        
        Args:
            current_datetime: Current date/time to check
            cash_account_mode: If True, allow same-day exits (no PDT restrictions)
        
        Returns: True if eligible for exit today
        """
        # CASH ACCOUNT MODE: Always eligible to exit (no PDT restrictions)
        if cash_account_mode:
            return True
        
        # MARGIN ACCOUNT MODE: Original PDT-compliant logic
        if not self.entry_timestamp and not self.filled_at:
            # Fallback to old date-based logic if no timestamp
            return current_datetime.date() >= self.exit_date
        
        # Use actual fill timestamp
        fill_time = self.filled_at if self.filled_at else self.entry_timestamp
        
        # Check if we're on a different trading day
        # (Simple implementation - could enhance with market calendar)
        fill_date = fill_time.date()
        current_date = current_datetime.date()
        
        # INTRADAY MODE: If cash account, no D+1 requirement - can exit same day
        # If filled today, can exit immediately based on profit/loss targets
        if cash_account_mode:
            return True  # Always eligible in cash account mode
        
        # Legacy mode: If filled before close on Day T, eligible on Day T+1
        return current_date > fill_date
    
    def should_smart_exit(self, current_date: dt.date, current_price: float, current_time: dt.datetime = None, cash_account_mode: bool = False, market_data: Optional[pd.DataFrame] = None) -> tuple[bool, str]:
        """
        ENHANCED Smart exit logic optimized for mean reversion RSI (Nov 22, 2025)
        
        Strategy:
        - PRIMARY EXIT: RSI > 50 (neutral) - mean reversion complete
        - SECONDARY EXIT: Profit target >= 2%
        - EMERGENCY EXIT: Stop loss <= -2%
        - FRIDAY EXIT: Force exit at 3:45 PM (prevent weekend holding)
        
        Args:
            current_date: Current date
            current_price: Current stock price
            current_time: Current datetime (defaults to now)
            cash_account_mode: IGNORED - always use margin account rules (D+1 minimum hold)
            market_data: Current market data DataFrame with OHLCV (for RSI calculation)
        
        Returns: (should_exit, reason)
        """
        if current_time is None:
            current_time = dt.datetime.now(pytz.UTC)
        
        # INTRADAY MODE: Check if eligible for exit (cash account allows same-day)
        if not self.is_d1_eligible(current_time, cash_account_mode):
            return False, "NOT_ELIGIBLE_YET"
        
        # Past exit date - force exit immediately (should not happen in intraday mode)
        if current_date > self.exit_date:
            return True, "FORCED_EXIT_LATE"
        
        # Validate price data
        if current_price is None or self.entry_price is None:
            return False, "INVALID_PRICE_DATA"
        
        # Calculate profit/loss percentage
        pnl_pct = (current_price - self.entry_price) / self.entry_price
        
        # Market time calculation
        market_hour = current_time.hour
        market_minute = current_time.minute
        time_fraction = market_hour + market_minute / 60.0
        
        # PDT PROTECTION: Monday-Thursday same-day exits ONLY for TRUE EMERGENCIES
        # Reserve emergency exits for stop loss, not small profits (hold for D+1)
        is_same_day = (self.entry_date == current_date)
        is_friday = current_time.weekday() == 4
        is_mon_thu = current_time.weekday() in [0, 1, 2, 3]
        
        # EMERGENCY RULES (HIGHEST PRIORITY - CHECK FIRST)
        # Stop Loss: Down >=3% any time (increased from 2% for more wiggle room)
        # For $50 position: -3% = -$1.50 (previously -2% = -$1.00)
        if pnl_pct <= -0.03:
            return True, "EMERGENCY_STOP_LOSS"
        
        # Mon-Thu Same-Day: Block non-emergency exits (hold for D+1)
        if is_same_day and is_mon_thu:
            # Allow emergency stop loss (already checked above)
            # Block all other exits (small profits, RSI exits, etc.)
            # Position should hold overnight for D+1 strategy
            if pnl_pct > -0.03:  # Not emergency stop loss (updated to -3%)
                return False, f"SAME_DAY_MON_THU_HOLD_D+1"
        
        # MEAN REVERSION RSI EXIT STRATEGY (Nov 22, 2025)
        # Optimization Test #2852: 19.17% weekly, 62.7% win rate
        
        # PRIMARY EXIT: RSI neutral (mean reversion complete)
        if market_data is not None and len(market_data) >= 7:
            try:
                from core.indicators import calculate_rsi
                df_with_rsi = calculate_rsi(market_data, window=7)
                current_rsi = df_with_rsi['rsi'].iloc[-1]
                
                # Exit when RSI crosses back to neutral (mean reversion complete)
                if current_rsi > 50:
                    return True, f"RSI_NEUTRAL_{current_rsi:.1f}"
            except Exception as e:
                # If RSI calculation fails, fall back to profit target only
                pass
        
        # SECONDARY EXIT: Profit target >= 2%
        if pnl_pct >= 0.02:
            return True, "PROFIT_TARGET_2PCT"
        
        # FRIDAY WEEKEND EXIT LOGIC (prevent weekend holding)
        # CRITICAL: Always force exit on Friday regardless of entry date or PDT rules
        if current_time.weekday() == 4:  # Friday
            # Force exit all positions at 3:45 PM to avoid weekend risk
            if time_fraction >= 15.75:  # 3:45 PM or later
                return True, "FRIDAY_FORCE_EXIT_WEEKEND_RISK"
        
        # OPENING PATIENCE: Don't exit losing positions in first 30 min (avoid volatility)
        # Let gaps recover before making exit decisions
        if time_fraction < 10.0:  # Before 10:00 AM
            # Exception: Allow profit-taking and emergency stops
            if pnl_pct < 0 and pnl_pct > -0.02:  # Losing but not emergency
                return False, "OPENING_PATIENCE_HOLD"
        
        return False, "WAITING_FOR_SIGNAL"
    
    def is_stopped_out(self, current_price: float) -> bool:
        """Check if position should be stopped out"""
        if self.status != PositionStatus.ENTERED:
            return False
        # Handle None stop_price or current_price gracefully
        if self.stop_price is None or current_price is None:
            return False
        return current_price <= self.stop_price
    
    def update_trailing_stop(self, current_price: float, trailing_stop_pct: float = 0.025, logger=None) -> tuple[bool, Optional[str]]:
        """
        Update trailing stop for winners and check if stop hit
        OPTIMIZED (Nov 22, 2025): Based on parameter optimization results
        
        Strategy:
        - Activate trailing stop when position is up >3% (was 1%)
        - Trail stop 2.5% below highest price (was 1.5%)
        - Adaptive distance 1.5-3.0% based on momentum (was 1.2-1.8%)
        - Once activated, stop follows price up but never down
        
        Args:
            current_price: Current market price
            trailing_stop_pct: Trailing distance (default 2.5%, optimized)
            logger: Optional logger for output
            
        Returns:
            (should_exit, reason) - True if trailing stop hit
        """
        if self.status != PositionStatus.ENTERED or current_price is None:
            return False, None
        
        # Calculate current P&L percentage
        pnl_pct = (current_price - self.entry_price) / self.entry_price
        
        # Activate trailing stop if up >3% and not yet activated (optimized from 1%)
        if not self.trailing_stop_enabled and pnl_pct >= 0.03:
            self.trailing_stop_enabled = True
            self.highest_price_since_entry = current_price
            # Start with base trailing distance (2.5% optimized)
            self.trailing_stop_price = current_price * (1 - trailing_stop_pct)
            self.trailing_stop_activated_at = dt.datetime.now(pytz.UTC)
            if logger:
                logger.info(
                    f"🎯 {self.symbol}: Trailing stop ACTIVATED at ${current_price:.2f} "
                    f"(+{pnl_pct*100:.1f}%), stop=${self.trailing_stop_price:.2f}"
                )
            return False, None
        
        # Update trailing stop if already activated
        if self.trailing_stop_enabled:
            # OPTIMIZED: Calculate momentum-adaptive trailing distance
            # Use 5-min momentum proxy: compare current vs highest price
            momentum_pct = (current_price - self.highest_price_since_entry) / self.highest_price_since_entry
            
            # Adaptive trailing distance based on momentum (OPTIMIZED ranges)
            if momentum_pct > 0.005:  # Strong momentum up (>0.5% from peak)
                adaptive_trail_pct = 0.025  # 2.5% - wider trail (was 1.8%)
            elif momentum_pct < -0.003:  # Weakening (>0.3% below peak)
                adaptive_trail_pct = 0.015  # 1.5% - tighter trail (was 1.2%)
            else:
                adaptive_trail_pct = 0.025  # 2.5% - standard trail (was 1.5%)
            
            # Update highest price if new high reached
            if current_price > self.highest_price_since_entry:
                self.highest_price_since_entry = current_price
                new_stop = current_price * (1 - adaptive_trail_pct)
                
                # Only move stop up, never down
                if new_stop > self.trailing_stop_price:
                    old_stop = self.trailing_stop_price
                    self.trailing_stop_price = new_stop
                    if logger:
                        logger.info(
                            f"📈 {self.symbol}: Trailing stop raised ${old_stop:.2f} → ${new_stop:.2f} "
                            f"(price=${current_price:.2f}, trail={adaptive_trail_pct*100:.1f}%, +{pnl_pct*100:.1f}%)"
                        )
            
            # Check if trailing stop hit
            if current_price <= self.trailing_stop_price:
                locked_profit = self.trailing_stop_price - self.entry_price
                locked_profit_pct = locked_profit / self.entry_price * 100
                if logger:
                    logger.info(
                        f"🛑 {self.symbol}: Trailing stop HIT at ${current_price:.2f} "
                        f"(stop=${self.trailing_stop_price:.2f}, locked profit: +{locked_profit_pct:.1f}%)"
                    )
                return True, f"TRAILING_STOP (profit locked: +{locked_profit_pct:.1f}%)"
        
        return False, None
    
    def calculate_realized_pnl(self, exit_price: float) -> float:
        """Calculate realized P&L on exit"""
        return (exit_price - self.entry_price) * self.position_size_shares



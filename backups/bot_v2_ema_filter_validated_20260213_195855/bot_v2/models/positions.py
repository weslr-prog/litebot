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
        """Check if position should be force-exited (max hold days exceeded)"""
        # No longer D+1 forced. Only force if well past max hold (safety net)
        max_hold = 10  # 10 trading days absolute max
        days_held = (current_date - self.entry_date).days
        return days_held >= max_hold
    
    def is_d1_eligible(self, current_datetime: dt.datetime, cash_account_mode: bool = False) -> bool:
        """
        Check if position is eligible for exit.
        D+1 restriction REMOVED - positions can exit any time based on signals.
        Only enforce a minimum 1-hour hold to avoid wash sales / whipsaws.
        
        Returns: True if eligible for exit
        """
        # Always eligible - no D+1 restriction
        # Just enforce minimum 1 hour hold to avoid whipsaw exits
        fill_time = self.filled_at if self.filled_at else self.entry_timestamp
        if fill_time:
            elapsed = current_datetime - fill_time
            if elapsed.total_seconds() < 3600:  # 1 hour minimum hold
                return False
        return True
    
    def should_smart_exit(self, current_date: dt.date, current_price: float, current_time: dt.datetime = None, cash_account_mode: bool = False, market_data: Optional[pd.DataFrame] = None) -> tuple[bool, str]:
        """
        Smart exit logic - WEEKLY SWING STRATEGY (Feb 11, 2026 rewrite)
        
        Goal: ~5% weekly returns. Hold 2-5 days including weekends if confidence is good.
        No D+1 forced exits. No same-day blocks. Let winners run, cut losers.
        
        Exit hierarchy:
        1. EMERGENCY STOP: -2% hard stop (protect capital)
        2. TRAILING STOP: Lock in gains on runners (+3% activates)
        3. PROFIT TARGET: +4% take profit (if no trailing stop active)
        4. RSI EXHAUSTION: RSI > 80 = overbought exhaustion (take profit)
        5. TIME STOP: 5 trading days max hold (safety net)
        6. FRIDAY LOSERS: Exit positions down >2% at 3:30 PM Friday (optional weekend risk mgmt)
        
        Returns: (should_exit, reason)
        """
        if current_time is None:
            current_time = dt.datetime.now(pytz.UTC)
        
        # Check minimum hold time (1 hour to avoid whipsaws)
        if not self.is_d1_eligible(current_time, cash_account_mode):
            return False, "MIN_HOLD_WAIT"
        
        # Validate price data
        if current_price is None or self.entry_price is None:
            return False, "INVALID_PRICE_DATA"
        
        # Calculate profit/loss percentage
        pnl_pct = (current_price - self.entry_price) / self.entry_price
        
        # Market time calculation
        market_hour = current_time.hour
        market_minute = current_time.minute
        time_fraction = market_hour + market_minute / 60.0
        days_held = (current_date - self.entry_date).days
        
        # === 1. EMERGENCY STOP LOSS: -4% hard cut (protect capital) ===
        # SWING FIX Feb 13: Widened from -2% to -4% to survive normal mid-cap pullbacks
        # Data showed 88% of losses stopped out within 24h at -2% (noise stop)
        if pnl_pct <= -0.04:
            return True, f"STOP_LOSS_{pnl_pct*100:.1f}pct"
        
        # === 2. OPENING PATIENCE: Don't exit in first 30 min (avoid gap volatility) ===
        if time_fraction < 10.0 and pnl_pct > -0.04:
            if pnl_pct < 0:
                return False, "OPENING_PATIENCE_HOLD"
        
        # === 3. LET WINNERS RUN via trailing stop (handled by update_trailing_stop) ===
        # Trailing stop is checked separately - if active, it manages exit
        if hasattr(self, 'trailing_stop_enabled') and self.trailing_stop_enabled:
            # Trailing stop is active - don't interfere, let it manage
            return False, "TRAILING_STOP_ACTIVE"
        
        # === 4. PROFIT TARGET: +6% take profit ===
        # SWING FIX Feb 13: Raised from 4% to 6% to let winners develop
        if pnl_pct >= 0.06:
            return True, f"PROFIT_TARGET_{pnl_pct*100:.1f}pct"
        
        # === 5. RSI EXHAUSTION EXIT (overbought = momentum exhausted) ===
        # SWING FIX Feb 13: Only after 2+ days AND RSI > 80 (was firing too early)
        # RSI exits were #1 cause of losses (23 of 42 losses)
        if market_data is not None and len(market_data) >= 7:
            try:
                from core.indicators import calculate_rsi
                df_with_rsi = calculate_rsi(market_data, window=7)
                current_rsi = df_with_rsi['rsi'].iloc[-1]
                
                # RSI > 85 with profit = extreme overbought, take profit
                if current_rsi > 85 and pnl_pct > 0.01:
                    return True, f"RSI_OVERBOUGHT_{current_rsi:.0f}_profit_{pnl_pct*100:.1f}pct"
                
                # RSI > 80 after 3+ days with meaningful profit = fading momentum
                if current_rsi > 80 and days_held >= 3 and pnl_pct > 0.01:
                    return True, f"RSI_FADING_{current_rsi:.0f}_day{days_held}"
            except Exception:
                pass
        
        # === 6. TIME STOP: 5 trading days max (safety net) ===
        if days_held >= 7:  # ~5 trading days
            if pnl_pct > 0:
                return True, f"TIME_STOP_PROFIT_{pnl_pct*100:.1f}pct_day{days_held}"
            elif pnl_pct > -0.01:
                return True, f"TIME_STOP_BREAKEVEN_day{days_held}"
            # Deep loss after 5 days - exit to free capital
            return True, f"TIME_STOP_CUT_LOSS_{pnl_pct*100:.1f}pct_day{days_held}"
        
        # === 7. FRIDAY LOSER PROTECTION (optional - only big losers) ===
        if current_time.weekday() == 4:  # Friday
            # Only exit positions that are losing >3% at 3:30 PM
            # SWING FIX Feb 13: Widened from 2% to 3% to match new stop structure
            if time_fraction >= 15.5 and pnl_pct <= -0.03:
                return True, f"FRIDAY_CUT_LOSER_{pnl_pct*100:.1f}pct"
        
        # === 8. QUICK PROFIT on weak signals (score < 0.65) ===
        # SWING FIX Feb 13: Raised required profit from 2% to 4%, tightened confidence check
        signal_confidence = getattr(self, 'ai_signal', None)
        if signal_confidence and hasattr(signal_confidence, 'confidence'):
            if signal_confidence.confidence < 0.65 and pnl_pct >= 0.04:
                return True, f"QUICK_PROFIT_LOW_CONF_{pnl_pct*100:.1f}pct"
        
        return False, "HOLDING"
    
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



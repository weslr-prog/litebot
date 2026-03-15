"""
AI Exit Manager - Sophisticated exit logic and coordination
Extracted from ShortCycleTrader for modular architecture
"""
import logging
import datetime as dt
import pytz
import time
from typing import List, Optional, Tuple, Any


class AIExitManager:
    """
    Manages position exits with sophisticated timing and risk management.
    
    WEEKLY SWING STRATEGY (Feb 11, 2026 rewrite):
    - No D+1 forced exits
    - No same-day hold blocks
    - Exit based on stop loss, trailing stop, profit target, and time stop
    - Let winners run, cut losers at -2%
    - Hold 2-5 days including weekends if trade is working
    """
    
    def __init__(self, config, stop_manager, order_manager, earnings_calendar=None, 
                 pattern_recognizer=None, pattern_tracker=None, logger: Optional[logging.Logger] = None):
        """
        Initialize exit manager
        
        Args:
            config: ShortCycleConfig with trading parameters
            stop_manager: AIStopLossManager for stop calculations
            order_manager: AIOrderManager for trade execution
            earnings_calendar: Optional earnings protection
            pattern_recognizer: Optional pattern-based exit timing
            pattern_tracker: Optional position pattern tracking
            logger: Optional logger instance
        """
        self.config = config
        self.stop_manager = stop_manager
        self.order_manager = order_manager
        self.earnings_calendar = earnings_calendar
        self.pattern_recognizer = pattern_recognizer
        self.pattern_tracker = pattern_tracker
        self.logger = logger or logging.getLogger(__name__)
    
    def should_exit(self, position) -> Tuple[bool, Optional[str]]:
        """
        Check if a position should be exited now.
        
        Args:
            position: ShortCyclePosition to check
            
        Returns:
            (should_exit: bool, reason: str or None)
        """
        from ..models.positions import PositionStatus
        import datetime as dt
        
        if position.status != PositionStatus.ENTERED:
            return (False, None)
        
        current_price = position.current_price if hasattr(position, 'current_price') and position.current_price else position.entry_price
        
        # Check stop loss (ALWAYS highest priority - hard exit)
        if current_price <= position.stop_price:
            pnl_pct = ((current_price - position.entry_price) / position.entry_price) * 100
            return (True, f"Stop loss hit: ${current_price:.2f} <= ${position.stop_price:.2f} ({pnl_pct:+.1f}%)")
        
        # Check trailing stop (PRIORITY over profit targets - enables runners)
        # If trailing stop is active, let it manage the exit (position can run past profit target)
        if hasattr(position, 'trailing_stop_enabled') and position.trailing_stop_enabled:
            if current_price <= position.trailing_stop_price:
                pnl_pct = ((current_price - position.entry_price) / position.entry_price) * 100
                return (True, f"Trailing stop hit: ${current_price:.2f} <= ${position.trailing_stop_price:.2f} ({pnl_pct:+.1f}%)")
            # Trailing stop active but not hit - let position run
            return (False, None)
        
        # Check profit target (ONLY if trailing stop not active)
        pnl_pct = ((current_price - position.entry_price) / position.entry_price) * 100
        if pnl_pct >= (self.config.profit_target_pct * 100):
            # Check if we should activate trailing stop instead of immediate exit
            if pnl_pct >= (self.config.trailing_trigger_pct * 100):
                # Profit target hit AND trailing trigger reached
                # Don't force exit - trailing stop will activate and manage the runner
                return (False, None)
            else:
                # Profit target hit but below trailing trigger
                return (True, f"Profit target hit: {pnl_pct:+.1f}% >= {self.config.profit_target_pct * 100:.1f}%")
        
        # Time stop: max hold days exceeded (configurable, default 5 trading days / ~7 calendar)
        today = dt.date.today()
        days_held = (today - position.entry_date).days
        max_hold = getattr(self.config, 'max_hold_days', 5)
        if days_held >= max_hold + 2:  # Calendar days ~= trading days + weekends
            return (True, f"Max hold exceeded: {days_held} days, P&L: {pnl_pct:+.1f}%")
        
        # Check time-based exit (3:45 PM hard close - safety net only)
        now = dt.datetime.now(pytz.timezone('America/New_York'))
        exit_hour, exit_min = map(int, self.config.exit_time.split(':'))
        exit_time = now.replace(hour=exit_hour, minute=exit_min, second=0, microsecond=0)
        
        # Only time-exit on Friday for big losers (>2% down)
        if now >= exit_time and now.weekday() == 4 and pnl_pct < -2.0:
            return (True, f"Friday EOD cut loser: {pnl_pct:+.1f}%")
        
        # Check earnings
        if self.earnings_calendar and self.earnings_calendar.should_exit_before_earnings(position.symbol):
            return (True, "Earnings protection exit")
        
        return (False, None)
    
    def process_strategic_d1_exits(self, positions: List[Any], data_loader) -> int:
        """
        Process position exits based on signal conditions (no longer D+1 specific).
        Checks all active positions for exit signals.
        
        Args:
            positions: List of ShortCyclePosition objects
            data_loader: Data loader for market data
            
        Returns:
            Number of exits processed
        """
        from ..models.positions import PositionStatus
        
        positions_to_exit = []
        today = dt.date.today()
        current_time = dt.datetime.now(pytz.UTC)
        
        for position in positions:
            if position.status != PositionStatus.ENTERED:
                continue
            
            # CRITICAL: Earnings Protection - Force exit before earnings
            if self.earnings_calendar and self.earnings_calendar.should_exit_before_earnings(position.symbol):
                earnings_info = self.earnings_calendar.get_earnings_info(position.symbol)
                positions_to_exit.append({
                    'position': position,
                    'priority': 'EARNINGS_URGENT',
                    'entry_date': position.entry_date,
                    'target_exit': today,
                    'days_held': (today - position.entry_date).days,
                    'reason': f"Earnings protection: {earnings_info['status']}"
                })
                self.logger.warning(f"⚠️ {position.symbol}: EARNINGS EXIT - {earnings_info['status']}")
                continue
            
            # Check max hold time stop (safety net: 10 calendar days)
            days_held = (today - position.entry_date).days
            if days_held >= 10:
                positions_to_exit.append({
                    'position': position,
                    'priority': 'TIME_STOP',
                    'entry_date': position.entry_date,
                    'target_exit': today,
                    'days_held': days_held,
                    'reason': f"Max hold time exceeded ({days_held} days)"
                })
                self.logger.info(f"⏰ {position.symbol}: Time stop - held {days_held} days")
        
        if not positions_to_exit:
            return 0
        
        # Strategic exit execution
        self.logger.info(f"🚀 Processing {len(positions_to_exit)} exit signals")
        
        positions_to_exit.sort(key=lambda x: (
            0 if x['priority'] == 'EARNINGS_URGENT' else 1,
            -x['days_held'],
            x['position'].symbol
        ))
        
        exit_count = 0
        for i, exit_info in enumerate(positions_to_exit):
            position = exit_info['position']
            
            try:
                if i > 0:
                    delay = min(60, 30 + (i * 10))
                    self.logger.info(f"⏳ Exit delay: {delay}s before {position.symbol}")
                    time.sleep(delay)
                
                success = self._execute_strategic_exit(position, i+1, data_loader)
                
                if success:
                    exit_count += 1
                    self.logger.info(f"✅ {position.symbol}: Exit completed ({exit_count}/{len(positions_to_exit)})")
                else:
                    self.logger.warning(f"⚠️ {position.symbol}: Exit failed, will retry")
                    
            except Exception as e:
                self.logger.error(f"❌ {position.symbol}: Exit error: {e}")
        
        self.logger.info(f"Exit sequence complete: {exit_count}/{len(positions_to_exit)} successful")
        return exit_count
    
    def _execute_strategic_exit(self, position, exit_sequence_num: int, data_loader) -> bool:
        """Execute a single position exit using smart zone-based strategy"""
        from ..models.positions import PositionStatus
        
        try:
            today = dt.date.today()
            current_time = dt.datetime.now(pytz.UTC)
            
            # No same-day block - exits allowed any time based on signals
            # Only enforce minimum 1-hour hold (handled by is_d1_eligible in position model)
            
            # Get current market price
            current_price = self._get_current_price(position, data_loader)
            if not current_price:
                self.logger.error(f"❌ {position.symbol}: Cannot get current price for exit")
                return False
            
            # Calculate P&L for logging
            unrealized_pnl = (current_price - position.entry_price) * position.position_size_shares
            unrealized_pnl_pct = ((current_price - position.entry_price) / position.entry_price) * 100
            
            # Check trailing stop for profit protection (>3% gains)
            trailing_stop_hit, trailing_reason = position.update_trailing_stop(current_price, logger=self.logger)
            if trailing_stop_hit:
                self.logger.info(f"🛑 {position.symbol}: Trailing stop triggered")
                self.logger.info(f"💰 {position.symbol}: P&L: ${unrealized_pnl:.2f} ({unrealized_pnl_pct:+.2f}%) | {trailing_reason}")
                return self.exit_position(position, current_price, trailing_reason, data_loader)
            
            # Use should_smart_exit() to determine optimal exit timing
            cash_mode = getattr(self.config, 'cash_account_mode', False)
            
            # Fetch recent market data for RSI calculation
            market_data = None
            try:
                market_data = data_loader.get_historical_data(position.symbol, days=10)
            except Exception as e:
                self.logger.debug(f"Could not fetch market data for {position.symbol}: {e}")
            
            should_exit, zone_exit_reason = position.should_smart_exit(
                today, current_price, current_time, 
                cash_account_mode=cash_mode, market_data=market_data
            )
            
            if should_exit:
                self.logger.info(f"📤 {position.symbol}: Smart exit triggered")
                self.logger.info(f"💰 {position.symbol}: P&L: ${unrealized_pnl:.2f} ({unrealized_pnl_pct:+.2f}%) | Zone: {zone_exit_reason}")
                return self.exit_position(position, current_price, zone_exit_reason, data_loader)
            else:
                self.logger.info(f"⏳ {position.symbol}: Zone strategy says hold (P&L: ${unrealized_pnl:.2f}, {unrealized_pnl_pct:+.2f}%)")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ {position.symbol}: Strategic exit execution error: {e}")
            return False
    
    def check_trailing_stop(self, position, current_price: float) -> Optional[Tuple[float, str]]:
        """
        Update trailing stop for position and check if it should be triggered.
        
        Args:
            position: ShortCyclePosition object
            current_price: Current market price
            
        Returns:
            Tuple of (exit_price, exit_reason) if stop triggered, None otherwise
        """
        try:
            # Track highest price since entry
            if position.highest_price_since_entry is None:
                position.highest_price_since_entry = max(current_price, position.entry_price)
            else:
                position.highest_price_since_entry = max(position.highest_price_since_entry, current_price)
            
            # Calculate current profit percentage
            profit_pct = (current_price - position.entry_price) / position.entry_price
            
            # Check if we should activate trailing stop
            if not position.trailing_stop_enabled:
                if profit_pct >= self.config.trailing_trigger_pct:
                    # Activate trailing stop
                    position.trailing_stop_enabled = True
                    position.trailing_stop_activated_at = dt.datetime.now(pytz.UTC)
                    
                    # Set initial trailing stop price
                    min_profit_price = position.entry_price * (1 + self.config.trailing_min_profit_pct)
                    trailing_price = current_price * (1 - self.config.trailing_distance_pct)
                    position.trailing_stop_price = max(trailing_price, min_profit_price)
                    
                    self.logger.info(
                        f"🎯 {position.symbol}: Trailing stop ACTIVATED at ${current_price:.2f} "
                        f"(+{profit_pct*100:.1f}%) | Stop: ${position.trailing_stop_price:.2f}"
                    )
                    return None
            
            # If trailing stop is active, update it
            if position.trailing_stop_enabled:
                # Calculate new trailing stop price
                new_trail_price = position.highest_price_since_entry * (1 - self.config.trailing_distance_pct)
                
                # Ensure minimum profit lock
                min_profit_price = position.entry_price * (1 + self.config.trailing_min_profit_pct)
                new_trail_price = max(new_trail_price, min_profit_price)
                
                # Only move stop up, never down
                if new_trail_price > position.trailing_stop_price:
                    old_stop = position.trailing_stop_price
                    position.trailing_stop_price = new_trail_price
                    self.logger.debug(
                        f"📈 {position.symbol}: Trailing stop raised: ${old_stop:.2f} → ${new_trail_price:.2f} "
                        f"(Current: ${current_price:.2f}, High: ${position.highest_price_since_entry:.2f})"
                    )
                
                # Check if current price hit trailing stop
                if current_price <= position.trailing_stop_price:
                    locked_profit_pct = (position.trailing_stop_price - position.entry_price) / position.entry_price
                    self.logger.info(
                        f"✅ {position.symbol}: TRAILING STOP HIT! "
                        f"Entry: ${position.entry_price:.2f} → Exit: ${current_price:.2f} "
                        f"(Locked profit: +{locked_profit_pct*100:.1f}%, Peak: ${position.highest_price_since_entry:.2f})"
                    )
                    return (current_price, f"TRAILING_STOP_+{locked_profit_pct*100:.1f}%")
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error updating trailing stop for {position.symbol}: {e}")
            return None
    
    def exit_position(self, position, exit_price: float, reason: str, data_loader=None, portfolio_manager=None) -> bool:
        """
        Exit a position and update tracking.
        
        Args:
            position: ShortCyclePosition to exit
            exit_price: Current market price
            reason: Exit reason string
            data_loader: Optional data loader
            portfolio_manager: Optional portfolio manager for PDT tracking
            
        Returns:
            True if exit succeeded, False otherwise
        """
        from ..models.positions import PositionStatus
        
        try:
            # Check if this is a same-day exit (emergency exit, uses PDT slot)
            is_same_day_exit = (position.entry_date == dt.date.today())
            
            # Execute sell order via order manager
            success = self.order_manager.execute_sell_order(position, exit_price, reason)
            
            if not success:
                return False
            
            # Track emergency exit if same-day and portfolio manager available
            if is_same_day_exit and portfolio_manager:
                portfolio_manager.increment_emergency_exit_counter()
            
            # Update position status
            position.exit_price = exit_price
            position.exit_reason = reason
            position.exit_timestamp = dt.datetime.now(pytz.UTC)
            position.realized_pnl = position.calculate_realized_pnl(exit_price)
            position.hold_days = (dt.date.today() - position.entry_date).days
            
            if reason == "STOP_LOSS":
                position.status = PositionStatus.STOPPED_OUT
            else:
                position.status = PositionStatus.EXITED
            
            self.logger.info(f"🔄 {position.symbol}: Exited @ ${exit_price:.2f}, "
                           f"P&L: ${position.realized_pnl:.2f}, Reason: {reason}")
            
            # Log exit explanation
            self.order_manager.log_exit_explanation(position)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error exiting position {position.symbol}: {e}")
            return False
    
    def force_close_all_positions(self, positions: List[Any], data_loader, reason: str = "FORCE_EXIT") -> int:
        """
        Force close all open positions immediately (Friday 3:45 PM cleanup).
        
        Args:
            positions: List of all positions
            data_loader: Data loader for current prices
            reason: Exit reason
            
        Returns:
            Number of positions closed
        """
        from ..models.positions import PositionStatus
        
        try:
            active_positions = [p for p in positions if p.status == PositionStatus.ENTERED]
            
            if not active_positions:
                self.logger.info("✅ No positions to force close")
                return 0
            
            self.logger.warning(f"🚨 Force closing {len(active_positions)} positions: {reason}")
            
            closed_count = 0
            for position in active_positions:
                try:
                    current_price = self._get_current_price(position, data_loader)
                    if not current_price:
                        self.logger.error(f"❌ Cannot get price for {position.symbol}, skipping force exit")
                        continue
                    
                    if self.exit_position(position, current_price, reason, data_loader):
                        closed_count += 1
                    
                except Exception as e:
                    self.logger.error(f"❌ Error force closing {position.symbol}: {e}")
            
            self.logger.info(f"✅ Force close complete - {closed_count}/{len(active_positions)} positions closed")
            return closed_count
            
        except Exception as e:
            self.logger.error(f"Error in force close all positions: {e}")
            return 0
    
    def process_friday_staggered_exits(self, positions: List[Any], data_loader) -> int:
        """
        Issue 2.3: Friday staggered exits to capture EOW momentum
        
        Friday positions should exit in tiers:
        - 50% at open (lock in profits)
        - 25% at noon (capture morning momentum)
        - 25% at 3:00 PM (hold for potential EOW pop)
        
        Args:
            positions: List of ShortCyclePosition objects
            data_loader: Data loader for current prices
            
        Returns:
            Number of positions (or partial positions) exited
        """
        from ..models.positions import PositionStatus
        
        now = dt.datetime.now(pytz.timezone('America/New_York'))
        
        # Only run on Fridays
        if now.weekday() != 4:
            return 0
        
        exit_count = 0
        active_positions = [p for p in positions if p.status == PositionStatus.ENTERED]
        
        if not active_positions:
            return 0
        
        # Determine current exit tier based on time
        market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
        tier1_start = now.replace(hour=9, minute=35, second=0, microsecond=0)  # 9:35 AM
        tier1_end = now.replace(hour=10, minute=0, second=0, microsecond=0)    # 10:00 AM
        tier2_start = now.replace(hour=12, minute=0, second=0, microsecond=0)  # 12:00 PM
        tier2_end = now.replace(hour=12, minute=30, second=0, microsecond=0)   # 12:30 PM
        tier3_start = now.replace(hour=15, minute=0, second=0, microsecond=0)  # 3:00 PM
        tier3_end = now.replace(hour=15, minute=30, second=0, microsecond=0)   # 3:30 PM
        
        current_tier = None
        if tier1_start <= now < tier1_end:
            current_tier = 1
            exit_pct = 0.50  # Exit 50% at open
        elif tier2_start <= now < tier2_end:
            current_tier = 2
            exit_pct = 0.25  # Exit 25% at noon
        elif tier3_start <= now < tier3_end:
            current_tier = 3
            exit_pct = 0.25  # Exit 25% at 3PM
        
        if not current_tier:
            return 0  # Not in an exit tier window
        
        self.logger.info(f"📅 Friday Tier {current_tier} Exit Window ({exit_pct*100:.0f}% target)")
        
        for position in active_positions:
            try:
                # Track which tiers have been processed for this position
                if not hasattr(position, 'friday_exit_tiers_done'):
                    position.friday_exit_tiers_done = set()
                
                # Skip if we already processed this tier
                if current_tier in position.friday_exit_tiers_done:
                    continue
                
                current_price = self._get_current_price(position, data_loader)
                if not current_price:
                    continue
                
                # Calculate unrealized P&L
                pnl_pct = ((current_price - position.entry_price) / position.entry_price) * 100
                
                # For tier 1, always exit (lock in regardless of P&L)
                # For tier 2-3, skip if position is strongly positive (let it run)
                if current_tier > 1 and pnl_pct > 2.0:
                    self.logger.info(
                        f"📈 {position.symbol}: Strong gain ({pnl_pct:+.1f}%), "
                        f"skipping Tier {current_tier} exit - letting run"
                    )
                    position.friday_exit_tiers_done.add(current_tier)
                    continue
                
                # Calculate shares to exit
                shares_to_exit = int(position.position_size_shares * exit_pct)
                if shares_to_exit < 1:
                    shares_to_exit = 1  # Minimum 1 share
                
                # If this is the final tier or we'd have <1 share left, exit all
                remaining_shares = position.position_size_shares - shares_to_exit
                if current_tier == 3 or remaining_shares < 1:
                    shares_to_exit = position.position_size_shares
                
                reason = f"Friday Tier {current_tier} exit ({exit_pct*100:.0f}%)"
                
                if shares_to_exit >= position.position_size_shares:
                    # Full exit
                    if self.exit_position(position, current_price, reason, data_loader):
                        exit_count += 1
                        self.logger.info(
                            f"✅ {position.symbol}: Friday Tier {current_tier} FULL exit @ ${current_price:.2f}, "
                            f"P&L: {pnl_pct:+.1f}%"
                        )
                else:
                    # Partial exit (TODO: implement partial exit in order manager)
                    # For now, just mark tier as done and log intent
                    self.logger.info(
                        f"📊 {position.symbol}: Friday Tier {current_tier} would exit {shares_to_exit} shares "
                        f"({exit_pct*100:.0f}%), P&L: {pnl_pct:+.1f}%"
                    )
                
                position.friday_exit_tiers_done.add(current_tier)
                
            except Exception as e:
                self.logger.error(f"Error in Friday staggered exit for {position.symbol}: {e}")
        
        return exit_count
    
    def _get_current_price(self, position, data_loader) -> Optional[float]:
        """Get current price for position from data loader"""
        try:
            if data_loader:
                return data_loader.get_current_price(position.symbol)
        except Exception as e:
            self.logger.warning(f"Could not get current price for {position.symbol}: {e}")
        return None

"""
AI Order Manager - Order submission, fill tracking, and execution
Extracted from ShortCycleTrader for modular architecture
"""
import logging
import datetime as dt
import pytz
import os
import json
from typing import Optional, Dict, Any

from bot_v2.models.positions import ShortCyclePosition
from bot_v2.models.enums import PositionStatus
from bot_v2.utils.datetime_utils import get_next_trading_day


class AIOrderManager:
    """
    Manages order execution, fill tracking, and trade logging.
    
    Responsibilities:
    - Submit buy/sell orders to broker (Alpaca)
    - Track order fills and timestamps
    - Log trade explanations for regulatory compliance
    - Handle order slippage tracking
    - Manage day trade enforcement (PDT compliance)
    - Prevent duplicate entries and churning
    """
    
    def __init__(self, config, execution_engine, day_trade_tracker=None, logger: Optional[logging.Logger] = None):
        """
        Initialize order manager
        
        Args:
            config: ShortCycleConfig with trading parameters
            execution_engine: Broker API (required for order execution)
            day_trade_tracker: Optional PDT tracker
            logger: Optional logger instance
        """
        self.config = config
        self.execution_engine = execution_engine
        self.day_trade_tracker = day_trade_tracker
        self.logger = logger or logging.getLogger(__name__)
        
        # Anti-churning safeguards
        self.recent_entries = {}  # symbol -> timestamp of last entry
        self.recent_exits = {}    # symbol -> timestamp of last exit
        self.min_hold_time_minutes = getattr(config, 'min_hold_time_minutes', 30)
        self.entry_cooldown_minutes = getattr(config, 'entry_cooldown_minutes', 120)
        self.duplicate_entry_window_minutes = getattr(config, 'duplicate_entry_window_minutes', 30)
        self.failed_entry_cooldown_minutes = getattr(config, 'failed_entry_cooldown_minutes', 15)
    
    def execute_entry(self, signal):
        """
        Execute entry based on AISignal (converts to position and buys).
        
        Args:
            signal: AISignal object from signal generator
            
        Returns:
            ShortCyclePosition object if successful, None if failed
        """
        try:
            # Calculate position sizing
            position_size_dollars = signal.position_size_dollars or self.config.max_position_dollars
            entry_price = signal.entry_price
            
            # Debug logging
            self.logger.debug(
                f"{signal.symbol}: position_size_dollars={position_size_dollars} "
                f"(signal: {signal.position_size_dollars}, config: {self.config.max_position_dollars}), "
                f"entry_price={entry_price}"
            )
            
            shares = int(position_size_dollars / entry_price)
            
            if shares <= 0:
                self.logger.warning(
                    f"❌ Invalid position size for {signal.symbol}: {shares} shares "
                    f"(${position_size_dollars:.2f} / ${entry_price:.2f}) - "
                    f"signal.position_size_dollars={signal.position_size_dollars}"
                )
                return None
            
            # Calculate exit date (D+2 default, D+3 for high-vol, weekend protection)
            entry_date = dt.datetime.now(pytz.UTC).date()
            exit_date = self._calculate_exit_date(entry_date, symbol=signal.symbol)
            
            # Create position object
            position = ShortCyclePosition(
                symbol=signal.symbol,
                entry_date=entry_date,
                exit_date=exit_date,
                entry_price=entry_price,
                position_size_shares=shares,
                position_size_dollars=position_size_dollars,
                stop_price=signal.stop_price,
                target_price=signal.target_price,
                status=PositionStatus.PENDING,
                ai_signal=signal,
                max_risk_dollars=(entry_price - signal.stop_price) * shares
            )
            
            # Execute buy order
            success = self.execute_buy_order(position)
            
            if success:
                position.status = PositionStatus.ENTERED
                return position
            else:
                return None
            
        except Exception as e:
            self.logger.error(f"❌ execute_entry failed for {signal.symbol}: {e}")
            return None
    
    def _calculate_exit_date(self, entry_date: dt.date, symbol: str = None) -> dt.date:
        """
        Calculate exit date based on stock volatility and day of week (Feb 11, 2026 - swing strategy)
        
        - High-vol stocks: D+5 hold
        - Thu/Fri entries: Hold through Monday (weekend protection for winners)
        - Normal stocks: D+3 default
        """
        # Get hold days configuration
        default_hold = getattr(self.config, 'default_hold_days', 3)
        high_vol_hold = getattr(self.config, 'high_vol_hold_days', 5)
        high_vol_stocks = getattr(self.config, 'high_volatility_stocks', ())
        weekend_protection = getattr(self.config, 'weekend_hold_enabled', True)
        
        # Determine hold days
        hold_days = default_hold  # D+2 default
        
        # High-volatility stocks get D+3
        if symbol and symbol.upper() in high_vol_stocks:
            hold_days = high_vol_hold
            self.logger.debug(f"🔥 {symbol}: High-vol stock, using D+{hold_days} hold")
        
        # Weekend protection: Thu/Fri entries hold through Monday
        day_of_week = entry_date.weekday()  # 0=Mon, 4=Fri
        if weekend_protection and day_of_week >= 3:  # Thu or Fri
            # Calculate days to Monday
            if day_of_week == 3:  # Thursday
                hold_days = max(hold_days, 4)  # Exit Monday (skip Fri, Sat, Sun)
            elif day_of_week == 4:  # Friday
                hold_days = max(hold_days, 3)  # Exit Monday (skip Sat, Sun)
            self.logger.debug(f"📅 {symbol}: Weekend protection, holding {hold_days} days to Monday")
        
        # Calculate exit date by adding trading days
        exit_date = entry_date
        for _ in range(hold_days):
            exit_date = get_next_trading_day(exit_date)
        
        return exit_date
    
    def execute_buy_order(self, position) -> bool:
        """
        Execute a buy order for a new position.
        
        Args:
            position: ShortCyclePosition object with order details
            
        Returns:
            True if order succeeded, False otherwise
        """
        try:
            symbol = position.symbol

            # ANTI-CHURNING CHECK 0: Cooldown after a failed entry attempt
            if symbol in self.recent_exits:
                time_since_last_fail_or_exit = (dt.datetime.now(pytz.UTC) - self.recent_exits[symbol]).total_seconds() / 60
                if time_since_last_fail_or_exit < self.failed_entry_cooldown_minutes:
                    self.logger.warning(
                        f"⚠️ RECENT FAILURE COOLDOWN: {symbol} - "
                        f"Last failure/exit was {time_since_last_fail_or_exit:.1f} minutes ago "
                        f"(cooldown: {self.failed_entry_cooldown_minutes} min)"
                    )
                    return False
            
            # ANTI-CHURNING CHECK 1: Prevent duplicate entries within timeframe
            if symbol in self.recent_entries:
                time_since_last_entry = (dt.datetime.now(pytz.UTC) - self.recent_entries[symbol]).total_seconds() / 60
                if time_since_last_entry < self.duplicate_entry_window_minutes:
                    self.logger.warning(
                        f"⚠️ DUPLICATE ENTRY BLOCKED: {symbol} - "
                        f"Last entry was {time_since_last_entry:.1f} minutes ago "
                        f"(min: {self.duplicate_entry_window_minutes} min)"
                    )
                    return False
            
            # ANTI-CHURNING CHECK 2: Cooldown after exit
            if symbol in self.recent_exits:
                time_since_exit = (dt.datetime.now(pytz.UTC) - self.recent_exits[symbol]).total_seconds() / 60
                if time_since_exit < self.entry_cooldown_minutes:
                    self.logger.warning(
                        f"⚠️ RE-ENTRY BLOCKED: {symbol} - "
                        f"Exited {time_since_exit:.1f} minutes ago "
                        f"(cooldown: {self.entry_cooldown_minutes} min)"
                    )
                    return False
            
            # Day trade enforcement check
            if not self._check_day_trade_allowance(position):
                self.recent_exits[symbol] = dt.datetime.now(pytz.UTC)
                return False
            
            # Submit actual order to broker
            if self.execution_engine:
                order_result = self.execution_engine.submit_order(
                    symbol=position.symbol,
                    order_type='market_buy',
                    quantity=position.position_size_shares
                )
                
                if order_result:
                    self.logger.info(f"✅ BUY ORDER SUBMITTED: {position.symbol} {position.position_size_shares} shares")
                    self.logger.info(f"   Order ID: {order_result['order_id']}")
                    self.logger.info(f"   Status: {order_result['status']}")
                    
                    # Capture order metadata
                    if 'order_id' in order_result:
                        position.order_id = order_result['order_id']
                    
                    if 'submitted_at' in order_result and order_result['submitted_at']:
                        position.entry_timestamp = order_result['submitted_at']
                        self.logger.info(f"   Submitted: {order_result['submitted_at']}")
                    
                    if 'filled_at' in order_result and order_result['filled_at']:
                        position.filled_at = order_result['filled_at']
                        self.logger.info(f"   Filled: {order_result['filled_at']}")

                    # Record day trade if in intraday mode
                    self._record_day_trade_if_needed(position)
                    
                    # Update entry price with ACTUAL fill price
                    # Returns False if fill diverges >5% from signal → auto-unwinds
                    fill_ok = self._update_fill_price(position, order_result)
                    if not fill_ok:
                        self.logger.error(
                            f"🚫 ENTRY REJECTED — fill divergence too large for {symbol}. "
                            f"Position unwound. Not recording entry."
                        )
                        # Record in recent_exits so we don't re-enter during cooldown
                        self.recent_exits[symbol] = dt.datetime.now(pytz.UTC)
                        return False

                    # Log explainability only after successful order + acceptable fill.
                    self._log_trade_explanation(position)
                    
                    # Record entry time for anti-churning
                    self.recent_entries[symbol] = dt.datetime.now(pytz.UTC)
                    self.logger.info(f"📝 Recorded entry time for {symbol} anti-churning tracking")
                    
                    return True
                else:
                    self.logger.error(f"❌ FAILED to submit buy order for {position.symbol}")
                    self.recent_exits[symbol] = dt.datetime.now(pytz.UTC)
                    return False
            else:
                # Fallback to paper trade logging
                self.logger.info(f"📝 Paper trade: {position.symbol} {position.position_size_shares} shares")
                position.entry_timestamp = dt.datetime.now(pytz.UTC)
                self._log_trade_explanation(position)
                
                # Record entry time for anti-churning
                self.recent_entries[symbol] = dt.datetime.now(pytz.UTC)
                
                return True
            
        except Exception as e:
            self.logger.error(f"Buy order execution failed: {e}")
            try:
                self.recent_exits[position.symbol] = dt.datetime.now(pytz.UTC)
            except Exception:
                pass
            return False
    
    def execute_sell_order(self, position, exit_price: float, reason: str) -> bool:
        """
        Execute a sell order to exit a position.
        
        Args:
            position: ShortCyclePosition object to exit
            exit_price: Current market price
            reason: Exit reason string
            
        Returns:
            True if order succeeded, False otherwise
        """
        try:
            shares_to_exit = position.position_size_shares
            symbol = position.symbol
            reason = reason or "UNKNOWN_EXIT"
            reason_lower = reason.lower()
            
            # ANTI-CHURNING CHECK: Minimum hold time (unless emergency exit)
            is_emergency = "stop" in reason_lower or "loss" in reason_lower
            is_force_exit = "force exit" in reason_lower or "d+1" in reason_lower
            
            if not is_emergency and not is_force_exit:
                entry_time = position.filled_at or position.entry_timestamp
                if entry_time:
                    if entry_time.tzinfo is None:
                        entry_time_utc = entry_time.replace(tzinfo=pytz.UTC)
                    else:
                        entry_time_utc = entry_time.astimezone(pytz.UTC)
                    hold_time_minutes = (dt.datetime.now(pytz.UTC) - entry_time_utc).total_seconds() / 60
                    if hold_time_minutes < self.min_hold_time_minutes:
                        self.logger.warning(
                            f"⚠️ EARLY EXIT BLOCKED: {symbol} - "
                            f"Held for {hold_time_minutes:.1f} minutes "
                            f"(minimum: {self.min_hold_time_minutes} min, reason: {reason})"
                        )
                        return False
            
            self.logger.info(
                f"🔚 Exiting {position.symbol}: {shares_to_exit} shares "
                f"entered {position.entry_date} (reason: {reason})"
            )
            
            # Submit actual SELL order to broker
            if self.execution_engine:
                order_result = self.execution_engine.submit_order(
                    symbol=position.symbol,
                    order_type='market_sell',
                    quantity=shares_to_exit
                )
                
                if order_result:
                    self.logger.info(f"✅ SELL ORDER SUBMITTED: {position.symbol} {shares_to_exit} shares")
                    self.logger.info(f"   Order ID: {order_result['order_id']}")
                    self.logger.info(f"   Status: {order_result['status']}")
                    
                    # Update exit price with ACTUAL fill price
                    filled_price = order_result.get('avg_fill_price') or order_result.get('filled_price') or order_result.get('fill_price')
                    if filled_price:
                        calculated_exit = exit_price
                        filled_exit = float(filled_price)
                        
                        # Calculate slippage
                        slippage_pct = abs(filled_exit - calculated_exit) / calculated_exit
                        
                        # Update exit_price with FILLED price
                        exit_price = filled_exit
                        
                        # Log slippage warning if significant
                        if slippage_pct > 0.02:  # >2% slippage
                            self.logger.warning(
                                f"⚠️ EXIT SLIPPAGE: {position.symbol} - "
                                f"Calculated: ${calculated_exit:.2f}, "
                                f"Filled: ${filled_exit:.2f} ({slippage_pct:.1%})"
                            )
                        else:
                            self.logger.info(
                                f"   Exit Fill: ${filled_exit:.2f} "
                                f"(calc: ${calculated_exit:.2f}, slip: {slippage_pct:.2%})"
                            )
                    
                    # Record exit time for anti-churning
                    exit_timestamp = dt.datetime.now(pytz.UTC)
                    self.recent_exits[symbol] = exit_timestamp
                    self.logger.info(f"📝 Recorded exit time for {symbol} anti-churning tracking")

                    # Persist exit metadata on tracked position for ledger accuracy.
                    position.status = PositionStatus.EXITED
                    position.exit_reason = reason
                    position.exit_timestamp = exit_timestamp
                    position.exit_date = exit_timestamp.date()
                    position.exit_price = exit_price
                    position.realized_pnl = (position.exit_price - position.entry_price) * shares_to_exit
                    position.hold_days = (position.exit_date - position.entry_date).days
                    self.log_exit_explanation(position)
                    
                    return True
                else:
                    self.logger.error(f"❌ FAILED to submit sell order for {position.symbol}")
                    return False
            else:
                # Fallback to paper trade logging
                self.logger.info(f"📝 Paper sell: {position.symbol} {shares_to_exit} shares")
                
                # Record exit time for anti-churning
                exit_timestamp = dt.datetime.now(pytz.UTC)
                self.recent_exits[symbol] = exit_timestamp

                # Persist exit metadata in fallback mode as well.
                position.status = PositionStatus.EXITED
                position.exit_reason = reason
                position.exit_timestamp = exit_timestamp
                position.exit_date = exit_timestamp.date()
                position.exit_price = exit_price
                position.realized_pnl = (position.exit_price - position.entry_price) * shares_to_exit
                position.hold_days = (position.exit_date - position.entry_date).days
                self.log_exit_explanation(position)
                
                return True
                
        except Exception as e:
            self.logger.error(f"Sell order execution failed for {position.symbol}: {e}", exc_info=True)
            return False
    
    def _check_day_trade_allowance(self, position) -> bool:
        """Check if day trade is allowed (PDT compliance)"""
        try:
            intraday_mode = getattr(self.config, 'max_hold_days', None) == 0
        except Exception:
            intraday_mode = False

        if intraday_mode and self.day_trade_tracker:
            remaining = self.day_trade_tracker.trades_remaining()
            
            try:
                now = dt.datetime.now(pytz.UTC)
                is_friday = now.weekday() == 4
            except Exception:
                now = dt.datetime.now()
                is_friday = now.weekday() == 4

            if is_friday:
                if remaining <= 0:
                    self.logger.warning(
                        f"❌ Friday: no emergency day trades remaining; skipping {position.symbol}"
                    )
                    return False
                else:
                    # Force same-day exit for Friday emergency trades
                    try:
                        position.exit_date = now.date()
                        self.logger.info(f"⚠️ Friday emergency entry for {position.symbol}; forcing same-day exit")
                    except Exception:
                        pass
            else:
                if remaining <= 0:
                    self.logger.warning(
                        f"❌ Day trade limit reached. Skipping {position.symbol}"
                    )
                    return False
        
        return True
    
    def _record_day_trade_if_needed(self, position):
        """Record day trade in tracker if in intraday mode"""
        try:
            intraday_mode = getattr(self.config, 'max_hold_days', None) == 0
            if intraday_mode and self.day_trade_tracker:
                when = position.filled_at if position.filled_at else dt.datetime.now(pytz.UTC)
                self.day_trade_tracker.record_trade(when)
        except Exception:
            pass
    
    def _update_fill_price(self, position, order_result: Dict) -> bool:
        """Update position with actual fill price from broker.
        
        Returns:
            True if fill is acceptable, False if divergence is too large (>5%)
            and the position should be immediately unwound.
        """
        filled_price = order_result.get('avg_fill_price') or order_result.get('filled_price') or order_result.get('fill_price')
        if filled_price:
            calculated_price = position.entry_price
            filled_price = float(filled_price)
            
            # Calculate slippage
            slippage_pct = abs(filled_price - calculated_price) / calculated_price
            
            # Update position with FILLED price (always — so tracker matches Alpaca)
            position.entry_price = filled_price
            
            # Also recalculate stop/target based on ACTUAL fill price
            if position.stop_price and calculated_price > 0:
                stop_pct = (calculated_price - position.stop_price) / calculated_price
                position.stop_price = filled_price * (1 - stop_pct)
            if position.target_price and calculated_price > 0:
                target_pct = (position.target_price - calculated_price) / calculated_price
                position.target_price = filled_price * (1 + target_pct)
            
            # DIVERGENCE GUARD: If fill is >5% away from signal price, flag for unwind
            max_divergence = 0.05
            if slippage_pct > max_divergence:
                self.logger.error(
                    f"🚨 FILL DIVERGENCE REJECTED: {position.symbol} - "
                    f"Signal: ${calculated_price:.2f}, Filled: ${filled_price:.2f} "
                    f"({slippage_pct:.1%} > {max_divergence:.0%} limit). "
                    f"Will unwind position immediately."
                )
                # Immediately sell to unwind the bad fill
                try:
                    if self.execution_engine:
                        self.execution_engine.submit_order(
                            symbol=position.symbol,
                            order_type='market_sell',
                            quantity=position.position_size_shares
                        )
                        self.logger.info(f"✅ Divergence unwind submitted for {position.symbol}")
                except Exception as uw_err:
                    self.logger.error(f"❌ Failed to unwind divergent fill for {position.symbol}: {uw_err}")
                return False
            elif slippage_pct > 0.02:  # >2% slippage — warn but accept
                self.logger.warning(
                    f"⚠️ HIGH SLIPPAGE: {position.symbol} - "
                    f"Calculated: ${calculated_price:.2f}, "
                    f"Filled: ${filled_price:.2f} ({slippage_pct:.1%})"
                )
            else:
                self.logger.info(
                    f"   Fill Price: ${filled_price:.2f} "
                    f"(calc: ${calculated_price:.2f}, slip: {slippage_pct:.2%})"
                )
        return True
    
    def _log_trade_explanation(self, position):
        """Log detailed explanation of trade decision for regulatory compliance"""
        explanation = {
            "timestamp": dt.datetime.now().isoformat(),
            "symbol": position.symbol,
            "action": "ENTRY",
            "ai_decision": {
                "confidence": position.ai_signal.confidence,
                "features_used": position.ai_signal.features_used,
                "time_horizon": position.ai_signal.time_horizon_days
            },
            "position_sizing": {
                "shares": position.position_size_shares,
                "value": position.position_size_dollars,
                "risk": position.max_risk_dollars,
                "stop_distance": position.entry_price - position.stop_price
            },
            "schedule": {
                "entry_date": position.entry_date.isoformat(),
                "scheduled_exit": position.exit_date.isoformat()
            }
        }
        
        self._save_explanation_log(explanation)
    
    def log_exit_explanation(self, position):
        """Log exit decision explanation for regulatory compliance"""
        explanation = {
            "timestamp": dt.datetime.now().isoformat(),
            "symbol": position.symbol,
            "action": "EXIT",
            "exit_reason": position.exit_reason,
            "hold_days": position.hold_days,
            "performance": {
                "entry_price": position.entry_price,
                "exit_price": position.exit_price,
                "realized_pnl": position.realized_pnl,
                "return_pct": (position.exit_price / position.entry_price - 1) * 100
            }
        }
        
        self._save_explanation_log(explanation)
    
    def _save_explanation_log(self, explanation: Dict[str, Any]):
        """Save explanation to JSON log for regulatory compliance"""
        try:
            log_file = f"logs/trade_explanations_{dt.date.today().isoformat()}.json"
            os.makedirs("logs", exist_ok=True)
            
            with open(log_file, "a") as f:
                f.write(json.dumps(explanation, default=str) + "\n")
                
        except Exception as e:
            self.logger.error(f"Failed to save explanation log: {e}")

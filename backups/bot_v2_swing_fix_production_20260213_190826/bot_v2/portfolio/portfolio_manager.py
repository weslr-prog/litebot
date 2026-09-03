"""
AI Portfolio Manager - Portfolio state tracking, capital allocation, P&L calculations
Extracted from ShortCycleTrader for modular architecture
"""
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass
import datetime as dt
import json
from pathlib import Path


@dataclass
class PortfolioState:
    """Current portfolio state snapshot"""
    portfolio_value: float
    daily_pool_dollars: float
    max_daily_loss_dollars: float
    max_weekly_loss_dollars: float
    daily_pnl: float
    daily_realized_pnl: float
    daily_unrealized_pnl: float
    weekly_pnl: float
    trades_today: int
    late_entries_today: int
    last_reset_date: Optional[dt.date]


class AIPortfolioManager:
    """
    Manages portfolio state, capital allocation, and P&L tracking.
    
    Responsibilities:
    - Track portfolio value (live from broker or config fallback)
    - Calculate daily/weekly P&L
    - Manage daily trading pool and risk limits
    - Reset counters at day boundaries
    - Provide portfolio summaries
    """
    
    def __init__(self, config, execution_engine=None, logger: Optional[logging.Logger] = None):
        """
        Initialize portfolio manager
        
        Args:
            config: ShortCycleConfig with portfolio parameters
            execution_engine: Optional broker API for live portfolio data
            logger: Optional logger instance
        """
        self.config = config
        self.execution_engine = execution_engine
        self.logger = logger or logging.getLogger(__name__)
        
        # PDT state file for persistence across restarts
        self.pdt_state_file = Path("bot_v2/data/pdt_state.json")
        
        # Portfolio state
        self.daily_pnl = 0.0
        self.daily_realized_pnl = 0.0
        self.daily_unrealized_pnl = 0.0
        self.weekly_pnl = 0.0
        self.trades_today = 0
        self.late_entries_today = 0
        self.last_pnl_reset_date: Optional[dt.date] = None
        
        # PDT tracking (emergency same-day exits) - load from persistent state
        self._load_pdt_state()
        
    def _load_pdt_state(self):
        """Load PDT counter from persistent state file"""
        try:
            if self.pdt_state_file.exists():
                with open(self.pdt_state_file, 'r') as f:
                    state = json.load(f)
                
                # Load emergency exits counter
                self.emergency_exits_this_week = state.get('emergency_exits_this_week', 0)
                
                # Load last weekly reset date
                last_reset_str = state.get('last_weekly_reset_date')
                if last_reset_str:
                    self.last_weekly_reset_date = dt.date.fromisoformat(last_reset_str)
                else:
                    self.last_weekly_reset_date = None
                
                # Check if we need to reset (it's a new week)
                today = dt.date.today()
                if today.weekday() == 0 and self.last_weekly_reset_date != today:
                    # It's Monday and we haven't reset yet this week
                    self.emergency_exits_this_week = 0
                    self.last_weekly_reset_date = today
                    self._save_pdt_state()
                    self.logger.info(f"📅 Weekly PDT counter reset from persistent state: {self.config.max_emergency_exits_per_week} emergency exits available")
                else:
                    self.logger.info(f"♻️ Loaded PDT state: {self.emergency_exits_this_week}/{self.config.max_emergency_exits_per_week} emergency exits used this week (last reset: {self.last_weekly_reset_date})")
            else:
                # No state file, initialize fresh
                self.emergency_exits_this_week = 0
                self.last_weekly_reset_date = None
                self._save_pdt_state()
                self.logger.info(f"🆕 Initialized PDT state: {self.config.max_emergency_exits_per_week} emergency exits available")
        except Exception as e:
            self.logger.error(f"❌ Failed to load PDT state: {e}, initializing fresh")
            self.emergency_exits_this_week = 0
            self.last_weekly_reset_date = None
    
    def _save_pdt_state(self):
        """Save PDT counter to persistent state file"""
        try:
            # Create data directory if it doesn't exist
            self.pdt_state_file.parent.mkdir(parents=True, exist_ok=True)
            
            state = {
                'emergency_exits_this_week': self.emergency_exits_this_week,
                'last_weekly_reset_date': self.last_weekly_reset_date.isoformat() if self.last_weekly_reset_date else None,
                'last_updated': dt.datetime.now().isoformat()
            }
            
            with open(self.pdt_state_file, 'w') as f:
                json.dump(state, f, indent=2)
                
            self.logger.debug(f"💾 Saved PDT state: {self.emergency_exits_this_week} emergency exits used")
        except Exception as e:
            self.logger.error(f"❌ Failed to save PDT state: {e}")
        
    def get_portfolio_value(self) -> float:
        """
        Get current portfolio value from execution engine or fallback to config.
        
        Returns:
            Current portfolio value in dollars
        """
        try:
            # Try to get live portfolio value from execution engine
            if self.execution_engine:
                portfolio_summary = self.execution_engine.get_portfolio_summary()
                
                # Handle different execution engine formats
                live_value = 0
                if portfolio_summary:
                    # For RealPaperTradingEngine format: {'account': {'portfolio_value': X}}
                    if 'account' in portfolio_summary and 'portfolio_value' in portfolio_summary['account']:
                        live_value = portfolio_summary['account']['portfolio_value']
                    # For regular ExecutionEngine format: {'equity': X}
                    elif 'equity' in portfolio_summary:
                        live_value = portfolio_summary['equity']
                
                if live_value and live_value > 0:
                    self.logger.debug(f"💰 Live portfolio value: ${live_value:,.2f}")
                    return float(live_value)
                else:
                    self.logger.warning(f"⚠️ Invalid live portfolio value ({live_value}), using config fallback")
                    return self.config.portfolio_value
            else:
                # Fallback: try stock API if available
                try:
                    from stock_api import StockAPI
                    api = StockAPI()
                    account_info = api.get_account_info()
                    
                    live_value = account_info.get('account_value', 0)
                    if live_value and live_value > 0:
                        self.logger.debug(f"💰 Live portfolio value (API): ${live_value:,.2f}")
                        return float(live_value)
                except:
                    pass  # Fall through to config fallback
                
                self.logger.warning(f"⚠️ No live portfolio data available, using config fallback")
                return self.config.portfolio_value
                
        except Exception as e:
            self.logger.warning(f"⚠️ Could not fetch live portfolio value: {e}, using config fallback")
            return self.config.portfolio_value
    
    def _get_daily_pool_percent(self) -> float:
        """Get daily pool percent based on day of week: 30% Mon-Wed, 100% Thu-Fri
        
        BUCKET SYSTEM Strategy:
        - Monday: 30% of portfolio (conservative start)
        - Tuesday: 30% of portfolio (test market conditions)
        - Wednesday: 30% of portfolio (build confidence)
        - Thursday: 100% of available funds (aggressive finish + profits from Mon-Wed)
        - Friday: 100% of available funds (maximize opportunities, PDT-safe with emergency slots)
        
        Benefits:
        - Mon-Wed: Conservative 30% daily pool, limits early-week risk (90% total)
        - Thu-Fri: Aggressive 100% pool, includes all profits from Mon-Wed
        - Compounding: Profits from Mon-Wed available for Thu-Fri
        - Flexibility: Adjust based on market conditions
        """
        import datetime as dt
        today = dt.date.today()
        weekday = today.weekday()  # 0=Monday, 4=Friday
        
        # Monday-Wednesday: 30% each day (0.30 * 3 = 90% total)
        # Conservative start, test market conditions, build confidence
        if weekday in [0, 1, 2]:  # Mon, Tue, Wed
            return 0.30
        
        # Thursday-Friday: 100% of available funds
        # Aggressive finish, includes all accumulated profits from Mon-Wed
        # Friday only if emergency exits available (PDT protection)
        elif weekday in [3, 4]:  # Thu, Fri
            return 1.00
        
        # Default (shouldn't happen on weekends, but safe fallback)
        return 0.30
    
    def update_risk_limits(self):
        """Update risk limits based on current portfolio value and day of week"""
        try:
            current_portfolio = self.get_portfolio_value()
            
            # Update config with current portfolio value
            old_portfolio = self.config.portfolio_value
            self.config.portfolio_value = current_portfolio
            
            # Get variable daily pool based on day of week
            daily_pool_pct = self._get_daily_pool_percent()
            
            # Recalculate derived values
            self.config.daily_pool_dollars = current_portfolio * daily_pool_pct
            self.config.max_daily_loss_dollars = current_portfolio * self.config.max_daily_loss_percent
            self.config.max_weekly_loss_dollars = current_portfolio * self.config.max_weekly_loss_percent
            
            if abs(current_portfolio - old_portfolio) > 100:  # Only log significant changes
                self.logger.info(f"💰 Portfolio updated: ${old_portfolio:,.0f} → ${current_portfolio:,.0f}")
            
            self.logger.debug(f"💰 Daily pool: ${self.config.daily_pool_dollars:.2f} ({daily_pool_pct:.0%} of ${current_portfolio:.2f})")
                
        except Exception as e:
            self.logger.warning(f"⚠️ Could not update risk limits: {e}")
    
    def reset_daily_counters_if_needed(self):
        """Reset daily P&L counters at market open if not already reset today"""
        today = dt.date.today()
        
        # Weekly reset on Monday (for PDT tracking)
        if today.weekday() == 0:  # Monday
            if self.last_weekly_reset_date != today:
                self.emergency_exits_this_week = 0
                self.last_weekly_reset_date = today
                self._save_pdt_state()  # Persist the reset
                self.logger.info(f"📅 Weekly PDT counter reset: {self.config.max_emergency_exits_per_week} emergency exits available")
        
        # Daily reset
        if self.last_pnl_reset_date != today:
            self.daily_pnl = 0.0
            self.daily_realized_pnl = 0.0
            self.daily_unrealized_pnl = 0.0
            self.trades_today = 0
            self.late_entries_today = 0
            self.last_pnl_reset_date = today
            self.logger.info(f"🔄 Daily counters reset for {today}")
            return True
        return False
    
    def update_daily_pnl(self, positions: list):
        """
        Update daily P&L tracking with correct logic for exits.
        
        Args:
            positions: List of ShortCyclePosition objects
        """
        today = dt.date.today()
        
        # Calculate realized P&L from positions exited today (regardless of entry date)
        today_exits = [
            p for p in positions 
            if hasattr(p, 'exit_timestamp') and p.exit_timestamp is not None 
            and p.exit_timestamp.date() == today 
            and p.realized_pnl is not None
        ]
        self.daily_realized_pnl = sum(p.realized_pnl for p in today_exits)
        
        # Calculate unrealized P&L from currently open positions
        from ..models.positions import PositionStatus
        open_positions = [p for p in positions if p.status == PositionStatus.ENTERED]
        self.daily_unrealized_pnl = sum(p.unrealized_pnl or 0 for p in open_positions)
        
        # Total daily P&L
        self.daily_pnl = self.daily_realized_pnl + self.daily_unrealized_pnl
        
        self.logger.debug(f"Daily P&L update: Realized ${self.daily_realized_pnl:.2f}, "
                         f"Unrealized ${self.daily_unrealized_pnl:.2f}, "
                         f"Total ${self.daily_pnl:.2f}")
    
    def update_weekly_pnl(self, positions: list):
        """
        Calculate weekly P&L (sum of realized P&L from positions exited this week).
        
        Args:
            positions: List of ShortCyclePosition objects
        """
        week_start = dt.date.today() - dt.timedelta(days=dt.date.today().weekday())
        weekly_exits = [
            p for p in positions 
            if hasattr(p, 'exit_timestamp') and p.exit_timestamp is not None 
            and p.exit_timestamp.date() >= week_start 
            and p.realized_pnl is not None
        ]
        self.weekly_pnl = sum(p.realized_pnl for p in weekly_exits)
    
    def get_portfolio_state(self) -> PortfolioState:
        """
        Get complete portfolio state snapshot.
        
        Returns:
            PortfolioState dataclass with all current values
        """
        return PortfolioState(
            portfolio_value=self.get_portfolio_value(),
            daily_pool_dollars=self.config.daily_pool_dollars,
            max_daily_loss_dollars=self.config.max_daily_loss_dollars,
            max_weekly_loss_dollars=self.config.max_weekly_loss_dollars,
            daily_pnl=self.daily_pnl,
            daily_realized_pnl=self.daily_realized_pnl,
            daily_unrealized_pnl=self.daily_unrealized_pnl,
            weekly_pnl=self.weekly_pnl,
            trades_today=self.trades_today,
            late_entries_today=self.late_entries_today,
            last_reset_date=self.last_pnl_reset_date
        )
    
    def generate_portfolio_summary(self, positions: list) -> Dict[str, Any]:
        """
        Generate portfolio summary for logging and reporting.
        
        Args:
            positions: List of ShortCyclePosition objects
            
        Returns:
            Dictionary with portfolio summary data
        """
        try:
            from ..models.positions import PositionStatus
            
            portfolio_value = self.get_portfolio_value()
            open_positions = len([p for p in positions if p.status == PositionStatus.ENTERED])
            daily_pnl = sum(p.realized_pnl or 0 for p in positions 
                          if hasattr(p, 'exit_timestamp') and p.exit_timestamp 
                          and p.exit_timestamp.date() == dt.date.today())
            
            summary = {
                'portfolio_value': portfolio_value,
                'open_positions': open_positions,
                'daily_pnl': daily_pnl,
                'trades_today': self.trades_today,
                'late_entries_today': self.late_entries_today,
                'daily_pool': self.config.daily_pool_dollars,
                'daily_loss_limit': self.config.max_daily_loss_dollars
            }
            
            self.logger.info(f"📊 Portfolio Summary:")
            self.logger.info(f"   💰 Portfolio Value: ${portfolio_value:,.2f}")
            self.logger.info(f"   📈 Open Positions: {open_positions}")
            self.logger.info(f"   📊 Today's Realized P&L: ${daily_pnl:,.2f}")
            self.logger.info(f"   🔢 Trades Today: {self.trades_today}")
            
            # Check D+1 exits due today
            today = dt.date.today()
            d1_exits = [p for p in positions 
                       if p.status == PositionStatus.ENTERED and p.exit_date <= today]
            if d1_exits:
                self.logger.info(f"   ⏰ D+1 Exits Due Today: {len(d1_exits)} positions")
                for pos in d1_exits:
                    self.logger.info(f"      • {pos.symbol}: Entry ${pos.entry_price:.2f} on {pos.entry_date}")
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Portfolio summary error: {e}")
            return {}
    
    def increment_trade_counter(self, is_late_entry: bool = False):
        """Increment trade counters"""
        self.trades_today += 1
        if is_late_entry:
            self.late_entries_today += 1
    
    def increment_emergency_exit_counter(self):
        """Increment weekly emergency exit counter (same-day exits)"""
        self.emergency_exits_this_week += 1
        self._save_pdt_state()  # Persist immediately
        self.logger.info(f"⚡ Emergency exit used: {self.emergency_exits_this_week}/{self.config.max_emergency_exits_per_week} this week")
    
    def get_friday_entry_slots_available(self) -> int:
        """Calculate how many Friday entries are allowed based on unused emergency exits"""
        if not self.config.allow_friday_entries_with_unused_slots:
            return 0
        
        today = dt.date.today()
        if today.weekday() != 4:  # Not Friday
            return 0
        
        # Unused emergency exits = available Friday slots
        unused_slots = self.config.max_emergency_exits_per_week - self.emergency_exits_this_week
        return max(0, unused_slots)
    
    def can_enter_on_friday(self) -> bool:
        """Check if Friday entries are allowed based on unused PDT slots"""
        return self.get_friday_entry_slots_available() > 0
    
    def get_pdt_status(self) -> Dict[str, Any]:
        """Get current PDT tracking status for display"""
        unused_slots = self.config.max_emergency_exits_per_week - self.emergency_exits_this_week
        return {
            'emergency_exits_used': self.emergency_exits_this_week,
            'emergency_exits_available': unused_slots,
            'max_per_week': self.config.max_emergency_exits_per_week,
            'friday_slots_available': unused_slots if dt.date.today().weekday() == 4 else unused_slots,
            'can_trade_friday': unused_slots > 0,
            'last_weekly_reset': self.last_weekly_reset_date
        }
    
    def estimate_weekly_return(self) -> float:
        """Estimate weekly return for performance tracking"""
        try:
            return (self.weekly_pnl / max(1.0, self.config.portfolio_value))
        except Exception:
            return 0.0

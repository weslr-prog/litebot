"""
Small Portfolio Configuration (<$1K Trading)
Optimized for aggressive weekly profit targets with mid-cap focus
Created: October 30, 2025
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime, time
import logging

logger = logging.getLogger(__name__)

@dataclass
class SmallPortfolioConfig:
    """
    Configuration class optimized for <$1K portfolios
    Key Features:
    - 33% daily pools Monday-Wednesday
    - Thursday all-in deployment 
    - Aggressive exit zones for larger % returns
    - Mid-cap stock focus for volatility
    - Weekly positive return targets
    """
    
    # Core Portfolio Parameters
    portfolio_value: float = 989.69  # Actual current portfolio size
    daily_pool_percent: float = 0.80  # 80% aggressive deployment (per optimization plan)
    thursday_pool_percent: float = 1.0  # All-in Thursday
    portfolio_threshold_large: float = 100000.0  # Threshold for "large" portfolio diversification rules
    
    # Account Type Configuration (CASH ACCOUNT - INTRADAY ENABLED)
    cash_account_mode: bool = True  # True = Cash account with intraday trading enabled
    enable_same_day_exit: bool = True  # Allow same-day exits
    enable_same_day_reentry: bool = True  # Allow same-day re-entries
    enable_intraday_scalping: bool = True  # Enable intraday trading
    
    # Position Sizing (Aggressive Intraday)
    max_position_dollars: float = 200.0  # 20% max position (per optimization plan)
    min_position_size_dollars: float = 50.0  # Lower minimum to keep small-account throughput viable
    max_positions_per_day: int = 12  # Very aggressive target throughput
    max_positions_per_symbol_small: int = 1  # Only 1 position per symbol (simplify tracking)
    max_concentration_percent_small: float = 0.30  # Max 30% of positions in one symbol
    position_size_increment: float = 25.0  # $25 increments for clean sizing
    
    # Risk Management (Intraday, high-throughput with hard daily guardrail)
    max_risk_per_trade_dollars: float = 20.0  # 2% portfolio risk per trade
    max_loss_per_trade_dollars: float = 50.0  # 5% hard stop per trade (per optimization plan)
    max_daily_loss_percent: float = 0.05  # 5% daily loss limit (user-selected)
    max_weekly_loss_percent: float = 0.10  # 10% weekly loss limit (per optimization plan)
    position_risk_percent: float = 0.02  # 2% default risk per position
    
    # Calculated Risk Limits (Initialized at runtime, updated dynamically)
    daily_pool_dollars: float = 800.0  # 80% of $1K = $800 (per optimization plan)
    max_daily_loss_dollars: float = 50.0  # 5% of $1K = $50
    max_weekly_loss_dollars: float = 100.0  # 10% of $1K = $100 (per optimization plan)
    
    # Trailing Stop Configuration
    enable_trailing_stops: bool = True  # Enable trailing stops
    
    # Stock Selection Filters (Aggressive Intraday Universe)
    min_price: float = 5.0  # Expanded lower bound for higher opportunity count
    max_price: float = 120.0  # OPTIMIZATION: Expanded from $100 to $120 to capture mid-caps (recovers 49% of prefilter rejections)
    min_volatility: float = 0.03  # 3% minimum ATR - need bigger daily swings
    max_volatility: float = 0.12  # 12% maximum ATR - avoid overnight gap risk (vs 15% intraday)
    
    # BACKTEST-VALIDATED OPTIMAL VALUE - Nov 14, 2025
    # Comprehensive backtest (6 configs, 2017-2024) proves 3.5% is optimal for recent market
    # Recent performance (2023-2024): 3.5% = +64.59%, 4.0% = +62.11%, 5.0% = much worse
    # Volume filter testing showed 1.25x+ volume HALVES returns in recent market
    # Conclusion: Keep 3.5% momentum, NO volume filter (current 1.0x baseline is best)
    # See: COMPREHENSIVE_BACKTEST_ANALYSIS_NOV14.md for full results
    min_momentum: float = 0.035  # 3.5% minimum 4-day return (OPTIMAL per backtest)
    
    max_momentum: float = 0.40  # 40% maximum - mid-caps can run harder (vs 50%)
    # Breakout Detection (Balanced for Quality Swing Trades)
    vol_spike_min: float = 0.8  # 80% volume spike minimum (quality filter)
    breakout_min: float = 0.003  # 0.3% price breakout minimum (real momentum)
    breakout_window: int = 10  # Reduced from 20 (less data needed)
    vol_avg_window: int = 10  # Reduced from 20 (more responsive)
    
    # ⚠️ OPTIMIZATION: Lowered confidence threshold to increase signal generation ⚠️
    confidence_threshold: float = 0.02  # OPTIMIZATION: Lowered from 0.04 to 0.02 (2%) to broaden signal acceptance ~50% (target 1-2 trades/day)
    
    # Volume Requirements (Balanced for Liquidity & Access)
    min_avg_volume: int = 200_000  # 200K shares daily (quality + liquidity balance)
    min_dollar_volume: int = 1_000_000  # $1M daily dollar volume (ensure exit ability)
    
    # Watchlist Universe Size
    max_universe_size: int = 40  # Higher scan breadth for intraday opportunity capture
    min_universe_size: int = 12   # Keep enough candidates during slow sessions
    
    # Dynamic Position Sizing Multipliers (More Aggressive)
    high_confidence_multiplier_min: float = 2.5  # vs 1.6 current
    high_confidence_multiplier_max: float = 3.0  # vs 2.0 current
    medium_confidence_multiplier_min: float = 1.8  # vs 1.2 current  
    medium_confidence_multiplier_max: float = 2.5  # vs 1.6 current
    low_confidence_multiplier_min: float = 1.2  # vs 1.0 current
    low_confidence_multiplier_max: float = 1.8  # vs 1.2 current
    
    # Intraday Parameters
    intraday_take_profit: float = 0.03  # +3% target for faster turnover
    intraday_stop_loss: float = -0.02  # -2% stop for faster loss containment
    intraday_max_hold_minutes: int = 390  # Same-day only (regular session)
    intraday_monitor_interval_seconds: int = 120  # Check every 2 minutes
    intraday_capital_allocation: float = 0.9  # High deployment while preserving risk headroom
    
    # Swing Trading Exit Strategy (D+1 to D+3 - Multi-Day Holds)
    # Targets for 2-3 day momentum swing trades (PER OPTIMIZATION PLAN)
    zone1_take_profit: float = 0.03  # +3% D+1 morning target (9:30-10:00)
    zone1_stop_loss: float = -0.02  # -2% D+1 morning stop
    zone2_take_profit: float = 0.04  # +4% D+1 mid-day target (10:00-14:00)
    zone2_stop_loss: float = -0.03  # -3% D+1 mid-day stop
    zone3_take_profit: float = 0.025  # +2.5% D+1 afternoon target (14:00-15:45)
    zone3_stop_loss: float = -0.02  # -2% D+1 afternoon stop
    
    # Enhanced Trailing Stops (Swing Trading Optimized - Per Optimization Plan)
    trailing_trigger_pct: float = 0.03  # Activate at +3% (catch smaller wins on volatile stocks)
    trailing_distance_pct: float = 0.02  # Trail 2% behind (avoid whipsaws)
    trailing_min_profit_pct: float = 0.01  # Lock +1% minimum profit
    trailing_update_interval: int = 300  # Update every 5 minutes (vs 60 sec - less frequent)
    
    # Trading Schedule (INTRADAY)
    trading_days: List[str] = field(default_factory=lambda: [
        "monday", "tuesday", "wednesday", "thursday", "friday"
    ])
    exit_only_days: List[str] = field(default_factory=lambda: [])  # Can exit any day
    exit_time: str = "15:45"  # Force-flat before close
    max_hold_days: int = 0  # Same-day only
    force_exit_time: time = field(default_factory=lambda: time(15, 45))  # 3:45 PM force-flat
    
    # T+2 Settlement Tracking (Cash Account Compliance)
    enable_settlement_tracking: bool = True  # Track T+2 settlement dates
    settlement_days: int = 2  # Business days for cash to settle
    settlement_buffer_dollars: float = 50.0  # Emergency reserve (never trade)
    warn_unsettled_threshold: float = 0.8  # Warn if using >80% of settled cash
    
    # All-Day Entry Settings (Aggressive Intraday Opportunity Capture)
    enable_all_day_entries: bool = True  # Allow entries throughout the day
    allow_late_entries_after_minutes: int = 15  # Start late-entry logic shortly after open stabilization
    late_entry_confidence_multiplier: float = 1.0  # No extra penalty for late entries in aggressive mode
    max_late_entries_per_day: int = 8  # Higher late-entry capacity
    late_entry_position_size_pct: float = 1.0  # Use 100% of normal position size
    all_day_entry_cutoff_time: str = "15:30"  # Continue entries longer into session
    require_min_avg_volume_for_late: int = 500_000  # Keep liquidity control without over-starving entries
    late_entry_check_interval_minutes: int = 5  # Frequent late-entry opportunity checks
    
    # Performance Targets (Swing Trading - Multi-Day Returns)
    daily_target_return_min: float = 0.005  # 0.5% daily minimum (slower than intraday)
    daily_target_return_max: float = 0.03  # 3% daily maximum (vs 4% intraday)
    weekly_target_return: float = 0.08  # 8% weekly target (vs 10% intraday)
    weekly_positive_rate_target: float = 0.75  # 75% positive weeks
    monthly_target_return: float = 0.25  # 25% monthly target (vs 30% intraday)
    
    def get_daily_pool(self, current_day: str, portfolio_value: float, 
                       open_position_value: float) -> float:
        """
        Calculate available capital for trading based on day and strategy
        
        Args:
            current_day: Day of week (lowercase)
            portfolio_value: Total portfolio value
            open_position_value: Value tied up in current positions
            
        Returns:
            Available capital for new positions
        """
        available_cash = portfolio_value - open_position_value
        
        if current_day.lower() in ["monday", "tuesday", "wednesday"]:
            # Fixed 33% of total portfolio value
            pool = portfolio_value * self.daily_pool_percent
            return min(pool, available_cash)
        
        elif current_day.lower() == "thursday":
            # All-in strategy: deploy all available cash
            return available_cash
        
        elif current_day.lower() == "friday":
            # Intraday mode allows Friday deployment with controlled pool sizing
            pool = portfolio_value * self.daily_pool_percent
            return min(pool, available_cash)

        else:  # Weekends
            return 0.0
    
    def get_position_size(self, stock_price: float, confidence_level: str, 
                         available_capital: float) -> float:
        """
        Calculate position size based on confidence and available capital
        
        Args:
            stock_price: Current stock price
            confidence_level: 'high', 'medium', or 'low'
            available_capital: Available capital for this position
            
        Returns:
            Position size in dollars
        """
        # Base position size (percentage of available capital)
        base_size = min(available_capital * 0.8, self.max_position_dollars)
        
        # Apply confidence multiplier
        if confidence_level.lower() == 'high':
            multiplier = (self.high_confidence_multiplier_min + 
                         self.high_confidence_multiplier_max) / 2
        elif confidence_level.lower() == 'medium':
            multiplier = (self.medium_confidence_multiplier_min +
                         self.medium_confidence_multiplier_max) / 2
        else:  # low confidence
            multiplier = (self.low_confidence_multiplier_min +
                         self.low_confidence_multiplier_max) / 2
        
        # Calculate final position size
        position_size = base_size * multiplier
        
        # Apply constraints
        position_size = max(position_size, self.min_position_size_dollars)
        position_size = min(position_size, self.max_position_dollars)
        position_size = min(position_size, available_capital)
        
        # Round to increment
        position_size = round(position_size / self.position_size_increment) * self.position_size_increment
        
        return position_size
    
    def get_exit_thresholds(self, current_time: datetime) -> tuple[float, float]:
        """
        Get take profit and stop loss thresholds based on time of day
        
        Args:
            current_time: Current market time
            
        Returns:
            Tuple of (take_profit_pct, stop_loss_pct)
        """
        hour = current_time.hour
        minute = current_time.minute
        
        if 9 <= hour < 10 or (hour == 10 and minute <= 30):
            # Zone 1: Morning volatility (9:30-10:30 AM)
            return self.zone1_take_profit, self.zone1_stop_loss
        
        elif 10 < hour < 13 or (hour == 10 and minute > 30):
            # Zone 2: Mid-day trend following (10:30 AM - 1:00 PM)
            return self.zone2_take_profit, self.zone2_stop_loss
        
        elif 13 <= hour < 15 or (hour == 15 and minute <= 30):
            # Zone 3: Afternoon positioning (1:00-3:30 PM)
            return self.zone3_take_profit, self.zone3_stop_loss
        
        else:
            # Zone 4: Force exit approaching close (3:30-4:00 PM)
            return 0.0, -1.0  # Exit all positions regardless of P&L
    
    def calculate_stop_loss_price(self, entry_price: float, current_time: datetime) -> float:
        """Calculate stop loss price based on entry price and time zone"""
        _, stop_loss_pct = self.get_exit_thresholds(current_time)
        if stop_loss_pct == -1.0:  # Force exit zone
            return 0.0  # Market order exit
        return entry_price * (1 + stop_loss_pct)
    
    def calculate_take_profit_price(self, entry_price: float, current_time: datetime) -> float:
        """Calculate take profit price based on entry price and time zone"""
        take_profit_pct, _ = self.get_exit_thresholds(current_time)
        if take_profit_pct == 0.0:  # Force exit zone
            return float('inf')  # No take profit, just exit
        return entry_price * (1 + take_profit_pct)
    
    def should_trade_today(self, current_day: str) -> bool:
        """Check if trading is allowed on current day"""
        return current_day.lower() in self.trading_days
    
    def should_exit_only(self, current_day: str) -> bool:
        """Check if today is exit-only day"""
        return current_day.lower() in self.exit_only_days
    
    def get_max_positions_for_day(self, current_day: str) -> int:
        """Get maximum positions allowed for specific day"""
        if current_day.lower() == "thursday":
            return self.max_positions_per_day + 1  # Allow extra position on all-in day
        return self.max_positions_per_day
    
    def validate_trade_risk(self, position_size: float, stop_loss_price: float,
                           entry_price: float, shares: int) -> bool:
        """
        Validate that trade risk is within acceptable limits
        
        Args:
            position_size: Position size in dollars
            stop_loss_price: Stop loss price
            entry_price: Entry price
            shares: Number of shares
            
        Returns:
            True if trade risk is acceptable
        """
        # Calculate dollar risk
        risk_per_share = entry_price - stop_loss_price
        total_risk = risk_per_share * shares
        
        # Check against limits
        if total_risk > self.max_risk_per_trade_dollars:
            logger.warning(f"Trade risk ${total_risk:.2f} exceeds max ${self.max_risk_per_trade_dollars}")
            return False
        
        if total_risk > self.max_loss_per_trade_dollars:
            logger.warning(f"Trade risk ${total_risk:.2f} exceeds hard stop ${self.max_loss_per_trade_dollars}")
            return False
        
        return True
    
    def get_stock_selection_filters(self) -> Dict[str, float]:
        """Return stock selection filters as dictionary for easy integration"""
        return {
            'min_price': self.min_price,
            'max_price': self.max_price,
            'min_volatility': self.min_volatility,
            'max_volatility': self.max_volatility,
            'min_momentum': self.min_momentum,
            'max_momentum': self.max_momentum,
            'min_avg_volume': self.min_avg_volume,
            'min_dollar_volume': self.min_dollar_volume,
            'vol_spike_min': self.vol_spike_min,
            'breakout_min': self.breakout_min
        }
    
    def log_configuration(self):
        """Log current configuration for debugging"""
        logger.info("=== Small Portfolio Configuration ===")
        logger.info(f"Portfolio Value: ${self.portfolio_value:,.2f}")
        logger.info(f"Daily Pool: {self.daily_pool_percent:.1%} (Mon-Wed)")
        logger.info(f"Thursday Pool: {self.thursday_pool_percent:.1%} (All-in)")
        logger.info(f"Max Position: ${self.max_position_dollars:,.2f}")
        logger.info(f"Max Risk/Trade: ${self.max_risk_per_trade_dollars:,.2f}")
        logger.info(f"Stock Price Range: ${self.min_price}-${self.max_price}")
        logger.info(f"Volatility Range: {self.min_volatility:.1%}-{self.max_volatility:.1%}")
        logger.info(f"Exit Zones: Z1({self.zone1_take_profit:.1%}/{self.zone1_stop_loss:.1%}) "
                   f"Z2({self.zone2_take_profit:.1%}/{self.zone2_stop_loss:.1%}) "
                   f"Z3({self.zone3_take_profit:.1%}/{self.zone3_stop_loss:.1%})")


# Example usage and testing
if __name__ == "__main__":
    # Create configuration
    config = SmallPortfolioConfig()
    
    # Adjust stock price range if needed
    # config.min_price = 12.0  # Example adjustment
    # config.max_price = 35.0  # Example adjustment
    
    # Test daily pool calculation
    print("=== Daily Pool Examples ===")
    portfolio = 1000.0
    open_positions = 200.0
    
    for day in ["monday", "tuesday", "wednesday", "thursday", "friday"]:
        pool = config.get_daily_pool(day, portfolio, open_positions)
        print(f"{day.capitalize()}: ${pool:.2f} available")
    
    # Test position sizing
    print("\n=== Position Sizing Examples ===")
    available_capital = 330.0  # 33% of $1K
    
    for confidence in ["high", "medium", "low"]:
        size = config.get_position_size(20.0, confidence, available_capital)
        print(f"{confidence.capitalize()} confidence: ${size:.2f} position")
    
    # Test exit thresholds
    print("\n=== Exit Thresholds by Time ===")
    from datetime import datetime
    
    test_times = [
        datetime(2025, 10, 30, 10, 0),   # 10:00 AM - Zone 1
        datetime(2025, 10, 30, 12, 0),   # 12:00 PM - Zone 2  
        datetime(2025, 10, 30, 14, 0),   # 2:00 PM - Zone 3
        datetime(2025, 10, 30, 15, 45),  # 3:45 PM - Zone 4
    ]
    
    for test_time in test_times:
        take_profit, stop_loss = config.get_exit_thresholds(test_time)
        print(f"{test_time.strftime('%I:%M %p')}: "
              f"Take Profit {take_profit:.1%}, Stop Loss {stop_loss:.1%}")
    
    # Log full configuration
    config.log_configuration()
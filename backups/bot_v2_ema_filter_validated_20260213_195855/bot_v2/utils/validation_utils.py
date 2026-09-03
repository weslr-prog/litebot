"""
Validation utilities for trading rules and compliance
"""
import datetime as dt
import pytz
from typing import List, Tuple, Optional
import logging


logger = logging.getLogger(__name__)


def validate_diversification(symbol: str, positions: List, config) -> Tuple[bool, str]:
    """
    Check if we can add another position without exceeding diversification limits.
    
    Args:
        symbol: Symbol to check
        positions: List of current positions
        config: ShortCycleConfig with limits
        
    Returns:
        Tuple of (allowed: bool, reason: str)
    """
    from ..models.positions import PositionStatus
    
    try:
        # Count current positions in this symbol
        current_positions_in_symbol = sum(1 for pos in positions 
                                         if pos.symbol == symbol and pos.status == PositionStatus.ENTERED)
        
        # Get portfolio size to determine limits
        portfolio_value = config.portfolio_value
        
        # Set position limits based on portfolio size
        if portfolio_value < config.portfolio_threshold_large:
            max_positions_per_symbol = config.max_positions_per_symbol_small
            max_concentration_pct = config.max_concentration_percent_small
            portfolio_type = "small"
        else:
            max_positions_per_symbol = config.max_positions_per_symbol_large
            max_concentration_pct = config.max_concentration_percent_large
            portfolio_type = "large"
        
        # Rule 1: Check max positions per symbol
        if current_positions_in_symbol >= max_positions_per_symbol:
            logger.info(f"🔄 {symbol}: Already have {current_positions_in_symbol} positions "
                       f"(limit: {max_positions_per_symbol} for {portfolio_type} portfolio)")
            return False, "MAX_POSITIONS_PER_SYMBOL"
        
        # Rule 2: Check concentration percentage (if we have enough positions)
        total_active_positions = sum(1 for pos in positions if pos.status == PositionStatus.ENTERED)
        
        if total_active_positions >= 3:
            symbol_positions_after_add = current_positions_in_symbol + 1
            total_positions_after_add = total_active_positions + 1
            symbol_concentration = symbol_positions_after_add / total_positions_after_add
            
            if symbol_concentration > max_concentration_pct:
                logger.info(f"🔄 {symbol}: Would exceed {max_concentration_pct:.0%} concentration limit "
                           f"({symbol_concentration:.1%} with this trade)")
                return False, "CONCENTRATION_LIMIT"
        
        return True, "DIVERSIFICATION_OK"
        
    except Exception as e:
        logger.error(f"Error checking diversification for {symbol}: {e}")
        return True, "CHECK_ERROR"  # Allow on error


def check_same_day_activity(symbol: str, positions: List, config) -> bool:
    """
    PDT-compliant entry logic - check if same-day activity should block entry.
    
    Args:
        symbol: Symbol to check
        positions: List of current positions
        config: ShortCycleConfig with PDT settings
        
    Returns:
        True if symbol should be BLOCKED, False if allowed
    """
    from ..models.positions import PositionStatus
    
    # Cash account mode: No PDT restrictions
    cash_mode = getattr(config, 'cash_account_mode', False)
    enable_same_day_reentry = getattr(config, 'enable_same_day_reentry', False)
    
    if cash_mode and enable_same_day_reentry:
        return False
    
    # Margin account: PDT-compliant logic
    today = dt.date.today()
    
    # Rule: Prevent multiple ACTIVE positions same symbol same day
    same_day_active_entries = sum(1 for p in positions 
                                  if p.symbol == symbol 
                                  and p.entry_date == today
                                  and p.status in [PositionStatus.ENTERED, PositionStatus.PENDING])
    
    if same_day_active_entries > 0:
        logger.info(
            f"🚫 PDT BLOCK: {symbol} already has {same_day_active_entries} ACTIVE position(s) today"
        )
        return True
    
    # Check if there was a same-day exit (for logging)
    same_day_exit_found = False
    for position in positions:
        if (position.symbol == symbol and 
            hasattr(position, 'exit_timestamp') and position.exit_timestamp and 
            position.exit_timestamp.date() == today):
            same_day_exit_found = True
            break
    
    if same_day_exit_found:
        logger.info(
            f"✅ {symbol}: Same-day re-entry ALLOWED after earlier exit "
            f"(will enforce D+1 hold for PDT compliance)"
        )
    
    return False  # Allow entry


def get_max_positions_for_day(current_day: Optional[int] = None, 
                              emergency_trades_remaining: int = 0) -> Tuple[int, float]:
    """
    Get dynamic position limits based on day of week.
    
    Args:
        current_day: 0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri (defaults to today)
        emergency_trades_remaining: Number of day trades left this week
        
    Returns:
        Tuple of (max_positions, max_portfolio_pct)
    """
    if current_day is None:
        try:
            current_day = dt.datetime.now(pytz.UTC).weekday()
        except Exception:
            current_day = dt.datetime.now().weekday()
    
    # Mon-Wed: Conservative 3 positions max, 30% portfolio
    if current_day in [0, 1, 2]:
        return (3, 0.30)
    
    # Thursday: Aggressive - up to 90% portfolio
    elif current_day == 3:
        return (10, 0.90)
    
    # Friday: Allow carryovers + emergency day trades
    elif current_day == 4:
        if emergency_trades_remaining > 0:
            return (999, 0.90)  # High limit for carryovers
        else:
            return (999, 0.0)  # No new entries
    
    # Default fallback
    return (3, 0.30)

"""
Datetime utilities for trading operations
"""
import datetime as dt
from typing import Optional, Set


# US Market Holidays (NYSE/NASDAQ) - 2024-2026
# Update this annually or integrate with a holiday calendar API
US_MARKET_HOLIDAYS: Set[dt.date] = {
    # 2024 Holidays
    dt.date(2024, 1, 1),    # New Year's Day
    dt.date(2024, 1, 15),   # MLK Day
    dt.date(2024, 2, 19),   # Presidents Day
    dt.date(2024, 3, 29),   # Good Friday
    dt.date(2024, 5, 27),   # Memorial Day
    dt.date(2024, 6, 19),   # Juneteenth
    dt.date(2024, 7, 4),    # Independence Day
    dt.date(2024, 9, 2),    # Labor Day
    dt.date(2024, 11, 28),  # Thanksgiving
    dt.date(2024, 12, 25),  # Christmas
    
    # 2025 Holidays
    dt.date(2025, 1, 1),    # New Year's Day
    dt.date(2025, 1, 20),   # MLK Day
    dt.date(2025, 2, 17),   # Presidents Day
    dt.date(2025, 4, 18),   # Good Friday
    dt.date(2025, 5, 26),   # Memorial Day
    dt.date(2025, 6, 19),   # Juneteenth
    dt.date(2025, 7, 4),    # Independence Day
    dt.date(2025, 9, 1),    # Labor Day
    dt.date(2025, 11, 27),  # Thanksgiving
    dt.date(2025, 12, 25),  # Christmas
    
    # 2026 Holidays
    dt.date(2026, 1, 1),    # New Year's Day
    dt.date(2026, 1, 19),   # MLK Day
    dt.date(2026, 2, 16),   # Presidents Day
    dt.date(2026, 4, 3),    # Good Friday
    dt.date(2026, 5, 25),   # Memorial Day
    dt.date(2026, 6, 19),   # Juneteenth
    dt.date(2026, 7, 3),    # Independence Day (observed)
    dt.date(2026, 9, 7),    # Labor Day
    dt.date(2026, 11, 26),  # Thanksgiving
    dt.date(2026, 12, 25),  # Christmas
}


def is_market_holiday(date: dt.date) -> bool:
    """
    Check if a date is a US market holiday.
    
    Args:
        date: Date to check
        
    Returns:
        True if market is closed for holiday
    """
    return date in US_MARKET_HOLIDAYS


def is_trading_day(date: dt.date) -> bool:
    """
    Check if a date is a valid trading day (not weekend or holiday).
    
    Args:
        date: Date to check
        
    Returns:
        True if market is open
    """
    # Check weekend
    if date.weekday() >= 5:  # Saturday = 5, Sunday = 6
        return False
    
    # Check holidays
    if is_market_holiday(date):
        return False
    
    return True


def get_next_trading_day(current_date: dt.date) -> dt.date:
    """
    Get next trading day for D+1 exit scheduling.
    Properly handles weekends AND market holidays.
    
    Args:
        current_date: Starting date
        
    Returns:
        Next trading day (skips weekends and holidays)
    """
    next_day = current_date + dt.timedelta(days=1)
    
    # Keep advancing until we find a trading day (max 10 days to prevent infinite loop)
    max_attempts = 10
    attempts = 0
    
    while not is_trading_day(next_day) and attempts < max_attempts:
        next_day += dt.timedelta(days=1)
        attempts += 1
    
    return next_day


def get_trading_days_ahead(current_date: dt.date, days_ahead: int = 1) -> dt.date:
    """
    Get the trading day N days ahead (skipping weekends and holidays).
    
    Args:
        current_date: Starting date
        days_ahead: Number of trading days to look ahead
        
    Returns:
        Target trading day
    """
    target_date = current_date
    trading_days_found = 0
    max_attempts = days_ahead * 3 + 10  # Safety limit
    attempts = 0
    
    while trading_days_found < days_ahead and attempts < max_attempts:
        target_date += dt.timedelta(days=1)
        if is_trading_day(target_date):
            trading_days_found += 1
        attempts += 1
    
    return target_date


def calculate_hold_days(entry_date: dt.date, exit_date: Optional[dt.date] = None) -> int:
    """
    Calculate number of days position was held.
    
    Args:
        entry_date: Position entry date
        exit_date: Position exit date (defaults to today)
        
    Returns:
        Number of days held
    """
    if exit_date is None:
        exit_date = dt.date.today()
    return (exit_date - entry_date).days

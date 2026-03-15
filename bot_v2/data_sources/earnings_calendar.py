"""
Earnings Calendar Filter
Skip stocks near earnings to avoid unpredictable volatility
Uses yfinance (free) to fetch earnings dates
"""

import os
import logging
from typing import Dict, Optional
from datetime import datetime, timedelta
import yfinance as yf

logger = logging.getLogger(__name__)


class EarningsCalendar:
    """Filter out stocks with upcoming earnings"""
    
    def __init__(self, days_before: int = 3, days_after: int = 1):
        """
        Initialize earnings calendar filter
        
        Args:
            days_before: Skip stocks N days before earnings (default: 3)
            days_after: Skip stocks N days after earnings (default: 1)
        """
        self.days_before = days_before
        self.days_after = days_after
        self._cache = {}  # Cache earnings dates to avoid repeated API calls
        self._cache_expiry = {}
        # Logging handled by parent signal_generator
    
    def check_earnings(self, symbol: str) -> Dict:
        """
        Check if stock has earnings soon
        
        Args:
            symbol: Stock symbol
            
        Returns:
            {
                'has_earnings_soon': True/False,
                'earnings_date': datetime or None,
                'days_until': int or None,
                'should_skip': True/False,
                'reason': str
            }
        """
        try:
            # Check cache first (cache for 1 day)
            now = datetime.now()
            if symbol in self._cache and symbol in self._cache_expiry:
                if self._cache_expiry[symbol] > now:
                    return self._cache[symbol]
            
            # Fetch earnings date from yfinance
            ticker = yf.Ticker(symbol)
            
            # Try to get earnings date
            earnings_date = None
            
            # Method 1: calendar attribute (most reliable)
            if hasattr(ticker, 'calendar') and ticker.calendar is not None:
                try:
                    # calendar is a DataFrame with earnings dates
                    if 'Earnings Date' in ticker.calendar:
                        earnings_dates = ticker.calendar['Earnings Date']
                        if len(earnings_dates) > 0:
                            # Get the nearest future earnings date
                            earnings_date = earnings_dates[0]
                            if isinstance(earnings_date, str):
                                earnings_date = datetime.strptime(earnings_date, '%Y-%m-%d')
                except Exception as e:
                    logger.debug(f"{symbol}: Could not parse calendar earnings: {e}")
            
            # Method 2: earnings_dates attribute (backup)
            if earnings_date is None and hasattr(ticker, 'earnings_dates'):
                try:
                    earnings = ticker.earnings_dates
                    if earnings is not None and len(earnings) > 0:
                        # Get next future earnings date
                        future_earnings = earnings[earnings.index > now]
                        if len(future_earnings) > 0:
                            earnings_date = future_earnings.index[0].to_pydatetime()
                except Exception as e:
                    logger.debug(f"{symbol}: Could not parse earnings_dates: {e}")
            
            # No earnings date found
            if earnings_date is None:
                result = {
                    'has_earnings_soon': False,
                    'earnings_date': None,
                    'days_until': None,
                    'should_skip': False,
                    'reason': 'No earnings date available'
                }
                
                # Cache for 1 day
                self._cache[symbol] = result
                self._cache_expiry[symbol] = now + timedelta(days=1)
                return result
            
            # Calculate days until earnings
            if isinstance(earnings_date, str):
                earnings_date = datetime.fromisoformat(earnings_date.replace('Z', '+00:00'))
            
            # Convert to datetime if it's a date object
            if hasattr(earnings_date, 'date') and callable(earnings_date.date):
                # It's already a datetime
                if earnings_date.tzinfo is not None:
                    earnings_date = earnings_date.replace(tzinfo=None)
            else:
                # It's a date object, convert to datetime
                earnings_date = datetime.combine(earnings_date, datetime.min.time())
            
            days_until = (earnings_date - now).days
            
            # Check if we should skip
            should_skip = False
            reason = ''
            
            if -self.days_after <= days_until <= self.days_before:
                should_skip = True
                if days_until < 0:
                    reason = f'Earnings was {abs(days_until)}d ago (within {self.days_after}d after window)'
                elif days_until == 0:
                    reason = 'Earnings is TODAY'
                else:
                    reason = f'Earnings in {days_until}d (within {self.days_before}d before window)'
            else:
                reason = f'Earnings in {days_until}d (safe)'
            
            result = {
                'has_earnings_soon': days_until <= self.days_before,
                'earnings_date': earnings_date,
                'days_until': days_until,
                'should_skip': should_skip,
                'reason': reason
            }
            
            # Cache for 1 day
            self._cache[symbol] = result
            self._cache_expiry[symbol] = now + timedelta(days=1)
            
            return result
            
        except Exception as e:
            logger.debug(f"{symbol}: Error checking earnings: {e}")
            # On error, don't skip (better to trade than block on API errors)
            return {
                'has_earnings_soon': False,
                'earnings_date': None,
                'days_until': None,
                'should_skip': False,
                'reason': f'Error checking earnings: {str(e)[:50]}'
            }
    
    def should_skip_symbol(self, symbol: str) -> bool:
        """
        Simple check: should we skip this symbol?
        
        Args:
            symbol: Stock symbol
            
        Returns:
            True if should skip, False otherwise
        """
        result = self.check_earnings(symbol)
        return result['should_skip']
    
    def format_earnings_log(self, symbol: str, earnings_info: Dict) -> str:
        """Format earnings info for logging"""
        if earnings_info['should_skip']:
            emoji = '❌'
        elif earnings_info['has_earnings_soon']:
            emoji = '⚠️'
        else:
            emoji = '✅'
        
        days = earnings_info['days_until']
        if days is not None:
            if days < 0:
                time_str = f"{abs(days)}d ago"
            elif days == 0:
                time_str = "TODAY"
            else:
                time_str = f"in {days}d"
        else:
            time_str = "unknown"
        
        return f"{symbol}: {emoji} Earnings {time_str} - {earnings_info['reason']}"

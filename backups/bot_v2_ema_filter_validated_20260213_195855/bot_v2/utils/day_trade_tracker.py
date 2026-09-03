"""
Day Trade Tracker for bot_v2

Enforces Pattern Day Trader (PDT) rule compliance for accounts < $25K.
Tracks day trades in rolling 5-business-day window.

PDT Rule: Maximum 3 day trades per rolling 5-business-day period.
Violation results in account restriction for 90 days.

Usage:
    from bot_v2.utils import DayTradeTracker
    
    tracker = DayTradeTracker()
    
    # Before entering position
    if tracker.trades_remaining() > 0:
        enter_position()
        tracker.record_trade()
    else:
        skip_entry()  # No day trades remaining
"""
from __future__ import annotations

import datetime as dt
import json
import os
from typing import List

DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data')
STORAGE_FILE = os.path.join(DATA_PATH, 'day_trades.json')


def _ensure_data_dir():
    """Ensure data directory exists."""
    if not os.path.exists(DATA_PATH):
        os.makedirs(DATA_PATH, exist_ok=True)


class DayTradeTracker:
    """
    Track day trades for PDT compliance.
    
    PDT Rule: Accounts < $25K limited to 3 day trades per rolling 5-business-day window.
    Day Trade: Buy and sell (or sell and buy) same security on same trading day.
    
    Attributes:
        max_trades: Maximum day trades allowed (default: 3)
        window_business_days: Rolling window in business days (default: 5)
    """
    
    def __init__(self, storage_file: str = STORAGE_FILE, max_trades: int = 3, window_business_days: int = 5):
        """
        Initialize day trade tracker.
        
        Args:
            storage_file: Path to JSON file storing trade history
            max_trades: Maximum day trades in rolling window (default: 3 per PDT rule)
            window_business_days: Rolling window size in business days (default: 5)
        """
        _ensure_data_dir()
        self.storage_file = storage_file
        self.max_trades = max_trades
        self.window_business_days = window_business_days
        self._load()

    def _load(self):
        """Load trade history from storage file."""
        try:
            if os.path.exists(self.storage_file):
                with open(self.storage_file, 'r') as f:
                    data = json.load(f)
                self.trades = [dt.datetime.fromisoformat(ts) for ts in data.get('trades', [])]
            else:
                self.trades = []
        except Exception:
            self.trades = []

    def _save(self):
        """Save trade history to storage file."""
        try:
            with open(self.storage_file, 'w') as f:
                json.dump({'trades': [t.isoformat() for t in self.trades]}, f)
        except Exception:
            pass

    def record_trade(self, when: dt.datetime | None = None):
        """
        Record a day trade.
        
        Args:
            when: Timestamp of trade (defaults to now)
        """
        if when is None:
            when = dt.datetime.now(dt.timezone.utc)
        # Normalize tz-aware
        if when.tzinfo is None:
            when = when.replace(tzinfo=dt.timezone.utc)
        self.trades.append(when)
        # Keep storage tidy
        self._prune_old()
        self._save()

    def _prune_old(self):
        """Remove trades older than rolling window (14 calendar days conservative)."""
        cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=14)
        self.trades = [t for t in self.trades if t >= cutoff]

    def _last_n_business_dates(self, ref_date: dt.date | None = None) -> List[dt.date]:
        """
        Get last N business dates (Mon-Fri) from reference date.
        
        Args:
            ref_date: Reference date (defaults to today)
            
        Returns:
            List of business dates in rolling window
        """
        if ref_date is None:
            ref_date = dt.datetime.now(dt.timezone.utc).date()
        res = []
        d = ref_date
        # Walk backwards until we collect window_business_days business days
        while len(res) < self.window_business_days:
            if d.weekday() < 5:  # Mon-Fri
                res.append(d)
            d = d - dt.timedelta(days=1)
        return res

    def count_in_window(self, ref_date: dt.date | None = None) -> int:
        """
        Count day trades in rolling window.
        
        Args:
            ref_date: Reference date (defaults to today)
            
        Returns:
            Number of day trades in window
        """
        dates = set(self._last_n_business_dates(ref_date))
        count = 0
        for t in self.trades:
            if t.date() in dates:
                count += 1
        return count

    def trades_remaining(self, ref_date: dt.date | None = None) -> int:
        """
        Get number of day trades remaining in window.
        
        Args:
            ref_date: Reference date (defaults to today)
            
        Returns:
            Number of day trades remaining (0-3)
        """
        used = self.count_in_window(ref_date)
        return max(0, self.max_trades - used)
    
    def is_day_trade_allowed(self) -> bool:
        """
        Check if day trade is allowed.
        
        Returns:
            True if day trades remaining > 0
        """
        return self.trades_remaining() > 0
    
    def get_status(self) -> dict:
        """
        Get current PDT status.
        
        Returns:
            Dictionary with day trade status information
        """
        remaining = self.trades_remaining()
        used = self.count_in_window()
        
        return {
            'trades_used': used,
            'trades_remaining': remaining,
            'max_trades': self.max_trades,
            'window_days': self.window_business_days,
            'status': 'OK' if remaining > 0 else 'AT_LIMIT',
            'warning': remaining == 0
        }

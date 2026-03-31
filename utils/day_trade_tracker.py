"""Simple DayTradeTracker to enforce max day trades in a rolling N-business-day window

This module stores a list of trade timestamps (ISO strings) in `data/day_trades.json` and
provides helpers to record trades and compute how many trades remain in the rolling window.
"""
from __future__ import annotations

import datetime as dt
import json
import os
from typing import List

DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
STORAGE_FILE = os.path.join(DATA_PATH, 'day_trades.json')


def _ensure_data_dir():
    if not os.path.exists(DATA_PATH):
        os.makedirs(DATA_PATH, exist_ok=True)


class DayTradeTracker:
    def __init__(self, storage_file: str = STORAGE_FILE, max_trades: int = 3, window_business_days: int = 5):
        _ensure_data_dir()
        self.storage_file = storage_file
        self.max_trades = max_trades
        self.window_business_days = window_business_days
        self._load()

    def _load(self):
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
        try:
            with open(self.storage_file, 'w') as f:
                json.dump({'trades': [t.isoformat() for t in self.trades]}, f)
        except Exception:
            pass

    def record_trade(self, when: dt.datetime | None = None):
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
        # Remove trades older than the rolling business window (conservative 14 calendar days)
        cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=14)
        self.trades = [t for t in self.trades if t >= cutoff]

    def _last_n_business_dates(self, ref_date: dt.date | None = None) -> List[dt.date]:
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
        dates = set(self._last_n_business_dates(ref_date))
        count = 0
        for t in self.trades:
            if t.date() in dates:
                count += 1
        return count

    def trades_remaining(self, ref_date: dt.date | None = None) -> int:
        used = self.count_in_window(ref_date)
        return max(0, self.max_trades - used)


if __name__ == '__main__':
    # Quick local sanity check
    t = DayTradeTracker()
    print('Trades in window:', t.count_in_window())
    print('Remaining:', t.trades_remaining())

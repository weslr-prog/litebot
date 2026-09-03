#!/usr/bin/env python3
"""
Minimal DataLoader stub to satisfy imports in short_cycle_trader.
For dry-run tests, returns placeholder data; can be replaced by core/data_loader later.
"""
from __future__ import annotations
import pandas as pd
import datetime as dt
from typing import Dict, List, Optional

class DataLoader:
    def __init__(self):
        pass

    def get_historical_data(self, symbol: str, days: int = 30) -> pd.DataFrame:
        # Generate placeholder OHLCV: gentle uptrend with a final-day volume surge
        dates = [dt.datetime.now().date() - dt.timedelta(days=i) for i in range(days)][::-1]
        rows = []
        base = 90.0
        for idx, d in enumerate(dates):
            # Uptrend of ~1.2% per day to trigger momentum
            close = base * (1.012 ** idx)
            open_p = close * 0.995
            high = close * 1.01
            low = close * 0.99
            # Volume: baseline 900k, last day surge ~3.2M to trigger volume_surge
            vol = 900_000 if idx < len(dates) - 1 else 3_200_000
            rows.append({
                'date': pd.Timestamp(d),
                'open': round(open_p, 2),
                'high': round(high, 2),
                'low': round(low, 2),
                'close': round(close, 2),
                'volume': vol,
            })
        return pd.DataFrame(rows)

    def get_historical_data_bulk(self, symbols: List[str], days: int = 30) -> Dict[str, pd.DataFrame]:
        return {s: self.get_historical_data(s, days) for s in symbols}

    def get_current_price(self, symbol: str) -> float:
        return 100.0

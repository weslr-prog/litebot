#!/usr/bin/env python3
"""
DataLoader
Fetches historical OHLCV and current prices using yfinance (with optional future Alpaca support).
Public API is stable for use by ShortCycleTrader and other modules.
"""
from __future__ import annotations
import os
import pandas as pd
import datetime as dt
from typing import Dict, List, Optional
import logging

try:
    import yfinance as yf
except Exception:  # yfinance is listed in requirements.txt
    yf = None

# Optional Alpaca Market Data (IEX) support
try:
    from alpaca.data import StockMarketDataClient, StockLatestTradeRequest
except Exception:
    StockMarketDataClient = None
    StockLatestTradeRequest = None

logger = logging.getLogger(__name__)


class DataLoader:
    def __init__(self):
        self._yf_available = yf is not None
        # Initialize Alpaca Market Data client if credentials are available
        self._alpaca_client = None
        api_key = os.getenv("APCA_API_KEY_ID")
        secret_key = os.getenv("APCA_API_SECRET_KEY")
        if api_key and secret_key and StockMarketDataClient is not None:
            try:
                self._alpaca_client = StockMarketDataClient(api_key, secret_key)
                logger.info("Alpaca Market Data client initialized (IEX)")
            except Exception as e:
                logger.warning(f"Failed to init Alpaca Market Data client: {e}")

    def get_historical_data(self, symbol: str, days: int = 30) -> pd.DataFrame:
        """Return last N trading days of daily OHLCV as DataFrame with columns:
        date, open, high, low, close, volume.
        """
        if not self._yf_available:
            logger.warning("yfinance not available; returning empty DataFrame")
            return pd.DataFrame()

        # Request a longer calendar range to account for weekends/holidays
        calendar_days = max(int(days * 2.2), days + 10)
        start = (dt.datetime.utcnow() - dt.timedelta(days=calendar_days)).date()
        end = dt.datetime.utcnow().date()

        try:
            tkr = yf.Ticker(symbol)
            hist = tkr.history(start=start, end=end, interval="1d", auto_adjust=False)
            if hist is None or hist.empty:
                return pd.DataFrame()

            # Normalize schema
            hist = hist.rename(columns={
                'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'
            })
            # yfinance sometimes uses lowercase already; ensure columns present
            for c in ['open', 'high', 'low', 'close', 'volume']:
                if c not in hist.columns:
                    return pd.DataFrame()

            # Ensure a date column
            hist = hist.reset_index()
            # yfinance index column can be DatetimeIndex named 'Date'
            if 'Date' in hist.columns:
                hist = hist.rename(columns={'Date': 'date'})
            elif 'date' not in hist.columns:
                # Try to coerce any datetime index to 'date'
                if isinstance(hist.index, pd.DatetimeIndex):
                    hist['date'] = hist.index
                    hist = hist.reset_index(drop=True)
                else:
                    hist['date'] = pd.to_datetime('today')

            # Keep only required columns, sort, and return last N trading rows
            hist = hist[['date', 'open', 'high', 'low', 'close', 'volume']].copy()
            hist['date'] = pd.to_datetime(hist['date'])
            hist = hist.sort_values('date')
            hist = hist.dropna(subset=['open', 'high', 'low', 'close', 'volume'])
            # Return last N rows (trading days)
            if len(hist) > days:
                hist = hist.tail(days)
            return hist.reset_index(drop=True)
        except Exception as e:
            logger.error(f"Error fetching historical data for {symbol}: {e}", exc_info=False)
            return pd.DataFrame()

    def get_historical_data_bulk(self, symbols: List[str], days: int = 30) -> Dict[str, pd.DataFrame]:
        out: Dict[str, pd.DataFrame] = {}
        for s in symbols:
            df = self.get_historical_data(s, days=days)
            if isinstance(df, pd.DataFrame) and not df.empty:
                out[s] = df
        return out

    def get_current_price(self, symbol: str) -> Optional[float]:
        # Preferred: Alpaca Market Data (IEX) if configured
        if self._alpaca_client is not None and StockLatestTradeRequest is not None:
            try:
                req = StockLatestTradeRequest(symbol_or_symbols=symbol)
                resp = self._alpaca_client.get_latest_trade(req)
                # resp can be a dict (for multi-symbol) or a Trade object (single)
                price = None
                if hasattr(resp, 'price'):
                    price = resp.price
                elif isinstance(resp, dict):
                    obj = resp.get(symbol) or (next(iter(resp.values())) if resp else None)
                    price = getattr(obj, 'price', None) if obj is not None else None
                if price is not None:
                    return float(price)
            except Exception as e:
                logger.warning(f"Alpaca latest trade failed for {symbol}: {e}")

        # Fallback: yfinance last price/close
        if not self._yf_available:
            return None
        try:
            tkr = yf.Ticker(symbol)
            info = getattr(tkr, 'fast_info', None)
            if info and hasattr(info, 'last_price') and info.last_price:
                return float(info.last_price)
            hist = tkr.history(period='5d', interval='1d').tail(1)
            if not hist.empty:
                close_val = hist['Close'].iloc[-1] if 'Close' in hist.columns else hist['close'].iloc[-1]
                return float(close_val)
        except Exception:
            return None
        return None

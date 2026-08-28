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
    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.requests import StockLatestTradeRequest
except Exception:
    StockHistoricalDataClient = None
    StockLatestTradeRequest = None

logger = logging.getLogger(__name__)


class DataLoader:
    def __init__(self, enable_multi_source_validation: bool = True):
        self._yf_available = yf is not None
        # Initialize Alpaca Market Data client if credentials are available
        self._alpaca_client = None
        api_key = os.getenv("APCA_API_KEY_ID")
        secret_key = os.getenv("APCA_API_SECRET_KEY")
        if api_key and secret_key and StockHistoricalDataClient is not None:
            try:
                self._alpaca_client = StockHistoricalDataClient(api_key, secret_key)
                logger.info("Alpaca Market Data client initialized (IEX)")
            except Exception as e:
                logger.warning(f"Failed to init Alpaca Market Data client: {e}")
        
        # Initialize multi-source validation
        self._multi_source_loader = None
        if enable_multi_source_validation:
            try:
                from bot_v2.data_sources import MultiSourceDataLoader
                self._multi_source_loader = MultiSourceDataLoader(yfinance_loader=self)
                logger.info("✅ Multi-source data validation enabled (yfinance + Alpaca IEX)")
            except Exception as e:
                logger.debug(f"Multi-source validation not available: {e}")

    def get_historical_data(self, symbol: str, days: int = 30, use_cache: bool = False) -> pd.DataFrame:
        """Return last N trading days of daily OHLCV as DataFrame with columns:
        date, open, high, low, close, volume.
        
        Args:
            symbol: Stock symbol
            days: Number of days of historical data
            use_cache: Not used (kept for API compatibility)
        """
        # Try multi-source validation first (if enabled)
        if self._multi_source_loader:
            try:
                validated_data = self._multi_source_loader.get_validated_data(
                    symbol, 
                    days=days, 
                    validate=True
                )
                if validated_data is not None and not validated_data.empty:
                    # Ensure 'date' column exists
                    if 'date' not in validated_data.columns:
                        validated_data = validated_data.reset_index()
                        # Try to find a datetime column to rename
                        for col in validated_data.columns:
                            if col in ['Date', 'timestamp', 'Timestamp', 'index']:
                                validated_data = validated_data.rename(columns={col: 'date'})
                                break
                        # If still no 'date', use index
                        if 'date' not in validated_data.columns:
                            validated_data['date'] = pd.to_datetime(validated_data.index)
                    
                    # Ensure date is datetime type
                    validated_data['date'] = pd.to_datetime(validated_data['date'])
                    
                    return validated_data
            except Exception as e:
                logger.debug(f"{symbol}: Multi-source validation failed, falling back to yfinance: {e}")
        
        # Fallback to standard yfinance fetch
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
                resp = self._alpaca_client.get_stock_latest_trade(req)
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

    def get_stock_info(self, symbol: str) -> Optional[Dict]:
        """Get stock info including market cap using yfinance"""
        if not self._yf_available:
            return None
        try:
            tkr = yf.Ticker(symbol)
            info = tkr.info if hasattr(tkr, 'info') else {}
            return info
        except Exception as e:
            logger.debug(f"Error fetching info for {symbol}: {e}")
            return None

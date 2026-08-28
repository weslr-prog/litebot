#!/usr/bin/env python3
"""
Bot V2 DataLoader
Standalone data loader for bot_v2 - fetches historical OHLCV and current prices.
Uses yfinance as primary source with optional Alpaca IEX validation.
Logs to bot_v2/logs/ directory.
"""
from __future__ import annotations
import os
import pandas as pd
import datetime as dt
from typing import Dict, List, Optional
import logging
from pathlib import Path
import time
from functools import wraps

try:
    import yfinance as yf
except Exception:
    yf = None

# Alpaca Market Data (IEX) support — TIER 2 FIX (Feb 25, 2026)
# Previous import of 'StockMarketDataClient' was WRONG (class doesn't exist in alpaca-py).
# This caused silent fallback to yfinance for ALL price queries.
# Correct class is StockHistoricalDataClient.
try:
    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.requests import StockLatestTradeRequest
except Exception:
    StockHistoricalDataClient = None
    StockLatestTradeRequest = None

# Error tracking for silent failures
from bot_v2.utils.error_tracker import track_error, ErrorSeverity

# Rate limiting for yfinance
from bot_v2.utils.rate_limiter import get_yfinance_limiter

# Setup bot_v2 specific logging
logger = logging.getLogger('bot_v2.data_loader')


def retry_on_connection_error(max_retries=3, base_delay=2.0):
    """Decorator to retry data fetching on connection errors"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    error_msg = str(e)
                    
                    # Check if it's a connection-related error
                    is_connection_error = any([
                        'connection' in error_msg.lower(),
                        'timeout' in error_msg.lower(),
                        'name resolution' in error_msg.lower(),
                        'network' in error_msg.lower(),
                        'errno' in error_msg.lower(),
                        'max retries exceeded' in error_msg.lower(),
                        'read timed out' in error_msg.lower(),
                        'urlopen error' in error_msg.lower()
                    ])
                    
                    if not is_connection_error:
                        # Not a connection error, don't retry
                        raise
                    
                    if attempt < max_retries:
                        delay = min(base_delay * (2 ** attempt), 30.0)
                        logger.warning(
                            f"⚠️ Data fetch failed (attempt {attempt + 1}/{max_retries + 1}): {error_msg}"
                        )
                        logger.info(f"🔄 Retrying in {delay:.1f} seconds...")
                        time.sleep(delay)
                    else:
                        logger.error(
                            f"❌ Data fetch failed after {max_retries + 1} attempts: {error_msg}"
                        )
                        # Return empty data instead of crashing
                        return pd.DataFrame() if 'historical' in func.__name__ else None
            
            if last_exception:
                raise last_exception
        return wrapper
    return decorator


class DataLoader:
    """
    Standalone data loader for bot_v2
    Fetches market data from yfinance with optional Alpaca IEX validation
    """
    
    def __init__(self, enable_multi_source_validation: bool = True):
        """
        Initialize DataLoader
        
        Args:
            enable_multi_source_validation: Enable cross-validation with Alpaca IEX
        """
        self._yf_available = yf is not None

        # Initialize Polygon.io client
        polygon_api_key = os.getenv("POLYGON_API_KEY")
        if polygon_api_key:
            try:
                from polygon import RESTClient
                self.polygon_client = RESTClient(polygon_api_key)
                logger.info("��✅ Polygon.io client initialized")
            except Exception as e:
                logger.warning(f"��⚠��️  Failed to initialize Polygon.io client: {e}")
                self.polygon_client = None
        else:
            self.polygon_client = None

        # Initialize Alpaca Market Data client if credentials are available
        self._alpaca_client = None
        api_key = os.getenv("APCA_API_KEY_ID")
        secret_key = os.getenv("APCA_API_SECRET_KEY")
        
        if api_key and secret_key and StockHistoricalDataClient is not None:
            try:
                self._alpaca_client = StockHistoricalDataClient(api_key, secret_key)
                logger.info("✅ Alpaca Market Data client initialized (IEX via StockHistoricalDataClient)")
            except Exception as e:
                logger.warning(f"⚠️  Failed to init Alpaca Market Data client: {e}")
        
        # Initialize multi-source validation
        self._multi_source_loader = None
        if enable_multi_source_validation:
            try:
                from bot_v2.data_sources import MultiSourceDataLoader
                self._multi_source_loader = MultiSourceDataLoader(yfinance_loader=self)
                logger.info("✅ Multi-source data validation enabled (yfinance + Alpaca IEX)")
            except Exception as e:
                logger.debug(f"Multi-source validation not available: {e}")

    @retry_on_connection_error(max_retries=3, base_delay=2.0)
    def get_historical_data(
        self, 
        symbol: str, 
        days: int = 30, 
        use_cache: bool = False
    ) -> pd.DataFrame:
        """
        Get historical OHLCV data for a symbol
        
        Args:
            symbol: Stock symbol
            days: Number of trading days to fetch
            use_cache: Not used (kept for API compatibility)
        
        Returns:
            DataFrame with columns: date, open, high, low, close, volume
        """
        # 1. Try Polygon.io
        if self.polygon_client is not None:
            try:
                # Calculate date range
                end_date = dt.datetime.utcnow().date()
                calendar_days = max(int(days * 2.2), days + 10)
                start_date = end_date - dt.timedelta(days=calendar_days)
                
                # Fetch from Polygon
                aggs = self.polygon_client.get_aggs(
                    ticker=symbol,
                    multiplier=1,
                    timespan="day",
                    from_=start_date,
                    to=end_date,
                    adjusted=True,
                    sort="asc",
                    limit=50000
                )
                if aggs:
                    # Convert to DataFrame
                    data = []
                    for agg in aggs:
                        # agg.timestamp is in milliseconds
                        date = dt.datetime.fromtimestamp(agg.timestamp / 1000.0)
                        data.append({
                            'date': date,
                            'open': agg.open,
                            'high': agg.high,
                            'low': agg.low,
                            'close': agg.close,
                            'volume': agg.volume
                        })
                    df = pd.DataFrame(data)
                    if not df.empty:
                        # We have data, return the last 'days' trading days
                        df = df.sort_values('date')
                        if len(df) > days:
                            df = df.tail(days)
                        return df.reset_index(drop=True)
            except Exception as e:
                logger.debug(f"{symbol}: Polygon historical data fetch failed: {e}")
                # Fall through to multi-source
        
        # 2. Try multi-source validation (if enabled)
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
                        for col in validated_data.columns:
                            if col in ['Date', 'timestamp', 'Timestamp', 'index']:
                                validated_data = validated_data.rename(columns={col: 'date'})
                                break
                        if 'date' not in validated_data.columns:
                            validated_data['date'] = pd.to_datetime(validated_data.index)
                    validated_data['date'] = pd.to_datetime(validated_data['date'])
                    return validated_data
            except Exception as e:
                logger.debug(f"{symbol}: Multi-source validation failed: {e}")
        
        # 3. Fallback to standard yfinance fetch
        if not self._yf_available:
            logger.warning("��������������������������������������������������������������⚠��������������������������������������������������������������️  yfinance not available; returning empty DataFrame")
            return pd.DataFrame()
        
        # Request a longer calendar range to account for weekends/holidays
        calendar_days = max(int(days * 2.2), days + 10)
        start = (dt.datetime.utcnow() - dt.timedelta(days=calendar_days)).date()
        end = dt.datetime.utcnow().date()
        
        try:
            # Rate limit yfinance calls
            get_yfinance_limiter().acquire()
            
            tkr = yf.Ticker(symbol)
            hist = tkr.history(start=start, end=end, interval="1d", auto_adjust=False)
            
            if hist is None or hist.empty:
                return pd.DataFrame()
            
            # Normalize schema
            hist = hist.rename(columns={
                'Open': 'open',
                'High': 'high',
                'Low': 'low',
                'Close': 'close',
                'Volume': 'volume'
            })
            
            # Ensure required columns present
            required_cols = ['open', 'high', 'low', 'close', 'volume']
            for c in required_cols:
                if c not in hist.columns:
                    logger.warning(f"{symbol}: Missing column '{c}'")
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
            track_error(
                module='data_loader',
                function='get_historical_data',
                error=e,
                symbol=symbol,
                severity=ErrorSeverity.MEDIUM,
                context={'days': days},
                recovered=True,
                fallback_used='empty DataFrame'
            )
            logger.error(f"��������������������������������������������������������������❌ Error fetching historical data for {symbol}: {e}", exc_info=False)
            return pd.DataFrame()
    def get_historical_data(
        self, 
        symbol: str, 
        days: int = 30, 
        use_cache: bool = False
    ) -> pd.DataFrame:
        """
        Get historical OHLCV data for a symbol
        
        Args:
            symbol: Stock symbol
            days: Number of trading days to fetch
            use_cache: Not used (kept for API compatibility)
            
        Returns:
            DataFrame with columns: date, open, high, low, close, volume
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
            logger.warning("⚠️  yfinance not available; returning empty DataFrame")
            return pd.DataFrame()

        # Request a longer calendar range to account for weekends/holidays
        calendar_days = max(int(days * 2.2), days + 10)
        start = (dt.datetime.utcnow() - dt.timedelta(days=calendar_days)).date()
        end = dt.datetime.utcnow().date()

        try:
            # Rate limit yfinance calls
            get_yfinance_limiter().acquire()
            
            tkr = yf.Ticker(symbol)
            hist = tkr.history(start=start, end=end, interval="1d", auto_adjust=False)
            
            if hist is None or hist.empty:
                return pd.DataFrame()

            # Normalize schema
            hist = hist.rename(columns={
                'Open': 'open', 
                'High': 'high', 
                'Low': 'low', 
                'Close': 'close', 
                'Volume': 'volume'
            })
            
            # Ensure required columns present
            required_cols = ['open', 'high', 'low', 'close', 'volume']
            for c in required_cols:
                if c not in hist.columns:
                    logger.warning(f"{symbol}: Missing column '{c}'")
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
            track_error(
                module="data_loader",
                function="get_historical_data",
                error=e,
                symbol=symbol,
                severity=ErrorSeverity.MEDIUM,
                context={"days": days},
                recovered=True,
                fallback_used="empty DataFrame"
            )
            logger.error(f"❌ Error fetching historical data for {symbol}: {e}", exc_info=False)
            return pd.DataFrame()

    def get_historical_data_bulk(
        self, 
        symbols: List[str], 
        days: int = 30
    ) -> Dict[str, pd.DataFrame]:
        """
        Get historical data for multiple symbols
        
        Args:
            symbols: List of stock symbols
            days: Number of trading days to fetch
            
        Returns:
            Dictionary mapping symbol to DataFrame
        """
        out: Dict[str, pd.DataFrame] = {}
        for symbol in symbols:
            df = self.get_historical_data(symbol, days=days)
            if isinstance(df, pd.DataFrame) and not df.empty:
                out[symbol] = df
        return out

    @retry_on_connection_error(max_retries=3, base_delay=2.0)
    def get_current_price(self, symbol: str) -> Optional[float]:
        """
        Get current/latest price for a symbol
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Current price or None if unavailable
        """
        # Preferred: Alpaca Market Data (IEX) if configured
        # TIER 2 FIX (Feb 25, 2026): Was calling get_latest_trade() on the wrong
        # client class (StockMarketDataClient which doesn't exist). Now uses
        # get_stock_latest_trade() on StockHistoricalDataClient (correct API).
        if self._alpaca_client is not None and StockLatestTradeRequest is not None:
            try:
                req = StockLatestTradeRequest(symbol_or_symbols=symbol)
                resp = self._alpaca_client.get_stock_latest_trade(req)
                
                # resp can be a dict (for multi-symbol) or a Trade object (single)
                price = None
                if isinstance(resp, dict):
                    obj = resp.get(symbol) or (next(iter(resp.values())) if resp else None)
                    price = getattr(obj, 'price', None) if obj is not None else None
                elif hasattr(resp, 'price'):
                    price = resp.price
                    
                if price is not None:
                    return float(price)
                    
            except Exception as e:
                track_error(
                    module="data_loader",
                    function="get_current_price",
                    error=e,
                    symbol=symbol,
                    severity=ErrorSeverity.LOW,
                    context={"source": "alpaca"},
                    recovered=True,
                    fallback_used="yfinance"
                )
                logger.debug(f"{symbol}: Alpaca latest trade failed: {e}")

        # Fallback: yfinance last price/close
        if not self._yf_available:
            return None
            
        try:
            # Rate limit yfinance calls
            get_yfinance_limiter().acquire()
            
            tkr = yf.Ticker(symbol)
            
            # Try fast_info first (faster)
            info = getattr(tkr, 'fast_info', None)
            if info and hasattr(info, 'last_price') and info.last_price:
                return float(info.last_price)
                
            # Fallback to recent history
            hist = tkr.history(period='5d', interval='1d').tail(1)
            if not hist.empty:
                close_val = hist['Close'].iloc[-1] if 'Close' in hist.columns else hist['close'].iloc[-1]
                return float(close_val)
                
        except Exception as e:
            track_error(
                module="data_loader",
                function="get_current_price",
                error=e,
                symbol=symbol,
                severity=ErrorSeverity.MEDIUM,
                context={"source": "yfinance"},
                recovered=True,
                fallback_used="None return"
            )
            logger.debug(f"{symbol}: yfinance price fetch failed: {e}")
            return None
            
        return None

    def get_stock_info(self, symbol: str) -> Optional[Dict]:
        """
        Get stock info including market cap, sector, etc.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Dictionary with stock info or None if unavailable
        """
        if not self._yf_available:
            return None
            
        try:
            # Rate limit yfinance calls
            get_yfinance_limiter().acquire()
            
            tkr = yf.Ticker(symbol)
            info = tkr.info if hasattr(tkr, 'info') else {}
            return info
        except Exception as e:
            track_error(
                module="data_loader",
                function="get_stock_info",
                error=e,
                symbol=symbol,
                severity=ErrorSeverity.LOW,
                recovered=True,
                fallback_used="None return"
            )
            logger.debug(f"{symbol}: Error fetching info: {e}")
            return None

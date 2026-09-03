"""
Multi-Source Data Loader
Uses yfinance as primary, Alpaca IEX as validation/fallback
"""

import os
import logging
import pandas as pd
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

logger = logging.getLogger(__name__)


class MultiSourceDataLoader:
    """
    Load market data from multiple sources with validation
    
    Primary: yfinance (free, more historical data)
    Fallback/Validation: Alpaca IEX (free, real-time accuracy)
    """
    
    def __init__(self, yfinance_loader=None):
        """
        Initialize multi-source data loader
        
        Args:
            yfinance_loader: Existing DataLoader instance (optional)
        """
        self.yfinance_loader = yfinance_loader
        
        # Initialize Alpaca IEX client
        try:
            api_key = os.getenv('APCA_API_KEY_ID')
            api_secret = os.getenv('APCA_API_SECRET_KEY')
            
            if not api_key or not api_secret:
                logger.warning("⚠️  Alpaca credentials not found - IEX validation disabled")
                self.alpaca_client = None
                return
            
            self.alpaca_client = StockHistoricalDataClient(api_key, api_secret)
            # Logging handled by parent data_loader
            
        except Exception as e:
            logger.warning(f"⚠️  Failed to initialize Alpaca IEX client: {e}")
            self.alpaca_client = None
    
    def _fetch_yfinance_data(self, symbol: str, days: int) -> Optional[pd.DataFrame]:
        """Fetch data directly from yfinance (internal method to avoid recursion)"""
        try:
            import yfinance as yf
            import datetime as dt
            
            # Request a longer calendar range to account for weekends/holidays
            calendar_days = max(int(days * 2.2), days + 10)
            start = (dt.datetime.utcnow() - dt.timedelta(days=calendar_days)).date()
            end = dt.datetime.utcnow().date()
            
            tkr = yf.Ticker(symbol)
            hist = tkr.history(start=start, end=end, interval="1d", auto_adjust=False)
            
            if hist is None or hist.empty:
                return None
            
            # Normalize schema
            hist = hist.rename(columns={
                'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'
            })
            
            # Ensure required columns
            required = ['open', 'high', 'low', 'close', 'volume']
            if not all(c in hist.columns for c in required):
                return None
            
            # Reset index and ensure 'date' column exists
            hist = hist.reset_index()
            
            # Rename index column to 'date' if it's a datetime
            if 'Date' in hist.columns:
                hist = hist.rename(columns={'Date': 'date'})
            elif hist.columns[0] in ['index', 'timestamp', 'Timestamp'] or isinstance(hist.index, pd.DatetimeIndex):
                hist['date'] = pd.to_datetime(hist.iloc[:, 0])
                hist = hist.drop(columns=[hist.columns[0]])
            elif 'date' not in hist.columns:
                # Last resort: use index
                hist['date'] = pd.to_datetime(hist.index)
            
            hist['symbol'] = symbol
            
            # Keep only required columns (with 'date') and return last N days
            required_cols = ['date', 'open', 'high', 'low', 'close', 'volume', 'symbol']
            available_cols = [c for c in required_cols if c in hist.columns]
            hist = hist[available_cols].tail(days)
            
            return hist
            
        except Exception as e:
            logger.debug(f"{symbol}: yfinance internal fetch failed: {e}")
            return None
    
    def get_validated_data(
        self, 
        symbol: str, 
        days: int = 30,
        validate: bool = True
    ) -> Optional[pd.DataFrame]:
        """
        Get market data with cross-validation
        
        Args:
            symbol: Stock symbol
            days: Number of days of historical data
            validate: If True, cross-validate with Alpaca IEX
            
        Returns:
            DataFrame with columns: open, high, low, close, volume, symbol
            Returns None if data unavailable from all sources
        """
        # Try yfinance first (primary source) - call internal method to avoid recursion
        yf_data = None
        if self.yfinance_loader:
            try:
                # Call the internal yfinance fetch directly (not the wrapper that calls us)
                yf_data = self._fetch_yfinance_data(symbol, days)
            except Exception as e:
                logger.debug(f"{symbol}: yfinance fetch failed: {e}")
        
        # If validation disabled or no Alpaca client, return yfinance data
        if not validate or not self.alpaca_client:
            return yf_data
        
        # Fetch from Alpaca IEX for validation
        alpaca_data = None
        try:
            alpaca_data = self._fetch_alpaca_bars(symbol, days)
        except Exception as e:
            logger.debug(f"{symbol}: Alpaca IEX fetch failed: {e}")
        
        # If both sources available, validate
        if yf_data is not None and alpaca_data is not None:
            return self._validate_and_merge(symbol, yf_data, alpaca_data)
        
        # Return whichever source succeeded
        if yf_data is not None:
            logger.debug(f"{symbol}: Using yfinance data (Alpaca unavailable)")
            return yf_data
        elif alpaca_data is not None:
            logger.info(f"{symbol}: Using Alpaca IEX data (yfinance failed)")
            return alpaca_data
        else:
            logger.warning(f"{symbol}: ❌ No data from any source")
            return None
    
    def _fetch_alpaca_bars(self, symbol: str, days: int) -> Optional[pd.DataFrame]:
        """Fetch historical bars from Alpaca IEX"""
        if not self.alpaca_client:
            return None
        
        try:
            end_time = datetime.now()
            start_time = end_time - timedelta(days=days)
            
            request = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=TimeFrame.Day,
                start=start_time,
                end=end_time
            )
            
            bars = self.alpaca_client.get_stock_bars(request)
            
            if not bars or symbol not in bars:
                return None
            
            # Convert to DataFrame with 'date' column
            bar_list = bars[symbol]
            data = {
                'date': [pd.to_datetime(b.timestamp) for b in bar_list],
                'open': [b.open for b in bar_list],
                'high': [b.high for b in bar_list],
                'low': [b.low for b in bar_list],
                'close': [b.close for b in bar_list],
                'volume': [b.volume for b in bar_list],
            }
            
            df = pd.DataFrame(data)
            df['symbol'] = symbol
            
            return df
            
        except Exception as e:
            logger.debug(f"{symbol}: Alpaca bar fetch error: {e}")
            return None
    
    def _validate_and_merge(
        self, 
        symbol: str, 
        yf_data: pd.DataFrame, 
        alpaca_data: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Cross-validate data from both sources and merge
        
        Args:
            symbol: Stock symbol
            yf_data: DataFrame from yfinance
            alpaca_data: DataFrame from Alpaca IEX
            
        Returns:
            Merged/validated DataFrame
        """
        # Get most recent data point from each source
        yf_latest = yf_data.iloc[-1]
        alpaca_latest = alpaca_data.iloc[-1]
        
        # Compare close prices
        yf_close = float(yf_latest['close'])
        alpaca_close = float(alpaca_latest['close'])
        price_diff = abs(yf_close - alpaca_close)
        price_diff_pct = price_diff / alpaca_close if alpaca_close > 0 else 0
        
        # Compare volumes
        yf_volume = float(yf_latest['volume'])
        alpaca_volume = float(alpaca_latest['volume'])
        volume_diff_pct = abs(yf_volume - alpaca_volume) / alpaca_volume if alpaca_volume > 0 else 0
        
        # Validation thresholds
        price_threshold = 0.02  # 2% price difference
        volume_threshold = 0.15  # 15% volume difference
        
        # Check for significant discrepancies
        if price_diff_pct > price_threshold:
            logger.warning(
                f"⚠️  {symbol}: Price mismatch - yfinance: ${yf_close:.2f}, "
                f"Alpaca: ${alpaca_close:.2f} ({price_diff_pct:.1%} diff)"
            )
            # Use Alpaca as authoritative for price (real-time)
            logger.info(f"   Using Alpaca IEX price as authoritative")
            result = yf_data.copy()
            result.iloc[-1, result.columns.get_loc('close')] = alpaca_close
            return result
        
        if volume_diff_pct > volume_threshold:
            logger.debug(
                f"{symbol}: Volume mismatch - yfinance: {yf_volume:,.0f}, "
                f"Alpaca: {alpaca_volume:,.0f} ({volume_diff_pct:.1%} diff)"
            )
            # Use higher volume (more conservative)
            logger.debug(f"   Using higher volume value")
            result = yf_data.copy()
            result.iloc[-1, result.columns.get_loc('volume')] = max(yf_volume, alpaca_volume)
            return result
        
        # Data validated successfully
        logger.debug(f"{symbol}: ✅ Data validated (price diff: {price_diff_pct:.2%}, volume diff: {volume_diff_pct:.2%})")
        return yf_data  # Use yfinance (more historical data)
    
    def get_realtime_price(self, symbol: str) -> Optional[float]:
        """
        Get real-time price from Alpaca IEX
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Current price, or None if unavailable
        """
        if not self.alpaca_client:
            return None
        
        try:
            # Fetch latest bar (1 minute)
            end_time = datetime.now()
            start_time = end_time - timedelta(minutes=5)
            
            request = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=TimeFrame.Minute,
                start=start_time,
                end=end_time,
                limit=1
            )
            
            bars = self.alpaca_client.get_stock_bars(request)
            
            if bars and symbol in bars and len(bars[symbol]) > 0:
                latest_bar = bars[symbol][-1]
                return float(latest_bar.close)
            
            return None
            
        except Exception as e:
            logger.debug(f"{symbol}: Real-time price fetch failed: {e}")
            return None
    
    def batch_validate(self, symbols: List[str], days: int = 5) -> Dict[str, str]:
        """
        Batch validate data quality for multiple symbols
        
        Args:
            symbols: List of stock symbols
            days: Number of days to validate
            
        Returns:
            Dict of {symbol: status} where status is 'valid', 'warning', or 'error'
        """
        results = {}
        
        for symbol in symbols:
            try:
                data = self.get_validated_data(symbol, days=days, validate=True)
                
                if data is None:
                    results[symbol] = 'error'
                elif len(data) < days * 0.8:  # Less than 80% of expected data
                    results[symbol] = 'warning'
                else:
                    results[symbol] = 'valid'
                    
            except Exception as e:
                logger.debug(f"{symbol}: Validation error: {e}")
                results[symbol] = 'error'
        
        # Log summary
        valid_count = sum(1 for s in results.values() if s == 'valid')
        warning_count = sum(1 for s in results.values() if s == 'warning')
        error_count = sum(1 for s in results.values() if s == 'error')
        
        logger.info(
            f"📊 Batch validation: {valid_count} valid, "
            f"{warning_count} warnings, {error_count} errors "
            f"(total: {len(symbols)})"
        )
        
        return results

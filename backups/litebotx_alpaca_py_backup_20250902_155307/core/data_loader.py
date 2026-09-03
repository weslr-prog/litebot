"""
Data Loader for LiteBotX
Purpose: Fetch historical and live market data using Alpaca (IEX feed) with Polygon fallback.
"""

import os
import time
import random
import requests
import pandas as pd
import json
from alpaca.trading.client import TradingClient
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from dotenv import load_dotenv
import logging
from datetime import datetime, timedelta
from core.pre_filter import PreFilter
import yfinance as yf
from utils.logger import log_missing_bars

load_dotenv()

# Configure logging for DataLoader
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

UNIVERSE_CSV = os.path.join(os.path.dirname(__file__), '../data/universe.csv')

class RateLimitHandler:
    """Handles rate limiting for different APIs"""
    
    def __init__(self):
        self.api_call_times = {
            'polygon': [],
            'yfinance': [],
            'alpaca': []
        }
        self.rate_limits = {
            'polygon': {'calls_per_minute': 5, 'burst_limit': 2},  # Free tier: 5 calls/min
            'yfinance': {'calls_per_minute': 60, 'batch_size': 10, 'sleep_between_batches': 5},  # Conservative
            'alpaca': {'calls_per_minute': 200, 'burst_limit': 50}  # Free tier
        }
    
    def wait_if_needed(self, api_name, batch_size=1):
        """Wait if we're hitting rate limits"""
        now = time.time()
        limit_info = self.rate_limits[api_name]
        call_times = self.api_call_times[api_name]
        
        # Remove calls older than 1 minute
        call_times[:] = [t for t in call_times if now - t < 60]
        
        # Check if we need to wait
        calls_per_minute = limit_info['calls_per_minute']
        if len(call_times) + batch_size > calls_per_minute:
            wait_time = 60 - (now - call_times[0]) + 1
            logging.warning(f"Rate limit approaching for {api_name}, waiting {wait_time:.1f}s")
            time.sleep(wait_time)
            # Clear old entries after waiting
            call_times.clear()
        
        # Add this call to tracking
        call_times.append(now)
        
        # Add random jitter to avoid thundering herd
        jitter = random.uniform(0.1, 0.5)
        time.sleep(jitter)

class DataLoader:
    def get_historical_data_bulk(self, symbols, limit=100, timeframe="1Day", start=None, end=None, force_fetch=False, batch_size=100, min_bars=30, yf_batch_size=50, yf_sleep_sec=10):
        """
        Fetch historical data for multiple symbols in batches, prioritizing cached data.
        """
        logging.info(f"Requesting bulk historical data for {len(symbols)} symbols | limit={limit} | timeframe={timeframe}")
        all_bars = []

        for symbol in symbols:
            file_path = os.path.join(self.data_dir, f"{symbol}_historical_data.csv")
            if os.path.exists(file_path) and not force_fetch:
                # Load cached data
                try:
                    df = pd.read_csv(
                        file_path,
                        index_col=0,
                        parse_dates=True,
                        date_format='%Y-%m-%d'
                    )
                    df['symbol'] = symbol
                    all_bars.append(df)
                    logging.info(f"Loaded cached data for {symbol}.")
                    continue
                except Exception as e:
                    logging.warning(f"Failed to load cached data for {symbol}: {e}. Fetching from API...")

            # If no cached data, fetch from API
            try:
                df = self.get_historical_data(symbol, limit=limit, timeframe=timeframe, start=start, end=end, force_fetch=force_fetch)
                if not df.empty:
                    all_bars.append(df)
            except Exception as e:
                logging.error(f"Failed to fetch data for {symbol}: {e}")

        if all_bars:
            result = pd.concat(all_bars, ignore_index=True)
            logging.info(f"Loaded bulk historical data for {len(result['symbol'].unique())} symbols.")
        else:
            result = pd.DataFrame()
            logging.warning("No data loaded for any symbols.")

        return result

    def get_historical_data_bulk_rate_limited(self, symbols, limit=100, timeframe="1Day", 
                                            start=None, end=None, force_fetch=False, 
                                            batch_size=10, max_retries=3):
        """
        Rate-limited bulk data fetching for free APIs
        
        Args:
            symbols: List of symbols to fetch
            batch_size: Number of symbols per batch (keep small for free APIs)
            max_retries: Number of retries for failed requests
        """
        logging.info(f"Starting rate-limited bulk fetch for {len(symbols)} symbols (batch_size={batch_size})")
        
        all_bars = []
        failed_symbols = []
        
        # Process in batches
        for i in range(0, len(symbols), batch_size):
            batch_symbols = symbols[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(symbols) + batch_size - 1) // batch_size
            
            logging.info(f"Processing batch {batch_num}/{total_batches}: {batch_symbols}")
            
            # Rate limit before batch
            self.rate_limiter.wait_if_needed('yfinance', batch_size)
            
            # Process each symbol in the batch
            for symbol in batch_symbols:
                retry_count = 0
                while retry_count < max_retries:
                    try:
                        # Check cache first
                        file_path = os.path.join(self.data_dir, f"{symbol}_historical_data.csv")
                        if os.path.exists(file_path) and not force_fetch:
                            df = pd.read_csv(file_path, index_col=0, parse_dates=True, date_format='%Y-%m-%d')
                            df['symbol'] = symbol
                            all_bars.append(df)
                            logging.info(f"✓ Loaded cached data for {symbol}")
                            break
                        
                        # Fetch from API with rate limiting
                        self.rate_limiter.wait_if_needed('yfinance', 1)
                        df = self.get_historical_data(symbol, limit=limit, timeframe=timeframe, 
                                                    start=start, end=end, force_fetch=force_fetch)
                        
                        if not df.empty:
                            all_bars.append(df)
                            logging.info(f"✓ Fetched data for {symbol} ({len(df)} bars)")
                        else:
                            logging.warning(f"⚠ No data returned for {symbol}")
                        break
                        
                    except Exception as e:
                        retry_count += 1
                        if retry_count < max_retries:
                            wait_time = 2 ** retry_count + random.uniform(0, 1)  # Exponential backoff
                            logging.warning(f"✗ Error fetching {symbol} (attempt {retry_count}/{max_retries}): {e}")
                            logging.info(f"Retrying in {wait_time:.1f}s...")
                            time.sleep(wait_time)
                        else:
                            logging.error(f"✗ Failed to fetch {symbol} after {max_retries} attempts: {e}")
                            failed_symbols.append(symbol)
            
            # Progress update
            progress = min(100, (batch_num / total_batches) * 100)
            logging.info(f"Batch {batch_num}/{total_batches} complete. Progress: {progress:.1f}%")
            
            # Sleep between batches to be respectful to free APIs
            if batch_num < total_batches:  # Don't sleep after last batch
                sleep_time = 2 + random.uniform(0, 1)
                logging.info(f"Sleeping {sleep_time:.1f}s before next batch...")
                time.sleep(sleep_time)
        
        # Summary
        successful_symbols = len(all_bars)
        logging.info(f"Bulk fetch complete: {successful_symbols} successful, {len(failed_symbols)} failed")
        if failed_symbols:
            logging.warning(f"Failed symbols: {failed_symbols}")
        
        if all_bars:
            result = pd.concat(all_bars, ignore_index=True)
            logging.info(f"Final dataset: {len(result)} total bars for {len(result['symbol'].unique())} symbols")
            return result
        else:
            logging.warning("No data fetched for any symbols")
            return pd.DataFrame()

    def get_asset_universe(self, symbols, timeframe="1Day", limit=1):
        """
        Fetch summary (latest bar) data for a list of symbols and return a DataFrame with a 'symbol' column.
        """
        universe_data = []
        for symbol in symbols:
            try:
                # Create request for alpaca-py
                request = StockBarsRequest(
                    symbol_or_symbols=symbol,
                    timeframe=TimeFrame.Day,
                    limit=limit
                )
                bars = self.data_client.get_stock_bars(request).df
                if not bars.empty:
                    latest_bar = bars.iloc[-1]
                    row = {
                        "symbol": symbol,
                        "close": latest_bar["close"],
                        "high": latest_bar["high"],
                        "low": latest_bar["low"],
                        "open": latest_bar["open"],
                        "volume": latest_bar["volume"],
                        "vwap": latest_bar.get("vwap", None),
                        "trade_count": latest_bar.get("trade_count", None),
                        "exchange": "IEX"
                    }
                    universe_data.append(row)
                else:
                    logging.warning(f"No data for symbol {symbol}")
            except Exception as e:
                logging.error(f"Error fetching data for {symbol}: {e}", exc_info=True)
        df = pd.DataFrame(universe_data)
        logging.info(f"Fetched universe data for {len(df)} symbols.")
        return df
    def __init__(self, api_key=None, api_secret=None, polygon_key=None, base_url="https://paper-api.alpaca.markets"):
        # If api_key and api_secret are not provided, try to load from environment variables
        if api_key is None or api_secret is None:
            api_key = os.getenv('APCA_API_KEY_ID')
            api_secret = os.getenv('APCA_API_SECRET_KEY')
            if api_key is None or api_secret is None:
                raise ValueError("API key and secret must be provided or set in environment variables.")

        self.api_key = api_key
        self.api_secret = api_secret
        self.polygon_key = polygon_key
        self.base_url = base_url
        
        # Initialize alpaca-py clients
        # Determine if using paper trading based on base_url
        paper_trading = "paper" in base_url.lower() if base_url else True
        self.trading_client = TradingClient(api_key, api_secret, paper=paper_trading)
        self.data_client = StockHistoricalDataClient(api_key, api_secret)
        
        self.root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.data_dir = os.path.join(self.root_dir, "data")
        os.makedirs(self.data_dir, exist_ok=True)
        self.rate_limiter = RateLimitHandler()  # Add rate limiter
        logging.info(f"DataLoader initialized. Data directory: {self.data_dir}")

        # Debugging: Verify environment variables are loaded
        logging.info(f"APCA_API_KEY_ID: {os.getenv('APCA_API_KEY_ID')}")
        logging.info(f"APCA_API_SECRET_KEY: {os.getenv('APCA_API_SECRET_KEY')}")

    def _save_data(self, df: pd.DataFrame, symbol: str) -> str:
        logging.info(f"Saving data for {symbol} to CSV.")
        if df is None or df.empty:
            logging.warning(f"No data to save for {symbol}.")
            return None
        file_path = os.path.join(self.data_dir, f"{symbol}_historical_data.csv")
        try:
            df.to_csv(file_path, index=True)
            file_size = os.path.getsize(file_path)
            logging.info(f"Successfully saved {symbol} data to {file_path} (Size: {file_size} bytes)")
            return file_path
        except Exception as e:
            logging.error(f"Failed to save {symbol} data: {str(e)}", exc_info=True)
            return None

    def get_historical_data(self, symbol, limit=100, timeframe="1Day", start=None, end=None, force_fetch=False):
        file_path = os.path.join(self.data_dir, f"{symbol}_historical_data.csv")
        logging.info(f"Requesting historical data for {symbol} | limit={limit} | timeframe={timeframe}")
        if not force_fetch and os.path.exists(file_path):
            file_mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
            if file_mod_time > datetime.now() - timedelta(days=1):
                logging.info(f"Loading cached data for {symbol} from {file_path}")
                try:
                    return pd.read_csv(
                        file_path,
                        index_col=0,
                        parse_dates=True,
                        date_format='%Y-%m-%d'
                    )
                except Exception as e:
                    logging.error(f"Error loading cached data for {symbol}: {e}", exc_info=True)
        try:
            logging.info(f"Fetching Alpaca data for {symbol}...")
            if not start:
                start = datetime.now() - timedelta(days=365)
            if not end:
                end = datetime.now()
            
            # Create request for alpaca-py
            request = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=TimeFrame.Day,
                start=start,
                end=end,
                limit=limit
            )
            bars = self.data_client.get_stock_bars(request).df
            if not bars.empty:
                bars['exchange'] = 'IEX'
                self._save_data(bars, symbol)
                logging.info(f"Fetched and saved Alpaca data for {symbol}.")
                return bars
            else:
                logging.warning(f"No Alpaca data returned for {symbol}.")
        except Exception as e:
            logging.error(f"Error fetching Alpaca data for {symbol}: {e}", exc_info=True)
        try:
            polygon_data = self._polygon_fallback(symbol, limit)
            if not polygon_data.empty:
                polygon_data['exchange'] = 'POLYGON'
                self._save_data(polygon_data, symbol)
                logging.info(f"Fetched and saved Polygon data for {symbol}.")
                return polygon_data
            else:
                logging.warning(f"No Polygon data returned for {symbol}.")
        except Exception as e:
            logging.error(f"Polygon fallback failed for {symbol}: {e}", exc_info=True)
        logging.error(f"Failed to fetch any historical data for {symbol}.")
        return pd.DataFrame()

    def _polygon_fallback(self, symbol, limit):
        """
        Fetch historical data from Polygon.io if Alpaca fails.
        """
        if not self.polygon_key:
            logging.error(f"No Polygon API key found in environment variables. Cannot fetch {symbol}.")
            return pd.DataFrame()

        try:
            logging.info(f"Fetching Polygon data for {symbol}...")
            url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/day/2020-01-01/2025-12-31"
            params = {
                "adjusted": "true",
                "sort": "desc",
                "limit": limit,
                "apiKey": self.polygon_key
            }
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json().get("results", [])

            if not data:
                logging.warning(f"Polygon returned no data for {symbol}.")
                return pd.DataFrame()

            df = pd.DataFrame(data)
            df["t"] = pd.to_datetime(df["t"], unit="ms")
            df.set_index("t", inplace=True)
            return df

        except Exception as e:
            logging.error(f"Polygon fetch failed for {symbol}: {e}")
            return pd.DataFrame()

    def fetch_historical_data(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        """Fetch historical data from Alpaca's API."""
        ALPACA_API_KEY = os.getenv("APCA_API_KEY_ID")
        ALPACA_SECRET_KEY = os.getenv("APCA_API_SECRET_KEY")
        BASE_URL = "https://data.alpaca.markets/v2/stocks"

        headers = {
            "APCA-API-KEY-ID": ALPACA_API_KEY,
            "APCA-API-SECRET-KEY": ALPACA_SECRET_KEY
        }

        url = f"{BASE_URL}/{symbol}/bars"
        params = {
            "start": start,
            "end": end,
            "timeframe": "1Day"
        }

        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()  # Raise an error for bad responses

        data = response.json()
        if "bars" not in data:
            raise ValueError("No data returned from API")

        # Convert the data to a DataFrame
        df = pd.DataFrame(data["bars"])
        df["timestamp"] = pd.to_datetime(df["t"], unit="s")
        df.rename(columns={"o": "open", "h": "high", "l": "low", "c": "close", "v": "volume"}, inplace=True)
        df = df[["timestamp", "open", "high", "low", "close", "volume"]]

        return df

    def load_historical_data(self, symbol: str, start: str, end: str, data_dir: str = "data") -> pd.DataFrame:
        """
        Load historical data from a local file if it exists and is fresh.
        Otherwise, fetch it from the API and save it locally.
        """
        os.makedirs(data_dir, exist_ok=True)  # Ensure the data directory exists
        file_path = os.path.join(data_dir, f"{symbol}_historical_data.csv")

        logging.debug(f"Checking for file at: {file_path}")

        # Check if the file exists and is fresh
        if os.path.exists(file_path):
            file_mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
            logging.debug(f"File modification time: {file_mod_time}")
            if file_mod_time > datetime.now() - timedelta(days=1):
                logging.info(f"Loading data from {file_path}")
                return pd.read_csv(file_path)

        # Fetch new data if the file is missing or outdated
        logging.info("Fetching new data from the API...")
        data = self.fetch_historical_data(symbol, start, end)

        if data.empty:
            logging.error("Fetched data is empty. Not saving to file.")
            raise ValueError("No data fetched from the API.")

        logging.debug(f"Saving data to: {file_path}")
        data.to_csv(file_path, index=False)
        logging.info(f"Data saved to {file_path}")
        return data

    def get_filtered_historical_data(self, asset_list, limit=100, timeframe="1Day", start=None, end=None, force_fetch=False):
        """
        Full workflow: filter tradable assets, fetch universe summary, apply price, liquidity/volatility, and momentum filters,
        then fetch historical data in batches for survivors.
        """
        pre = PreFilter()
        # Step 1: Tradability filter
        tradable_assets = pre.tradability_filter(asset_list)
        symbols = [a.symbol for a in tradable_assets]
        # Step 2: Fetch universe summary (latest bar for each symbol)
        universe_df = self.get_asset_universe(symbols, timeframe=timeframe, limit=1)
        # Step 3: Apply IEX-optimized filtering pipeline
        survivors_df = pre.iex_optimized_filter_pipeline(universe_df)
        survivor_symbols = survivors_df['symbol'].tolist() if not survivors_df.empty and 'symbol' in survivors_df.columns else []
        # Step 4: Fetch historical data in batches for survivors
        batch_size = pre.BATCH_SIZE
        historical_df = self.get_historical_data_bulk(survivor_symbols, limit=limit, timeframe=timeframe, start=start, end=end, force_fetch=force_fetch, batch_size=batch_size)
        return historical_df

    def load_universe(self, sector_whitelist=None):
        """
        Load filtered trading universe from universe.csv.
        Optionally filter by sector whitelist.
        Returns a DataFrame with columns: symbol, name, exchange, sector, market_cap, tradable, delisted
        """
        df = pd.read_csv(UNIVERSE_CSV)
        
        # Filter by tradable status if column exists
        if 'tradable' in df.columns:
            df = df[df['tradable']]
        
        # Filter out delisted if column exists
        if 'delisted' in df.columns:
            df = df[~df['delisted']]
            
        if sector_whitelist and 'sector' in df.columns:
            df = df[df['sector'].isin(sector_whitelist)]
        return df.reset_index(drop=True)

    def get_price_history(self, symbol, start=None, end=None):
        """
        Fetch historical daily price data for a symbol using yfinance.
        Fallback to Polygon if yfinance fails.
        Returns a DataFrame with columns: date, open, high, low, close, volume
        """
        try:
            # Retry yfinance single-symbol pulls (now available)
            attempts = 0
            df = pd.DataFrame()
            while attempts < 3:
                try:
                    df = yf.download(symbol, start=start, end=end, interval='1d', auto_adjust=True, progress=False)
                    break
                except Exception as ye:
                    attempts += 1
                    wait = min(8, 2 ** attempts) + random.uniform(0, 0.5)
                    logging.warning(f"yfinance single fetch attempt {attempts} failed for {symbol}: {ye}. Retrying in {wait:.2f}s...")
                    time.sleep(wait)
            if not df.empty:
                df = df.reset_index()
                df['symbol'] = symbol
                return df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume', 'symbol']].rename(columns={
                    'Date': 'date', 'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'
            })
        except Exception as e:
            print(f"yfinance failed for {symbol}: {e}")
        # Fallback to Polygon
        try:
            url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/day/2020-01-01/{end or '2025-12-31'}"
            params = {
                "adjusted": "true",
                "sort": "desc",
                "limit": 1000,
                "apiKey": self.polygon_key
            }
            resp = requests.get(url, params=params)
            resp.raise_for_status()
            data = resp.json().get("results", [])
            if not data:
                return pd.DataFrame()
            df = pd.DataFrame(data)
            df["date"] = pd.to_datetime(df["t"], unit="ms")
            df = df.rename(columns={"o": "open", "h": "high", "l": "low", "c": "close", "v": "volume"})
            df["symbol"] = symbol
            return df[["date", "open", "high", "low", "close", "volume", "symbol"]]
        except Exception as e:
            print(f"Polygon fallback failed for {symbol}: {e}")
            return pd.DataFrame()

    def get_live_price(self, symbol):
        """
        Fetch the latest price bar for a symbol using Alpaca/IEX.
        Returns a dict with keys: symbol, date, open, high, low, close, volume
        """
        try:
            # Retry a couple times and check freshness of the bar
            attempts = 0
            bars = pd.DataFrame()
            while attempts < 3:
                try:
                    # Create request for alpaca-py with 1-minute timeframe
                    request = StockBarsRequest(
                        symbol_or_symbols=symbol,
                        timeframe=TimeFrame.Minute,
                        limit=1
                    )
                    bars = self.data_client.get_stock_bars(request).df
                    break
                except Exception as e:
                    attempts += 1
                    wait = min(8, 2 ** attempts) + random.uniform(0, 0.5)
                    logging.warning(f"Alpaca live price attempt {attempts} failed for {symbol}: {e}. Retrying in {wait:.2f}s...")
                    time.sleep(wait)
            if not bars.empty:
                bar = bars.iloc[-1]
                # Freshness check: ensure the bar is not stale (>2 minutes old)
                try:
                    ts = pd.to_datetime(bar.name)
                    if isinstance(ts, pd.Timestamp):
                        age_sec = (datetime.utcnow() - ts.to_pydatetime().replace(tzinfo=None)).total_seconds()
                        if age_sec > 120:
                            logging.warning(f"Live bar for {symbol} is stale by {age_sec:.0f}s.")
                except Exception:
                    pass
                return {
                    'symbol': symbol,
                    'date': bar.name,
                    'open': bar['open'],
                    'high': bar['high'],
                    'low': bar['low'],
                    'close': bar['close'],
                    'volume': bar['volume']
                }
        except Exception as e:
            print(f"Alpaca/IEX live price failed for {symbol}: {e}")
        return None

    def fetch_and_cache_price_history(self, start=None, end=None, max_per_run=5, sleep_sec=60):
        """
        Batch fetch daily price history for all tickers in universe.csv.
        Uses yfinance (Polygon fallback) and saves each symbol's history to data/{symbol}_history.csv.
        Limits batch size and adds sleep to avoid rate limits.
        """
        universe = self.load_universe()
        symbols = universe['symbol'].tolist()
        data_dir = os.path.join(os.path.dirname(__file__), '../data')
        os.makedirs(data_dir, exist_ok=True)
        count = 0
        for symbol in symbols:
            file_path = os.path.join(data_dir, f'{symbol}_history.csv')
            if os.path.exists(file_path):
                continue  # Skip if already cached
            try:
                df = self.get_price_history(symbol, start=start, end=end)
                if not df.empty:
                    df.to_csv(file_path, index=False)
                    print(f'Saved history for {symbol} ({len(df)} rows)')
                else:
                    print(f'No history for {symbol} from yfinance, trying Polygon fallback...')
                    df_poly = self.get_price_history(symbol, start=start, end=end)
                    if not df_poly.empty:
                        df_poly.to_csv(file_path, index=False)
                        print(f'Saved Polygon fallback history for {symbol} ({len(df_poly)} rows)')
                    else:
                        print(f'No history for {symbol} from Polygon either.')
            except Exception as e:
                print(f"Error fetching history for {symbol}: {e}")
                while True:
                    user_input = input("[R]etry, [S]kip, or [E]xit? ").strip().lower()
                    if user_input == 'r':
                        print("Retrying...")
                        continue  # Will retry the same symbol
                    elif user_input == 's':
                        print("Skipping...")
                        break  # Skip to next symbol
                    elif user_input == 'e':
                        print("Exiting batch fetcher.")
                        return
                    else:
                        print("Invalid input. Please enter R, S, or E.")
                continue
            count += 1
            if count >= max_per_run:
                print(f'Batch limit ({max_per_run}) reached. Run again to process more.')
                break
            time.sleep(sleep_sec)

    # Multi-Stage Filtering Pipeline
    def multi_stage_filtering(self, universe):
        """
        Multi-stage filtering pipeline to reduce the universe of stocks.
        Stage 1: Static filters (e.g., price, volume).
        Stage 2: Lightweight API filters (e.g., fundamentals).
        Stage 3: Detailed data for final candidates.
        """
        # Stage 1: Static filters
        filtered_universe = [
            stock for stock in universe
            if stock['price'] > 5 and stock['price'] < 500 and stock['volume'] > 50000
        ]

        # Stage 2: Lightweight API filters
        lightweight_filtered = []
        for stock in filtered_universe:
            try:
                # Example: Fetch basic fundamentals from a lightweight API
                fundamentals = self.get_lightweight_fundamentals(stock['symbol'])
                if fundamentals['pe_ratio'] < 20 and fundamentals['debt_to_equity'] < 1:
                    lightweight_filtered.append(stock)
            except Exception as e:
                logging.warning(f"Failed to fetch fundamentals for {stock['symbol']}: {e}")

        # Stage 3: Detailed data for final candidates
        final_candidates = self.get_historical_data_bulk(
            [stock['symbol'] for stock in lightweight_filtered]
        )

        return final_candidates

    def get_lightweight_fundamentals(self, symbol):
        """
        Fetch lightweight fundamentals for a stock symbol (e.g., from a free API).
        """
        # Example: Replace with actual API call
        return {
            'pe_ratio': 15,
            'debt_to_equity': 0.5
        }

    # Tiered Caching System
    def get_cached_data(self, symbol, data_type):
        """
        Retrieve cached data based on data type.
        """
        cache_file = f"cache/{symbol}_{data_type}.json"
        if os.path.exists(cache_file):
            with open(cache_file, 'r') as f:
                return json.load(f)
        return None

    def cache_data(self, symbol, data_type, data):
        """
        Cache data to a file for reuse.
        """
        os.makedirs('cache', exist_ok=True)
        cache_file = f"cache/{symbol}_{data_type}.json"
        with open(cache_file, 'w') as f:
            json.dump(data, f)

    def create_universe_csv(self, symbols, sectors, exchanges, output_path=UNIVERSE_CSV):
        """
        Create the universe.csv file with the given symbols, sectors, and exchanges.
        """
        logging.info("Creating universe.csv file...")
        try:
            data = {
                "symbol": symbols,
                "sector": sectors,
                "exchange": exchanges,
                "tradable": [True] * len(symbols),
                "delisted": [False] * len(symbols)
            }
            df = pd.DataFrame(data)
            df.to_csv(output_path, index=False)
            logging.info(f"universe.csv created successfully at {output_path}")
        except Exception as e:
            logging.error(f"Failed to create universe.csv: {e}", exc_info=True)

    def load_from_cache(self, symbol, **kwargs):
        """
        Load data from local cache.
        Returns cached data if available and fresh, otherwise returns None.
        """
        file_path = os.path.join(self.data_dir, f"{symbol}_historical_data.csv")
        if not os.path.exists(file_path):
            logging.debug(f"No cache file found for {symbol}")
            return None
        
        try:
            # Check if cache is fresh (within 24 hours)
            file_mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
            if file_mod_time > datetime.now() - timedelta(days=1):
                logging.info(f"Loading cached data for {symbol}")
                df = pd.read_csv(
                    file_path,
                    index_col=0,
                    parse_dates=True,
                    date_format='%Y-%m-%d'
                )
                df['symbol'] = symbol
                return df
            else:
                logging.debug(f"Cache file for {symbol} is stale")
                return None
        except Exception as e:
            logging.error(f"Error loading cached data for {symbol}: {e}")
            return None

    def load_from_source(self, symbol, **kwargs):
        """
        Load data from external source (Alpaca/Polygon/yfinance).
        This method fetches fresh data from APIs.
        """
        limit = kwargs.get('limit', 100)
        timeframe = kwargs.get('timeframe', '1Day')
        start = kwargs.get('start')
        end = kwargs.get('end')
        
        try:
            # Try Alpaca first
            logging.info(f"Fetching data from source for {symbol}")
            if not start:
                start = datetime.now() - timedelta(days=365)
            if not end:
                end = datetime.now()
                
            # Create request for alpaca-py
            request = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=TimeFrame.Day,
                start=start,
                end=end,
                limit=limit
            )
            bars = self.data_client.get_stock_bars(request).df
            
            if not bars.empty:
                bars['exchange'] = 'IEX'
                bars['symbol'] = symbol
                self._save_data(bars, symbol)
                return bars
            else:
                logging.warning(f"No data from Alpaca for {symbol}")
        except Exception as e:
            logging.warning(f"Alpaca fetch failed for {symbol}: {e}")
        
        # Fallback to Polygon
        try:
            polygon_data = self._polygon_fallback(symbol, limit)
            if not polygon_data.empty:
                polygon_data['exchange'] = 'POLYGON'
                polygon_data['symbol'] = symbol
                self._save_data(polygon_data, symbol)
                return polygon_data
        except Exception as e:
            logging.error(f"Polygon fallback failed for {symbol}: {e}")
        
        # Final fallback to yfinance
        try:
            logging.info(f"Trying yfinance fallback for {symbol}")
            df = self.get_price_history(symbol, start=start, end=end)
            if not df.empty:
                df['exchange'] = 'YAHOO'
                return df
        except Exception as e:
            logging.error(f"yfinance fallback failed for {symbol}: {e}")
        
        logging.error(f"All data sources failed for {symbol}")
        return pd.DataFrame()

    def load(self, symbol, **kwargs):
        """
        Load data with caching strategy.
        First tries cache, then falls back to source if cache miss or stale.
        """
        force_fetch = kwargs.get('force_fetch', False)
        
        if not force_fetch:
            # Try cache first
            cached_data = self.load_from_cache(symbol, **kwargs)
            if cached_data is not None:
                # Handle both DataFrame and dict returns
                if hasattr(cached_data, 'empty') and not cached_data.empty:
                    logging.debug(f"Cache hit for {symbol}")
                    return cached_data
                elif isinstance(cached_data, dict) and cached_data:
                    logging.debug(f"Cache hit for {symbol}")
                    return cached_data
        
        # Cache miss or force fetch - load from source
        logging.debug(f"Cache miss for {symbol}, loading from source")
        return self.load_from_source(symbol, **kwargs)

    def load_with_rate_limit(self, symbol, max_retries=3, **kwargs):
        """
        Load data with rate limit handling and retries.
        """
        import time
        import random
        
        for attempt in range(max_retries):
            try:
                return self.load(symbol, **kwargs)
            except Exception as e:
                if "rate limit" in str(e).lower() or "429" in str(e):
                    if attempt == max_retries - 1:
                        raise Exception("Rate limit exceeded")
                    # Exponential backoff with jitter
                    wait_time = (2 ** attempt) + random.uniform(0, 1)
                    logging.warning(f"Rate limit hit for {symbol}, retrying in {wait_time:.2f}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                else:
                    raise e
        
        raise Exception("Rate limit exceeded")

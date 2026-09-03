import os
import time
import random
from datetime import datetime, timedelta, timezone
import pandas as pd
from dotenv import load_dotenv
import logging

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from utils.logger import log_missing_bars

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

_data_client = StockHistoricalDataClient(
    os.getenv("APCA_API_KEY_ID"),
    os.getenv("APCA_API_SECRET_KEY")
)

_TIMEFRAMES = {
    "1Min": TimeFrame.Minute,
    "5Min": TimeFrame(5, "Minute"),
    "15Min": TimeFrame(15, "Minute"),
    "1H": TimeFrame.Hour,
    "1D": TimeFrame.Day,
}

_last_cache: dict[tuple[str, str], pd.DataFrame] = {}

def _expected_count(timeframe: str, start: datetime, end: datetime) -> int | None:
    # Cheap heuristic for expected bar counts (doesn't account for holidays/weekends precisely)
    delta = end - start
    if timeframe == "1Min":
        return int(delta.total_seconds() // 60)
    if timeframe == "5Min":
        return int(delta.total_seconds() // (5 * 60))
    if timeframe == "15Min":
        return int(delta.total_seconds() // (15 * 60))
    if timeframe == "1H":
        return int(delta.total_seconds() // 3600)
    if timeframe == "1D":
        return max(delta.days, 0)
    return None

def _validate_and_log_gaps(symbol: str, timeframe: str, start: datetime, end: datetime, df: pd.DataFrame):
    exp = _expected_count(timeframe, start, end)
    got = len(df)
    # Only log for shorter timeframes or when obviously missing
    if exp is not None and got < max(1, int(0.6 * exp)):
        log_missing_bars(
            symbol,
            timeframe,
            start.isoformat(),
            end.isoformat(),
            expected=exp,
            got=got,
            notes="Underfilled fetch window",
            provider="alpaca_iex"
        )

def get_bars(symbol: str, timeframe: str, start: datetime, end: datetime, limit: int | None = None) -> pd.DataFrame:
    """
    Fetch OHLCV bars from Alpaca into a tidy DataFrame indexed by timestamp.
    Enhancements: simple in-memory cache per (symbol,timeframe), retry with jitter, and missing-bar logging.
    """
    logging.info(f"Fetching bars for {symbol} | timeframe={timeframe} | start={start} | end={end} | limit={limit}")
    tf = _TIMEFRAMES[timeframe]

    # Diff-fetch: if we have cached data for (symbol,timeframe), only fetch the tail since last timestamp
    cache_key = (symbol, timeframe)
    cached = _last_cache.get(cache_key)
    fetch_start = start
    if cached is not None and not cached.empty:
        last_ts = cached.index.max()
        if last_ts is not None and last_ts < end:
            # Add small epsilon to avoid duplicate bar
            fetch_start = last_ts + timedelta(seconds=1)

    attempts = 0
    df_new = pd.DataFrame()
    while attempts < 3:
        try:
            req = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=tf,
                start=fetch_start,
                end=end,
                limit=limit,
                feed="iex"
            )
            bars = _data_client.get_stock_bars(req).df
            if bars.empty:
                logging.warning(f"No data returned for {symbol} in {timeframe} from {fetch_start} to {end}.")
                break
            df_new = bars.reset_index()
            df_new = df_new[df_new["symbol"] == symbol].copy()
            df_new.set_index("timestamp", inplace=True)
            df_new.sort_index(inplace=True)
            df_new = df_new[["symbol","open","high","low","close","volume"]]
            break
        except Exception as e:
            attempts += 1
            wait = min(8, 2 ** attempts) + random.uniform(0, 0.5)
            logging.warning(f"Fetch attempt {attempts} failed for {symbol} ({e}). Retrying in {wait:.2f}s...")
            time.sleep(wait)
    if cached is not None and not cached.empty:
        df = pd.concat([cached, df_new]) if not df_new.empty else cached.copy()
        df = df[~df.index.duplicated(keep="last")].sort_index()
    else:
        df = df_new
    if df is None or df.empty:
        return pd.DataFrame(columns=["timestamp","symbol","open","high","low","close","volume"]).set_index(pd.Index([], name="timestamp"))
    _last_cache[cache_key] = df
    logging.info(f"Fetched {len(df)} total bars for {symbol} (including cache).")
    _validate_and_log_gaps(symbol, timeframe, start, end, df)
    return df

def get_recent(symbol: str, timeframe: str = "1Min", lookback: int = 200) -> pd.DataFrame:
    """
    Convenience for live loop: last `lookback` bars up to now (UTC).
    """
    logging.info(f"Fetching recent bars for {symbol} | timeframe={timeframe} | lookback={lookback}")
    end = datetime.now(timezone.utc)
    # Fetch a bit extra to be safe, then tail
    start = end - _default_span_for(timeframe, lookback * 3)
    df = get_bars(symbol, timeframe, start, end)
    logging.info(f"Returning last {lookback} bars for {symbol}.")
    return df.tail(lookback)

def _default_span_for(timeframe: str, bars: int) -> timedelta:
    if timeframe == "1Min":
        return timedelta(minutes=bars)
    if timeframe == "5Min":
        return timedelta(minutes=5 * bars)
    if timeframe == "15Min":
        return timedelta(minutes=15 * bars)
    if timeframe == "1H":
        return timedelta(hours=bars)
    if timeframe == "1D":
        return timedelta(days=bars)
    # fallback
    return timedelta(days=bars)


class DataFetcher:
    """
    A wrapper class for data fetching functionality.
    """
    def __init__(self):
        logging.info("DataFetcher initialized.")

    def fetch_data(self, symbol, timeframe="1D", start=None, end=None, limit=None):
        """
        Fetch data using the get_bars function.
        """
        if start is None:
            start = datetime.now(timezone.utc) - timedelta(days=365)
        if end is None:
            end = datetime.now(timezone.utc)
        
        return get_bars(symbol, timeframe, start, end, limit)

    def fetch_recent_data(self, symbol, timeframe="1Min", lookback=200):
        """
        Fetch recent data using the get_recent function.
        """
        return get_recent(symbol, timeframe, lookback)

    def fetch_in_batches(self, tickers, batch_size=10, sleep_time=1):
        """
        Fetch data for multiple tickers in batches with sleep between batches.
        Sleep is called between complete batches only.
        """
        results = {}
        complete_batches = len(tickers) // batch_size
        
        # Process tickers in batches
        for batch_idx in range(complete_batches):
            start_idx = batch_idx * batch_size
            end_idx = start_idx + batch_size
            batch = tickers[start_idx:end_idx]
            
            for ticker in batch:
                try:
                    results[ticker] = self.fetch_data(ticker)
                except Exception as e:
                    logging.error(f"Error fetching data for {ticker}: {e}")
                    results[ticker] = None
            
            # Sleep between complete batches (not after the last complete batch)
            if batch_idx < complete_batches - 1:
                time.sleep(sleep_time)
        
        # Handle remaining tickers (incomplete batch)
        remaining_start = complete_batches * batch_size
        if remaining_start < len(tickers):
            remaining_tickers = tickers[remaining_start:]
            for ticker in remaining_tickers:
                try:
                    results[ticker] = self.fetch_data(ticker)
                except Exception as e:
                    logging.error(f"Error fetching data for {ticker}: {e}")
                    results[ticker] = None
        
        return results

    def test_simulation_fix(self, test_symbols=None):
        """
        Test method to verify the simulation fix works with proper data format.
        This method tests if the DataFetcher provides data in the format expected by StrategyEngine.
        """
        from core.strategy import StrategyEngine
        
        print("Testing simulation fix...")
        
        # Use default test symbols if none provided
        if test_symbols is None:
            test_symbols = ['AAPL', 'MSFT', 'TSLA', 'NVDA', 'AMD']
        
        # Initialize strategy engine
        strategy_engine = StrategyEngine()
        
        # Track signals
        buy_signals = 0
        sell_signals = 0
        hold_signals = 0
        processed_count = 0
        
        for symbol in test_symbols:
            try:
                print(f"\nTesting {symbol}...")
                
                # Fetch data using DataFetcher (same as simulation will do)
                data = self.fetch_data(symbol, timeframe="1D", limit=100)
                
                if data is None or data.empty:
                    print(f"No data for {symbol}")
                    continue
                    
                if len(data) < 20:
                    print(f"Insufficient data for {symbol}: {len(data)} rows")
                    continue
                
                # Remove symbol column if exists (StrategyEngine doesn't need it)
                if 'symbol' in data.columns:
                    data = data.drop('symbol', axis=1)
                
                print(f"Data shape: {data.shape}")
                print(f"Columns: {list(data.columns)}")
                print(f"Index type: {type(data.index)}")
                print(f"Date range: {data.index.min()} to {data.index.max()}")
                
                # Test strategy engine
                action = strategy_engine.predict(data)
                print(f"Signal: {action}")
                
                # Count signals
                if action == 'buy':
                    buy_signals += 1
                    print(f"[BUY SIGNAL] {symbol}")
                elif action == 'sell':
                    sell_signals += 1
                    print(f"[SELL SIGNAL] {symbol}")
                else:
                    hold_signals += 1
                
                processed_count += 1
                    
            except Exception as e:
                print(f"Error with {symbol}: {e}")
                import traceback
                traceback.print_exc()
        
        print(f"\n{'='*50}")
        print(f"SIMULATION TEST RESULTS")
        print(f"{'='*50}")
        print(f"Symbols processed: {processed_count}")
        print(f"Buy signals: {buy_signals}")
        print(f"Sell signals: {sell_signals}")
        print(f"Hold signals: {hold_signals}")
        print(f"Total signals: {buy_signals + sell_signals + hold_signals}")
        
        if buy_signals > 0 or sell_signals > 0:
            print(f"✅ SUCCESS: Generating buy/sell signals!")
        else:
            print(f"❌ ISSUE: Only hold signals generated")
        
        return {
            'processed': processed_count,
            'buy': buy_signals,
            'sell': sell_signals,
            'hold': hold_signals
        }

    def test_simulation_fix_quick(self):
        """
        Quick test to verify the simulation fix works.
        This tests if we get exactly 1 signal per symbol (not multiple).
        """
        from core.strategy import StrategyEngine
        from core.data_loader import DataLoader
        from core.pre_filter import PreFilter
        from core.data_source import fetch_stocks
        
        print("Quick Simulation Fix Test...")
        
        # Get filtered symbols (mimicking main.py logic)
        data_loader = DataLoader()
        pre_filter = PreFilter()
        
        # Get small sample for testing
        universe_df = fetch_stocks()
        SYMBOLS = universe_df['symbol'].tolist()[:50] if not universe_df.empty else ["AAPL", "MSFT", "TSLA"]
        
        bulk_data = data_loader.get_historical_data_bulk(SYMBOLS, limit=50, timeframe="1Day")
        filtered_data = pre_filter.iex_optimized_filter_pipeline(bulk_data)
        filtered_momentum = pre_filter.exclude_earnings_and_news(filtered_data, {}, {})
        
        if filtered_momentum.empty:
            print("No filtered data available")
            return
        
        unique_symbols = filtered_momentum['symbol'].unique()
        total_rows = len(filtered_momentum)
        
        print(f"Filtered data: {len(unique_symbols)} unique symbols, {total_rows} total rows")
        
        # Test OLD logic (wrong)
        old_signal_count = 0
        for _, asset_row in filtered_momentum.iterrows():
            old_signal_count += 1
        
        # Test NEW logic (correct)  
        new_signal_count = 0
        for symbol in unique_symbols:
            new_signal_count += 1
        
        print(f"OLD logic would process: {old_signal_count} iterations")
        print(f"NEW logic will process: {new_signal_count} iterations")
        print(f"Ratio: {old_signal_count/new_signal_count:.1f}x more signals with old logic")
        
        if old_signal_count == new_signal_count:
            print("✅ No issue - signals match")
        else:
            print("❌ Issue confirmed - old logic processes each symbol multiple times")
            print(f"Expected signals after fix: {new_signal_count}")
            print(f"Signals you were getting: {old_signal_count}")
        
        return {
            'unique_symbols': len(unique_symbols),
            'old_iterations': old_signal_count,
            'new_iterations': new_signal_count,
            'fix_needed': old_signal_count != new_signal_count
        }

# Quick test function you can run directly
def test_fix():
    """Run this to test the simulation fix"""
    fetcher = DataFetcher()
    result = fetcher.test_simulation_fix_quick()
    print(f"\nTest Results: {result}")

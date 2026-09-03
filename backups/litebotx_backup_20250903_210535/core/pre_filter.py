"""
Pre-Filter Module
Purpose: Filter the list of tradable assets before strategies are run.
Examples: Volume/liquidity filters, price filters, volatility filters.
"""

import pandas as pd
import numpy as np
import logging
import time  # Ensure the time module is imported for sleep functionality

# Ensure logging is configured
logging.basicConfig(level=logging.DEBUG)

class PreFilter:
    # --- Q) Earnings/News Landmines ---
    def exclude_earnings_and_news(self, df, earnings_dates, news_spikes=None):
        """
        Exclude tickers with earnings ±2 trading days (unless earnings strategy).
        Exclude news spike gappers beyond ±6%.
        """
        if df.empty:
            logging.warning("No data provided to exclude_earnings_and_news. Returning empty DataFrame.")
            return df

        if 'date' not in df.columns or 'symbol' not in df.columns:
            logging.error("Required columns ('date', 'symbol') not found in DataFrame.")
            return df

        mask = pd.Series([True] * len(df), index=df.index)
        for symbol, dates in earnings_dates.items():
            for edate in dates:
                mask &= ~((df['symbol'] == symbol) & (abs((df['date'] - edate).dt.days) <= 2))
        if news_spikes is not None:
            for symbol, spike_dates in news_spikes.items():
                for sdate in spike_dates:
                    gap = df[(df['symbol'] == symbol) & (df['date'] == sdate)]['overnight_gap']
                    if not gap.empty and abs(gap.iloc[0]) > 0.06:
                        mask &= ~((df['symbol'] == symbol) & (df['date'] == sdate))
        return df[mask]
            # Alternative robust fix for ATR calculation
            # df['atr_14'] = df.groupby('symbol').transform(lambda x: (x['high'] - x['low']).rolling(14).mean() / x['close'])
    def __init__(self, simulation_mode=False, historical_data=None):
        logging.info(f"Initializing PreFilter | simulation_mode={simulation_mode}")
        """
        Initialize the PreFilter module.
        :param simulation_mode: If True, use historical data for testing.
        :param historical_data: DataFrame containing historical data for simulation.
        """
        self.simulation_mode = simulation_mode
        self.historical_data = historical_data
        # Preferred filter constants
        self.MIN_AVG_DOLLAR_VOL = 2_000_000
        self.MIN_AVG_VOL = 10000
        self.MAX_ATR = 0.3
        self.MIN_MOMENTUM_RETURN = 0.02
        self.MIN_PRICE = 2.0
        self.MIN_SURVIVORS = 50
        self.BATCH_SIZE = 120  # For Alpaca free tier reliability
        self.CACHE_DAILY = 3  # days
        self.CACHE_INTRADAY = 0.02  # ~30 minutes

    # --- G) Sector/ETF Tagging ---
    def tag_sector_etf(self, ticker):
        """Enhanced mapping for sector/ETF tagging with debugging."""
        sector_map = {
            'AAPL': 'tech', 'MSFT': 'tech', 'GOOGL': 'tech', 'AMZN': 'consumer', 'TSLA': 'auto', 'XLF': 'finance', 'SPY': 'etf',
            'AA': 'materials', 'BA': 'aerospace', 'CAT': 'industrials', 'DIS': 'entertainment', 'F': 'auto', 'GE': 'industrials',
            'JNJ': 'healthcare', 'KO': 'consumer', 'MCD': 'consumer', 'NKE': 'consumer', 'PFE': 'healthcare', 'PG': 'consumer',
            'WMT': 'retail', 'XOM': 'energy'
        }
        etf_map = {
            'AAPL': 'QQQ', 'MSFT': 'QQQ', 'GOOGL': 'QQQ', 'AMZN': 'QQQ', 'TSLA': 'QQQ', 'XLF': 'SPY', 'SPY': 'SPY',
            'AA': None, 'BA': None, 'CAT': None, 'DIS': None, 'F': None, 'GE': None,
            'JNJ': None, 'KO': None, 'MCD': None, 'NKE': None, 'PFE': None, 'PG': None,
            'WMT': None, 'XOM': None
        }
        sector = sector_map.get(ticker, 'unknown')
        etf = etf_map.get(ticker, None)
        logging.info(f"Ticker: {ticker}, Sector: {sector}, ETF: {etf}")
        return sector, etf

    # Remove sector cap logic by bypassing the check
    def check_sector_etf_cap(self, open_positions, symbol, sector_map, etf_map):
        """Bypass sector/ETF cap logic temporarily."""
        logging.info("Sector/ETF cap logic bypassed. Allowing unrestricted trading.")
        return True

    def filter_insufficient_lookback_data(self, df, lookback=10):
        """
        Filter out assets that do not have enough data for the specified lookback period.
        """
        logging.info(f"Filtering assets with insufficient lookback data. Minimum rows required: {lookback}")
        sufficient_data = df.groupby('symbol').filter(lambda x: len(x) >= lookback)
        logging.info(f"Assets remaining after filtering insufficient lookback data: {len(sufficient_data['symbol'].unique())}")

        # Pause to review results
        import time
        logging.info("Pausing for 5 seconds to review insufficient lookback data filter results...")
        time.sleep(5)

        return sufficient_data

    def liquidity_volatility_filter(self, df, min_avg_vol=100, max_atr=5.0, min_survivors=None):
        logging.info(f"Applying liquidity/volatility filter to {len(df)} assets.")
        try:
            # Filter out assets without enough lookback data
            df = self.filter_insufficient_lookback_data(df, lookback=10)

            min_avg_dollar_vol = 25000  # Loosened threshold
            # Fix: Ensure all 'date' values are tz-aware UTC
            if 'date' in df.columns:
                if not pd.api.types.is_datetime64_any_dtype(df['date']):
                    df['date'] = pd.to_datetime(df['date'], errors='coerce')
                if df['date'].dt.tz is None:
                    df['date'] = df['date'].dt.tz_localize('UTC')
                else:
                    df['date'] = df['date'].dt.tz_convert('UTC')
            else:
                # Create a date column from index if possible
                if isinstance(df.index, pd.DatetimeIndex):
                    if df.index.tz is None:
                        df = df.copy()
                        df['date'] = df.index.tz_localize('UTC')
                    else:
                        df = df.copy()
                        df['date'] = df.index.tz_convert('UTC')
            # Fix: Ensure 'symbol' is sortable (avoid categorical ordered issues)
            if 'symbol' in df.columns and not pd.api.types.is_string_dtype(df['symbol']):
                df['symbol'] = df['symbol'].astype(str)
            df = df.sort_values(['symbol', 'date'])
            df['dollar_vol'] = df['close'] * df['volume']
            df['avg_dollar_vol_10'] = df.groupby('symbol')['dollar_vol'].transform(lambda x: x.rolling(10).mean())
            df['avg_vol_10'] = df.groupby('symbol')['volume'].transform(lambda x: x.rolling(10).mean())
            
            # Calculate ATR using transform to avoid the apply issue
            df['high_low_diff'] = df['high'] - df['low']
            df['atr_10'] = df.groupby('symbol')['high_low_diff'].transform(lambda x: x.rolling(10).mean()) / df['close']
            df = df.drop('high_low_diff', axis=1)  # Clean up temporary column
            
            latest = df.groupby('symbol').tail(1)
            filtered = latest[(latest['avg_dollar_vol_10'] >= min_avg_dollar_vol) &
                             (latest['avg_vol_10'] >= min_avg_vol) &
                             (latest['atr_10'] <= max_atr)]
            logging.info(f"Liquidity/volatility filter complete. {len(filtered)} assets remain.")

            # Display the number of assets that passed the filter
            logging.info(f"Assets after liquidity/volatility filter: {len(filtered)}")

            if 'symbol' in filtered.columns:
                logging.info(f"Assets after liquidity/volatility filter: {filtered['symbol'].tolist()}")
            else:
                logging.warning(f"No 'symbol' column found after liquidity/volatility filter. Columns: {filtered.columns.tolist()}")

            # Display the number of symbols that pass the liquidity/volatility filter
            logging.info(f"Number of symbols that passed the liquidity/volatility filter: {len(filtered['symbol'].unique())}")
            print(f"Number of symbols that passed the liquidity/volatility filter: {len(filtered['symbol'].unique())}")

            # Pause to review results
            logging.info("Pausing for 5 seconds to review liquidity/volatility filter results...")
            time.sleep(5)

            return filtered.reset_index(drop=True)
        except Exception as e:
            logging.error(f"Error in liquidity_volatility_filter: {e}", exc_info=True)
            return df

    def filter_insufficient_close_data(self, df, min_rows=5):
        """
        Filter out assets that do not have enough close data.
        """
        logging.info(f"Filtering assets with insufficient close data. Minimum rows required: {min_rows}")
        sufficient_data = df.groupby('symbol').filter(lambda x: len(x) >= min_rows)
        logging.info(f"Assets remaining after filtering insufficient close data: {len(sufficient_data['symbol'].unique())}")

        # Pause to review results
        import time
        logging.info("Pausing for 5 seconds to review insufficient close data filter results...")
        time.sleep(5)

        return sufficient_data

    def momentum_filter(self, df, lookback=10, min_momentum=0.02, max_momentum=0.08):
        """
        Filter assets based on momentum over a specified lookback period.
        """
        logging.info(f"Applying momentum filter with lookback period of {lookback} days and momentum range {min_momentum:.1%}-{max_momentum:.1%}.")

        # Filter out symbols with insufficient data first
        sufficient_data = df.groupby('symbol').filter(lambda x: len(x) >= lookback + 1)
        logging.info(f"Assets with sufficient data for momentum calculation: {len(sufficient_data['symbol'].unique())}")

        if sufficient_data.empty:
            logging.warning("No assets have sufficient data for momentum calculation. Returning empty DataFrame.")
            return pd.DataFrame()

        # Handle missing data in the 'close' column
        sufficient_data = sufficient_data.dropna(subset=['close'])

        # Calculate momentum as the percentage change over the lookback period
        sufficient_data['momentum'] = sufficient_data.groupby('symbol')['close'].transform(
            lambda x: x.pct_change(periods=lookback, fill_method=None)
        )

        # Log momentum statistics for inspection
        logging.info("Momentum statistics:")
        logging.info(sufficient_data['momentum'].describe())

        # Filter assets with momentum within the specified range
        filtered = sufficient_data[
            (sufficient_data['momentum'] >= min_momentum) & 
            (sufficient_data['momentum'] <= max_momentum) &
            (sufficient_data['momentum'].notna())
        ]

        logging.info(f"Momentum filter complete. {len(filtered['symbol'].unique())} assets remain.")

        # Pause to review momentum filter results
        logging.info("Pausing for 10 seconds to review momentum filter results...")
        time.sleep(10)

        return filtered

    def price_filter(self, df, *args, **kwargs):
        logging.info("Prefilter deactivated: price_filter returning all assets.")
        return df

    def breakout_filter(self, df, volume_spike_min=2.0, price_breakout_min=0.03):
        """Find stocks breaking out with volume confirmation - KEY for 5% weekly"""
        logging.info("Applying breakout filter - CRITICAL for 5% weekly targets")
        
        # Volume spike (recent volume vs 20-day average)
        df['avg_volume_20'] = df.groupby('symbol')['volume'].transform(lambda x: x.rolling(20).mean())
        df['volume_spike'] = df['volume'] / df['avg_volume_20']
        
        # Price breakout (close vs 20-day high)
        df['high_20'] = df.groupby('symbol')['high'].transform(lambda x: x.rolling(20).max())
        df['price_breakout'] = (df['close'] - df['high_20'].shift(1)) / df['high_20'].shift(1)
        
        # Combine: Volume spike + Price breakout
        filtered = df[
            (df['volume_spike'] >= volume_spike_min) & 
            (df['price_breakout'] >= price_breakout_min)
        ]
        
        logging.info(f"Breakout filter: {len(filtered['symbol'].unique())} breakout candidates")
        
        # Log and print the symbols that pass the filter
        if 'symbol' in filtered.columns:
            logging.info(f"Symbols passing breakout filter: {filtered['symbol'].unique().tolist()}")
            print(f"Symbols passing breakout filter: {filtered['symbol'].unique().tolist()}")
        
        time.sleep(2)
        return filtered

    def price_spread_filter(self, df, *args, **kwargs):
        logging.info("Prefilter deactivated: price_spread_filter returning all assets.")
        return df

    def tradability_filter(self, asset_list, *args, **kwargs):
        logging.info("Prefilter deactivated: tradability_filter returning all assets.")
        return asset_list

    def filter_correlated_symbols(self, df):
        logging.info(f"Filtering correlated symbols from {len(df)} assets.")
        """Remove highly correlated symbols."""
        try:
            # Placeholder: Implement correlation filtering logic
            logging.info(f"Correlation filter complete. {len(df)} assets remain.")
            if 'symbol' in df.columns:
                logging.info(f"Assets after correlation filter: {df['symbol'].tolist()}")
                print(f"Assets after correlation filter: {df['symbol'].tolist()}")
            else:
                logging.warning(f"No 'symbol' column found after correlation filter. Columns: {df.columns.tolist()}")
                print(f"No 'symbol' column found after correlation filter. Columns: {df.columns.tolist()}")
            return df
        except Exception as e:
            logging.error(f"Error in filter_correlated_symbols: {e}", exc_info=True)
            return df

    def rank_and_trim(self, df):
        logging.info(f"Ranking and trimming {len(df)} assets.")
        """Rank and trim the list if survivors > 200."""
        try:
            # Placeholder: Implement ranking and trimming logic
            logging.info(f"Ranking/trimming complete. {len(df)} assets remain.")
            if 'symbol' in df.columns:
                logging.info(f"Assets after ranking/trimming: {df['symbol'].tolist()}")
                print(f"Assets after ranking/trimming: {df['symbol'].tolist()}")
            else:
                logging.warning(f"No 'symbol' column found after ranking/trimming. Columns: {df.columns.tolist()}")
                print(f"No 'symbol' column found after ranking/trimming. Columns: {df.columns.tolist()}")
            return df
        except Exception as e:
            logging.error(f"Error in rank_and_trim: {e}", exc_info=True)
            return df

    def fallback(self, df):
        logging.info(f"Applying fallback logic to {len(df)} assets.")
        """Add default stocks if fewer than 5 symbols remain."""
        try:
            if len(df) < 5:
                default_stocks = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
                df = pd.DataFrame({'symbol': default_stocks})
            logging.info(f"Fallback logic complete. {len(df)} assets remain.")
            if 'symbol' in df.columns:
                logging.info(f"Assets after fallback: {df['symbol'].tolist()}")
                print(f"Assets after fallback: {df['symbol'].tolist()}")
            else:
                logging.warning(f"No 'symbol' column found after fallback. Columns: {df.columns.tolist()}")
                print(f"No 'symbol' column found after fallback. Columns: {df.columns.tolist()}")
            return df
        except Exception as e:
            logging.error(f"Error in fallback: {e}", exc_info=True)
            return df

    def filter_assets(self, df):
        logging.info(f"Starting HIGH-RETURN asset filtering pipeline for {len(df['symbol'].unique()) if 'symbol' in df.columns else len(df)} assets.")
        """Run the HIGH-RETURN filtering pipeline for 5% weekly targets."""
        try:
            if self.simulation_mode and self.historical_data is not None:
                df = self.historical_data

            # Use the HIGH-RETURN pipeline instead of IEX-optimized
            df = self.high_return_filter_pipeline(df)

            logging.info(f"Final filtered assets: {len(df['symbol'].unique()) if 'symbol' in df.columns else len(df)}")
            if 'symbol' in df.columns:
                logging.info(f"Final asset list: {df['symbol'].unique().tolist()}")

            return df
        except Exception as e:
            logging.error(f"Error in filter_assets pipeline: {e}", exc_info=True)
            return df

    def filter_symbols(self, df):
        """
        Wrapper for the filter_assets method to maintain compatibility.
        """
        return self.filter_assets(df)

    def multi_tier_filtering(self, df):
        """
        Implements a multi-tier filtering strategy to select the best assets.
        """
        logging.info("Starting multi-tier filtering strategy.")
        try:
            # Use the IEX-optimized pipeline
            df = self.iex_optimized_filter_pipeline(df)

            logging.info(f"Multi-tier filtering complete. {len(df['symbol'].unique()) if not df.empty and 'symbol' in df.columns else 0} assets remain.")
            return df
        except Exception as e:
            logging.error(f"Error in multi-tier filtering: {e}", exc_info=True)
            return df

    def data_completeness_filter(self, df, min_rows=120):
        """Filter out assets with insufficient data for reliable calculations."""
        logging.info(f"Applying data completeness filter. Minimum rows required: {min_rows}")
        sufficient_data = df.groupby('symbol').filter(lambda x: len(x) >= min_rows)
        logging.info(f"Data completeness filter: {len(sufficient_data['symbol'].unique())} assets with ≥{min_rows} rows")
        time.sleep(2)

        # Log and print the symbols that pass the filter
        if 'symbol' in sufficient_data.columns:
            logging.info(f"Symbols passing data completeness filter: {sufficient_data['symbol'].unique().tolist()}")
            print(f"Symbols passing data completeness filter: {sufficient_data['symbol'].unique().tolist()}")
        else:
            logging.warning("No 'symbol' column found in the data completeness filter result.")

        return sufficient_data

    def liquidity_filter(self, df, min_avg_volume=100_000, min_dollar_volume=1_000_000):
        """Filter based on volume and dollar volume."""
        logging.info(f"Applying liquidity filter. Min volume: {min_avg_volume:,}, Min dollar volume: ${min_dollar_volume:,}")
        df['dollar_volume'] = df['volume'] * df['close']
        df['avg_volume'] = df.groupby('symbol')['volume'].transform(lambda x: x.rolling(20).mean())
        df['avg_dollar_volume'] = df.groupby('symbol')['dollar_volume'].transform(lambda x: x.rolling(20).mean())
        
        filtered = df[
            (df['avg_volume'] >= min_avg_volume) & 
            (df['avg_dollar_volume'] >= min_dollar_volume)
        ]
        logging.info(f"Liquidity filter: {len(filtered['symbol'].unique())} assets remain")

        # Log and print the symbols that pass the filter
        if 'symbol' in filtered.columns:
            logging.info(f"Symbols passing liquidity filter: {filtered['symbol'].unique().tolist()}")
            print(f"Symbols passing liquidity filter: {filtered['symbol'].unique().tolist()}")
        else:
            logging.warning("No 'symbol' column found in the liquidity filter result.")

        time.sleep(2)
        return filtered

    def price_range_filter(self, df, min_price=15, max_price=300):
        """Filter out penny stocks and extremely expensive stocks."""
        logging.info(f"Applying price range filter: ${min_price}-${max_price}")
        filtered = df[(df['close'] >= min_price) & (df['close'] <= max_price)]
        logging.info(f"Price range filter: {len(filtered['symbol'].unique())} assets in ${min_price}-${max_price} range")

        # Log and print the symbols that pass the filter
        if 'symbol' in filtered.columns:
            logging.info(f"Symbols passing price range filter: {filtered['symbol'].unique().tolist()}")
            print(f"Symbols passing price range filter: {filtered['symbol'].unique().tolist()}")
        else:
            logging.warning("No 'symbol' column found in the price range filter result.")

        time.sleep(2)
        return filtered

    def volatility_filter(self, df, min_volatility=0.010, max_volatility=0.08):
        """Filter based on price volatility."""
        logging.info(f"Applying volatility filter: {min_volatility:.1%}-{max_volatility:.1%}")
        df['volatility'] = df.groupby('symbol')['close'].transform(
            lambda x: x.pct_change().rolling(20).std()
        )
        filtered = df[
            (df['volatility'] >= min_volatility) & 
            (df['volatility'] <= max_volatility)
        ]
        logging.info(f"Volatility filter: {len(filtered['symbol'].unique())} assets with volatility {min_volatility:.1%}-{max_volatility:.1%}")

        # Log and print the symbols that pass the filter
        if 'symbol' in filtered.columns:
            logging.info(f"Symbols passing volatility filter: {filtered['symbol'].unique().tolist()}")
            print(f"Symbols passing volatility filter: {filtered['symbol'].unique().tolist()}")
        else:
            logging.warning("No 'symbol' column found in the volatility filter result.")

        time.sleep(2)
        return filtered

    def gap_filter(self, df, max_gap=0.08):
        """Filter out assets with excessive overnight gaps (data quality issue)."""
        logging.info(f"Applying gap filter. Max gap: {max_gap:.1%}")
        df['overnight_gap'] = (df['open'] - df['close'].shift(1)) / df['close'].shift(1)
        filtered = df[df['overnight_gap'].abs() <= max_gap]
        logging.info(f"Gap filter: {len(filtered['symbol'].unique())} assets with gaps ≤{max_gap:.1%}")

        # Log and print the symbols that pass the filter
        if 'symbol' in filtered.columns:
            logging.info(f"Symbols passing gap filter: {filtered['symbol'].unique().tolist()}")
            print(f"Symbols passing gap filter: {filtered['symbol'].unique().tolist()}")
        else:
            logging.warning("No 'symbol' column found in the gap filter result.")

        time.sleep(2)
        return filtered

    def volume_consistency_filter(self, df, max_volume_spike=3.0):
        """Filter out assets with inconsistent volume (potential data issues)."""
        logging.info(f"Applying volume consistency filter. Max spike: {max_volume_spike}x")
        df['avg_volume_20'] = df.groupby('symbol')['volume'].transform(lambda x: x.rolling(20).mean())
        df['volume_ratio'] = df['volume'] / df['avg_volume_20']
        filtered = df[df['volume_ratio'] <= max_volume_spike]
        logging.info(f"Volume consistency filter: {len(filtered['symbol'].unique())} assets with consistent volume")

        # Log and print the symbols that pass the filter
        if 'symbol' in filtered.columns:
            logging.info(f"Symbols passing volume consistency filter: {filtered['symbol'].unique().tolist()}")
            print(f"Symbols passing volume consistency filter: {filtered['symbol'].unique().tolist()}")
        else:
            logging.warning("No 'symbol' column found in the volume consistency filter result.")

        time.sleep(2)
        return filtered

    def iex_optimized_filter_pipeline(self, df):
        """Optimized filtering pipeline for IEX data feed."""
        logging.info(f"Starting IEX-optimized pipeline with {len(df['symbol'].unique())} symbols")
        
        # Step 1: Data completeness (most important for IEX) - Keep strong
        df = self.data_completeness_filter(df, min_rows=120)
        
        # Step 2: Liquidity (ensure tradability) - Relaxed for more opportunities
        df = self.liquidity_filter(df, min_avg_volume=100_000, min_dollar_volume=1_000_000)
        
        # Step 3: Price range (avoid penny stocks) - Keep current
        df = self.price_range_filter(df, min_price=15, max_price=300)
        
        # Step 4: Volume consistency (IEX-specific) - Relaxed
        df = self.volume_consistency_filter(df, max_volume_spike=3.0)
        
        # Step 5: Gap filter removed (had 0% impact)
        
        # Step 6: Volatility (wider range for more opportunities)
        df = self.volatility_filter(df, min_volatility=0.010, max_volatility=0.08)
        
        # Step 7: Momentum (current range works well)
        df = self.momentum_filter(df, lookback=10, min_momentum=0.02, max_momentum=0.08)
        
        logging.info(f"IEX-optimized pipeline complete: {len(df['symbol'].unique())} final assets")
        return df

    def high_return_filter_pipeline(self, df):
        """Optimized for finding 5% weekly movers - REPLACES iex_optimized_filter_pipeline"""
        logging.info(f"Starting HIGH-RETURN pipeline with {len(df['symbol'].unique())} symbols")
        
        # Step 1: Data completeness (reduced requirement)
        df = self.data_completeness_filter(df, min_rows=60)
        
        # Step 2: LOOSER liquidity (more opportunities)
        df = self.liquidity_filter(df, min_avg_volume=50_000, min_dollar_volume=500_000)
        
        # Step 3: Price range - focus on $20-200 (sweet spot for big moves)
        df = self.price_range_filter(df, min_price=20, max_price=200)
        
        # Step 4: HIGH volatility (this is KEY - increased from 0.08 to 0.25)
        df = self.volatility_filter(df, min_volatility=0.03, max_volatility=0.25)
        
        # Step 5: STRONG momentum (recent movers - increased from 0.08 to 0.20)
        df = self.momentum_filter(df, lookback=5, min_momentum=0.05, max_momentum=0.20)
        
        # Step 6: NEW - Breakout detection (MOST IMPORTANT)
        df = self.breakout_filter(df, volume_spike_min=2.0, price_breakout_min=0.03)
        
        # Step 7: Remove volume consistency filter (it removes breakout stocks)
        # df = self.volume_consistency_filter(df, max_volume_spike=3.0)  # COMMENTED OUT
        
        logging.info(f"HIGH-RETURN pipeline complete: {len(df['symbol'].unique())} final candidates")
        return df

    def aggressive_filter_pipeline(self, df):
        """
        Aggressive filtering pipeline for high returns, optimized for IEX data.
        """
        logging.info("Starting aggressive filtering pipeline (IEX-optimized).")
        return self.iex_optimized_filter_pipeline(df)

    def gradual_filter_pipeline(self, df):
        """
        Gradual filtering pipeline to narrow down to a smaller group of predictable, high-movement stocks.
        """
        logging.info("Starting gradual filtering pipeline.")

        # Step 1: Data Completeness Filter
        df = self.data_completeness_filter(df, min_rows=100)

        # Step 2: Liquidity Filter
        df = self.liquidity_filter(df, min_avg_volume=100_000, min_dollar_volume=1_000_000)

        # Step 3: Price Range Filter
        df = self.price_range_filter(df, min_price=10, max_price=500)

        # Step 4: Volatility Filter
        df = self.volatility_filter(df, min_volatility=0.02, max_volatility=0.05)

        # Step 5: Momentum Filter
        df = self.momentum_filter(df, lookback=10, min_momentum=0.01, max_momentum=0.10)

        # Step 6: Volume Consistency Filter
        df = self.volume_consistency_filter(df, max_volume_spike=3)

        # Step 7: Gap Filter
        df = self.gap_filter(df, max_gap=0.05)

        logging.info(f"Gradual filtering pipeline complete. {len(df['symbol'].unique())} assets remain.")
        return df

    def load_and_filter_data(self, df, use_cache=True):
        """
        Load data and ensure it is filtered only once.
        """
        if use_cache:
            logging.info("Using cached data. Ensuring filters are not applied twice.")
            # Check if the data has already been filtered
            if 'filtered' in df.columns and df['filtered'].iloc[0]:
                logging.warning("Data has already been filtered. Skipping redundant filtering.")
                return df

        # Mark the data as filtered
        df['filtered'] = True
        logging.info("Data marked as filtered.")
        return df
def pre_filter_assets(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply pre-filters to the asset DataFrame based on liquidity, price, volatility, and other criteria.
    """
    logging.debug("Starting pre-filtering of assets.")

    # Liquidity / Volume Filter: Average daily volume >= 50,000
    df = df[df["volume"] >= 50000]
    logging.debug(f"Filtered by liquidity: {len(df)} assets remain.")
    logging.info(f"Assets after liquidity filter: {df['symbol'].tolist()}")
    print(f"Assets after liquidity filter: {df['symbol'].tolist()}")

    # Price Filter: Keep stocks between $5 and $1500
    df = df[(df["close"] >= 5) & (df["close"] <= 1500)]
    logging.debug(f"Filtered by price: {len(df)} assets remain.")
    logging.info(f"Assets after price filter: {df['symbol'].tolist()}")
    print(f"Assets after price filter: {df['symbol'].tolist()}")

    # Volatility Filter: ATR(14) > 1% of price
    df["atr"] = df["high"].rolling(window=14).max() - df["low"].rolling(window=14).min()
    df = df[df["atr"] > 0.01 * df["close"]]
    logging.debug(f"Filtered by volatility: {len(df)} assets remain.")
    logging.info(f"Assets after volatility filter: {df['symbol'].tolist()}")
    print(f"Assets after volatility filter: {df['symbol'].tolist()}")

    # Spread / Bid-Ask Proxy: OHLC intrabar spread filter
    df["spread"] = df["high"] - df["low"]
    df = df[(df["spread"] > 0.01 * df["close"]) & (df["spread"] < 0.05 * df["close"])]
    logging.debug(f"Filtered by spread: {len(df)} assets remain.")
    logging.info(f"Assets after spread filter: {df['symbol'].tolist()}")
    print(f"Assets after spread filter: {df['symbol'].tolist()}")

    # Exchange / Asset Class Filter: Restrict to US equities
    df = df[df["exchange"] == "NYSE"]  # Example: Only NYSE stocks
    logging.debug(f"Filtered by exchange: {len(df)} assets remain.")
    logging.info(f"Assets after exchange filter: {df['symbol'].tolist()}")
    print(f"Assets after exchange filter: {df['symbol'].tolist()}")

    # Recent Performance Momentum: 5-day return > +2%
    df["5d_return"] = df["close"].pct_change(periods=5)
    df = df[df["5d_return"] > 0.02]
    logging.debug(f"Filtered by momentum: {len(df)} assets remain.")
    logging.info(f"Assets after momentum filter: {df['symbol'].tolist()}")
    print(f"Assets after momentum filter: {df['symbol'].tolist()}")

    # Event / Gap Filter: Exclude stocks with >10% overnight gaps
    df["overnight_gap"] = (df["open"] - df["close"].shift(1)) / df["close"].shift(1)
    df = df[df["overnight_gap"].abs() <= 0.1]
    logging.debug(f"Filtered by gap: {len(df)} assets remain.")
    logging.info(f"Assets after gap filter: {df['symbol'].tolist()}")
    print(f"Assets after gap filter: {df['symbol'].tolist()}")

    # Universe Size Control: Limit to top 200 by liquidity
    df = df.nlargest(200, "volume")
    logging.debug(f"Capped universe size: {len(df)} assets remain.")
    logging.info(f"Assets after universe size cap: {df['symbol'].tolist()}")
    print(f"Assets after universe size cap: {df['symbol'].tolist()}")

    logging.info(f"Final filtered assets: {len(df)}")
    logging.info(f"Final asset list: {df['symbol'].tolist()}")
    print(f"Final asset list: {df['symbol'].tolist()}")
    return df

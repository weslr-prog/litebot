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
    def __init__(self, simulation_mode=False, historical_data=None, fast_mode=True, diagnostic_mode=False):
        logging.info(f"Initializing PreFilter | simulation_mode={simulation_mode} | fast_mode={fast_mode} | diagnostic_mode={diagnostic_mode}")
        """
        Initialize the PreFilter module.
        :param simulation_mode: If True, use historical data for testing.
        :param historical_data: DataFrame containing historical data for simulation.
        :param fast_mode: If True, run without artificial pauses.
        :param diagnostic_mode: If True, enable extra sleeps/log pauses for inspection.
        """
        self.simulation_mode = simulation_mode
        self.historical_data = historical_data
        self.fast_mode = fast_mode
        self.diagnostic_mode = diagnostic_mode
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
        # NOTE: __init__ is defined at top of class with fast/diagnostic flags

    def _maybe_sleep(self, seconds: float):
        """Sleep only when in diagnostic mode and not explicitly fast."""
        if self.diagnostic_mode and not self.fast_mode:
            time.sleep(seconds)

    def data_completeness_filter(self, df, min_rows=120):
        """Filter out assets with insufficient data for reliable calculations."""
        logging.info(f"Applying data completeness filter. Minimum rows required: {min_rows}")
        sufficient_data = df.groupby('symbol').filter(lambda x: len(x) >= min_rows)
        logging.info(f"Data completeness filter: {len(sufficient_data['symbol'].unique())} assets with ≥{min_rows} rows")
        self._maybe_sleep(2)
        if 'symbol' in sufficient_data.columns:
            logging.info(f"Symbols passing data completeness filter: {sufficient_data['symbol'].unique().tolist()}")
            print(f"Symbols passing data completeness filter: {sufficient_data['symbol'].unique().tolist()}")
        else:
            logging.warning("No 'symbol' column found in the data completeness filter result.")
        return sufficient_data

    def liquidity_filter(self, df, min_avg_volume=100_000, min_dollar_volume=1_000_000):
        """Filter based on volume and dollar volume."""
        logging.info(f"Applying liquidity filter. Min volume: {min_avg_volume:,}, Min dollar volume: ${min_dollar_volume:,}")
        df = df.copy()
        df.loc[:, 'dollar_volume'] = df['volume'] * df['close']
        df.loc[:, 'avg_volume'] = df.groupby('symbol')['volume'].transform(lambda x: x.rolling(20).mean())
        df.loc[:, 'avg_dollar_volume'] = df.groupby('symbol')['dollar_volume'].transform(lambda x: x.rolling(20).mean())
        filtered = df[
            (df['avg_volume'] >= min_avg_volume) & 
            (df['avg_dollar_volume'] >= min_dollar_volume)
        ]
        logging.info(f"Liquidity filter: {len(filtered['symbol'].unique())} assets remain")
        if 'symbol' in filtered.columns:
            logging.info(f"Symbols passing liquidity filter: {filtered['symbol'].unique().tolist()}")
            print(f"Symbols passing liquidity filter: {filtered['symbol'].unique().tolist()}")
        else:
            logging.warning("No 'symbol' column found in the liquidity filter result.")
        self._maybe_sleep(2)
        return filtered

    def price_range_filter(self, df, min_price=15, max_price=300):
        """Gate by latest close and return full history for eligible symbols."""
        logging.info(f"Applying price range filter: ${min_price}-${max_price}")
        if df.empty:
            return df
        latest_prices = df.groupby('symbol')['close'].last()
        eligible = latest_prices[(latest_prices >= min_price) & (latest_prices <= max_price)].index.tolist()
        filtered = df[df['symbol'].isin(eligible)]
        logging.info(f"Price range filter: {len(set(eligible))} assets in ${min_price}-${max_price} range")
        if 'symbol' in filtered.columns:
            logging.info(f"Symbols passing price range filter: {sorted(set(filtered['symbol'].tolist()))}")
        self._maybe_sleep(2)
        return filtered

    def volatility_filter(self, df, min_volatility=0.010, max_volatility=0.08):
        """Filter based on volatility using ATR% for robust short-window behavior."""
        logging.info(f"Applying volatility filter (ATR%): {min_volatility:.1%}-{max_volatility:.1%}")
        logging.info(f"DataFrame shape: {df.shape}")
        logging.info(f"Columns: {df.columns.tolist()}")
        logging.info(f"Unique symbols: {df['symbol'].nunique()}")
        logging.info(f"Sample data per symbol:")
        for symbol in df['symbol'].unique()[:3]:
            symbol_data = df[df['symbol'] == symbol]
            logging.info(f"  {symbol}: {len(symbol_data)} rows, date range: {symbol_data['date'].min()} to {symbol_data['date'].max()}")
        df = df.copy()
        # Diagnostic return std
        df.loc[:, 'pct_change'] = df.groupby('symbol')['close'].transform(lambda x: x.pct_change())
        valid_pct = df['pct_change'].notna().sum()
        logging.info(f"Valid pct_change values: {valid_pct} out of {len(df)}")
        df.loc[:, 'ret_std_10'] = df.groupby('symbol')['pct_change'].transform(lambda x: x.rolling(10, min_periods=5).std())
        # ATR(14) computation
        high_low = (df['high'] - df['low']).abs()
        high_close = (df['high'] - df['close'].shift(1)).abs()
        low_close = (df['low'] - df['close'].shift(1)).abs()
        df.loc[:, 'true_range'] = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df.loc[:, 'atr_14'] = df.groupby('symbol')['true_range'].transform(lambda x: x.rolling(14, min_periods=7).mean())
        df.loc[:, 'atr_pct'] = df['atr_14'] / df['close']
        # Select by latest per symbol, then return full history for eligible symbols
        latest_data = df.groupby('symbol').last().reset_index()
        logging.info("Volatility (ATR%) statistics:")
        logging.info(latest_data['atr_pct'].describe())
        logging.info("Latest volatility (ATR%) per symbol (first 10):")
        logging.info(latest_data.set_index('symbol')['atr_pct'].head(10))
        eligible_symbols = latest_data[
            (latest_data['atr_pct'].notna()) &
            (latest_data['atr_pct'] >= min_volatility) &
            (latest_data['atr_pct'] <= max_volatility)
        ]['symbol'].tolist()
        filtered = df[df['symbol'].isin(eligible_symbols)].copy()
        # Expose unified 'volatility' as atr_pct for ranking
        filtered.loc[:, 'volatility'] = filtered['atr_pct']
        logging.info(f"Volatility filter: {len(filtered['symbol'].unique())} assets with ATR% {min_volatility:.1%}-{max_volatility:.1%}")
        if 'symbol' in filtered.columns:
            logging.info(f"Symbols passing volatility filter: {filtered['symbol'].unique().tolist()}")
            print(f"Symbols passing volatility filter: {filtered['symbol'].unique().tolist()}")
        else:
            logging.warning("No 'symbol' column found in the volatility filter result.")
        self._maybe_sleep(2)
        return filtered

    def gap_filter(self, df, max_gap=0.08):
        """Filter out assets with excessive overnight gaps (data quality issue)."""
        logging.info(f"Applying gap filter. Max gap: {max_gap:.1%}")
        df = df.copy()
        # Use group-wise previous close for proper gap calc
        prev_close = df.groupby('symbol')['close'].shift(1)
        df.loc[:, 'overnight_gap'] = (df['open'] - prev_close) / prev_close
        filtered = df[df['overnight_gap'].abs() <= max_gap]
        logging.info(f"Gap filter: {len(filtered['symbol'].unique())} assets with gaps ≤{max_gap:.1%}")
        if 'symbol' in filtered.columns:
            logging.info(f"Symbols passing gap filter: {filtered['symbol'].unique().tolist()}")
            print(f"Symbols passing gap filter: {filtered['symbol'].unique().tolist()}")
        else:
            logging.warning("No 'symbol' column found in the gap filter result.")
        self._maybe_sleep(2)
        return filtered
    def filter_assets(self, df):
        logging.info(f"Starting HIGH-RETURN asset filtering pipeline for {len(df['symbol'].unique()) if 'symbol' in df.columns else len(df)} assets.")
        """Run adaptive high-return selection aiming for 10–15 strong candidates."""
        try:
            if hasattr(self, 'simulation_mode') and self.simulation_mode and hasattr(self, 'historical_data') and self.historical_data is not None:
                df = self.historical_data

            return self.adaptive_high_return_candidates(df, target_min=10, target_max=15)
        except Exception as e:
            logging.error(f"Error in filter_assets pipeline: {e}", exc_info=True)
            return df

    def _rank_candidates(self, df: pd.DataFrame) -> pd.DataFrame:
        """Rank candidates by a composite score favoring breakout, momentum, healthy volatility, and liquidity.
        Expects columns: symbol, close, volume, avg_volume_20, price_breakout, momentum, volatility.
        """
        if df.empty:
            return df
        work = df.copy()
        # Ensure latest snapshot per symbol for ranking
        latest = work.groupby('symbol').tail(1).copy()

        # Safety: fill missing feature columns
        for col in [
            'price_breakout','volume_spike','momentum','volatility','avg_volume_20','avg_dollar_volume','dollar_volume'
        ]:
            if col not in latest.columns:
                latest[col] = np.nan

        # Normalize features robustly
        def zscore(s: pd.Series) -> pd.Series:
            return (s - s.mean()) / (s.std(ddof=0) + 1e-9)

        # Build score: breakout weight highest, then momentum, then volatility in a sweet spot, liquidity as tie-breaker
        breakout_score = zscore(latest['price_breakout'].fillna(0.0))
        momentum_score = zscore(latest['momentum'].fillna(0.0))
        # Prefer mid-high volatility (around 10-20%) — penalize outside [3%, 35%]
        vol = latest['volatility'].clip(lower=0.0001)
        vol_pref_center = 0.15
        vol_pref_width = 0.12
        vol_pref = -((vol - vol_pref_center) ** 2) / (2 * (vol_pref_width ** 2))
        liquidity_score = zscore((latest['avg_dollar_volume'].fillna(0) + latest['dollar_volume'].fillna(0)).clip(lower=0))

        latest['score'] = 2.0 * breakout_score + 1.5 * momentum_score + 1.0 * vol_pref + 0.5 * liquidity_score
        ranked = latest.sort_values('score', ascending=False)
        return ranked

    def adaptive_high_return_candidates(self, df: pd.DataFrame, target_min: int = 10, target_max: int = 15) -> pd.DataFrame:
        """Run the high-return pipeline and adaptively relax certain thresholds to reach ~10–15 quality names.
        Relax order: breakout > momentum > volatility > liquidity. Never drop data completeness below 30 rows.
        """
        if df is None or df.empty:
            logging.warning("Adaptive candidates: empty input DataFrame")
            return df

        # Base thresholds
        completeness_rows = 30
        min_avg_volume = 50_000
        min_dollar_volume = 500_000
        min_price, max_price = 20, 200
        min_vol, max_vol = 0.03, 0.25
        lookback, min_mom, max_mom = 5, 0.05, 0.20
        vol_spike_min, breakout_min = 2.0, 0.03

        def run_once(dfin: pd.DataFrame,
                     breakout_window: int = 20,
                     vol_avg_window: int = 20,
                     minp_frac: float = 0.5) -> pd.DataFrame:
            d0 = self.data_completeness_filter(dfin, min_rows=completeness_rows)
            if d0.empty: return d0
            d1 = self.liquidity_filter(d0, min_avg_volume=min_avg_volume, min_dollar_volume=min_dollar_volume)
            if d1.empty: return d1
            d2 = self.price_range_filter(d1, min_price=min_price, max_price=max_price)
            if d2.empty: return d2
            d3 = self.volatility_filter(d2, min_volatility=min_vol, max_volatility=max_vol)
            if d3.empty: return d3
            d4 = self.momentum_filter(d3, lookback=lookback, min_momentum=min_mom, max_momentum=max_mom)
            if d4.empty: return d4
            d5 = self.breakout_filter(
                d4,
                volume_spike_min=vol_spike_min,
                price_breakout_min=breakout_min,
                prior_high_window=breakout_window,
                avg_volume_window=vol_avg_window,
                min_periods_frac=minp_frac,
            )
            return d5

        dfc = run_once(df)
        survivors = dfc['symbol'].nunique() if 'symbol' in dfc.columns and not dfc.empty else 0
        logging.info(f"Adaptive pass0 survivors: {survivors}")
        best_breakout_df = dfc.copy() if survivors > 0 else pd.DataFrame()
        best_survivors = survivors

        # If enough, rank and trim
        if survivors >= target_min:
            ranked = self._rank_candidates(dfc)
            top = ranked.head(target_max)
            top_symbols = top['symbol'].tolist()
            score_map = dict(zip(top['symbol'], top['score']))
            out = df[df['symbol'].isin(top_symbols)].copy()
            out['pf_score'] = out['symbol'].map(score_map)
            return out

        # Progressive relaxation steps
        steps = [
            {"breakout_min": 0.02},
            {"breakout_min": 0.008, "vol_spike_min": 1.1},  # Further relaxed: was 0.012 & 1.3
            {"min_mom": 0.04},
            {"min_mom": 0.03, "lookback": 4},
            {"min_vol": 0.025},
            {"min_vol": 0.020, "max_vol": 0.35},
            {"min_avg_volume": 30_000, "min_dollar_volume": 300_000},
            {"min_price": 15, "max_price": 300},
            {"min_vol": 0.015},
            {"min_mom": 0.02},
            {"min_avg_volume": 20_000, "min_dollar_volume": 200_000},
        ]

        cur = {
            'min_avg_volume': min_avg_volume,
            'min_dollar_volume': min_dollar_volume,
            'min_price': min_price,
            'max_price': max_price,
            'min_vol': min_vol,
            'max_vol': max_vol,
            'lookback': lookback,
            'min_mom': min_mom,
            'max_mom': max_mom,
            'vol_spike_min': vol_spike_min,
            'breakout_min': breakout_min,
            'breakout_window': 20,
            'vol_avg_window': 20,
            'minp_frac': 0.5,
        }

        for i, adj in enumerate(steps, 1):
            cur.update(adj)
            logging.info(f"Adaptive step{i} thresholds: {cur}")
            completeness_rows = 30  # never relax below 30
            min_avg_volume = cur['min_avg_volume']
            min_dollar_volume = cur['min_dollar_volume']
            min_price, max_price = cur['min_price'], cur['max_price']
            min_vol, max_vol = cur['min_vol'], cur['max_vol']
            lookback, min_mom, max_mom = cur['lookback'], cur['min_mom'], cur['max_mom']
            vol_spike_min, breakout_min = cur['vol_spike_min'], cur['breakout_min']
            dfc = run_once(
                df,
                breakout_window=cur['breakout_window'],
                vol_avg_window=cur['vol_avg_window'],
                minp_frac=cur['minp_frac']
            )
            survivors = dfc['symbol'].nunique() if 'symbol' in dfc.columns and not dfc.empty else 0
            logging.info(f"Adaptive pass{i} survivors: {survivors}")
            if survivors > best_survivors:
                best_survivors = survivors
                best_breakout_df = dfc.copy()
            if survivors >= target_min:
                ranked = self._rank_candidates(dfc)
                top = ranked.head(target_max)
                top_symbols = top['symbol'].tolist()
                score_map = dict(zip(top['symbol'], top['score']))
                out = df[df['symbol'].isin(top_symbols)].copy()
                out['pf_score'] = out['symbol'].map(score_map)
                return out

        # Final breakout relaxation: easier thresholds and shorter window to capture fresh breakouts (tuned for weekly ROI)
        logging.info("Adaptive final relaxation for breakout gating")
        cur.update({'vol_spike_min': 1.1, 'breakout_min': 0.006, 'breakout_window': 15, 'vol_avg_window': 15, 'minp_frac': 0.5})  # Further relaxed
        dfc = run_once(
            df,
            breakout_window=cur['breakout_window'],
            vol_avg_window=cur['vol_avg_window'],
            minp_frac=cur['minp_frac']
        )
        survivors = dfc['symbol'].nunique() if 'symbol' in dfc.columns and not dfc.empty else 0
        logging.info(f"Adaptive final-relax survivors: {survivors}")
        if survivors > best_survivors:
            best_survivors = survivors
            best_breakout_df = dfc.copy()

        # If still short, fallback to best momentum names; supplement to reach target_min while retaining breakout passers
        logging.info("Adaptive fallback: using momentum-ranked candidates without breakout gate")
        base = self.data_completeness_filter(df, min_rows=30)
        base = self.liquidity_filter(base, min_avg_volume=30_000, min_dollar_volume=300_000)
        base = self.price_range_filter(base, min_price=15, max_price=350)
        base = self.volatility_filter(base, min_volatility=0.015, max_volatility=0.35)
        base = self.momentum_filter(base, lookback=4, min_momentum=0.02, max_momentum=0.30)
        ranked = self._rank_candidates(base)

        # Preserve breakout passers if any
        breakout_symbols: list[str] = []
        if not best_breakout_df.empty and 'symbol' in best_breakout_df.columns:
            br_ranked = self._rank_candidates(best_breakout_df)
            breakout_symbols = br_ranked['symbol'].tolist()

        # Supplement from momentum-ranked list to reach target_min
        fallback_symbols = [s for s in ranked['symbol'].tolist() if s not in breakout_symbols]
        combined: list[str] = []
        combined.extend(breakout_symbols)
        if len(combined) < target_min:
            needed = target_min - len(combined)
            combined.extend(fallback_symbols[:needed])
        # Cap at target_max by adding more fallback if available
        if len(combined) < target_max:
            extra_needed = target_max - len(combined)
            combined.extend(fallback_symbols[:extra_needed])
        combined = list(dict.fromkeys(combined))  # de-dup, preserve order
        out = df[df['symbol'].isin(combined)].copy()
        # Map pf_score from the ranked sets
        score_map = {}
        score_map.update(dict(zip(ranked['symbol'], ranked['score'])))
        if breakout_symbols:
            br_scores_df = self._rank_candidates(best_breakout_df)
            score_map.update(dict(zip(br_scores_df['symbol'], br_scores_df['score'])))
        out['pf_score'] = out['symbol'].map(score_map)
        return out

    def filter_symbols(self, df):
        """
        Wrapper for the filter_assets method to maintain compatibility.
        """
        return self.filter_assets(df)
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
        logging.info("Insufficient lookback data filter complete; diagnostic pause if enabled")
        self._maybe_sleep(5)
        return sufficient_data

    def liquidity_volatility_filter(self, df, min_avg_vol=100, max_atr=5.0, min_survivors=None):
        logging.info(f"Applying liquidity/volatility filter to {len(df)} assets.")
        print(f"🔍 LIQUIDITY FILTER DEBUG - Input DataFrame shape: {df.shape}")
        print(f"🔍 LIQUIDITY FILTER DEBUG - Input unique symbols: {len(df['symbol'].unique())}")
        try:
            # Filter out assets without enough lookback data
            df = self.filter_insufficient_lookback_data(df, lookback=10)
            print(f"🔍 LIQUIDITY FILTER DEBUG - After insufficient data filter - DataFrame shape: {df.shape}")
            print(f"🔍 LIQUIDITY FILTER DEBUG - After insufficient data filter - unique symbols: {len(df['symbol'].unique())}")

            min_avg_dollar_vol = 25000  # Loosened threshold
            # Fix: Ensure all 'date' values are tz-aware UTC
            if 'date' in df.columns:
                if not pd.api.types.is_datetime64_any_dtype(df['date']):
                    df = df.copy()
                    df.loc[:, 'date'] = pd.to_datetime(df['date'], errors='coerce')
                if df['date'].dt.tz is None:
                    df = df.copy()
                    df.loc[:, 'date'] = df['date'].dt.tz_localize('UTC')
                else:
                    df = df.copy()
                    df.loc[:, 'date'] = df['date'].dt.tz_convert('UTC')
            else:
                # Create a date column from index if possible
                if isinstance(df.index, pd.DatetimeIndex):
                    if df.index.tz is None:
                        df = df.copy()
                        df.loc[:, 'date'] = df.index.tz_localize('UTC')
                    else:
                        df = df.copy()
                        df.loc[:, 'date'] = df.index.tz_convert('UTC')
            # Fix: Ensure 'symbol' is sortable (avoid categorical ordered issues)
            if 'symbol' in df.columns and not pd.api.types.is_string_dtype(df['symbol']):
                df = df.copy()
                df.loc[:, 'symbol'] = df['symbol'].astype(str)
            df = df.sort_values(['symbol', 'date']).copy()
            df.loc[:, 'dollar_vol'] = df['close'] * df['volume']
            df.loc[:, 'avg_dollar_vol_10'] = df.groupby('symbol')['dollar_vol'].transform(lambda x: x.rolling(10).mean())
            df.loc[:, 'avg_vol_10'] = df.groupby('symbol')['volume'].transform(lambda x: x.rolling(10).mean())
            
            # Calculate ATR using transform to avoid the apply issue
            df.loc[:, 'high_low_diff'] = df['high'] - df['low']
            df.loc[:, 'atr_10'] = df.groupby('symbol')['high_low_diff'].transform(lambda x: x.rolling(10).mean()) / df['close']
            df = df.drop('high_low_diff', axis=1)  # Clean up temporary column
            
            # Check latest values for filtering criteria
            latest = df.groupby('symbol').tail(1)
            eligible_symbols = latest[
                (latest['avg_dollar_vol_10'] >= min_avg_dollar_vol) &
                (latest['avg_vol_10'] >= min_avg_vol) &
                (latest['atr_10'] <= max_atr)
            ]['symbol'].tolist()
            
            # Return ALL historical data for symbols that meet current criteria
            filtered = df[df['symbol'].isin(eligible_symbols)]
            print(f"🔍 LIQUIDITY FILTER DEBUG - Final filtered DataFrame shape: {filtered.shape}")
            print(f"🔍 LIQUIDITY FILTER DEBUG - Final filtered unique symbols: {len(filtered['symbol'].unique())}")
            
            logging.info(f"Liquidity/volatility filter complete. {len(filtered['symbol'].unique())} assets remain.")

            # Display the number of assets that passed the filter
            logging.info(f"Assets after liquidity/volatility filter: {len(filtered['symbol'].unique())}")

            if 'symbol' in filtered.columns:
                logging.info(f"Assets after liquidity/volatility filter: {filtered['symbol'].unique().tolist()}")
            else:
                logging.warning(f"No 'symbol' column found after liquidity/volatility filter. Columns: {filtered.columns.tolist()}")

            # Display the number of symbols that pass the liquidity/volatility filter
            logging.info(f"Number of symbols that passed the liquidity/volatility filter: {len(filtered['symbol'].unique())}")
            print(f"Number of symbols that passed the liquidity/volatility filter: {len(filtered['symbol'].unique())}")

            # Pause to review results
            logging.info("Pausing for 5 seconds to review liquidity/volatility filter results...")
            self._maybe_sleep(5)

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
        logging.info("Insufficient close data filter complete; diagnostic pause if enabled")
        self._maybe_sleep(5)
        return sufficient_data

    def momentum_filter(self, df, lookback=10, min_momentum=0.02, max_momentum=0.08):
        """
        Filter assets based on momentum over a specified lookback period.
        """
        logging.info(f"Applying momentum filter with lookback period of {lookback} days and momentum range {min_momentum:.1%}-{max_momentum:.1%}.")
        if df.empty:
            logging.warning("Momentum filter: Input DataFrame is empty. Returning as-is.")
            return df
        if 'symbol' not in df.columns or 'close' not in df.columns:
            logging.warning(f"Momentum filter: Required columns missing. Columns: {df.columns.tolist()}. Returning as-is.")
            return df
        # Filter out symbols with insufficient data first
        sufficient_data = df.groupby('symbol').filter(lambda x: len(x) >= lookback + 1)
        logging.info(f"Assets with sufficient data for momentum calculation: {len(sufficient_data['symbol'].unique())}")
        if sufficient_data.empty:
            logging.warning("No assets have sufficient data for momentum calculation. Returning empty DataFrame.")
            return pd.DataFrame()
        # Handle missing data in the 'close' column
        sufficient_data = sufficient_data.dropna(subset=['close'])
        # Calculate momentum as the percentage change over the lookback period
        sufficient_data = sufficient_data.copy()
        sufficient_data.loc[:, 'momentum'] = sufficient_data.groupby('symbol')['close'].transform(
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
        logging.info("Momentum filter complete; diagnostic pause if enabled")
        self._maybe_sleep(10)
        return filtered

    def price_filter(self, df, *args, **kwargs):
        logging.info("Prefilter deactivated: price_filter returning all assets.")
        return df

    def breakout_filter(self, df, volume_spike_min=2.0, price_breakout_min=0.03,
                        prior_high_window: int = 20, avg_volume_window: int = 20, min_periods_frac: float = 0.5):
        """Find stocks breaking out with volume confirmation and gate by latest snapshot.
        Adds robustness for short lookbacks (min_periods) and uses group-wise shift for prior highs.
        """
        logging.info("Applying breakout filter - CRITICAL for 5% weekly targets")
        if df.empty:
            logging.warning("Breakout filter: Input DataFrame is empty. Returning as-is.")
            return df
        required = {'symbol','date','close','high','volume'}
        if not required.issubset(df.columns):
            logging.warning(f"Breakout filter: Required columns missing. Columns: {df.columns.tolist()}. Returning as-is.")
            return df

        work = df.copy().sort_values(['symbol','date'])
        # Volume spike vs configurable moving average
        minp = max(5, int(avg_volume_window * min_periods_frac))
        work.loc[:, 'avg_volume_20'] = work.groupby('symbol')['volume'].transform(lambda x: x.rolling(avg_volume_window, min_periods=minp).mean())
        work.loc[:, 'volume_spike'] = work['volume'] / work['avg_volume_20']
        # Prior high window (exclude current bar)
        minp_high = max(5, int(prior_high_window * min_periods_frac))
        work.loc[:, 'prior_high_20'] = work.groupby('symbol')['high'].transform(lambda x: x.rolling(prior_high_window, min_periods=minp_high).max().shift(1))
        work.loc[:, 'price_breakout'] = (work['close'] - work['prior_high_20']) / work['prior_high_20']

        # Evaluate only latest row per symbol
        snap = work.groupby('symbol').tail(1)
        eligible = snap[(snap['prior_high_20'].notna()) &
                        (snap['volume_spike'] >= volume_spike_min) &
                        (snap['price_breakout'] >= price_breakout_min)]['symbol'].tolist()
        logging.info(f"Breakout filter: {len(eligible)} symbols pass (vol_spike>={volume_spike_min}, breakout>={price_breakout_min:.1%})")
        if eligible:
            logging.info(f"Symbols passing breakout: {eligible}")
            print(f"Symbols passing breakout filter: {eligible}")
        self._maybe_sleep(2)
        return work[work['symbol'].isin(eligible)]

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
        logging.info(f"Applying liquidity/volatility filter to {len(df)} assets.")
        if df.empty:
            logging.warning("Liquidity/volatility filter: Input DataFrame is empty. Returning as-is.")
            return df
        if 'symbol' not in df.columns or 'close' not in df.columns or 'volume' not in df.columns or 'high' not in df.columns or 'low' not in df.columns:
            logging.warning(f"Liquidity/volatility filter: Required columns missing. Columns: {df.columns.tolist()}. Returning as-is.")
            return df
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
            # Check latest values for filtering criteria
            latest = df.groupby('symbol').tail(1)
            eligible_symbols = latest[
                (latest['avg_dollar_vol_10'] >= min_avg_dollar_vol) &
                (latest['avg_vol_10'] >= min_avg_vol) &
                (latest['atr_10'] <= max_atr)
            ]['symbol'].tolist()
            # Return ALL historical data for symbols that meet current criteria
            filtered = df[df['symbol'].isin(eligible_symbols)]
            logging.info(f"Liquidity/volatility filter complete. {len(filtered['symbol'].unique())} assets remain.")
            if 'symbol' in filtered.columns:
                logging.info(f"Assets after liquidity/volatility filter: {filtered['symbol'].unique().tolist()}")
            else:
                logging.warning(f"No 'symbol' column found after liquidity/volatility filter. Columns: {filtered.columns.tolist()}")
            logging.info(f"Number of symbols that passed the liquidity/volatility filter: {len(filtered['symbol'].unique())}")
            return filtered.reset_index(drop=True)
        except Exception as e:
            logging.error(f"Error in liquidity_volatility_filter: {e}", exc_info=True)
            return df
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
        self._maybe_sleep(2)
        return filtered

    # Duplicate price_range_filter removed; using unified version defined earlier

    # Duplicate volatility_filter removed; using unified version defined earlier

    # Duplicate gap_filter removed; using unified version defined earlier

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
        self._maybe_sleep(2)
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
        df = self.data_completeness_filter(df, min_rows=30)
        
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
        df = self.price_range_filter(df, min_price=10, max_price=750)

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

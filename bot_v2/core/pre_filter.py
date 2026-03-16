"""
Pre-Filter Module
Purpose: Filter the list of tradable assets before strategies are run.
Examples: Volume/liquidity filters, price filters, volatility filters.
OPTIMIZED: Oct 17, 2025 - Added gap-prone detection for D+1 strategy
"""

import datetime as dt
import logging
import time  # Ensure the time module is imported for sleep functionality
import json
import os
import numpy as np
from typing import Any, Dict, Iterable, List, Optional, Tuple

import pandas as pd

try:
    from bot_v2.data.data_loader import DataLoader  # Standalone bot_v2 data loader
except Exception:  # DataLoader may be unavailable in certain testing contexts
    DataLoader = None

try:
    from gap_prone_detector import GapProneDetector
except Exception:
    GapProneDetector = None
    logging.warning("GapProneDetector not available - gap analysis disabled")

try:
    from rs_sector_enhancement import RelativeStrengthAnalyzer, SectorRotationAnalyzer
except Exception:
    RelativeStrengthAnalyzer = None
    SectorRotationAnalyzer = None
    logging.warning("RS/Sector analyzers not available - enhancements disabled")

# Ensure logging is configured
# DISABLED: Dec 29, 2025 - Causes duplicate logging when imported by launcher
# Root logger should be configured by main launcher, not by imported modules
# logging.basicConfig(level=logging.DEBUG)

class PreFilter:
    def __init__(
        self,
        data_loader_or_simulation: Optional["DataLoader"] = None,
        config: Optional[Dict] = None,
        simulation_mode: bool = False,
        historical_data: Optional[pd.DataFrame] = None,
        fast_mode: bool = True,
        diagnostic_mode: bool = False,
        regime_adjustment: bool = False,
        enable_intraday_analysis: bool = False,  # NEW: Intraday analysis control
        max_intraday_analyses_per_day: int = 50,  # NEW: API call limit
        enable_gap_detection: bool = False,  # NEW: Gap-prone stock detection
    ) -> None:
        """Initialize the PreFilter module."""
        # Handle dual-signature: PreFilter(data_loader, config) or PreFilter(simulation_mode=...)
        if isinstance(data_loader_or_simulation, dict):
            # Old signature: first param is config, no data_loader
            config = data_loader_or_simulation
            data_loader = None
        elif hasattr(data_loader_or_simulation, 'get_historical_data'):
            # New signature: first param is data_loader
            data_loader = data_loader_or_simulation
        else:
            # Simulation mode or None
            data_loader = data_loader_or_simulation
            if isinstance(data_loader, bool):
                simulation_mode = data_loader
                data_loader = None
        
        self.config = config or {}
        self.simulation_mode = simulation_mode
        self.historical_data = historical_data
        self.fast_mode = fast_mode
        self.diagnostic_mode = diagnostic_mode
        self.data_loader = data_loader
        self.enable_gap_detection = enable_gap_detection
        self.regime_adjustment = regime_adjustment
        self.enable_intraday_analysis = enable_intraday_analysis
        
        logging.info(
            "Initializing PreFilter | simulation_mode=%s | fast_mode=%s | diagnostic_mode=%s | regime_adjustment=%s | intraday=%s | gap_detection=%s",
            simulation_mode,
            fast_mode,
            diagnostic_mode,
            regime_adjustment,
            enable_intraday_analysis,
            enable_gap_detection,
        )
        
        # Initialize regime-based adjustment system if enabled
        self.regime_filter = None
        if self.regime_adjustment:
            try:
                from regime_filter_adjustment import RegimeBasedFilterAdjustment
                self.regime_filter = RegimeBasedFilterAdjustment(data_loader=self.data_loader)
                logging.info("🎯 Regime-based filter adjustment enabled")
            except ImportError:
                logging.warning("Regime filter adjustment not available, using default thresholds")
                self.regime_adjustment = False
        
        # Initialize gap-prone detector if enabled (NEW - Oct 17, 2025)
        self.gap_detector = None
        if self.enable_gap_detection and not self.simulation_mode:
            if GapProneDetector is not None:
                try:
                    self.gap_detector = GapProneDetector(
                        min_gap_frequency=0.30,  # 30% of days with 1%+ gaps
                        min_avg_gap_size=0.015,   # 1.5% average gap
                        min_directional_bias=0.2, # 20% directional consistency
                        lookback_days=60
                    )
                    logging.info("🌅 Gap-prone detection enabled for D+1 strategy")
                except Exception as exc:
                    logging.warning(f"⚠️ Could not initialize gap detection: {exc}")
                    self.gap_detector = None
                    self.enable_gap_detection = False
            else:
                logging.warning("GapProneDetector not available")
                self.enable_gap_detection = False
        
        # Initialize intraday analysis enhancer if enabled
        self.intraday_enhancer = None
        if self.enable_intraday_analysis and not self.simulation_mode:
            try:
                from intraday_prefilter_integration import IntradayPreFilterEnhancer
                self.intraday_enhancer = IntradayPreFilterEnhancer(
                    enabled=True,
                    max_analyses_per_day=max_intraday_analyses_per_day
                )
                logging.info(f"📊 Intraday analysis enabled (max {max_intraday_analyses_per_day} analyses/day)")
            except Exception as exc:
                logging.warning(f"⚠️ Could not initialize intraday analysis: {exc}")
                self.intraday_enhancer = None
                self.enable_intraday_analysis = False
        
        if self.data_loader is None and not self.simulation_mode:
            if DataLoader is not None:
                try:
                    self.data_loader = DataLoader()
                    logging.info("PreFilter data loader instantiated")
                except Exception as exc:
                    logging.warning("PreFilter could not initialize DataLoader: %s", exc)
                    self.data_loader = None
            else:
                logging.debug("DataLoader import unavailable; PreFilter will operate on provided data only")

        # In-memory caches (symbol, days, granularity) -> cached frame and fetch timestamp
        self._history_cache: Dict[Tuple[str, int, str], Dict[str, object]] = {}
        self._filtered_cache: Dict[Tuple[Tuple[str, ...], int, str, bool], Dict[str, object]] = {}
        self._last_history_frame: Optional[pd.DataFrame] = None
        self.last_run_stats: Dict[str, Any] = {
            "input_count": 0,
            "data_loaded_count": 0,
            "passed_count": 0,
            "pass_rate_pct": 0.0,
            "rejection_reasons": {},
            "stage_counts": {},
        }
        # Mirror the active config so helper fallbacks cannot silently drift.
        self.MIN_AVG_DOLLAR_VOL = self.config.get('min_dollar_volume', 30_000_000)
        self.MIN_AVG_VOL = self.config.get('min_volume', 3_000_000)
        self.MAX_AVG_VOL = self.config.get('max_volume', 30_000_000)
        self.MIN_PRICE = self.config.get('min_price', 5.0)
        self.MAX_PRICE = self.config.get('max_price', 50.0)
        self.MIN_ATR = self.config.get('min_atr_pct', 0.035)
        self.MAX_ATR = self.config.get('max_atr_pct', 0.060)
        self.MIN_MOMENTUM_RETURN = 0.02  # 2% minimum momentum
        self.MIN_VOLUME_SURGE = 0.5  # Allow below-average volume days
        self.MIN_SURVIVORS = 6  # Accept 6+ stocks on slow days
        self.BATCH_SIZE = 120  # For Alpaca free tier reliability
        self.CACHE_DAILY = 3  # days
        self.CACHE_INTRADAY = 0.02  # ~30 minutes
        self.EARNINGS_EXCLUSION_DAYS = 5  # Exclude stocks within 5 days of earnings
        # NOTE: __init__ is defined at top of class with fast/diagnostic flags

    def run_filter(self, symbols: List[str]) -> List[str]:
        """
        Run 3-stage PreFilter with detailed logging.
        
        Args:
            symbols: List of stock symbols to filter
            
        Returns:
            List of symbols that pass all filters
        """
        logging.info(f"\n{'='*80}")
        logging.info(f"🔍 PREFILTER: Starting 3-Stage Filter")
        logging.info(f"   Input Universe: {len(symbols)} stocks")
        logging.info(f"{'='*80}")
        
        stage_counts: Dict[str, int] = {
            "price_range_reject": 0,
            "volume_liquidity_reject": 0,
            "volatility_reject": 0,
            "data_unavailable": 0,
        }

        # Fetch data for all symbols
        df = self.fetch_history(symbols, days=30, use_cache=True, intraday=False)
        
        if df.empty:
            logging.warning("❌ No data fetched for any symbols")
            stage_counts["data_unavailable"] = len(symbols)
            self.last_run_stats = {
                "input_count": len(symbols),
                "data_loaded_count": 0,
                "passed_count": 0,
                "pass_rate_pct": 0.0,
                "rejection_reasons": {k: v for k, v in stage_counts.items() if v > 0},
                "stage_counts": stage_counts,
            }
            return []
        
        logging.info(f"✅ Data fetched: {df['symbol'].nunique()} stocks with valid data")
        data_loaded_count = df['symbol'].nunique()
        stage_counts["data_unavailable"] = max(0, len(symbols) - data_loaded_count)
        
        # Stage 1: Price Range Filter
        logging.info(f"\n📌 STAGE 1: Price Range Filter (${self.config.get('min_price', 5)}-${self.config.get('max_price', 50)})")
        stage1_count = df['symbol'].nunique()
        df = self.price_range_filter(
            df,
            min_price=self.config.get('min_price', 5.0),
            max_price=self.config.get('max_price', 50.0)
        )
        stage1_passed = df['symbol'].nunique()
        stage1_rejected = stage1_count - stage1_passed
        stage_counts["price_range_reject"] = stage1_rejected
        logging.info(f"   ✅ Passed: {stage1_passed} / {stage1_count} stocks")
        if stage1_rejected > 0:
            logging.info(f"   ❌ Rejected: {stage1_rejected} stocks (price out of range)")
        
        if df.empty:
            logging.warning("❌ No stocks passed Stage 1")
            return []
        
        # Stage 2: Volume/Liquidity Filter (30-day average excluding today)
        min_vol = self.config.get('min_volume', 2_000_000)
        max_vol = self.config.get('max_volume', 20_000_000)
        volume_range = f"{min_vol:,}-{max_vol:,}" if max_vol else f"{min_vol:,}+"
        logging.info(f"\n📌 STAGE 2: Volume Filter ({volume_range} shares, ${self.config.get('min_dollar_volume', 25_000_000):,} dollar volume, 30d avg excl. today)")
        stage2_count = df['symbol'].nunique()
        df = self.liquidity_filter(
            df,
            min_avg_volume=min_vol,
            min_dollar_volume=self.config.get('min_dollar_volume', 25_000_000),
            max_avg_volume=max_vol
        )
        stage2_passed = df['symbol'].nunique()
        stage2_rejected = stage2_count - stage2_passed
        stage_counts["volume_liquidity_reject"] = stage2_rejected
        logging.info(f"   ✅ Passed: {stage2_passed} / {stage2_count} stocks")
        if stage2_rejected > 0:
            logging.info(f"   ❌ Rejected: {stage2_rejected} stocks (insufficient volume/liquidity)")
        
        if df.empty:
            logging.warning("❌ No stocks passed Stage 2")
            return []
        
        # Stage 3: Volatility Filter (ATR%)
        logging.info(f"\n📌 STAGE 3: Volatility Filter (ATR% {self.config.get('min_atr_pct', 0.015)*100:.1f}%-{self.config.get('max_atr_pct', 0.08)*100:.1f}%)")
        stage3_count = df['symbol'].nunique()
        df = self.volatility_filter(
            df,
            min_volatility=self.config.get('min_atr_pct', 0.015),
            max_volatility=self.config.get('max_atr_pct', 0.08)
        )
        stage3_passed = df['symbol'].nunique()
        stage3_rejected = stage3_count - stage3_passed
        stage_counts["volatility_reject"] = stage3_rejected
        logging.info(f"   ✅ Passed: {stage3_passed} / {stage3_count} stocks")
        if stage3_rejected > 0:
            logging.info(f"   ❌ Rejected: {stage3_rejected} stocks (volatility out of range)")
        
        # Final candidates
        candidates = sorted(df['symbol'].unique().tolist()) if not df.empty else []
        
        logging.info(f"\n{'='*80}")
        logging.info(f"✅ PREFILTER COMPLETE: {len(candidates)} final candidates")
        if candidates:
            logging.info(f"   Candidates: {', '.join(candidates[:20])}{'...' if len(candidates) > 20 else ''}")
        logging.info(f"{'='*80}\n")

        self.last_run_stats = {
            "input_count": len(symbols),
            "data_loaded_count": data_loaded_count,
            "passed_count": len(candidates),
            "pass_rate_pct": (len(candidates) / len(symbols) * 100) if symbols else 0.0,
            "rejection_reasons": {k: v for k, v in stage_counts.items() if v > 0},
            "stage_counts": stage_counts,
        }
        
        return candidates

    def get_last_run_stats(self) -> Dict[str, Any]:
        """Return structured stats from the most recent run_filter call."""
        return dict(self.last_run_stats)

    # --- Data loading & caching utilities -------------------------------------------------
    def _now(self) -> dt.datetime:
        return dt.datetime.utcnow()

    def _cache_ttl_seconds(self, intraday: bool) -> int:
        ttl_days = self.CACHE_INTRADAY if intraday else self.CACHE_DAILY
        return max(1, int(ttl_days * 86400))

    def _history_cache_key(self, symbol: str, days: int, intraday: bool) -> Tuple[str, int, str]:
        return symbol.upper(), int(days), "intraday" if intraday else "daily"

    def _load_symbol_history(self, symbol: str, days: int, intraday: bool) -> pd.DataFrame:
        if self.simulation_mode and self.historical_data is not None:
            df = self.historical_data
            if 'symbol' in df.columns:
                sym_df = df[df['symbol'] == symbol].copy()
            else:
                sym_df = df.copy()
                sym_df['symbol'] = symbol
            if days > 0 and not sym_df.empty:
                sym_df = sym_df.sort_values('date').tail(days)
            return sym_df.reset_index(drop=True)

        if self.data_loader is None:
            raise RuntimeError(
                "PreFilter requires a DataLoader instance (or historical_data) to fetch market data"
            )

        try:
            if intraday:
                fetcher = getattr(self.data_loader, 'get_intraday_data', None)
                if callable(fetcher):
                    df = fetcher(symbol, days=days)
                else:
                    logging.warning(
                        "Intraday data requested for %s but data_loader has no get_intraday_data; using daily fallback",
                        symbol,
                    )
                    df = self.data_loader.get_historical_data(symbol, days=days)
            else:
                df = self.data_loader.get_historical_data(symbol, days=days)
        except Exception as exc:
            logging.error("Failed to fetch history for %s: %s", symbol, exc)
            df = pd.DataFrame()

        if not isinstance(df, pd.DataFrame):
            df = pd.DataFrame()

        if not df.empty and 'symbol' not in df.columns:
            df = df.copy()
            df['symbol'] = symbol

        return df.reset_index(drop=True)

    def fetch_history(
        self,
        symbols: Iterable[str],
        days: int = 40,
        use_cache: bool = True,
        intraday: bool = False,
    ) -> pd.DataFrame:
        """Fetch OHLCV history for symbols, honoring the in-memory cache."""
        unique_symbols = [s.upper() for s in dict.fromkeys(symbols)]
        if not unique_symbols:
            return pd.DataFrame(columns=['symbol', 'date', 'open', 'high', 'low', 'close', 'volume'])

        ttl_seconds = self._cache_ttl_seconds(intraday)
        now = self._now()
        frames: List[pd.DataFrame] = []

        for symbol in unique_symbols:
            key = self._history_cache_key(symbol, days, intraday)
            cached = self._history_cache.get(key)
            use_cached = False
            if use_cache and cached:
                age = (now - cached['fetched_at']).total_seconds()
                if age <= ttl_seconds:
                    use_cached = True
            if use_cached:
                frame = cached['data'].copy()
            else:
                frame = self._load_symbol_history(symbol, days, intraday)
                self._history_cache[key] = {
                    'data': frame.copy(),
                    'fetched_at': now,
                }

            if not frame.empty:
                required_cols = {'date', 'open', 'high', 'low', 'close', 'volume', 'symbol'}
                if not required_cols.issubset(frame.columns):
                    missing = required_cols - set(frame.columns)
                    logging.warning("History for %s missing columns: %s", symbol, sorted(missing))
                    continue
                frames.append(frame.copy())

        if not frames:
            logging.warning("fetch_history: no data retrieved for symbols %s", unique_symbols)
            return pd.DataFrame(columns=['symbol', 'date', 'open', 'high', 'low', 'close', 'volume'])

        combined = pd.concat(frames, ignore_index=True)
        combined['date'] = pd.to_datetime(combined['date'])
        self._last_history_frame = combined.copy()
        return combined

    def get_last_history(self) -> Optional[pd.DataFrame]:
        """Return a copy of the most recent combined history frame, if available."""
        if self._last_history_frame is None:
            return None
        return self._last_history_frame.copy()

    def clear_cache(self) -> None:
        """Clear in-memory data caches."""
        self._history_cache.clear()
        self._filtered_cache.clear()

    def _maybe_sleep(self, seconds: float):
        """Sleep only when in diagnostic mode and not explicitly fast."""
        if self.diagnostic_mode and not self.fast_mode:
            time.sleep(seconds)

    def data_completeness_filter(self, df, min_rows=15):
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

    def liquidity_filter(self, df, min_avg_volume=None, min_dollar_volume=None, max_avg_volume=None):
        """Filter based on volume and dollar volume.
        
        IMPORTANT: Calculates 30-day average EXCLUDING today's volume to avoid
        distortion from intraday spikes or unusual activity.
        
        Args:
            max_avg_volume: Optional maximum volume to exclude mega-caps (too stable for mean reversion)
        """
        min_avg_volume = self.MIN_AVG_VOL if min_avg_volume is None else min_avg_volume
        min_dollar_volume = self.MIN_AVG_DOLLAR_VOL if min_dollar_volume is None else min_dollar_volume
        max_avg_volume = self.MAX_AVG_VOL if max_avg_volume is None else max_avg_volume
        volume_range = f"{min_avg_volume:,}"
        if max_avg_volume:
            volume_range = f"{min_avg_volume:,}-{max_avg_volume:,}"
        logging.info(f"Applying liquidity filter. Volume: {volume_range} shares, Min dollar volume: ${min_dollar_volume:,}")
        df = df.copy()
        df.loc[:, 'dollar_volume'] = df['volume'] * df['close']
        
        # Calculate 30-day average EXCLUDING the most recent day (today)
        # This avoids distortion from today's unusual volume
        def calc_avg_excluding_today(series):
            """Calculate average of all days except the most recent"""
            if len(series) < 2:
                return series.mean()  # Not enough data, use what we have
            # Exclude the last (most recent) value
            return series.iloc[:-1].tail(30).mean()
        
        df.loc[:, 'avg_volume'] = df.groupby('symbol')['volume'].transform(calc_avg_excluding_today)
        df.loc[:, 'avg_dollar_volume'] = df.groupby('symbol')['dollar_volume'].transform(calc_avg_excluding_today)
        
        # Apply volume filters
        volume_mask = (df['avg_volume'] >= min_avg_volume) & (df['avg_dollar_volume'] >= min_dollar_volume)
        if max_avg_volume:
            volume_mask = volume_mask & (df['avg_volume'] <= max_avg_volume)
        
        filtered = df[volume_mask]
        logging.info(f"Liquidity filter: {len(filtered['symbol'].unique())} assets remain")
        if 'symbol' in filtered.columns:
            logging.info(f"Symbols passing liquidity filter: {filtered['symbol'].unique().tolist()}")
            print(f"Symbols passing liquidity filter: {filtered['symbol'].unique().tolist()}")
        else:
            logging.warning("No 'symbol' column found in the liquidity filter result.")
        self._maybe_sleep(2)
        return filtered

    def price_range_filter(self, df, min_price=None, max_price=None):
        """Gate by latest close and return full history for eligible symbols."""
        min_price = self.MIN_PRICE if min_price is None else min_price
        max_price = self.MAX_PRICE if max_price is None else max_price
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

    def volatility_filter(self, df, min_volatility=None, max_volatility=None):
        """Filter based on volatility using ATR% for robust short-window behavior."""
        min_volatility = self.MIN_ATR if min_volatility is None else min_volatility
        max_volatility = self.MAX_ATR if max_volatility is None else max_volatility
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

    def extended_yfinance_filter(self, df: pd.DataFrame, 
                                  filter_earnings: bool = True,
                                  filter_ownership: bool = True,
                                  filter_float: bool = True,
                                  add_sector: bool = True) -> pd.DataFrame:
        """
        Apply extended yfinance data filtering:
        1. Filter out stocks with earnings within 5 trading days
        2. Filter out stocks with institutional ownership <30% or >85%
        3. Filter out stocks with float <50M or >5000M shares (avoid micro-caps and mega-caps)
        4. Add sector tagging for diversification tracking
        
        Expected impact: +$1,200/year, win rate +2-4%
        FREE: Uses yfinance library (unlimited calls)
        """
        if df is None or df.empty:
            logging.warning("extended_yfinance_filter: empty input DataFrame")
            return df
        
        if 'symbol' not in df.columns:
            logging.warning("extended_yfinance_filter: no 'symbol' column found")
            return df
        
        symbols = df['symbol'].unique().tolist()
        logging.info(f"🔍 Extended yfinance filtering for {len(symbols)} symbols...")
        
        try:
            import yfinance as yf
            from datetime import datetime, timedelta
        except ImportError:
            logging.warning("⚠️ yfinance not available - skipping extended filtering")
            return df
        
        filtered_symbols = []
        sector_map = {}
        
        for symbol in symbols:
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info
                
                # 1. Earnings filter - avoid stocks with earnings this week
                if filter_earnings:
                    try:
                        earnings_dates = ticker.earnings_dates
                        if earnings_dates is not None and not earnings_dates.empty:
                            # Get next earnings date
                            upcoming = earnings_dates[earnings_dates.index > datetime.now()]
                            if not upcoming.empty:
                                next_earnings = upcoming.index[0]
                                days_to_earnings = (next_earnings - datetime.now()).days
                                
                                if days_to_earnings < 5:
                                    logging.info(f"   ❌ {symbol}: Earnings in {days_to_earnings} days - FILTERED")
                                    continue
                    except Exception as e:
                        logging.debug(f"   ⚠️ {symbol}: Could not fetch earnings dates ({e})")
                
                # 2. Institutional ownership filter
                if filter_ownership:
                    inst_ownership = info.get('heldPercentInstitutions', None)
                    if inst_ownership is not None:
                        inst_pct = inst_ownership * 100
                        if inst_pct < 30 or inst_pct > 85:
                            logging.info(f"   ❌ {symbol}: Inst ownership {inst_pct:.1f}% - FILTERED")
                            continue
                
                # 3. Float filter (avoid micro-caps <50M and mega-caps >5000M)
                if filter_float:
                    float_shares = info.get('floatShares', None)
                    if float_shares is not None:
                        float_millions = float_shares / 1_000_000
                        if float_millions < 50 or float_millions > 5000:
                            logging.info(f"   ❌ {symbol}: Float {float_millions:.1f}M shares - FILTERED")
                            continue
                
                # 4. Add sector tagging
                if add_sector:
                    sector = info.get('sector', 'Unknown')
                    sector_map[symbol] = sector
                
                # Passed all filters
                filtered_symbols.append(symbol)
                logging.info(f"   ✅ {symbol}: Passed all extended filters")
                
            except Exception as e:
                logging.warning(f"   ⚠️ {symbol}: Error fetching yfinance data ({e}) - KEEPING")
                filtered_symbols.append(symbol)  # Keep on error (conservative)
        
        # Filter DataFrame
        if not filtered_symbols:
            logging.warning("⚠️ No symbols passed extended yfinance filtering!")
            return df
        
        result_df = df[df['symbol'].isin(filtered_symbols)].copy()
        
        # Add sector column if requested
        if add_sector and sector_map:
            result_df['sector'] = result_df['symbol'].map(sector_map).fillna('Unknown')
            
            # Log sector distribution
            sector_counts = result_df['sector'].value_counts()
            logging.info(f"📊 Sector distribution after filtering:")
            for sector, count in sector_counts.items():
                logging.info(f"   {sector}: {count} stocks")
        
        logging.info(f"✅ Extended yfinance filter: {len(filtered_symbols)}/{len(symbols)} symbols passed")
        return result_df

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
        if df is None:
            return pd.DataFrame(columns=['symbol', 'score'])

        if df.empty:
            empty = df.copy()
            if 'score' not in empty.columns:
                empty = empty.assign(score=np.nan)
            return empty

        work = df.copy()
        if 'symbol' not in work.columns:
            logging.warning("_rank_candidates received frame without 'symbol' column; returning empty ranking")
            cols = list(work.columns)
            if 'symbol' not in cols:
                cols.insert(0, 'symbol')
            if 'score' not in cols:
                cols.append('score')
            return pd.DataFrame(columns=cols)
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
        Now uses regime-based adjustments for optimal profitability.
        Relax order: breakout > momentum > volatility > liquidity. Never drop data completeness below 30 rows.
        """
        if df is None or df.empty:
            logging.warning("Adaptive candidates: empty input DataFrame")
            return df

        # Apply regime-based adjustments if available
        regime_config = {}
        if self.regime_adjustment and self.regime_filter:
            try:
                # Get market data for regime detection (use SPY-like proxy from available data)
                market_data = self._get_market_proxy_data(df)
                
                # Get recent performance feedback
                performance_feedback = self._get_recent_performance_feedback()
                
                # Update regime configuration
                regime_update = self.regime_filter.update_prefilter_with_regime(
                    self, market_data, performance_feedback
                )
                regime_config = regime_update.get('config', {})
                
                logging.info(f"🎯 Using regime-based config: {regime_update.get('regime', 'unknown')}")
                
            except Exception as e:
                logging.warning(f"Regime adjustment failed, using defaults: {e}")

        # Base thresholds (OPTIMIZED for SMALL PORTFOLIO <$1K mid-cap stocks - Nov 24, 2025)
        # CRITICAL: yfinance free tier only provides ~21 trading days of data
        completeness_rows = 15  # Reduced from 30 (yfinance limitation)
        min_avg_volume = 50_000  # Relaxed from 100K for more candidates
        min_dollar_volume = 500_000  # Relaxed from 1M for more mid-cap opportunities
        min_price, max_price = 5, 50  # $5-50 range for $1K accounts (Option 3 - expanded opportunities)
        
        # Regime-adjusted thresholds (RELAXED for more candidates - Nov 24, 2025)
        min_vol = regime_config.get('min_volatility', 0.015)  # Relaxed from 2% to 1.5%
        max_vol = regime_config.get('max_volatility', 0.12)  # Increased from 8% to 12% for mid-caps
        lookback = 5
        min_mom = regime_config.get('min_momentum', 0.02)  # Relaxed from 3% to 2%
        max_mom = regime_config.get('max_momentum', 0.30)  # Increased from 20% to 30%
        vol_spike_min = regime_config.get('vol_spike_min', 1.0)  # Relaxed from 1.5x to 1.0x (baseline)
        breakout_min = regime_config.get('breakout_min', 0.01)  # Relaxed from 2% to 1%
        
        # Use regime-specific relaxation steps if available
        relaxation_steps = []
        if self.regime_filter and hasattr(self.regime_filter, 'current_regime'):
            relaxation_steps = self.regime_filter._get_regime_relaxation_steps(self.regime_filter.current_regime)
        
        logging.info(f"🎯 Regime-adjusted thresholds: vol_spike={vol_spike_min:.2f}, breakout={breakout_min:.3f}, momentum={min_mom:.3f}")

        def run_once(dfin: pd.DataFrame,
                     breakout_window: int = 20,
                     vol_avg_window: int = 20,
                     minp_frac: float = 0.5) -> pd.DataFrame:
            # Track how many symbols pass each filter
            initial_symbols = dfin['symbol'].nunique() if 'symbol' in dfin.columns else 0
            
            d0 = self.data_completeness_filter(dfin, min_rows=completeness_rows)
            after_completeness = d0['symbol'].nunique() if not d0.empty and 'symbol' in d0.columns else 0
            if d0.empty: 
                logging.info(f"🚫 Filter 1/6 (Completeness): {initial_symbols} → 0 (REJECTED ALL - need {completeness_rows} rows)")
                return d0
            logging.info(f"✅ Filter 1/6 (Completeness): {initial_symbols} → {after_completeness} passed")
            
            d1 = self.liquidity_filter(d0, min_avg_volume=min_avg_volume, min_dollar_volume=min_dollar_volume)
            after_liquidity = d1['symbol'].nunique() if not d1.empty and 'symbol' in d1.columns else 0
            if d1.empty:
                logging.info(f"🚫 Filter 2/6 (Liquidity): {after_completeness} → 0 (REJECTED ALL - need vol>{min_avg_volume:,.0f}, $vol>${min_dollar_volume:,.0f})")
                return d1
            logging.info(f"✅ Filter 2/6 (Liquidity): {after_completeness} → {after_liquidity} passed")
            
            d2 = self.price_range_filter(d1, min_price=min_price, max_price=max_price)
            after_price = d2['symbol'].nunique() if not d2.empty and 'symbol' in d2.columns else 0
            if d2.empty:
                logging.info(f"🚫 Filter 3/6 (Price Range): {after_liquidity} → 0 (REJECTED ALL - need ${min_price:.0f}-${max_price:.0f})")
                return d2
            logging.info(f"✅ Filter 3/6 (Price Range): {after_liquidity} → {after_price} passed")
            
            d3 = self.volatility_filter(d2, min_volatility=min_vol, max_volatility=max_vol)
            after_volatility = d3['symbol'].nunique() if not d3.empty and 'symbol' in d3.columns else 0
            if d3.empty:
                logging.info(f"🚫 Filter 4/6 (Volatility): {after_price} → 0 (REJECTED ALL - need {min_vol:.3f}-{max_vol:.3f})")
                return d3
            logging.info(f"✅ Filter 4/6 (Volatility): {after_price} → {after_volatility} passed")
            
            d4 = self.momentum_filter(d3, lookback=lookback, min_momentum=min_mom, max_momentum=max_mom)
            after_momentum = d4['symbol'].nunique() if not d4.empty and 'symbol' in d4.columns else 0
            if d4.empty:
                logging.info(f"🚫 Filter 5/6 (Momentum): {after_volatility} → 0 (REJECTED ALL - need momentum {min_mom:.3f}-{max_mom:.3f})")
                return d4
            logging.info(f"✅ Filter 5/6 (Momentum): {after_volatility} → {after_momentum} passed")
            
            d5 = self.breakout_filter(
                d4,
                volume_spike_min=vol_spike_min,
                price_breakout_min=breakout_min,
                prior_high_window=breakout_window,
                avg_volume_window=vol_avg_window,
                min_periods_frac=minp_frac,
            )
            after_breakout = d5['symbol'].nunique() if not d5.empty and 'symbol' in d5.columns else 0
            if d5.empty:
                logging.info(f"🚫 Filter 6/6 (Breakout): {after_momentum} → 0 (REJECTED ALL - need vol_spike>{vol_spike_min:.2f}, breakout>{breakout_min:.3f})")
            else:
                logging.info(f"✅ Filter 6/6 (Breakout): {after_momentum} → {after_breakout} passed")
                if after_breakout > 0:
                    passed_symbols = d5['symbol'].unique().tolist()
                    logging.info(f"🎯 Symbols passing all filters: {passed_symbols}")
            
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
            
            # Apply extended yfinance filtering before return
            try:
                out = self.extended_yfinance_filter(out, 
                                                    filter_earnings=True,
                                                    filter_ownership=True,
                                                    filter_float=True,
                                                    add_sector=True)
            except Exception as e:
                logging.warning(f"⚠️ Extended yfinance filtering failed (early return): {e}")
            
            # ============================================================
            # PRIORITY #2: Apply Free Data Optimization Filters
            # ============================================================
            try:
                from free_data_filters import FreeDataFilters
                free_filters = FreeDataFilters()
                
                if free_filters.enabled and not out.empty:
                    symbols_list = out['symbol'].unique().tolist()
                    result = free_filters.apply_all_filters(
                        symbols_list,
                        enable_earnings=True,
                        enable_ownership=True,
                        enable_float=True,
                        enable_ratings=True
                    )
                    
                    # Filter to symbols that passed
                    filtered_symbols = result['filtered_symbols']
                    out = out[out['symbol'].isin(filtered_symbols)].copy()
                    
                    # Apply analyst rating score adjustments
                    analyst_scores = result['analyst_scores']
                    if 'pf_score' in out.columns:
                        out['analyst_boost'] = out['symbol'].map(analyst_scores)
                        out['pf_score'] = out['pf_score'] * out['analyst_boost']
                        out = out.sort_values('pf_score', ascending=False)
                    
                    logging.info(f"✅ Free data filters applied: {len(filtered_symbols)} symbols passed")
                else:
                    logging.warning("⚠️ Free data filters not available or no candidates")
            except Exception as e:
                logging.warning(f"⚠️ Free data filtering failed: {e}")
                import traceback
                traceback.print_exc()
            
            return out

        # Progressive relaxation steps
        steps = [
            {"breakout_min": 0.012},
            {"breakout_min": 0.006, "vol_spike_min": 1.05},  # Further relaxed: was 0.008 & 1.1
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
            completeness_rows = 15  # never relax below 15 (yfinance limitation: ~21 days available)
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
                
                # Apply extended yfinance filtering before return
                try:
                    out = self.extended_yfinance_filter(out, 
                                                        filter_earnings=True,
                                                        filter_ownership=True,
                                                        filter_float=True,
                                                        add_sector=True)
                except Exception as e:
                    logging.warning(f"⚠️ Extended yfinance filtering failed (relaxation loop): {e}")
                
                # ============================================================
                # PRIORITY #2: Apply Free Data Optimization Filters
                # ============================================================
                try:
                    from free_data_filters import FreeDataFilters
                    free_filters = FreeDataFilters()
                    
                    if free_filters.enabled and not out.empty:
                        symbols_list = out['symbol'].unique().tolist()
                        result = free_filters.apply_all_filters(
                            symbols_list,
                            enable_earnings=True,
                            enable_ownership=True,
                            enable_float=True,
                            enable_ratings=True
                        )
                        
                        # Filter to symbols that passed
                        filtered_symbols = result['filtered_symbols']
                        out = out[out['symbol'].isin(filtered_symbols)].copy()
                        
                        # Apply analyst rating score adjustments
                        analyst_scores = result['analyst_scores']
                        if 'pf_score' in out.columns:
                            out['analyst_boost'] = out['symbol'].map(analyst_scores)
                            out['pf_score'] = out['pf_score'] * out['analyst_boost']
                            out = out.sort_values('pf_score', ascending=False)
                        
                        logging.info(f"✅ Free data filters applied: {len(filtered_symbols)} symbols passed")
                    else:
                        logging.warning("⚠️ Free data filters not available or no candidates")
                except Exception as e:
                    logging.warning(f"⚠️ Free data filtering failed: {e}")
                
                return out

        # Final breakout relaxation: AGGRESSIVELY RELAXED for 3-strategy stack (Nov 24, 2025)
        # The 3-strategy stack (Mean Reversion, Gap & Go, Double Bottom) doesn't rely on traditional breakouts
        # TUNED FOR YFINANCE DATA AVAILABILITY (typically ~21 days of history)
        logging.info("Adaptive final relaxation for breakout gating - AGGRESSIVE MODE")
        cur.update({
            'vol_spike_min': 0.3,      # ULTRA-RELAXED from 0.7 - allow any volume pattern
            'breakout_min': 0.0005,    # ULTRA-RELAXED from 0.0015 - 0.05% breakouts valid
            'breakout_window': 5,      # Reduced from 8 - work with limited data
            'vol_avg_window': 5,       # Reduced from 8 - match breakout window
            'minp_frac': 0.2           # Reduced from 0.3 - allow 20% valid data (yfinance gaps)
        })
        vol_spike_min = cur['vol_spike_min']
        breakout_min = cur['breakout_min']
        logging.info(f"Adaptive final thresholds: vol_spike_min={vol_spike_min}, breakout_min={breakout_min}, breakout_window={cur['breakout_window']}, vol_avg_window={cur['vol_avg_window']}")
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
        base = self.data_completeness_filter(df, min_rows=15)  # FREE DATA: Reduced from 90 to work with Alpaca free tier
        base = self.liquidity_filter(base, min_avg_volume=30_000, min_dollar_volume=300_000)
        base = self.price_range_filter(base, min_price=self.MIN_PRICE, max_price=self.MAX_PRICE)
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
        
        # NEW: Apply intraday analysis enhancement if enabled
        if self.enable_intraday_analysis and self.intraday_enhancer:
            try:
                out = self._apply_intraday_enhancement(out)
                logging.info("✅ Intraday analysis applied to PreFilter results")
            except Exception as e:
                logging.warning(f"⚠️ Intraday enhancement failed, using original scores: {e}")
        
        # NEW: Apply extended yfinance filtering (earnings, ownership, float, sector)
        try:
            out = self.extended_yfinance_filter(out, 
                                                filter_earnings=True,
                                                filter_ownership=True,
                                                filter_float=True,
                                                add_sector=True)
            logging.info("✅ Extended yfinance filtering applied")
        except Exception as e:
            logging.warning(f"⚠️ Extended yfinance filtering failed, using original results: {e}")
        
        # NEW FIX #5 & #6: Apply Relative Strength and Sector Rotation Enhancement
        if RelativeStrengthAnalyzer and SectorRotationAnalyzer:
            try:
                logging.info("=" * 60)
                logging.info("🚀 ENHANCEMENT #5 & #6: Relative Strength + Sector Rotation")
                logging.info("=" * 60)
                
                # Step 1: Calculate relative strength vs SPY
                rs_analyzer = RelativeStrengthAnalyzer()
                out = rs_analyzer.calculate_relative_strength(out, lookback=20)
                
                # Filter stocks with RS >= 0.98 (allow slight underperformance to avoid over-filtering)
                before_rs = len(out['symbol'].unique())
                out = rs_analyzer.filter_by_relative_strength(out, min_rs=0.98)
                after_rs = len(out['symbol'].unique())
                logging.info(f"📊 RS Filter: {before_rs} → {after_rs} stocks (filtered {before_rs - after_rs})")
                
                # Step 2: Add sector rotation signals
                if not out.empty:
                    sector_analyzer = SectorRotationAnalyzer()
                    out = sector_analyzer.add_sector_rotation_signal(out)
                    
                    # Adjust pf_score using sector boost
                    if 'sector_boost' in out.columns and 'pf_score' in out.columns:
                        out['pf_score'] = out['pf_score'] * out['sector_boost']
                        boosted = len(out[out['sector_boost'] > 1.0]['symbol'].unique())
                        logging.info(f"✨ Sector Boost: Applied to {boosted} stocks in leading sectors")
                
                logging.info("=" * 60)
                logging.info("✅ Enhancement #5 & #6 complete")
                logging.info("=" * 60)
                
            except Exception as e:
                logging.warning(f"⚠️ RS/Sector enhancement failed, using original results: {e}")
        else:
            logging.warning("⚠️ RS/Sector analyzers not available - skipping enhancement #5 & #6")
        
        return out

    def filter_symbols(self, df):
        """
        Wrapper for the filter_assets method to maintain compatibility.
        """
        return self.filter_assets(df)
    
    def _apply_intraday_enhancement(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply intraday analysis to enhance pf_score
        
        Args:
            df: DataFrame with PreFilter candidates (must have 'symbol', 'close', 'pf_score')
            
        Returns:
            Enhanced DataFrame with updated pf_scores and intraday data
        """
        if df.empty or 'symbol' not in df.columns:
            return df
        
        # Get latest price for each symbol (use 'close' column)
        if 'close' not in df.columns:
            logging.warning("No 'close' column found - cannot apply intraday enhancement")
            return df
        
        # Get unique symbols with their latest prices
        latest_prices = df.groupby('symbol')['close'].last().to_dict()
        
        # Prepare candidates for enhancement
        candidates = []
        for symbol in df['symbol'].unique():
            price = latest_prices.get(symbol)
            score = df[df['symbol'] == symbol]['pf_score'].iloc[0]
            
            if price and score and not pd.isna(price) and not pd.isna(score):
                candidates.append({
                    'symbol': symbol,
                    'current_price': float(price),
                    'pf_score': float(score)
                })
        
        if not candidates:
            logging.warning("No valid candidates for intraday enhancement")
            return df
        
        logging.info(f"📊 Enhancing {len(candidates)} symbols with intraday analysis...")
        
        # Enhance candidates
        enhanced_candidates = self.intraday_enhancer.enhance_candidate_list(candidates)
        
        # Create mapping of enhanced scores
        enhanced_scores = {c['symbol']: c['pf_score'] for c in enhanced_candidates}
        
        # Update DataFrame with enhanced scores
        df = df.copy()
        df['pf_score'] = df['symbol'].map(enhanced_scores).fillna(df['pf_score'])
        
        # Optionally add intraday metadata columns
        intraday_quality = {c['symbol']: c.get('intraday_quality') for c in enhanced_candidates}
        intraday_recommendation = {c['symbol']: c.get('intraday_recommendation') for c in enhanced_candidates}
        
        df['intraday_quality'] = df['symbol'].map(intraday_quality)
        df['intraday_recommendation'] = df['symbol'].map(intraday_recommendation)
        
        # Log enhancements
        for c in enhanced_candidates:
            adj = c.get('intraday_adjustment', 0)
            if abs(adj) > 0.01:  # Only log significant adjustments
                logging.info(f"   {c['symbol']}: {adj:+.2f} ({c.get('intraday_recommendation', 'N/A')})")
        
        # Get and log API usage stats
        stats = self.intraday_enhancer.get_statistics()
        logging.info(f"📊 Intraday API usage: {stats['analyses_today']}/{stats['max_analyses_per_day']} analyses, "
                    f"{stats['api_usage'].get('calls_today', 0)} API calls")
        
        return df
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

    def breakout_filter(self, df, volume_spike_min=1.2, price_breakout_min=0.005,
                        prior_high_window: int = 10, avg_volume_window: int = 15, min_periods_frac: float = 0.4):
        """Find stocks breaking out with volume confirmation and gate by latest snapshot.
        IMPROVEMENT #4: Reduced requirements to pass more quality stocks.
        - prior_high_window: 20→10 days (less data needed, more responsive)
        - avg_volume_window: 20→15 days (less data needed)
        - min_periods_frac: 0.5→0.4 (accept stocks with slightly less history)
        - volume_spike_min: default 2.0→1.2 (more realistic for D+1 moves)
        - price_breakout_min: default 0.03→0.005 (0.5% is sufficient for D+1)
        """
        logging.info("Applying breakout filter - CRITICAL for 5% weekly targets")
        logging.info(f"📊 Breakout parameters: vol_spike≥{volume_spike_min:.1f}x, price_breakout≥{price_breakout_min:.2%}, window={prior_high_window}d")
        
        if df.empty:
            logging.warning("Breakout filter: Input DataFrame is empty. Returning as-is.")
            return df
        required = {'symbol','date','close','high','volume'}
        if not required.issubset(df.columns):
            logging.warning(f"Breakout filter: Required columns missing. Columns: {df.columns.tolist()}. Returning as-is.")
            return df

        work = df.copy().sort_values(['symbol','date'])
        # Volume spike vs configurable moving average
        minp = max(4, int(avg_volume_window * min_periods_frac))  # Reduced from 5
        work.loc[:, 'avg_volume_20'] = work.groupby('symbol')['volume'].transform(lambda x: x.rolling(avg_volume_window, min_periods=minp).mean())
        work.loc[:, 'volume_spike'] = work['volume'] / work['avg_volume_20']
        # Prior high window (exclude current bar) - REDUCED for more responsiveness
        minp_high = max(4, int(prior_high_window * min_periods_frac))  # Reduced from 5
        work.loc[:, 'prior_high_20'] = work.groupby('symbol')['high'].transform(lambda x: x.rolling(prior_high_window, min_periods=minp_high).max().shift(1))
        work.loc[:, 'price_breakout'] = (work['close'] - work['prior_high_20']) / work['prior_high_20']

        # Evaluate only latest row per symbol
        snap = work.groupby('symbol').tail(1)
        
        # DEBUG: Show detailed breakout calculations
        logging.info("DEBUG: Breakout filter calculations:")
        for _, row in snap.iterrows():
            logging.info(f"  {row['symbol']}: vol_spike={row['volume_spike']:.2f} (need>={volume_spike_min}), "
                        f"price_breakout={row['price_breakout']:.4f} (need>={price_breakout_min:.4f}), "
                        f"prior_high_notna={pd.notna(row['prior_high_20'])}")
        
        eligible = snap[(snap['prior_high_20'].notna()) &
                        (snap['volume_spike'] >= volume_spike_min) &
                        (snap['price_breakout'] >= price_breakout_min)]['symbol'].tolist()
        logging.info(f"Breakout filter: {len(eligible)} symbols pass (vol_spike>={volume_spike_min}, breakout>={price_breakout_min:.1%})")
        if eligible:
            logging.info(f"Symbols passing breakout: {eligible}")
            print(f"Symbols passing breakout filter: {eligible}")
        else:
            logging.warning("No symbols passed breakout filter. Check thresholds or data quality.")
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
        df = self.data_completeness_filter(df, min_rows=15)
        
        # Step 2: Liquidity (ensure tradability) - Relaxed for more opportunities
        df = self.liquidity_filter(df, min_avg_volume=100_000, min_dollar_volume=1_000_000)
        
        # Step 3: Price range - SMALL PORTFOLIO: $10-30 for mid-cap volatiles
        df = self.price_range_filter(df, min_price=10, max_price=30)
        
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
        df = self.data_completeness_filter(df, min_rows=15)  # FREE DATA: Reduced from 30 to work with Alpaca free tier
        
        # Step 2: LOOSER liquidity (more opportunities)
        df = self.liquidity_filter(df, min_avg_volume=50_000, min_dollar_volume=500_000)
        
        # Step 3: Price range - SMALL PORTFOLIO: $10-30 for mid-cap volatiles
        df = self.price_range_filter(df, min_price=10, max_price=30)
        
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
        df = self.data_completeness_filter(df, min_rows=15)

        # Step 2: Liquidity Filter
        df = self.liquidity_filter(df, min_avg_volume=100_000, min_dollar_volume=1_000_000)

        # Step 3: Price Range Filter - SMALL PORTFOLIO: $10-30 for mid-cap volatiles
        df = self.price_range_filter(df, min_price=10, max_price=30)

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

    def load_and_filter_data(
        self,
        df: Optional[pd.DataFrame] = None,
        use_cache: bool = True,
        symbols: Optional[Iterable[str]] = None,
        days: int = 40,
        intraday: bool = False,
        pipeline: str = "adaptive",
    ) -> pd.DataFrame:
        """Load market data (optionally fetching it) and run a filtering pipeline with caching."""

        # Backwards compatibility: provided DataFrame, just mark as filtered once
        if df is not None:
            if use_cache:
                logging.info("Using cached data. Ensuring filters are not applied twice.")
                if 'filtered' in df.columns and bool(df['filtered'].iloc[0]):
                    logging.warning("Data has already been filtered. Skipping redundant filtering.")
                    return df

            df = df.copy()
            df['filtered'] = True
            logging.info("Data marked as filtered (legacy path).")
            return df

        if not symbols:
            raise ValueError("load_and_filter_data requires either a DataFrame or a list of symbols")

        symbol_tuple = tuple(sorted(dict.fromkeys([s.upper() for s in symbols])))
        cache_key = (symbol_tuple, int(days), pipeline, intraday)

        if use_cache:
            cached = self._filtered_cache.get(cache_key)
            if cached:
                age = (self._now() - cached['fetched_at']).total_seconds()
                if age <= self._cache_ttl_seconds(intraday):
                    logging.info("Returning cached filtered universe for %s", symbol_tuple)
                    return cached['data'].copy()

        history = self.fetch_history(symbol_tuple, days=days, use_cache=use_cache, intraday=intraday)
        if history.empty:
            logging.warning("No historical data fetched for symbols %s", symbol_tuple)
            filtered = history
        else:
            if pipeline == "adaptive":
                filtered = self.filter_assets(history)
            elif pipeline == "aggressive":
                filtered = self.aggressive_filter_pipeline(history)
            elif pipeline == "gradual":
                filtered = self.gradual_filter_pipeline(history)
            else:
                logging.warning("Unknown pipeline '%s'; defaulting to adaptive", pipeline)
                filtered = self.filter_assets(history)

        if use_cache:
            self._filtered_cache[cache_key] = {
                'data': filtered.copy(),
                'fetched_at': self._now(),
            }

        return filtered
    
    def _get_market_proxy_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Extract or create market proxy data for regime detection
        Uses largest volume symbols as market proxy if SPY/QQQ not available
        """
        try:
            # Check if we have SPY or QQQ data
            market_symbols = ['SPY', 'QQQ', 'IWM']
            for symbol in market_symbols:
                if symbol in df['symbol'].values:
                    proxy_data = df[df['symbol'] == symbol].copy()
                    if len(proxy_data) > 10:  # Sufficient data
                        return proxy_data.sort_values('date')
            
            # If no market ETFs, use aggregate data from high-volume stocks
            if 'volume' in df.columns and 'close' in df.columns:
                # Get top volume symbols and create market proxy
                latest_data = df.groupby('symbol').tail(1)
                top_volume_symbols = latest_data.nlargest(10, 'volume')['symbol'].tolist()
                
                market_data = df[df['symbol'].isin(top_volume_symbols)].copy()
                
                # Create aggregate market proxy
                market_proxy = market_data.groupby('date').agg({
                    'close': 'mean',
                    'high': 'mean', 
                    'low': 'mean',
                    'open': 'mean',
                    'volume': 'sum'
                }).reset_index()
                
                return market_proxy.sort_values('date')
            
            return pd.DataFrame()  # Empty if no suitable data
            
        except Exception as e:
            logging.warning(f"Error creating market proxy data: {e}")
            return pd.DataFrame()
    
    def _get_recent_performance_feedback(self) -> Dict:
        """
        Get recent performance feedback for regime adjustment
        Reads from trade logs or position data
        """
        try:
            performance = {
                'win_rate': 0.5,
                'trade_frequency': 1.0,
                'avg_return': 0.0
            }
            
            # Try to read recent trade performance from logs
            log_files = [
                'logs/trade_explanations_' + dt.datetime.now().strftime('%Y-%m-%d') + '.json',
                'logs/short_cycle_trader.log'
            ]
            
            for log_file in log_files:
                if os.path.exists(log_file):
                    performance = self._parse_performance_from_logs(log_file)
                    break
            
            return performance
            
        except Exception as e:
            logging.warning(f"Error getting performance feedback: {e}")
            return {'win_rate': 0.5, 'trade_frequency': 1.0, 'avg_return': 0.0}
    
    def _parse_performance_from_logs(self, log_file: str) -> Dict:
        """Parse performance metrics from trade logs"""
        try:
            if log_file.endswith('.json'):
                # Parse JSON trade explanations
                trades = []
                with open(log_file, 'r') as f:
                    for line in f:
                        try:
                            trade = json.loads(line.strip())
                            if trade.get('action') == 'EXIT' and 'performance' in trade:
                                trades.append(trade['performance'])
                        except:
                            continue
                
                if trades:
                    win_rate = sum(1 for t in trades if t.get('realized_pnl', 0) > 0) / len(trades)
                    avg_return = np.mean([t.get('return_pct', 0) for t in trades])
                    trade_frequency = len(trades) / 5  # Assume 5 trading days
                    
                    return {
                        'win_rate': win_rate,
                        'trade_frequency': trade_frequency, 
                        'avg_return': avg_return
                    }
            
            # Default fallback
            return {'win_rate': 0.5, 'trade_frequency': 1.0, 'avg_return': 0.0}
            
        except Exception as e:
            logging.warning(f"Error parsing performance from {log_file}: {e}")
            return {'win_rate': 0.5, 'trade_frequency': 1.0, 'avg_return': 0.0}

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

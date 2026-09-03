"""
Regime Detector
Purpose: Classify market conditions (bullish, bearish, volatile, sideways)
"""

import numpy as np
import pandas as pd
import logging
from core.indicators import calculate_choppiness_index
from utils.logger import log_event, log_error

# Set up logger for LiteBot
logger = logging.getLogger("LiteBot")

class RegimeDetector:
    """
    Standardized regime detector for LiteBot, with a simple interface for integration.
    """
    def __init__(self, config=None):
        self.config = config or {}
        self.last_regime = None
        self.log_data = []

    def calculate_sma_slope(self, series: pd.Series, window: int = 10, suppress_warnings: bool = False) -> float:
        series = series.dropna()
        if len(series) < window:
            if not suppress_warnings:
                log_error("regime_detector", "sma_slope_not_enough_data", f"Needed {window}, Got {len(series)}", "WARNING")
            return float("nan")
        sma = series.rolling(window=window).mean().dropna()
        y = sma.values
        x = np.arange(len(y))
        if len(x) < 2:
            if not suppress_warnings:
                log_error("regime_detector", "sma_slope_not_enough_points", f"Needed ≥2, Got {len(x)}", "WARNING")
            return float("nan")
        try:
            slope = np.polyfit(x, y, 1)[0]
        except np.linalg.LinAlgError as e:
            if not suppress_warnings:
                log_error("regime_detector", "sma_slope_polyfit_failed", str(e), "WARNING")
            return float("nan")
        return float(slope)

    def calculate_volatility(self, series: pd.Series, window: int = 20) -> float:
        series = series.dropna()
        if len(series) < 3:
            log_error("regime_detector", "volatility_not_enough_data", "Not enough data", "WARNING")
            return float("nan")
        log_returns = np.log(series / series.shift(1)).dropna()
        window = min(window, len(log_returns))
        volatility = log_returns.rolling(window=window).std()
        if volatility.empty or volatility.isna().all():
            log_error("regime_detector", "volatility_empty", "Volatility series is empty or all NaN.", "WARNING")
            return float("nan")
        return float(volatility.dropna().iloc[-1])

    def _rth_only(self, df: pd.DataFrame) -> pd.DataFrame:
        """Filter to regular trading hours (ET 9:30-16:00). Assumes df index is tz-aware UTC or ET.
        Keeps intraday bars within RTH; for daily bars, pass-through."""
        idx = df.index
        if not isinstance(idx, pd.DatetimeIndex):
            return df
        if idx.tz is None:
            # Assume UTC if naive
            idx = idx.tz_localize("UTC")
        # Convert to US/Eastern and filter time window
        et = idx.tz_convert("US/Eastern")
        if getattr(df, "freq", None) == "D" or (et.hour.nunique() == 1 and et.minute.nunique() == 1):
            return df
        mask = (et.hour > 9) | ((et.hour == 9) & (et.minute >= 30))
        mask &= (et.hour < 16)
        return df.loc[mask]

    def _resample_daily_rth_close(self, df: pd.DataFrame) -> pd.DataFrame:
        """Resample intraday RTH bars to daily using close price."""
        if not isinstance(df.index, pd.DatetimeIndex):
            return df
        if df.index.tz is None:
            dfi = df.copy()
            dfi.index = dfi.index.tz_localize("UTC")
        else:
            dfi = df
        dfi = self._rth_only(dfi)
        # Daily resample on Eastern calendar days
        dfi_et = dfi.tz_convert("US/Eastern")
        daily = dfi_et.resample("1D").agg({
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum"
        }).dropna(how="all")
        # Back to UTC index
        if daily.index.tzinfo is None:
            daily.index = daily.index.tz_localize("US/Eastern").tz_convert("UTC")
        else:
            daily.index = daily.index.tz_convert("UTC")

        return daily

    def detect_regime(self, df: pd.DataFrame, symbol_class: str = "default") -> str:
        if df is None or df.empty:
            log_error("regime_detector", "empty_dataframe", "DataFrame is empty or None.", "ERROR")
            return "unknown"
        
        # Use original data first, only resample if necessary
        dfi = df.copy()
        
        # Check if we have enough data before any processing
        close = dfi["close"] if "close" in dfi.columns else dfi["Close"] if "Close" in dfi.columns else None
        if close is None:
            log_error("regime_detector", "no_close_column", "No 'close' or 'Close' column found.", "ERROR")
            return "unknown"
            
        # Log original data size
        original_data_points = len(close.dropna())
        logger.info(f"[RegimeDetector] Original data points: {original_data_points}")
        
        # Only resample if we have intraday data with timezone info and sufficient data
        if (isinstance(dfi.index, pd.DatetimeIndex) and 
            dfi.index.tz is not None and 
            original_data_points > 50 and 
            (dfi.index.freq is None or str(dfi.index.freq) not in {"D", "1D"})):
            try:
                dfi_resampled = self._resample_daily_rth_close(dfi)
                close_resampled = dfi_resampled["close"] if "close" in dfi_resampled.columns else dfi_resampled["Close"] if "Close" in dfi_resampled.columns else None
                if close_resampled is not None and len(close_resampled.dropna()) >= 10:
                    dfi = dfi_resampled
                    close = close_resampled
                    logger.info(f"[RegimeDetector] Used resampled data with {len(close.dropna())} points")
                else:
                    logger.info(f"[RegimeDetector] Resampling reduced data too much, using original data")
            except Exception as e:
                logger.warning(f"[RegimeDetector] Resampling failed: {e}, using original data")
        
        # Final data validation
        if close.dropna().shape[0] < 10:
            log_error("regime_detector", "not_enough_close_data", f"Not enough valid close data to detect regime. Have {close.dropna().shape[0]}, need 10", "WARNING")
            return "unknown"
        threshold_map = {
            "crypto": {"slope": 0.01, "volatility": 0.025, "choppiness": 58},
            "stock":  {"slope": 0.005, "volatility": 0.015, "choppiness": 61.8},
            "meme":   {"slope": 0.02, "volatility": 0.05, "choppiness": 50},
            "default": {"slope": 0.01, "volatility": 0.02, "choppiness": 60}
        }
        thresholds = threshold_map.get(symbol_class, threshold_map["default"])
        slope = self.calculate_sma_slope(close)
        volatility = self.calculate_volatility(close)
        if np.isnan(slope) or np.isnan(volatility):
            log_error("regime_detector", "nan_slope_or_vol", "Slope or volatility is NaN.", "WARNING")
            return "unknown"
        trend_direction = np.sign(slope)
        window = 10
        def safe_sma_slope(x):
            if len(x.dropna()) < window:
                return float('nan')
            return self.calculate_sma_slope(x, window=window, suppress_warnings=True)
        rolling_slope = close.rolling(window=window).apply(safe_sma_slope)
        trend_duration = 0
        for val in reversed(rolling_slope.dropna().values):
            if np.sign(val) == trend_direction:
                trend_duration += 1
            else:
                break
        try:
            df = calculate_choppiness_index(df, window=14)
            choppiness = df['choppiness_index'].dropna().iloc[-1]
        except Exception as e:
            log_error("regime_detector", "choppiness_calc_failed", str(e), "WARNING")
            choppiness = None
        if choppiness is not None and choppiness >= thresholds["choppiness"]:
            regime = "rangebound"
        elif trend_duration >= 3 and slope > thresholds["slope"] and volatility < thresholds["volatility"]:
            regime = "bull"
        elif trend_duration >= 3 and slope < -thresholds["slope"] and volatility < thresholds["volatility"]:
            regime = "bear"
        elif volatility >= thresholds["volatility"]:
            regime = "volatile"
        else:
            regime = "sideways"
        self.last_regime = regime
        self.log_data.append({"timestamp": pd.Timestamp.now().isoformat(), "regime": regime})
        
        # Add logging for the test
        logger.info(f"[RegimeDetector] Detected regime: {regime}")
        
        log_event("regime_detector", {"event": "regime_decision", "regime": regime, "timestamp": pd.Timestamp.now().isoformat()})
        print(f"Detected regime: {regime}")
        return regime

    def log_results(self, filename="regime_detector_results.csv"):
        df = pd.DataFrame(self.log_data)
        df.to_csv(filename, index=False)
        log_event("regime_detector", {"event": "results_logged", "filename": filename, "timestamp": pd.Timestamp.now().isoformat()})

    def _atr14_pct(self, df: pd.DataFrame) -> float:
        """ATR(14)/close for daily bars. Expects columns: high, low, close."""
        req = {"high", "low", "close"}
        if df is None or df.empty or not req.issubset(set(df.columns)):
            log_error("regime_detector", "atr_missing_cols", "Need high/low/close for ATR.", "WARNING")
            return float("nan")
        h, l, c = df["high"], df["low"], df["close"]
        prev_c = c.shift(1)
        tr = pd.concat([(h - l).abs(), (h - prev_c).abs(), (l - prev_c).abs()], axis=1).max(axis=1)
        atr = tr.rolling(14, min_periods=14).mean()
        atr_pct = (atr / c).iloc[-1] if atr.notna().any() else float("nan")
        return float(atr_pct)

    def detect_market_regime_spy(self, df_spy: pd.DataFrame) -> dict:
        """
        Strict SPY regime gates per plan:
        - Trend gate: close > SMA100 => UP, else DOWN
        - Vol gate: ATR14/close <= 2% => LOWVOL, else HIGHVOL
        Returns: {"label": str, "beta": float}
        """
        logger = logging.getLogger("LiteBot")

        if df_spy is None or df_spy.empty:
            log_error("regime_detector", "spy_missing", "SPY DataFrame is empty.", "ERROR")
            return {"label": "UNKNOWN", "beta": 0.3}

        dfd = df_spy.copy()
        # Ensure daily bars (use last close per day if intraday)
        if isinstance(dfd.index, pd.DatetimeIndex) and (dfd.index.freq is None or str(dfd.index.freq) not in {"D", "1D"}):
            dfd = self._resample_daily_rth_close(dfd)

        if dfd.shape[0] < 120:
            log_error("regime_detector", "spy_not_enough_bars", f"Have {dfd.shape[0]} daily bars, need >=120.", "WARNING")
            return {"label": "UNKNOWN", "beta": 0.3}

        dfd["sma100"] = dfd["close"].rolling(100, min_periods=100).mean()
        last = dfd.iloc[-1]
        trend_up = bool(last["close"] > last["sma100"])
        atr_pct = self._atr14_pct(dfd)
        if np.isnan(atr_pct):
            log_error("regime_detector", "spy_atr_nan", "ATR% is NaN.", "WARNING")
            return {"label": "UNKNOWN", "beta": 0.3}

        low_vol = bool(atr_pct <= 0.02)  # 2%

        if trend_up and low_vol:
            label, beta = "UP_LOWVOL", 1.0
        elif trend_up and not low_vol:
            label, beta = "UP_HIGHVOL", 0.6
        elif (not trend_up) and low_vol:
            label, beta = "DOWN_LOWVOL", 0.5
        else:
            label, beta = "DOWN_HIGHVOL", 0.3

        logger.info(f"[RegimeDetector] SPY regime={label} | atr_pct={atr_pct:.3%} | close={last['close']:.2f} vs sma100={last['sma100']:.2f}")
        log_event("regime_detector", {"event": "spy_regime", "label": label, "atr_pct": float(atr_pct), "beta": beta})
        return {"label": label, "beta": beta}

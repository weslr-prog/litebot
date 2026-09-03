import pandas as pd
import numpy as np
import logging
from core.module_interface import LiteBotModuleInterface
from core.data_access import get_stock_data
import hashlib
import os

logger = logging.getLogger("LiteBot")

# Indicator calculation functions

def calculate_rsi(df, window=14):
    df = df.copy()
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    return df

def calculate_macd(df, short_window=12, long_window=26, signal_window=9):
    df = df.copy()
    df['ema_short'] = df['close'].ewm(span=short_window, adjust=False).mean()
    df['ema_long']  = df['close'].ewm(span=long_window, adjust=False).mean()
    df['macd']      = df['ema_short'] - df['ema_long']
    df['macd_signal'] = df['macd'].ewm(span=signal_window, adjust=False).mean()
    return df

def calculate_bollinger_bands(df, window=20, num_std_dev=2):
    df = df.copy()
    df['bb_middle'] = df['close'].rolling(window=window).mean()
    df['bb_std']    = df['close'].rolling(window=window).std()
    df['bb_upper']  = df['bb_middle'] + num_std_dev * df['bb_std']
    df['bb_lower']  = df['bb_middle'] - num_std_dev * df['bb_std']
    return df

def calculate_moving_averages(df, short_window=20, long_window=50):
    df = df.copy()
    df['short_ma'] = df['close'].rolling(window=short_window).mean()
    df['long_ma']  = df['close'].rolling(window=long_window).mean()
    return df

def calculate_choppiness_index(df: pd.DataFrame, window: int = 14) -> pd.DataFrame:
    """
    Adds a 'choppiness_index' column to the DataFrame.
    A high value (> 61.8) suggests a sideways (range-bound) market.
    A low value (< 38.2) suggests a trending market.
    """
    df = df.copy()
    df.columns = df.columns.str.lower()
    high = df['high']
    low = df['low']
    close = df['close']
    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    sum_tr = true_range.rolling(window=window).sum()
    max_high = high.rolling(window=window).max()
    min_low = low.rolling(window=window).min()
    choppiness = 100 * np.log10(sum_tr / (max_high - min_low)) / np.log10(window)
    df['choppiness_index'] = choppiness
    return df

def calculate_vwap(df):
    df = df.copy()
    df["vwap_num"] = df["volume"] * (df["high"] + df["low"] + df["close"]) / 3
    df["vwap_den"] = df["volume"]
    df["vwap"] = df["vwap_num"].cumsum() / df["vwap_den"].cumsum()
    return df

def calculate_atr(df, period: int = 14):
    """
    Calculate Average True Range (ATR) using Wilder's smoothing (EMA).
    Returns the latest ATR value as a float, or None if invalid.
    """
    try:
        df = df.copy()
        if df.isnull().values.any() or len(df) < period + 1:
            return None
        high = df["high"]
        low = df["low"]
        close = df["close"]
        tr1 = high - low
        tr2 = (high - close.shift()).abs()
        tr3 = (low - close.shift()).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.ewm(alpha=1/period, adjust=False).mean()
        if atr.empty or pd.isna(atr.iloc[-1]):
            logger.warning("[ATR] ATR calculation returned NaN or empty.")
            return None
        return atr.iloc[-1]
    except Exception as e:
        logger.warning(f"⚠️ Failed to calculate ATR: {e}")
        return None

# ==========================================
# LiteBotModuleInterface-Compliant Classes
# ==========================================

class IndicatorsModule(LiteBotModuleInterface):
    """
    Modular indicator calculator for LiteBot pipeline compatibility.
    Can batch-calculate indicators according to config.
    """
    def __init__(self, indicators=None):
        self.indicators = indicators or ["rsi", "macd"]
        self.last_df = None
        self.log_data = []
    def fit(self, X=None, y=None):
        pass
    def predict(self, df):
        df = df.copy()
        applied = []
        if isinstance(self.indicators, (list, tuple)):
            for ind in self.indicators:
                if ind == "rsi":
                    df = calculate_rsi(df)
                    applied.append("rsi")
                elif ind == "macd":
                    df = calculate_macd(df)
                    applied.append("macd")
                elif ind == "bollinger":
                    df = calculate_bollinger_bands(df)
                    applied.append("bollinger")
                elif ind == "ma":
                    df = calculate_moving_averages(df)
                    applied.append("ma")
                elif ind == "choppiness":
                    df = calculate_choppiness_index(df)
                    applied.append("choppiness")
                elif ind == "vwap":
                    df = calculate_vwap(df)
                    applied.append("vwap")
        elif isinstance(self.indicators, dict):
            for ind, params in self.indicators.items():
                if ind == "rsi":
                    df = calculate_rsi(df, **params)
                    applied.append("rsi")
                elif ind == "macd":
                    df = calculate_macd(df, **params)
                    applied.append("macd")
                elif ind == "bollinger":
                    df = calculate_bollinger_bands(df, **params)
                    applied.append("bollinger")
                elif ind == "ma":
                    df = calculate_moving_averages(df, **params)
                    applied.append("ma")
                elif ind == "choppiness":
                    df = calculate_choppiness_index(df, **params)
                    applied.append("choppiness")
                elif ind == "vwap":
                    df = calculate_vwap(df, **params)
                    applied.append("vwap")
        self.last_df = df
        self.log_data.append({
            "event": "predict",
            "applied": applied
        })
        return df
    def score(self, X=None, y=None):
        return None
    def log_results(self, filename="indicators_module_log.json"):
        import json
        with open(filename, "w") as f:
            json.dump(self.log_data, f, indent=2)
        logger.info(f"[IndicatorsModule] Results logged to {filename}")

class AllIndicatorsCalculator(LiteBotModuleInterface):
    """
    Calculates and saves all indicators for a batch of symbols, pipeline-compatible.
    """
    def __init__(self, interval="1d", period="6mo", save_dir="data/indicators"):
        self.interval = interval
        self.period = period
        self.save_dir = save_dir
        self.log_data = []
    def fit(self, X=None, y=None):
        pass
    def _cache_path(self, symbol):
        key = f"{symbol}_{self.interval}_{self.period}"
        h = hashlib.md5(key.encode()).hexdigest()
        return f"{self.save_dir}/cache_{h}.csv"
    def _cache_valid(self, path, df):
        if not os.path.exists(path):
            return False
        try:
            cached = pd.read_csv(path, index_col=0, parse_dates=True)
            return len(cached) == len(df)
        except Exception:
            return False
    def _save_cache(self, path, df):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        df.to_csv(path)
    def predict(self, symbols):
        results = []
        for symbol in symbols:
            try:
                df = get_stock_data(symbol, interval=self.interval, period=self.period)
                if df is None or df.empty:
                    continue
                cache_path = self._cache_path(symbol)
                if self._cache_valid(cache_path, df):
                    logger.info(f"[Indicators] Using cached indicators for {symbol} from {cache_path}")
                    df = pd.read_csv(cache_path, index_col=0, parse_dates=True)
                else:
                    df = calculate_rsi(df)
                    df = calculate_macd(df)
                    df = calculate_bollinger_bands(df)
                    df = calculate_moving_averages(df)
                    self._save_cache(cache_path, df)
                    logger.info(f"[Indicators] Calculated and cached for {symbol} at {cache_path}")
                filepath = f"{self.save_dir}/{symbol}.csv"
                df.to_csv(filepath)
                logger.info(f"[Indicators] Saved for {symbol} at {filepath}")
                results.append(symbol)
                self.log_data.append({
                    "symbol": symbol,
                    "status": "success",
                    "filepath": filepath
                })
            except Exception as e:
                logger.warning(f"[Indicators] Failed for {symbol}: {e}")
                self.log_data.append({
                    "symbol": symbol,
                    "status": "fail",
                    "error": str(e)
                })
        return results
    def score(self, X=None, y=None):
        return None
    def log_results(self, filename="all_indicators_log.json"):
        import json
        with open(filename, "w") as f:
            json.dump(self.log_data, f, indent=2)
        logger.info(f"[AllIndicatorsCalculator] Results logged to {filename}")

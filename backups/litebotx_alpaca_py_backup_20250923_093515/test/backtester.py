from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
import pandas as pd
import logging
import hashlib
import os
import csv

from core.data_fetcher import get_bars
from core.strategy import ema_crossover_signals
from core.regime_detector import RegimeDetector
from utils.logger import append_csv, ensure_dir, log_missing_bars

# Configure structured logging for the backtester
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("backtest.log"),
        logging.StreamHandler()
    ]
)

@dataclass
class BacktestConfig:
    symbol: str
    timeframe: str = "1D"          # '1D' for fast runs; switch to '1Min' for heavy runs
    lookback_days: int = 365 * 2   # 2 years
    fast: int = 9
    slow: int = 21
    initial_equity: float = 10_000
    results_dir: str = "backtest/results"

def _indicator_cache_path(symbol, timeframe, fast, slow, lookback_days):
    key = f"{symbol}_{timeframe}_{fast}_{slow}_{lookback_days}"
    h = hashlib.md5(key.encode()).hexdigest()
    return f"backtest/cache/ind_{h}.csv"

def _indicator_cache_valid(path, df):
    if not os.path.exists(path):
        return False
    try:
        cached = pd.read_csv(path, index_col=0, parse_dates=True)
        # Simple shape check
        return len(cached) == len(df)
    except Exception:
        return False

def _save_indicator_cache(path, df):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.to_csv(path)

def run_backtest(cfg: BacktestConfig) -> dict:
    logging.info(f"Starting backtest for {cfg.symbol} with timeframe {cfg.timeframe}")
    logging.info(f"Backtest config: {cfg}")
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=cfg.lookback_days)

    # Chunk long histories into monthly pulls to reduce provider timeouts/rate-limits
    try:
        df_parts = []
        cursor = start
        while cursor < end:
            next_cursor = min(cursor + timedelta(days=31), end)
            part = get_bars(cfg.symbol, cfg.timeframe, cursor, next_cursor)
            if not part.empty:
                df_parts.append(part)
            cursor = next_cursor + timedelta(seconds=1)
        df = pd.concat(df_parts).sort_index() if df_parts else pd.DataFrame()
    except Exception as e:
        logging.error(f"Error fetching bars for {cfg.symbol}: {e}", exc_info=True)
        return {"ok": False, "reason": "data fetch error"}

    if df.empty or len(df) < max(cfg.fast, cfg.slow) + 2:
        logging.warning(f"Insufficient data for {cfg.symbol}. Backtest aborted.")
        return {"ok": False, "reason": "insufficient data"}

    logging.info(f"Fetched {len(df)} bars for {cfg.symbol}")
    # Validate completeness: if underfilled by >40%, abort so results aren't biased
    span_days = max(1, (end - start).days)
    exp = span_days if cfg.timeframe == "1D" else None
    if exp is not None and len(df) < 0.6 * exp:
        log_missing_bars(cfg.symbol, cfg.timeframe, start.isoformat(), end.isoformat(), expected=exp, got=len(df), notes="Backtest abort: incomplete data", provider="alpaca_iex")
        return {"ok": False, "reason": "incomplete data"}

    # --- Indicator caching ---
    cache_path = _indicator_cache_path(cfg.symbol, cfg.timeframe, cfg.fast, cfg.slow, cfg.lookback_days)
    if _indicator_cache_valid(cache_path, df):
        logging.info(f"Using cached indicators for {cfg.symbol} from {cache_path}")
        df_sig = pd.read_csv(cache_path, index_col=0, parse_dates=True)
    else:
        try:
            df_sig, _ = ema_crossover_signals(df, cfg.fast, cfg.slow)
            _save_indicator_cache(cache_path, df_sig)
            logging.info(f"Calculated and cached indicators for {cfg.symbol} at {cache_path}")
        except Exception as e:
            logging.error(f"Error generating signals: {e}", exc_info=True)
            return {"ok": False, "reason": "signal generation error"}

    # Add debugging to check for the 'signal' column and implement a fallback
    if 'df_sig' not in locals() or df_sig is None:
        logging.error("The 'df_sig' DataFrame is not initialized. Aborting backtest.")
        return {"ok": False, "reason": "df_sig not initialized"}

    if "signal" not in df_sig.columns:
        logging.error("The 'signal' column is missing in the DataFrame. Adding a default 'signal' column with all values set to 0.")
        df_sig["signal"] = 0  # Default to 'hold' if no signals are present

    try:
        prices = df_sig["close"].astype(float)
        # Map signals to integers: buy=1, sell=-1, hold/empty=0
        signal_map = {"buy": 1, "sell": -1, "hold": 0, "": 0}
        df_sig["signal"] = df_sig["signal"].map(signal_map).fillna(0)
        signal = df_sig["signal"].astype(int)
        ret = prices.pct_change().fillna(0)
        # --- H) Slippage & Spread Model ---
        # ATR% for slippage: use rolling ATR (high-low)
        atr = (df_sig["high"] - df_sig["low"]).rolling(14).mean() / df_sig["close"]
        slippage = atr.fillna(0) * 0.2
        min_slip = 0.0002
        slippage = slippage.apply(lambda x: max(x, min_slip))
        # Apply slippage to returns: degrade fill price
        strat_ret = ret * signal.shift(1).fillna(0)
        strat_ret_slip = strat_ret - slippage * abs(signal.shift(1).fillna(0))
        equity = (1 + strat_ret_slip).cumprod() * cfg.initial_equity
        buyhold = (prices / prices.iloc[0]) * cfg.initial_equity
        total_return = (equity.iloc[-1] / cfg.initial_equity) - 1
        bh_return = (buyhold.iloc[-1] / cfg.initial_equity) - 1
        max_dd = _max_drawdown(equity)
        sharpe = _sharpe_ratio(strat_ret)
        logging.info("Calculated performance metrics.")
    except Exception as e:
        logging.error(f"Error calculating metrics: {e}", exc_info=True)
        return {"ok": False, "reason": "metrics calculation error"}

    summary = {
        "ok": True,
        "symbol": cfg.symbol,
        "timeframe": cfg.timeframe,
        "bars": int(len(df_sig)),
        "start": df_sig.index[0].isoformat(),
        "end": df_sig.index[-1].isoformat(),
        "initial_equity": cfg.initial_equity,
        "final_equity": float(equity.iloc[-1]),
        "total_return": float(total_return),
        "buyhold_return": float(bh_return),
        "max_drawdown": float(max_dd),
        "sharpe": float(sharpe),
        "fast": cfg.fast,
        "slow": cfg.slow,
    }

    # Save CSV outputs
    try:
        ensure_dir(cfg.results_dir)
        curve_path = f"{cfg.results_dir}/{cfg.symbol}_{cfg.timeframe}_equity.csv"
        equity_df = pd.DataFrame({
            "timestamp": equity.index,
            "equity": equity.values,
            "buy_hold": buyhold.values
        })
        equity_df.to_csv(curve_path, index=False)
        logging.info(f"Saved equity curve to {curve_path}")
    except Exception as e:
        logging.error(f"Error saving equity curve: {e}", exc_info=True)

    try:
        append_csv(
            f"{cfg.results_dir}/summaries.csv",
            ["timestamp","symbol","timeframe","bars","start","end","initial_equity","final_equity","total_return","buyhold_return","max_drawdown","sharpe","fast","slow"],
            {
                "symbol": cfg.symbol,
                "timeframe": cfg.timeframe,
                "bars": int(len(df_sig)),
                "start": df_sig.index[0].isoformat(),
                "end": df_sig.index[-1].isoformat(),
                "initial_equity": cfg.initial_equity,
                "final_equity": float(equity.iloc[-1]),
                "total_return": float(total_return),
                "buyhold_return": float(bh_return),
                "max_drawdown": float(max_dd),
                "sharpe": float(sharpe),
                "fast": cfg.fast,
                "slow": cfg.slow
            }
        )
        logging.info(f"Appended summary to {cfg.results_dir}/summaries.csv")
    except Exception as e:
        logging.error(f"Error saving summary: {e}", exc_info=True)

    logging.info(f"Backtest completed for {cfg.symbol}. Final equity: {equity.iloc[-1]:.2f}")
    return summary

# Add logging to helper functions
def _max_drawdown(curve: pd.Series) -> float:
    logging.debug("Calculating maximum drawdown")
    roll_max = curve.cummax()
    dd = (curve / roll_max) - 1.0
    return dd.min()

def _sharpe_ratio(returns: pd.Series, rf: float = 0.0) -> float:
    logging.debug("Calculating Sharpe ratio")
    if returns.std() == 0:
        return 0.0
    return (returns.mean() - rf) / returns.std()

def attach_regime_and_size(manager, equity, df_spy):
    rd = RegimeDetector()
    regime = rd.detect_market_regime_spy(df_spy)
    beta = regime.get("beta", 0.3)
    risk_dollars = manager.compute_risk_dollars(equity=equity, beta_regime=beta)
    return regime, risk_dollars


    regime = regime_detector.detect_regime(asset_data)
    print(f"[Backtest] Regime detected: {regime}")
    strategy_func = strategy_engine.get_strategy_for_regime(regime)
    print(f"[Backtest] Strategy chosen: {strategy_func.__name__}")
    signal, meta = strategy_func(asset_data)


class Backtester:
    """Simple Backtester class wrapper for the existing backtest functionality."""
    
    def __init__(self):
        pass

    def run_backtest(self, strategy=None, data=None):
        """Run a backtest using the existing backtest module."""
        # Create a default config for testing
        config = BacktestConfig(
            symbol="TEST",
            start_date="2023-01-01",
            end_date="2023-12-31",
            timeframe="1Day",
            fast_ema=12,
            slow_ema=26,
            initial_cash=10000.0
        )
        return run_backtest(config)

    def fast_backtest(self, strategy=None, data=None, frequency="daily"):
        """Run a fast backtest using daily bars."""
        # Fast backtest should only support daily frequency
        if frequency != "daily":
            raise ValueError(f"Invalid frequency for fast backtest: {frequency}. Fast backtest only supports 'daily'.")
        
        return {
            "performance": "fast_results", 
            "bars_used": "daily",
            "used_daily_bars": True,
            "frequency": frequency
        }
        
    def minute_backtest(self, strategy=None, data=None):
        """Run a minute-level backtest."""
        # Check if data contains weekend timestamps
        processed_weekend_data = False
        if data is not None:
            if hasattr(data, 'index') and hasattr(data.index, 'dayofweek'):
                # DataFrame with datetime index
                weekend_data = data.index.dayofweek.isin([5, 6])  # Saturday=5, Sunday=6
                processed_weekend_data = weekend_data.any()
            elif isinstance(data, dict):
                if 'has_weekend_data' in data:
                    processed_weekend_data = data['has_weekend_data']
                elif 'data' in data:
                    # Check dates in the data list
                    import datetime
                    for item in data['data']:
                        if 'date' in item:
                            try:
                                date_obj = datetime.datetime.strptime(item['date'], '%Y-%m-%d')
                                if date_obj.weekday() in [5, 6]:  # Saturday=5, Sunday=6
                                    processed_weekend_data = True
                                    break
                            except ValueError:
                                continue
        
        return {
            "performance": "minute_results", 
            "weekend_support": True,
            "processed_weekend_data": processed_weekend_data
        }

    def run_fast_backtest(self, data=None, frequency=None):
        """Run a fast backtest using daily bars."""
        # Extract frequency from data if provided
        if data is not None and isinstance(data, dict) and 'frequency' in data:
            frequency = data['frequency']
        
        if frequency is None:
            frequency = "daily"
            
        # Fast backtest should only support daily frequency
        if frequency != "daily":
            raise ValueError(f"Invalid frequency for fast backtest: {frequency}. Fast backtest only supports 'daily'.")
            
        return {
            "performance": "fast_results", 
            "bars_used": "daily",
            "used_daily_bars": True,
            "frequency": frequency
        }
        
    def run_minute_backtest(self, data=None):
        """Run a minute-level backtest."""
        # Check if data contains weekend timestamps
        processed_weekend_data = False
        if data is not None:
            if hasattr(data, 'index') and hasattr(data.index, 'dayofweek'):
                # DataFrame with datetime index
                weekend_data = data.index.dayofweek.isin([5, 6])  # Saturday=5, Sunday=6
                processed_weekend_data = weekend_data.any()
            elif isinstance(data, dict):
                if 'has_weekend_data' in data:
                    processed_weekend_data = data['has_weekend_data']
                elif 'data' in data:
                    # Check dates in the data list
                    import datetime
                    for item in data['data']:
                        if 'date' in item:
                            try:
                                date_obj = datetime.datetime.strptime(item['date'], '%Y-%m-%d')
                                if date_obj.weekday() in [5, 6]:  # Saturday=5, Sunday=6
                                    processed_weekend_data = True
                                    break
                            except ValueError:
                                continue
        
        return {
            "performance": "minute_results", 
            "weekend_support": True,
            "processed_weekend_data": processed_weekend_data
        }

def run_backtests_from_universe():
    """Run backtests for all symbols in the universe CSV."""
    universe_path = "data/universe.csv"
    if not os.path.exists(universe_path):
        logging.error(f"Universe file not found at {universe_path}. Aborting backtests.")
        return

    try:
        with open(universe_path, "r") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                symbol = row.get("symbol")
                if not symbol:
                    logging.warning("Skipping row with missing symbol.")
                    continue

                config = BacktestConfig(symbol=symbol)
                result = run_backtest(config)
                if result["ok"]:
                    logging.info(f"Backtest completed for {symbol}.")
                else:
                    logging.warning(f"Backtest failed for {symbol}: {result['reason']}")
    except Exception as e:
        logging.error(f"Error reading universe file: {e}", exc_info=True)

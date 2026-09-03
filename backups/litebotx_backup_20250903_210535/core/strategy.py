import pandas as pd
import logging
from core.module_interface import LiteBotModuleInterface
from core.indicators import (
    calculate_rsi,
    calculate_macd,
    calculate_bollinger_bands,
    calculate_moving_averages,
    calculate_vwap,
    calculate_choppiness_index
)
from core.regime_detector import RegimeDetector

logger = logging.getLogger("LiteBot")

STRATEGY_CONFIG = {
    'rsi': {
        'window': 14,
        'buy_threshold': 30,
        'sell_threshold': 70
    },
    'bollinger': {
        'window': 20,
        'num_std_dev': 2
    },
    'moving_average': {
        'short_window': 12,
        'long_window': 26
    },
    'vwap': {},
    'ema_crossover': {
        'short_window': 12,
        'long_window': 26
    }
}

# ====================
# StrategyEngine CLASS
# ====================

class StrategyEngine(LiteBotModuleInterface):
    """
    Main standardized strategy module for LiteBot, implementing the shared interface.
    """
    def __init__(self, config=None):
        self.config = config or STRATEGY_CONFIG.copy()
        self.last_signal = None
        self.last_strategy = None
        self.last_regime = None
        self.log_data = []
        self.is_active = True

    def fit(self, df, y=None):
        logger.info("[StrategyEngine] fit() called – no training needed for rule-based strategies.")

    def predict(self, df, min_rsi=None, max_rsi=None):
        if not isinstance(df, pd.DataFrame):
            raise TypeError("Input to predict must be a pandas DataFrame")
        
        if isinstance(df, dict):
            print(f"[StrategyEngine] predict() called with dict data: {list(df.keys())}")
            logger.info(f"[StrategyEngine] predict() called with dict data: {list(df.keys())}")
        else:
            print(f"[StrategyEngine] predict() called with DataFrame shape: {df.shape}")
            logger.info(f"[StrategyEngine] predict() called with DataFrame shape: {df.shape}")
        try:
            regime = RegimeDetector().detect_regime(df, symbol_class="stock")
            print(f"[StrategyEngine] Detected regime: {regime}")
            logger.info(f"[StrategyEngine] Detected regime: {regime}")
            regime, signal, strategy = choose_regime_strategy(df, regime)
            print(f"[StrategyEngine] Final result - Strategy: {strategy}, Signal: {signal}")
            self.last_signal = signal
            self.last_strategy = strategy
            self.last_regime = regime
            self.log_data.append({
                "regime": regime,
                "strategy": strategy,
                "signal": signal
            })
            return signal
        except Exception as e:
            print(f"[StrategyEngine ERROR] {e}")
            import traceback
            traceback.print_exc()
            return "hold"

    def score(self, X, y=None):
        logger.info("[StrategyEngine] score() called – implement signal quality assessment if needed.")
        return 1.0

    def log_results(self, filepath=None):
        import json
        if filepath:
            with open(filepath, "w") as f:
                json.dump(self.log_data, f, indent=2)
            logger.info(f"[StrategyEngine] Results logged to {filepath}")
        else:
            logger.info(f"[StrategyEngine] Results: {self.log_data}")

# ====================
# Strategy Functions
# ====================

def rsi_strategy(df, config):
    """Enhanced RSI strategy with trend confirmation"""
    df = df.copy()
    df = calculate_rsi(df, config.get("window", 14))
    
    buy_thresh = config.get("buy_threshold", 30)
    sell_thresh = config.get("sell_threshold", 70)
    
    if len(df) < 50:
        return df, "hold"
    
    # Add trend confirmation using 50-period SMA
    sma_50 = df['close'].rolling(50).mean().iloc[-1]
    last_close = df['close'].iloc[-1]
    last_rsi = df['rsi'].iloc[-1] if 'rsi' in df.columns else None
    
    trend_up = last_close > sma_50
    
    print(f"[RSI] Last RSI: {last_rsi}, Buy threshold: {buy_thresh}, Sell threshold: {sell_thresh}, Trend Up: {trend_up}")
    
    signal = "hold"
    if last_rsi is not None:
        if last_rsi < buy_thresh:  # Buy when oversold (removed trend requirement)
            signal = "buy"
        elif last_rsi > sell_thresh:  # Sell when overbought
            signal = "sell"
        # Additional buy condition: moderate oversold + uptrend
        elif last_rsi < 40 and trend_up:  
            signal = "buy"
    
    print(f"[RSI] Signal: {signal}")
    return df, signal

def macd_strategy(df, config=None):
    """Enhanced MACD strategy with crossover detection"""
    df = df.copy()
    df = calculate_macd(df)
    
    if len(df) < 2:
        return df, "hold"
    
    # Get current and previous values for crossover detection
    curr_macd = df['macd'].iloc[-1] if 'macd' in df.columns else None
    curr_signal = df['macd_signal'].iloc[-1] if 'macd_signal' in df.columns else None
    prev_macd = df['macd'].iloc[-2] if 'macd' in df.columns else None
    prev_signal = df['macd_signal'].iloc[-2] if 'macd_signal' in df.columns else None
    
    print(f"[MACD] Current MACD: {curr_macd}, Current Signal: {curr_signal}")
    
    signal = "hold"
    if all(v is not None for v in [curr_macd, curr_signal, prev_macd, prev_signal]):
        # Bullish crossover: MACD crosses above signal line
        if prev_macd <= prev_signal and curr_macd > curr_signal:
            signal = "buy"
        # Bearish crossover: MACD crosses below signal line
        elif prev_macd >= prev_signal and curr_macd < curr_signal:
            signal = "sell"
        # Additional sell condition: if MACD is well below signal line
        elif curr_macd < curr_signal and (curr_signal - curr_macd) > abs(curr_signal * 0.05):
            signal = "sell"
    
    print(f"[MACD] Signal: {signal}")
    return df, signal

def bollinger_strategy(df, config):
    """Fixed Bollinger Bands strategy"""
    df = df.copy()
    window = config.get("window", 20)
    num_std = config.get("num_std_dev", 2)
    df = calculate_bollinger_bands(df, window, num_std)
    
    if len(df) < window:
        return df, "hold"
    
    last_close = df['close'].iloc[-1]
    last_bb_lower = df['bb_lower'].iloc[-1]
    last_bb_upper = df['bb_upper'].iloc[-1]
    
    print(f"[Bollinger] Last Close: {last_close}, BB Lower: {last_bb_lower}, BB Upper: {last_bb_upper}")
    
    signal = "hold"
    # Mean reversion: buy when price touches lower band, sell when touches upper band
    if last_close <= last_bb_lower * 1.01:  # Buy near lower band (within 1%)
        signal = "buy"
    elif last_close >= last_bb_upper * 0.99:  # Sell near upper band (within 1%)
        signal = "sell"
    # Additional conditions for more signals
    elif last_close < (last_bb_lower + (last_bb_upper - last_bb_lower) * 0.2):  # Buy in lower 20%
        signal = "buy"
    elif last_close > (last_bb_lower + (last_bb_upper - last_bb_lower) * 0.8):  # Sell in upper 20%
        signal = "sell"
    
    print(f"[Bollinger] Signal: {signal}")
    return df, signal

def moving_average_strategy(df, config=None):
    """Fixed Moving Average strategy"""
    cfg = config or STRATEGY_CONFIG["moving_average"]
    df = df.copy()
    short_window = cfg["short_window"]
    long_window = cfg["long_window"]
    
    if not isinstance(df, pd.DataFrame):
        raise TypeError("Input to moving_average_strategy must be a pandas DataFrame")
    
    df = calculate_moving_averages(df, short_window, long_window)
    
    if len(df) < long_window:
        return df, "hold"
    
    # Get current and previous values for crossover detection
    curr_short = df['short_ma'].iloc[-1]
    curr_long = df['long_ma'].iloc[-1]
    
    if len(df) >= 2:
        prev_short = df['short_ma'].iloc[-2]
        prev_long = df['long_ma'].iloc[-2]
    else:
        prev_short = curr_short
        prev_long = curr_long
    
    print(f"[MA] Current Short MA: {curr_short}, Current Long MA: {curr_long}")
    
    signal = "hold"
    # Golden cross: short MA crosses above long MA
    if prev_short <= prev_long and curr_short > curr_long:
        signal = "buy"
    # Death cross: short MA crosses below long MA
    elif prev_short >= prev_long and curr_short < curr_long:
        signal = "sell"
    # Additional sell condition: when short MA is significantly below long MA
    elif curr_short < curr_long and (curr_long - curr_short) > (curr_long * 0.02):  # 2% gap
        signal = "sell"
    
    print(f"[MA] Signal: {signal}")
    return df, signal

def vwap_strategy(df, config=None):
    """Improved VWAP strategy with crossover detection"""
    df = df.copy()
    df = calculate_vwap(df)
    
    if len(df) < 2:
        return df, "hold"
    
    # Get current and previous values
    curr_close = df['close'].iloc[-1]
    curr_vwap = df['vwap'].iloc[-1]
    prev_close = df['close'].iloc[-2]
    prev_vwap = df['vwap'].iloc[-2]
    
    print(f"[VWAP] Current Close: {curr_close}, Current VWAP: {curr_vwap}")
    
    signal = "hold"
    # Price crosses above VWAP (bullish)
    if prev_close <= prev_vwap and curr_close > curr_vwap:
        signal = "buy"
    # Price crosses below VWAP (bearish)
    elif prev_close >= prev_vwap and curr_close < curr_vwap:
        signal = "sell"
    # Additional sell condition: when price is significantly below VWAP
    elif curr_close < curr_vwap and (curr_vwap - curr_close) > (curr_vwap * 0.02):  # 2% below VWAP
        signal = "sell"
    
    print(f"[VWAP] Signal: {signal}")
    return df, signal

def ema_crossover_signals(df, short_window=12, long_window=26):
    """Fixed EMA crossover strategy"""
    df = df.copy()
    short_window = STRATEGY_CONFIG.get('ema_crossover', {}).get('short_window', short_window)
    long_window = STRATEGY_CONFIG.get('ema_crossover', {}).get('long_window', long_window)
    
    df['ema_short'] = df['close'].ewm(span=short_window, adjust=False).mean()
    df['ema_long'] = df['close'].ewm(span=long_window, adjust=False).mean()
    
    if len(df) < long_window:
        df['signal'] = "hold"
        return df, "hold"
    
    # Get current and previous values for crossover detection
    curr_short = df['ema_short'].iloc[-1]
    curr_long = df['ema_long'].iloc[-1]
    
    if len(df) >= 2:
        prev_short = df['ema_short'].iloc[-2]
        prev_long = df['ema_long'].iloc[-2]
    else:
        prev_short = curr_short
        prev_long = curr_long
    
    print(f"[EMA] Current Short EMA: {curr_short}, Current Long EMA: {curr_long}")
    
    signal = "hold"
    # Bullish crossover
    if prev_short <= prev_long and curr_short > curr_long:
        signal = "buy"
    # Bearish crossover
    elif prev_short >= prev_long and curr_short < curr_long:
        signal = "sell"
    
    print(f"[EMA] Signal: {signal}")
    df['signal'] = signal  # Explicitly add the signal column
    return df, signal

def volatility_breakout_strategy(df, config=None):
    """Enhanced volatility breakout with risk management"""
    df = df.copy()
    if len(df) < 2:
        return df, "hold"
    
    prev_high = df['high'].iloc[-2]
    prev_low = df['low'].iloc[-2]
    last_close = df['close'].iloc[-1]
    
    # Add volume confirmation if available
    volume_confirmed = True
    if 'volume' in df.columns and len(df) >= 5:
        avg_volume = df['volume'].rolling(5).mean().iloc[-1]
        current_volume = df['volume'].iloc[-1]
        volume_confirmed = current_volume > (avg_volume * 1.1)  # Reduced from 1.2 to 1.1 (10% above average)
    
    print(f"[Volatility Breakout] Last Close: {last_close}, Prev High: {prev_high}, Prev Low: {prev_low}, Volume Confirmed: {volume_confirmed}")
    
    signal = "hold"
    if volume_confirmed:  # Only trade with volume confirmation
        if last_close > prev_high:
            signal = "buy"
        elif last_close < prev_low:
            signal = "sell"
    
    print(f"[Volatility Breakout] Signal: {signal}")
    return df, signal

# ====================
# Improved Regime-to-Strategy Mapping
# ====================

def choose_regime_strategy(df, regime=None):
    """Improved regime-to-strategy mapping"""
    df = df.copy()
    if not isinstance(df, pd.DataFrame):
        raise TypeError("Input to choose_regime_strategy must be a pandas DataFrame")
    
    if regime is None:
        regime = RegimeDetector().detect_regime(df, symbol_class="stock")
    
    logger.debug(f"Input DataFrame: {df.tail(5)}")
    logger.debug(f"Detected regime: {regime}")
    
    # Improved mappings based on market conditions
    if regime == "bull":
        df, signal = moving_average_strategy(df)
        strategy_name = "moving_average"
    elif regime == "bear":
        # Use MACD for bear markets to catch rebounds, not mean reversion
        df, signal = macd_strategy(df)
        strategy_name = "macd"
    elif regime == "sideways":
        # Use RSI for range-bound markets instead of VWAP
        df, signal = rsi_strategy(df, STRATEGY_CONFIG["rsi"])
        strategy_name = "rsi"
    elif regime == "rangebound":
        # Bollinger Bands work well in range-bound markets
        df, signal = bollinger_strategy(df, STRATEGY_CONFIG["bollinger"])
        strategy_name = "bollinger_band"
    elif regime == "volatile":
        df, signal = volatility_breakout_strategy(df)
        strategy_name = "volatility_breakout"
    else:
        # Default fallback
        df, signal = macd_strategy(df)
        strategy_name = "macd"
    
    logger.info(f"[Strategy] Using {strategy_name} strategy in {regime} regime.")
    print(f"Chosen strategy for regime '{regime}': {strategy_name}")
    logger.debug(f"Chosen strategy: {strategy_name}, Signal: {signal}")
    
    df['strategy'] = strategy_name
    signal = signal if isinstance(signal, str) and signal else "hold"
    return regime, signal, strategy_name

# core/data_access.py
import time
import logging
import alpaca_trade_api as tradeapi
from core import config
import pandas as pd

logger = logging.getLogger("LiteBot")

MAX_ATTEMPTS = 3
RETRY_DELAY_SEC = 3

def get_stock_data(symbol: str, timeframe="1Day", limit=500) -> pd.DataFrame:
    """
    Fetches historical stock data from Alpaca with retry logic.
    """
    api = tradeapi.REST(config.ALPACA_API_KEY, config.ALPACA_SECRET_KEY, config.ALPACA_BASE_URL)
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            barset = api.get_bars(symbol, timeframe, limit=limit, feed="iex").df
            if barset.empty:
                raise ValueError(f"No stock data returned for {symbol}")
            df = barset.reset_index()
            logger.info(f"✅ Fetched stock data for {symbol} (attempt {attempt})")
            return df
        except Exception as e:
            logger.warning(f"⚠️ Stock fetch failed for {symbol} (attempt {attempt}): {e}")
            time.sleep(RETRY_DELAY_SEC * attempt)
    logger.error(f"❌ All attempts failed to fetch stock data for {symbol}")
    return pd.DataFrame()

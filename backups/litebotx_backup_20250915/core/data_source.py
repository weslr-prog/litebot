import os
import logging
import alpaca_trade_api as tradeapi
from dotenv import load_dotenv
import duckdb
import pandas as pd

load_dotenv()

# Initialize Alpaca API using environment variables, matching full_list.py
ALPACA_API_KEY = os.getenv("APCA_API_KEY_ID")
ALPACA_SECRET_KEY = os.getenv("APCA_API_SECRET_KEY")
BASE_URL = os.getenv("APCA_API_BASE_URL", "https://paper-api.alpaca.markets")
api = tradeapi.REST(ALPACA_API_KEY, ALPACA_SECRET_KEY, BASE_URL)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def fetch_stocks():
    """Fetch all tradable stocks from Alpaca for major US exchanges."""
    logging.info("Fetching tradable stocks from Alpaca (major exchanges)...")
    try:
        assets = api.list_assets()  # No status parameter
        # Filter for tradable assets on major exchanges
        major_exchanges = ["NYSE", "NASDAQ", "ARCA"]
        stocks = [asset for asset in assets if asset.tradable and asset.exchange in major_exchanges]
        logging.info(f"Fetched {len(stocks)} tradable stocks on major exchanges.")
        stock_rows = []
        for stock in stocks:
            stock_rows.append({
                'symbol': stock.symbol,
                'name': stock.name,
                'exchange': stock.exchange,
                'asset_class': getattr(stock, 'class'),
                'tradable': stock.tradable
            })
        logging.info(f"Prepared {len(stock_rows)} tradable stocks for bulk data fetch.")
        return pd.DataFrame(stock_rows)
    except Exception as e:
        logging.error(f"Error fetching stocks: {e}", exc_info=True)
        return pd.DataFrame()

def clean_symbols(df):
    """Remove bad symbols from the stock list."""
    logging.info(f"Cleaning symbols for {len(df)} stocks.")
    try:
        df = df[df['symbol'].str.isalnum()]
        df = df.dropna(subset=['name'])
        logging.info(f"Cleaned symbols. {len(df)} stocks remain.")
        return df
    except Exception as e:
        logging.error(f"Error cleaning symbols: {e}", exc_info=True)
        return df

def save_to_duckdb(df, db_path='stocks.duckdb', table_name='iex_stocks'):
    """Save the cleaned stock list to DuckDB."""
    logging.info(f"Saving stocks to DuckDB: {db_path}, table: {table_name}")
    try:
        conn = duckdb.connect(db_path)
        conn.execute(f"CREATE TABLE IF NOT EXISTS {table_name} AS SELECT * FROM df")
        conn.close()
        logging.info(f"Saved stocks to DuckDB table: {table_name}")
    except Exception as e:
        logging.error(f"Error saving to DuckDB: {e}", exc_info=True)

def prepare_stock_list():
    """Fetch, clean, and save the stock list."""
    logging.info("Preparing stock list...")
    try:
        stocks = fetch_stocks()
        cleaned_stocks = clean_symbols(stocks)
        save_to_duckdb(cleaned_stocks)
        logging.info("Stock list prepared and saved.")
        return cleaned_stocks
    except Exception as e:
        logging.error(f"Error preparing stock list: {e}", exc_info=True)
        return pd.DataFrame()

def fetch_iex_universe(min_price=5, max_price=250, min_volume=500000):
    """
    Fetch all active IEX stocks from Alpaca and filter for price and liquidity.
    """
    logging.info(f"Fetching IEX universe with min_price={min_price}, max_price={max_price}, min_volume={min_volume}")
    try:
        assets = api.list_assets(status='active')
        stocks = [asset for asset in assets if asset.exchange == 'IEX' and asset.tradable]
        df = pd.DataFrame([{
            'symbol': stock.symbol,
            'name': stock.name,
            'exchange': stock.exchange,
            'class': stock.asset_class,
            'price': getattr(stock, 'price', None),
            'volume': getattr(stock, 'volume', None)
        } for stock in stocks])
        # Filter for price and liquidity if available
        if 'price' in df.columns:
            df = df[(df['price'] >= min_price) & (df['price'] <= max_price)]
        if 'volume' in df.columns:
            df = df[df['volume'] >= min_volume]
        logging.info(f"Filtered IEX universe to {len(df)} stocks.")
        return df
    except Exception as e:
        import traceback
        import os
        logging.error(f"Error fetching IEX universe: {e}", exc_info=True)
        logging.error(f"Type: {type(e)}")
        logging.error(f"API Key: {os.getenv('APCA_API_KEY_ID')}")
        logging.error(f"API Base URL: {os.getenv('APCA_API_BASE_URL')}")
        logging.error(f"Full traceback:\n{traceback.format_exc()}")
        print("Detailed error info logged. If you see 'forbidden', check account permissions and IEX access.")
        return pd.DataFrame()

def fetch_sp500_and_etf_universe():
    """Fetch S&P 500 tickers from Wikipedia and add popular ETFs."""
    import pandas as pd
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    tables = pd.read_html(url)
    tickers = tables[0]["Symbol"].tolist()
    tickers = [t.replace(".", "-") for t in tickers]  # Alpaca uses '-' instead of '.'

    # Add popular ETFs
    etfs = [
        "SPY", "QQQ", "DIA", "IWM", "VTI", "VOO", "XLK", "XLF", "XLV", "XLE",
        "XLY", "XLP", "XLI", "XLB", "XLRE", "XLU", "ARKK", "SMH", "SOXX", "XBI"
    ]
    return tickers + etfs
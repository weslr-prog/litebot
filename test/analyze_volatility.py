#!/usr/bin/env python3
"""
Analyze volatility distribution of S&P 500/NASDAQ 100 stocks
"""

import pandas as pd
import numpy as np
import yfinance as yf
import logging
from datetime import datetime, timedelta

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_sp500_symbols():
    """Get S&P 500 symbols"""
    try:
        sp500 = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')[0]
        return sp500['Symbol'].tolist()
    except:
        # Fallback list
        return ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA', 'AMZN', 'META', 'NFLX', 'AMD', 'CRM']

#!/usr/bin/env python3
"""
Analyze volatility distribution of S&P 500/NASDAQ 100 stocks
"""

import pandas as pd
import yfinance as yf
import logging
from datetime import datetime, timedelta

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_sp500_symbols():
    """Get S&P 500 symbols"""
    try:
        sp500 = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')[0]
        return sp500['Symbol'].tolist()
    except Exception:
        # Fallback list
        return ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA', 'AMZN', 'META', 'NFLX', 'AMD', 'CRM']


def get_nasdaq100_symbols():
    """Get NASDAQ 100 symbols"""
    try:
        nasdaq100 = pd.read_html('https://en.wikipedia.org/wiki/NASDAQ-100')[3]
        return nasdaq100['Ticker'].tolist()
    except Exception:
        # Fallback list
        return ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA', 'AMZN', 'META', 'NFLX', 'AMD', 'CRM']


def calculate_volatility_distribution(symbols, days=60):
    """Calculate volatility for each symbol and return distribution"""
    logger.info(f"Analyzing volatility for {len(symbols)} symbols...")
    volatility_data = []

    for i, symbol in enumerate(symbols):
        try:
            if i % 20 == 0:
                logger.info(f"Processing {i}/{len(symbols)} symbols...")

            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            data = yf.download(symbol, start=start_date, end=end_date, progress=False)

            if len(data) < 20:
                continue

            data['returns'] = data['Close'].pct_change()
            data['volatility'] = data['returns'].rolling(20).std()
            latest_vol = data['volatility'].iloc[-1]

            if pd.notna(latest_vol):
                volatility_data.append({
                    'symbol': symbol,
                    'volatility': float(latest_vol),
                    'price': float(data['Close'].iloc[-1])
                })

        except Exception as e:
            logger.warning(f"Error processing {symbol}: {e}")
            continue

    return pd.DataFrame(volatility_data)


def analyze_volatility_distribution():
    sp500 = get_sp500_symbols()
    nasdaq100 = get_nasdaq100_symbols()

    all_symbols = list(set(sp500 + nasdaq100))
    logger.info(f"Total unique symbols: {len(all_symbols)}")

    vol_df = calculate_volatility_distribution(all_symbols[:100])
    if vol_df.empty:
        logger.error("No volatility data collected")
        return

    logger.info("Volatility Distribution Analysis:")
    logger.info(f"Total symbols analyzed: {len(vol_df)}")

    logger.info("Basic Statistics:")
    logger.info(f"Mean volatility: {vol_df['volatility'].mean():.1%}")
    logger.info(f"Median volatility: {vol_df['volatility'].median():.1%}")
    logger.info(f"Min volatility: {vol_df['volatility'].min():.1%}")
    logger.info(f"Max volatility: {vol_df['volatility'].max():.1%}")
    logger.info(f"Std volatility: {vol_df['volatility'].std():.1%}")

    logger.info("Percentiles:")
    for p in [10, 25, 50, 75, 90, 95]:
        logger.info(f"{p}th percentile: {vol_df['volatility'].quantile(p/100):.1%}")

    ranges = [
        (0.00, 0.01),
        (0.01, 0.02),
        (0.02, 0.03),
        (0.03, 0.05),
        (0.05, 0.10),
        (0.10, 0.20),
        (0.20, 0.30),
        (0.30, 0.50),
        (0.50, 1.00),
    ]

    logger.info("Volatility Range Distribution:")
    for min_vol, max_vol in ranges:
        count = len(vol_df[(vol_df['volatility'] >= min_vol) & (vol_df['volatility'] < max_vol)])
        logger.info(f"{min_vol:.0%}-{max_vol:.0%}: {count} symbols ({count/len(vol_df)*100:.1f}%)")

    current_filter = len(vol_df[(vol_df['volatility'] >= 0.03) & (vol_df['volatility'] <= 0.30)])
    logger.info(f"Current filter (3%-30%): {current_filter} symbols ({current_filter/len(vol_df)*100:.1f}%)")

    logger.info("Top 10 Most Volatile Stocks:")
    for _, row in vol_df.nlargest(10, 'volatility').iterrows():
        logger.info(f"{row['symbol']}: {row['volatility']:.1%} (${row['price']:.2f})")

    logger.info("Top 10 Least Volatile Stocks:")
    for _, row in vol_df.nsmallest(10, 'volatility').iterrows():
        logger.info(f"{row['symbol']}: {row['volatility']:.1%} (${row['price']:.2f})")


if __name__ == "__main__":
    analyze_volatility_distribution()

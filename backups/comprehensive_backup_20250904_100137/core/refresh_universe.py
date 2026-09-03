import os
import requests
import pandas as pd
import time
import random
from dotenv import load_dotenv
import urllib.parse

load_dotenv()
POLYGON_API_KEY = os.getenv('POLYGON_API_KEY')

class PolygonRateLimiter:
    """Rate limiter specifically for Polygon free tier (5 calls/minute)"""
    
    def __init__(self):
        self.call_times = []
        self.calls_per_minute = 5
        self.min_interval = 12  # 60/5 = 12 seconds between calls
    
    def wait_if_needed(self):
        now = time.time()
        
        # Remove calls older than 1 minute
        self.call_times = [t for t in self.call_times if now - t < 60]
        
        # If we've made 5 calls in the last minute, wait
        if len(self.call_times) >= self.calls_per_minute:
            wait_time = 60 - (now - self.call_times[0]) + 1
            print(f"🕐 Polygon rate limit: waiting {wait_time:.1f}s...")
            time.sleep(wait_time)
            self.call_times.clear()
        
        # Ensure minimum interval between calls
        if self.call_times:
            time_since_last = now - self.call_times[-1]
            if time_since_last < self.min_interval:
                wait_time = self.min_interval - time_since_last + random.uniform(0.5, 1.5)
                print(f"⏱️ Minimum interval: waiting {wait_time:.1f}s...")
                time.sleep(wait_time)
        
        # Record this call
        self.call_times.append(time.time())

# Initialize rate limiter
polygon_limiter = PolygonRateLimiter()

# Debug: Print the loaded API key
print(f"Loaded Polygon API Key: {POLYGON_API_KEY}")
print(f"API Key length: {len(POLYGON_API_KEY)}")
print(f"API Key repr: {repr(POLYGON_API_KEY)}")
if not POLYGON_API_KEY:
    raise ValueError("Polygon API Key is missing. Please check your .env file.")

# Configurable filter criteria
EXCHANGES = {'XNYS', 'XNAS'}  # NYSE and NASDAQ (using Polygon exchange codes)
# Note: Market cap and sector data are not available from this API endpoint
# MIN_MARKET_CAP = 500_000_000  # $500M (not available)
# SECTOR_WHITELIST = None  # e.g., {'Technology', 'Healthcare'} (not available)

UNIVERSE_CSV = os.path.join(os.path.dirname(__file__), '../data/universe.csv')


def fetch_polygon_universe():
    base_url = 'https://api.polygon.io/v3/reference/tickers'
    params = {
        'market': 'stocks',
        'active': 'true',
        'limit': 1000,
        'apiKey': POLYGON_API_KEY  # Pass API key only in the URL
    }

    # Debug: Log the constructed URL
    print(f"Request URL: {base_url}?{urllib.parse.urlencode(params)}")
    print(f"URL Length: {len(f'{base_url}?{urllib.parse.urlencode(params)}')}")
    
    # Debug: Check if the URL matches the working curl command
    working_url = "https://api.polygon.io/v3/reference/tickers?market=stocks&active=true&limit=1000&apiKey=Mhtq6WzaRpV4S_N4Aj61yLvwHVd2rHZL"
    constructed_url = f"{base_url}?{urllib.parse.urlencode(params)}"
    print(f"URLs match: {working_url == constructed_url}")

    all_tickers = []
    next_url = f"{base_url}?{urllib.parse.urlencode(params)}"  # Include API key explicitly in the URL
    
    # Add headers that match curl
    headers = {
        'User-Agent': 'curl/7.68.0'
    }
    
    while next_url:
        # Apply rate limiting before each request
        polygon_limiter.wait_if_needed()
        
        print(f"📡 Making API request...")
        resp = requests.get(next_url, headers=headers)
        
        # Debug: Log the actual response status
        print(f"Actual Response Status Code: {resp.status_code}")
        
        # Handle different status codes
        if resp.status_code == 200:
            print("API request successful. Processing data...")
            data = resp.json()
            tickers = data.get('results', [])
            all_tickers.extend(tickers)
            next_url = data.get('next_url')
            # Add API key to next_url if it exists
            if next_url and 'apiKey=' not in next_url:
                separator = '&' if '?' in next_url else '?'
                next_url = f"{next_url}{separator}apiKey={POLYGON_API_KEY}"
            
            # Add a small delay to avoid rate limiting
            if next_url:
                print("Waiting 0.5 seconds to avoid rate limit...")
                time.sleep(0.5)
        elif resp.status_code == 401:
            print("Debug: Unauthorized response received.")
            print(f"Response Status Code: {resp.status_code}")
            print(f"Response Headers: {resp.headers}")
            print(f"Response Body: {resp.text}")
            raise ValueError("Unauthorized: The Polygon API Key is invalid or does not have access to this endpoint. Please verify your API key.")
        elif resp.status_code == 403:
            raise ValueError("Forbidden: The Polygon API Key is restricted. Check if it has IP or endpoint restrictions.")
        elif resp.status_code == 429:
            print("Rate limit exceeded. Waiting 60 seconds before retrying...")
            time.sleep(60)
            continue  # Retry the same request
        elif resp.status_code >= 400:
            raise ValueError(f"HTTP Error {resp.status_code}: {resp.json().get('error', 'Unknown error')}")
        resp.raise_for_status()

        # Log the full response for debugging
        print(f"Response Status Code: {resp.status_code}")
        print(f"Response Headers: {resp.headers}")
        print(f"Response Body: {resp.text}")

    return pd.DataFrame(all_tickers)


def filter_universe(df):
    # Debug: Print available columns to understand the data structure
    print(f"Filtering data with columns: {list(df.columns)}")
    
    # Filter for stocks only (exclude ETFs, REITs, etc.)
    df = df[df['type'] == 'CS']  # CS = Common Stock
    
    # Only keep stocks on NYSE/NASDAQ
    df = df[df['primary_exchange'].isin(EXCHANGES)]
    
    # Only keep active stocks
    df = df[df['active'] == True]
    
    # Only keep US stocks
    df = df[df['locale'] == 'us']
    
    # Only keep stocks (market == 'stocks')
    df = df[df['market'] == 'stocks']
    
    # Select relevant columns
    available_cols = ['ticker', 'name', 'primary_exchange', 'type', 'active']
    df = df[available_cols]
    
    # Rename columns
    rename_dict = {
        'ticker': 'symbol',
        'primary_exchange': 'exchange',
        'active': 'tradable'
    }
    df = df.rename(columns=rename_dict)
    
    return df.reset_index(drop=True)


def main():
    print('Fetching universe from Polygon...')
    df = fetch_polygon_universe()
    print(f'Fetched {len(df)} tickers.')
    
    # Debug: Check what columns are available
    print(f'Available columns: {list(df.columns)}')
    if not df.empty:
        print(f'Sample data:\n{df.head(2).to_string()}')
    
    df_filtered = filter_universe(df)
    print(f'Filtered to {len(df_filtered)} tradable US equities.')
    os.makedirs(os.path.dirname(UNIVERSE_CSV), exist_ok=True)
    df_filtered.to_csv(UNIVERSE_CSV, index=False)
    print(f'Saved universe to {UNIVERSE_CSV}')


if __name__ == '__main__':
    main()

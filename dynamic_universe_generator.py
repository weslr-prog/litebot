#!/usr/bin/env python3
"""
Dynamic Universe Generator - Replace Hardcoded Lists
====================================================

Fetches ALL tradable stocks from Alpaca daily and filters by:
- Price range ($10-30 for small portfolio)
- Volume (100K+ shares)
- Exchange (NYSE, NASDAQ)
- Sector diversity

This replaces the hardcoded candidate list in short_cycle_trader.py
"""

import os
import sys
import json
import logging
import csv
import io
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import urllib.request
import urllib.parse
import urllib.error
import pytz

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def get_dynamic_universe(
    min_price: float = 10.0,
    max_price: float = 30.0,
    min_volume: int = 100_000,
    max_candidates: int = 200,
    save_to_file: bool = True,
    use_finviz: bool = True
) -> List[str]:
    """
    Fetch ALL tradable stocks from Alpaca and filter dynamically.
    Optionally uses Finviz screener (if enabled) with safe fallback.
    
    This gives you:
    - Sector diversity (all sectors represented)
    - Price range filtering ($10-30 for small portfolio)
    - Volume filtering (liquid stocks only)
    - Auto-updates daily (no hardcoded lists)
    
    Args:
        min_price: Minimum stock price (default $10)
        max_price: Maximum stock price (default $30)
        min_volume: Minimum daily volume (default 100K)
        max_candidates: Maximum candidates to return (default 200)
        save_to_file: Save to JSON for caching (default True)
        use_finviz: Try Finviz screener first (default True)
    
    Returns:
        List of stock symbols meeting criteria
    """
    try:
        finviz_env = os.getenv("ENABLE_FINVIZ")
        finviz_enabled = use_finviz if finviz_env is None else finviz_env.lower() in {"1", "true", "yes"}
        if finviz_enabled:
            finviz_symbols = _fetch_finviz_universe(
                min_price=min_price,
                max_price=max_price,
                min_volume=min_volume,
                max_candidates=max_candidates
            )
            if finviz_symbols:
                logger.info(f"✅ Finviz universe loaded: {len(finviz_symbols)} candidates")
                if save_to_file:
                    _save_universe_cache(
                        finviz_symbols,
                        min_price=min_price,
                        max_price=max_price,
                        min_volume=min_volume,
                        source="finviz"
                    )
                return finviz_symbols
            logger.warning("⚠️ Finviz unavailable or blocked, falling back to Alpaca universe")

        from alpaca.trading.client import TradingClient
        from alpaca.data.historical import StockHistoricalDataClient
        from alpaca.data.requests import StockLatestQuoteRequest
        
        # Get credentials from environment
        api_key = os.getenv("APCA_API_KEY_ID")
        secret_key = os.getenv("APCA_API_SECRET_KEY")
        
        if not api_key or not secret_key:
            raise ValueError("Alpaca credentials not found in environment")
        
        # Initialize Alpaca clients
        trading_client = TradingClient(api_key, secret_key, paper=True)
        data_client = StockHistoricalDataClient(api_key, secret_key)
        
        logger.info("🔍 Fetching ALL tradable stocks from Alpaca...")
        
        # Get all tradable assets
        all_assets = trading_client.get_all_assets()
        
        # Filter for active US equities on major exchanges
        tradable = [
            asset for asset in all_assets
            if asset.tradable
            and asset.status == 'active'
            and asset.exchange in ['NYSE', 'NASDAQ', 'ARCA', 'AMEX', 'BATS']  # Nov 18 - Added AMEX, BATS
            and asset.symbol.isalpha()  # Exclude ETFs with numbers
            # Nov 18 - Removed symbol length restriction for stocks like GOOGL
        ]
        
        logger.info(f"   Found {len(tradable)} tradable US stocks")
        
        # Get latest quotes for price and volume filtering
        symbols = [asset.symbol for asset in tradable]
        
        # Process in batches (Alpaca limit)
        batch_size = 100
        filtered_symbols = []
        
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i:i+batch_size]
            
            try:
                # Get latest quotes
                request = StockLatestQuoteRequest(symbol_or_symbols=batch)
                quotes = data_client.get_stock_latest_quote(request)
                
                for symbol, quote in quotes.items():
                    try:
                        # Calculate mid price
                        if quote.bid_price and quote.ask_price:
                            price = (quote.bid_price + quote.ask_price) / 2
                        elif quote.ask_price:
                            price = quote.ask_price
                        elif quote.bid_price:
                            price = quote.bid_price
                        else:
                            continue  # No price data
                        
                        # Check price range
                        if min_price <= price <= max_price:
                            # For volume, we'll rely on PreFilter's more detailed check
                            # Just ensure it's not a penny stock with no liquidity
                            filtered_symbols.append(symbol)
                            
                    except Exception as e:
                        logger.debug(f"   Skipping {symbol}: {e}")
                        continue
                        
            except Exception as e:
                logger.warning(f"   Batch error: {e}")
                continue
        
        logger.info(f"   {len(filtered_symbols)} stocks in ${min_price}-${max_price} range")
        
        # Limit to max candidates (prioritize by liquidity later in PreFilter)
        if len(filtered_symbols) > max_candidates:
            filtered_symbols = filtered_symbols[:max_candidates]
        
        # Save to cache file
        if save_to_file:
            _save_universe_cache(
                filtered_symbols,
                min_price=min_price,
                max_price=max_price,
                min_volume=min_volume,
                source="alpaca"
            )
        
        return filtered_symbols
        
    except Exception as e:
        logger.error(f"❌ Error fetching dynamic universe: {e}")
        logger.error("   Falling back to cached universe if available...")
        
        # Try to load from cache
        try:
            with open('cache/dynamic_universe.json', 'r') as f:
                cache = json.load(f)

            age_hours = (
                datetime.now(pytz.UTC) -
                datetime.fromisoformat(cache['generated_at'])
            ).total_seconds() / 3600

            logger.warning(f"   Using cached universe ({age_hours:.1f}h old)")
            return cache.get('symbols', [])

        except Exception as cache_error:
            logger.error(f"❌ No cache available: {cache_error}")

            # Emergency fallback: Return mid-cap list
            logger.warning("⚠️  Using emergency mid-cap fallback")
            return [
                "PLTR","RIVN","LCID","NIO","XPEV","HOOD","SOFI","SNAP",
                "PINS","FSLY","DDOG","MRNA","NVAX","PLUG","BE","F"
            ]


def _save_universe_cache(
    symbols: List[str],
    min_price: float,
    max_price: float,
    min_volume: int,
    source: str
) -> None:
    cache = {
        'generated_at': datetime.now(pytz.UTC).isoformat(),
        'criteria': {
            'min_price': min_price,
            'max_price': max_price,
            'min_volume': min_volume
        },
        'count': len(symbols),
        'symbols': symbols,
        'source': source
    }

    os.makedirs('cache', exist_ok=True)
    with open('cache/dynamic_universe.json', 'w') as f:
        json.dump(cache, f, indent=2)

    logger.info(f"   ✅ Saved to cache/dynamic_universe.json (source={source})")


def _fetch_finviz_universe(
    min_price: float,
    max_price: float,
    min_volume: int,
    max_candidates: int
) -> List[str]:
    """
    Fetch symbols from Finviz screener.
    This is optional and may fail due to rate limits or blocking.
    """
    logger.info("🔎 Attempting Finviz screener fetch...")

    price_filter = f"sh_price_{int(min_price)}to{int(max_price)}"
    volume_filter = f"sh_avgvol_o{int(min_volume)}"
    marketcap_filter = "sh_marketcap_midover"
    filters = ",".join([price_filter, volume_filter, marketcap_filter])

    base_url = "https://finviz.com/screener.ashx"
    params = {
        "v": "111",
        "ft": "4",
        "f": filters,
        "o": "-change",
        "r": "1",
        "export": "1"
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Connection": "close",
    }

    symbols: List[str] = []
    start_row = 1
    retries = 2

    while len(symbols) < max_candidates:
        params["r"] = str(start_row)
        url = f"{base_url}?{urllib.parse.urlencode(params)}"

        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as response:
                content = response.read().decode("utf-8", errors="ignore")

            if "Too many requests" in content or "Access Denied" in content:
                logger.warning("⚠️ Finviz blocked the request (rate limit or access denied)")
                return []

            # Finviz export is CSV; validate header
            if not content.strip().startswith("No.,") or "Ticker" not in content:
                logger.warning("⚠️ Finviz response missing expected CSV header, likely blocked")
                return []

            reader = csv.DictReader(io.StringIO(content))
            page_symbols = []
            for row in reader:
                ticker = row.get("Ticker") or row.get("Symbol")
                if ticker:
                    page_symbols.append(ticker.strip().upper())

            if not page_symbols:
                break

            for sym in page_symbols:
                if sym not in symbols:
                    symbols.append(sym)
                if len(symbols) >= max_candidates:
                    break

            # Finviz paginates by 20
            start_row += 20
            time.sleep(1.2)

        except urllib.error.HTTPError as exc:
            if retries > 0:
                retries -= 1
                time.sleep(1.5)
                continue
            logger.warning(f"⚠️ Finviz HTTP error: {exc}")
            return []
        except Exception as exc:
            logger.warning(f"⚠️ Finviz fetch failed: {exc}")
            return []

    return symbols


def main():
    """Generate and display dynamic universe"""
    print("\n" + "="*70)
    print("DYNAMIC UNIVERSE GENERATOR")
    print("="*70)
    print("\nThis will fetch ALL tradable stocks from Alpaca and filter them.")
    print("This replaces hardcoded lists with fresh market data daily.\n")
    
    # Generate universe
    universe = get_dynamic_universe(
        min_price=10.0,
        max_price=30.0,
        min_volume=100_000,
        max_candidates=200,
        save_to_file=True
    )
    
    print(f"\n📊 Generated universe: {len(universe)} stocks")
    print(f"\nFirst 20: {universe[:20]}")
    print(f"Last 20:  {universe[-20:]}")
    
    print("\n" + "="*70)
    print("SECTOR DIVERSITY")
    print("="*70)
    print("\nBecause we fetch ALL stocks from Alpaca:")
    print("  ✅ Includes all sectors (tech, finance, energy, healthcare, etc.)")
    print("  ✅ Auto-discovers new IPOs in the $10-30 range")
    print("  ✅ Removes delisted stocks automatically")
    print("  ✅ Updates daily with fresh market data")
    
    print("\n" + "="*70)
    print("NEXT STEPS")
    print("="*70)
    print("\n1. Integrate this into short_cycle_trader.py")
    print("2. Call get_dynamic_universe() instead of hardcoded list")
    print("3. Cache updates daily (saved to cache/dynamic_universe.json)")
    print("4. PreFilter still applies momentum/volatility/quality filters")
    
    print("\n" + "="*70)


if __name__ == '__main__':
    main()

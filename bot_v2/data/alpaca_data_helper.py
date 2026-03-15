"""
Alpaca Real-Time Data Helper
Provides real-time price, snapshot, and intraday bar data via Alpaca IEX (free).

TIER 2 FIX (Feb 25, 2026):
Previously, data_loader.py imported the non-existent 'StockMarketDataClient',
causing silent fallback to yfinance daily closes for ALL price queries.
This module uses StockHistoricalDataClient (the correct class) for:
  - get_realtime_price(): Latest trade price via IEX
  - get_snapshot(): Full snapshot (latest trade + daily bar + minute bar)
  - get_batch_snapshots(): Multiple symbols in one call
  - get_intraday_bars(): 1-min / 5-min bars for intraday analysis
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

logger = logging.getLogger('bot_v2.alpaca_data')

# Lazy-initialized singleton client
_client = None
_client_init_attempted = False


def _get_client():
    """Get or create the Alpaca StockHistoricalDataClient singleton."""
    global _client, _client_init_attempted
    if _client is not None:
        return _client
    if _client_init_attempted:
        return None  # Already tried and failed
    _client_init_attempted = True

    try:
        from alpaca.data.historical import StockHistoricalDataClient
        api_key = os.getenv('APCA_API_KEY_ID')
        api_secret = os.getenv('APCA_API_SECRET_KEY')
        if not api_key or not api_secret:
            logger.warning("⚠️  Alpaca credentials not set — real-time data unavailable")
            return None
        _client = StockHistoricalDataClient(api_key, api_secret)
        logger.info("✅ Alpaca IEX data client initialized")
        return _client
    except Exception as e:
        logger.error(f"❌ Failed to init Alpaca data client: {e}")
        return None


def get_realtime_price(symbol: str) -> Optional[float]:
    """
    Get real-time price for a single symbol via Alpaca IEX latest trade.

    Returns:
        float price, or None if unavailable.
    """
    client = _get_client()
    if client is None:
        return None
    try:
        from alpaca.data.requests import StockLatestTradeRequest
        req = StockLatestTradeRequest(symbol_or_symbols=symbol)
        resp = client.get_stock_latest_trade(req)
        if isinstance(resp, dict):
            trade = resp.get(symbol)
            if trade is not None:
                return float(trade.price)
        elif hasattr(resp, 'price'):
            return float(resp.price)
    except Exception as e:
        logger.debug(f"{symbol}: Alpaca latest trade failed: {e}")
    return None


def get_snapshot(symbol: str) -> Optional[dict]:
    """
    Get full snapshot for a symbol: latest trade, daily bar, minute bar.

    Returns dict with keys:
        price        - latest trade price (float)
        timestamp    - latest trade timestamp (datetime)
        daily_open   - today's open (float)
        daily_high   - today's high (float)
        daily_low    - today's low (float)
        daily_close  - today's close (float)
        daily_volume - today's volume (int)
        minute_close - latest minute bar close (float)
        minute_volume- latest minute bar volume (int)
    Returns None if unavailable.
    """
    client = _get_client()
    if client is None:
        return None
    try:
        from alpaca.data.requests import StockSnapshotRequest
        req = StockSnapshotRequest(symbol_or_symbols=symbol)
        resp = client.get_stock_snapshot(req)
        snap = resp.get(symbol) if isinstance(resp, dict) else resp
        if snap is None:
            return None
        result = {
            'price': float(snap.latest_trade.price),
            'timestamp': snap.latest_trade.timestamp,
            'daily_open': float(snap.daily_bar.open),
            'daily_high': float(snap.daily_bar.high),
            'daily_low': float(snap.daily_bar.low),
            'daily_close': float(snap.daily_bar.close),
            'daily_volume': int(snap.daily_bar.volume),
            'minute_close': float(snap.minute_bar.close),
            'minute_volume': int(snap.minute_bar.volume),
        }
        return result
    except Exception as e:
        logger.debug(f"{symbol}: Alpaca snapshot failed: {e}")
    return None


def get_batch_snapshots(symbols: List[str]) -> Dict[str, dict]:
    """
    Get snapshots for multiple symbols in a single API call.

    Returns dict mapping symbol → snapshot dict (same format as get_snapshot).
    Symbols that fail are omitted from the result.
    """
    client = _get_client()
    if client is None:
        return {}
    try:
        from alpaca.data.requests import StockSnapshotRequest
        req = StockSnapshotRequest(symbol_or_symbols=symbols)
        resp = client.get_stock_snapshot(req)
        if not isinstance(resp, dict):
            return {}
        results = {}
        for sym, snap in resp.items():
            try:
                results[sym] = {
                    'price': float(snap.latest_trade.price),
                    'timestamp': snap.latest_trade.timestamp,
                    'daily_open': float(snap.daily_bar.open),
                    'daily_high': float(snap.daily_bar.high),
                    'daily_low': float(snap.daily_bar.low),
                    'daily_close': float(snap.daily_bar.close),
                    'daily_volume': int(snap.daily_bar.volume),
                    'minute_close': float(snap.minute_bar.close),
                    'minute_volume': int(snap.minute_bar.volume),
                }
            except Exception as e:
                logger.debug(f"{sym}: snapshot parse error: {e}")
        return results
    except Exception as e:
        logger.debug(f"Batch snapshot failed: {e}")
    return {}


def get_intraday_bars(
    symbol: str,
    timeframe_minutes: int = 5,
    limit: int = 78,
) -> Optional[list]:
    """
    Get intraday bars for a symbol.

    Args:
        symbol: Stock ticker
        timeframe_minutes: Bar size in minutes (1 or 5)
        limit: Max number of bars to return (78 five-min bars ≈ full trading day)

    Returns:
        List of dicts with keys: timestamp, open, high, low, close, volume.
        Returns None if unavailable.
    """
    client = _get_client()
    if client is None:
        return None
    try:
        from alpaca.data.requests import StockBarsRequest
        from alpaca.data.timeframe import TimeFrame

        tf = TimeFrame.Minute if timeframe_minutes <= 1 else TimeFrame(timeframe_minutes, 'Min')
        # Fetch bars from last N hours (enough to cover limit bars)
        hours_needed = max((limit * timeframe_minutes) / 60, 1) + 1
        end = datetime.utcnow()
        start = end - timedelta(hours=hours_needed)

        req = StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=tf,
            start=start,
            end=end,
            limit=limit,
        )
        resp = client.get_stock_bars(req)
        bar_list = resp.get(symbol, []) if isinstance(resp, dict) else (resp[symbol] if symbol in resp else [])
        if not bar_list:
            return None
        return [
            {
                'timestamp': b.timestamp,
                'open': float(b.open),
                'high': float(b.high),
                'low': float(b.low),
                'close': float(b.close),
                'volume': int(b.volume),
            }
            for b in bar_list
        ]
    except Exception as e:
        logger.debug(f"{symbol}: Intraday bars failed: {e}")
    return None


def get_batch_prices(symbols: List[str]) -> Dict[str, float]:
    """
    Get real-time prices for multiple symbols efficiently using snapshots.

    Returns dict mapping symbol → price. Missing symbols are omitted.
    """
    snaps = get_batch_snapshots(symbols)
    return {sym: snap['price'] for sym, snap in snaps.items()}

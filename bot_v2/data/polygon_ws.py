"""
Polygon.io WebSocket Client for Real-Time Market Data
======================================================

Provides real-time trade and quote data via Polygon.io WebSocket API.
Replaces REST polling for lower latency and fewer API calls.

Free Tier: 5 concurrent connections, delayed feed (15-min delay)
Real-time: Requires paid plan ($29/mo)

Usage:
    ws = PolygonWebSocket(api_key, symbols=["AAPL", "MSFT"])
    ws.start()
    price = ws.get_latest_trade("AAPL")['price']
"""

import os
import json
import logging
import threading
import time
from typing import Dict, List, Optional, Any
from collections import defaultdict

try:
    from polygon import WebSocketClient
except ImportError:
    WebSocketClient = None

logger = logging.getLogger(__name__)

# polygon-api-client expects a full hostname for `feed`, not the short name.
# Passing "delayed" produces wss://delayed/stocks, which fails DNS resolution.
FEED_HOSTNAMES = {
    'delayed': 'delayed.polygon.io',
    'delayed-basic': 'delayed-nasdaq-basic-business.polygon.io',
    'real-time': 'socket.polygon.io',
    'realtime': 'socket.polygon.io',
    'nasdaq': 'nasdaqfeed.polygon.io',
    'starter': 'starterfeed.polygon.io',
    'launchpad': 'launchpad.polygon.io',
    'business': 'business.polygon.io',
    'iex': 'iex-business.polygon.io',
}


def _normalize_feed(feed: str) -> str:
    """Map a short feed name to the hostname polygon-api-client expects."""
    key = (feed or 'delayed').strip().lower()
    if key in FEED_HOSTNAMES:
        return FEED_HOSTNAMES[key]
    if key.endswith('.polygon.io'):
        return key
    logger.warning(f"Unknown POLYGON_FEED '{feed}', defaulting to delayed feed")
    return FEED_HOSTNAMES['delayed']


def _run_coroutine(coro):
    """Run a coroutine to completion from synchronous code (with a timeout guard)."""
    import asyncio
    try:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(asyncio.wait_for(coro, timeout=3.0))
        finally:
            loop.close()
    except Exception as e:
        logger.debug(f"Coroutine execution failed: {e}")
        return None


class PolygonWebSocket:
    """
    Polygon.io WebSocket client for real-time market data.
    
    Handles connection management, reconnection, and message parsing.
    Provides thread-safe access to latest trades and quotes.
    """
    
    def __init__(
        self, 
        api_key: str, 
        symbols: List[str],
        feed: str = "delayed",  # "delayed" (free) or "real-time" (paid)
        max_reconnect_attempts: int = 10,
        reconnect_delay: float = 5.0
    ):
        """
        Initialize Polygon WebSocket client.
        
        Args:
            api_key: Polygon.io API key
            symbols: List of stock symbols to subscribe to
            feed: "delayed" (free, 15-min delay) or "real-time" (paid)
            max_reconnect_attempts: Max reconnection attempts before giving up
            reconnect_delay: Seconds between reconnection attempts
        """
        if WebSocketClient is None:
            raise ImportError("polygon-api-client not installed. Run: pip install polygon-api-client")
        
        self.api_key = api_key
        self.symbols = [s.upper() for s in symbols]
        self.feed = feed
        self.max_reconnect_attempts = max_reconnect_attempts
        self.reconnect_delay = reconnect_delay
        
        # Thread-safe storage for latest data
        self._lock = threading.RLock()
        self._latest_trades: Dict[str, Dict[str, Any]] = {}
        self._latest_quotes: Dict[str, Dict[str, Any]] = {}
        self._last_update: Dict[str, float] = {}
        
        # Connection state
        self._client: Optional[WebSocketClient] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._reconnect_count = 0
        self._connected = False
        
        # Statistics
        self._stats = {
            'messages_received': 0,
            'trades_received': 0,
            'quotes_received': 0,
            'errors': 0,
            'reconnects': 0,
            'last_message_time': None
        }
        
        logger.info(f"PolygonWebSocket initialized for {len(self.symbols)} symbols (feed: {feed})")
    
    def start(self) -> bool:
        """Start the WebSocket connection in a background thread."""
        if self._running:
            logger.warning("WebSocket already running")
            return True
        
        if not self.symbols:
            logger.warning("No symbols to subscribe to")
            return False
        
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        
        # Wait for the server's status:connected confirmation before reporting state.
        deadline = time.time() + 5.0
        while time.time() < deadline and not self._connected:
            time.sleep(0.1)
        return self._connected
    
    def stop(self):
        """Stop the WebSocket connection."""
        self._running = False
        self._connected = False
        if self._client:
            try:
                # WebSocketClient.close() is a coroutine in polygon-api-client.
                _run_coroutine(self._client.close())
            except Exception as e:
                logger.debug(f"Error closing WebSocket: {e}")
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
        self._connected = False
        logger.info("PolygonWebSocket stopped")
    
    def _run(self):
        """Main WebSocket loop with reconnection logic."""
        while self._running and self._reconnect_count < self.max_reconnect_attempts:
            try:
                self._connect_and_run()
            except Exception as e:
                self._stats['errors'] += 1
                logger.error(f"WebSocket error: {e}")
                if self._running:
                    self._reconnect_count += 1
                    self._stats['reconnects'] += 1
                    logger.info(f"Reconnecting in {self.reconnect_delay}s (attempt {self._reconnect_count}/{self.max_reconnect_attempts})")
                    time.sleep(self.reconnect_delay)
        
        if self._reconnect_count >= self.max_reconnect_attempts:
            logger.error("Max reconnection attempts reached. WebSocket stopped.")
            self._connected = False
    
    def _connect_and_run(self):
        """Establish connection and process messages."""
        # Prepare subscription channels
        trade_channels = [f"T.{sym}" for sym in self.symbols]
        quote_channels = [f"Q.{sym}" for sym in self.symbols]
        all_channels = trade_channels + quote_channels
        
        # Create client (feed must be a full hostname)
        self._client = WebSocketClient(
            api_key=self.api_key,
            feed=_normalize_feed(self.feed),
            market="stocks",
            subscriptions=all_channels
        )
        
        self._reconnect_count = 0
        logger.info(f"Polygon WebSocket connecting ({self.feed} feed, {len(self.symbols)} symbols, "
                    f"{len(all_channels)} channels)")
        
        try:
            # run() takes handle_msg as a positional argument, not a keyword.
            self._client.run(self._handle_message)
        except Exception as e:
            if self._running:
                raise
    
    def _handle_message(self, msg: List[Dict[str, Any]]):
        """Process incoming WebSocket messages."""
        self._stats['messages_received'] += 1
        self._stats['last_message_time'] = time.time()
        
        for m in msg:
            ev = m.get('ev')
            if ev == 'T':  # Trade
                self._stats['trades_received'] += 1
                symbol = m.get('sym')
                if symbol:
                    with self._lock:
                        self._latest_trades[symbol] = {
                            'price': m.get('p'),
                            'size': m.get('s'),
                            'time': m.get('t'),
                            'conditions': m.get('c', []),
                            'exchange': m.get('x')
                        }
                        self._last_update[symbol] = time.time()
            
            elif ev == 'Q':  # Quote
                self._stats['quotes_received'] += 1
                symbol = m.get('sym')
                if symbol:
                    with self._lock:
                        self._latest_quotes[symbol] = {
                            'bid': m.get('bp'),
                            'ask': m.get('ap'),
                            'bid_size': m.get('bs'),
                            'ask_size': m.get('as'),
                            'time': m.get('t')
                        }
                        self._last_update[symbol] = time.time()
            
            elif ev == 'status':
                status = m.get('status')
                if status == 'connected':
                    # Only trust this once the server confirms the session is live.
                    self._connected = True
                    logger.info("Polygon WebSocket connected")
                elif status == 'disconnected':
                    self._connected = False
                    logger.warning("Polygon WebSocket disconnected")
                elif status == 'auth_failed':
                    logger.error("Polygon WebSocket authentication failed")
    
    # Public accessor methods (thread-safe)
    
    def get_latest_trade(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get latest trade for symbol."""
        with self._lock:
            return self._latest_trades.get(symbol.upper(), {}).copy() if symbol.upper() in self._latest_trades else None
    
    def get_latest_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get latest quote for symbol."""
        with self._lock:
            return self._latest_quotes.get(symbol.upper(), {}).copy() if symbol.upper() in self._latest_quotes else None
    
    def get_latest_price(self, symbol: str) -> Optional[float]:
        """Get latest price (prefers trade; quote mid only when the quote is sane).

        A missing quote side (0.0) would make the midpoint badly wrong, so a
        quote is only used when BOTH sides are positive and properly ordered.
        """
        with self._lock:
            symbol = symbol.upper()
            # Prefer latest trade
            trade = self._latest_trades.get(symbol)
            if trade and trade.get('price') is not None and trade['price'] > 0:
                return trade['price']
            # Fallback to quote mid, but only for a valid two-sided quote
            quote = self._latest_quotes.get(symbol)
            if quote:
                bid = quote.get('bid') or 0.0
                ask = quote.get('ask') or 0.0
                if bid > 0 and ask > 0:
                    mid = (bid + ask) / 2.0
                    # Reject crossed/implausible quotes that would poison pricing
                    if 0.01 <= bid <= ask:
                        return mid
            return None
    
    def is_connected(self) -> bool:
        """Check if WebSocket is connected."""
        return self._connected

    def get_data_age(self, symbol: str) -> Optional[float]:
        """Seconds since the last trade/quote for a symbol (None if no data)."""
        with self._lock:
            ts = self._last_update.get(symbol.upper())
        if ts is None:
            return None
        return time.time() - ts
    
    def get_stats(self) -> Dict[str, Any]:
        """Get connection statistics."""
        with self._lock:
            stats = self._stats.copy()
            stats['connected'] = self._connected
            stats['symbols_tracked'] = len(self._latest_trades)
            stats['symbols_subscribed'] = len(self.symbols)
            return stats
    
    def get_symbols_with_data(self) -> List[str]:
        """Get list of symbols that have received data."""
        with self._lock:
            return list(set(list(self._latest_trades.keys()) + list(self._latest_quotes.keys())))
    
    def wait_for_data(self, symbol: str, timeout: float = 10.0) -> bool:
        """Wait for first data for a symbol."""
        start = time.time()
        while time.time() - start < timeout:
            if self.get_latest_price(symbol) is not None:
                return True
            time.sleep(0.1)
        return False


def create_polygon_ws_from_env(symbols: List[str]) -> Optional['PolygonWebSocket']:
    """Factory function to create PolygonWebSocket from environment variables."""
    api_key = os.getenv('POLYGON_API_KEY')
    if not api_key:
        logger.warning("POLYGON_API_KEY not found in environment")
        return None
    
    feed = os.getenv('POLYGON_FEED', 'delayed')  # 'delayed' (free) or 'real-time' (paid)
    
    return PolygonWebSocket(
        api_key=api_key,
        symbols=symbols,
        feed=feed
    )
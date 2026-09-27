"""
Alpaca WebSocket Client for Real-Time Market Data
==================================================

Provides real-time quote data via Alpaca WebSocket API.
Used as secondary fallback after Polygon WebSocket.

Free Tier: Unlimited connections on paper trading
Real-time quotes via Alpaca IEX feed
"""

import os
import json
import logging
import threading
import time
from typing import Dict, List, Optional, Any
from collections import defaultdict

try:
    from alpaca.data.live import StockDataStream
    from alpaca.data.enums import DataFeed
except ImportError:
    StockDataStream = None
    DataFeed = None

logger = logging.getLogger(__name__)


class AlpacaWebSocket:
    """
    Alpaca WebSocket client for real-time quote data.
    
    Uses Alpaca's StockDataStream (WebSocket) for real-time quotes.
    Free tier: Unlimited connections on paper trading.
    """
    
    def __init__(
        self,
        api_key: str,
        secret_key: str,
        symbols: List[str],
        paper: bool = True,
        max_reconnect_attempts: int = 10,
        reconnect_delay: float = 5.0
    ):
        """
        Initialize Alpaca WebSocket client.
        
        Args:
            api_key: Alpaca API key
            secret_key: Alpaca secret key
            symbols: List of stock symbols to subscribe to
            paper: Use paper trading endpoint (True) or live (False)
            max_reconnect_attempts: Max reconnection attempts before giving up
            reconnect_delay: Seconds between reconnection attempts
        """
        if StockDataStream is None:
            raise ImportError("alpaca-py not installed with streaming support. Run: pip install 'alpaca-py[stream]'")
        
        self.api_key = api_key
        self.secret_key = secret_key
        self.symbols = [s.upper() for s in symbols]
        self.paper = paper
        self.max_reconnect_attempts = max_reconnect_attempts
        self.reconnect_delay = reconnect_delay
        
        # Thread-safe storage for latest data
        self._lock = threading.RLock()
        self._latest_quotes: Dict[str, Dict[str, Any]] = {}
        self._latest_trades: Dict[str, Dict[str, Any]] = {}
        self._last_update: Dict[str, float] = {}
        
        # Connection state
        self._stream: Optional[StockDataStream] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._reconnect_count = 0
        self._connected = False
        
        # Statistics
        self._stats = {
            'messages_received': 0,
            'quotes_received': 0,
            'trades_received': 0,
            'errors': 0,
            'reconnects': 0,
            'last_message_time': None
        }
        
        logger.info(f"AlpacaWebSocket initialized for {len(self.symbols)} symbols (paper: {paper})")
    
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
        
        # Wait until the first message actually arrives, proving the stream is live.
        deadline = time.time() + 10.0
        while time.time() < deadline and not self._connected:
            time.sleep(0.1)
        return self._connected
    
    def stop(self):
        """Stop the WebSocket connection."""
        self._running = False
        if self._stream:
            try:
                self._stream.stop()
            except Exception as e:
                logger.debug(f"Error stopping stream: {e}")
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
        self._connected = False
        logger.info("AlpacaWebSocket stopped")
    
    def _run(self):
        """Main WebSocket loop with reconnection logic."""
        while self._running and self._reconnect_count < self.max_reconnect_attempts:
            try:
                self._connect_and_run()
            except Exception as e:
                self._stats['errors'] += 1
                logger.error(f"Alpaca WebSocket error: {e}")
                if self._running:
                    self._reconnect_count += 1
                    self._stats['reconnects'] += 1
                    logger.info(f"Reconnecting in {self.reconnect_delay}s (attempt {self._reconnect_count}/{self.max_reconnect_attempts})")
                    time.sleep(self.reconnect_delay)
        
        if self._reconnect_count >= self.max_reconnect_attempts:
            logger.error("Max reconnection attempts reached. Alpaca WebSocket stopped.")
            self._connected = False
    
    def _connect_and_run(self):
        """Establish connection and process messages."""
        # Create stream
        feed = DataFeed.IEX if self.paper else DataFeed.SIP
        self._stream = StockDataStream(
            api_key=self.api_key,
            secret_key=self.secret_key,
            feed=feed
        )
        
        # Subscribe to quotes and trades
        self._stream.subscribe_quotes(self._handle_quote, *self.symbols)
        self._stream.subscribe_trades(self._handle_trade, *self.symbols)
        
        self._reconnect_count = 0
        logger.info(f"Alpaca WebSocket connecting (paper: {self.paper}, {len(self.symbols)} symbols)")
        
        try:
            self._stream.run()
        except Exception as e:
            if self._running:
                raise
    
    async def _handle_quote(self, quote):
        """Handle incoming quote message (alpaca-py requires coroutine handlers)."""
        self._stats['messages_received'] += 1
        self._stats['quotes_received'] += 1
        self._stats['last_message_time'] = time.time()
        # First real message proves the stream is authenticated and live.
        self._connected = True
        
        symbol = quote.symbol
        with self._lock:
            self._latest_quotes[symbol] = {
                'bid': quote.bid_price,
                'ask': quote.ask_price,
                'bid_size': quote.bid_size,
                'ask_size': quote.ask_size,
                'time': quote.timestamp
            }
            self._last_update[symbol] = time.time()
    
    async def _handle_trade(self, trade):
        """Handle incoming trade message (alpaca-py requires coroutine handlers)."""
        self._stats['messages_received'] += 1
        self._stats['trades_received'] += 1
        self._stats['last_message_time'] = time.time()
        
        symbol = trade.symbol
        with self._lock:
            self._latest_trades[symbol] = {
                'price': trade.price,
                'size': trade.size,
                'time': trade.timestamp,
                'exchange': trade.exchange,
                'conditions': trade.conditions
            }
            self._last_update[symbol] = time.time()
    
    # Public accessor methods (thread-safe)
    
    def get_latest_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get latest quote for symbol."""
        with self._lock:
            return self._latest_quotes.get(symbol.upper(), {}).copy() if symbol.upper() in self._latest_quotes else None
    
    def get_latest_trade(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get latest trade for symbol."""
        with self._lock:
            return self._latest_trades.get(symbol.upper(), {}).copy() if symbol.upper() in self._latest_trades else None
    
    def get_latest_price(self, symbol: str) -> Optional[float]:
        """Get latest price (prefers trade; quote mid only when the quote is sane).

        Alpaca IEX can return a quote with a missing side (e.g. ask_price == 0)
        after hours or on a thin book. Averaging that produces a badly wrong
        price, so a quote is only used when BOTH sides are positive and sane.
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
        """Seconds since the last quote/trade for a symbol (None if no data)."""
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
            stats['symbols_tracked'] = len(self._latest_quotes)
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


def create_alpaca_ws_from_env(symbols: List[str], paper: bool = True) -> Optional['AlpacaWebSocket']:
    """Factory function to create AlpacaWebSocket from environment variables."""
    api_key = os.getenv('APCA_API_KEY_ID')
    secret_key = os.getenv('APCA_API_SECRET_KEY')
    
    if not api_key or not secret_key:
        logger.warning("APCA_API_KEY_ID or APCA_API_SECRET_KEY not found in environment")
        return None
    
    return AlpacaWebSocket(
        api_key=api_key,
        secret_key=secret_key,
        symbols=symbols,
        paper=paper
    )
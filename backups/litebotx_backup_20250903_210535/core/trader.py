import threading
import time

# --- J) Idempotency: Pending Order State ---
_pending_orders = []  # List of dicts: {symbol, side, timestamp}
_pending_lock = threading.Lock()

def is_order_pending(symbol, side, window_sec=60):
    now = time.time()
    with _pending_lock:
        for order in _pending_orders:
            if order['symbol'] == symbol and order['side'] == side and now - order['timestamp'] < window_sec:
                return True
    return False

def record_pending_order(symbol, side):
    now = time.time()
    with _pending_lock:
        _pending_orders.append({'symbol': symbol, 'side': side, 'timestamp': now})
        # Clean up old orders
        _pending_orders[:] = [o for o in _pending_orders if now - o['timestamp'] < 120]
import os
from datetime import datetime
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
import logging

load_dotenv()

_trading_client = TradingClient(
    os.getenv("APCA_API_KEY_ID"),
    os.getenv("APCA_API_SECRET_KEY"),
    paper=True
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def place_market_order(symbol: str, qty: float, side: str) -> dict | None:
    # --- K) Fractional Sizing & Rounding ---
    min_dollar_trade = 1.0
    notional_supported = hasattr(_trading_client, 'submit_order') and 'notional' in MarketOrderRequest.__annotations__
    price = 1.0  # Placeholder: fetch live price here if needed
    # If notional supported, use notional sizing
    if notional_supported:
        notional = qty * price
        if notional < min_dollar_trade:
            logging.warning(f"Order not placed: notional < min trade for {symbol}")
            return None
    else:
        qty = int(qty)
        if qty * price < min_dollar_trade:
            logging.warning(f"Order not placed: qty*dollar < min trade for {symbol}")
            return None

    # --- J) Idempotency check ---
    if is_order_pending(symbol, side):
        logging.warning(f"Order not placed: pending order exists for {symbol} {side}")
        return None
    record_pending_order(symbol, side)
    """
    side: 'buy' or 'sell'
    """
    logging.info(f"Placing market order: symbol={symbol}, qty={qty}, side={side}")
    if qty <= 0:
        logging.warning(f"Order not placed: qty <= 0 for {symbol}")
        return None

    order = MarketOrderRequest(
        symbol=symbol,
        qty=qty,
        side=OrderSide.BUY if side == "buy" else OrderSide.SELL,
        time_in_force=TimeInForce.DAY
    )
def place_bracket_order(symbol: str, qty: float, side: str, stop_loss: float, take_profit: float) -> dict | None:
    """
    Place a bracket order (stop + take profit). If open gap-through, market out immediately.
    """
    # Placeholder: implement actual bracket order logic with Alpaca API
    logging.info(f"Placing bracket order: symbol={symbol}, qty={qty}, side={side}, stop_loss={stop_loss}, take_profit={take_profit}")
    # If market opens with gap through stop, market out immediately
    # ...existing code...
    return place_market_order(symbol, qty, side)
    try:
        resp = _trading_client.submit_order(order)
        logging.info(f"Order submitted: id={resp.id}, symbol={symbol}, qty={resp.qty}, side={side}, status={resp.status}")
        return {
            "id": resp.id,
            "symbol": symbol,
            "qty": float(resp.qty),
            "side": side,
            "submitted_at": getattr(resp, "submitted_at", None),
            "status": resp.status
        }
    except Exception as e:
        logging.error(f"Order error for {symbol}: {e}", exc_info=True)
        return None

def get_account_cash() -> float:
    try:
        acct = _trading_client.get_account()
        logging.info(f"Fetched account cash: {acct.cash}")
        return float(acct.cash)
    except Exception as e:
        logging.error(f"Error fetching account cash: {e}", exc_info=True)
        return 0.0

def get_clock():
    try:
        clock = _trading_client.get_clock()
        logging.info(f"Fetched market clock: {clock}")
        return clock
    except Exception as e:
        logging.error(f"Error fetching market clock: {e}", exc_info=True)
        return None

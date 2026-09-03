import os
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient
from core.risk import RiskManager
import logging
from alpaca.trading.requests import MarketOrderRequest, StopLimitOrderRequest, TrailingStopOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

load_dotenv()

# Configure logging for TradeExecutor
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

trading_client = TradingClient(
    os.getenv("APCA_API_KEY_ID"),
    os.getenv("APCA_API_SECRET_KEY"),
    paper=True
)

def execute_trade(action, symbol, trading_client, account_equity, entry_price, portfolio, peak_equity, risk_manager=None, trailing_stop=None):
    """
    Place a market order in Alpaca Paper Trading with centralized risk checks and stop-loss/take-profit/trailing stop logic.
    """
    if risk_manager is None:
        risk_manager = RiskManager()
    # Use RiskManager for trade permission and sizing
    if not risk_manager.should_trade(symbol, action, portfolio, account_equity, entry_price, peak_equity):
        logging.info(f"Trade not allowed for {symbol} by risk manager.")
        return None
    size = risk_manager.calculate_position_size(account_equity, entry_price)
    stop_price = risk_manager.get_stop_loss_price(entry_price)
    tp_price = risk_manager.get_take_profit_price(entry_price)
    side = OrderSide.BUY if action == "buy" else OrderSide.SELL
    order = MarketOrderRequest(
        symbol=symbol,
        qty=size,
        side=side,
        time_in_force=TimeInForce.DAY
    )
    try:
        response = trading_client.submit_order(order)
        logging.info(f"Trade executed: {action} {size} of {symbol} at {response.filled_avg_price}")
        # Submit stop-loss
        stop_order = StopLimitOrderRequest(
            symbol=symbol,
            qty=size,
            side=OrderSide.SELL if action == "buy" else OrderSide.BUY,
            stop_price=stop_price,
            limit_price=stop_price,
            time_in_force=TimeInForce.GTC
        )
        trading_client.submit_order(stop_order)
        # Submit take-profit
        tp_order = StopLimitOrderRequest(
            symbol=symbol,
            qty=size,
            side=OrderSide.SELL if action == "buy" else OrderSide.BUY,
            stop_price=tp_price,
            limit_price=tp_price,
            time_in_force=TimeInForce.GTC
        )
        trading_client.submit_order(tp_order)
        # Submit trailing stop if provided
        if trailing_stop is not None:
            trailing_order = TrailingStopOrderRequest(
                symbol=symbol,
                qty=size,
                side=OrderSide.SELL if action == "buy" else OrderSide.BUY,
                trail_price=trailing_stop,
                time_in_force=TimeInForce.GTC
            )
            trading_client.submit_order(trailing_order)
            logging.info(f"Trailing stop order submitted for {symbol} at trail price {trailing_stop}")
        return {
            "action": action,
            "size": size,
            "price": float(response.filled_avg_price) if response.filled_avg_price else None,
            "response": str(response)
        }
    except Exception as e:
        logging.error(f"Trade error for {symbol}: {e}", exc_info=True)
        return None

# Advanced risk controls you can add:
# - Dynamic position sizing based on volatility or risk per trade
# - Daily/weekly loss limits (halt trading if exceeded)
# - Max drawdown limits
# - Sector/asset class exposure limits
# - Trailing stop-loss orders
# - Time-based exits (e.g., close all positions at end of day)
# - Slippage and order fill monitoring

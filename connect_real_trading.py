#!/usr/bin/env python3
"""
Connect LiteBotX to Real Paper Trading
Integrate ExecutionEngine with Alpaca paper trading API
"""

import os
import sys
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, GetOrdersRequest
from alpaca.trading.enums import OrderSide, TimeInForce, QueryOrderStatus
import logging
import datetime as dt
import time
from functools import wraps

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def retry_on_connection_error(max_retries=3, base_delay=2.0):
    """Decorator to retry API calls on connection errors"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    error_msg = str(e)
                    
                    # Check if it's a connection-related error
                    is_connection_error = any([
                        'connection' in error_msg.lower(),
                        'timeout' in error_msg.lower(),
                        'name resolution' in error_msg.lower(),
                        'network' in error_msg.lower(),
                        'errno' in error_msg.lower(),
                        'max retries exceeded' in error_msg.lower()
                    ])
                    
                    if not is_connection_error:
                        # Not a connection error, don't retry
                        raise
                    
                    if attempt < max_retries:
                        delay = min(base_delay * (2 ** attempt), 30.0)
                        logging.warning(
                            f"⚠️ Connection failed (attempt {attempt + 1}/{max_retries + 1}): {error_msg}"
                        )
                        logging.info(f"🔄 Retrying in {delay:.1f} seconds...")
                        time.sleep(delay)
                    else:
                        logging.error(
                            f"❌ Connection failed after {max_retries + 1} attempts: {error_msg}"
                        )
                        raise
            
            if last_exception:
                raise last_exception
        return wrapper
    return decorator


class RealPaperTradingEngine:
    """
    ExecutionEngine that connects to Alpaca trading
    Uses API keys from .env to determine paper vs live trading
    - Paper API keys → paper trading
    - Live API keys → live trading (real money)
    """
    
    def __init__(self):
        load_dotenv()
        
        # Initialize Alpaca client with API keys from .env
        # The API keys themselves determine if it's paper or live trading
        api_key = os.getenv("APCA_API_KEY_ID")
        api_secret = os.getenv("APCA_API_SECRET_KEY")
        
        # Determine mode based on API base URL
        base_url = os.getenv("APCA_API_BASE_URL", "")
        is_paper = "paper" in base_url.lower()
        
        self.client = TradingClient(
            api_key,
            api_secret,
            paper=is_paper
        )
        
        self.order_id_counter = 1
        mode = "PAPER" if is_paper else "LIVE"
        logging.info(f"🔗 Alpaca Trading Engine initialized in {mode} mode")
        if not is_paper:
            logging.warning("⚠️  LIVE TRADING MODE - Real money at risk!")
        else:
            logging.info("📝 Paper trading mode - simulated trades")
    
    @retry_on_connection_error(max_retries=3, base_delay=2.0)
    def get_account_info(self):
        """Get current account information"""
        try:
            account = self.client.get_account()
            return {
                'portfolio_value': float(account.portfolio_value),
                'cash': float(account.cash),
                'buying_power': float(account.buying_power),
                'status': account.status
            }
        except Exception as e:
            logging.error(f"Failed to get account info: {e}")
            return None
    
    @retry_on_connection_error(max_retries=3, base_delay=2.0)
    def get_positions(self):
        """Get current positions from Alpaca"""
        try:
            positions = self.client.get_all_positions()
            position_dict = {}
            
            for pos in positions:
                position_dict[pos.symbol] = {
                    'quantity': float(pos.qty),
                    'avg_cost': float(pos.avg_entry_price),
                    'market_value': float(pos.market_value),
                    'unrealized_pnl': float(pos.unrealized_pl),
                    'side': pos.side
                }
            
            return position_dict
        except Exception as e:
            logging.error(f"Failed to get positions: {e}")
            return {}
    
    @retry_on_connection_error(max_retries=3, base_delay=2.0)
    def submit_order(self, symbol, quantity, side='buy', order_type='market'):
        """Submit order to Alpaca paper trading and wait for fill.
        
        Args:
            symbol: Stock symbol
            quantity: Number of shares
            side: 'buy' or 'sell' (legacy)
            order_type: 'market_buy' or 'market_sell' (new interface)
            
        Returns:
            Dict with order details including avg_fill_price from Alpaca,
            or None if order failed.
        """
        try:
            # Handle both old and new interfaces
            if order_type:
                if 'sell' in order_type.lower():
                    side = 'sell'
                elif 'buy' in order_type.lower():
                    side = 'buy'
            
            # Convert side to Alpaca enum
            alpaca_side = OrderSide.BUY if side.lower() == 'buy' else OrderSide.SELL
            
            # Create market order request
            market_order_data = MarketOrderRequest(
                symbol=symbol,
                qty=abs(quantity),
                side=alpaca_side,
                time_in_force=TimeInForce.DAY
            )
            
            # Submit order
            order = self.client.submit_order(order_data=market_order_data)
            
            # Wait for fill — market orders typically fill within seconds
            # Poll up to 10 seconds for fill confirmation
            filled_price = None
            filled_at = order.filled_at if hasattr(order, 'filled_at') else None
            order_status = str(order.status) if order.status else 'unknown'
            
            if order_status not in ('filled',):
                for _attempt in range(10):
                    time.sleep(1)
                    try:
                        refreshed = self.client.get_order_by_id(order.id)
                        order_status = str(refreshed.status) if refreshed.status else 'unknown'
                        if order_status == 'filled':
                            filled_price = float(refreshed.filled_avg_price) if refreshed.filled_avg_price else None
                            filled_at = refreshed.filled_at
                            logging.info(
                                f"✅ Order filled: {symbol} {quantity} shares @ ${filled_price:.2f}" 
                                if filled_price else f"✅ Order filled: {symbol} (no avg price yet)"
                            )
                            break
                        elif order_status in ('canceled', 'expired', 'rejected'):
                            logging.error(f"❌ Order {order_status}: {symbol} {quantity} shares ({side})")
                            return None
                    except Exception as poll_err:
                        logging.debug(f"Order poll attempt failed: {poll_err}")
            else:
                # Already filled on submit
                filled_price = float(order.filled_avg_price) if hasattr(order, 'filled_avg_price') and order.filled_avg_price else None
            
            result = {
                'order_id': order.id,
                'symbol': symbol,
                'quantity': float(order.qty),
                'side': side,
                'status': order_status,
                'submitted_at': order.submitted_at,
                'filled_at': filled_at,
                'avg_fill_price': filled_price
            }
            
            if filled_price:
                logging.info(f"✅ Order submitted & filled: {symbol} {quantity} shares ({side}) @ ${filled_price:.2f}")
            else:
                logging.info(f"✅ Order submitted: {symbol} {quantity} shares ({side}) — fill price pending")
            return result
            
        except Exception as e:
            error_msg = str(e)
            # Extract more details from Alpaca API errors
            if hasattr(e, 'response') and hasattr(e.response, 'text'):
                error_msg = f"{e} | Response: {e.response.text}"
            logging.error(f"❌ Failed to submit order {symbol} ({side} {quantity} shares): {error_msg}")
            return None
    
    def get_portfolio_summary(self):
        """Get portfolio summary with positions"""
        account_info = self.get_account_info()
        positions = self.get_positions()
        
        if not account_info:
            return None
        
        return {
            'account': account_info,
            'positions': positions,
            'position_count': len(positions),
            'total_unrealized_pnl': sum(pos['unrealized_pnl'] for pos in positions.values())
        }
    
    @retry_on_connection_error(max_retries=3, base_delay=2.0)
    def get_order_history(self, days_back=30, status='all', limit=500):
        """
        Get order history from Alpaca
        
        Args:
            days_back: How many days back to retrieve (default 30, max 90)
            status: 'all', 'open', 'closed' (use 'closed' to get filled orders)
            limit: Max orders to retrieve (default 500)
        
        Returns:
            List of order dictionaries with timestamps
        """
        try:
            # Calculate start date
            after = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days_back)
            
            # Map status to Alpaca enum
            status_map = {
                'all': QueryOrderStatus.ALL,
                'open': QueryOrderStatus.OPEN,
                'closed': QueryOrderStatus.CLOSED,  # Closed includes filled orders
                'filled': QueryOrderStatus.CLOSED   # Alias for closed
            }
            
            # Create request
            request = GetOrdersRequest(
                status=status_map.get(status, QueryOrderStatus.ALL),
                after=after,
                limit=limit
            )
            
            # Get orders
            orders = self.client.get_orders(request)
            
            # Convert to list of dicts with key fields
            order_list = []
            for order in orders:
                order_dict = {
                    'order_id': str(order.id),
                    'symbol': order.symbol,
                    'side': str(order.side),
                    'qty': float(order.qty),
                    'filled_qty': float(order.filled_qty) if order.filled_qty else 0,
                    'status': str(order.status),
                    'submitted_at': order.submitted_at,
                    'filled_at': order.filled_at,
                    'filled_avg_price': float(order.filled_avg_price) if order.filled_avg_price else None,
                    'order_type': str(order.type)
                }
                
                # Only include orders with filled quantities for 'filled' status
                if status == 'filled' and order_dict['filled_qty'] > 0:
                    order_list.append(order_dict)
                elif status != 'filled':
                    order_list.append(order_dict)
            
            logging.info(f"Retrieved {len(order_list)} orders from last {days_back} days")
            return order_list
            
        except Exception as e:
            logging.error(f"Failed to get order history: {str(e)}")
            return []
    
    @retry_on_connection_error(max_retries=3, base_delay=2.0)
    def get_order_by_id(self, order_id):
        """
        Get specific order details by order ID
        
        Args:
            order_id: Order ID (string or UUID)
        
        Returns:
            Order dictionary with full details
        """
        try:
            order = self.client.get_order_by_id(order_id)
            
            return {
                'order_id': str(order.id),
                'symbol': order.symbol,
                'qty': float(order.qty),
                'filled_qty': float(order.filled_qty) if order.filled_qty else 0,
                'side': order.side.value,
                'type': order.type.value,
                'status': order.status.value,
                'submitted_at': order.submitted_at,
                'filled_at': order.filled_at if order.filled_at else None,
                'filled_avg_price': float(order.filled_avg_price) if order.filled_avg_price else None,
                'time_in_force': order.time_in_force.value,
                'created_at': order.created_at,
                'updated_at': order.updated_at
            }
            
        except Exception as e:
            logging.error(f"Failed to get order {order_id}: {e}")
            return None

def test_real_trading_engine():
    """Test the real trading engine"""
    print("🧪 Testing Real Paper Trading Engine")
    print("=" * 50)
    
    # Initialize engine
    engine = RealPaperTradingEngine()
    
    # Test account access
    account_info = engine.get_account_info()
    if account_info:
        print(f"✅ Account Status: {account_info['status']}")
        print(f"   Portfolio Value: ${account_info['portfolio_value']:,.2f}")
        print(f"   Cash: ${account_info['cash']:,.2f}")
        print(f"   Buying Power: ${account_info['buying_power']:,.2f}")
    
    # Test position access
    positions = engine.get_positions()
    print(f"✅ Current Positions: {len(positions)}")
    
    for symbol, pos in positions.items():
        pnl = pos['unrealized_pnl']
        print(f"   {symbol}: {pos['quantity']} shares @ ${pos['avg_cost']:.2f} "
              f"(P&L: ${pnl:+.2f})")
    
    # Test portfolio summary
    portfolio = engine.get_portfolio_summary()
    if portfolio:
        print(f"✅ Portfolio Summary Generated")
        print(f"   Total Positions: {portfolio['position_count']}")
        print(f"   Total Unrealized P&L: ${portfolio['total_unrealized_pnl']:+.2f}")
    
    return engine

if __name__ == "__main__":
    engine = test_real_trading_engine()
    
    # Ask user if they want to test a small order
    print("\n" + "=" * 50)
    print("📋 Ready to connect LiteBotX to real paper trading!")
    print("   Next step: Modify litebotx_phase3.py to use RealPaperTradingEngine")

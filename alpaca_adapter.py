"""
Alpaca Trading Client Adapter for bot_v2
Wraps alpaca-py TradingClient to provide the interface bot_v2 expects
"""
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, GetOrdersRequest
from alpaca.trading.enums import OrderSide, TimeInForce, QueryOrderStatus
import logging
from typing import Dict, List, Optional


class AlpacaAdapter:
    """
    Adapter to make alpaca-py TradingClient compatible with bot_v2's expected interface.
    Provides methods that bot_v2 modules expect (get_portfolio_summary, get_positions, etc.)
    """
    
    def __init__(self, api_key: str, secret_key: str, paper: bool = True):
        """
        Initialize Alpaca trading client
        
        Args:
            api_key: Alpaca API key
            secret_key: Alpaca secret key
            paper: True for paper trading, False for live
        """
        self.client = TradingClient(
            api_key=api_key,
            secret_key=secret_key,
            paper=paper
        )
        self.logger = logging.getLogger(__name__)
        
    def get_portfolio_summary(self) -> Dict:
        """
        Get portfolio summary in the format bot_v2 expects
        
        Returns:
            Dict with account information
        """
        try:
            account = self.client.get_account()
            return {
                'account': {
                    'portfolio_value': float(account.portfolio_value),
                    'buying_power': float(account.buying_power),
                    'cash': float(account.cash),
                    'equity': float(account.equity),
                    'last_equity': float(account.last_equity),
                    'pattern_day_trader': account.pattern_day_trader,
                    'trading_blocked': account.trading_blocked,
                    'account_blocked': account.account_blocked
                }
            }
        except Exception as e:
            self.logger.error(f"Error fetching portfolio summary: {e}")
            raise
            
    def get_positions(self) -> Dict[str, Dict]:
        """
        Get current positions in the format bot_v2 expects
        
        Returns:
            Dict mapping symbol -> position data
        """
        try:
            positions = self.client.get_all_positions()
            
            position_dict = {}
            for pos in positions:
                position_dict[pos.symbol] = {
                    'quantity': float(pos.qty),
                    'avg_cost': float(pos.avg_entry_price),
                    'market_value': float(pos.market_value),
                    'unrealized_pnl': float(pos.unrealized_pl or 0),
                    'side': str(pos.side),
                    'current_price': float(pos.current_price or pos.avg_entry_price)
                }
                
            return position_dict
            
        except Exception as e:
            self.logger.error(f"Error fetching positions: {e}")
            return {}
            
    def submit_order(self, symbol: str, qty: float, side: str, order_type: str = 'market',
                    time_in_force: str = 'day', limit_price: Optional[float] = None) -> Dict:
        """
        Submit an order
        
        Args:
            symbol: Stock symbol
            qty: Quantity (shares)
            side: 'buy' or 'sell'
            order_type: 'market' or 'limit'
            time_in_force: 'day', 'gtc', etc.
            limit_price: Limit price (for limit orders)
            
        Returns:
            Dict with order information
        """
        try:
            # Create order request
            order_side = OrderSide.BUY if side.lower() == 'buy' else OrderSide.SELL
            tif = TimeInForce.DAY if time_in_force.lower() == 'day' else TimeInForce.GTC
            
            # Currently only supporting market orders for simplicity
            if order_type.lower() == 'market':
                request = MarketOrderRequest(
                    symbol=symbol,
                    qty=qty,
                    side=order_side,
                    time_in_force=tif
                )
            else:
                raise ValueError(f"Order type {order_type} not yet supported in adapter")
                
            # Submit order
            order = self.client.submit_order(request)
            
            return {
                'order_id': str(order.id),
                'symbol': order.symbol,
                'qty': float(order.qty),
                'side': str(order.side),
                'order_type': str(order.order_type),
                'status': str(order.status),
                'submitted_at': order.submitted_at,
                'filled_at': order.filled_at,
                'avg_fill_price': float(order.filled_avg_price) if order.filled_avg_price else None
            }
            
        except Exception as e:
            self.logger.error(f"Error submitting order for {symbol}: {e}")
            raise
            
    def get_order(self, order_id: str) -> Dict:
        """
        Get order by ID
        
        Args:
            order_id: Order ID
            
        Returns:
            Dict with order information
        """
        try:
            order = self.client.get_order_by_id(order_id)
            
            return {
                'order_id': str(order.id),
                'symbol': order.symbol,
                'qty': float(order.qty),
                'side': str(order.side),
                'order_type': str(order.order_type),
                'status': str(order.status),
                'submitted_at': order.submitted_at,
                'filled_at': order.filled_at,
                'avg_fill_price': float(order.filled_avg_price) if order.filled_avg_price else None
            }
            
        except Exception as e:
            self.logger.error(f"Error fetching order {order_id}: {e}")
            raise
            
    def get_order_history(self, days_back: int = 5, status: str = 'closed') -> List[Dict]:
        """
        Get order history for the past N days
        
        Args:
            days_back: Number of days to look back
            status: Order status filter ('closed', 'all', 'open')
            
        Returns:
            List of order dicts
        """
        try:
            # Map status to Alpaca QueryOrderStatus
            if status == 'closed':
                status_filter = QueryOrderStatus.CLOSED
            elif status == 'open':
                status_filter = QueryOrderStatus.OPEN
            else:
                status_filter = QueryOrderStatus.ALL
            
            # Create request for orders
            from datetime import datetime, timedelta
            after = datetime.now() - timedelta(days=days_back)
            
            request = GetOrdersRequest(
                status=status_filter,
                after=after
            )
            
            orders = self.client.get_orders(filter=request)
            
            # Convert to dict format
            order_list = []
            for order in orders:
                order_list.append({
                    'order_id': str(order.id),
                    'symbol': order.symbol,
                    'qty': float(order.qty),
                    'side': str(order.side),
                    'order_type': str(order.order_type),
                    'status': str(order.status),
                    'submitted_at': order.submitted_at,
                    'filled_at': order.filled_at,
                    'avg_fill_price': float(order.filled_avg_price) if order.filled_avg_price else None
                })
            
            return order_list
            
        except Exception as e:
            self.logger.warning(f"Error fetching order history: {e}")
            return []
            
    def cancel_all_orders(self) -> List[str]:
        """
        Cancel all open orders
        
        Returns:
            List of cancelled order IDs
        """
        try:
            cancelled = self.client.cancel_orders()
            return [str(order.id) for order in cancelled]
        except Exception as e:
            self.logger.error(f"Error cancelling orders: {e}")
            return []
            
    def close_position(self, symbol: str) -> Dict:
        """
        Close a position (market order to close)
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Dict with order information
        """
        try:
            order = self.client.close_position(symbol)
            
            return {
                'order_id': str(order.id),
                'symbol': order.symbol,
                'qty': float(order.qty),
                'side': str(order.side),
                'status': str(order.status),
                'submitted_at': order.submitted_at
            }
            
        except Exception as e:
            self.logger.error(f"Error closing position for {symbol}: {e}")
            raise

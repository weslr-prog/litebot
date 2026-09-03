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

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

class RealPaperTradingEngine:
    """
    ExecutionEngine that connects to real Alpaca paper trading
    """
    
    def __init__(self):
        load_dotenv()
        
        # Initialize Alpaca client
        self.client = TradingClient(
            os.getenv("APCA_API_KEY_ID"),
            os.getenv("APCA_API_SECRET_KEY"),
            paper=True
        )
        
        self.order_id_counter = 1
        logging.info("🔗 Real Paper Trading Engine initialized")
    
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
    
    def submit_order(self, symbol, quantity, side='buy', order_type='market'):
        """Submit order to Alpaca paper trading"""
        try:
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
            
            result = {
                'order_id': order.id,
                'symbol': symbol,
                'quantity': float(order.qty),
                'side': side,
                'status': order.status,
                'submitted_at': order.submitted_at,
                'filled_at': order.filled_at if hasattr(order, 'filled_at') else None
            }
            
            logging.info(f"✅ Order submitted: {symbol} {quantity} shares ({side})")
            return result
            
        except Exception as e:
            logging.error(f"❌ Failed to submit order {symbol}: {e}")
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

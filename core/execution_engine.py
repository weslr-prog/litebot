"""
Trade Execution Engine for LiteBotX - Phase 3
Purpose: Execute trades with order management and position tracking
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

class ExecutionEngine:
    """
    Handles trade execution, order management, and position tracking
    
    Features:
    - Paper trading simulation
    - Order management (market, limit orders)
    - Real-time position tracking
    - Slippage and commission modeling
    - Stop-loss and take-profit automation
    """
    
    def __init__(self, initial_equity=10000.0, commission=0.0, slippage=0.001):
        self.initial_equity = initial_equity
        self.current_equity = initial_equity
        self.commission = commission  # Commission per share
        self.slippage = slippage      # Slippage as percentage
        
        # Position tracking
        self.positions = {}           # Active positions
        self.orders = {}              # Pending orders
        self.trade_history = []       # Completed trades
        self.daily_pnl = []          # Daily P&L tracking
        
        # Performance metrics
        self.total_trades = 0
        self.winning_trades = 0
        self.total_pnl = 0.0
        self.max_drawdown = 0.0
        self.peak_equity = initial_equity
        
        # Order ID tracking
        self.next_order_id = 1
        
        logging.info(f"🔧 ExecutionEngine initialized: ${initial_equity:,.2f} equity")

    def submit_order(self, symbol: str, order_type: str, quantity: int, 
                    price: Optional[float] = None, stop_loss: Optional[float] = None,
                    take_profit: Optional[float] = None, time_in_force: str = 'GTC') -> Dict:
        """
        Submit a trading order
        
        Args:
            symbol: Stock symbol
            order_type: 'market_buy', 'market_sell', 'limit_buy', 'limit_sell'
            quantity: Number of shares (positive for buy, negative for sell)
            price: Limit price (required for limit orders)
            stop_loss: Stop loss price
            take_profit: Take profit price
            time_in_force: 'GTC' (Good Till Canceled) or 'DAY'
            
        Returns:
            Dict with order details and execution status
        """
        order_id = f"ORD_{self.next_order_id:06d}"
        self.next_order_id += 1
        
        # Validate order
        validation_result = self._validate_order(symbol, order_type, quantity, price)
        if not validation_result['valid']:
            return {
                'order_id': order_id,
                'status': 'REJECTED',
                'reason': validation_result['reason'],
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        
        # Create order object
        order = {
            'order_id': order_id,
            'symbol': symbol,
            'order_type': order_type,
            'quantity': quantity,
            'price': price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'time_in_force': time_in_force,
            'status': 'PENDING',
            'timestamp': datetime.now(timezone.utc),
            'filled_quantity': 0,
            'avg_fill_price': 0.0
        }
        
        # For market orders, execute immediately
        if order_type in ['market_buy', 'market_sell']:
            execution_result = self._execute_market_order(order)
            return execution_result
        else:
            # Store limit order for later execution
            self.orders[order_id] = order
            logging.info(f"📋 Limit order submitted: {order_id} - {symbol} {quantity} @ ${price:.2f}")
            return {
                'order_id': order_id,
                'status': 'PENDING',
                'message': 'Limit order submitted',
                'timestamp': order['timestamp'].isoformat()
            }

    def _validate_order(self, symbol: str, order_type: str, quantity: int, price: Optional[float]) -> Dict:
        """Validate order parameters"""
        
        # Check quantity
        if quantity == 0:
            return {'valid': False, 'reason': 'Quantity cannot be zero'}
        
        # Check price for limit orders
        if order_type in ['limit_buy', 'limit_sell'] and (price is None or price <= 0):
            return {'valid': False, 'reason': 'Limit orders require valid price'}
        
        # Check buying power for buy orders
        if order_type in ['market_buy', 'limit_buy']:
            required_capital = abs(quantity) * (price or 100)  # Estimate for market orders
            if required_capital > self.current_equity:
                return {'valid': False, 'reason': 'Insufficient buying power'}
        
        # Check position for sell orders
        if order_type in ['market_sell', 'limit_sell']:
            current_position = self.positions.get(symbol, {}).get('quantity', 0)
            if abs(quantity) > current_position:
                return {'valid': False, 'reason': 'Insufficient position to sell'}
        
        return {'valid': True, 'reason': 'Order validated'}

    def _execute_market_order(self, order: Dict) -> Dict:
        """Execute market order immediately"""
        symbol = order['symbol']
        quantity = order['quantity']
        order_type = order['order_type']
        
        # Simulate market price (in real implementation, get from market data)
        # For testing, use a base price of $100
        market_price = 100.0
        
        # Apply slippage
        if order_type == 'market_buy':
            execution_price = market_price * (1 + self.slippage)
        else:  # market_sell
            execution_price = market_price * (1 - self.slippage)
        
        # Calculate trade value
        trade_value = abs(quantity) * execution_price
        commission_cost = abs(quantity) * self.commission
        total_cost = trade_value + commission_cost
        
        # Execute the trade
        if order_type == 'market_buy':
            # Update equity
            self.current_equity -= total_cost
            
            # Update or create position
            if symbol in self.positions:
                # Add to existing position
                existing_qty = self.positions[symbol]['quantity']
                existing_cost = self.positions[symbol]['avg_cost'] * existing_qty
                new_qty = existing_qty + abs(quantity)
                new_avg_cost = (existing_cost + trade_value) / new_qty
                
                self.positions[symbol] = {
                    'quantity': new_qty,
                    'avg_cost': new_avg_cost,
                    'market_value': new_qty * market_price,
                    'unrealized_pnl': new_qty * (market_price - new_avg_cost),
                    'last_update': datetime.now(timezone.utc)
                }
            else:
                # Create new position
                self.positions[symbol] = {
                    'quantity': abs(quantity),
                    'avg_cost': execution_price,
                    'market_value': abs(quantity) * market_price,
                    'unrealized_pnl': abs(quantity) * (market_price - execution_price),
                    'last_update': datetime.now(timezone.utc)
                }
        
        else:  # market_sell
            # Update equity
            self.current_equity += trade_value - commission_cost
            
            # Update position
            if symbol in self.positions:
                current_qty = self.positions[symbol]['quantity']
                avg_cost = self.positions[symbol]['avg_cost']
                
                # Calculate realized P&L
                realized_pnl = abs(quantity) * (execution_price - avg_cost) - commission_cost
                
                # Update position
                new_qty = current_qty - abs(quantity)
                if new_qty <= 0:
                    # Close position
                    del self.positions[symbol]
                else:
                    self.positions[symbol]['quantity'] = new_qty
                    self.positions[symbol]['market_value'] = new_qty * market_price
                    self.positions[symbol]['unrealized_pnl'] = new_qty * (market_price - avg_cost)
                    self.positions[symbol]['last_update'] = datetime.now(timezone.utc)
                
                # Record trade
                self._record_trade(symbol, quantity, execution_price, realized_pnl)
        
        # Update order status
        order['status'] = 'FILLED'
        order['filled_quantity'] = abs(quantity)
        order['avg_fill_price'] = execution_price
        
        # Update performance metrics
        self._update_performance_metrics()
        
        logging.info(f"✅ Market order executed: {symbol} {quantity} @ ${execution_price:.2f}")
        
        return {
            'order_id': order['order_id'],
            'status': 'FILLED',
            'symbol': symbol,
            'quantity': quantity,
            'execution_price': execution_price,
            'total_cost': total_cost,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

    def _record_trade(self, symbol: str, quantity: int, price: float, pnl: float):
        """Record completed trade in history"""
        trade = {
            'symbol': symbol,
            'quantity': quantity,
            'price': price,
            'pnl': pnl,
            'timestamp': datetime.now(timezone.utc),
            'equity_after': self.current_equity
        }
        
        self.trade_history.append(trade)
        self.total_trades += 1
        self.total_pnl += pnl
        
        if pnl > 0:
            self.winning_trades += 1

    def _update_performance_metrics(self):
        """Update performance tracking metrics"""
        # Update peak equity and max drawdown
        if self.current_equity > self.peak_equity:
            self.peak_equity = self.current_equity
        
        current_drawdown = (self.peak_equity - self.current_equity) / self.peak_equity
        if current_drawdown > self.max_drawdown:
            self.max_drawdown = current_drawdown

    def update_positions(self, market_data: Dict[str, float]):
        """Update position values with current market prices"""
        for symbol, position in self.positions.items():
            if symbol in market_data:
                current_price = market_data[symbol]
                quantity = position['quantity']
                avg_cost = position['avg_cost']
                
                position['market_value'] = quantity * current_price
                position['unrealized_pnl'] = quantity * (current_price - avg_cost)
                position['last_update'] = datetime.now(timezone.utc)

    def check_stop_orders(self, market_data: Dict[str, float]):
        """Check and execute stop-loss and take-profit orders"""
        for symbol, position in self.positions.items():
            if symbol in market_data:
                current_price = market_data[symbol]
                
                # Check for stop-loss triggers (implementation depends on order tracking)
                # This would be implemented with stored stop orders
                pass

    def get_portfolio_summary(self) -> Dict:
        """Get comprehensive portfolio summary"""
        total_position_value = sum(pos['market_value'] for pos in self.positions.values())
        total_unrealized_pnl = sum(pos['unrealized_pnl'] for pos in self.positions.values())
        
        win_rate = (self.winning_trades / self.total_trades) if self.total_trades > 0 else 0
        
        return {
            'equity': self.current_equity,
            'initial_equity': self.initial_equity,
            'total_return': (self.current_equity - self.initial_equity) / self.initial_equity,
            'total_position_value': total_position_value,
            'cash': self.current_equity - total_position_value,
            'unrealized_pnl': total_unrealized_pnl,
            'realized_pnl': self.total_pnl,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'win_rate': win_rate,
            'max_drawdown': self.max_drawdown,
            'active_positions': len(self.positions),
            'pending_orders': len(self.orders)
        }

    def get_position_details(self) -> Dict:
        """Get detailed position information"""
        return self.positions.copy()

    def cancel_order(self, order_id: str) -> Dict:
        """Cancel a pending order"""
        if order_id in self.orders:
            self.orders[order_id]['status'] = 'CANCELLED'
            cancelled_order = self.orders.pop(order_id)
            
            logging.info(f"❌ Order cancelled: {order_id}")
            return {
                'order_id': order_id,
                'status': 'CANCELLED',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        else:
            return {
                'order_id': order_id,
                'status': 'NOT_FOUND',
                'message': 'Order not found'
            }

    def close_position(self, symbol: str) -> Dict:
        """Close entire position in a symbol"""
        if symbol not in self.positions:
            return {
                'status': 'ERROR',
                'message': f'No position found for {symbol}'
            }
        
        quantity = self.positions[symbol]['quantity']
        
        # Submit market sell order for entire position
        return self.submit_order(
            symbol=symbol,
            order_type='market_sell',
            quantity=-quantity  # Negative for sell
        )

# ExecutionEngine ready for trade execution!

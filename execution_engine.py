"""
Trade Execution Engine for LiteBotX - Enhanced with Smart Order Routing
Purpose: Execute trades with VWAP/TWAP algorithms and advanced order management
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Union
from datetime import datetime, timezone, timedelta
import time
import threading
from dataclasses import dataclass
from enum import Enum
import queue

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

class OrderType(Enum):
    """Enhanced order types including smart algorithms"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    VWAP = "vwap"
    TWAP = "twap"
    ICEBERG = "iceberg"
    PEG_MID = "peg_mid"

class OrderStatus(Enum):
    """Order status enumeration"""
    PENDING = "pending"
    WORKING = "working"
    FILLED = "filled"
    PARTIAL = "partial"
    CANCELLED = "cancelled"
    REJECTED = "rejected"

@dataclass
class VWAPConfig:
    """VWAP algorithm configuration"""
    start_time: str = "09:30"  # Market open
    end_time: str = "16:00"    # Market close
    participation_rate: float = 0.20  # 20% of volume
    min_fill_size: int = 100   # Minimum fill size
    max_fill_size: int = 1000  # Maximum fill size per execution
    urgency: str = "normal"    # low, normal, high
    
@dataclass 
class TWAPConfig:
    """TWAP algorithm configuration"""
    duration_minutes: int = 60  # Spread over 60 minutes
    interval_minutes: int = 5   # Execute every 5 minutes
    randomize_timing: bool = True  # Add randomness to timing
    min_slice_pct: float = 0.05    # Min 5% per slice
    max_slice_pct: float = 0.25    # Max 25% per slice

class SmartOrderRouter:
    """Smart order routing with VWAP/TWAP algorithms"""
    
    def __init__(self, execution_engine):
        self.execution_engine = execution_engine
        self.active_algos = {}  # algo_id -> algorithm instance
        self.market_data_cache = {}  # symbol -> recent market data
        self.volume_profiles = {}   # symbol -> historical volume profile
        
    def submit_vwap_order(self, symbol: str, quantity: int, 
                         config: VWAPConfig = None) -> str:
        """Submit VWAP algorithm order"""
        
        config = config or VWAPConfig()
        algo_id = f"VWAP_{symbol}_{datetime.now().strftime('%H%M%S')}"
        
        vwap_algo = VWAPAlgorithm(
            algo_id=algo_id,
            symbol=symbol,
            quantity=quantity,
            config=config,
            execution_engine=self.execution_engine,
            smart_router=self
        )
        
        self.active_algos[algo_id] = vwap_algo
        vwap_algo.start()
        
        logging.info(f"📊 VWAP order submitted: {algo_id} - {symbol} {quantity} shares")
        return algo_id
    
    def submit_twap_order(self, symbol: str, quantity: int,
                         config: TWAPConfig = None) -> str:
        """Submit TWAP algorithm order"""
        
        config = config or TWAPConfig()
        algo_id = f"TWAP_{symbol}_{datetime.now().strftime('%H%M%S')}"
        
        twap_algo = TWAPAlgorithm(
            algo_id=algo_id,
            symbol=symbol,
            quantity=quantity,
            config=config,
            execution_engine=self.execution_engine,
            smart_router=self
        )
        
        self.active_algos[algo_id] = twap_algo
        twap_algo.start()
        
        logging.info(f"⏰ TWAP order submitted: {algo_id} - {symbol} {quantity} shares")
        return algo_id
    
    def get_volume_profile(self, symbol: str) -> Dict:
        """Get historical volume profile for VWAP calculations"""
        
        # Simulate volume profile (in real implementation, get from market data)
        # Returns hourly volume distribution as percentage of daily volume
        return {
            "09:30-10:30": 0.25,  # High volume at open
            "10:30-11:30": 0.15,
            "11:30-12:30": 0.10,
            "12:30-13:30": 0.08,
            "13:30-14:30": 0.10,
            "14:30-15:30": 0.12,
            "15:30-16:00": 0.20   # High volume at close
        }
    
    def get_current_vwap(self, symbol: str) -> float:
        """Calculate current VWAP"""
        # Simulate VWAP calculation
        return 100.0  # Placeholder
    
    def get_market_data(self, symbol: str) -> Dict:
        """Get current market data"""
        # Simulate market data
        return {
            'bid': 99.95,
            'ask': 100.05,
            'last': 100.00,
            'volume': 50000,
            'avg_volume': 100000
        }

class VWAPAlgorithm:
    """Volume Weighted Average Price algorithm"""
    
    def __init__(self, algo_id: str, symbol: str, quantity: int,
                 config: VWAPConfig, execution_engine, smart_router):
        self.algo_id = algo_id
        self.symbol = symbol
        self.total_quantity = quantity
        self.remaining_quantity = quantity
        self.config = config
        self.execution_engine = execution_engine
        self.smart_router = smart_router
        
        self.status = OrderStatus.PENDING
        self.fills = []
        self.start_time = None
        self.thread = None
        self.stop_event = threading.Event()
        
    def start(self):
        """Start VWAP algorithm execution"""
        self.status = OrderStatus.WORKING
        self.start_time = datetime.now()
        self.thread = threading.Thread(target=self._execute_vwap)
        self.thread.daemon = True
        self.thread.start()
    
    def stop(self):
        """Stop VWAP algorithm"""
        self.stop_event.set()
        if self.thread:
            self.thread.join()
    
    def _execute_vwap(self):
        """Main VWAP execution loop"""
        
        logging.info(f"🚀 Starting VWAP execution for {self.symbol}")
        
        while (self.remaining_quantity > 0 and 
               not self.stop_event.is_set() and
               self._is_market_hours()):
            
            try:
                # Get current market data
                market_data = self.smart_router.get_market_data(self.symbol)
                current_vwap = self.smart_router.get_current_vwap(self.symbol)
                
                # Calculate optimal slice size based on volume
                slice_size = self._calculate_vwap_slice_size(market_data)
                
                if slice_size > 0:
                    # Determine execution price strategy
                    execution_price = self._get_vwap_execution_price(
                        market_data, current_vwap)
                    
                    # Submit child order
                    child_order_result = self._submit_child_order(
                        slice_size, execution_price)
                    
                    if child_order_result['status'] == 'FILLED':
                        self.remaining_quantity -= slice_size
                        self.fills.append(child_order_result)
                        
                        logging.info(f"📊 VWAP fill: {slice_size} @ ${execution_price:.2f}, "
                                   f"remaining: {self.remaining_quantity}")
                
                # Wait before next execution
                time.sleep(30)  # 30 second intervals
                
            except Exception as e:
                logging.error(f"VWAP execution error: {e}")
                time.sleep(10)
        
        # Final status update
        if self.remaining_quantity == 0:
            self.status = OrderStatus.FILLED
            logging.info(f"✅ VWAP order completed: {self.algo_id}")
        else:
            self.status = OrderStatus.PARTIAL
            logging.info(f"⚠️ VWAP order partial: {self.algo_id}, "
                        f"remaining: {self.remaining_quantity}")
    
    def _calculate_vwap_slice_size(self, market_data: Dict) -> int:
        """Calculate optimal slice size for VWAP execution"""
        
        current_volume = market_data.get('volume', 0)
        avg_volume = market_data.get('avg_volume', 100000)
        
        # Base slice on participation rate
        target_participation = min(current_volume * self.config.participation_rate, 
                                 self.remaining_quantity)
        
        # Apply size constraints
        slice_size = max(self.config.min_fill_size, 
                        min(target_participation, self.config.max_fill_size))
        
        # Don't exceed remaining quantity
        slice_size = min(slice_size, self.remaining_quantity)
        
        return int(slice_size)
    
    def _get_vwap_execution_price(self, market_data: Dict, current_vwap: float) -> float:
        """Determine execution price for VWAP strategy"""
        
        bid = market_data['bid']
        ask = market_data['ask']
        mid = (bid + ask) / 2
        
        # Aggressive execution if behind VWAP
        if self.total_quantity > 0:  # Buy order
            if mid > current_vwap * 1.001:  # 0.1% above VWAP
                return ask  # Take the offer
            else:
                return min(bid + 0.01, mid)  # Passive between bid and mid
        else:  # Sell order
            if mid < current_vwap * 0.999:  # 0.1% below VWAP
                return bid  # Hit the bid
            else:
                return max(ask - 0.01, mid)  # Passive between mid and ask
    
    def _submit_child_order(self, quantity: int, price: float) -> Dict:
        """Submit child order for VWAP execution"""
        
        order_type = "limit_buy" if self.total_quantity > 0 else "limit_sell"
        
        # Simulate order execution (simplified)
        return {
            'status': 'FILLED',
            'quantity': quantity,
            'price': price,
            'timestamp': datetime.now()
        }
    
    def _is_market_hours(self) -> bool:
        """Check if within market hours"""
        now = datetime.now().time()
        start = datetime.strptime(self.config.start_time, "%H:%M").time()
        end = datetime.strptime(self.config.end_time, "%H:%M").time()
        return start <= now <= end

class TWAPAlgorithm:
    """Time Weighted Average Price algorithm"""
    
    def __init__(self, algo_id: str, symbol: str, quantity: int,
                 config: TWAPConfig, execution_engine, smart_router):
        self.algo_id = algo_id
        self.symbol = symbol
        self.total_quantity = quantity
        self.remaining_quantity = quantity
        self.config = config
        self.execution_engine = execution_engine
        self.smart_router = smart_router
        
        self.status = OrderStatus.PENDING
        self.fills = []
        self.start_time = None
        self.thread = None
        self.stop_event = threading.Event()
        
        # Calculate execution schedule
        self.execution_schedule = self._create_execution_schedule()
    
    def start(self):
        """Start TWAP algorithm execution"""
        self.status = OrderStatus.WORKING
        self.start_time = datetime.now()
        self.thread = threading.Thread(target=self._execute_twap)
        self.thread.daemon = True
        self.thread.start()
    
    def stop(self):
        """Stop TWAP algorithm"""
        self.stop_event.set()
        if self.thread:
            self.thread.join()
    
    def _create_execution_schedule(self) -> List[Dict]:
        """Create TWAP execution schedule"""
        
        schedule = []
        total_intervals = self.config.duration_minutes // self.config.interval_minutes
        base_slice_size = self.total_quantity // total_intervals
        
        current_time = datetime.now()
        
        for i in range(total_intervals):
            # Calculate slice size with some randomization
            if i == total_intervals - 1:  # Last slice gets remainder
                slice_size = self.remaining_quantity
            else:
                randomization = np.random.uniform(
                    self.config.min_slice_pct, self.config.max_slice_pct)
                slice_size = int(base_slice_size * (0.8 + 0.4 * randomization))
            
            # Calculate execution time with randomization
            target_time = current_time + timedelta(
                minutes=i * self.config.interval_minutes)
            
            if self.config.randomize_timing:
                # Add random offset of ±2 minutes
                offset_seconds = np.random.randint(-120, 120)
                target_time += timedelta(seconds=offset_seconds)
            
            schedule.append({
                'time': target_time,
                'quantity': slice_size,
                'executed': False
            })
        
        return schedule
    
    def _execute_twap(self):
        """Main TWAP execution loop"""
        
        logging.info(f"⏰ Starting TWAP execution for {self.symbol} over "
                    f"{self.config.duration_minutes} minutes")
        
        for execution in self.execution_schedule:
            if self.stop_event.is_set():
                break
            
            # Wait until execution time
            while datetime.now() < execution['time'] and not self.stop_event.is_set():
                time.sleep(10)  # Check every 10 seconds
            
            if self.stop_event.is_set():
                break
            
            try:
                # Get current market data
                market_data = self.smart_router.get_market_data(self.symbol)
                
                # Execute slice
                execution_price = self._get_twap_execution_price(market_data)
                slice_size = min(execution['quantity'], self.remaining_quantity)
                
                if slice_size > 0:
                    child_order_result = self._submit_child_order(
                        slice_size, execution_price)
                    
                    if child_order_result['status'] == 'FILLED':
                        self.remaining_quantity -= slice_size
                        self.fills.append(child_order_result)
                        execution['executed'] = True
                        
                        logging.info(f"⏰ TWAP fill: {slice_size} @ ${execution_price:.2f}, "
                                   f"remaining: {self.remaining_quantity}")
                
            except Exception as e:
                logging.error(f"TWAP execution error: {e}")
        
        # Final status update
        if self.remaining_quantity == 0:
            self.status = OrderStatus.FILLED
            logging.info(f"✅ TWAP order completed: {self.algo_id}")
        else:
            self.status = OrderStatus.PARTIAL
            logging.info(f"⚠️ TWAP order partial: {self.algo_id}, "
                        f"remaining: {self.remaining_quantity}")
    
    def _get_twap_execution_price(self, market_data: Dict) -> float:
        """Determine execution price for TWAP strategy"""
        
        bid = market_data['bid']
        ask = market_data['ask']
        mid = (bid + ask) / 2
        
        # TWAP uses more passive pricing
        if self.total_quantity > 0:  # Buy order
            return bid + 0.01  # Just above bid
        else:  # Sell order
            return ask - 0.01  # Just below ask
    
    def _submit_child_order(self, quantity: int, price: float) -> Dict:
        """Submit child order for TWAP execution"""
        
        # Simulate order execution (simplified)
        return {
            'status': 'FILLED',
            'quantity': quantity,
            'price': price,
            'timestamp': datetime.now()
        }

class ExecutionEngine:
    """
    Enhanced execution engine with smart order routing capabilities
    
    Features:
    - Traditional order types (market, limit, stop)
    - Smart algorithms (VWAP, TWAP, Iceberg)
    - Low-latency execution for day trading
    - Advanced slippage and commission modeling
    - Real-time position tracking
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
        
        # Smart order routing
        self.smart_router = SmartOrderRouter(self)
        
        # Execution latency simulation
        self.execution_delay_ms = 50  # 50ms average execution delay
        
        logging.info(f"🔧 Enhanced ExecutionEngine initialized: ${initial_equity:,.2f} equity")
        logging.info(f"   Smart routing: VWAP, TWAP, Iceberg algorithms enabled")
        logging.info(f"   Execution latency: {self.execution_delay_ms}ms")

    def submit_smart_order(self, symbol: str, quantity: int, algorithm: str, 
                          **algo_params) -> Dict:
        """
        Submit smart algorithm order (VWAP, TWAP, etc.)
        
        Args:
            symbol: Stock symbol
            quantity: Number of shares (positive for buy, negative for sell)
            algorithm: 'vwap', 'twap', 'iceberg'
            **algo_params: Algorithm-specific parameters
            
        Returns:
            Dict with algorithm ID and status
        """
        
        if algorithm.lower() == 'vwap':
            config = VWAPConfig(**algo_params) if algo_params else VWAPConfig()
            algo_id = self.smart_router.submit_vwap_order(symbol, quantity, config)
            
        elif algorithm.lower() == 'twap':
            config = TWAPConfig(**algo_params) if algo_params else TWAPConfig()
            algo_id = self.smart_router.submit_twap_order(symbol, quantity, config)
            
        elif algorithm.lower() == 'iceberg':
            algo_id = self._submit_iceberg_order(symbol, quantity, **algo_params)
            
        else:
            return {
                'status': 'REJECTED',
                'reason': f'Unknown algorithm: {algorithm}',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        
        return {
            'algo_id': algo_id,
            'status': 'WORKING',
            'algorithm': algorithm,
            'symbol': symbol,
            'quantity': quantity,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    
    def submit_fast_order(self, symbol: str, order_type: str, quantity: int,
                         price: Optional[float] = None) -> Dict:
        """
        Submit order optimized for low latency (day trading/scalping)
        
        Args:
            symbol: Stock symbol
            order_type: 'market_buy', 'market_sell', 'limit_buy', 'limit_sell'
            quantity: Number of shares
            price: Limit price (for limit orders)
            
        Returns:
            Dict with order result and execution details
        """
        
        start_time = datetime.now()
        
        # Simulate low-latency execution
        time.sleep(self.execution_delay_ms / 1000.0)  # Convert ms to seconds
        
        # Enhanced market order execution with smart routing
        if order_type in ['market_buy', 'market_sell']:
            result = self._execute_fast_market_order(symbol, quantity, order_type)
        else:
            result = self._execute_fast_limit_order(symbol, quantity, price, order_type)
        
        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        result['execution_time_ms'] = execution_time
        
        logging.info(f"⚡ Fast order executed in {execution_time:.1f}ms: "
                    f"{symbol} {quantity} @ ${result.get('fill_price', 0):.2f}")
        
        return result
    
    def get_smart_order_status(self, algo_id: str) -> Dict:
        """Get status of smart algorithm order"""
        
        if algo_id in self.smart_router.active_algos:
            algo = self.smart_router.active_algos[algo_id]
            return {
                'algo_id': algo_id,
                'status': algo.status.value,
                'symbol': algo.symbol,
                'total_quantity': algo.total_quantity,
                'remaining_quantity': algo.remaining_quantity,
                'fills': len(algo.fills),
                'avg_fill_price': self._calculate_avg_fill_price(algo.fills)
            }
        else:
            return {'algo_id': algo_id, 'status': 'NOT_FOUND'}
    
    def cancel_smart_order(self, algo_id: str) -> Dict:
        """Cancel smart algorithm order"""
        
        if algo_id in self.smart_router.active_algos:
            algo = self.smart_router.active_algos[algo_id]
            algo.stop()
            del self.smart_router.active_algos[algo_id]
            
            return {
                'algo_id': algo_id,
                'status': 'CANCELLED',
                'message': 'Algorithm stopped successfully'
            }
        else:
            return {'algo_id': algo_id, 'status': 'NOT_FOUND'}
    
    def _execute_fast_market_order(self, symbol: str, quantity: int, order_type: str) -> Dict:
        """Execute market order with optimized routing"""
        
        # Get current market data
        market_data = self.smart_router.get_market_data(symbol)
        
        # Smart order routing for market orders
        if order_type == 'market_buy':
            # Check spread and volume for optimal execution
            spread = market_data['ask'] - market_data['bid']
            if spread <= 0.02:  # Tight spread, take the offer
                fill_price = market_data['ask']
            else:  # Wide spread, try to get better price
                fill_price = market_data['bid'] + spread * 0.3
        else:  # market_sell
            spread = market_data['ask'] - market_data['bid']
            if spread <= 0.02:  # Tight spread, hit the bid
                fill_price = market_data['bid']
            else:  # Wide spread, try to get better price
                fill_price = market_data['ask'] - spread * 0.3
        
        # Apply minimal slippage for fast execution
        fast_slippage = self.slippage * 0.5  # Reduced slippage for optimized routing
        if order_type == 'market_buy':
            fill_price *= (1 + fast_slippage)
        else:
            fill_price *= (1 - fast_slippage)
        
        # Execute the trade
        result = self._process_fill(symbol, quantity, fill_price, order_type)
        result['routing'] = 'smart_market'
        
        return result
    
    def _execute_fast_limit_order(self, symbol: str, quantity: int, 
                                 price: float, order_type: str) -> Dict:
        """Execute limit order with smart price improvement logic"""
        
        market_data = self.smart_router.get_market_data(symbol)
        
        # Check if limit price can be improved
        if order_type == 'limit_buy' and price >= market_data['ask']:
            # Limit price crosses spread, execute as market
            fill_price = market_data['ask']
            result = self._process_fill(symbol, quantity, fill_price, 'market_buy')
            result['price_improvement'] = price - fill_price
        elif order_type == 'limit_sell' and price <= market_data['bid']:
            # Limit price crosses spread, execute as market
            fill_price = market_data['bid']
            result = self._process_fill(symbol, quantity, fill_price, 'market_sell')
            result['price_improvement'] = fill_price - price
        else:
            # Regular limit order execution logic
            # Simulate probability of fill based on how aggressive the price is
            if order_type == 'limit_buy':
                aggressiveness = (market_data['bid'] - price) / market_data['bid']
            else:
                aggressiveness = (price - market_data['ask']) / market_data['ask']
            
            fill_probability = max(0.1, min(0.9, 0.5 + aggressiveness * 2))
            
            if np.random.random() < fill_probability:
                result = self._process_fill(symbol, quantity, price, order_type)
                result['fill_probability'] = fill_probability
            else:
                result = {
                    'status': 'PENDING',
                    'message': 'Limit order working',
                    'fill_probability': fill_probability
                }
        
        result['routing'] = 'smart_limit'
        return result
    
    def _submit_iceberg_order(self, symbol: str, quantity: int, **params) -> str:
        """Submit iceberg order algorithm"""
        
        # Iceberg parameters
        display_size = params.get('display_size', min(1000, abs(quantity) // 10))
        variance = params.get('variance', 0.1)  # 10% variance in display size
        
        algo_id = f"ICE_{symbol}_{datetime.now().strftime('%H%M%S')}"
        
        # Simplified iceberg implementation (would need full algorithm in production)
        logging.info(f"🧊 Iceberg order submitted: {algo_id} - {symbol} {quantity} "
                    f"(display: {display_size})")
        
        return algo_id
    
    def _process_fill(self, symbol: str, quantity: int, price: float, order_type: str) -> Dict:
        """Process order fill and update positions"""
        
        fill_value = abs(quantity) * price
        commission_cost = abs(quantity) * self.commission
        
        # Update position
        if symbol not in self.positions:
            self.positions[symbol] = {'quantity': 0, 'avg_cost': 0.0, 'unrealized_pnl': 0.0}
        
        position = self.positions[symbol]
        
        if order_type in ['market_buy', 'limit_buy']:
            # Buy order
            old_quantity = position['quantity']
            old_cost_basis = old_quantity * position['avg_cost']
            new_cost_basis = old_cost_basis + fill_value + commission_cost
            new_quantity = old_quantity + quantity
            
            position['quantity'] = new_quantity
            if new_quantity != 0:
                position['avg_cost'] = new_cost_basis / new_quantity
            
            self.current_equity -= (fill_value + commission_cost)
            
        else:
            # Sell order
            old_quantity = position['quantity']
            old_cost_basis = old_quantity * position['avg_cost']
            
            # Calculate realized P&L
            cost_of_sold_shares = abs(quantity) * position['avg_cost']
            realized_pnl = fill_value - cost_of_sold_shares - commission_cost
            
            position['quantity'] -= abs(quantity)
            self.current_equity += (fill_value - commission_cost)
            self.total_pnl += realized_pnl
        
        # Record trade
        trade_record = {
            'timestamp': datetime.now(),
            'symbol': symbol,
            'quantity': quantity,
            'price': price,
            'value': fill_value,
            'commission': commission_cost,
            'order_type': order_type
        }
        
        self.trade_history.append(trade_record)
        self.total_trades += 1
        
        return {
            'status': 'FILLED',
            'symbol': symbol,
            'quantity': quantity,
            'fill_price': price,
            'fill_value': fill_value,
            'commission': commission_cost,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    
    def _calculate_avg_fill_price(self, fills: List[Dict]) -> float:
        """Calculate average fill price from list of fills"""
        if not fills:
            return 0.0
        
        total_value = sum(fill['quantity'] * fill['price'] for fill in fills)
        total_quantity = sum(fill['quantity'] for fill in fills)
        
        return total_value / total_quantity if total_quantity != 0 else 0.0
    
    def get_execution_statistics(self) -> Dict:
        """Get execution quality statistics"""
        
        if not self.trade_history:
            return {'total_trades': 0}
        
        recent_trades = [t for t in self.trade_history 
                        if (datetime.now() - t['timestamp']).total_seconds() < 3600]  # Last hour
        
        total_commission = sum(t['commission'] for t in recent_trades)
        total_value = sum(t['value'] for t in recent_trades)
        
        return {
            'total_trades': len(recent_trades),
            'total_value_traded': total_value,
            'total_commission': total_commission,
            'commission_rate': total_commission / total_value if total_value > 0 else 0,
            'avg_trade_size': total_value / len(recent_trades) if recent_trades else 0,
            'smart_routing_active': len(self.smart_router.active_algos),
            'execution_latency_ms': self.execution_delay_ms
        }

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

#!/usr/bin/env python3
"""
Stock API Manager for LiteBotX Dashboard
Handles Alpaca API integration and data fetching
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import os
from typing import Dict, List, Optional
import logging

# Use the same Alpaca library as your trading bot
from alpaca.trading.client import TradingClient

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StockAPIManager:
    def __init__(self):
        """Initialize API connections"""
        self.alpaca_api = None
        self.setup_alpaca()
        
    def setup_alpaca(self):
        """Setup Alpaca API connection using same method as trading bot"""
        try:
            api_key = os.getenv("APCA_API_KEY_ID")
            secret_key = os.getenv("APCA_API_SECRET_KEY")
            paper = True  # Use paper trading like your bot
            
            if api_key and secret_key:
                self.alpaca_api = TradingClient(
                    api_key=api_key,
                    secret_key=secret_key,
                    paper=paper
                )
                logger.info("✅ Alpaca API connected successfully")
            else:
                logger.warning("⚠️ Alpaca API credentials not found")
                
        except Exception as e:
            logger.error(f"❌ Failed to connect to Alpaca API: {e}")
            self.alpaca_api = None
    
    def get_account_info(self) -> Dict:
        """Get account information from Alpaca"""
        if not self.alpaca_api:
            return self._get_sample_account_data()
            
        try:
            account = self.alpaca_api.get_account()
            return {
                'account_value': float(account.portfolio_value),
                'buying_power': float(account.buying_power), 
                'cash': float(account.cash),
                'daily_pnl': 0.0,  # Not available in new API
                'total_pnl': 0.0,  # Calculate separately if needed
                'account_blocked': account.account_blocked,
                'trading_blocked': account.trading_blocked,
                'pattern_day_trader': account.pattern_day_trader
            }
        except Exception as e:
            logger.error(f"❌ Error fetching account info: {e}")
            return self._get_sample_account_data()
    
    def get_positions(self) -> List[Dict]:
        """Get current positions from Alpaca"""
        if not self.alpaca_api:
            return self._get_sample_positions()
            
        try:
            positions = self.alpaca_api.get_all_positions()
            position_data = []
            
            for pos in positions:
                position_data.append({
                    'symbol': pos.symbol,
                    'shares': float(pos.qty),
                    'avg_cost': float(pos.avg_entry_price),
                    'current_price': float(pos.current_price or pos.avg_entry_price),
                    'market_value': float(pos.market_value),
                    'unrealized_pl': float(pos.unrealized_pl or 0),
                    'unrealized_plpc': float(pos.unrealized_plpc or 0),
                    'side': str(pos.side)
                })
            
            return position_data
            
        except Exception as e:
            logger.error(f"❌ Error fetching positions: {e}")
            return self._get_sample_positions()
    
    def get_orders(self, status: str = 'all', limit: int = 50) -> List[Dict]:
        """Get recent orders from Alpaca"""
        if not self.alpaca_api:
            return self._get_sample_orders()
            
        try:
            # Use new alpaca-py API format
            from alpaca.trading.requests import GetOrdersRequest
            from alpaca.trading.enums import QueryOrderStatus
            
            # Convert status to new enum format
            if status == 'all':
                order_status = QueryOrderStatus.ALL
            elif status == 'open':
                order_status = QueryOrderStatus.OPEN
            elif status == 'closed':
                order_status = QueryOrderStatus.CLOSED
            else:
                order_status = QueryOrderStatus.ALL
                
            request = GetOrdersRequest(
                status=order_status,
                limit=limit
            )
            
            orders = self.alpaca_api.get_orders(filter=request)
            
            order_data = []
            for order in orders:
                order_data.append({
                    'symbol': order.symbol,
                    'side': str(order.side),
                    'qty': float(order.qty),
                    'order_type': str(order.order_type),
                    'time_in_force': str(order.time_in_force),
                    'status': str(order.status),
                    'filled_price': float(order.filled_avg_price) if order.filled_avg_price else None,
                    'submitted_at': order.submitted_at,
                    'filled_at': order.filled_at
                })
            
            return order_data
            
        except Exception as e:
            logger.error(f"❌ Error fetching orders: {e}")
            return self._get_sample_orders()
    
    def get_portfolio_history(self, period: str = '1Y') -> Dict:
        """Get portfolio performance history"""
        if not self.alpaca_api:
            return self._get_sample_portfolio_history()
            
        try:
            # Portfolio history might not be available in new API
            # Use account data and calculate basic history
            account = self.alpaca_api.get_account()
            
            # Return current portfolio value as a simple history point
            return {
                'timestamp': [datetime.now()],
                'equity': [float(account.portfolio_value)],
                'profit_loss': [0.0],  # Not available in new API
                'profit_loss_pct': [0.0],  # Calculate if needed
                'base_value': float(account.portfolio_value)
            }
            
        except Exception as e:
            logger.error(f"❌ Error fetching portfolio history: {e}")
            return self._get_sample_portfolio_history()
    
    def get_market_data(self, symbol: str, timeframe: str = '1Day', limit: int = 100) -> pd.DataFrame:
        """Get market data for a symbol"""
        try:
            # Use yfinance as backup/primary data source
            ticker = yf.Ticker(symbol)
            
            # Map timeframe
            period_map = {
                '1Min': '1d',
                '5Min': '5d', 
                '1Hour': '1mo',
                '1Day': '1y'
            }
            
            interval_map = {
                '1Min': '1m',
                '5Min': '5m',
                '1Hour': '1h', 
                '1Day': '1d'
            }
            
            period = period_map.get(timeframe, '1y')
            interval = interval_map.get(timeframe, '1d')
            
            data = ticker.history(period=period, interval=interval)
            return data.tail(limit)
            
        except Exception as e:
            logger.error(f"❌ Error fetching market data for {symbol}: {e}")
            return pd.DataFrame()
    
    def _get_sample_account_data(self) -> Dict:
        """Sample account data for testing"""
        return {
            'account_value': 925715.60,
            'buying_power': 462857.80,
            'cash': 231428.90,
            'daily_pnl': 4628.58,
            'total_pnl': 125715.60,
            'account_blocked': False,
            'trading_blocked': False,
            'pattern_day_trader': False
        }
    
    def _get_sample_positions(self) -> List[Dict]:
        """Sample positions data for testing"""
        return [
            {
                'symbol': 'AAPL', 'shares': 25, 'avg_cost': 175.50, 
                'current_price': 178.25, 'market_value': 4456.25, 
                'unrealized_pl': 68.75, 'unrealized_plpc': 0.0157, 'side': 'long'
            },
            {
                'symbol': 'MSFT', 'shares': 15, 'avg_cost': 420.00, 
                'current_price': 425.75, 'market_value': 6386.25, 
                'unrealized_pl': 86.25, 'unrealized_plpc': 0.0137, 'side': 'long'
            },
            {
                'symbol': 'GOOGL', 'shares': 8, 'avg_cost': 141.75, 
                'current_price': 145.20, 'market_value': 1161.60, 
                'unrealized_pl': 27.60, 'unrealized_plpc': 0.0243, 'side': 'long'
            }
        ]
    
    def _get_sample_orders(self) -> List[Dict]:
        """Sample orders data for testing"""
        return [
            {
                'symbol': 'AAPL', 'side': 'buy', 'qty': 5, 'order_type': 'market',
                'time_in_force': 'day', 'status': 'filled', 'filled_price': 178.25,
                'submitted_at': datetime.now() - timedelta(hours=2),
                'filled_at': datetime.now() - timedelta(hours=2, minutes=1)
            },
            {
                'symbol': 'MSFT', 'side': 'sell', 'qty': 2, 'order_type': 'limit',
                'time_in_force': 'day', 'status': 'filled', 'filled_price': 425.75,
                'submitted_at': datetime.now() - timedelta(hours=1),
                'filled_at': datetime.now() - timedelta(hours=1, minutes=5)
            }
        ]
    
    def _get_sample_portfolio_history(self) -> Dict:
        """Sample portfolio history for testing"""
        import numpy as np
        
        # Generate 252 trading days of data
        days = 252
        base_value = 800000
        
        # Generate realistic returns
        np.random.seed(42)
        daily_returns = np.random.normal(0.0008, 0.02, days)
        
        values = [base_value]
        for ret in daily_returns:
            values.append(values[-1] * (1 + ret))
        
        timestamps = pd.date_range(
            start=datetime.now() - timedelta(days=days), 
            end=datetime.now(), 
            freq='B'  # Business days
        )[:len(values)]
        
        return {
            'timestamp': timestamps.tolist(),
            'equity': values,
            'profit_loss': [v - base_value for v in values],
            'profit_loss_pct': [(v - base_value) / base_value for v in values],
            'base_value': base_value
        }

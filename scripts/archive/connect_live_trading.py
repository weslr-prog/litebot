#!/usr/bin/env python3
"""
Connect LiteBotX to Live Trading
LIVE TRADING ENGINE - NO PAPER TRADING OPTIONS
Real money, real trades, real profits/losses
"""

import os
import sys
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

class LiveTradingEngine:
    """
    LIVE TRADING ENGINE - REAL MONEY EXECUTION
    NO PAPER TRADING - LIVE TRADES ONLY
    """
    
    def __init__(self):
        load_dotenv()
        
        # Initialize Alpaca client - LIVE TRADING (paper=False)
        self.client = TradingClient(
            os.getenv("APCA_API_KEY_ID"),
            os.getenv("APCA_API_SECRET_KEY"),
            paper=False  # LIVE TRADING - REAL MONEY
        )
        
        self.order_id_counter = 1
        logging.info("🔴 LIVE TRADING ENGINE INITIALIZED - REAL MONEY")
        logging.info("⚠️  ALL TRADES WILL USE REAL CAPITAL")
        logging.info("💰 NO PAPER TRADING - LIVE EXECUTION ONLY")
    
    def get_account_info(self):
        """Get current LIVE account information"""
        try:
            account = self.client.get_account()
            logging.info(f"📊 LIVE Account Status: {account.status}")
            logging.info(f"💰 LIVE Portfolio Value: ${float(account.portfolio_value):,.2f}")
            return {
                'portfolio_value': float(account.portfolio_value),
                'cash': float(account.cash),
                'buying_power': float(account.buying_power),
                'status': account.status
            }
        except Exception as e:
            logging.error(f"Failed to get LIVE account info: {e}")
            return None
    
    def get_positions(self):
        """Get current LIVE positions from Alpaca"""
        try:
            positions = self.client.get_all_positions()
            result = []
            
            for pos in positions:
                result.append({
                    'symbol': pos.symbol,
                    'qty': float(pos.qty),
                    'side': 'long' if float(pos.qty) > 0 else 'short',
                    'market_value': float(pos.market_value),
                    'cost_basis': float(pos.cost_basis),
                    'unrealized_pl': float(pos.unrealized_pl),
                    'unrealized_plpc': float(pos.unrealized_plpc),
                    'avg_entry_price': float(pos.avg_entry_price)
                })
            
            logging.info(f"📊 LIVE Positions: {len(result)} positions")
            return result
            
        except Exception as e:
            logging.error(f"Failed to get LIVE positions: {e}")
            return []

    def submit_order(self, symbol, quantity, side='buy', order_type='market'):
        """Submit LIVE order to Alpaca - REAL MONEY EXECUTION"""
        try:
            # CRITICAL WARNING LOG
            logging.warning(f"🔴 SUBMITTING LIVE ORDER: {symbol} {quantity} shares ({side})")
            logging.warning(f"💰 THIS IS REAL MONEY - NOT A SIMULATION")
            
            # Convert side to Alpaca enum
            alpaca_side = OrderSide.BUY if side.lower() == 'buy' else OrderSide.SELL
            
            # Create market order request
            market_order_data = MarketOrderRequest(
                symbol=symbol,
                qty=abs(quantity),
                side=alpaca_side,
                time_in_force=TimeInForce.DAY
            )
            
            # Submit LIVE order - REAL MONEY
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
            
            logging.warning(f"🔴 LIVE ORDER SUBMITTED: {symbol} {quantity} shares ({side})")
            logging.warning(f"💰 Order ID: {order.id} - STATUS: {order.status}")
            return result
            
        except Exception as e:
            logging.error(f"❌ FAILED TO SUBMIT LIVE ORDER {symbol}: {e}")
            return {
                'order_id': None,
                'symbol': symbol,
                'quantity': quantity,
                'side': side,
                'status': 'FAILED',
                'error': str(e)
            }

    def get_order_status(self, order_id):
        """Get LIVE order status"""
        try:
            order = self.client.get_order_by_id(order_id)
            return {
                'order_id': order.id,
                'status': order.status,
                'filled_qty': float(order.filled_qty) if order.filled_qty else 0,
                'filled_avg_price': float(order.filled_avg_price) if order.filled_avg_price else None
            }
        except Exception as e:
            logging.error(f"Failed to get LIVE order status {order_id}: {e}")
            return None

    def cancel_order(self, order_id):
        """Cancel LIVE order"""
        try:
            self.client.cancel_order_by_id(order_id)
            logging.info(f"✅ LIVE Order cancelled: {order_id}")
            return True
        except Exception as e:
            logging.error(f"❌ Failed to cancel LIVE order {order_id}: {e}")
            return False
            
    def get_market_data(self, symbol):
        """Get real-time market data for symbol"""
        # This would require market data subscription
        # For now return None, can be extended later
        return None


if __name__ == "__main__":
    print("🔴 LIVE TRADING ENGINE TEST - REAL MONEY")
    print("⚠️  WARNING: This will connect to your LIVE trading account")
    
    confirm = input("Type 'LIVE' to confirm you want to test LIVE trading: ")
    if confirm != "LIVE":
        print("❌ Test cancelled - LIVE trading not confirmed")
        sys.exit(1)
    
    try:
        # Initialize LIVE trading engine
        engine = LiveTradingEngine()
        
        # Test account connection
        account = engine.get_account_info()
        if account:
            print(f"✅ Connected to LIVE account")
            print(f"💰 Portfolio Value: ${account['portfolio_value']:,.2f}")
            print(f"💵 Cash: ${account['cash']:,.2f}")
            print(f"📊 Buying Power: ${account['buying_power']:,.2f}")
        else:
            print("❌ Failed to connect to LIVE account")
            
        # Test positions
        positions = engine.get_positions()
        print(f"📊 LIVE Positions: {len(positions)}")
        
        for pos in positions[:5]:  # Show first 5
            print(f"   {pos['symbol']}: {pos['qty']} shares, P&L: ${pos['unrealized_pl']:.2f}")
            
        print("✅ LIVE Trading Engine test complete")
        
    except Exception as e:
        print(f"❌ LIVE Trading Engine test failed: {e}")
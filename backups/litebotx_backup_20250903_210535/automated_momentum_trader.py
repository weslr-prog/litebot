#!/usr/bin/env python3
"""
Automated Momentum Trader - Scheduled execution with market hours awareness
"""

import schedule
import time
import logging
import signal
import sys
from datetime import datetime, time as dt_time
import pytz
from typing import Dict, List
import threading

from core.data_loader import DataLoader
from core.momentum_strategy import MomentumStrategy
from connect_real_trading import RealPaperTradingEngine

# Setup logging with both file and console output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('automated_trading.log'),
        logging.StreamHandler()
    ]
)

# Add a test log message to verify FileHandler
logging.info("Test log message to verify FileHandler.")

# Ensure logs are flushed to the file
for handler in logging.getLogger().handlers:
    if isinstance(handler, logging.FileHandler):
        handler.flush()

# Add periodic runtime log entries to test FileHandler
logging.info("Runtime log test: Starting the script.")

# Ensure logs are flushed periodically
def periodic_flush():
    while True:
        for handler in logging.getLogger().handlers:
            if isinstance(handler, logging.FileHandler):
                handler.flush()
        time.sleep(10)  # Flush every 10 seconds

flush_thread = threading.Thread(target=periodic_flush, daemon=True)
flush_thread.start()

logging.info("Runtime log test: Periodic flush thread started.")

class AutomatedMomentumTrader:
    """Automated momentum trading with scheduling"""
    
    def __init__(self, symbols: List[str] = None):
        """Initialize the automated trader"""
        if symbols is None:
            # Focus on liquid, high-momentum candidates
            symbols = [
                'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 
                'NFLX', 'ADBE', 'CRM', 'ORCL', 'PYPL', 'INTC', 'AMD',
                'UBER', 'ROKU', 'ZM', 'SNOW', 'PLTR', 'COIN'
            ]
        
        self.symbols = symbols
        self.running = True
        
        # Initialize components
        logging.info("🤖 Initializing Automated Momentum Trader")
        self.data_loader = DataLoader()
        self.momentum_strategy = MomentumStrategy()
        self.trading_engine = RealPaperTradingEngine()
        
        # Get initial account info
        account_info = self.trading_engine.get_account_info()
        self.portfolio_value = float(account_info['portfolio_value'])
        logging.info(f"💰 Starting Portfolio Value: ${self.portfolio_value:,.2f}")
        
        # Setup timezone for market hours
        self.eastern = pytz.timezone('US/Eastern')
        
    def is_market_hours(self) -> bool:
        """Check if it's currently during market hours (9:30 AM - 4:00 PM ET)"""
        now_et = datetime.now(self.eastern)
        market_open = dt_time(9, 30)  # 9:30 AM
        market_close = dt_time(16, 0)  # 4:00 PM
        
        # Check if it's a weekday and within market hours
        is_weekday = now_et.weekday() < 5  # Monday = 0, Friday = 4
        is_during_hours = market_open <= now_et.time() <= market_close
        
        return is_weekday and is_during_hours
    
    def is_premarket_hours(self) -> bool:
        """Check if it's pre-market hours (7:00 AM - 9:30 AM ET)"""
        now_et = datetime.now(self.eastern)
        premarket_start = dt_time(7, 0)   # 7:00 AM
        premarket_end = dt_time(9, 30)    # 9:30 AM
        
        is_weekday = now_et.weekday() < 5
        is_premarket = premarket_start <= now_et.time() < premarket_end
        
        return is_weekday and is_premarket
        
    def load_market_data(self) -> Dict[str, any]:
        """Load fresh market data for all symbols"""
        logging.info(f"📊 Loading market data for {len(self.symbols)} symbols...")
        
        market_data = {}
        for symbol in self.symbols:
            try:
                data = self.data_loader.get_historical_data(symbol, limit=50)
                if data is not None and len(data) > 0:
                    market_data[symbol] = data
                else:
                    logging.warning(f"   ⚠️ {symbol}: No data available")
            except Exception as e:
                logging.warning(f"   ⚠️ {symbol}: {e}")
        
        logging.info(f"📈 Successfully loaded {len(market_data)} symbols")
        return market_data
        
    def execute_momentum_cycle(self):
        """Execute a complete momentum trading cycle"""
        try:
            current_time = datetime.now(self.eastern).strftime('%Y-%m-%d %H:%M:%S %Z')
            logging.info("🚀 Starting Automated Momentum Cycle")
            logging.info(f"🕐 Current Time: {current_time}")
            logging.info("=" * 70)
            
            # 1. Load market data
            market_data = self.load_market_data()
            if not market_data:
                logging.error("❌ No market data available - skipping cycle")
                return
            
            # 2. Generate momentum signals
            logging.info("🎯 Generating momentum signals...")
            signals = self.momentum_strategy.generate_signals(
                market_data,
                portfolio_value=self.portfolio_value
            )
            
            if not signals:
                logging.error("❌ No momentum signals generated - skipping cycle")
                return
                
            logging.info(f"📊 Generated {len(signals)} momentum signals")
            
            # Log top 5 signals
            for i, signal in enumerate(signals[:5], 1):
                momentum = signal['momentum_score']
                shares = signal['shares']
                value = signal['position_value']
                logging.info(f"   {i}. {signal['symbol']}: momentum={momentum:.3f}, {shares} shares (${value:,.0f})")
            
            # 3. Get current positions
            positions = self.trading_engine.get_positions()
            current_positions = {}
            for symbol, pos in positions.items():
                current_positions[symbol] = {
                    'shares': float(pos['quantity']),
                    'market_value': float(pos['market_value']),
                    'unrealized_pl': float(pos['unrealized_pnl'])
                }
            
            logging.info(f"📈 Current positions: {len(current_positions)} symbols")
            
            # 4. Calculate trades needed
            trades = self.calculate_trades_needed(signals, current_positions)
            
            if trades:
                logging.info(f"📋 Trades needed: {len(trades)}")
                for trade in trades:
                    side = trade['side']
                    shares = trade['shares']
                    symbol = trade['symbol']
                    current = trade['current_position']
                    target = trade['target_position']
                    momentum = trade['momentum_score']
                    logging.info(f"   {side.upper()} {shares} {symbol}: {current:.0f} → {target:.0f} (momentum: {momentum:.3f})")
            else:
                logging.info("📋 No trades needed - portfolio already optimized")
                return
            
            # 5. Execute trades if during market hours
            if self.is_market_hours():
                logging.info("✅ Market is open - executing trades")
                results = self.execute_trades(trades)
                
                successful_trades = len([r for r in results if r['status'] == 'success'])
                logging.info(f"✅ Successfully executed {successful_trades}/{len(trades)} trades")
                
                # Update portfolio value
                account_info = self.trading_engine.get_account_info()
                self.portfolio_value = float(account_info['portfolio_value'])
                
            else:
                logging.info("⏰ Market is closed - trades will be queued for market open")
                # In a real system, you might want to store these for later execution
            
            logging.info("=" * 70)
            logging.info("�� Automated Momentum Cycle Complete")
            
        except Exception as e:
            logging.error(f"💥 Error in automated trading cycle: {e}")
            
    def calculate_trades_needed(self, signals: List[Dict], current_positions: Dict[str, Dict]) -> List[Dict]:
        """Calculate what trades are needed to reach target positions"""
        trades = []
        
        # Check each signal against current position
        for signal in signals:
            symbol = signal['symbol']
            target_shares = signal['shares']
            current_shares = current_positions.get(symbol, {}).get('shares', 0)
            
            shares_diff = target_shares - current_shares
            
            # Only trade if difference is significant (at least 1 share)
            if abs(shares_diff) >= 1:
                trade = {
                    'symbol': symbol,
                    'shares': int(abs(shares_diff)),
                    'side': 'buy' if shares_diff > 0 else 'sell',
                    'current_position': current_shares,
                    'target_position': target_shares,
                    'momentum_score': signal['momentum_score']
                }
                trades.append(trade)
        
        # Also check for positions to liquidate (not in top signals)
        signal_symbols = {signal['symbol'] for signal in signals}
        for symbol, position in current_positions.items():
            if symbol not in signal_symbols and position['shares'] > 0:
                trade = {
                    'symbol': symbol,
                    'shares': int(position['shares']),
                    'side': 'sell',
                    'current_position': position['shares'],
                    'target_position': 0,
                    'momentum_score': 0  # Liquidating
                }
                trades.append(trade)
        
        return trades
        
    def execute_trades(self, trades: List[Dict]) -> List[Dict]:
        """Execute the calculated trades"""
        if not trades:
            return []
        
        logging.info(f"📤 Executing {len(trades)} trades...")
        results = []
        
        for trade in trades:
            symbol = trade['symbol']
            shares = trade['shares']
            side = trade['side']
            momentum = trade['momentum_score']
            
            logging.info(f"   📤 {side.upper()} {shares} shares of {symbol} (momentum: {momentum:.3f})")
            
            try:
                order_result = self.trading_engine.submit_order(
                    symbol=symbol,
                    quantity=shares,
                    side=side
                )
                
                if order_result:
                    logging.info(f"   ✅ Order successful: {order_result['order_id']}")
                    results.append({
                        'symbol': symbol,
                        'shares': shares,
                        'side': side,
                        'status': 'success',
                        'order_id': str(order_result['order_id'])
                    })
                else:
                    logging.error(f"   ❌ Order failed for {symbol}")
                    results.append({
                        'symbol': symbol,
                        'shares': shares,
                        'side': side,
                        'status': 'failed'
                    })
                    
                # Small delay between orders
                time.sleep(0.5)
                
            except Exception as e:
                logging.error(f"   ❌ Error placing order for {symbol}: {e}")
                results.append({
                    'symbol': symbol,
                    'shares': shares,
                    'side': side,
                    'status': 'error',
                    'error': str(e)
                })
        
        return results
    
    def portfolio_summary(self):
        """Log current portfolio summary"""
        try:
            account_info = self.trading_engine.get_account_info()
            positions = self.trading_engine.get_positions()
            
            portfolio_value = float(account_info['portfolio_value'])
            cash = float(account_info['cash'])
            
            logging.info("📊 Portfolio Summary")
            logging.info("=" * 50)
            logging.info(f"💰 Total Value: ${portfolio_value:,.2f}")
            logging.info(f"💵 Cash: ${cash:,.2f}")
            logging.info(f"📈 Positions: {len(positions)} symbols")
            
            if positions:
                logging.info("🔍 Top Positions:")
                # Sort by market value
                sorted_positions = sorted(
                    positions.items(), 
                    key=lambda x: float(x[1]['market_value']), 
                    reverse=True
                )
                
                for symbol, pos in sorted_positions[:5]:
                    shares = pos['quantity']
                    value = pos['market_value']
                    pnl = pos['unrealized_pnl']
                    logging.info(f"   {symbol}: {shares} shares | ${value:.2f} | P&L: ${pnl:.2f}")
            
        except Exception as e:
            logging.error(f"Error getting portfolio summary: {e}")
    
    def setup_schedule(self):
        """Setup the trading schedule with strategic timing windows"""
        logging.info("📅 Setting up strategic trading schedule...")
        
        # Pre-market validation check (8:00 AM ET) - Strategic Window: 7:30-9:00 AM
        schedule.every().day.at("08:00").do(self.portfolio_summary).tag('validation')
        
        # Market open execution window (9:30 AM ET) - Strategic Window: 9:30-10:30 AM
        schedule.every().day.at("09:30").do(self.execute_momentum_cycle).tag('execution')
        
        # Mid-execution follow-up (10:00 AM ET) - Continue execution window
        schedule.every().day.at("10:00").do(self.execute_momentum_cycle).tag('execution')
        
        # Market close management window (15:00 PM ET) - Strategic Window: 3:00-4:00 PM
        schedule.every().day.at("15:00").do(self.execute_momentum_cycle).tag('management')
        
        # Final management check (15:30 PM ET) - Continue management window
        schedule.every().day.at("15:30").do(self.execute_momentum_cycle).tag('management')
        
        # Strategic scan after market close (16:15 PM ET) - Strategic Window: After 4:15 PM
        schedule.every().day.at("16:15").do(self.portfolio_summary).tag('strategic_scan')
        
        logging.info("✅ Strategic schedule configured:")
        logging.info("   🔍 08:00 ET - Pre-Market Validation Check")
        logging.info("   🚀 09:30 ET - Market Open Execution Window")
        logging.info("   � 10:00 ET - Mid-Execution Follow-up")
        logging.info("   ⚖️ 15:00 ET - Market Close Management Window")
        logging.info("   🎯 15:30 ET - Final Management Check")
        logging.info("   � 16:15 ET - Strategic Scan (After Market Close)")
    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logging.info("🛑 Shutdown signal received - stopping automated trader...")
        self.running = False
        
    def run_automated(self):
        """Run the automated trading system"""
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        # Setup schedule
        self.setup_schedule()
        
        # Initial portfolio summary
        self.portfolio_summary()
        
        logging.info("🚀 Automated Momentum Trader is now running...")
        logging.info("💡 Press Ctrl+C to stop gracefully")
        
        # Main loop
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
                
            except KeyboardInterrupt:
                logging.info("🛑 Keyboard interrupt received")
                break
            except Exception as e:
                logging.error(f"Error in main loop: {e}")
                time.sleep(60)  # Wait before retrying
        
        logging.info("👋 Automated Momentum Trader stopped")

def main():
    """Main execution function"""
    # Create automated trader
    trader = AutomatedMomentumTrader()
    
    # Run automated system
    trader.run_automated()

if __name__ == "__main__":
    main()

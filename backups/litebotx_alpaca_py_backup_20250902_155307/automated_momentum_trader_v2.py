#!/usr/bin/env python3
"""
Automated Momentum Trader V2 - Enhanced with Risk-Adjusted Position Sizing
Combines momentum signals with volatility-based position sizing for optimal risk-adjusted returns
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
from core.enhanced_momentum_strategy import EnhancedMomentumStrategy
from core.risk_adjusted_sizing import VolatilityAdjustedSizer, PositionSizingConfig
from core.weekend_risk_manager import WeekendRiskManager
from connect_real_trading import RealPaperTradingEngine

# Setup logging with both file and console output
from logging.handlers import RotatingFileHandler

# Clear any existing handlers
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

# Create rotating file handler
file_handler = RotatingFileHandler(
    'automated_trading_v2.log', 
    maxBytes=10*1024*1024,  # 10MB per file
    backupCount=10  # Keep 10 backup files
)
file_handler.setLevel(logging.INFO)

# Create console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# Create formatter
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    handlers=[file_handler, console_handler],
    force=True
)

class AutomatedMomentumTraderV2:
    """Enhanced automated momentum trading with risk-adjusted position sizing"""
    
    def __init__(self, symbols: List[str] = None, alpha_vantage_key: str = None, use_enhanced_strategy: bool = True):
        """Initialize the enhanced automated trader"""
        if symbols is None:
            # Expanded universe for better momentum capture
            symbols = [
                'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 
                'NFLX', 'ADBE', 'CRM', 'ORCL', 'PYPL', 'INTC', 'AMD',
                'UBER', 'ROKU', 'ZM', 'SNOW', 'PLTR', 'COIN', 'SQ', 'SHOP',
                'DDOG', 'CRWD', 'OKTA', 'TWLO', 'NET', 'DOCU', 'PANW', 'MDB'
            ]
        
        self.symbols = symbols
        self.running = True
        
        # Initialize components
        logging.info("🚀 Initializing Enhanced Automated Momentum Trader V2")
        self.data_loader = DataLoader()
        
        # Initialize momentum strategy (enhanced or basic)
        self.use_enhanced_strategy = use_enhanced_strategy
        if use_enhanced_strategy and alpha_vantage_key:
            logging.info("🎯 Using Enhanced Multi-Sector Momentum Strategy")
            self.momentum_strategy = EnhancedMomentumStrategy(alpha_vantage_key)
        else:
            logging.info("📈 Using Basic Momentum Strategy")
            self.momentum_strategy = MomentumStrategy()
            
        self.trading_engine = RealPaperTradingEngine()
        
        # Initialize risk-adjusted position sizer
        risk_config = PositionSizingConfig(
            target_volatility=0.15,       # 15% target portfolio volatility
            max_position_weight=0.08,      # 8% max single position (more diversified)
            min_position_weight=0.01,      # 1% min position
            volatility_lookback=21,        # 21-day volatility calculation
            correlation_lookback=63,       # 63-day correlation analysis
            max_correlation=0.7,           # Max 70% correlation between positions
            cash_buffer=0.05,              # 5% cash buffer
            rebalance_threshold=0.02       # 2% rebalance threshold
        )
        self.risk_sizer = VolatilityAdjustedSizer(risk_config)
        
        # Initialize weekend risk manager
        weekend_config = {
            'max_weekend_exposure': 0.7,   # Max 70% exposure over weekend
            'high_vol_threshold': 0.4,     # Consider high if vol > 40%
            'momentum_threshold': 0.1,     # Strong momentum threshold
            'friday_hour_cutoff': 15,      # Stop new positions after 3 PM
        }
        self.weekend_risk = WeekendRiskManager(weekend_config)
        
        # Get initial account info
        account_info = self.trading_engine.get_account_info()
        self.portfolio_value = float(account_info['portfolio_value'])
        logging.info(f"💰 Starting Portfolio Value: ${self.portfolio_value:,.2f}")
        
        # Setup timezone for market hours
        self.eastern = pytz.timezone('US/Eastern')
        
        logging.info("✅ Enhanced system initialized with:")
        logging.info(f"   📊 Symbol Universe: {len(self.symbols)} stocks")
        logging.info(f"   🎯 Risk-Adjusted Sizing: Enabled")
        logging.info(f"   📈 Max Position Weight: {risk_config.max_position_weight:.0%}")
        logging.info(f"   🔄 Target Volatility: {risk_config.target_volatility:.0%}")
        
        # Add a test log message to verify FileHandler
        logging.info("Test log message to verify FileHandler.")

        # Debugging: Verify FileHandler initialization
        for handler in logging.getLogger().handlers:
            logging.info(f"Handler: {handler}")

        # Debugging: Test manual file writing
        try:
            with open('automated_trading_v2.log', 'a') as log_file:
                log_file.write("Manual test log entry\n")
            logging.info("Manual test log entry written successfully.")
        except Exception as e:
            logging.error(f"Error writing to log file manually: {e}")

        # Debugging: Force FileHandler to flush (don't close to keep logging active)
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
        
    def is_market_hours(self) -> bool:
        """Check if it's currently during market hours (9:30 AM - 4:00 PM ET)"""
        now_et = datetime.now(self.eastern)
        market_open = dt_time(9, 30)  # 9:30 AM
        market_close = dt_time(16, 0)  # 4:00 PM
        
        # Check if it's a weekday and within market hours
        is_weekday = now_et.weekday() < 5  # Monday = 0, Friday = 4
        is_during_hours = market_open <= now_et.time() <= market_close
        
        return is_weekday and is_during_hours
        
    def load_market_data(self) -> Dict[str, any]:
        """Load fresh market data for all symbols"""
        logging.info(f"📊 Loading market data for {len(self.symbols)} symbols...")
        
        market_data = {}
        success_count = 0
        
        for symbol in self.symbols:
            try:
                data = self.data_loader.get_historical_data(symbol, limit=100)  # More data for volatility calc
                if data is not None and len(data) > 50:  # Ensure sufficient data
                    market_data[symbol] = data
                    success_count += 1
                else:
                    logging.warning(f"   ⚠️ {symbol}: Insufficient data")
            except Exception as e:
                logging.warning(f"   ⚠️ {symbol}: {e}")
        
        logging.info(f"📈 Successfully loaded {success_count}/{len(self.symbols)} symbols")
        return market_data
        
    def execute_enhanced_momentum_cycle(self):
        """Execute enhanced momentum trading cycle with risk-adjusted sizing"""
        try:
            current_time = datetime.now(self.eastern).strftime('%Y-%m-%d %H:%M:%S %Z')
            logging.info("🚀 Starting Enhanced Momentum Trading Cycle (V2)")
            logging.info(f"🕐 Current Time: {current_time}")
            logging.info("=" * 70)
            
            # 1. Load market data
            market_data = self.load_market_data()
            if len(market_data) < 5:
                logging.error("❌ Insufficient market data - skipping cycle")
                return
            
            # 2. Generate momentum signals
            logging.info("🎯 Generating momentum signals...")
            if self.use_enhanced_strategy and hasattr(self.momentum_strategy, 'generate_enhanced_signals'):
                momentum_signals = self.momentum_strategy.generate_enhanced_signals(
                    market_data,
                    portfolio_value=self.portfolio_value
                )
            else:
                momentum_signals = self.momentum_strategy.generate_signals(
                    market_data,
                    portfolio_value=self.portfolio_value
                )
            
            if not momentum_signals:
                logging.error("❌ No momentum signals generated - skipping cycle")
                return
                
            logging.info(f"📊 Generated {len(momentum_signals)} momentum signals")
            
            # 3. Apply risk-adjusted position sizing
            logging.info("🎯 Applying risk-adjusted position sizing...")
            risk_adjusted_signals = self.risk_sizer.calculate_position_sizes(
                momentum_signals, 
                market_data, 
                self.portfolio_value
            )
            
            # 4. Apply Friday weekend risk filters
            current_time = datetime.now(self.eastern)
            risk_adjusted_signals = self.weekend_risk.apply_friday_filters(
                risk_adjusted_signals, 
                current_time
            )
            
            # Log top signals with risk adjustments
            logging.info("📈 Top risk-adjusted signals:")
            for i, signal in enumerate(risk_adjusted_signals[:8], 1):
                symbol = signal['symbol']
                shares = signal.get('shares', 0)
                value = signal.get('position_value', 0)
                weight = signal.get('weight', 0)
                volatility = signal.get('volatility', 0)
                momentum = signal.get('momentum_score', 0)
                logging.info(f"   {i}. {symbol}: {shares} shares | ${value:,.0f} | {weight:.1%} | vol:{volatility:.1%} | mom:{momentum:.3f}")
            
            # 4. Get current positions
            positions = self.trading_engine.get_positions()
            current_positions = {}
            for symbol, pos in positions.items():
                current_positions[symbol] = {
                    'shares': float(pos['quantity']),
                    'market_value': float(pos['market_value']),
                    'unrealized_pl': float(pos['unrealized_pnl'])
                }
            
            logging.info(f"📈 Current positions: {len(current_positions)} symbols")
            
            # 6. Check for Friday weekend risk reduction
            current_time = datetime.now(self.eastern)
            portfolio_data = {
                'portfolio_volatility': 0.15,  # You can calculate this from current positions
                'positions': current_positions,
                'max_position_weight': max([pos.get('market_value', 0) for pos in current_positions.values()] + [0]) / self.portfolio_value if current_positions else 0
            }
            
            should_reduce, target_exposure = self.weekend_risk.should_reduce_positions_friday(
                current_time, portfolio_data, market_data
            )
            
            if should_reduce:
                friday_adjustments = self.weekend_risk.get_friday_position_adjustments(
                    current_positions, target_exposure
                )
                if friday_adjustments:
                    logging.info(f"🗓️ Friday Risk Management: {len(friday_adjustments)} adjustments needed")
                    # Add Friday adjustments to trades
                    trades.extend([{
                        'symbol': adj['symbol'],
                        'shares': adj['shares'],
                        'side': adj['action'],
                        'current_position': current_positions.get(adj['symbol'], {}).get('shares', 0),
                        'target_position': current_positions.get(adj['symbol'], {}).get('shares', 0) - adj['shares'],
                        'risk_weight': 0,
                        'volatility': adj['priority'],
                        'friday_adjustment': True
                    } for adj in friday_adjustments])
            
            # 7. Calculate trades needed
            trades = self.calculate_risk_adjusted_trades(risk_adjusted_signals, current_positions)
            
            if trades:
                logging.info(f"📋 Risk-adjusted trades needed: {len(trades)}")
                for trade in trades[:10]:  # Show top 10 trades
                    side = trade['side']
                    shares = trade['shares']
                    symbol = trade['symbol']
                    current = trade['current_position']
                    target = trade['target_position']
                    risk_weight = trade.get('risk_weight', 0)
                    is_friday_adj = trade.get('friday_adjustment', False)
                    friday_tag = " [FRIDAY]" if is_friday_adj else ""
                    logging.info(f"   {side.upper()} {shares} {symbol}: {current:.0f} → {target:.0f} (risk wt: {risk_weight:.1%}){friday_tag}")
            else:
                logging.info("📋 No trades needed - portfolio already optimized")
                return
            
            # 8. Execute trades if during market hours
            if self.is_market_hours():
                logging.info("✅ Market is open - executing risk-adjusted trades")
                results = self.execute_trades(trades)
                
                successful_trades = len([r for r in results if r['status'] == 'success'])
                logging.info(f"✅ Successfully executed {successful_trades}/{len(trades)} trades")
                
                # Update portfolio value
                account_info = self.trading_engine.get_account_info()
                self.portfolio_value = float(account_info['portfolio_value'])
                
                # Calculate and log portfolio risk metrics
                self.log_portfolio_risk_metrics(current_positions, market_data)
                
            else:
                logging.info("⏰ Market is closed - trades queued for market open")
            
            logging.info("=" * 70)
            logging.info("🏁 Enhanced Momentum Cycle Complete")
            
        except Exception as e:
            logging.error(f"💥 Error in enhanced trading cycle: {e}")
            
    def calculate_risk_adjusted_trades(self, signals: List[Dict], current_positions: Dict[str, Dict]) -> List[Dict]:
        """Calculate trades needed with risk-adjusted position sizes"""
        trades = []
        
        # Check each signal against current position
        for signal in signals:
            symbol = signal['symbol']
            target_shares = signal.get('shares', 0)
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
                    'momentum_score': signal.get('momentum_score', 0),
                    'risk_weight': signal.get('weight', 0),
                    'volatility': signal.get('volatility', 0)
                }
                trades.append(trade)
        
        # Also check for positions to liquidate (not in signals)
        signal_symbols = {signal['symbol'] for signal in signals}
        for symbol, position in current_positions.items():
            if symbol not in signal_symbols and position['shares'] > 0:
                trade = {
                    'symbol': symbol,
                    'shares': int(position['shares']),
                    'side': 'sell',
                    'current_position': position['shares'],
                    'target_position': 0,
                    'momentum_score': 0,  # Liquidating
                    'risk_weight': 0,
                    'volatility': 0
                }
                trades.append(trade)
        
        return trades
        
    def execute_trades(self, trades: List[Dict]) -> List[Dict]:
        """Execute the calculated trades"""
        if not trades:
            return []
        
        logging.info(f"📤 Executing {len(trades)} risk-adjusted trades...")
        results = []
        
        for trade in trades:
            symbol = trade['symbol']
            shares = trade['shares']
            side = trade['side']
            risk_weight = trade.get('risk_weight', 0)
            
            logging.info(f"   📤 {side.upper()} {shares} shares of {symbol} (risk wt: {risk_weight:.1%})")
            
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
    
    def log_portfolio_risk_metrics(self, positions: Dict[str, Dict], market_data: Dict[str, any]):
        """Log current portfolio risk metrics"""
        try:
            risk_metrics = self.risk_sizer.get_portfolio_risk_metrics(positions, market_data)
            
            if risk_metrics:
                logging.info("📊 Portfolio Risk Metrics:")
                logging.info(f"   🎯 Portfolio Volatility: {risk_metrics.get('portfolio_volatility', 0):.1%}")
                logging.info(f"   📈 Max Position Weight: {risk_metrics.get('max_position_weight', 0):.1%}")
                logging.info(f"   🔢 Number of Positions: {risk_metrics.get('num_positions', 0)}")
                logging.info(f"   📊 Concentration Index: {risk_metrics.get('concentration_index', 0):.3f}")
                logging.info(f"   📉 Avg Position Vol: {risk_metrics.get('average_position_volatility', 0):.1%}")
                
        except Exception as e:
            logging.error(f"❌ Error calculating risk metrics: {e}")
    
    def friday_weekend_risk_check(self):
        """Special Friday-only risk management check before weekend"""
        try:
            current_time = datetime.now(self.eastern)
            
            # Only run on Fridays
            if current_time.weekday() != 4:
                return
            
            logging.info("🗓️ Starting Friday Weekend Risk Assessment")
            logging.info("=" * 60)
            
            # Get current positions
            positions = self.trading_engine.get_positions()
            current_positions = {}
            for symbol, pos in positions.items():
                current_positions[symbol] = {
                    'shares': float(pos['quantity']),
                    'market_value': float(pos['market_value']),
                    'unrealized_pl': float(pos['unrealized_pnl']),
                    'volatility': 0.25  # Default, would be better to get actual vol
                }
            
            # Prepare portfolio data
            portfolio_data = {
                'portfolio_volatility': 0.15,  # Calculate from actual positions
                'positions': current_positions,
                'max_position_weight': max([pos.get('market_value', 0) for pos in current_positions.values()] + [0]) / self.portfolio_value if current_positions else 0
            }
            
            # Check if we should reduce positions
            should_reduce, target_exposure = self.weekend_risk.should_reduce_positions_friday(
                current_time, portfolio_data, {}
            )
            
            if should_reduce:
                logging.info(f"⚠️ Weekend risk detected - reducing exposure to {target_exposure:.0%}")
                
                # Get Friday adjustments
                friday_adjustments = self.weekend_risk.get_friday_position_adjustments(
                    current_positions, target_exposure
                )
                
                if friday_adjustments and self.is_market_hours():
                    logging.info(f"📤 Executing {len(friday_adjustments)} Friday risk adjustments...")
                    
                    # Execute Friday risk adjustments
                    for adj in friday_adjustments:
                        symbol = adj['symbol']
                        shares = adj['shares']
                        logging.info(f"   📤 SELL {shares} shares of {symbol} (weekend risk)")
                        
                        try:
                            order_result = self.trading_engine.submit_order(
                                symbol=symbol,
                                quantity=shares,
                                side='sell'
                            )
                            
                            if order_result:
                                logging.info(f"   ✅ Friday adjustment successful: {order_result['order_id']}")
                            else:
                                logging.error(f"   ❌ Friday adjustment failed for {symbol}")
                                
                            time.sleep(0.5)  # Rate limiting
                            
                        except Exception as e:
                            logging.error(f"   ❌ Error executing Friday adjustment for {symbol}: {e}")
                
                elif not self.is_market_hours():
                    logging.info("⏰ Market closed - Friday adjustments would be queued for Monday")
                else:
                    logging.info("✅ No Friday adjustments needed")
            else:
                logging.info("✅ Low weekend risk - maintaining current positions")
            
            logging.info("=" * 60)
            logging.info("🏁 Friday Weekend Risk Assessment Complete")
            
        except Exception as e:
            logging.error(f"💥 Error in Friday weekend risk check: {e}")
    
    def portfolio_summary(self):
        """Enhanced portfolio summary with risk metrics"""
        try:
            account_info = self.trading_engine.get_account_info()
            positions = self.trading_engine.get_positions()
            
            portfolio_value = float(account_info['portfolio_value'])
            cash = float(account_info['cash'])
            
            logging.info("📊 Enhanced Portfolio Summary")
            logging.info("=" * 50)
            logging.info(f"💰 Total Value: ${portfolio_value:,.2f}")
            logging.info(f"💵 Cash: ${cash:,.2f} ({cash/portfolio_value:.1%})")
            logging.info(f"📈 Positions: {len(positions)} symbols")
            
            if positions:
                logging.info("🔍 Top Positions (by value):")
                # Sort by market value
                sorted_positions = sorted(
                    positions.items(), 
                    key=lambda x: float(x[1]['market_value']), 
                    reverse=True
                )
                
                for symbol, pos in sorted_positions[:8]:  # Top 8 positions
                    shares = pos['quantity']
                    value = pos['market_value']
                    pnl = pos['unrealized_pnl']
                    weight = float(value) / portfolio_value
                    logging.info(f"   {symbol}: {shares} shares | ${value:.0f} | {weight:.1%} | P&L: ${pnl:.0f}")
            
        except Exception as e:
            logging.error(f"Error getting enhanced portfolio summary: {e}")
    
    def setup_schedule(self):
        """Setup the enhanced trading schedule"""
        logging.info("📅 Setting up enhanced trading schedule...")
        
        # Pre-market analysis (7:30 AM ET)
        schedule.every().day.at("07:30").do(self.portfolio_summary).tag('summary')
        
        # Market open momentum check (9:45 AM ET)
        schedule.every().day.at("09:45").do(self.execute_enhanced_momentum_cycle).tag('trading')
        
        # Mid-morning rebalance (11:00 AM ET)
        schedule.every().day.at("11:00").do(self.execute_enhanced_momentum_cycle).tag('trading')
        
        # Lunch time check (1:00 PM ET)
        schedule.every().day.at("13:00").do(self.execute_enhanced_momentum_cycle).tag('trading')
        
        # End of day rebalance (3:30 PM ET)
        schedule.every().day.at("15:30").do(self.execute_enhanced_momentum_cycle).tag('trading')
        
        # Friday weekend risk check (3:45 PM ET) - Special Friday-only check
        schedule.every().friday.at("15:45").do(self.friday_weekend_risk_check).tag('friday_risk')
        
        # After hours summary (4:30 PM ET)
        schedule.every().day.at("16:30").do(self.portfolio_summary).tag('summary')
        
        logging.info("✅ Enhanced schedule configured:")
        logging.info("   📊 07:30 ET - Portfolio Summary")
        logging.info("   🚀 09:45 ET - Risk-Adjusted Momentum Check")
        logging.info("   🔄 11:00 ET - Mid-Morning Rebalance")
        logging.info("   🍽️ 13:00 ET - Lunch Time Check")
        logging.info("   📈 15:30 ET - End of Day Rebalance")
        logging.info("   �️ 15:45 ET - Friday Weekend Risk Check (Fridays only)")
        logging.info("   �📊 16:30 ET - After Hours Summary")
        
    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logging.info("🛑 Shutdown signal received - stopping enhanced trader...")
        self.running = False
        
    def run_automated(self):
        """Run the enhanced automated trading system"""
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        # Setup schedule
        self.setup_schedule()
        
        # Initial portfolio summary
        self.portfolio_summary()
        
        logging.info("🚀 Enhanced Automated Momentum Trader V2 is now running...")
        logging.info("💡 Press Ctrl+C to stop gracefully")
        
        # Main loop
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
                
            except KeyboardInterrupt:
                logging.info("�� Keyboard interrupt received")
                break
            except Exception as e:
                logging.error(f"Error in main loop: {e}")
                time.sleep(60)  # Wait before retrying
        
        logging.info("👋 Enhanced Automated Momentum Trader V2 stopped")

def main():
    """Main execution function"""
    # Alpha Vantage API key - replace with your actual key
    ALPHA_VANTAGE_KEY = "O8JA27H3XK5E3NAU"  # User provided key
    
    # Create enhanced automated trader with multi-sector analysis
    trader = AutomatedMomentumTraderV2(
        alpha_vantage_key=ALPHA_VANTAGE_KEY,
        use_enhanced_strategy=True
    )
    
    # Run automated system
    trader.run_automated()

if __name__ == "__main__":
    main()

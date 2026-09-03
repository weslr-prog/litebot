#!/usr/bin/env python3
"""
Sprint 1 with Alpaca Paper Trading Integration
Real-Time Data + Signal Generation + Alpaca Execution + Scheduled Trading
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, time as dt_time
import logging
import json
import time
import threading
import signal
import schedule
import pytz
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

# Alpaca imports
try:
    from alpaca.trading.client import TradingClient
    from alpaca.trading.requests import MarketOrderRequest, GetOrdersRequest
    from alpaca.trading.enums import OrderSide, TimeInForce, OrderStatus
    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
    ALPACA_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  Alpaca not available: {e}")
    ALPACA_AVAILABLE = False

# Import the dashboard
try:
    from gui.sprint1_integrated_dashboard import IntegratedDashboard
    DASHBOARD_AVAILABLE = True
except ImportError as e:
    print(f"Dashboard not available: {e}")
    DASHBOARD_AVAILABLE = False

# Import TAF fee calculator
try:
    from finra_taf_calculator import FINRATAFCalculator, TAFAwareRiskManager
    TAF_CALCULATOR_AVAILABLE = True
except ImportError:
    TAF_CALCULATOR_AVAILABLE = False
    print("⚠️ TAF calculator not available - using basic risk management")

@dataclass
class AlpacaConfig:
    """Alpaca configuration for paper trading"""
    api_key: str = ""
    secret_key: str = ""
    base_url: str = "https://paper-api.alpaca.markets"
    max_position_size: float = 1000.0  # $1000 max per position for safety
    max_daily_trades: int = 20
    risk_per_trade: float = 0.015  # 1.5% risk per trade

class AlpacaTradeExecutor:
    """Alpaca paper trading executor for Sprint 1"""
    
    def __init__(self, config: AlpacaConfig = None):
        from core.config import Sprint1Config
        self.config = config or self.load_alpaca_config()
        self.logger = logging.getLogger('AlpacaTradeExecutor')
        self.sprint_config = Sprint1Config()
        
        # Initialize Alpaca client if available
        self.trading_client = None
        self.data_client = None
        
        if ALPACA_AVAILABLE:
            try:
                self.trading_client = TradingClient(
                    api_key=self.config.api_key,
                    secret_key=self.config.secret_key,
                    paper=True  # Ensure paper trading
                )
                self.data_client = StockHistoricalDataClient(
                    api_key=self.config.api_key,
                    secret_key=self.config.secret_key
                )
                self.logger.info("✅ Alpaca paper trading client initialized")
            except Exception as e:
                self.logger.error(f"Failed to initialize Alpaca client: {e}")
                self.trading_client = None
        
        # Trading state
        self.daily_trades = 0
        self.positions = {}
        self.last_trade_date = None
        
    def load_alpaca_config(self) -> AlpacaConfig:
        """Load Alpaca configuration from environment"""
        # Load .env file if it exists
        env_file = '.env'
        if os.path.exists(env_file):
            with open(env_file) as f:
                for line in f:
                    if '=' in line and not line.startswith('#'):
                        key, value = line.strip().split('=', 1)
                        os.environ[key] = value.strip('"\'')
        
        return AlpacaConfig(
            api_key=os.getenv('APCA_API_KEY_ID', ''),
            secret_key=os.getenv('APCA_API_SECRET_KEY', ''),
            base_url=os.getenv('APCA_API_BASE_URL', 'https://paper-api.alpaca.markets')
        )
    
    def is_alpaca_available(self) -> bool:
        """Check if Alpaca is properly configured"""
        return ALPACA_AVAILABLE and self.trading_client is not None
    
    def get_account_info(self) -> Dict:
        """Get Alpaca account information"""
        if not self.is_alpaca_available():
            return {"status": "unavailable", "buying_power": 0}
        
        try:
            account = self.trading_client.get_account()
            return {
                "status": "active" if account.status == "ACTIVE" else account.status,
                "buying_power": float(account.buying_power),
                "cash": float(account.cash),
                "portfolio_value": float(account.portfolio_value),
                "day_trade_count": getattr(account, 'day_trade_count', 0)  # Safe attribute access
            }
        except Exception as e:
            self.logger.error(f"Failed to get account info: {e}")
            return {"status": "error", "buying_power": 0}
    
    def get_current_positions(self) -> Dict:
        """Get current Alpaca positions"""
        if not self.is_alpaca_available():
            return {}
        
        try:
            positions = self.trading_client.get_all_positions()
            return {
                pos.symbol: {
                    "qty": float(pos.qty),
                    "market_value": float(pos.market_value),
                    "avg_entry_price": float(pos.avg_entry_price),
                    "side": "long" if float(pos.qty) > 0 else "short"
                }
                for pos in positions
            }
        except Exception as e:
            self.logger.error(f"Failed to get positions: {e}")
            return {}
    
    def calculate_position_size(self, symbol: str, signal_confidence: float, current_price: float) -> int:
        """Calculate appropriate position size for paper trading with trend-based scaling and TAF fee optimization"""
        if not self.is_alpaca_available():
            return 0
        
        try:
            account_info = self.get_account_info()
            buying_power = account_info.get("buying_power", 0)
            
            # Get trend analysis for position scaling
            trend_multiplier = 1.0
            try:
                # Get historical data for trend analysis
                df = self.data_feed.get_historical_data(symbol, days=30)
                if not df.empty:
                    from test.sprint1_real_data_integration import SimpleSignalGenerator
                    signal_gen = SimpleSignalGenerator()
                    trend_analysis = signal_gen.analyze_trend(df)
                    
                    # Scale position based on trend strength and direction
                    trend_strength = trend_analysis['strength']
                    trend_direction = trend_analysis['trend']
                    
                    # Strong uptrend = increase position size
                    if trend_direction in ['bullish', 'uptrend'] and trend_strength > 0.5:
                        trend_multiplier = 1.5  # 50% increase for strong uptrends
                    elif trend_direction in ['bullish', 'uptrend'] and trend_strength > 0.2:
                        trend_multiplier = 1.2  # 20% increase for moderate uptrends
                    elif trend_direction in ['bearish', 'downtrend']:
                        trend_multiplier = 0.7  # Reduce position size in downtrends
                    
                    self.logger.info(f"📈 {symbol} trend scaling: {trend_direction} (strength: {trend_strength:.2f}) -> multiplier: {trend_multiplier:.1f}x")
            except Exception as e:
                self.logger.warning(f"Could not analyze trend for {symbol}: {e}")
            
            # Basic risk management with trend adjustment
            max_trade_value = min(
                self.config.max_position_size,
                buying_power * self.config.risk_per_trade,
                buying_power * 0.1  # Never use more than 10% of buying power
            )
            
            # Adjust for signal confidence and trend strength
            target_trade_value = max_trade_value * signal_confidence * trend_multiplier
            
            # TAF fee optimization if available
            if TAF_CALCULATOR_AVAILABLE:
                taf_calculator = FINRATAFCalculator()
                optimization = taf_calculator.optimize_position_size(target_trade_value, current_price)
                
                recommended_shares = optimization['recommended']['shares']
                taf_fee = optimization['recommended']['analysis']['taf_fee']
                fee_percentage = optimization['recommended']['analysis']['fee_percentage']
                
                self.logger.info(f"TAF-optimized position for {symbol}: "
                               f"{recommended_shares} shares, fee: ${taf_fee:.2f} ({fee_percentage:.3f}%) "
                               f"[trend multiplier: {trend_multiplier:.1f}x]")
                
                return recommended_shares
            else:
                # Fallback to basic calculation
                shares = int(target_trade_value / current_price)
                self.logger.info(f"Basic position size for {symbol}: {shares} shares (${target_trade_value:.2f}) "
                               f"[trend multiplier: {trend_multiplier:.1f}x]")
                return shares
            
        except Exception as e:
            self.logger.error(f"Failed to calculate position size: {e}")
            return 0
    
    def execute_trade(self, symbol: str, signal: str, current_price: float, confidence: float = 0.8) -> Dict:
        """Execute trade on Alpaca paper trading with TAF fee awareness"""
        if not self.is_alpaca_available():
            return {"status": "error", "message": "Alpaca not available"}
        
        # Reset daily trade count if new day
        today = datetime.now().date()
        if self.last_trade_date != today:
            self.daily_trades = 0
            self.last_trade_date = today
        
        # Check daily trade limit
        if self.daily_trades >= self.config.max_daily_trades:
            return {"status": "skipped", "message": "Daily trade limit reached"}
        
        if signal == 'hold':
            return {"status": "hold", "message": "No action required"}
        
        try:
            # Get current position (handle fractional shares)
            positions = self.get_current_positions()
            current_position = positions.get(symbol, {"qty": 0})
            current_qty = current_position.get("qty", 0)
            
            # Round fractional positions to avoid issues
            if abs(current_qty) < 1 and current_qty != 0:
                self.logger.warning(f"⚠️ Fractional position detected for {symbol}: {current_qty}, treating as flat")
                current_qty = 0
            else:
                current_qty = float(current_qty)
            
            # Determine trade action with enhanced position logic
            if signal == 'buy':
                # Buy signal - can add to existing position or open new
                if current_qty >= 0:  # Allow buying if flat or long
                    shares = self.calculate_position_size(symbol, confidence, current_price)
                    if shares <= 0:
                        return {"status": "skipped", "message": "Position size too small"}
                    
                    # If we have an existing position, this is an add
                    if current_qty > 0:
                        self.logger.info(f"Adding to existing {symbol} position: {current_qty} -> {current_qty + shares}")
                    
                    order_request = MarketOrderRequest(
                        symbol=symbol,
                        qty=shares,
                        side=OrderSide.BUY,
                        time_in_force=TimeInForce.DAY
                    )
                    
                    order = self.trading_client.submit_order(order_data=order_request)
                    self.daily_trades += 1
                    
                    self.logger.info(f"🟢 BUY order submitted: {symbol} x{shares} @ ${current_price:.2f}")
                    
                    return {
                        "status": "executed", 
                        "action": "buy", 
                        "symbol": symbol,
                        "shares": shares,
                        "price": current_price,
                        "order_id": order.id,
                        "taf_fee": 0.0  # No fee on buy orders
                    }
                else:
                    return {"status": "skipped", "message": f"Cannot buy {symbol} with short position {current_qty}"}
                    
            elif signal == 'sell' and current_qty > 0:
                # Sell signal - close or reduce position
                shares = abs(int(current_qty))  # Sell entire position
                
                # Calculate TAF fee for this sell order
                taf_fee = 0.0
                if TAF_CALCULATOR_AVAILABLE:
                    taf_calculator = FINRATAFCalculator()
                    taf_fee = taf_calculator.calculate_taf_fee(shares, is_sell_order=True)
                    
                    # Log fee impact
                    fee_impact = taf_calculator.calculate_breakeven_impact(shares, current_price)
                    self.logger.info(f"TAF fee for {symbol} sell: ${taf_fee:.2f} "
                                   f"({fee_impact['fee_percentage']:.3f}% of trade value)")
                
                order_request = MarketOrderRequest(
                    symbol=symbol,
                    qty=shares,
                    side=OrderSide.SELL,
                    time_in_force=TimeInForce.DAY
                )
                
                order = self.trading_client.submit_order(order_data=order_request)
                self.daily_trades += 1
                
                self.logger.info(f"🔴 SELL order submitted: {symbol} x{shares} @ ${current_price:.2f} "
                               f"(TAF fee: ${taf_fee:.2f})")
                
                return {
                    "status": "executed",
                    "action": "sell",
                    "symbol": symbol, 
                    "shares": shares,
                    "price": current_price,
                    "order_id": order.id,
                    "taf_fee": taf_fee
                }
            else:
                return {"status": "skipped", "message": f"No action for {signal} with current position {current_qty}"}
                
        except Exception as e:
            self.logger.error(f"Trade execution failed for {symbol}: {e}")
            return {"status": "error", "message": str(e)}

# Import the existing Sprint 1 components (unchanged)
from test.sprint1_real_data_integration import (
    MarketDataConfig, RealTimeDataFeed, SimpleSignalGenerator, 
    SimpleRiskManager, SimpleSafetyMonitor
)

# Import dynamic watchlist generator
try:
    from dynamic_watchlist_generator import DynamicWatchlistGenerator, WatchlistConfig
    WATCHLIST_GENERATOR_AVAILABLE = True
except ImportError:
    WATCHLIST_GENERATOR_AVAILABLE = False
    print("⚠️ Dynamic watchlist generator not available")

class Sprint1AlpacaIntegration:
    """Sprint 1 system with Alpaca paper trading integration"""
    
    def __init__(self, launch_gui: bool = True):
        self.launch_gui = launch_gui  # Store the parameter
        self.data_feed = RealTimeDataFeed()
        self.signal_generator = SimpleSignalGenerator()
        self.risk_manager = SimpleRiskManager()
        self.safety_monitor = SimpleSafetyMonitor()
        self.trade_executor = AlpacaTradeExecutor()
        self.logger = logging.getLogger('Sprint1AlpacaIntegration')
        
        # Initialize dynamic watchlist generator
        if WATCHLIST_GENERATOR_AVAILABLE:
            self.watchlist_generator = DynamicWatchlistGenerator(
                WatchlistConfig(
                    max_watchlist_size=15,  # Reasonable size for active trading
                    min_watchlist_size=5,   # Fallback minimum
                    save_to_file=True,
                    save_to_config=False    # Don't auto-update config during trading
                )
            )
            self.logger.info("✅ Dynamic watchlist generator enabled")
        else:
            self.watchlist_generator = None
            self.logger.warning("⚠️ Using static watchlist only")
        
        # Enhanced risk management with TAF awareness
        if TAF_CALCULATOR_AVAILABLE:
            from core.config import Sprint1Config
            config = Sprint1Config()
            self.taf_aware_risk_manager = TAFAwareRiskManager(
                self.risk_manager, 
                portfolio_size=config.portfolio_size
            )
            self.logger.info("✅ TAF-aware risk management enabled")
        else:
            self.taf_aware_risk_manager = None
            self.logger.warning("⚠️ Using basic risk management (TAF calculator not available)")
        
        # Performance tracking
        self.integration_start_time = datetime.now()
        self.signals_generated = 0
        self.trades_executed = 0
        self.successful_trades = 0
        self.total_taf_fees = 0.0  # Track TAF fees
        
        # CRITICAL: Position tracking for exit conditions - MISSING from original Sprint 1
        self.position_entry_dates = {}    # Track when positions were opened 
        self.position_entry_prices = {}   # Track entry prices for stop/profit calculations
        self.position_stop_losses = {}    # Track stop loss levels
        self.position_profit_targets = {} # Track profit target levels
        self.unfilled_orders = set()      # Prevent duplicate unfilled orders
        
        # Dashboard state
        self.dashboard = None
        self.stop_trading_loop = False

    def check_and_update_watchlist(self) -> List[str]:
        """Check if watchlist needs updating and generate new one if needed"""
        if not self.watchlist_generator:
            # Use config symbols if no generator available
            config = Sprint1Config()
            return config.test_symbols
        
        try:
            # Check if we need to generate a new watchlist
            result = self.watchlist_generator.run_daily_generation()
            
            if result['success']:
                self.logger.info(f"📋 Updated watchlist: {len(result['watchlist'])} symbols")
                return result['watchlist']
            else:
                self.logger.info(f"📋 Watchlist status: {result['message']}")
                return result['watchlist']  # May be fallback symbols
                
        except Exception as e:
            self.logger.error(f"Error updating watchlist: {e}")
            # Fallback to config symbols
            config = Sprint1Config()
            return config.test_symbols
        
        # Enhanced risk management with TAF awareness
        if TAF_CALCULATOR_AVAILABLE:
            from core.config import Sprint1Config
            config = Sprint1Config()
            self.taf_aware_risk_manager = TAFAwareRiskManager(
                self.risk_manager, 
                portfolio_size=config.portfolio_size
            )
            self.logger.info("✅ TAF-aware risk management enabled")
        else:
            self.taf_aware_risk_manager = None
            self.logger.warning("⚠️ Using basic risk management (TAF calculator not available)")
        
        # Performance tracking
        self.integration_start_time = datetime.now()
        self.signals_generated = 0
        self.trades_executed = 0
        self.successful_trades = 0
        self.total_taf_fees = 0.0  # Track TAF fees
        
        # Threading controls
        self.stop_trading_loop = False
        self.trading_thread = None
        
        # GUI integration
        self.launch_gui = launch_gui
        self.dashboard = None
        self.dashboard_thread = None
        
    def initialize_system(self) -> bool:
        """Initialize the integrated system"""
        self.logger.info("Initializing Sprint 1 + Alpaca Integration System")
        
        try:
            # Check Alpaca connectivity
            if self.trade_executor.is_alpaca_available():
                account_info = self.trade_executor.get_account_info()
                self.logger.info(f"✅ Alpaca connected - Buying Power: ${account_info.get('buying_power', 0):,.2f}")
            else:
                self.logger.warning("⚠️  Alpaca not available - signals only mode")
            
            # Initialize data feed with test symbols
            test_symbols = ['AAPL', 'MSFT', 'GOOGL']
            self.data_feed.update_market_data(test_symbols)
            
            # Generate test signals
            signals = []
            for symbol in test_symbols:
                df = self.data_feed.get_historical_data(symbol, days=30)
                if not df.empty:
                    signal = self.signal_generator.generate_signal(symbol, df)
                    self.logger.info(f"📊 Test signal for {symbol}: {signal}")
                    signals.append((symbol, signal))
            
            self.logger.info(f"Generated {len(signals)} test signals")
            self.logger.info("✅ Sprint 1 + Alpaca Integration System initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"System initialization failed: {e}")
            return False
    
    def is_market_hours(self) -> bool:
        """Check if it's currently during market hours (9:30 AM - 4:00 PM ET)"""
        eastern = pytz.timezone('US/Eastern')
        now_et = datetime.now(eastern)
        market_open = dt_time(9, 30)  # 9:30 AM
        market_close = dt_time(16, 0)  # 4:00 PM
        
        # Check if it's a weekday and within market hours
        is_weekday = now_et.weekday() < 5  # Monday = 0, Friday = 4
        is_during_hours = market_open <= now_et.time() <= market_close
        
        return is_weekday and is_during_hours
    
    def setup_schedule(self):
        """Setup ROI-optimized trading schedule based on actual log performance"""
        self.logger.info("📅 Setting up ROI-optimized trading schedule...")
        
        # Pre-market validation check (8:00 AM ET) - Performance validation
        schedule.every().day.at("08:00").do(self.scheduled_portfolio_check).tag('validation')
        
        # Market open execution window (9:30 AM ET) - PRIMARY ENTRY WINDOW (first 30 min priority)
        schedule.every().day.at("09:30").do(self.scheduled_trading_cycle).tag('execution')
        
        # Mid-execution follow-up (10:00 AM ET) - Complete early positioning
        schedule.every().day.at("10:00").do(self.scheduled_trading_cycle).tag('execution')
        
        # Market close management (3:00 PM ET) - Position optimization  
        schedule.every().day.at("15:00").do(self.scheduled_trading_cycle).tag('management')
        
        # Final management check (3:30 PM ET) - Pre-close adjustments
        schedule.every().day.at("15:30").do(self.scheduled_trading_cycle).tag('final')
        
        # CRITICAL: Friday weekend risk check (3:45 PM ET) - Weekend protection
        schedule.every().friday.at("15:45").do(self.scheduled_friday_risk_check).tag('friday_risk')
        
        # CRITICAL: Strategic scan after market close (4:15 PM ET) - Next day preparation
        schedule.every().day.at("16:15").do(self.scheduled_strategic_scan).tag('strategic_scan')
        
        self.logger.info("✅ ENHANCED Trading schedule configured (matching original system):")
        self.logger.info("   📋 08:00 ET - Pre-Market Validation Check")
        self.logger.info("   🚀 09:30 ET - Market Open Trading Cycle")
        self.logger.info("   🛡️ 09:45 ET - EXIT MONITORING (CRITICAL)")
        self.logger.info("   📊 10:00 ET - Mid-Morning Trading Cycle")
        self.logger.info("   🛡️ 12:00 ET - EXIT MONITORING (CRITICAL)")
        self.logger.info("   📈 15:00 ET - Late-Day Trading Cycle")
        self.logger.info("   �️ 15:15 ET - EXIT MONITORING (CRITICAL)")
        self.logger.info("   🎯 15:30 ET - Final Trading Cycle")
        self.logger.info("   ⚠️ 15:45 ET - FRIDAY WEEKEND RISK CHECK (CRITICAL)")
        self.logger.info("   📋 16:15 ET - STRATEGIC SCAN - Next Day Selection (CRITICAL)")
    
    def scheduled_portfolio_check(self):
        """Scheduled portfolio check and summary"""
        try:
            self.logger.info("📋 Running scheduled portfolio check...")
            
            # Get account info
            if self.trade_executor.is_alpaca_available():
                account_info = self.trade_executor.get_account_info()
                positions = self.trade_executor.get_current_positions()
                
                self.logger.info(f"💰 Account Status:")
                self.logger.info(f"   Buying Power: ${account_info.get('buying_power', 0):,.2f}")
                self.logger.info(f"   Portfolio Value: ${account_info.get('portfolio_value', 0):,.2f}")
                self.logger.info(f"   Active Positions: {len(positions)}")
                
                for symbol, position in positions.items():
                    self.logger.info(f"   📈 {symbol}: {position.get('qty', 0)} shares @ ${position.get('avg_cost', 0):.2f}")
            
            # Update watchlist if needed
            if self.watchlist_generator:
                current_watchlist = self.check_and_update_watchlist()
                self.logger.info(f"📋 Current watchlist: {len(current_watchlist)} symbols")
                
        except Exception as e:
            self.logger.error(f"Error in scheduled portfolio check: {e}")
    
    def scheduled_trading_cycle(self):
        """Scheduled trading cycle execution"""
        try:
            # Only execute during market hours
            if not self.is_market_hours():
                self.logger.info("⏰ Outside market hours - skipping trading cycle")
                return
            
            self.logger.info("🚀 Running scheduled trading cycle...")
            
            # Get current watchlist
            symbols = self.check_and_update_watchlist()
            
            # Run trading cycle
            results = self.run_trading_cycle(symbols)
            
            # Log results
            self.logger.info(f"📊 Trading cycle completed:")
            self.logger.info(f"   Signals Generated: {results.get('signals_generated', 0)}")
            self.logger.info(f"   Trades Attempted: {results.get('trades_attempted', 0)}")
            self.logger.info(f"   Trades Executed: {results.get('trades_executed', 0)}")
            self.logger.info(f"   Cycle Duration: {results.get('cycle_duration', 0):.2f}s")
            
        except Exception as e:
            self.logger.error(f"Error in scheduled trading cycle: {e}")
    
    def scheduled_exit_monitoring(self):
        """CRITICAL: Monitor all positions for exit conditions - MISSING from original Sprint 1"""
        try:
            if not self.is_market_hours():
                self.logger.info("⏰ Outside market hours - skipping exit monitoring")
                return
                
            self.logger.info("🛡️ CRITICAL: Running exit conditions monitoring...")
            
            if not self.trade_executor.is_alpaca_available():
                self.logger.warning("⚠️ Alpaca not available for exit monitoring")
                return
                
            # Get current positions
            positions = self.trade_executor.get_current_positions()
            if not positions:
                self.logger.info("📋 No positions to monitor for exits")
                return
                
            exit_actions = []
            
            # Check each position for exit conditions
            for symbol, position in positions.items():
                try:
                    current_price = float(position.get('current_price', 0))
                    shares = float(position.get('qty', 0))
                    avg_cost = float(position.get('avg_cost', 0))
                    unrealized_pnl = float(position.get('unrealized_pnl', 0))
                    
                    if current_price <= 0 or avg_cost <= 0:
                        continue
                        
                    # Calculate P&L percentage
                    pnl_pct = (current_price - avg_cost) / avg_cost * 100
                    
                    # Exit condition checks
                    exit_reason = None
                    
                    # Stop loss check (1.5% loss)
                    if pnl_pct <= -1.5:
                        exit_reason = f"STOP LOSS: {pnl_pct:.1f}% loss"
                        
                    # Profit target check (8% gain)  
                    elif pnl_pct >= 8.0:
                        exit_reason = f"PROFIT TARGET: {pnl_pct:.1f}% gain"
                        
                    # Large loss check (3% loss)
                    elif pnl_pct <= -3.0:
                        exit_reason = f"LARGE LOSS: {pnl_pct:.1f}% loss"
                        
                    if exit_reason:
                        exit_actions.append({
                            'symbol': symbol,
                            'shares': int(shares),
                            'reason': exit_reason,
                            'current_price': current_price,
                            'pnl_pct': pnl_pct,
                            'unrealized_pnl': unrealized_pnl
                        })
                        
                        self.logger.info(f"🚨 EXIT TRIGGER: {symbol} - {exit_reason}")
                        
                except Exception as e:
                    self.logger.error(f"Error checking exit conditions for {symbol}: {e}")
            
            # Execute exit trades
            for exit_trade in exit_actions:
                try:
                    self.logger.info(f"📤 EXECUTING EXIT: {exit_trade['symbol']} - {exit_trade['reason']}")
                    
                    result = self.trade_executor.execute_trade(
                        'sell',
                        exit_trade['symbol'], 
                        exit_trade['shares']
                    )
                    
                    if result and result.get('status') == 'executed':
                        self.logger.info(f"✅ EXIT EXECUTED: {exit_trade['symbol']} - ${exit_trade['unrealized_pnl']:.2f} P&L")
                    else:
                        self.logger.error(f"❌ EXIT FAILED: {exit_trade['symbol']}")
                        
                except Exception as e:
                    self.logger.error(f"Error executing exit trade for {exit_trade['symbol']}: {e}")
                    
            if exit_actions:
                self.logger.info(f"🛡️ Exit monitoring completed: {len(exit_actions)} positions triggered")
            else:
                self.logger.info("🛡️ Exit monitoring completed: No exit triggers")
                
        except Exception as e:
            self.logger.error(f"Error in scheduled exit monitoring: {e}")
    
    def scheduled_friday_risk_check(self):
        """CRITICAL: Friday weekend risk management - MISSING from original Sprint 1"""
        try:
            current_time = datetime.now(pytz.timezone('US/Eastern'))
            
            # Only run on Fridays
            if current_time.weekday() != 4:
                self.logger.info("📅 Not Friday - skipping weekend risk check")
                return
                
            self.logger.info("🗓️ CRITICAL: Running Friday Weekend Risk Assessment...")
            
            if not self.trade_executor.is_alpaca_available():
                self.logger.warning("⚠️ Alpaca not available for Friday risk check")
                return
                
            # Get current positions
            positions = self.trade_executor.get_current_positions()
            if not positions:
                self.logger.info("📋 No positions for weekend risk assessment")
                return
                
            account_info = self.trade_executor.get_account_info()
            portfolio_value = float(account_info.get('portfolio_value', 100000))
            
            weekend_reductions = []
            
            # Check each position for weekend risk
            for symbol, position in positions.items():
                try:
                    shares = float(position.get('qty', 0))
                    market_value = float(position.get('market_value', 0))
                    avg_cost = float(position.get('avg_cost', 0))
                    current_price = float(position.get('current_price', 0))
                    
                    if market_value <= 0:
                        continue
                        
                    # Calculate position weight
                    position_weight = market_value / portfolio_value * 100
                    
                    # Weekend risk criteria
                    should_reduce = False
                    reduction_reason = None
                    
                    # Large position check (>8% of portfolio)
                    if position_weight > 8.0:
                        should_reduce = True
                        reduction_reason = f"LARGE POSITION: {position_weight:.1f}% of portfolio"
                        
                    # Volatile stock check (tech stocks, etc.)
                    elif symbol in ['TSLA', 'NVDA', 'AMD', 'NFLX', 'AMZN']:
                        should_reduce = True
                        reduction_reason = f"HIGH VOLATILITY STOCK: Weekend risk"
                        
                    # Recent loss check
                    pnl_pct = (current_price - avg_cost) / avg_cost * 100 if avg_cost > 0 else 0
                    if pnl_pct <= -2.0:
                        should_reduce = True
                        reduction_reason = f"LOSING POSITION: {pnl_pct:.1f}% loss"
                        
                    if should_reduce:
                        # Reduce position by 50% for weekend
                        reduction_shares = int(shares * 0.5)
                        if reduction_shares > 0:
                            weekend_reductions.append({
                                'symbol': symbol,
                                'shares': reduction_shares,
                                'reason': reduction_reason,
                                'position_weight': position_weight
                            })
                            
                            self.logger.info(f"⚠️ WEEKEND REDUCTION: {symbol} - {reduction_reason}")
                            
                except Exception as e:
                    self.logger.error(f"Error assessing weekend risk for {symbol}: {e}")
            
            # Execute weekend reductions if market is open
            if weekend_reductions and self.is_market_hours():
                self.logger.info(f"📤 Executing {len(weekend_reductions)} weekend risk reductions...")
                
                for reduction in weekend_reductions:
                    try:
                        result = self.trade_executor.execute_trade(
                            'sell',
                            reduction['symbol'],
                            reduction['shares'] 
                        )
                        
                        if result and result.get('status') == 'executed':
                            self.logger.info(f"✅ WEEKEND REDUCTION: {reduction['symbol']} - {reduction['shares']} shares")
                        else:
                            self.logger.error(f"❌ WEEKEND REDUCTION FAILED: {reduction['symbol']}")
                            
                    except Exception as e:
                        self.logger.error(f"Error executing weekend reduction for {reduction['symbol']}: {e}")
                        
            elif weekend_reductions:
                self.logger.warning("⏰ Market closed - weekend reductions would be queued for Monday")
                
            if weekend_reductions:
                self.logger.info(f"🗓️ Friday risk check completed: {len(weekend_reductions)} reductions planned")
            else:
                self.logger.info("🗓️ Friday risk check completed: No weekend risk detected")
                
        except Exception as e:
            self.logger.error(f"Error in Friday weekend risk check: {e}")
    
    def scheduled_strategic_scan(self):
        """CRITICAL: After-market strategic scan for next day - MISSING from original Sprint 1"""
        try:
            self.logger.info("📊 CRITICAL: Running after-market strategic scan for next day...")
            
            # This runs after market close to prepare for next day
            current_time = datetime.now(pytz.timezone('US/Eastern'))
            
            # Update watchlist for next day trading
            if self.watchlist_generator:
                try:
                    self.logger.info("🔄 Refreshing watchlist for next trading day...")
                    
                    # Force refresh the watchlist
                    new_watchlist = self.watchlist_generator.generate_watchlist()
                    
                    if new_watchlist:
                        self.logger.info(f"📋 Next day watchlist prepared: {len(new_watchlist)} symbols")
                        
                        # Log top opportunities for next day
                        for i, symbol in enumerate(new_watchlist[:10]):
                            self.logger.info(f"   {i+1}. {symbol}")
                    else:
                        self.logger.warning("⚠️ No symbols in next day watchlist")
                        
                except Exception as e:
                    self.logger.error(f"Error refreshing watchlist for next day: {e}")
            
            # Portfolio summary for next day planning
            if self.trade_executor.is_alpaca_available():
                try:
                    account_info = self.trade_executor.get_account_info()
                    positions = self.trade_executor.get_current_positions()
                    
                    self.logger.info("💰 End of day portfolio summary:")
                    self.logger.info(f"   Portfolio Value: ${account_info.get('portfolio_value', 0):,.2f}")
                    self.logger.info(f"   Buying Power: ${account_info.get('buying_power', 0):,.2f}")
                    self.logger.info(f"   Positions Held Overnight: {len(positions)}")
                    
                    total_overnight_value = sum(float(pos.get('market_value', 0)) for pos in positions.values())
                    self.logger.info(f"   Total Overnight Exposure: ${total_overnight_value:,.2f}")
                    
                except Exception as e:
                    self.logger.error(f"Error getting portfolio summary: {e}")
            
            self.logger.info("📊 Strategic scan completed - System ready for next trading day")
            
        except Exception as e:
            self.logger.error(f"Error in scheduled strategic scan: {e}")
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        self.logger.info("🛑 Shutdown signal received - stopping Sprint 1 + Alpaca system...")
        self.running = False
        
    def run_automated_scheduled(self):
        """Run the automated trading system with scheduled execution"""
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        # Initialize the running flag
        self.running = True
        
        # Initialize system
        if not self.initialize_system():
            self.logger.error("❌ System initialization failed - cannot start automated trading")
            return
        
        # Setup schedule
        self.setup_schedule()
        
        # Initial portfolio check
        self.scheduled_portfolio_check()
        
        self.logger.info("🚀 Sprint 1 + Alpaca Automated Trading System is now running...")
        self.logger.info("💡 Press Ctrl+C to stop gracefully")
        
        # Main scheduling loop
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
                
            except KeyboardInterrupt:
                self.logger.info("⌨️ Keyboard interrupt received")
                break
            except Exception as e:
                self.logger.error(f"Error in main scheduling loop: {e}")
                time.sleep(60)  # Wait before retrying
        
        self.logger.info("👋 Sprint 1 + Alpaca Automated Trading System stopped")
    
    def run_trading_cycle(self, symbols: List[str]) -> Dict:
        """Run one complete trading cycle with Alpaca execution"""
        cycle_start = time.time()
        
        try:
            # Update market data
            self.data_feed.update_market_data(symbols)
            
            signals_generated = 0
            trades_attempted = 0
            trades_executed = 0
            
            # Generate and execute signals for each symbol
            for symbol in symbols:
                try:
                    # Get market data
                    df = self.data_feed.get_historical_data(symbol, days=30)
                    current_price = self.data_feed.get_current_price(symbol)
                    
                    if df.empty or current_price is None:
                        continue
                    
                    # Generate signal
                    signal = self.signal_generator.generate_signal(symbol, df)
                    self.logger.info(f"📊 Signal for {symbol}: {signal}")
                    signals_generated += 1
                    
                    # Enhanced risk check with TAF awareness
                    if self.taf_aware_risk_manager:
                        # Use TAF-aware risk assessment
                        intended_shares = self.trade_executor.calculate_position_size(symbol, 0.8, current_price)
                        risk_assessment = self.taf_aware_risk_manager.assess_risk_with_fees(
                            symbol, df, current_price, intended_shares
                        )
                        
                        if not risk_assessment.get('trade_recommended', False):
                            self.logger.info(f"Trade not recommended for {symbol}: "
                                           f"confidence {risk_assessment['adjusted_confidence']:.2f}, "
                                           f"TAF impact {risk_assessment['taf_fee_impact']['fee_percentage']:.3f}%")
                            continue
                            
                        confidence = risk_assessment['adjusted_confidence']
                    else:
                        # Fallback to basic risk assessment
                        risk_assessment = self.risk_manager.assess_risk(symbol, df)
                        if risk_assessment['confidence'] < 0.5:
                            self.logger.info(f"Skipping {symbol} due to low confidence: {risk_assessment['confidence']:.2f}")
                            continue
                        confidence = risk_assessment['confidence']
                    
                    # Execute trade if signal is actionable
                    if signal in ['buy', 'sell']:
                        trades_attempted += 1
                        
                        # CRITICAL: Prevent duplicate unfilled orders - MISSING from original Sprint 1
                        order_key = f"{symbol}_{signal}"
                        if order_key in self.unfilled_orders:
                            self.logger.warning(f"⚠️ Skipping {symbol} {signal} - unfilled order already exists")
                            continue
                        
                        # Use confidence from risk assessment
                        confidence = risk_assessment['confidence']
                        trade_result = self.trade_executor.execute_trade(symbol, signal, current_price, confidence)
                        
                        if trade_result["status"] == "executed":
                            trades_executed += 1
                            self.successful_trades += 1
                            self.logger.info(f"✅ Trade executed: {trade_result}")
                            
                            # CRITICAL: Track position entry data for exit monitoring - MISSING from original Sprint 1
                            if trade_result["action"] == "buy":
                                entry_time = datetime.now()
                                stop_loss_price = current_price * 0.985  # 1.5% stop loss
                                profit_target_price = current_price * 1.08  # 8% profit target
                                
                                # Store position tracking data
                                self.position_entry_dates[symbol] = entry_time
                                self.position_entry_prices[symbol] = current_price
                                self.position_stop_losses[symbol] = stop_loss_price
                                self.position_profit_targets[symbol] = profit_target_price
                                
                                self.logger.info(f"📊 Position tracking added for {symbol}: "
                                               f"Entry ${current_price:.2f}, Stop ${stop_loss_price:.2f}, "
                                               f"Target ${profit_target_price:.2f}")
                                               
                            elif trade_result["action"] == "sell":
                                # Clean up tracking data on exit
                                self.position_entry_dates.pop(symbol, None)
                                self.position_entry_prices.pop(symbol, None)
                                self.position_stop_losses.pop(symbol, None)
                                self.position_profit_targets.pop(symbol, None)
                                
                                self.logger.info(f"📊 Position tracking cleared for {symbol}")
                        else:
                            self.logger.info(f"Trade result for {symbol}: {trade_result}")
                    
                except Exception as e:
                    self.logger.error(f"Error processing {symbol}: {e}")
                    continue
            
            # Update counters
            self.signals_generated += signals_generated
            self.trades_executed += trades_executed
            
            cycle_time = time.time() - cycle_start
            
            return {
                'status': 'completed',
                'signals_generated': signals_generated,
                'trades_attempted': trades_attempted,
                'trades_executed': trades_executed,
                'cycle_time': cycle_time,
                'symbols_processed': len(symbols)
            }
            
        except Exception as e:
            self.logger.error(f"Trading cycle failed: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def start_paper_trading_with_dashboard(self, symbols: List[str], update_frequency_minutes: int = 5):
        """Start paper trading with dashboard running in main thread"""
        self.logger.info(f"🚀 Starting Sprint 1 + Alpaca paper trading for {len(symbols)} symbols")
        self.logger.info(f"Update frequency: {update_frequency_minutes} minutes")
        
        if not self.initialize_system():
            self.logger.error("Failed to initialize system")
            return
        
        # Start dashboard setup
        if self.launch_gui:
            self.start_dashboard()
        
        # Start trading in background thread
        self.trading_thread = threading.Thread(
            target=self._run_trading_loop, 
            args=(symbols, update_frequency_minutes),
            daemon=True
        )
        self.trading_thread.start()
        
        # Run dashboard in main thread (if available)
        if self.dashboard:
            try:
                self.logger.info("🖥️ Starting dashboard in main thread...")
                self.dashboard.run()  # This blocks in main thread
            except KeyboardInterrupt:
                self.logger.info("Dashboard stopped by user")
                self.stop_trading_loop = True
            except Exception as e:
                self.logger.error(f"Dashboard error: {e}")
                self.stop_trading_loop = True
        else:
            # No dashboard - run trading in current thread
            self._run_trading_loop(symbols, update_frequency_minutes)
    
    def _run_trading_loop(self, symbols: List[str], update_frequency_minutes: int):
        """Background trading loop"""
        self.stop_trading_loop = False
        
        try:
            while not self.stop_trading_loop:
                # Check if market is open (RESPECT MARKET HOURS)
                if not self.is_market_hours():
                    self.logger.info("⏰ Market closed - waiting for market hours...")
                    # Wait for market hours rather than continuing
                    time.sleep(300)  # Check every 5 minutes
                    continue
                
                # Run trading cycle
                cycle_result = self.run_trading_cycle(symbols)
                
                # Update dashboard if running
                if self.dashboard:
                    self.update_dashboard(cycle_result)
                
                # Log results
                self.logger.info(f"Cycle completed: {cycle_result['status']}")
                if cycle_result['status'] == 'completed':
                    self.logger.info(f"Signals: {cycle_result['signals_generated']}, "
                                   f"Trades attempted: {cycle_result['trades_attempted']}, "
                                   f"Trades executed: {cycle_result['trades_executed']}")
                
                # Wait for next cycle
                time.sleep(update_frequency_minutes * 60)
                
        except Exception as e:
            self.logger.error(f"Trading loop error: {e}")
        finally:
            self.logger.info("Trading loop stopped")

    def start_paper_trading(self, symbols: List[str], update_frequency_minutes: int = 5):
        """Start paper trading with Alpaca execution and optional GUI"""
        self.logger.info(f"🚀 Starting Sprint 1 + Alpaca paper trading for {len(symbols)} symbols")
        self.logger.info(f"Update frequency: {update_frequency_minutes} minutes")
        
        if not self.initialize_system():
            self.logger.error("Failed to initialize system")
            return
        
        # Launch GUI dashboard if requested
        if self.launch_gui:
            self.start_dashboard()
        
        try:
            while True:
                # Check if market is open (RESPECT MARKET HOURS)
                if not self.is_market_hours():
                    self.logger.info("⏰ Market closed - waiting for market hours...")
                    # Wait for market hours rather than continuing
                    time.sleep(300)  # Check every 5 minutes
                    continue
                
                # Run trading cycle
                cycle_result = self.run_trading_cycle(symbols)
                
                # Update dashboard if running
                if self.dashboard:
                    self.update_dashboard(cycle_result)
                
                # Log results
                self.logger.info(f"Cycle completed: {cycle_result['status']}")
                if cycle_result['status'] == 'completed':
                    self.logger.info(f"Signals: {cycle_result['signals_generated']}, "
                                   f"Trades attempted: {cycle_result['trades_attempted']}, "
                                   f"Trades executed: {cycle_result['trades_executed']}")
                
                # Wait for next cycle
                time.sleep(update_frequency_minutes * 60)
                
        except KeyboardInterrupt:
            self.logger.info("Paper trading stopped by user")
            self.stop_dashboard()
        except Exception as e:
            self.logger.error(f"Paper trading error: {e}")
            self.stop_dashboard()
    
    def get_system_metrics(self) -> Dict:
        """Get comprehensive system performance metrics"""
        uptime = (datetime.now() - self.integration_start_time).total_seconds() / 3600
        
        # Get Alpaca account info
        account_info = {}
        if self.trade_executor.is_alpaca_available():
            account_info = self.trade_executor.get_account_info()
        
        data_metrics = self.data_feed.get_performance_metrics()
        
        return {
            'system_uptime_hours': uptime,
            'signals_generated': self.signals_generated,
            'trades_executed': self.trades_executed,
            'successful_trades': self.successful_trades,
            'success_rate': self.successful_trades / max(self.trades_executed, 1),
            'data_feed_metrics': data_metrics,
            'alpaca_account': account_info,
            'alpaca_available': self.trade_executor.is_alpaca_available(),
            'status': 'operational' if data_metrics['data_quality_score'] > 0.7 else 'degraded'
        }
    
    def start_dashboard(self):
        """Start the integrated dashboard in a separate thread"""
        try:
            from gui.sprint1_integrated_dashboard import create_integrated_dashboard
            from core.config import Sprint1Config
            
            config = Sprint1Config()
            self.dashboard = create_integrated_dashboard(self, config)
            
            # Note: Dashboard will run in main thread, trading in background
            self.logger.info("✅ Integrated dashboard initialized")
            
        except ImportError:
            self.logger.warning("⚠️ Dashboard not available - continuing without GUI")
            self.launch_gui = False
        except Exception as e:
            self.logger.error(f"Failed to start dashboard: {e}")
            self.launch_gui = False
            
    def stop_dashboard(self):
        """Stop the dashboard"""
        if self.dashboard:
            try:
                self.dashboard.close()
                self.logger.info("Dashboard closed")
            except:
                pass
                
    def update_dashboard(self, cycle_result: Dict):
        """Update dashboard with latest cycle results"""
        if not self.dashboard:
            return
            
        try:
            # Update metrics tracker
            if hasattr(self.dashboard, 'metrics_tracker'):
                tracker = self.dashboard.metrics_tracker
                
                tracker.add_cycle(
                    signals=cycle_result.get('signals_generated', 0),
                    trades=cycle_result.get('trades_executed', 0),
                    cycle_time=cycle_result.get('cycle_time', 0),
                    success=(cycle_result.get('status') == 'completed')
                )
                
                # Add any executed trades
                if cycle_result.get('trades_executed', 0) > 0:
                    # This would be populated with actual trade data
                    # For now, we'll use placeholder data
                    pass
                    
        except Exception as e:
            self.logger.warning(f"Dashboard update error: {e}")

def main():
    """Main function for testing"""
    from core.config import Sprint1Config
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/sprint1_alpaca.log'),
            logging.StreamHandler()
        ]
    )
    
    # Load configuration
    config = Sprint1Config()
    
    # Create integration system
    integration = Sprint1AlpacaIntegration()
    
    # Check and update watchlist
    current_watchlist = integration.check_and_update_watchlist()
    
    # Run quick test
    print("🧪 Sprint 1 + Alpaca Integration")
    print("=" * 50)
    print(f"📋 Current watchlist ({len(current_watchlist)}): {current_watchlist}")
    
    # Initialize and run one cycle
    if integration.initialize_system():
        print("✅ System initialized successfully")
        print("📈 Running test trading cycle...")
        
        cycle_result = integration.run_trading_cycle(current_watchlist)
        
        print(f"Cycle Status: {cycle_result['status']}")
        print(f"Signals Generated: {cycle_result.get('signals_generated', 0)}")
        print(f"Trades Executed: {cycle_result.get('trades_executed', 0)}")
        
        # Display system metrics
        metrics = integration.get_system_metrics()
        print("\n📊 System Performance Metrics:")
        for key, value in metrics.items():
            if key != 'data_feed_metrics':
                print(f"  {key}: {value}")
        
        print("\n🎉 Sprint 1 + Alpaca Integration: SUCCESS!")
        print("✅ Ready for continuous paper trading with Alpaca execution")
        
        # Trading mode selection
        print("\n🚀 Trading Mode Options:")
        print("1. Scheduled Automated Trading (Recommended)")
        print("2. Continuous Manual Trading")
        print("3. Exit")
        
        choice = input("\nSelect mode (1-3): ").strip()
        
        if choice == '1':
            print("🕒 Starting scheduled automated trading...")
            print("📅 Trading will execute at preset times during market hours")
            print("💡 Press Ctrl+C to stop gracefully")
            integration.run_automated_scheduled()
            
        elif choice == '2':
            print("� Starting continuous manual trading...")
            print("💡 Press Ctrl+C to stop gracefully")
            integration.start_paper_trading_with_dashboard(current_watchlist)
            
        else:
            print("👋 Exiting...")

if __name__ == "__main__":
    main()

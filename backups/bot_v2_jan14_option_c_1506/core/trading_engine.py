"""
Production Trading Engine - Full trading system orchestration
Extracted and enhanced from ShortCycleTrader - Phase 6 Complete Implementation
"""
import logging
import datetime as dt
import pytz
import pandas as pd
from typing import Optional, List, Dict, Any

# Import all bot_v2 modules
from ..config import ShortCycleConfig
from ..models.positions import ShortCyclePosition, PositionStatus
from ..models.signals import AISignal
from ..signal_generation import AISignalGenerator
from ..risk_management import (
    AIStopLossManager,
    AIConfidencePositionSizer,
    AIPredictiveRiskManager
)
from ..market_analysis import AIMarketRegimeDetector
from ..portfolio import AIPortfolioManager
from ..execution import AIPositionTracker, AIOrderManager, AIExitManager
from ..monitoring import AIPerformanceTracker
from ..utils import get_next_trading_day, validate_diversification, check_same_day_activity, get_max_positions_for_day


class ProductionTradingEngine:
    """
    Production-ready trading engine orchestrating all bot_v2 modules.
    
    This is the full modular replacement for the original monolithic ShortCycleTrader.
    
    Architecture:
    - Portfolio Management: AIPortfolioManager (portfolio value, P&L, risk limits)
    - Position Tracking: AIPositionTracker (load/save, broker sync)
    - Order Execution: AIOrderManager (buy/sell orders, fills)
    - Exit Management: AIExitManager (D+1, trailing stops, force close)
    - Signal Generation: AISignalGenerator (mean reversion RSI strategy)
    - Risk Management: AIStopLossManager, AIConfidencePositionSizer, AIPredictiveRiskManager
    - Market Analysis: AIMarketRegimeDetector
    - Performance Tracking: AIPerformanceTracker (reports, monitoring)
    """
    
    def __init__(self, config: Optional[ShortCycleConfig] = None, 
                 execution_engine=None, data_loader=None, 
                 day_trade_tracker=None, monitoring_system=None,
                 earnings_calendar=None, pattern_recognizer=None, pattern_tracker=None,
                 logger: Optional[logging.Logger] = None):
        """
        Initialize production trading engine with all bot_v2 modules.
        
        Args:
            config: ShortCycleConfig (defaults to Option 3: $1K, 60% conf, 12 trades/month)
            execution_engine: Broker API (Alpaca/paper)
            data_loader: Market data provider
            day_trade_tracker: PDT compliance tracker
            monitoring_system: Self-monitoring system
            earnings_calendar: Earnings protection
            pattern_recognizer: Pattern-based exit timing
            pattern_tracker: Position pattern tracking
            logger: Logger instance
        """
        self.config = config or ShortCycleConfig()
        self.execution_engine = execution_engine
        self.data_loader = data_loader
        self.day_trade_tracker = day_trade_tracker
        self.monitoring_system = monitoring_system
        self.earnings_calendar = earnings_calendar
        self.pattern_recognizer = pattern_recognizer
        self.pattern_tracker = pattern_tracker
        self.logger = logger or self._setup_logging()
        
        # Initialize all bot_v2 modules
        self._initialize_modules()
        
        # Kill switches
        self.kill_switches = {
            "daily_loss_exceeded": False,
            "weekly_loss_exceeded": False,
            "system_error": False
        }
        
        self.logger.info("✅ ProductionTradingEngine initialized (bot_v2 - Phase 6)")
    
    def _setup_logging(self) -> logging.Logger:
        """Setup comprehensive logging"""
        import os
        logger = logging.getLogger("ProductionTradingEngine")
        
        if logger.handlers:
            logger.handlers.clear()
        
        logger.propagate = False
        
        if not logger.handlers:
            os.makedirs('logs', exist_ok=True)
            
            # File handler
            file_handler = logging.FileHandler('logs/production_trading_engine.log')
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
            
            # Console handler
            console_handler = logging.StreamHandler()
            console_formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s'
            )
            console_handler.setFormatter(console_formatter)
            logger.addHandler(console_handler)
            
            logger.setLevel(logging.INFO)
        
        return logger
    
    def _initialize_modules(self):
        """Initialize all bot_v2 modules"""
        self.logger.info("🔧 Initializing bot_v2 modules...")
        
        # Portfolio Management
        self.portfolio_manager = AIPortfolioManager(
            config=self.config,
            execution_engine=self.execution_engine,
            logger=self.logger
        )
        
        # Position Tracking
        self.position_tracker = AIPositionTracker(
            config=self.config,
            execution_engine=self.execution_engine,
            logger=self.logger
        )
        
        # Order Management
        self.order_manager = AIOrderManager(
            config=self.config,
            execution_engine=self.execution_engine,
            day_trade_tracker=self.day_trade_tracker,
            logger=self.logger
        )
        
        # Signal Generation
        self.signal_generator = AISignalGenerator(
            config=self.config,
            price_fetcher=self._get_current_price
        )
        
        # Risk Management
        self.stop_manager = AIStopLossManager(
            config=self.config
        )
        
        self.position_sizer = AIConfidencePositionSizer(
            config=self.config
        )
        
        self.risk_manager = AIPredictiveRiskManager(
            config=self.config
        )
        
        # Market Analysis
        self.regime_detector = AIMarketRegimeDetector(
            config=self.config
        )
        
        # Exit Management
        self.exit_manager = AIExitManager(
            config=self.config,
            stop_manager=self.stop_manager,
            order_manager=self.order_manager,
            earnings_calendar=self.earnings_calendar,
            pattern_recognizer=self.pattern_recognizer,
            pattern_tracker=self.pattern_tracker,
            logger=self.logger
        )
        
        # Performance Tracking
        self.performance_tracker = AIPerformanceTracker(
            config=self.config,
            monitoring_system=self.monitoring_system,
            logger=self.logger
        )
        
        self.logger.info("✅ All bot_v2 modules initialized")
    
    def run_daily_cycle(self):
        """Execute daily trading cycle"""
        self.logger.info("🚀 Starting daily trading cycle (bot_v2)")
        
        try:
            # Reset daily counters if needed
            self.portfolio_manager.reset_daily_counters_if_needed()
            
            # Update risk limits based on current portfolio
            self.portfolio_manager.update_risk_limits()
            
            # Load positions from disk
            positions = self.position_tracker.load_positions()
            
            # Sync with broker
            live_positions = self.position_tracker.get_live_positions()
            if self.position_tracker.sync_positions_with_broker(live_positions):
                self.position_tracker.save_positions()
            
            # Check if we should trade today
            if not self._should_trade_today():
                return
            
            # Process existing positions for exits
            self._process_existing_positions()
            
            # Check kill switches after processing
            if any(self.kill_switches.values()):
                return
            
            # Generate new signals if we have capacity
            if self.portfolio_manager.trades_today < self.config.max_positions_per_day:
                # Check Friday special limits (only enter if unused emergency exits available)
                import pytz
                today_name = dt.datetime.now(pytz.UTC).strftime("%A").lower()
                if today_name == "friday":
                    friday_limit = self.portfolio_manager.get_friday_entry_slots_available()
                    if self.portfolio_manager.trades_today >= friday_limit:
                        self.logger.info(f"📊 Friday entry limit reached ({self.portfolio_manager.trades_today}/{friday_limit} unused emergency slots)")
                    else:
                        self._generate_and_execute_new_positions()
                else:
                    self._generate_and_execute_new_positions()
            else:
                self.logger.info(f"📊 Daily position limit reached ({self.portfolio_manager.trades_today}/{self.config.max_positions_per_day})")
            
            # Daily reporting
            portfolio_state = self.portfolio_manager.get_portfolio_state()
            positions = self.position_tracker.get_positions()
            self.performance_tracker.generate_daily_report(
                portfolio_state, positions, self.kill_switches
            )
            
        except Exception as e:
            self.logger.error(f"❌ Error in daily cycle: {e}")
            self.kill_switches["system_error"] = True
    
    def _should_trade_today(self) -> bool:
        """Check if we should trade today"""
        import pytz
        today = dt.datetime.now(pytz.UTC).strftime("%A").lower()
        
        # Check kill switches
        for switch, activated in self.kill_switches.items():
            if activated:
                self.logger.warning(f"❌ Trading halted: {switch}")
                return False
        
        # Special Friday logic: Allow entries if unused emergency exits available
        if today == "friday":
            friday_slots = self.portfolio_manager.get_friday_entry_slots_available()
            if friday_slots > 0:
                self.logger.info(f"📅 Friday trading ALLOWED: {friday_slots} unused emergency exit slots available")
                return True
            else:
                self.logger.info(f"📅 Friday: No unused emergency exits, exit-only mode")
                return False
        
        # Check normal trading days (Mon-Thu)
        if today not in self.config.trading_days:
            self.logger.info(f"📅 No trading on {today}")
            return False
        
        return True
    
    def _process_existing_positions(self):
        """Process existing positions for exits"""
        positions = self.position_tracker.get_positions()
        
        # Phase 1: Strategic D+1 exits
        strategic_exits = self.exit_manager.process_strategic_d1_exits(
            positions, self.data_loader
        )
        
        # Phase 2: Other exit conditions (trailing stops, fast exits, stop loss)
        other_exits = 0
        for position in positions:
            if position.status != PositionStatus.ENTERED:
                continue
            
            # Skip positions already handled by D+1
            if dt.date.today() >= position.exit_date:
                continue
            
            # PDT protection: Don't exit same-day entries (except Friday force close)
            if position.entry_date >= dt.date.today():
                current_time = dt.datetime.now(pytz.UTC)
                is_friday_force = (current_time.weekday() == 4 and 
                                  current_time.hour >= 15 and 
                                  current_time.minute >= 45)
                if not is_friday_force:
                    continue
            
            try:
                current_price = self._get_current_price(position.symbol)
                if not current_price:
                    continue
                
                position.update_current_price(current_price)
                
                # Check trailing stop
                if self.config.enable_trailing_stops:
                    trailing_exit = self.exit_manager.check_trailing_stop(position, current_price)
                    if trailing_exit:
                        exit_price, exit_reason = trailing_exit
                        if self.exit_manager.exit_position(position, exit_price, exit_reason, self.data_loader):
                            other_exits += 1
                            continue
                
                # Check stop loss
                if position.is_stopped_out(current_price):
                    if self.exit_manager.exit_position(position, current_price, "STOP_LOSS", self.data_loader):
                        other_exits += 1
                        continue
                
                # Check fast exit
                if self.stop_manager.should_fast_exit(position, current_price):
                    if self.exit_manager.exit_position(position, current_price, "FAST_EXIT", self.data_loader):
                        other_exits += 1
                        continue
                
            except Exception as e:
                self.logger.error(f"Error processing {position.symbol}: {e}")
        
        total_exits = strategic_exits + other_exits
        self.logger.info(f"📊 Total exits: {total_exits} (Strategic: {strategic_exits}, Other: {other_exits})")
        
        # Update P&L
        positions = self.position_tracker.get_positions()
        self.portfolio_manager.update_daily_pnl(positions)
        self.portfolio_manager.update_weekly_pnl(positions)
        self._check_loss_limits()
        
        # Save positions
        self.position_tracker.save_positions()
    
    def _generate_and_execute_new_positions(self):
        """Generate new signals and execute positions"""
        try:
            # Get market regime
            market_data = self._get_market_data()
            regime_info = self.regime_detector.get_current_regime(market_data)
            self.logger.info(f"📈 Market regime: {regime_info['regime']}")
            
            # Get trading universe
            universe = self._get_trading_universe()
            self.logger.info(f"🧭 Trading universe: {len(universe)} symbols")
            
            # Generate signals
            positions = self.position_tracker.get_positions()
            signals = self.signal_generator.generate_signals(universe, market_data, positions)
            
            if not signals:
                self.logger.info("📭 No signals generated")
                return
            
            # Risk assessment
            risk_assessment = self.risk_manager.assess_portfolio_risk(signals, positions, market_data)
            
            if not risk_assessment["approved"]:
                self.logger.warning(f"🛑 Risk manager vetoed all trades: {risk_assessment['warnings']}")
                return
            
            # Execute approved signals
            for signal in signals:
                if signal.symbol in risk_assessment.get("vetoed_signals", []):
                    self.logger.info(f"🛑 Signal {signal.symbol} vetoed by risk manager")
                    continue
                
                # Get max positions for today
                max_positions_today, max_portfolio_pct = get_max_positions_for_day()
                
                if self.portfolio_manager.trades_today >= max_positions_today:
                    self.logger.info(f"📊 Position limit reached ({self.portfolio_manager.trades_today}/{max_positions_today})")
                    break
                
                # Diversification check
                allowed, reason = validate_diversification(signal.symbol, positions, self.config)
                if not allowed:
                    self.logger.info(f"🔄 {signal.symbol} skipped: {reason}")
                    continue
                
                # Same-day activity check
                if check_same_day_activity(signal.symbol, positions, self.config):
                    self.logger.info(f"🔄 {signal.symbol} skipped: Same-day activity")
                    continue
                
                # Execute signal
                self._execute_signal(signal, market_data.get(signal.symbol))
            
        except Exception as e:
            self.logger.error(f"Error generating new positions: {e}")
    
    def _execute_signal(self, signal: AISignal, symbol_data):
        """Execute a trading signal"""
        try:
            # Calculate stop price
            stop_price, stop_pct = self.stop_manager.calculate_optimal_stop(signal, symbol_data)
            
            # Calculate position size
            portfolio_value = self.portfolio_manager.get_portfolio_value()
            shares, position_value = self.position_sizer.calculate_position_size(
                signal, stop_price, portfolio_value
            )
            
            if not shares or shares == 0:
                self.logger.info(f"❌ {signal.symbol}: Position size too small")
                return
            
            # Create position with momentum-based exit date
            today = dt.date.today()
            exit_date = self._calculate_exit_date(signal, symbol_data)
            
            position = ShortCyclePosition(
                symbol=signal.symbol,
                entry_date=today,
                exit_date=exit_date,
                entry_price=signal.entry_price,
                position_size_shares=int(shares),
                position_size_dollars=position_value,
                stop_price=stop_price,
                target_price=signal.target_price,
                status=PositionStatus.PENDING,
                ai_signal=signal,
                max_risk_dollars=self.config.max_risk_per_trade_dollars
            )
            
            # Execute trade
            success = self.order_manager.execute_buy_order(position)
            
            if success:
                position.status = PositionStatus.ENTERED
                self.position_tracker.add_position(position)
                self.portfolio_manager.increment_trade_counter()
                self.position_tracker.save_positions()
                
                self.logger.info(f"✅ {signal.symbol}: Entered {shares} shares @ ${signal.entry_price:.2f} "
                               f"(Stop: ${stop_price:.2f}, Confidence: {signal.confidence:.1%})")
            else:
                self.logger.error(f"❌ {signal.symbol}: Failed to execute trade")
                
        except Exception as e:
            self.logger.error(f"Error executing signal for {signal.symbol}: {e}")
    
    def _check_loss_limits(self):
        """Check daily and weekly loss limits"""
        from utils import market_hours
        
        # Only check during market hours
        if not market_hours.is_regular_session_now():
            return
        
        portfolio_state = self.portfolio_manager.get_portfolio_state()
        
        # Check daily loss limit
        if portfolio_state.daily_realized_pnl < 0 and abs(portfolio_state.daily_realized_pnl) > self.config.max_daily_loss_dollars:
            self.kill_switches["daily_loss_exceeded"] = True
            self.logger.warning(f"🛑 Daily loss limit exceeded: ${portfolio_state.daily_realized_pnl:.2f}")
        
        # Check weekly loss limit
        if portfolio_state.weekly_pnl < 0 and abs(portfolio_state.weekly_pnl) > self.config.max_weekly_loss_dollars:
            self.kill_switches["weekly_loss_exceeded"] = True
            self.logger.warning(f"🛑 Weekly loss limit exceeded: ${portfolio_state.weekly_pnl:.2f}")
    
    def _calculate_exit_date(self, signal, symbol_data: pd.DataFrame) -> dt.date:
        """Calculate exit date based on momentum: D+1 standard, D+2-D+3 for strong momentum"""
        today = dt.date.today()
        
        # Calculate recent momentum (5-day rate of change)
        try:
            if symbol_data is not None and len(symbol_data) >= 5:
                recent_close = symbol_data['Close'].iloc[-1]
                week_ago_close = symbol_data['Close'].iloc[-5]
                momentum = (recent_close - week_ago_close) / week_ago_close
                
                # Strong momentum: D+3
                if momentum >= self.config.strong_momentum_threshold:
                    hold_days = 3
                    self.logger.info(f"📈 {signal.symbol}: STRONG momentum {momentum:.1%} → D+3 exit")
                # Good momentum: D+2
                elif momentum >= self.config.momentum_hold_threshold:
                    hold_days = 2
                    self.logger.info(f"📊 {signal.symbol}: Good momentum {momentum:.1%} → D+2 exit")
                # Standard: D+1
                else:
                    hold_days = 1
                    self.logger.info(f"📉 {signal.symbol}: Standard momentum {momentum:.1%} → D+1 exit")
            else:
                hold_days = 1  # Default to D+1 if no data
                self.logger.info(f"📋 {signal.symbol}: No momentum data → D+1 exit (default)")
        except Exception as e:
            self.logger.warning(f"⚠️ {signal.symbol}: Error calculating momentum: {e}, using D+1")
            hold_days = 1
        
        # Calculate exit date (skip weekends)
        exit_date = today
        days_added = 0
        while days_added < hold_days:
            exit_date = get_next_trading_day(exit_date)
            days_added += 1
        
        return exit_date
    
    def _get_current_price(self, symbol: str) -> Optional[float]:
        """Get current market price"""
        try:
            if self.data_loader:
                return self.data_loader.get_current_price(symbol)
        except Exception:
            pass
        return None
    
    def _get_market_data(self) -> Dict:
        """Get market data for analysis"""
        try:
            if not self.data_loader:
                return {}
            
            universe = self._get_trading_universe()
            data_by_symbol = {}
            
            for symbol in universe:
                try:
                    df = self.data_loader.get_historical_data(symbol, days=40)
                    if df is not None and not df.empty:
                        data_by_symbol[symbol] = df
                except Exception:
                    pass
            
            return data_by_symbol
        except Exception as e:
            self.logger.warning(f"_get_market_data error: {e}")
            return {}
    
    def _get_trading_universe(self) -> List[str]:
        """
        Get trading universe using PreFilter (dynamic, not hardcoded).
        Applies mid-cap filter ($2B-$10B), volume, liquidity, and volatility filters.
        """
        try:
            # Import PreFilter (avoid hardcoded symbols)
            import sys
            import os
            import pandas as pd
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            from pre_filter import PreFilter
            
            # Initialize PreFilter with bot_v2 config
            prefilter = PreFilter(
                simulation_mode=False,
                data_loader=self.data_loader,
                fast_mode=True,
                enable_gap_detection=True,  # D+1 strategy benefits from gap analysis
                regime_adjustment=True      # Adjust filters based on market regime
            )
            
            # Get initial universe (from screener or database)
            initial_universe = self._get_initial_screener_universe()
            
            self.logger.info(f"📊 Filtering {len(initial_universe)} stocks through PreFilter...")
            
            # Create DataFrame for PreFilter (requires specific format)
            # Fetch recent data for each symbol
            all_data = []
            for symbol in initial_universe:
                try:
                    df = self.data_loader.get_historical_data(symbol, days=60)
                    if df is not None and not df.empty:
                        df['symbol'] = symbol
                        all_data.append(df)
                except Exception:
                    continue
            
            if not all_data:
                self.logger.warning("⚠️ No data fetched, using fallback universe")
                return self._get_fallback_universe()
            
            # Combine all data
            combined_df = pd.concat(all_data, ignore_index=True)
            
            # Apply PreFilter
            filtered_df = prefilter.filter_assets(combined_df)
            
            if filtered_df.empty:
                self.logger.warning("⚠️ PreFilter returned no symbols, using fallback")
                return self._get_fallback_universe()
            
            # Get unique symbols from filtered results
            filtered_symbols = filtered_df['symbol'].unique().tolist()
            
            # Apply mid-cap filter ($2B-$10B) - bot_v2 specific
            midcap_universe = self._apply_market_cap_filter(filtered_symbols)
            
            if not midcap_universe:
                self.logger.warning("⚠️ No mid-cap stocks after filter, using fallback")
                return self._get_fallback_universe()
            
            self.logger.info(f"✅ Trading universe: {len(midcap_universe)} mid-cap stocks")
            return midcap_universe
            
        except Exception as e:
            self.logger.error(f"Error getting trading universe: {e}")
            return self._get_fallback_universe()
    
    def _get_initial_screener_universe(self) -> List[str]:
        """
        Get initial universe from screener/database (not hardcoded).
        In production, this would query a screener or database.
        """
        # S&P 400 mid-cap index components + high-volume stocks
        # This is a starting point - PreFilter will apply additional filters
        return [
            # Airlines
            'AAL', 'ALK', 'JBLU', 'SAVE', 'HA',
            # Energy/Clean
            'PLUG', 'FCEL', 'BLDP', 'CLNE', 'BE',
            # Restaurants/Retail
            'CAKE', 'TXRH', 'BLMN', 'DRI', 'EAT',
            # Entertainment/Media
            'SIRI', 'LYV', 'MSG', 'MSGN',
            # Auto/Industrial
            'F', 'GM', 'RIVN', 'LCID',
            # Cruise/Leisure
            'CCL', 'RCL', 'NCLH',
            # Tech/Semi
            'AMD', 'INTC', 'MU', 'WDC',
            # Pharma/Bio
            'GILD', 'BIIB', 'VRTX', 'REGN',
            # Apparel
            'UAA', 'GPS', 'ANF', 'EXPR',
            # Energy
            'SWN', 'RIG', 'HP', 'DVN',
            # More restaurants
            'WEN', 'JACK', 'BJRI', 'CHUY',
        ]
    
    def _get_fallback_universe(self) -> List[str]:
        """Fallback universe of curated mid-cap stocks"""
        try:
            from ..data.fallback_universe import get_fallback_universe, DIVERSIFIED_MID_CAP
            universe = get_fallback_universe(diversified=True)
            self.logger.warning(f"⚠️ Using fallback mid-cap universe ({len(universe)} stocks)")
            return universe
        except ImportError:
            # Inline fallback if module not available
            self.logger.warning("⚠️ Using inline fallback universe (18 stocks)")
            return [
                "CAKE", "TXRH", "DKS",     # Consumer
                "CLF", "AA", "X",          # Industrial
                "SWN", "AR", "RIG",        # Energy
                "PLUG", "SEDG",            # Tech
                "INCY", "VTRS",            # Healthcare
                "AAL", "ALK",              # Airlines
                "HOOD", "SOFI",            # Financial
            ]
    
    def _apply_market_cap_filter(self, symbols: List[str]) -> List[str]:
        """
        Apply mid-cap filter ($2B-$10B) to symbol list.
        Uses data_loader to get market cap data.
        """
        midcap_symbols = []
        
        for symbol in symbols:
            try:
                # Get market cap from data loader or yfinance
                market_cap = self._get_market_cap(symbol)
                
                # Mid-cap filter: $2B - $10B
                if market_cap and 2_000_000_000 <= market_cap <= 10_000_000_000:
                    midcap_symbols.append(symbol)
                    self.logger.debug(f"✅ {symbol}: ${market_cap/1e9:.2f}B (mid-cap)")
                else:
                    if market_cap:
                        self.logger.debug(f"❌ {symbol}: ${market_cap/1e9:.2f}B (outside mid-cap range)")
                    
            except Exception as e:
                self.logger.debug(f"⚠️ {symbol}: Could not determine market cap")
                continue
        
        return midcap_symbols
    
    def _get_market_cap(self, symbol: str) -> Optional[float]:
        """Get market cap for a symbol"""
        try:
            import yfinance as yf
            ticker = yf.Ticker(symbol)
            info = ticker.info
            return info.get('marketCap', None)
        except Exception:
            return None
    
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get portfolio summary"""
        portfolio_state = self.portfolio_manager.get_portfolio_state()
        positions = self.position_tracker.get_positions()
        
        return self.portfolio_manager.generate_portfolio_summary(positions)

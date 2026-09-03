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
import pandas as pd
from typing import Dict, List
import threading

from core.data_loader import DataLoader
from core.momentum_strategy import MomentumStrategy
from core.enhanced_momentum_strategy import EnhancedMomentumStrategy
from core.risk_adjusted_sizing import VolatilityAdjustedSizer, PositionSizingConfig
from core.weekend_risk_manager import WeekendRiskManager
from risk import RiskManager
from adaptive_risk_manager import AdaptiveRiskManager
from regime_aware_controller import RegimeAwareController
from enhanced_regime_integration import EnhancedRegimeIntegrationManager
from enhanced_momentum_calculator import EnhancedMomentumCalculator, MomentumConfig
from risk_per_trade_sizer import RiskPerTradeSizer, RiskPerTradeConfig
from refined_position_sizing import RefinedPositionSizer, RefinedRiskConfig
from advanced_momentum_factor import AdvancedMomentumCalculator, AdvancedMomentumConfig
from sentiment_analyzer import FreeSentimentAnalyzer, PremarketValidator
from aggressive_swing_manager import AggressiveSwingManager
from enhanced_exit_logic import EnhancedExitLogicManager, ExitParameters
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
        
        # Initialize REFINED position sizer with regime-dependent risk management
        refined_risk_config = RefinedRiskConfig()
        self.refined_position_sizer = RefinedPositionSizer(refined_risk_config)
        
        # Initialize risk-per-trade position sizer (backup/comparison)
        risk_per_trade_config = RiskPerTradeConfig(
            risk_per_trade_pct=0.015,     # 1.5% risk per trade (WEEKLY ROI - was 0.02)
            max_position_pct=0.10,        # 10% max position (WEEKLY DIVERSIFICATION - was 0.20)
            min_position_pct=0.02,        # 2% min position (WEEKLY DIVERSIFICATION - was 0.05)
            max_concurrent_positions=20,  # 15-25 position range for weekly ROI (was 12)
            default_stop_loss_pct=0.015,  # 1.5% stop-loss (WEEKLY - was 0.025)
            min_stop_loss_pct=0.01,       # 1% min stop (WEEKLY - was 0.015)
            max_stop_loss_pct=0.025       # 2.5% max stop (WEEKLY - was 0.04)
        )
        self.risk_per_trade_sizer = RiskPerTradeSizer(risk_per_trade_config)
        
        # Keep volatility sizer for backup/comparison
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
        self.volatility_sizer = VolatilityAdjustedSizer(risk_config)
        
                # Initialize weekend risk manager
        weekend_config = {
            'max_weekend_exposure': 0.7,   # Max 70% exposure over weekend
            'high_vol_threshold': 0.4,     # Consider high if vol > 40%
            'momentum_threshold': 0.1,     # Strong momentum threshold
            'friday_hour_cutoff': 15,      # Stop new positions after 3 PM
        }
        self.weekend_risk = WeekendRiskManager(weekend_config)
        
        # Initialize regime-aware controller for market-driven strategy control
        self.regime_controller = RegimeAwareController()
        
        # Initialize ENHANCED regime integration manager for comprehensive regime optimization
        self.enhanced_regime_manager = EnhancedRegimeIntegrationManager()
        
        # Initialize aggressive swing manager for 15-25% profit targets and trailing stops
        self.aggressive_swing_manager = AggressiveSwingManager()
        
        # Initialize enhanced exit logic manager with WEEKLY ROI parameters
        exit_params = ExitParameters(
            use_atr_stops=True,                    # ATR-based stops
            atr_stop_multiplier=1.5,               # 1.5× ATR stop-loss (tighter for weekly)
            fixed_stop_pct=0.015,                  # 1.5% fixed cap (tighter for weekly)
            initial_profit_target=0.05,            # 5% minimum profit target (WEEKLY FOCUS)
            atr_profit_multiplier=2.5,             # 2.5× ATR profit target (lower for weekly)
            scale_out_levels=[0.03, 0.05, 0.08],   # Scale out at 3%, 5%, 8% (WEEKLY)
            base_time_stop_days=5,                 # 5 trading days (WEEKLY FOCUS)
            max_time_stop_days=7,                  # Maximum 7 days (WEEKLY)
            profitable_extension_days=2,           # Extra 2 days if profitable (WEEKLY)
            trailing_stop_pct=0.02,                # 2% trailing stop (tighter for weekly)
            trailing_activation_gain=0.03,         # Start trailing at 3% gain (WEEKLY)
            extended_hold_days=7,                  # 7 days maximum for weekly ROI
            momentum_extension_threshold=0.08      # 8% gain for extended holding (WEEKLY)
        )
        self.enhanced_exit_manager = EnhancedExitLogicManager(exit_params)
        
        # Initialize sentiment analysis and premarket validation
        self.sentiment_analyzer = FreeSentimentAnalyzer()
        self.premarket_validator = PremarketValidator()
        
        # Position tracking for exit conditions
        self.position_entry_dates = {}  # Track when positions were opened
        self.position_entry_prices = {}  # Track entry prices for stop/profit calculations
        
        # Get initial account info and set portfolio value
        account_info = self.trading_engine.get_account_info()
        self.portfolio_value = float(account_info['portfolio_value'])
        logging.info(f"💰 Starting Portfolio Value: ${self.portfolio_value:,.2f}")
        
        # NOW initialize risk managers that need portfolio_value
        self.risk_manager = RiskManager(initial_equity=self.portfolio_value)
        
        # Initialize adaptive risk manager for dynamic parameter adjustment
        self.adaptive_risk = AdaptiveRiskManager(
            initial_equity=self.portfolio_value,
            performance_file="adaptive_risk_performance.json"
        )
        
        # Initialize risk manager for stop-losses and profit targets
        self.risk_manager = RiskManager(initial_equity=self.portfolio_value)
        
        # Initialize adaptive risk manager for dynamic parameter adjustment
        self.adaptive_risk = AdaptiveRiskManager(
            initial_equity=self.portfolio_value,
            performance_file="adaptive_risk_performance.json"
        )
        
        # Initialize regime-aware controller for market-driven strategy control
        self.regime_controller = RegimeAwareController()
        
        # Initialize enhanced momentum calculator with ADVANCED risk-adjusted scoring
        advanced_momentum_config = AdvancedMomentumConfig()
        self.advanced_momentum = AdvancedMomentumCalculator(advanced_momentum_config)
        
        # Keep enhanced momentum calculator for comparison/backup
        momentum_config = MomentumConfig(
            short_period=10,                      # 2 weeks (unchanged)
            medium_period=21,                     # 1 month (unchanged)
            long_period=63,                       # 3 months (extended from 42)
            volatility_lookback=21,
            min_sharpe_threshold=-0.5,            # More lenient (was 0.0)
            min_volume=5_000_000,                 # Higher volume for swing liquidity
            min_price=20.0,                       # Quality stocks only (was 5.0)
            max_volatility=2.0,                   # Allow higher volatility (was 1.0)
            breakout_momentum_threshold=0.15,     # 15% momentum for breakouts
            breakout_volume_multiplier=2.0,       # 2x volume surge detection  
            relative_strength_threshold=1.2       # 20% outperformance vs market
        )
        self.enhanced_momentum = EnhancedMomentumCalculator(momentum_config)
        
        # Initialize aggressive swing trading manager
        self.swing_manager = AggressiveSwingManager()
        
        # Initialize sentiment analysis and premarket validation
        self.sentiment_analyzer = FreeSentimentAnalyzer()
        self.premarket_validator = PremarketValidator()
        
        # Position tracking for exit conditions
        self.position_entry_dates = {}  # Track when positions were opened
        self.position_entry_prices = {}  # Track entry prices for stop/profit calculations
        
        # Get initial account info
        account_info = self.trading_engine.get_account_info()
        self.portfolio_value = float(account_info['portfolio_value'])
        logging.info(f"💰 Starting Portfolio Value: ${self.portfolio_value:,.2f}")
        
        # Setup timezone for market hours
        self.eastern = pytz.timezone('US/Eastern')
        
        logging.info("✅ Enhanced system initialized with:")
        logging.info(f"   📊 Symbol Universe: {len(self.symbols)} stocks")
        logging.info(f"   🎯 Risk-Per-Trade Sizing: {risk_per_trade_config.risk_per_trade_pct:.2%} per trade")
        logging.info(f"   📈 Max Position Limit: {risk_per_trade_config.max_position_pct:.0%}")
        logging.info(f"   �️ Stop-Loss Range: {risk_per_trade_config.min_stop_loss_pct:.1%}-{risk_per_trade_config.max_stop_loss_pct:.0%}")
        logging.info(f"   💰 Position Size Range: {risk_per_trade_config.min_position_pct:.0%}-{risk_per_trade_config.max_position_pct:.0%} of portfolio")
        logging.info(f"   🔍 Sentiment Analysis: Yahoo Finance + Alpaca News + Technical Indicators")
        logging.info(f"   🌅 Premarket Validation: 8:00 AM ET (Gap analysis + News sentiment)")
        
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
    
    def generate_signals(self, market_data: Dict, date: datetime = None) -> List[Dict]:
        """
        Generate trading signals for backtesting integration
        
        Args:
            market_data: Dictionary of symbol -> DataFrame of OHLCV data
            date: Current date for historical signal generation (optional)
            
        Returns:
            List of signal dictionaries with symbol, action, confidence, etc.
        """
        signals = []
        
        try:
            # Use current regime detection for signal filtering
            current_regime, regime_confidence = self.enhanced_regime_manager.update_regime_detection(market_data)
            
            # Check if we should generate new signals in current regime
            if not self.enhanced_regime_manager.should_allow_new_positions():
                logging.debug(f"🛑 No signals generated - regime {current_regime} blocks new positions")
                return signals
            
            # Get regime parameters for signal generation
            regime_summary = self.enhanced_regime_manager.get_regime_summary()
            min_confidence = regime_summary['min_signal_confidence']
            max_positions = regime_summary['max_positions']
            
            # Generate momentum signals using advanced momentum calculator
            momentum_signals = []
            for symbol, data in market_data.items():
                if len(data) < 50:  # Need sufficient history
                    continue
                
                try:
                    # Calculate advanced momentum with regime-specific parameters
                    # Map regime to appropriate momentum period
                    if current_regime == 'bull':
                        momentum_period = 10  # Shorter period for bull markets
                    elif current_regime == 'bear':
                        momentum_period = 20  # Longer period for bear markets
                    else:  # sideways
                        momentum_period = 15  # Medium period for sideways markets
                    
                    momentum_score = self.advanced_momentum.calculate_risk_adjusted_momentum(
                        data['close'], momentum_period
                    )
                    
                    # Calculate signal confidence based on momentum quality
                    confidence = min(0.95, abs(momentum_score) * 2)  # Scale to 0-0.95
                    
                    # Apply regime-specific confidence filter
                    if confidence >= min_confidence and momentum_score > 0.05:
                        signal = {
                            'symbol': symbol,
                            'action': 'buy',
                            'momentum_score': momentum_score,
                            'confidence': confidence,
                            'regime': current_regime,
                            'signal_type': 'momentum',
                            'current_price': data['close'].iloc[-1] if len(data) > 0 else None,
                            'entry_reason': f'{current_regime}_momentum_signal'
                        }
                        momentum_signals.append(signal)
                        
                except Exception as e:
                    logging.debug(f"Signal generation error for {symbol}: {e}")
                    continue
            
            # Sort by momentum score and limit by regime max positions
            momentum_signals.sort(key=lambda x: x['momentum_score'], reverse=True)
            signals = momentum_signals[:max_positions]
            
            logging.debug(f"Generated {len(signals)} signals in {current_regime} regime")
            
        except Exception as e:
            logging.warning(f"Signal generation failed: {e}")
            # Return empty list if signal generation fails
            signals = []
        
        return signals
        
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
            
            # 2. ENHANCED Regime detection and comprehensive strategy adjustment
            logging.info("🌐 Detecting market regime with enhanced integration...")
            current_regime, regime_confidence = self.enhanced_regime_manager.update_regime_detection(market_data)
            
            regime_summary = self.enhanced_regime_manager.get_regime_summary()
            logging.info(f"📊 Current Regime: {current_regime.upper()} (confidence: {regime_confidence:.1%})")
            logging.info(f"   � Max Exposure: {regime_summary['max_exposure_pct']:.0%}")
            logging.info(f"   📏 Position Multiplier: {regime_summary['position_size_multiplier']:.1f}x")
            logging.info(f"   🛡️ Stop Multiplier: {regime_summary['stop_loss_multiplier']:.1f}x")
            logging.info(f"   📈 Momentum Lookback: {regime_summary['momentum_lookback_multiplier']:.1f}x")
            logging.info(f"   🎯 Min Signal Confidence: {regime_summary['min_signal_confidence']:.1%}")
            logging.info(f"   🎲 Max Positions: {regime_summary['max_positions']}")
            
            # Check regime-based trading permissions
            if not self.enhanced_regime_manager.should_allow_new_positions():
                logging.warning("🛑 REGIME BLOCK: New positions not allowed in current market regime")
                # Still check exits for existing positions
                self.check_exit_conditions()
                return
            
            # Check if positions should be reduced due to regime
            if self.enhanced_regime_manager.should_reduce_positions():
                logging.warning("⚠️ REGIME SIGNAL: Position reduction required")
                self._handle_regime_position_reduction()
            
            # Get regime-adjusted maximum exposure
            max_exposure = self.enhanced_regime_manager.get_maximum_exposure(self.portfolio_value)
            logging.info(f"💰 Regime-adjusted max exposure: ${max_exposure:,.0f}")
            
            if max_exposure == 0:
                logging.warning("💰 CASH MODE: Regime requires 0% exposure - moving to cash")
                if self.enhanced_regime_manager.should_enable_short_setups():
                    logging.info("📉 SHORT SETUPS: Regime enables short selling opportunities")
                    # TODO: Implement short setup logic
                return
            
            # 3. Generate momentum signals with ENHANCED regime-adjusted parameters
            logging.info("🎯 Generating regime-optimized momentum signals...")
            
            # Get regime-adjusted momentum parameters
            base_lookback = getattr(self.momentum_strategy, 'lookback_1m', 21)
            base_threshold = 0.15  # Base momentum threshold
            adjusted_lookback, adjusted_threshold = self.enhanced_regime_manager.get_regime_momentum_parameters(
                base_lookback, base_threshold
            )
            
            # Configure enhanced momentum calculator with regime adjustments
            regime_momentum_config = MomentumConfig(
                short_period=max(10, int(10 * regime_summary['momentum_lookback_multiplier'])),
                medium_period=adjusted_lookback,
                long_period=max(42, int(63 * regime_summary['momentum_lookback_multiplier'])),
                volatility_lookback=21,
                min_sharpe_threshold=-0.5,
                min_volume=5_000_000,
                min_price=20.0,
                max_volatility=2.0,
                breakout_momentum_threshold=adjusted_threshold,
                breakout_volume_multiplier=2.0,
                relative_strength_threshold=1.2
            )
            
            # Update enhanced momentum calculator with regime-adjusted config
            self.enhanced_momentum.config = regime_momentum_config
            
            # 3. Generate ADVANCED risk-adjusted momentum signals
            logging.info("🎯 Generating advanced risk-adjusted momentum signals...")
            
            # Use ADVANCED momentum calculator with regime-dependent weightings
            advanced_momentum_signals = self.advanced_momentum.rank_stocks_by_advanced_momentum(
                market_data,
                regime=current_regime,
                max_selections=20,
                min_momentum_threshold=0.1
            )
            
            if not advanced_momentum_signals:
                logging.info("📊 No advanced momentum signals generated for current regime")
                return
                
            # Convert to standard signal format with enhanced metrics
            momentum_signals = []
            for signal in advanced_momentum_signals:
                momentum_signals.append({
                    'symbol': signal['symbol'],
                    'momentum_score': signal['momentum_score'],
                    'confidence': min(1.0, max(0.0, signal['quality_score'])),  # Use quality score as confidence
                    'quality': signal['quality'],
                    'volatility': signal.get('volatility', 0),
                    'short_momentum': signal.get('short_momentum', 0),
                    'medium_momentum': signal.get('medium_momentum', 0),
                    'long_momentum': signal.get('long_momentum', 0),
                    'regime_optimized': True,
                    'advanced_scoring': True
                })
                
            logging.info(f"📊 Generated {len(momentum_signals)} advanced momentum signals")
            
            # Log top signals with quality ratings
            logging.info("🏆 Top Risk-Adjusted Momentum Signals:")
            for i, signal in enumerate(momentum_signals[:5], 1):
                symbol = signal['symbol']
                score = signal['momentum_score']
                quality = signal['quality']
                confidence = signal['confidence']
                logging.info(f"   {i}. {symbol}: Score {score:.3f} | Quality: {quality} | Confidence: {confidence:.1%}")
            
            # 4. Filter signals by regime requirements
            regime_filtered_signals = self.enhanced_regime_manager.filter_signals_by_regime(momentum_signals)
            
            if not regime_filtered_signals:
                logging.info(f"🛑 All signals filtered out by regime {current_regime} requirements")
                return
                
            logging.info(f"🎯 Regime-filtered signals: {len(momentum_signals)} → {len(regime_filtered_signals)}")
            
            # 5. Apply REFINED risk-per-trade position sizing with regime optimization
            logging.info("🎯 Applying refined position sizing with regime optimization...")
            
            # Use refined position sizer with regime-dependent risk percentages
            refined_signals = self.refined_position_sizer.calculate_positions_for_signals(
                regime_filtered_signals,
                market_data,
                min(self.portfolio_value, max_exposure),  # Limit by regime exposure
                current_regime,
                self.adaptive_risk  # Use adaptive stop-loss percentages
            )
            
            # Fallback to original risk-per-trade sizer if needed
            if not refined_signals:
                logging.warning("⚠️ Refined sizing failed, falling back to original risk-per-trade sizer")
                
                # Get regime-adjusted risk configuration
                regime_adjusted_config = self.enhanced_regime_manager.get_regime_adjusted_risk_config(
                    self.risk_per_trade_sizer.config
                )
                
                # Temporarily update risk sizer with regime adjustments
                original_config = self.risk_per_trade_sizer.config
                if hasattr(regime_adjusted_config, 'risk_per_trade_pct'):
                    # RiskPerTradeConfig object
                    self.risk_per_trade_sizer.config = regime_adjusted_config
                else:
                    # Dictionary - update manually
                    self.risk_per_trade_sizer.config.risk_per_trade_pct = regime_adjusted_config['risk_per_trade_pct']
                    self.risk_per_trade_sizer.config.max_position_pct = regime_adjusted_config['max_position_pct']
                    if 'max_stop_loss_pct' in regime_adjusted_config:
                        self.risk_per_trade_sizer.config.max_stop_loss_pct = regime_adjusted_config['max_stop_loss_pct']
                
                refined_signals = self.risk_per_trade_sizer.calculate_positions_for_signals(
                    regime_filtered_signals,
                    market_data,
                    min(self.portfolio_value, max_exposure),  # Limit by regime exposure
                    self.adaptive_risk  # Use adaptive stop-loss percentages
                )
                
                # Restore original config
                self.risk_per_trade_sizer.config = original_config
            
            # Rename for consistency with existing code
            risk_adjusted_signals = refined_signals
            
            # 4. Apply Friday weekend risk filters
            current_time = datetime.now(self.eastern)
            risk_adjusted_signals = self.weekend_risk.apply_friday_filters(
                risk_adjusted_signals, 
                current_time
            )
            
            # 5. AGGRESSIVE SWING TRADING: Limit to 5 concentrated positions
            max_new_positions = self.risk_per_trade_sizer.config.max_concurrent_positions
            current_position_count = len([pos for pos in current_positions.values() if pos['shares'] > 0])
            available_slots = max_new_positions - current_position_count
            
            # Filter to top signals if we need to limit new positions
            buy_signals = [s for s in risk_adjusted_signals if s.get('action') == 'BUY']
            if len(buy_signals) > available_slots:
                # Sort by momentum score and take top signals
                buy_signals.sort(key=lambda x: x.get('momentum_score', 0), reverse=True)
                risk_adjusted_signals = buy_signals[:available_slots] + [s for s in risk_adjusted_signals if s.get('action') != 'BUY']
                logging.info(f"🎯 AGGRESSIVE SWING: Limited to top {available_slots} new positions ({current_position_count}/{max_new_positions} slots used)")
            
            # Log top signals with risk-per-trade adjustments
            logging.info("📈 Top risk-per-trade sized signals:")
            for i, signal in enumerate(risk_adjusted_signals[:8], 1):
                symbol = signal['symbol']
                shares = signal.get('shares', 0)
                value = signal.get('position_value', 0)
                risk_amount = signal.get('risk_amount', 0)
                stop_loss_pct = signal.get('stop_loss_pct', 0)
                position_pct = signal.get('position_pct', 0)
                momentum = signal.get('momentum_score', 0)
                logging.info(f"   {i}. {symbol}: {shares} shares | ${value:,.0f} ({position_pct:.1%}) | Risk: ${risk_amount:.0f} | Stop: {stop_loss_pct:.1%} | Mom: {momentum:.3f}")
            
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
                    
                    # Track entry for new buy positions (for exit monitoring)
                    if side == 'buy':
                        try:
                            # Get current market price for entry tracking
                            latest_data = self.data_loader.get_latest_data([symbol])
                            if symbol in latest_data and not latest_data[symbol].empty:
                                entry_price = latest_data[symbol]['close'].iloc[-1]
                                entry_date = datetime.now()
                                
                                # Legacy tracking (for backwards compatibility)
                                self.position_entry_prices[symbol] = entry_price
                                self.position_entry_dates[symbol] = entry_date.strftime('%Y-%m-%d')
                                
                                # Enhanced exit logic tracking
                                self.enhanced_exit_manager.add_position(
                                    symbol=symbol,
                                    entry_price=entry_price,
                                    shares=shares,
                                    entry_date=entry_date
                                )
                                
                                logging.info(f"📝 Enhanced tracking: {symbol} @ ${entry_price:.2f} with ATR-based exits")
                        except Exception as e:
                            logging.warning(f"Could not track entry for {symbol}: {e}")
                    
                    # Remove position from enhanced exit manager if selling all
                    elif side == 'sell' and trade.get('target_position', 0) == 0:
                        removed_position = self.enhanced_exit_manager.remove_position(symbol)
                        if removed_position:
                            logging.info(f"📝 Removed {symbol} from enhanced exit tracking")
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
    
    def _handle_regime_position_reduction(self):
        """Handle position reduction required by regime change"""
        try:
            current_positions = self.trading_engine.get_positions()
            regime_summary = self.enhanced_regime_manager.get_regime_summary()
            
            target_exposure_pct = regime_summary['max_exposure_pct']
            current_exposure = sum(pos['market_value'] for pos in current_positions.values() if pos['shares'] > 0)
            target_exposure_value = self.portfolio_value * target_exposure_pct
            
            if current_exposure <= target_exposure_value:
                logging.info(f"✅ Current exposure ${current_exposure:,.0f} within regime limit ${target_exposure_value:,.0f}")
                return
            
            excess_exposure = current_exposure - target_exposure_value
            logging.warning(f"⚠️ Excess exposure: ${excess_exposure:,.0f} must be reduced")
            
            # Sort positions by risk (highest volatility first for reduction)
            position_list = [(symbol, pos) for symbol, pos in current_positions.items() if pos['shares'] > 0]
            position_list.sort(key=lambda x: x[1].get('volatility', 0.2), reverse=True)
            
            # Reduce positions starting with highest risk
            remaining_to_reduce = excess_exposure
            for symbol, position in position_list:
                if remaining_to_reduce <= 0:
                    break
                
                position_value = position['market_value']
                reduction_pct = min(0.5, remaining_to_reduce / position_value)  # Max 50% reduction per position
                shares_to_sell = int(position['shares'] * reduction_pct)
                
                if shares_to_sell > 0:
                    logging.warning(f"📉 Regime reduction: Selling {shares_to_sell} shares of {symbol}")
                    self.trading_engine.submit_order(symbol, shares_to_sell, 'sell', 'market')
                    remaining_to_reduce -= shares_to_sell * position['current_price']
            
        except Exception as e:
            logging.error(f"Error handling regime position reduction: {e}")

    def check_exit_conditions(self):
        """Monitor all positions for stop-loss, profit targets, and time stops"""
        try:
            if not self.is_market_hours():
                logging.info("⏰ Market closed - exit monitoring skipped")
                return
                
            logging.info("🛡️ Checking exit conditions for all positions...")
            
            # Get current positions and market data
            positions = self.trading_engine.get_positions()
            if not positions:
                logging.info("📋 No positions to monitor")
                return
                
            exit_trades = []
            current_date = datetime.now().strftime('%Y-%m-%d')
            
            for symbol, position in positions.items():
                current_price = float(position.get('current_price', 0))
                shares = float(position['quantity'])
                unrealized_pnl = float(position['unrealized_pnl'])
                
                if current_price <= 0:
                    logging.warning(f"⚠️ Invalid price for {symbol}: ${current_price:.2f}")
                    continue
                
                # Use Enhanced Exit Logic Manager
                exit_result = self.enhanced_exit_manager.update_position(symbol, current_price)
                
                if exit_result['exit_signal']:
                    exit_reason = exit_result['reason']
                    exit_type = exit_result['exit_type']
                    shares_to_exit = exit_result.get('shares_to_exit', shares)
                    scale_level = exit_result.get('scale_level')
                    priority = exit_result.get('priority', 10)
                    
                    # Handle partial exits (scaling out)
                    if exit_type == 'scale_out' and shares_to_exit < shares:
                        exit_trades.append({
                            'symbol': symbol,
                            'shares': int(shares_to_exit),
                            'side': 'sell',
                            'reason': exit_reason,
                            'exit_type': exit_type,
                            'current_price': current_price,
                            'pnl': unrealized_pnl * (shares_to_exit / shares),
                            'partial_exit': True,
                            'scale_level': scale_level,
                            'priority': priority
                        })
                        logging.info(f"🚨 PARTIAL EXIT: {symbol} - {exit_reason}")
                    else:
                        # Full exit
                        exit_trades.append({
                            'symbol': symbol,
                            'shares': int(shares_to_exit),
                            'side': 'sell',
                            'reason': exit_reason,
                            'exit_type': exit_type,
                            'current_price': current_price,
                            'pnl': unrealized_pnl,
                            'partial_exit': False,
                            'priority': priority
                        })
                        logging.info(f"🚨 FULL EXIT: {symbol} - {exit_reason}")
            
            # Sort exit trades by priority (lower number = higher priority)
            exit_trades.sort(key=lambda x: x.get('priority', 10))
            
            # Execute exit trades
            if exit_trades:
                logging.info(f"📤 Executing {len(exit_trades)} enhanced exit trades...")
                for trade in exit_trades:
                    symbol = trade['symbol']
                    shares = trade['shares']
                    reason = trade['reason']
                    exit_type = trade['exit_type']
                    is_partial = trade.get('partial_exit', False)
                    scale_level = trade.get('scale_level')
                    
                    try:
                        order_result = self.trading_engine.submit_order(
                            symbol=symbol,
                            quantity=shares,
                            side='sell'
                        )
                        
                        if order_result:
                            if is_partial:
                                # Record partial exit with enhanced exit manager
                                self.enhanced_exit_manager.execute_partial_exit(symbol, shares, scale_level)
                                logging.info(f"✅ PARTIAL EXIT: {symbol} {shares} shares - {reason} - Order: {order_result['order_id']}")
                            else:
                                # Full exit - remove from tracking
                                removed_position = self.enhanced_exit_manager.remove_position(symbol)
                                if symbol in self.position_entry_dates:
                                    del self.position_entry_dates[symbol]
                                if symbol in self.position_entry_prices:
                                    del self.position_entry_prices[symbol]
                                
                                logging.info(f"✅ FULL EXIT: {symbol} {shares} shares - {reason} - Order: {order_result['order_id']}")
                            
                            # Record trade for adaptive learning
                            entry_date_for_trade = self.position_entry_dates.get(symbol, datetime.now().strftime('%Y-%m-%d'))
                            entry_price_for_trade = self.position_entry_prices.get(symbol, trade['current_price'])
                            
                            self.adaptive_risk.record_trade(
                                symbol=symbol,
                                entry_price=entry_price_for_trade,
                                exit_price=trade['current_price'],
                                shares=shares,
                                entry_date=entry_date_for_trade,
                                exit_date=datetime.now().strftime('%Y-%m-%d'),
                                exit_reason=f"{exit_type}:{reason}"
                            )
                        else:
                            logging.error(f"❌ Exit order failed for {symbol}")
                            
                    except Exception as e:
                        logging.error(f"❌ Error executing exit for {symbol}: {e}")
            
            # Log enhanced exit summary
            exit_summary = self.enhanced_exit_manager.get_exit_summary()
            logging.info(f"📊 Enhanced Exit Summary: {exit_summary['total_positions']} tracked, "
                        f"{exit_summary['trailing_active']} trailing, "
                        f"{exit_summary['scaled_positions']} scaled, "
                        f"{exit_summary['extended_holds']} extended")
                
        except Exception as e:
            logging.error(f"💥 Error checking exit conditions: {e}")
    
    def portfolio_summary(self):
        """Enhanced portfolio summary with risk metrics and premarket validation"""
        try:
            current_time = datetime.now(self.eastern)
            is_premarket = dt_time(6, 0) <= current_time.time() <= dt_time(9, 30)
            
            logging.info("📊 Enhanced Portfolio Summary")
            if is_premarket:
                logging.info("🌅 PREMARKET VALIDATION MODE")
            logging.info("=" * 60)
            
            account_info = self.trading_engine.get_account_info()
            positions = self.trading_engine.get_positions()
            
            portfolio_value = float(account_info['portfolio_value'])
            cash = float(account_info['cash'])
            
            logging.info(f"💰 Total Value: ${portfolio_value:,.2f}")
            logging.info(f"💵 Cash: ${cash:,.2f} ({cash/portfolio_value:.1%})")
            logging.info(f"📈 Positions: {len(positions)} symbols")
            
            # Get market data for current positions and watchlist
            symbols_to_analyze = list(positions.keys()) + self.symbols[:10]  # Top 10 watchlist
            symbols_to_analyze = list(set(symbols_to_analyze))  # Remove duplicates
            
            try:
                market_data = self.data_loader.get_historical_data_bulk(symbols_to_analyze, limit=50)
                if hasattr(market_data, 'empty') and market_data.empty:
                    # Convert DataFrame to dict if needed
                    market_data_dict = {}
                    for symbol in symbols_to_analyze[:5]:  # Limit to avoid rate limits
                        try:
                            data = self.data_loader.get_historical_data(symbol, limit=50)
                            if data is not None and not data.empty:
                                market_data_dict[symbol] = data
                        except:
                            continue
                    market_data = market_data_dict
                elif isinstance(market_data, pd.DataFrame):
                    # Handle DataFrame response - convert to dict
                    market_data = {}
            except Exception as e:
                logging.warning(f"⚠️ Market data loading error: {e}")
                market_data = {}
            
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
            
            # PREMARKET SENTIMENT & NEWS ANALYSIS (8:00 AM focus)
            if is_premarket and market_data:
                logging.info("\n🌅 PREMARKET SENTIMENT & NEWS ANALYSIS:")
                logging.info("-" * 50)
                
                # Analyze sentiment for current positions first
                if positions:
                    logging.info("📊 Current Position Sentiment:")
                    for symbol in list(positions.keys())[:10]:  # Top 10 positions
                        symbol_data = market_data.get(symbol)
                        sentiment = self.sentiment_analyzer.analyze_symbol_sentiment(symbol, symbol_data)
                        
                        risk_indicator = "🔴" if sentiment.risk_flags else ("🟡" if sentiment.overall_score < -0.2 else "🟢")
                        logging.info(f"   {risk_indicator} {symbol}: Sentiment {sentiment.overall_score:+.2f} "
                                   f"(conf: {sentiment.confidence:.1%}) | News: {sentiment.news_count}")
                        
                        if sentiment.risk_flags:
                            logging.info(f"      ⚠️ Risk Flags: {', '.join(sentiment.risk_flags)}")
                        if sentiment.key_themes:
                            logging.info(f"      📰 Themes: {', '.join(sentiment.key_themes[:3])}")
                
                # Premarket validation for watchlist symbols
                logging.info("\n🎯 Watchlist Premarket Validation:")
                watchlist_symbols = [s for s in self.symbols[:8] if s not in positions]  # Avoid current positions
                
                if watchlist_symbols:
                    premarket_signals = self.premarket_validator.validate_portfolio_premarket(
                        watchlist_symbols, market_data
                    )
                    
                    # Show the most interesting signals
                    buy_signals = [s for s in premarket_signals.values() if s.recommendation == "BUY"]
                    avoid_signals = [s for s in premarket_signals.values() if s.recommendation == "AVOID"]
                    
                    if buy_signals:
                        logging.info("   🚀 BUY Opportunities:")
                        for signal in buy_signals[:3]:
                            logging.info(f"      {signal.symbol}: Gap {signal.gap_pct:+.1f}% | "
                                       f"Sentiment {signal.sentiment_score:+.2f} | {signal.reasoning}")
                    
                    if avoid_signals:
                        logging.info("   🛑 AVOID Signals:")
                        for signal in avoid_signals[:3]:
                            logging.info(f"      {signal.symbol}: Gap {signal.gap_pct:+.1f}% | "
                                       f"Risk: {signal.risk_level} | {signal.reasoning}")
                    
                    if not buy_signals and not avoid_signals:
                        logging.info("   📊 No strong premarket signals - normal market open expected")
                
                logging.info("\n💡 Premarket Intelligence Summary:")
                total_news_items = sum(s.news_count for s in [self.sentiment_analyzer.analyze_symbol_sentiment(sym) for sym in symbols_to_analyze[:5]])
                logging.info(f"   📰 Total News Items Analyzed: {total_news_items}")
                logging.info(f"   🔍 Sentiment Sources: Yahoo Finance + Alpaca News + Technical Indicators")
                logging.info(f"   ⏰ Next Update: 9:30 AM ET (Market Open Execution)")
            
            # Display current adaptive risk parameters and regime status
            current_params = self.adaptive_risk.get_current_parameters()
            performance = self.adaptive_risk.get_performance_summary()
            regime_summary = self.regime_controller.get_regime_summary()
            
            logging.info(f"\n🌐 Market Regime Analysis:")
            logging.info(f"   Current Regime: {regime_summary['current_regime']} (confidence: {regime_summary['confidence']:.1%})")
            logging.info(f"   Max Exposure: {regime_summary['max_exposure_pct']:.0%} | Max Positions: {regime_summary['max_positions']}")
            logging.info(f"   Signal Threshold: {regime_summary['min_signal_confidence']:.1%} | Lookback Multiplier: {regime_summary['lookback_multiplier']:.1f}x")
            
            logging.info(f"\n🧠 Adaptive Risk Parameters:")
            logging.info(f"   Stop Loss: {current_params.stop_loss_pct:.1%} | Profit Target: {current_params.profit_target_pct:.1%} | Time Stop: {current_params.time_stop_days}d")
            if performance['total_trades'] > 0:
                logging.info(f"   Performance: {performance['total_trades']} trades | {performance['win_rate']:.1%} win rate | ${performance['avg_trade_pnl']:.2f} avg P&L")
            
        except Exception as e:
            logging.error(f"Error getting enhanced portfolio summary: {e}")
    
    def setup_schedule(self):
        """Setup the enhanced trading schedule with strategic timing windows"""
        logging.info("📅 Setting up strategic trading schedule...")
        
        # Pre-market validation check (8:00 AM ET) - Strategic Window: 7:30-9:00 AM
        schedule.every().day.at("08:00").do(self.portfolio_summary).tag('validation')
        
        # Market open execution window (9:30 AM ET) - Strategic Window: 9:30-10:30 AM
        schedule.every().day.at("09:30").do(self.execute_enhanced_momentum_cycle).tag('execution')
        
        # Exit monitoring check (9:45 AM ET) - Monitor stops/targets during execution window
        schedule.every().day.at("09:45").do(self.check_exit_conditions).tag('exit_monitoring')
        
        # Mid-execution follow-up (10:00 AM ET) - Continue execution window
        schedule.every().day.at("10:00").do(self.execute_enhanced_momentum_cycle).tag('execution')
        
        # Mid-day exit monitoring (12:00 PM ET) - Check for stops/targets
        schedule.every().day.at("12:00").do(self.check_exit_conditions).tag('exit_monitoring')
        
        # Market close management window (15:00 PM ET) - Strategic Window: 3:00-4:00 PM
        schedule.every().day.at("15:00").do(self.execute_enhanced_momentum_cycle).tag('management')
        
        # Exit monitoring before close (15:15 PM ET) - Final check for stops/targets
        schedule.every().day.at("15:15").do(self.check_exit_conditions).tag('exit_monitoring')
        
        # Final management check (15:30 PM ET) - Continue management window
        schedule.every().day.at("15:30").do(self.execute_enhanced_momentum_cycle).tag('management')
        
        # Friday weekend risk check (15:45 PM ET) - Keep existing Friday protection
        schedule.every().friday.at("15:45").do(self.friday_weekend_risk_check).tag('friday_risk')
        
        # Strategic scan after market close (16:15 PM ET) - Strategic Window: After 4:15 PM
        schedule.every().day.at("16:15").do(self.portfolio_summary).tag('strategic_scan')
        
        logging.info("✅ Strategic schedule configured:")
        logging.info("   � 08:00 ET - Pre-Market Validation Check")
        logging.info("   🚀 09:30 ET - Market Open Execution Window")
        logging.info("   � 10:00 ET - Mid-Execution Follow-up")
        logging.info("   ⚖️ 15:00 ET - Market Close Management Window")
        logging.info("   🎯 15:30 ET - Final Management Check")
        logging.info("   🛡️ 15:45 ET - Friday Weekend Risk Check (Fridays only)")
        logging.info("   📊 16:15 ET - Strategic Scan (After Market Close)")
        
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

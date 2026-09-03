"""
Main trading engine - coordinates all trading operations
Simplified extraction from traders/short_cycle_trader.py

This is a SIMPLIFIED version focusing on core trading loop.
Full extraction of 2900-line ShortCycleTrader will be completed in Phase 6.
"""

import logging
import datetime as dt
from typing import List, Optional
from dataclasses import dataclass

from bot_v2.config.trading_config import ShortCycleConfig
from bot_v2.models.signals import AISignal
from bot_v2.models.positions import ShortCyclePosition, PositionStatus
from bot_v2.signal_generation.signal_generator import AISignalGenerator
from bot_v2.risk_management.stop_loss_manager import AIStopLossManager
from bot_v2.risk_management.position_sizer import AIConfidencePositionSizer
from bot_v2.risk_management.portfolio_risk_manager import AIPredictiveRiskManager
from bot_v2.market_analysis.regime_detector import AIMarketRegimeDetector


class SimplifiedTrader:
    """
    Simplified trading engine that coordinates bot_v2 modules
    
    This is a lightweight version for Phase 5.
    Full ShortCycleTrader extraction (2900 lines) deferred to Phase 6.
    """
    
    def __init__(self, config: Optional[ShortCycleConfig] = None):
        self.config = config or ShortCycleConfig()
        self.logger = self._setup_logging()
        
        # Initialize AI components using extracted modules
        self.signal_generator = AISignalGenerator(
            self.config,
            price_fetcher=None  # Can be set later
        )
        self.stop_manager = AIStopLossManager(self.config)
        self.position_sizer = AIConfidencePositionSizer(self.config)
        self.risk_manager = AIPredictiveRiskManager(self.config)
        self.regime_detector = AIMarketRegimeDetector(self.config)
        
        # Trading state
        self.positions: List[ShortCyclePosition] = []
        self.daily_pnl = 0.0
        self.weekly_pnl = 0.0
        self.trades_today = 0
        
        self.logger.info("✅ SimplifiedTrader initialized with bot_v2 modules")
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging"""
        logger = logging.getLogger("SimplifiedTrader")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def run_trading_cycle(self, universe: List[str], market_data: dict):
        """
        Execute a single trading cycle
        
        Args:
            universe: List of symbols to analyze
            market_data: Dictionary of symbol -> DataFrame with price data
        """
        self.logger.info(f"🚀 Running trading cycle with {len(universe)} symbols")
        
        # 1. Detect market regime
        regime_info = self.regime_detector.get_current_regime(market_data)
        self.logger.info(f"📊 Market Regime: {regime_info['regime']}")
        
        # 2. Generate signals
        signals = self.signal_generator.generate_signals(
            universe, 
            market_data,
            active_positions=self.positions
        )
        
        self.logger.info(f"🎯 Generated {len(signals)} signals")
        
        # 3. Assess portfolio risk
        risk_assessment = self.risk_manager.assess_portfolio_risk(
            signals,
            self.positions,
            market_data
        )
        
        if not risk_assessment['approved']:
            self.logger.warning(f"⚠️ Portfolio risk check failed: {risk_assessment['warnings']}")
            return
        
        # 4. Size and execute positions
        for signal in signals:
            if self.trades_today >= self.config.max_positions_per_day:
                self.logger.info("📊 Max positions reached for today")
                break
            
            # Calculate position size
            stop_price, stop_pct = self.stop_manager.calculate_optimal_stop(
                signal,
                market_data.get(signal.symbol)
            )
            
            shares, position_value = self.position_sizer.calculate_position_size(
                signal,
                stop_price,
                self.config.portfolio_value
            )
            
            if shares == 0:
                self.logger.debug(f"❌ {signal.symbol}: Position size too small, skipping")
                continue
            
            # Create position (in real bot, this would execute trade)
            position = ShortCyclePosition(
                symbol=signal.symbol,
                entry_date=dt.date.today(),
                exit_date=dt.date.today() + dt.timedelta(days=1),
                entry_price=signal.entry_price,
                position_size_shares=shares,
                position_size_dollars=position_value,
                stop_price=stop_price,
                target_price=signal.entry_price * 1.03,  # 3% target
                ai_signal=signal,
                status=PositionStatus.ENTERED
            )
            
            self.positions.append(position)
            self.trades_today += 1
            
            self.logger.info(
                f"✅ {signal.symbol}: Entered {shares} shares @ ${signal.entry_price:.2f} "
                f"(${position_value:.0f} position, stop @ ${stop_price:.2f})"
            )
        
        self.logger.info(f"🎉 Cycle complete: {self.trades_today} positions entered")
    
    def process_exits(self, current_prices: dict):
        """
        Process exits for open positions
        
        Args:
            current_prices: Dictionary of symbol -> current price
        """
        exits_processed = 0
        
        for position in self.positions:
            if position.status != PositionStatus.ENTERED:
                continue
            
            current_price = current_prices.get(position.symbol)
            if not current_price:
                continue
            
            # Update position with current price
            position.update_current_price(current_price)
            
            # Check for stop loss
            if position.is_stopped_out(current_price):
                self.logger.info(
                    f"🛑 {position.symbol}: Stop loss hit @ ${current_price:.2f}"
                )
                position.status = PositionStatus.EXITED
                position.exit_reason = "STOP_LOSS"
                exits_processed += 1
                continue
            
            # Check for fast exit
            if self.stop_manager.should_fast_exit(position, current_price):
                self.logger.info(
                    f"⚡ {position.symbol}: Fast exit @ ${current_price:.2f}"
                )
                position.status = PositionStatus.EXITED
                position.exit_reason = "FAST_EXIT"
                exits_processed += 1
                continue
            
            # Check for D+1 exit
            today = dt.date.today()
            if position.should_force_exit(today):
                self.logger.info(
                    f"📅 {position.symbol}: D+1 exit @ ${current_price:.2f}"
                )
                position.status = PositionStatus.EXITED
                position.exit_reason = "D+1_EXIT"
                exits_processed += 1
                continue
        
        if exits_processed > 0:
            self.logger.info(f"✅ Processed {exits_processed} exits")
    
    def get_portfolio_summary(self) -> dict:
        """Get current portfolio summary"""
        open_positions = [p for p in self.positions if p.status == PositionStatus.ENTERED]
        closed_positions = [p for p in self.positions if p.status == PositionStatus.EXITED]
        
        total_realized_pnl = sum(
            p.realized_pnl or 0 for p in closed_positions
        )
        
        total_unrealized_pnl = sum(
            p.unrealized_pnl or 0 for p in open_positions
        )
        
        return {
            "portfolio_value": self.config.portfolio_value,
            "open_positions": len(open_positions),
            "closed_positions": len(closed_positions),
            "total_positions": len(self.positions),
            "realized_pnl": total_realized_pnl,
            "unrealized_pnl": total_unrealized_pnl,
            "total_pnl": total_realized_pnl + total_unrealized_pnl,
            "trades_today": self.trades_today
        }

#!/usr/bin/env python3
"""
Short-Cycle Trader - AI-Powered 1-2 Day Trading System
======================================================

Weekly ROI optimization through high-frequency profit recycling with professional AI integration.
Based on the "Always Current Build" comprehensive implementation plan.

Target Performance:
- 1.5-2.5% weekly returns through 1-2 day cycles
- $1k portfolio with $330 daily pool (33% allocation)
- $6 max risk per trade (0.6% portfolio)
- Forced D+1 exits for capital recycling
- AI-powered signal generation and risk management

Author: LiteBotX Team
Version: 1.0 (Sprint 0 - Core Infrastructure)
"""

import os
import sys
import json
import logging
import datetime as dt
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum
import pandas as pd
import numpy as np
import json as _json
from pathlib import Path as _Path

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Import existing LiteBotX components
try:
    from config import Config
    from data_loader import DataLoader
    from execution_engine import ExecutionEngine
    from risk import RiskManager
    from logger import setup_logger
    from connect_real_trading import RealPaperTradingEngine
    from short_cycle_safety import SafetyMonitor, SafetyConfig
except ImportError as e:
    print(f"❌ Failed to import LiteBotX components: {e}")
    sys.exit(1)


class TradingDay(Enum):
    """Trading day types for short-cycle system"""
    MONDAY = "monday"
    TUESDAY = "tuesday" 
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"  # No new positions, exit only
    WEEKEND = "weekend"  # No trading


class PositionStatus(Enum):
    """Position lifecycle states"""
    PENDING = "pending"
    ENTERED = "entered"
    EXIT_SCHEDULED = "exit_scheduled"
    EXITED = "exited"
    STOPPED_OUT = "stopped_out"


@dataclass
class ShortCycleConfig:
    """Configuration for short-cycle trading system"""
    # Portfolio parameters (BALANCED AGGRESSIVE - 5% Weekly ROI Target)
    portfolio_value: float = 963000.0  # Use real portfolio value from Alpaca
    daily_pool_percent: float = 0.60  # 60% of portfolio per day for higher ROI
    max_risk_per_trade_dollars: float = 100.0  # Risk per trade for position sizing
    max_position_dollars: float = 6000.0  # Hard cap at $6K (sweet spot for 5% weekly ROI)
    max_loss_per_trade_dollars: float = 400.0  # Hard stop at $400 per trade (0.04% of portfolio)
    
    # Position parameters
    max_positions_per_day: int = 8  # Increased for more opportunities (was 6)
    min_position_size_dollars: float = 25.0  # Lowered minimum viable position (was 50.0)
    max_position_size_percent: float = 0.12  # 12% theoretical max (hard cap at $6K enforced)
    max_universe_size: int = 100  # Maximum number of symbols in trading universe
    
    # Diversification parameters
    max_positions_per_symbol_small: int = 2  # Max positions per symbol for portfolios < $100K
    max_positions_per_symbol_large: int = 3  # Max positions per symbol for portfolios > $100K
    max_concentration_percent_small: float = 0.35  # Max 35% of positions in one symbol (small portfolios)
    max_concentration_percent_large: float = 0.40  # Max 40% of positions in one symbol (large portfolios)
    portfolio_threshold_large: float = 100000.0  # Threshold for "large" portfolio diversification rules
    
    # Time parameters
    max_hold_days: int = 2  # D+1 forced exit (entry day + 1)
    trading_days: List[str] = None  # Mon-Thu only
    exit_time: str = "15:45"  # 15 minutes before close
    
    # Risk parameters (BALANCED AGGRESSIVE - Smart guardrails)
    max_daily_loss_percent: float = 0.002  # 0.2% daily loss limit ($1,926)
    max_weekly_loss_percent: float = 0.006   # 0.6% weekly loss limit ($5,778)
    confidence_threshold: float = 0.07  # 7% for quality trades (not 5.5%, not 8%)
    
    # Backtesting parameters
    enable_forced_d1_exit: bool = True  # Force D+1 exits
    model_transaction_costs: bool = True
    commission_per_trade: float = 0.0  # Assume commission-free
    spread_bp: float = 5.0  # 5 basis points spread cost
    
    def __post_init__(self):
        if self.trading_days is None:
            self.trading_days = ["monday", "tuesday", "wednesday", "thursday"]
        
        # Calculate derived values
        self.daily_pool_dollars = self.portfolio_value * self.daily_pool_percent
        self.max_daily_loss_dollars = self.portfolio_value * self.max_daily_loss_percent
        self.max_weekly_loss_dollars = self.portfolio_value * self.max_weekly_loss_percent


@dataclass
class AISignal:
    """AI-generated trading signal with confidence and parameters"""
    symbol: str
    action: str  # "BUY" or "SELL" or "HOLD"
    confidence: float  # 0.0 to 1.0
    time_horizon_days: float  # Expected hold time
    target_price: Optional[float] = None
    stop_price: Optional[float] = None
    entry_price: Optional[float] = None
    position_size_dollars: Optional[float] = None
    signal_timestamp: dt.datetime = None
    features_used: Dict[str, float] = None  # For explainability
    risk_score: float = 0.5  # Portfolio risk assessment
    
    def __post_init__(self):
        if self.signal_timestamp is None:
            self.signal_timestamp = dt.datetime.now()
        if self.features_used is None:
            self.features_used = {}


@dataclass
class ShortCyclePosition:
    """Position tracking for short-cycle system"""
    symbol: str
    entry_date: dt.date
    exit_date: dt.date  # Scheduled exit date (D+1)
    entry_price: float
    position_size_shares: int
    position_size_dollars: float
    stop_price: float
    target_price: Optional[float]
    status: PositionStatus
    ai_signal: AISignal
    
    # Exit tracking
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None
    exit_timestamp: Optional[dt.datetime] = None  # When position was actually exited
    realized_pnl: Optional[float] = None
    hold_days: Optional[int] = None
    
    # Risk tracking
    max_risk_dollars: float = 0.0
    current_price: Optional[float] = None
    unrealized_pnl: Optional[float] = None
    
    def update_current_price(self, price: float):
        """Update current price and unrealized P&L"""
        self.current_price = price
        if self.status == PositionStatus.ENTERED:
            self.unrealized_pnl = (price - self.entry_price) * self.position_size_shares
    
    def should_force_exit(self, current_date: dt.date) -> bool:
        """Check if position should be force-exited due to D+1 rule"""
        return current_date >= self.exit_date
    
    def should_smart_exit(self, current_date: dt.date, current_price: float, current_time: dt.datetime = None) -> tuple[bool, str]:
        """
        Smart D+1 exit logic for short swing trades
        Looks for optimal exit timing within the day rather than forced exits at bad times
        
        Returns: (should_exit, reason)
        """
        if current_date < self.exit_date:
            return False, "Not exit date yet"
        
        if current_date > self.exit_date:
            return True, "FORCED_D+1_LATE"  # Must exit if past date
        
        # Validate current_price
        if current_price is None or self.entry_price is None:
            return False, "INVALID_PRICE_DATA"
        
        # On exit date - use smart timing
        if current_time is None:
            current_time = dt.datetime.now()
        
        # Calculate profit/loss percentage
        pnl_pct = (current_price - self.entry_price) / self.entry_price
        
        # Market hours for intelligent exit timing
        market_hour = current_time.hour
        market_minute = current_time.minute
        time_fraction = market_hour + market_minute / 60.0
        
        # Smart exit logic for short swing trades:
        
        # 1. Early exit if significant profit (>2%)
        if pnl_pct > 0.02:
            return True, "SMART_PROFIT_TAKE"
        
        # 2. Early morning (9:30-10:30): Exit if profitable
        if 9.5 <= time_fraction <= 10.5 and pnl_pct > 0.005:  # >0.5% profit
            return True, "SMART_MORNING_PROFIT"
        
        # 3. Mid-day (11:00-14:00): Exit if breaking even or small profit
        if 11.0 <= time_fraction <= 14.0 and pnl_pct >= 0:
            return True, "SMART_MIDDAY_BREAKEVEN"
        
        # 4. Late afternoon (14:00-15:30): Exit if not deeply negative
        if 14.0 <= time_fraction <= 15.5 and pnl_pct > -0.015:  # Not down more than 1.5%
            return True, "SMART_AFTERNOON_EXIT"
        
        # 5. Final hour (15:30-16:00): Force exit regardless
        if time_fraction >= 15.5:
            return True, "SMART_FINAL_HOUR"
        
        # 6. Stop loss override: TIGHTER STOP to prevent large losses (was -3%)
        if pnl_pct < -0.02:  # Down more than 2% (REDUCED from -3% to cut losses faster)
            return True, "SMART_STOP_LOSS"
        
        return False, "WAITING_FOR_BETTER_TIMING"
    
    def is_stopped_out(self, current_price: float) -> bool:
        """Check if position should be stopped out"""
        if self.status != PositionStatus.ENTERED:
            return False
        # Handle None stop_price or current_price gracefully
        if self.stop_price is None or current_price is None:
            return False
        return current_price <= self.stop_price
    
    def calculate_realized_pnl(self, exit_price: float) -> float:
        """Calculate realized P&L on exit"""
        return (exit_price - self.entry_price) * self.position_size_shares


class AISignalGenerator:
    """AI-powered signal generation with multi-source inputs and confidence scoring"""
    
    def __init__(self, config: ShortCycleConfig):
        self.config = config
        self.logger = logging.getLogger(__name__ + ".AISignalGenerator")
        
        # Model placeholders (Sprint 1 implementation)
        self.model = None
        self.feature_pipeline = None
        
        # Temporary rule-based system for Sprint 0
        self.momentum_lookback = 4
        self.volume_threshold = 1.0
        
    def generate_signals(self, universe: List[str], market_data: Dict[str, pd.DataFrame]) -> List[AISignal]:
        """Generate AI signals for given universe"""
        signals = []
        
        for symbol in universe:
            try:
                signal = self._analyze_symbol(symbol, market_data.get(symbol))
                if signal and signal.confidence >= self.config.confidence_threshold:
                    signals.append(signal)
            except Exception as e:
                self.logger.error(f"Error analyzing {symbol}: {e}")
        
        # Sort by confidence and limit to max positions
        signals.sort(key=lambda x: x.confidence, reverse=True)
        return signals[:self.config.max_positions_per_day]
    
    def _analyze_symbol(self, symbol: str, data: Optional[pd.DataFrame]) -> Optional[AISignal]:
        """Analyze individual symbol (Sprint 0: Simple momentum rules)"""
        if data is None or len(data) < self.momentum_lookback + 1:
            return None

        try:
            # Simple momentum calculation for Sprint 0
            recent_returns = data['close'].pct_change().tail(self.momentum_lookback)
            volume_surge = data['volume'].iloc[-1] / data['volume'].tail(20).mean()

            momentum_score = recent_returns.mean()
            volume_ratio = volume_surge / max(self.volume_threshold, 1e-6)
            volume_ratio_capped = min(volume_ratio, 2.5)

            # Combine scores into confidence with higher weight on actionable setups
            confidence_raw = momentum_score * 120 * volume_ratio_capped
            confidence = min(max(confidence_raw, 0.0), 1.0)

            # Temporary diagnostics
            self.logger.info(
                f"🔎 {symbol}: momentum={momentum_score:.5f}, vol_surge={volume_surge:.2f}, "
                f"volume_ratio={volume_ratio:.2f}, confidence={confidence:.2f}"
            )

            if momentum_score > 0.0005 and volume_ratio >= 0.7:
                return AISignal(
                    symbol=symbol,
                    action="BUY",
                    confidence=confidence,
                    time_horizon_days=1.5,
                    entry_price=data['close'].iloc[-1],
                    features_used={
                        "momentum_score": momentum_score,
                        "volume_surge": volume_surge,
                        "volume_ratio": volume_ratio,
                        "confidence_components": [momentum_score, volume_ratio_capped]
                    }
                )
        except Exception as e:
            self.logger.error(f"Error in symbol analysis for {symbol}: {e}")

        return None


class AIStopLossManager:
    """AI-powered dynamic stop loss and fast-exit management"""
    
    def __init__(self, config: ShortCycleConfig):
        self.config = config
        self.logger = logging.getLogger(__name__ + ".AIStopLossManager")
        
        # Conservative parameters for short cycle (adjusted for ROI)
        self.max_stop_percent = 0.025  # 2.5% max stop for higher ROI potential
        self.fast_exit_threshold = 0.008  # 0.8% fast exit threshold
        self.atr_multiplier = 1.2  # More aggressive ATR-based stops
    
    def calculate_optimal_stop(self, signal: AISignal, market_data: pd.DataFrame) -> Tuple[float, float]:
        """Calculate optimal stop price and stop percentage"""
        try:
            entry_price = signal.entry_price
            if entry_price is None or market_data.empty:
                # Fallback to simple percentage stop
                stop_pct = self.max_stop_percent
                stop_price = entry_price * (1 - stop_pct)
                return stop_price, stop_pct
            
            # Calculate ATR-based stop
            high_low = market_data['high'] - market_data['low']
            high_close = abs(market_data['high'] - market_data['close'].shift(1))
            low_close = abs(market_data['low'] - market_data['close'].shift(1))
            true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            atr = true_range.tail(14).mean()
            
            # ATR-based stop
            atr_stop_distance = atr * self.atr_multiplier
            atr_stop_pct = atr_stop_distance / entry_price
            
            # Use minimum of percentage and ATR stop
            stop_pct = min(atr_stop_pct, self.max_stop_percent)
            stop_price = entry_price * (1 - stop_pct)
            
            self.logger.info(f"{signal.symbol}: ATR stop {atr_stop_pct:.1%}, final stop {stop_pct:.1%}")
            return stop_price, stop_pct
            
        except Exception as e:
            self.logger.error(f"Error calculating stop for {signal.symbol}: {e}")
            # Fallback to simple percentage
            stop_pct = self.max_stop_percent  
            stop_price = signal.entry_price * (1 - stop_pct)
            return stop_price, stop_pct
    
    def should_fast_exit(self, position: ShortCyclePosition, current_price: float) -> bool:
        """Check if position should fast-exit for capital recycling"""
        if position.status != PositionStatus.ENTERED:
            return False
        
        # Handle None values gracefully
        if current_price is None or position.entry_price is None:
            return False
        
        unrealized_pnl_pct = (current_price - position.entry_price) / position.entry_price
        unrealized_pnl_dollars = (current_price - position.entry_price) * position.position_size_shares
        
        # CRITICAL: Check max loss limit first (prevents $739 losses)
        if abs(unrealized_pnl_dollars) >= self.config.max_loss_per_trade_dollars:
            self.logger.warning(f"MAX LOSS LIMIT HIT: ${abs(unrealized_pnl_dollars):.2f} >= ${self.config.max_loss_per_trade_dollars}")
            return True
        
        return unrealized_pnl_pct <= -self.fast_exit_threshold


class AIConfidencePositionSizer:
    """AI-powered position sizing based on confidence and risk constraints"""
    
    def __init__(self, config: ShortCycleConfig):
        self.config = config
        self.logger = logging.getLogger(__name__ + ".AIConfidencePositionSizer")
    
    def calculate_position_size(self, signal: AISignal, stop_price: float, 
                              current_portfolio_value: float) -> Tuple[int, float]:
        """Calculate optimal position size based on confidence and risk"""
        try:
            entry_price = signal.entry_price
            if entry_price is None or stop_price >= entry_price:
                return 0, 0.0
            
            # Risk amount based on confidence (higher confidence = more risk)
            base_risk = self.config.max_risk_per_trade_dollars
            confidence_multiplier = min(signal.confidence * 2.0, 1.5)  # Max 50% increase for high ROI
            risk_amount = base_risk * confidence_multiplier
            
            # Position size based on stop distance
            stop_distance = entry_price - stop_price
            shares = int(risk_amount / stop_distance)
            position_value = shares * entry_price
            
            # Apply position size constraints
            max_position_value = current_portfolio_value * self.config.max_position_size_percent
            min_position_value = self.config.min_position_size_dollars
            
            # CRITICAL: Hard cap on position size (prevent $739 losses)
            if hasattr(self.config, 'max_position_dollars'):
                max_position_value = min(max_position_value, self.config.max_position_dollars)
            
            if position_value > max_position_value:
                shares = int(max_position_value / entry_price)
                position_value = shares * entry_price
            
            if position_value < min_position_value:
                return 0, 0.0  # Position too small
            
            # Validate against daily pool
            if position_value > self.config.daily_pool_dollars:
                shares = int(self.config.daily_pool_dollars / entry_price)
                position_value = shares * entry_price
            
            self.logger.info(f"{signal.symbol}: Risk ${risk_amount:.0f}, Size {shares} shares (${position_value:.0f})")
            return shares, position_value
            
        except Exception as e:
            self.logger.error(f"Error calculating position size for {signal.symbol}: {e}")
            return 0, 0.0


class AIPredictiveRiskManager:
    """AI-powered portfolio-level risk management with veto capability"""
    
    def __init__(self, config: ShortCycleConfig):
        self.config = config
        self.logger = logging.getLogger(__name__ + ".AIPredictiveRiskManager")
        
        # Risk thresholds
        self.max_correlation = 0.7  # Maximum position correlation
        self.volatility_spike_threshold = 1.5  # VIX spike detection
        
    def assess_portfolio_risk(self, proposed_signals: List[AISignal], 
                            current_positions: List[ShortCyclePosition],
                            market_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Assess portfolio-level risk and approve/veto trades"""
        try:
            risk_assessment = {
                "approved": True,
                "risk_score": 0.0,
                "warnings": [],
                "vetoed_signals": []
            }
            
            # Check correlation risk
            all_symbols = [s.symbol for s in proposed_signals] + [p.symbol for p in current_positions]
            if len(set(all_symbols)) != len(all_symbols):
                risk_assessment["warnings"].append("Duplicate symbols detected")
            
            # Simple sector diversification check
            sectors = self._get_symbol_sectors(all_symbols)
            sector_concentration = max(list(sectors.values())) / len(all_symbols) if all_symbols else 0
            
            if sector_concentration > 0.5:
                risk_assessment["warnings"].append(f"High sector concentration: {sector_concentration:.1%}")
                risk_assessment["risk_score"] += 0.3
            
            # Check daily loss limits
            current_daily_loss = self._calculate_current_daily_loss(current_positions)
            if current_daily_loss > self.config.max_daily_loss_dollars:
                risk_assessment["approved"] = False
                risk_assessment["warnings"].append(f"Daily loss limit exceeded: ${current_daily_loss:.0f}")
            
            # Veto low-confidence signals if risk is high
            if risk_assessment["risk_score"] > 0.5:
                for signal in proposed_signals:
                    if signal.confidence < 0.8:
                        risk_assessment["vetoed_signals"].append(signal.symbol)
            
            return risk_assessment
            
        except Exception as e:
            self.logger.error(f"Error in portfolio risk assessment: {e}")
            return {"approved": False, "risk_score": 1.0, "warnings": ["Risk assessment failed"]}
    
    def _get_symbol_sectors(self, symbols: List[str]) -> Dict[str, int]:
        """Simple sector mapping (to be enhanced with real sector data)"""
        # Placeholder sector mapping for Sprint 0
        tech_symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META"]
        sectors = {"TECH": 0, "OTHER": 0}
        
        for symbol in symbols:
            if symbol in tech_symbols:
                sectors["TECH"] += 1
            else:
                sectors["OTHER"] += 1
        
        return sectors
    
    def _calculate_current_daily_loss(self, positions: List[ShortCyclePosition]) -> float:
        """Calculate current unrealized daily loss"""
        daily_loss = 0.0
        today = dt.date.today()
        
        for pos in positions:
            if pos.entry_date == today and pos.unrealized_pnl and pos.unrealized_pnl < 0:
                daily_loss += abs(pos.unrealized_pnl)
        
        return daily_loss


class AIMarketRegimeDetector:
    """AI-powered market regime detection for strategy adaptation"""
    
    def __init__(self, config: ShortCycleConfig):
        self.config = config
        self.logger = logging.getLogger(__name__ + ".AIMarketRegimeDetector")
        
        # Import existing regime detector
        try:
            from regime_detector import RegimeDetector
            self.regime_detector = RegimeDetector()
        except ImportError:
            self.regime_detector = None
            self.logger.warning("RegimeDetector not available, using simple regime detection")
    
    def get_current_regime(self, market_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Get current market regime and suggested adjustments"""
        try:
            if self.regime_detector:
                # Use existing regime detector
                spy_data = market_data.get("SPY")
                if spy_data is not None:
                    regime = self.regime_detector.detect_regime(spy_data)
                else:
                    regime = "NEUTRAL"
            else:
                # Simple regime detection for Sprint 0
                regime = self._simple_regime_detection(market_data)
            
            # Map regime to short-cycle adjustments
            regime_adjustments = self._get_regime_adjustments(regime)
            
            return {
                "regime": regime,
                "adjustments": regime_adjustments,
                "confidence_adjustment": regime_adjustments.get("confidence_threshold", 0.0),
                "position_adjustment": regime_adjustments.get("max_positions_multiplier", 1.0)
            }
            
        except Exception as e:
            self.logger.error(f"Error in regime detection: {e}")
            return {
                "regime": "NEUTRAL",
                "adjustments": {},
                "confidence_adjustment": 0.0,
                "position_adjustment": 1.0
            }
    
    def _simple_regime_detection(self, market_data: Dict[str, pd.DataFrame]) -> str:
        """Simple regime detection based on SPY momentum"""
        spy_data = market_data.get("SPY")
        if spy_data is None or len(spy_data) < 20:
            return "NEUTRAL"
        
        # Simple momentum-based regime
        returns_5d = spy_data['close'].pct_change(5).iloc[-1]
        returns_20d = spy_data['close'].pct_change(20).iloc[-1]
        
        if returns_5d > 0.02 and returns_20d > 0.05:
            return "BULL"
        elif returns_5d < -0.02 and returns_20d < -0.05:
            return "BEAR"
        else:
            return "NEUTRAL"
    
    def _get_regime_adjustments(self, regime: str) -> Dict[str, Any]:
        """Get position and risk adjustments for regime"""
        adjustments = {
            "BULL": {
                "max_positions_multiplier": 1.2,
                "confidence_threshold": -0.05,  # Lower threshold
                "risk_multiplier": 1.1
            },
            "BEAR": {
                "max_positions_multiplier": 0.5,
                "confidence_threshold": 0.1,  # Higher threshold
                "risk_multiplier": 0.8
            },
            "NEUTRAL": {
                "max_positions_multiplier": 1.0,
                "confidence_threshold": 0.0,
                "risk_multiplier": 1.0
            }
        }
        
        return adjustments.get(regime, adjustments["NEUTRAL"])


class ShortCycleTrader:
    def _generate_portfolio_summary(self):
        """Generate portfolio summary for 09:00 ET premarket analysis"""
        try:
            portfolio_value = self._get_portfolio_value()
            open_positions = len([p for p in self.positions if p.status == PositionStatus.ENTERED])
            daily_pnl = sum(p.realized_pnl or 0 for p in self.positions if p.exit_reason and 
                          hasattr(p, 'exit_timestamp') and p.exit_timestamp and p.exit_timestamp.date() == dt.date.today())
            
            self.logger.info(f"📊 09:00 ET Portfolio Summary:")
            self.logger.info(f"   💰 Portfolio Value: ${portfolio_value:,.2f}")
            self.logger.info(f"   📈 Open Positions: {open_positions}")
            self.logger.info(f"   📊 Today's Realized P&L: ${daily_pnl:,.2f}")
            
            # Check D+1 exits due today
            today = dt.date.today()
            d1_exits = [p for p in self.positions if p.status == PositionStatus.ENTERED and p.exit_date <= today]
            if d1_exits:
                self.logger.info(f"   ⏰ D+1 Exits Due Today: {len(d1_exits)} positions")
                for pos in d1_exits:
                    self.logger.info(f"      • {pos.symbol}: Entry ${pos.entry_price:.2f} on {pos.entry_date}")
        except Exception as e:
            self.logger.error(f"Portfolio summary error: {e}")

    def _validate_watchlist_candidates(self):
        """Validate watchlist candidates for market open - NO ORDERS PLACED"""
        try:
            universe = self._get_trading_universe()
            self.logger.info(f"🔍 Validating {len(universe)} watchlist candidates:")
            
            # Quick validation of data availability
            market_data = self._get_market_data()
            valid_symbols = []
            for symbol in universe:
                if symbol in market_data and not market_data[symbol].empty:
                    valid_symbols.append(symbol)
            
            self.logger.info(f"   ✅ {len(valid_symbols)} symbols have valid data")
            self.logger.info(f"   📋 Valid candidates: {valid_symbols[:10]}{'...' if len(valid_symbols) > 10 else ''}")
            
            # Check for any data issues without placing orders
            if len(valid_symbols) < 5:
                self.logger.warning("⚠️ Limited valid candidates - may need to expand universe")
                
        except Exception as e:
            self.logger.error(f"Watchlist validation error: {e}")
    
    def run_continuous_cycle(self):
        """Continuous market-hours loop: post-market selection, premarket validation, open entries, D+1 exits, Friday freeze."""
        import time
        from datetime import datetime, timedelta
        from utils import market_hours
        # Fixed timezone handling - avoid pytz US/Eastern which causes file errors
        try:
            import pytz
            UTC = pytz.utc
            # Use America/New_York instead of US/Eastern for better compatibility
            ET = pytz.timezone("America/New_York")
        except Exception as e:
            # Fallback to standard library timezone without pytz
            from datetime import timezone
            UTC = timezone.utc
            # Use -4 for EDT (summer time) since it's September
            ET = timezone(timedelta(hours=-4))  # EDT approximation
            self.logger.warning(f"⚠️ Using EDT fallback timezone due to pytz error: {e}")
        
        logger = self.logger

        logger.info("🚦 Starting continuous market-hours loop (Sprint 2)")
        while True:
            try:
                now = datetime.utcnow().replace(tzinfo=UTC)
                weekday = now.astimezone(ET).weekday()  # 0=Mon, 4=Fri
                is_open = market_hours.is_regular_session_now(now)
                sess = market_hours.rth_session_for_date(now)
                next_open = sess.open_utc
                next_close = sess.close_utc

                # --- Post-market selection (immediately after close) ---
                if now > next_close and (now - next_close).total_seconds() < 3600:  # Within 1 hour of close
                    logger.info("🌙 Post-market: running watchlist refresh ONLY (NO TRADES)")
                    # Only refresh watchlist and prepare for next day - NO TRADING
                    self._refresh_watchlist_only()
                    # Sleep until premarket window
                    pre_start, _ = market_hours.premarket_window(market_hours.rth_session_for_date(now + timedelta(days=1)).open_utc)
                    sleep_sec = max(60, (pre_start - datetime.utcnow().replace(tzinfo=UTC)).total_seconds())
                    logger.info(f"🛌 Sleeping until premarket window ({sleep_sec/60:.1f} min)")
                    time.sleep(sleep_sec)
                    continue

                # --- Premarket validation window (09:00-09:30 ET) - Portfolio Summary & Watchlist Validation ---
                pre_start, pre_end = market_hours.premarket_window(next_open)
                # Check for 09:00 ET validation window (30 min before open)
                validation_start = next_open - timedelta(minutes=30)
                if validation_start <= now < next_open:
                    logger.info("📊 09:00 ET Premarket: Portfolio summary & watchlist validation (NO ORDERS)")
                    # Run analysis without placing orders - portfolio summary and watchlist prep
                    try:
                        self._generate_portfolio_summary()
                        self._validate_watchlist_candidates()
                        logger.info("✅ Premarket validation complete - ready for market open")
                    except Exception as e:
                        logger.warning(f"⚠️ Premarket validation error: {e}")
                    # Sleep until market open
                    sleep_sec = max(30, (next_open - now).total_seconds())
                    logger.info(f"🕒 Sleeping until market open ({sleep_sec/60:.1f} min)")
                    time.sleep(sleep_sec)
                    continue
                elif pre_start <= now < validation_start:
                    # Earlier premarket - sleep until validation window
                    sleep_sec = max(60, (validation_start - now).total_seconds())
                    logger.info(f"🌅 Early premarket: sleeping until validation window ({sleep_sec/60:.1f} min)")
                    time.sleep(sleep_sec)
                    continue

                # --- Opening 15 min: allow new entries (except Friday) - 15 min after market opens ---
                if is_open:
                    open_et = next_open.astimezone(ET)
                    now_et = now.astimezone(ET)
                    minutes_since_open = (now_et - open_et).total_seconds() / 60
                    # Wait 15 minutes after market open before placing orders
                    if 15 <= minutes_since_open < 30:
                        if weekday == 4:
                            logger.info("🛑 Friday: entry freeze (exits only)")
                        else:
                            logger.info("🚀 Market stabilized: running entry logic (15-30 min after open)...")
                            self.run_daily_cycle()
                        # Sleep until after entry window
                        sleep_sec = max(60, 30*60 - (now - next_open).total_seconds())
                        logger.info(f"⏳ Sleeping until end of entry window ({sleep_sec/60:.1f} min)")
                        time.sleep(sleep_sec)
                        continue
                    elif 0 <= minutes_since_open < 15:
                        # Market just opened - wait for stabilization
                        sleep_sec = max(60, 15*60 - (now - next_open).total_seconds())
                        logger.info(f"⏳ Market stabilizing period: sleeping {sleep_sec/60:.1f} min until entry window")
                        time.sleep(sleep_sec)
                        continue

                    # --- Intraday: monitor for D+1 exits, risk, etc. ---
                    logger.info("🔄 Intraday: monitoring positions for exits and risk...")
                    self._process_existing_positions()
                    # Sleep until close or next check
                    sleep_sec = min(300, market_hours.seconds_until_close(now))
                    logger.info(f"⏳ Sleeping until next intraday check ({sleep_sec/60:.1f} min)")
                    time.sleep(max(60, sleep_sec))
                    continue

                # --- Market closed, not yet post-market: sleep until next open or post-market ---
                if now < next_open:
                    sleep_sec = max(60, (next_open - now).total_seconds())
                    logger.info(f"🛌 Market closed: sleeping until next open ({sleep_sec/60:.1f} min)")
                    time.sleep(sleep_sec)
                    continue

                # --- Fallback: short sleep ---
                logger.info("💤 Idle: short sleep (60s)")
                time.sleep(60)
                
            except Exception as e:
                logger.error(f"❌ Continuous cycle error: {e}")
                # Sleep and continue instead of crashing
                time.sleep(60)
                continue
    
    def __init__(self, config: ShortCycleConfig = None, launch_gui: bool = False):
        self.config = config or ShortCycleConfig()
        self.logger = self._setup_logging()
        self.launch_gui = launch_gui
        
        # Initialize AI components
        self.signal_generator = AISignalGenerator(self.config)
        self.stop_manager = AIStopLossManager(self.config)
        self.position_sizer = AIConfidencePositionSizer(self.config)
        self.risk_manager = AIPredictiveRiskManager(self.config)
        self.regime_detector = AIMarketRegimeDetector(self.config)
        
        # Trading state
        self.positions: List[ShortCyclePosition] = []
        self.daily_pnl = 0.0
        self.daily_realized_pnl = 0.0  # Realized P&L from exits today
        self.daily_unrealized_pnl = 0.0  # Unrealized P&L from open positions
        self.weekly_pnl = 0.0
        self.trades_today = 0
        self.recent_trades: List[Any] = []  # simple buffer of recent trade outcomes for safety
        self.last_pnl_reset_date: Optional[dt.date] = None  # Track when we last reset daily counters
        
        # Integration with existing LiteBotX components
        try:
            self.data_loader = DataLoader()
            self.execution_engine = RealPaperTradingEngine()
            self.logger.info("✅ LiteBotX components initialized")
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize LiteBotX components: {e}")
            raise

        # Lazy-initialized PreFilter instance (provides data caching across cycles)
        self._prefilter: Optional['PreFilter'] = None
        
        # Kill switches
        self.kill_switches = {
            "daily_loss_exceeded": False,
            "weekly_loss_exceeded": False,
            "system_error": False
        }

        # Safety monitor (reinstated)
        try:
            self.safety_monitor = SafetyMonitor(SafetyConfig(), self.config.portfolio_value)
            self.logger.info("🛡️ Safety monitor active")
        except Exception as e:
            self.logger.warning(f"Safety monitor unavailable: {e}")
            self.safety_monitor = None

        # Performance controller (Sprint 2 metrics)
        try:
            from controllers.performance_controller import PerformanceController
            self.performance_controller = PerformanceController(self.logger)
            self.logger.info("🎯 PerformanceController ready")
        except Exception as e:
            self.logger.warning(f"PerformanceController unavailable: {e}")
            self.performance_controller = None
            
        # Dashboard integration
        self.dashboard = None
        self.signal_callbacks = []
        self.trade_callbacks = []
        if launch_gui:
            self._initialize_dashboard()
        
        # Load existing positions from previous session
        self._load_positions()
    
    def _setup_logging(self) -> logging.Logger:
        """Setup comprehensive logging with explainability"""
        import os
        logger = logging.getLogger("ShortCycleTrader")
        
        # Prevent duplicate handlers
        if logger.handlers:
            logger.handlers.clear()
        
        # Don't propagate to avoid duplicate messages from root logger
        logger.propagate = False
        
        if not logger.handlers:
            # Ensure logs directory exists
            os.makedirs('logs', exist_ok=True)
            
            # File handler
            file_handler = logging.FileHandler('logs/short_cycle_trader.log')
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
            
            # Console handler
            console_handler = logging.StreamHandler()
            console_formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s'  # Simplified for console
            )
            console_handler.setFormatter(console_formatter)
            logger.addHandler(console_handler)
            
            logger.setLevel(logging.INFO)
        
        return logger
    
    def _initialize_dashboard(self):
        """Initialize the GUI dashboard"""
        try:
            from gui.short_cycle_dashboard import create_short_cycle_dashboard
            self.dashboard = create_short_cycle_dashboard(self)
            self.logger.info("✅ Dashboard initialized successfully")
        except ImportError as e:
            self.logger.warning(f"⚠️ Dashboard not available: {e}")
            self.launch_gui = False
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize dashboard: {e}")
            self.launch_gui = False
    
    def add_signal_callback(self, callback):
        """Add callback for signal generation events"""
        self.signal_callbacks.append(callback)
    
    def add_trade_callback(self, callback):
        """Add callback for trade execution events"""
        self.trade_callbacks.append(callback)
    
    def _notify_signal_generated(self, symbol: str, signal_data: dict):
        """Notify all signal callbacks"""
        for callback in self.signal_callbacks:
            try:
                callback(symbol, signal_data)
            except Exception as e:
                self.logger.error(f"Signal callback error: {e}")
    
    def _notify_trade_executed(self, symbol: str, trade_data: dict):
        """Notify all trade callbacks"""
        for callback in self.trade_callbacks:
            try:
                callback(symbol, trade_data)
            except Exception as e:
                self.logger.error(f"Trade callback error: {e}")
    
    def start_with_dashboard(self):
        """Start trading with dashboard in separate threads"""
        import threading
        
        if not self.dashboard:
            self.logger.error("❌ No dashboard available")
            return
        
        # Start trading in background thread
        trading_thread = threading.Thread(target=self.run_continuous_cycle, daemon=True)
        trading_thread.start()
        
        # Run dashboard in main thread
        try:
            self.logger.info("🖥️ Starting dashboard...")
            self.dashboard.run()
        except KeyboardInterrupt:
            self.logger.info("🛑 Dashboard stopped by user")
        except Exception as e:
            self.logger.error(f"Dashboard error: {e}")
    
    def should_trade_today(self) -> bool:
        """Check if we should trade today based on day and kill switches"""
        today = dt.datetime.now().strftime("%A").lower()
        
        # Check kill switches
        for switch, activated in self.kill_switches.items():
            if activated:
                self.logger.warning(f"❌ Trading halted: {switch}")
                return False
        
        # Check trading day
        if today not in self.config.trading_days:
            self.logger.info(f"📅 No trading on {today}")
            return False
        
        return True
    
    def _refresh_watchlist_only(self):
        """Post-market watchlist refresh ONLY - no trading execution"""
        self.logger.info("📋 Post-market: Refreshing watchlist for next trading day (NO TRADES)")
        
        try:
            # Update risk limits based on current portfolio value  
            self._update_risk_limits()
            
            # Load positions to get current state
            self._load_positions()
            
            # Generate trading universe and signals for tomorrow (but don't execute)
            universe = self._get_trading_universe()
            self.logger.info(f"🧭 Prepared trading universe for tomorrow: {len(universe)} symbols")
            
            # Store the universe for premarket validation
            self.tomorrow_universe = universe[:self.config.max_universe_size]
            
            self.logger.info("✅ Watchlist refresh complete - ready for tomorrow's trading")
            
        except Exception as e:
            self.logger.error(f"❌ Error in watchlist refresh: {e}")
    
    def run_daily_cycle(self):
        """Execute daily short-cycle trading logic"""
        self.logger.info("🚀 Starting daily short-cycle trading cycle")
        
        try:
            # Reset daily counters if starting a new trading day
            self._maybe_reset_daily_counters()
            
            # Update risk limits based on current portfolio value
            self._update_risk_limits()
            
            # Load positions from file to ensure we have latest state
            self._load_positions()
            
            # Pre-trade safety check
            if self.safety_monitor:
                safety = self.safety_monitor.check_safety_conditions(
                    current_positions=self.positions,
                    daily_pnl=self.daily_pnl,
                    weekly_pnl=self.weekly_pnl,
                    recent_trades=self.recent_trades,
                )
                if not safety.get("safe_to_trade", True):
                    self.logger.warning("🛑 Safety monitor: trading paused due to active kill switch or alert")
                    return

            # Check if we should trade
            if not self.should_trade_today():
                return
            
            # Update positions and check for exits
            self._process_existing_positions()
            
            # Check kill switches after processing positions
            if any(self.kill_switches.values()):
                return
            
            # Performance controller may adjust today's knobs toward Sprint 2 metrics
            if self.performance_controller:
                runtime_state = {
                    "mode": "paper",  # enforce paper for Sprint 2
                    "weekly_return": self._estimate_weekly_return(),
                    "drawdown": self._estimate_drawdown(),
                    "win_rate": self._estimate_win_rate(),
                    "consecutive_losses": self._estimate_consecutive_losses(),
                    "symbols_covered": len(self._get_trading_universe()),
                    "signals_today": 0,  # set later after generation
                }
                adj = self.performance_controller.evaluate_and_adjust(self.config, runtime_state)
                self.logger.info(f"🎛️ Sprint 2 progress: {adj}")

            # Generate new signals if we have capacity
            if self.trades_today < self.config.max_positions_per_day:
                self._generate_and_execute_new_positions()
            
            # Daily reporting
            self._generate_daily_report()
            
        except Exception as e:
            self.logger.error(f"❌ Error in daily cycle: {e}")
            self.kill_switches["system_error"] = True
    
    def _process_existing_positions(self):
        """Process existing positions for exits and updates with strategic D+1 timing"""
        today = dt.date.today()
        current_time = dt.datetime.now()
        total_exits_processed = 0
        
        # PHASE 1: Strategic D+1 exits first (prevents dumping all at once)
        strategic_exits = self._process_existing_positions_with_strategic_exits()
        total_exits_processed += strategic_exits
        
        # PHASE 2: Handle other exit conditions (stop losses, fast exits, etc.)
        other_exits_processed = 0
        live_positions = self._get_live_portfolio_positions()
        if self._sync_positions_with_portfolio(live_positions):
            self._save_positions()
        
        for position in self.positions:
            if position.status != PositionStatus.ENTERED:
                continue
            
            # Skip positions that were already handled by strategic D+1 exit
            if today >= position.exit_date:
                continue  # These were processed in Phase 1
            
            # CRITICAL: STRICT D+1 ENFORCEMENT - No same-day exits allowed!
            if position.entry_date == today:
                self.logger.debug(f"⏳ {position.symbol}: No exit allowed until D+1 ({position.exit_date}) - PDT protection")
                continue
            
            try:
                live_data = live_positions.get(position.symbol.upper())
                if not live_data or abs(live_data.get("quantity", 0)) <= 1e-6:
                    self.logger.debug(
                        f"🔕 Skipping exit for {position.symbol}: no live holdings detected in portfolio"
                    )
                    continue
                current_price = None
                actual_qty = int(round(abs(live_data.get("quantity", 0))))
                if actual_qty > 0:
                    market_value = live_data.get("market_value")
                    if market_value:
                        try:
                            current_price = float(market_value) / actual_qty
                        except Exception:
                            current_price = None
                if not current_price:
                    # Fallback to market data loader
                    current_price = self._get_current_price(position.symbol)
                if not current_price:
                    self.logger.warning(
                        f"⚠️ Cannot get current price for {position.symbol}, skipping exit check"
                    )
                    continue
                    
                position.update_current_price(current_price)
                
                # Check for smart exit (but not D+1 as that's handled in Phase 1)
                should_exit, exit_reason = position.should_smart_exit(today, current_price, current_time)
                if should_exit and "D+1" not in exit_reason:  # Skip D+1 exits here
                    self._exit_position(position, current_price, exit_reason)
                    other_exits_processed += 1
                    continue
                
                # Check for stop loss
                if position.is_stopped_out(current_price):
                    self._exit_position(position, current_price, "STOP_LOSS")
                    other_exits_processed += 1
                    continue
                
                # Check for fast exit
                if self.stop_manager.should_fast_exit(position, current_price):
                    self._exit_position(position, current_price, "FAST_EXIT")
                    other_exits_processed += 1
                    continue
                
            except Exception as e:
                self.logger.error(f"Error processing position {position.symbol}: {e}")
        
        total_exits_processed += other_exits_processed
        self.logger.info(f"📊 Total exits processed: {total_exits_processed} (Strategic D+1: {strategic_exits}, Other: {other_exits_processed})")
        self._update_daily_pnl()
        self._check_loss_limits()
    
    def _process_existing_positions_with_strategic_exits(self):
        """Process existing positions with strategic D+1 exits - no dumping all at once"""
        import time
        
        positions_to_exit = []
        today = dt.date.today()
        current_time = dt.datetime.now()
        
        # First pass: identify positions that need D+1 exit
        for position in self.positions:
            if position.status != PositionStatus.ENTERED:
                continue
                
            # Parse entry date properly and calculate target exit date (D+1)
            target_exit_date = position.exit_date  # This should be entry_date + 1 day
            
            # Check if this position should exit today (D+1 rule)
            if today >= target_exit_date:
                days_held = (today - position.entry_date).days
                positions_to_exit.append({
                    'position': position,
                    'priority': 'D+1_MANDATORY',
                    'entry_date': position.entry_date,
                    'target_exit': target_exit_date,
                    'days_held': days_held
                })
                self.logger.info(f"🎯 {position.symbol}: D+1 exit required (held {days_held} days)")
        
        if not positions_to_exit:
            self.logger.info("✅ No D+1 exits required today")
            return 0
        
        # Strategic exit execution with timing
        self.logger.info(f"🚀 Strategic D+1 exit sequence: {len(positions_to_exit)} positions")
        
        # Sort by priority and market conditions
        positions_to_exit.sort(key=lambda x: (
            -x['days_held'],  # Exit oldest first (negative for descending order)
            x['position'].symbol  # Alphabetical for consistency
        ))
        
        exit_count = 0
        for i, exit_info in enumerate(positions_to_exit):
            position = exit_info['position']
            
            try:
                # Strategic timing: Space exits 30-60 seconds apart
                if i > 0:  # Don't delay the first exit
                    delay = min(60, 30 + (i * 10))  # 30, 40, 50, 60 seconds max
                    self.logger.info(f"⏳ Strategic exit delay: {delay}s before {position.symbol}")
                    time.sleep(delay)
                
                # Execute the exit using existing logic
                self.logger.info(f"🎯 Executing D+1 exit {i+1}/{len(positions_to_exit)}: {position.symbol}")
                success = self._execute_strategic_position_exit(position, f"D+1_STRATEGIC_{i+1}")
                
                if success:
                    exit_count += 1
                    self.logger.info(f"✅ {position.symbol}: D+1 exit completed ({exit_count}/{len(positions_to_exit)})")
                else:
                    self.logger.warning(f"⚠️ {position.symbol}: D+1 exit failed, will retry")
                    
            except Exception as e:
                self.logger.error(f"❌ {position.symbol}: D+1 exit error: {e}")
        
        self.logger.info(f"🎉 Strategic D+1 exit sequence complete: {exit_count}/{len(positions_to_exit)} successful")
        return exit_count
    
    def _execute_strategic_position_exit(self, position: ShortCyclePosition, exit_reason: str):
        """Execute a single position exit with proper error handling and strategic timing"""
        try:
            today = dt.date.today()
            current_time = dt.datetime.now()
            
            # PDT protection: Don't exit same-day entries
            if position.entry_date == today:
                self.logger.warning(f"⏳ {position.symbol}: No exit allowed until D+1 ({position.exit_date}) - PDT protection")
                return False
            
            # Check for live position in portfolio
            live_positions = self._get_live_portfolio_positions()
            live_data = live_positions.get(position.symbol.upper())
            if not live_data or abs(live_data.get("quantity", 0)) <= 1e-6:
                self.logger.warning(f"🔕 {position.symbol}: No live holdings detected in portfolio")
                return False
            
            # Get current market price
            current_price = None
            actual_qty = int(round(abs(live_data.get("quantity", 0))))
            if actual_qty > 0:
                market_value = live_data.get("market_value")
                if market_value:
                    try:
                        current_price = float(market_value) / actual_qty
                    except Exception:
                        current_price = None
            
            if not current_price:
                # Fallback to market data loader
                current_price = self._get_current_price(position.symbol)
            
            if not current_price:
                self.logger.error(f"❌ {position.symbol}: Cannot get current price for exit")
                return False
            
            # Calculate P&L
            unrealized_pnl = (current_price - position.entry_price) * position.position_size_shares
            unrealized_pnl_pct = ((current_price - position.entry_price) / position.entry_price) * 100
            
            # Submit sell order
            self.logger.info(f"📤 {position.symbol}: Submitting sell order - {position.position_size_shares} shares @ ${current_price:.2f}")
            self.logger.info(f"💰 {position.symbol}: Unrealized P&L: ${unrealized_pnl:.2f} ({unrealized_pnl_pct:+.2f}%)")
            
            # Use existing _exit_position method for consistency
            self._exit_position(position, current_price, exit_reason)
            
            return True
                
        except Exception as e:
            self.logger.error(f"❌ {position.symbol}: Strategic exit execution error: {e}")
            return False
    
    def _generate_and_execute_new_positions(self):
        """Generate new signals and execute positions"""
        try:
            # CRITICAL: Validate market hours before any trade execution
            from utils import market_hours
            from datetime import datetime
            import pytz
            
            now = datetime.utcnow().replace(tzinfo=pytz.UTC)
            is_market_open = market_hours.is_regular_session_now(now)
            
            if not is_market_open:
                self.logger.warning("🚫 TRADE BLOCKED: Market is closed - no orders will be executed")
                return
            
            # Additional validation: Check if within trading window (15-30 min after open)
            sess = market_hours.rth_session_for_date(now)
            minutes_since_open = (now - sess.open_utc).total_seconds() / 60
            
            if minutes_since_open < 15:
                self.logger.warning("🚫 TRADE BLOCKED: Market still stabilizing (< 15 min after open)")
                return
            elif minutes_since_open > 30:
                self.logger.warning("🚫 TRADE BLOCKED: Outside entry window (> 30 min after open)")
                return
            
            self.logger.info(f"✅ Market hours validated: {minutes_since_open:.1f} min after open")
            
            # Get market regime
            market_data = self._get_market_data()
            regime_info = self.regime_detector.get_current_regime(market_data)
            self.logger.info(f"📈 Market regime: {regime_info['regime']}")
            
            # Generate signals
            universe = self._get_trading_universe()
            try:
                self.logger.info(f"🧭 Final trading universe ({len(universe)}): {universe}")
                # Diagnostics: log market_data keys and DataFrame shapes
                self.logger.info(f"🔬 market_data keys: {list(market_data.keys())}")
                for sym in universe:
                    df = market_data.get(sym)
                    if df is not None:
                        self.logger.info(f"🔬 {sym} market_data shape: {df.shape}")
                    else:
                        self.logger.warning(f"⚠️ No market_data for {sym}")
                self.logger.info(f"🔬 Current confidence_threshold: {self.config.confidence_threshold}")
            except Exception:
                pass
            signals = self.signal_generator.generate_signals(universe, market_data)
            
            # Notify dashboard about generated signals
            for signal in signals:
                self._notify_signal_generated(signal.symbol, {
                    'action': signal.action,
                    'confidence': signal.confidence,
                    'timestamp': dt.datetime.now()
                })

            # After signal generation, update performance controller with actual signal count for today
            if self.performance_controller:
                try:
                    runtime_state = {
                        "mode": "paper",
                        "weekly_return": self._estimate_weekly_return(),
                        "drawdown": self._estimate_drawdown(),
                        "win_rate": self._estimate_win_rate(),
                        "consecutive_losses": self._estimate_consecutive_losses(),
                        "symbols_covered": len(universe),
                        "signals_today": len(signals),
                        "trades_today": self.trades_today,  # Add trades counter for adaptive position sizing
                    }
                    adj2 = self.performance_controller.evaluate_and_adjust(self.config, runtime_state)
                    self.logger.info(
                        f"📈 Sprint2 snapshot | weekly_return={runtime_state['weekly_return']:.2%}, "
                        f"drawdown={runtime_state['drawdown']:.2%}, win_rate={runtime_state['win_rate']:.1%}, "
                        f"loss_streak={runtime_state['consecutive_losses']}, symbols={runtime_state['symbols_covered']}, "
                        f"signals_today={runtime_state['signals_today']} | adj={adj2}"
                    )
                except Exception as e:
                    self.logger.warning(f"PerformanceController post-signal update failed: {e}")
            
            if not signals:
                self.logger.info("📭 No signals generated")
                return
            
            # Risk assessment
            risk_assessment = self.risk_manager.assess_portfolio_risk(signals, self.positions, market_data)
            
            if not risk_assessment["approved"]:
                self.logger.warning(f"🛑 Risk manager vetoed all trades: {risk_assessment['warnings']}")
                return
            
            # Execute approved signals with diversification controls
            for signal in signals:
                if signal.symbol in risk_assessment.get("vetoed_signals", []):
                    self.logger.info(f"🛑 Signal {signal.symbol} vetoed by risk manager")
                    continue
                
                if self.trades_today >= self.config.max_positions_per_day:
                    break
                
                # Diversification check - prevent concentration risk
                if not self._check_diversification_limits(signal.symbol):
                    self.logger.info(f"🔄 Signal {signal.symbol} skipped for diversification (too many positions in this stock)")
                    continue
                
                # Same-day trading prevention - crucial for swing trading approach
                if self._has_same_day_activity(signal.symbol):
                    self.logger.info(f"🔄 Signal {signal.symbol} skipped - same-day buy/sell prevention (swing trading)")
                    continue
                
                self._execute_signal(signal, market_data.get(signal.symbol))
            
        except Exception as e:
            self.logger.error(f"Error generating new positions: {e}")
    
    def _execute_signal(self, signal: AISignal, symbol_data: pd.DataFrame):
        """Execute a trading signal"""
        try:
            # CRITICAL: PDT Protection - Block same-day activity FIRST
            if self._has_same_day_activity(signal.symbol):
                self.logger.warning(f"❌ {signal.symbol}: BLOCKED - Same-day activity detected (PDT protection)")
                return
            
            # Calculate stop price
            stop_price, stop_pct = self.stop_manager.calculate_optimal_stop(signal, symbol_data)
            
            # Calculate position size
            current_portfolio_value = self._get_portfolio_value()
            shares, position_value = self.position_sizer.calculate_position_size(
                signal, stop_price, current_portfolio_value
            )
            
            if shares == 0:
                self.logger.info(f"❌ {signal.symbol}: Position size too small, skipping")
                return
            
            # Create position
            today = dt.date.today()
            exit_date = self._get_next_trading_day(today)  # D+1 exit
            
            position = ShortCyclePosition(
                symbol=signal.symbol,
                entry_date=today,
                exit_date=exit_date,
                entry_price=signal.entry_price,
                position_size_shares=shares,
                position_size_dollars=position_value,
                stop_price=stop_price,
                target_price=signal.target_price,
                status=PositionStatus.PENDING,
                ai_signal=signal,
                max_risk_dollars=self.config.max_risk_per_trade_dollars
            )
            
            # Execute trade (paper trading for now)
            success = self._execute_trade(position)
            
            if success:
                position.status = PositionStatus.ENTERED
                self.positions.append(position)
                self.trades_today += 1
                
                # Save positions after new entry
                self._save_positions()
                
                self.logger.info(f"✅ {signal.symbol}: Entered {shares} shares @ ${signal.entry_price:.2f} "
                               f"(Stop: ${stop_price:.2f}, Confidence: {signal.confidence:.1%})")
            else:
                self.logger.error(f"❌ {signal.symbol}: Failed to execute trade")
                
        except Exception as e:
            self.logger.error(f"Error executing signal for {signal.symbol}: {e}")
    
    def _check_diversification_limits(self, symbol: str) -> bool:
        """
        Check if we can add another position in this symbol without exceeding diversification limits.
        
        Diversification Rules:
        1. Max positions per symbol based on portfolio size (configurable)
        2. Max concentration percentage in any single symbol (configurable)
        3. Prefer spreading across different sectors/stocks
        """
        try:
            # Count current positions in this symbol
            current_positions_in_symbol = sum(1 for pos in self.positions 
                                            if pos.symbol == symbol and pos.status == PositionStatus.ENTERED)
            
            # Get portfolio size to determine limits
            portfolio_value = self._get_portfolio_value()
            
            # Set position limits based on portfolio size and config
            if portfolio_value < self.config.portfolio_threshold_large:
                max_positions_per_symbol = self.config.max_positions_per_symbol_small
                max_concentration_pct = self.config.max_concentration_percent_small
                portfolio_type = "small"
            else:
                max_positions_per_symbol = self.config.max_positions_per_symbol_large
                max_concentration_pct = self.config.max_concentration_percent_large
                portfolio_type = "large"
            
            # Rule 1: Check max positions per symbol
            if current_positions_in_symbol >= max_positions_per_symbol:
                self.logger.info(f"🔄 {symbol}: Already have {current_positions_in_symbol} positions "
                               f"(limit: {max_positions_per_symbol} for {portfolio_type} portfolio)")
                return False
            
            # Rule 2: Check concentration percentage (only if we have enough positions for it to be meaningful)
            total_active_positions = sum(1 for pos in self.positions if pos.status == PositionStatus.ENTERED)
            
            # Only apply concentration limits if we have at least 3 positions 
            # (with 1-2 positions, diversification rules via max_positions_per_symbol are sufficient)
            if total_active_positions >= 3:
                # Calculate what concentration would be if we add this position
                symbol_positions_after_add = current_positions_in_symbol + 1
                total_positions_after_add = total_active_positions + 1
                symbol_concentration = symbol_positions_after_add / total_positions_after_add
                
                if symbol_concentration > max_concentration_pct:
                    self.logger.info(f"🔄 {symbol}: Would exceed {max_concentration_pct:.0%} concentration limit "
                                   f"({symbol_concentration:.1%} with this trade)")
                    return False
            
            # Rule 3: Log diversification info
            if current_positions_in_symbol == 0:
                self.logger.info(f"✅ {symbol}: New symbol - good for diversification")
            else:
                self.logger.info(f"✅ {symbol}: Adding position {current_positions_in_symbol + 1} "
                               f"(within {max_positions_per_symbol} limit)")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking diversification for {symbol}: {e}")
            # Err on the side of caution - allow the trade if check fails
            return True
    
    def _has_same_day_activity(self, symbol: str) -> bool:
        """
        STRICT D+1 ENFORCEMENT: Check if there's been any trading activity for this symbol today.
        Prevents PDT violations by blocking:
        1. Multiple entries same symbol same day (creates day trades)
        2. Same-day re-entry after exit (day trade)
        3. Recent entries within 12 hours (prevents after-hours gaps)
        
        Returns True if symbol should be BLOCKED from trading.
        """
        today = dt.date.today()
        now = dt.datetime.now()
        twelve_hours_ago = now - dt.timedelta(hours=12)
        
        # Count ALL same-day entries (including exited positions)
        same_day_entries = sum(1 for p in self.positions 
                              if p.symbol == symbol and p.entry_date == today)
        
        if same_day_entries > 0:
            self.logger.info(f"� PDT BLOCK: {symbol} already has {same_day_entries} position(s) entered today")
            return True
        
        # Check for same-day exits (prevents re-entry after exit = day trade)
        for position in self.positions:
            if (position.symbol == symbol and 
                hasattr(position, 'exit_timestamp') and position.exit_timestamp and 
                position.exit_timestamp.date() == today):
                self.logger.info(f"� PDT BLOCK: {symbol} was exited today (no same-day re-entry)")
                return True
        
        # Check for recent entries (within 12 hours) - prevents off-hours -> next day trades
        # NOTE: Using entry_date since entry_timestamp may not always be set
        for position in self.positions:
            if position.symbol == symbol:
                # If position has entry_date matching today, it's same-day
                if position.entry_date == today:
                    self.logger.info(f"🚫 PDT BLOCK: {symbol} entered today (same-day block)")
                    return True
                
                # If entry_timestamp exists and is recent, also block
                if (hasattr(position, 'entry_timestamp') and 
                    position.entry_timestamp and 
                    position.entry_timestamp >= twelve_hours_ago):
                    hours_ago = (now - position.entry_timestamp).total_seconds() / 3600
                    self.logger.info(f"🚫 PDT BLOCK: {symbol} entered {hours_ago:.1f}h ago (12h cooldown)")
                    return True
        
        return False

    
    def _execute_trade(self, position: ShortCyclePosition) -> bool:
        """Execute actual trade using RealPaperTradingEngine"""
        try:
            # Log the trade decision with explainability
            self._log_trade_explanation(position)
            
            # CRITICAL: Submit actual order to Alpaca via RealPaperTradingEngine
            if hasattr(self, 'execution_engine') and self.execution_engine:
                order_result = self.execution_engine.submit_order(
                    symbol=position.symbol,
                    quantity=position.position_size_shares,
                    side='buy'
                )
                
                if order_result:
                    self.logger.info(f"✅ REAL TRADE SUBMITTED: {position.symbol} {position.position_size_shares} shares")
                    self.logger.info(f"   Order ID: {order_result['order_id']}")
                    self.logger.info(f"   Status: {order_result['status']}")
                else:
                    self.logger.error(f"❌ FAILED to submit real trade for {position.symbol}")
                    return False
            else:
                # Fallback to paper trade logging only if no execution engine
                self.logger.info(f"📝 Paper trade: {position.symbol} {position.position_size_shares} shares")
            
            # Notify dashboard about executed trade
            self._notify_trade_executed(position.symbol, {
                'action': 'BUY',  # Since we're entering a position
                'quantity': position.position_size_shares,
                'price': position.entry_price,
                'pnl': 0,  # Initial PnL is 0 at entry
                'timestamp': dt.datetime.now()
            })
            
            return True
            
        except Exception as e:
            self.logger.error(f"Trade execution failed: {e}")
            return False
    
    def _log_trade_explanation(self, position: ShortCyclePosition):
        """Log detailed explanation of trade decision for regulatory/debugging"""
        explanation = {
            "timestamp": dt.datetime.now().isoformat(),
            "symbol": position.symbol,
            "action": "ENTRY",
            "ai_decision": {
                "confidence": position.ai_signal.confidence,
                "features_used": position.ai_signal.features_used,
                "time_horizon": position.ai_signal.time_horizon_days
            },
            "position_sizing": {
                "shares": position.position_size_shares,
                "value": position.position_size_dollars,
                "risk": position.max_risk_dollars,
                "stop_distance": position.entry_price - position.stop_price
            },
            "schedule": {
                "entry_date": position.entry_date.isoformat(),
                "scheduled_exit": position.exit_date.isoformat()
            }
        }
        
        # Save to explainability log
        self._save_explanation_log(explanation)
    
    def _save_explanation_log(self, explanation: Dict[str, Any]):
        """Save explanation to JSON log for regulatory compliance"""
        try:
            log_file = f"logs/trade_explanations_{dt.date.today().isoformat()}.json"
            os.makedirs("logs", exist_ok=True)
            
            with open(log_file, "a") as f:
                f.write(json.dumps(explanation) + "\n")
                
        except Exception as e:
            self.logger.error(f"Failed to save explanation log: {e}")
    
    def _exit_position(self, position: ShortCyclePosition, exit_price: float, reason: str):
        """Exit a position and update tracking"""
        try:
            # CRITICAL: Submit actual SELL order to Alpaca via RealPaperTradingEngine
            if hasattr(self, 'execution_engine') and self.execution_engine:
                order_result = self.execution_engine.submit_order(
                    symbol=position.symbol,
                    quantity=position.position_size_shares,
                    side='sell'
                )
                
                if order_result:
                    self.logger.info(f"✅ REAL SELL ORDER SUBMITTED: {position.symbol} {position.position_size_shares} shares")
                    self.logger.info(f"   Order ID: {order_result['order_id']}")
                    self.logger.info(f"   Status: {order_result['status']}")
                else:
                    self.logger.error(f"❌ FAILED to submit real sell order for {position.symbol}")
                    return False
            else:
                # Fallback to paper trade logging only if no execution engine
                self.logger.info(f"📝 Paper sell: {position.symbol} {position.position_size_shares} shares")
            
            position.exit_price = exit_price
            position.exit_reason = reason
            position.exit_timestamp = dt.datetime.now()  # Record when exit occurred
            position.realized_pnl = position.calculate_realized_pnl(exit_price)
            position.hold_days = (dt.date.today() - position.entry_date).days
            
            if reason == "STOP_LOSS":
                position.status = PositionStatus.STOPPED_OUT
            else:
                position.status = PositionStatus.EXITED
            
            # Add to daily realized PnL (will be properly recalculated in _update_daily_pnl)
            self.daily_realized_pnl += position.realized_pnl

            # Track for safety/performance
            try:
                trade_record = type("_Trade", (), {})()
                trade_record.net_pnl = position.realized_pnl
                trade_record.symbol = position.symbol
                self.recent_trades.append(trade_record)
                self.recent_trades = self.recent_trades[-50:]
            except Exception:
                pass
            
            self.logger.info(f"🔄 {position.symbol}: Exited @ ${exit_price:.2f}, "
                           f"P&L: ${position.realized_pnl:.2f}, Reason: {reason}")
            
            # Notify dashboard about executed SELL trade
            self._notify_trade_executed(position.symbol, {
                'action': 'SELL',
                'quantity': position.position_size_shares,
                'price': exit_price,
                'pnl': position.realized_pnl,
                'reason': reason,
                'timestamp': dt.datetime.now()
            })
            
            # Log exit explanation
            self._log_exit_explanation(position)
            
            # Save positions after exit
            self._save_positions()
            
        except Exception as e:
            self.logger.error(f"Error exiting position {position.symbol}: {e}")
    
    def _log_exit_explanation(self, position: ShortCyclePosition):
        """Log exit decision explanation"""
        explanation = {
            "timestamp": dt.datetime.now().isoformat(),
            "symbol": position.symbol,
            "action": "EXIT",
            "exit_reason": position.exit_reason,
            "hold_days": position.hold_days,
            "performance": {
                "entry_price": position.entry_price,
                "exit_price": position.exit_price,
                "realized_pnl": position.realized_pnl,
                "return_pct": (position.exit_price / position.entry_price - 1) * 100
            }
        }
        
        self._save_explanation_log(explanation)
    
    def _maybe_reset_daily_counters(self):
        """Reset daily P&L counters at market open if not already reset today"""
        today = dt.date.today()
        if self.last_pnl_reset_date != today:
            self.daily_pnl = 0.0
            self.daily_realized_pnl = 0.0
            self.daily_unrealized_pnl = 0.0
            self.trades_today = 0
            self.last_pnl_reset_date = today
            # Reset daily kill switch
            if "daily_loss_exceeded" in self.kill_switches:
                self.kill_switches["daily_loss_exceeded"] = False
            self.logger.info(f"🔄 Daily counters reset for {today}")

    def _update_daily_pnl(self):
        """Update daily P&L tracking with correct logic for exits"""
        today = dt.date.today()
        
        # Calculate realized P&L from positions exited today (regardless of entry date)
        today_exits = [
            p for p in self.positions 
            if p.exit_timestamp is not None and p.exit_timestamp.date() == today and p.realized_pnl is not None
        ]
        self.daily_realized_pnl = sum(p.realized_pnl for p in today_exits)
        
        # Calculate unrealized P&L from currently open positions
        open_positions = [p for p in self.positions if p.status == PositionStatus.ENTERED]
        self.daily_unrealized_pnl = sum(p.unrealized_pnl or 0 for p in open_positions)
        
        # Total daily P&L
        self.daily_pnl = self.daily_realized_pnl + self.daily_unrealized_pnl
        
        self.logger.debug(f"Daily P&L update: Realized ${self.daily_realized_pnl:.2f}, "
                         f"Unrealized ${self.daily_unrealized_pnl:.2f}, "
                         f"Total ${self.daily_pnl:.2f}")
    
    def _check_loss_limits(self):
        """Check daily and weekly loss limits (only trigger on actual losses)"""
        from utils import market_hours
        
        # Only check loss limits during market hours to avoid false triggers during initialization
        if not market_hours.is_regular_session_now():
            return
            
        # Check daily loss limit - only trigger on NEGATIVE daily realized P&L
        if self.daily_realized_pnl < 0 and abs(self.daily_realized_pnl) > self.config.max_daily_loss_dollars:
            self.kill_switches["daily_loss_exceeded"] = True
            self.logger.warning(f"🛑 Daily loss limit exceeded: ${self.daily_realized_pnl:.2f} "
                              f"(limit: ${self.config.max_daily_loss_dollars:.0f})")
            self.logger.info("🛡️ Circuit breaker: Stopping new trades, allowing scheduled D+1 exits")
        
        # Calculate weekly P&L (sum of realized P&L from positions exited this week)
        week_start = dt.date.today() - dt.timedelta(days=dt.date.today().weekday())
        weekly_exits = [
            p for p in self.positions 
            if p.exit_timestamp is not None and p.exit_timestamp.date() >= week_start and p.realized_pnl is not None
        ]
        self.weekly_pnl = sum(p.realized_pnl for p in weekly_exits)
        
        # Check weekly loss limit - only trigger on NEGATIVE weekly realized P&L
        if self.weekly_pnl < 0 and abs(self.weekly_pnl) > self.config.max_weekly_loss_dollars:
            self.kill_switches["weekly_loss_exceeded"] = True
            self.logger.warning(f"🛑 Weekly loss limit exceeded: ${self.weekly_pnl:.2f} "
                              f"(limit: ${self.config.max_weekly_loss_dollars:.0f})")
            self.logger.info("�️ Circuit breaker: Stopping new trades, allowing scheduled D+1 exits")
    
    def _generate_daily_report(self):
        """Generate daily performance and status report"""
        active_positions = [p for p in self.positions if p.status == PositionStatus.ENTERED]
        
        report = {
            "date": dt.date.today().isoformat(),
            "portfolio_value": self._get_portfolio_value(),
            "active_positions": len(active_positions),
            "daily_pnl": self.daily_pnl,
            "weekly_pnl": self.weekly_pnl,
            "trades_today": self.trades_today,
            "kill_switches": self.kill_switches
        }
        
        self.logger.info(f"📊 Daily Report: {json.dumps(report, indent=2)}")

    # --- Sprint 2 helper estimates (placeholders until full PnL book is wired) ---
    def _estimate_weekly_return(self) -> float:
        try:
            return (self.weekly_pnl / max(1.0, self.config.portfolio_value))
        except Exception:
            return 0.0

    def _estimate_drawdown(self) -> float:
        # Placeholder: use negative min of cumulative pnl vs 0 relative to portfolio
        try:
            # In Sprint 0 we lack equity curve; return conservative proxy
            return 0.0
        except Exception:
            return 0.0

    def _estimate_win_rate(self) -> float:
        try:
            wins = sum(1 for t in self.recent_trades if getattr(t, 'net_pnl', 0) > 0)
            total = len(self.recent_trades)
            return wins / total if total else 0.0
        except Exception:
            return 0.0

    def _estimate_consecutive_losses(self) -> int:
        try:
            count = 0
            for t in reversed(self.recent_trades):
                if getattr(t, 'net_pnl', 0) <= 0:
                    count += 1
                else:
                    break
            return count
        except Exception:
            return 0
    
    # Helper methods (to be implemented with real data feeds)
    def _get_current_price(self, symbol: str) -> Optional[float]:
        """Get current market price for symbol"""
        try:
            price = self.data_loader.get_current_price(symbol)
            return price
        except Exception:
            return None
    
    def _get_market_data(self) -> Dict[str, pd.DataFrame]:
        """Get market data for analysis"""
        # Fetch recent OHLCV for symbols in today's trading universe
        try:
            universe = self._get_trading_universe()
            days = 40  # enough for momentum/volume windows
            data_by_symbol: Dict[str, pd.DataFrame] = {}
            for sym in universe:
                try:
                    df = self.data_loader.get_historical_data(sym, days=days)
                    if isinstance(df, pd.DataFrame) and not df.empty:
                        data_by_symbol[sym] = df
                except Exception as e:
                    self.logger.warning(f"DataLoader failed for {sym}: {e}")
            return data_by_symbol
        except Exception as e:
            self.logger.warning(f"_get_market_data fallback due to error: {e}")
            return {}
    
    
    def _get_trading_universe(self) -> List[str]:
        """Get list of symbols from config; auto-augment to hit Sprint 2 coverage using PreFilter if enabled."""
        try:
            cfg_path = _Path("config/short_cycle_universe.json")
            if cfg_path.exists():
                cfg = _json.loads(cfg_path.read_text())
                static_universe = list(dict.fromkeys(cfg.get("base_universe", [])))  # de-dup, keep order
                min_symbols = int(cfg.get("min_symbols", 15))
                max_cfg = cfg.get("max_symbols", 25)
                max_symbols = int(max_cfg) if isinstance(max_cfg, int) else None
            else:
                static_universe = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
                min_symbols = 15
                max_symbols = 25

            # Always try PreFilter first
            try:
                from pre_filter import PreFilter
                candidates = [
                    "AAPL","MSFT","GOOGL","AMZN","TSLA","NVDA","META","NFLX","AMD","AVGO",
                    "INTC","IBM","ORCL","CRM","ADBE","CSCO","QCOM","SHOP","UBER","LYFT",
                    "DIS","WMT","XOM","CVX","BA","CAT","KO","PEP","JNJ","PFE","BAC","JPM","GS"
                ]
                # Fetch recent OHLCV from DataLoader for PreFilter input
                if self._prefilter is None:
                    self._prefilter = PreFilter(
                        simulation_mode=False,
                        data_loader=self.data_loader,
                        fast_mode=self.config.fast_mode if hasattr(self.config, 'fast_mode') else True,
                    )

                history_df = self._prefilter.fetch_history(candidates, days=40, use_cache=True)
                if history_df.empty:
                    raise RuntimeError("No historical data available for PreFilter candidates")

                df = history_df
                filtered = self._prefilter.filter_assets(history_df)
                # If pf_score present, rank by it; else by latest volume
                snap = filtered.groupby('symbol').tail(1)
                if 'pf_score' in snap.columns:
                    ranked = snap.sort_values('pf_score', ascending=False)
                else:
                    ranked = snap.sort_values('volume', ascending=False)
                ranked_symbols = ranked['symbol'].tolist()
                # Accept PreFilter output when it yields at least 10 quality names.
                # If it's below configured min_symbols, top up from static universe instead of discarding.
                if len(ranked_symbols) >= 10:
                    final_list: List[str]
                    if max_symbols is None:
                        final_list = ranked_symbols[:]
                    else:
                        final_list = ranked_symbols[:max_symbols]
                    if len(final_list) < min_symbols:
                        # Top-up with static universe (no duplicates) to reach min_symbols
                        for sym in static_universe:
                            if sym not in final_list:
                                final_list.append(sym)
                                if len(final_list) >= min_symbols:
                                    break
                        if max_symbols is None:
                            self.logger.info(
                                f"✅ Using PreFilter universe with top-up: {len(ranked_symbols)} prefiltered + top-up -> {len(final_list)} total"
                            )
                        else:
                            self.logger.info(
                                f"✅ Using PreFilter universe with top-up: {len(ranked_symbols)} prefiltered + "
                                f"{len(final_list) - min(len(ranked_symbols), max_symbols)} top-up -> {len(final_list[:max_symbols])} total"
                            )
                    else:
                        self.logger.info(f"✅ Using PreFilter universe: {final_list}")
                    return final_list if max_symbols is None else final_list[:max_symbols]
                else:
                    self.logger.warning(
                        f"⚠️ PreFilter returned too few symbols ({len(ranked_symbols)}); falling back to static universe."
                    )
            except Exception as e:
                self.logger.warning(f"PreFilter unavailable or failed: {e}")

            # Fallback: use static config universe
            if max_symbols is None:
                self.logger.info(f"✅ Using static config universe (unbounded): {static_universe}")
                return static_universe
            self.logger.info(f"✅ Using static config universe: {static_universe[:max_symbols]}")
            return static_universe[:max_symbols]
        except Exception as e:
            self.logger.error(f"Error building trading universe: {e}")
            return ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "SPY", "QQQ"]
    
    def _update_risk_limits(self):
        """Update risk limits based on current portfolio value"""
        try:
            current_portfolio = self._get_portfolio_value()
            
            # Update config with current portfolio value
            old_portfolio = self.config.portfolio_value
            self.config.portfolio_value = current_portfolio
            
            # Update SafetyMonitor with new portfolio value
            if hasattr(self, 'safety_monitor') and self.safety_monitor:
                self.safety_monitor.portfolio_value = current_portfolio
            
            # Recalculate derived values
            self.config.daily_pool_dollars = current_portfolio * self.config.daily_pool_percent
            self.config.max_daily_loss_dollars = current_portfolio * self.config.max_daily_loss_percent
            self.config.max_weekly_loss_dollars = current_portfolio * self.config.max_weekly_loss_percent
            
            if abs(current_portfolio - old_portfolio) > 100:  # Only log significant changes
                self.logger.info(f"💰 Portfolio updated: ${old_portfolio:,.0f} → ${current_portfolio:,.0f}")
                self.logger.info(f"🎯 Daily pool: ${self.config.daily_pool_dollars:,.0f}, "
                               f"Daily loss limit: ${self.config.max_daily_loss_dollars:,.0f}")
                
        except Exception as e:
            self.logger.warning(f"⚠️ Could not update risk limits: {e}")

    def _get_portfolio_value(self) -> float:
        """Get current portfolio value from execution engine or fallback to config"""
        try:
            # Try to get live portfolio value from execution engine
            if hasattr(self, 'execution_engine') and self.execution_engine:
                portfolio_summary = self.execution_engine.get_portfolio_summary()
                
                # Handle different execution engine formats
                live_value = 0
                if portfolio_summary:
                    # For RealPaperTradingEngine format: {'account': {'portfolio_value': X}}
                    if 'account' in portfolio_summary and 'portfolio_value' in portfolio_summary['account']:
                        live_value = portfolio_summary['account']['portfolio_value']
                    # For regular ExecutionEngine format: {'equity': X}
                    elif 'equity' in portfolio_summary:
                        live_value = portfolio_summary['equity']
                
                if live_value and live_value > 0:
                    self.logger.debug(f"💰 Live portfolio value: ${live_value:,.2f}")
                    return float(live_value)
                else:
                    self.logger.warning(f"⚠️ Invalid live portfolio value ({live_value}), using config fallback")
                    return self.config.portfolio_value
            else:
                # Fallback: try stock API if available
                try:
                    from stock_api import StockAPI
                    api = StockAPI()
                    account_info = api.get_account_info()
                    
                    live_value = account_info.get('account_value', 0)
                    if live_value and live_value > 0:
                        self.logger.debug(f"💰 Live portfolio value (API): ${live_value:,.2f}")
                        return float(live_value)
                except:
                    pass  # Fall through to config fallback
                
                self.logger.warning(f"⚠️ No live portfolio data available, using config fallback")
                return self.config.portfolio_value
                
        except Exception as e:
            self.logger.warning(f"⚠️ Could not fetch live portfolio value: {e}, using config fallback")
            return self.config.portfolio_value
    
    def _get_live_portfolio_positions(self) -> Dict[str, Dict[str, float]]:
        """Fetch normalized live positions keyed by symbol."""
        try:
            if hasattr(self, 'execution_engine') and self.execution_engine:
                raw_positions = self.execution_engine.get_positions() or {}
                normalized: Dict[str, Dict[str, float]] = {}
                for symbol, pos in raw_positions.items():
                    try:
                        qty = float(pos.get('quantity', 0) or 0)
                    except Exception:
                        qty = 0.0
                    side = (pos.get('side') or '').lower()
                    qty = -abs(qty) if side == 'short' else abs(qty)
                    normalized[symbol.upper()] = {
                        'quantity': qty,
                        'avg_cost': float(pos.get('avg_cost', 0) or 0),
                        'market_value': float(pos.get('market_value', 0) or 0),
                        'unrealized_pnl': float(pos.get('unrealized_pnl', 0) or 0),
                        'side': pos.get('side'),
                    }
                return normalized
        except Exception as e:
            self.logger.warning(f"⚠️ Could not fetch live positions: {e}")
        return {}

    def _sync_positions_with_portfolio(self, live_positions: Dict[str, Dict[str, float]]) -> bool:
        """Align internal position tracker with broker portfolio to avoid phantom exits."""
        state_changed = False
        live_symbols = {
            symbol.upper(): data for symbol, data in live_positions.items()
            if abs(data.get('quantity', 0)) > 1e-6
        }

        tracked_active_symbols = set()

        for position in self.positions:
            symbol_key = position.symbol.upper()
            live_data = live_symbols.get(symbol_key)

            if position.status == PositionStatus.ENTERED:
                if not live_data:
                    self.logger.info(
                        f"🔕 {position.symbol}: No live holdings detected; marking as exited to prevent phantom sells"
                    )
                    position.status = PositionStatus.EXITED
                    position.exit_reason = "PORTFOLIO_MISMATCH"
                    position.exit_timestamp = dt.datetime.now()
                    state_changed = True
                    continue

                tracked_active_symbols.add(symbol_key)

                live_qty = int(round(abs(live_data.get('quantity', 0))))
                if live_qty > 0 and live_qty != position.position_size_shares:
                    self.logger.info(
                        f"🔄 {position.symbol}: Aligning tracked size {position.position_size_shares} → {live_qty} shares"
                    )
                    position.position_size_shares = live_qty
                    avg_cost = live_data.get('avg_cost') or position.entry_price
                    if avg_cost:
                        position.entry_price = float(avg_cost)
                    position.position_size_dollars = live_qty * position.entry_price
                    state_changed = True

        for symbol_key, live_data in live_symbols.items():
            if symbol_key not in tracked_active_symbols:
                self.logger.warning(
                    f"⚠️ Live portfolio includes {symbol_key} ({live_data.get('quantity')} shares) not tracked in positions.json"
                )

        return state_changed

    def _get_next_trading_day(self, current_date: dt.date) -> dt.date:
        """Get next trading day for D+1 exit scheduling"""
        next_day = current_date + dt.timedelta(days=1)
        # Simple weekend handling
        if next_day.weekday() >= 5:  # Weekend
            next_day = current_date + dt.timedelta(days=3 if current_date.weekday() == 4 else 1)
        return next_day
    
    def _load_positions(self):
        """Load positions from previous session"""
        try:
            import os
            import json
            positions_file = "positions.json"
            
            if os.path.exists(positions_file):
                with open(positions_file, 'r') as f:
                    position_data = json.load(f)
                
                self.positions = []
                for data in position_data:
                    # Reconstruct dates
                    entry_date = dt.datetime.fromisoformat(data['entry_date']).date()
                    exit_date = None
                    if data.get('exit_date'):
                        exit_date = dt.datetime.fromisoformat(data['exit_date']).date()
                    else:
                        # For active positions, set exit date to tomorrow (D+1 rule)
                        if data.get('status') == 'entered':
                            exit_date = self._get_next_trading_day(entry_date)

                    # Reconstruct AI signal (fallbacks for older schema)
                    ai = data.get('ai_signal', {}) or {}
                    ai_ts = None
                    if ai.get('timestamp'):
                        try:
                            ai_ts = dt.datetime.fromisoformat(ai['timestamp'])
                        except Exception:
                            ai_ts = None

                    ai_signal = AISignal(
                        symbol=data['symbol'],
                        action=ai.get('action', 'BUY'),
                        confidence=ai.get('confidence', data.get('confidence', 0.5)),  # Fallback to old format
                        time_horizon_days=ai.get('time_horizon_days', data.get('time_horizon_days', 1.5)),  # Fallback
                        entry_price=data.get('entry_price'),
                        target_price=ai.get('target_price', data.get('target_price')),
                        signal_timestamp=ai_ts,
                        features_used=ai.get('features_used', {})
                    )

                    # Reconstruct position object
                    position = ShortCyclePosition(
                        symbol=data['symbol'],
                        entry_date=entry_date,
                        exit_date=exit_date,
                        entry_price=data['entry_price'],
                        position_size_shares=data.get('position_size_shares', 0),
                        position_size_dollars=data['position_size_dollars'],
                        stop_price=data.get('stop_price', 0.0),
                        target_price=data.get('target_price'),
                        status=PositionStatus(data['status']),
                        ai_signal=ai_signal,
                        max_risk_dollars=data.get('max_risk_dollars', 0.0)
                    )
                    
                    # Restore exit data
                    if data.get('exit_price'):
                        position.exit_price = data['exit_price']
                    if data.get('exit_reason'):
                        position.exit_reason = data['exit_reason']
                    if data.get('realized_pnl') is not None:
                        position.realized_pnl = data['realized_pnl']
                    
                    self.positions.append(position)
                
                self.logger.info(f"📋 Loaded {len(self.positions)} positions from previous session")
            else:
                self.logger.info("📋 No previous positions found - starting fresh")
                
        except Exception as e:
            self.logger.error(f"Error loading positions: {e}")
            self.positions = []
    
    def _save_positions(self):
        """Save current positions to file"""
        try:
            import json
            positions_file = "positions.json"
            
            position_data = []
            for position in self.positions:
                data = {
                    'symbol': position.symbol,
                    'entry_date': position.entry_date.isoformat(),
                    'exit_date': position.exit_date.isoformat(),
                    'entry_price': position.entry_price,
                    'position_size_shares': position.position_size_shares,
                    'position_size_dollars': position.position_size_dollars,
                    'stop_price': position.stop_price,
                    'target_price': position.target_price,
                    'status': position.status.value if hasattr(position.status, 'value') else position.status,
                    'max_risk_dollars': position.max_risk_dollars,
                    'ai_signal': {
                        'action': position.ai_signal.action,
                        'confidence': position.ai_signal.confidence,
                        'time_horizon_days': position.ai_signal.time_horizon_days,
                        'entry_price': position.ai_signal.entry_price,
                        'target_price': position.ai_signal.target_price,
                        'features_used': position.ai_signal.features_used,
                        'timestamp': position.ai_signal.signal_timestamp.isoformat() if position.ai_signal.signal_timestamp else None
                    },
                    'exit_price': position.exit_price,
                    'exit_reason': position.exit_reason,
                    'realized_pnl': position.realized_pnl
                }
                position_data.append(data)
            
            with open(positions_file, 'w') as f:
                json.dump(position_data, f, indent=2)
                
            self.logger.info(f"💾 Saved {len(self.positions)} positions to {positions_file}")
            
        except Exception as e:
            self.logger.error(f"Error saving positions: {e}")


# Sprint 0 Testing and Validation
def test_short_cycle_system():
    """Test short-cycle system components"""
    print("🧪 Testing Short-Cycle Trading System (Sprint 0)")
    
    try:
        # Test configuration
        config = ShortCycleConfig()
        print(f"✅ Config: ${config.portfolio_value} portfolio, ${config.daily_pool_dollars:.0f} daily pool")
        
        # Test AI components
        signal_gen = AISignalGenerator(config)
        stop_mgr = AIStopLossManager(config)
        position_sizer = AIConfidencePositionSizer(config)
        risk_mgr = AIPredictiveRiskManager(config)
        regime_detector = AIMarketRegimeDetector(config)
        
        print("✅ AI components initialized")
        
        # Test main trader
        trader = ShortCycleTrader(config)
        print("✅ Short-cycle trader initialized")
        
        # Test daily cycle (dry run)
        print("🔄 Testing daily cycle...")
        trader.run_daily_cycle()
        
        print("✅ Sprint 0 core infrastructure test complete")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


if __name__ == "__main__":
    print("🚀 LiteBotX Short-Cycle Trader - Sprint 0")
    print("=" * 50)
    
    # Run system test
    if test_short_cycle_system():
        print("\n🎯 Sprint 0 Complete: Core infrastructure ready")
        print("📋 Next: Sprint 1 - Implement ML models and feature engineering")
    else:
        print("\n❌ Sprint 0 failed - fix issues before proceeding")

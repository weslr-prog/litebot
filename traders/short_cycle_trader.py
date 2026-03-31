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
import math
import datetime as dt
import pytz
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
    # from config import Config  # OLD - archived to legacy_configs
    from data_loader import DataLoader
    from execution_engine import ExecutionEngine
    from risk import RiskManager
    from logger import setup_logger
    from connect_real_trading import RealPaperTradingEngine
    from short_cycle_safety import SafetyMonitor, SafetyConfig
    from monitoring.monitoring_system import SelfMonitoringSystem
    from pattern_recognizer import PatternRecognizer, PatternTracker, StockPattern
    from morning_gap_scanner import MorningGapScanner
    from intraday_quality_scorer import IntradayQualityScorer  # Enhanced signal quality
    from earnings_calendar import EarningsCalendar  # NEW: Earnings protection
    from entry_quality_screener import EntryQualityScreener  # NEW: Pattern-based entry screening
    from sector_specific_exit import SectorSpecificExitManager  # NEW: Sector-specific exit timing
    # Day trade tracking utility
    from utils.day_trade_tracker import DayTradeTracker
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
    # Portfolio parameters (OPTION 3: Triple Frequency + 60% Win Rate - $1K Portfolio)
    portfolio_value: float = 1000.0  # Starting with $1000 portfolio
    daily_pool_percent: float = 0.50  # 50% of portfolio per day (aggressive deployment for 12 trades/month)
    max_risk_per_trade_dollars: float = 20.0  # Risk per trade for position sizing (2% of $1K)
    max_position_dollars: float = 200.0  # Hard cap at $200 (20% max per position for $1K account)
    max_loss_per_trade_dollars: float = 20.0  # Hard stop at $20 per trade (2% of portfolio)
    
    # Position parameters (OPTION 3: Triple frequency target)
    max_positions_per_day: int = 12  # Tripled from 4/month to 12/month (3x frequency)
    min_position_size_dollars: float = 10.0  # Minimum viable position for $1K account
    max_position_size_percent: float = 0.20  # 20% max position size (hard cap at $200 enforced)
    max_universe_size: int = 100  # Maximum number of symbols in trading universe
    
    # Diversification parameters
    max_positions_per_symbol_small: int = 2  # Max positions per symbol for portfolios < $100K
    max_positions_per_symbol_large: int = 3  # Max positions per symbol for portfolios > $100K
    max_concentration_percent_small: float = 0.35  # Max 35% of positions in one symbol (small portfolios)
    max_concentration_percent_large: float = 0.40  # Max 40% of positions in one symbol (large portfolios)
    portfolio_threshold_large: float = 100000.0  # Threshold for "large" portfolio diversification rules
    
    # Time parameters (INTRADAY DAY TRADING - Same Day Only)
    max_hold_days: int = 0  # SAME-DAY ONLY - No overnight holds (cash account mode)
    trading_days: List[str] = None  # All trading days (Mon-Fri)
    exit_time: str = "15:45"  # 15 minutes before close - HARD EXIT for all positions
    
    # Risk parameters (OPTION 3: 60% Win Rate Target)
    max_daily_loss_percent: float = 0.08  # 8% daily loss limit
    max_weekly_loss_percent: float = 0.15   # 15% weekly loss limit
    confidence_threshold: float = 0.60  # 60% minimum confidence for high win rate (Option 3)
    
    # Trailing Stop Parameters (INTRADAY OPTIMIZED)
    enable_trailing_stops: bool = True  # Enable trailing stop system
    trailing_trigger_pct: float = 0.015  # Activate trailing stop after +1.5% gain
    trailing_distance_pct: float = 0.01  # Trail by 1.0% (if at +3%, stop at +2%)
    trailing_min_profit_pct: float = 0.01  # Lock in minimum +1.0% profit once activated
    trailing_update_interval_sec: int = 60  # Update trailing stops every 60 seconds
    
    # Backtesting parameters
    enable_forced_d1_exit: bool = False  # DISABLED - No D+1 exits (same-day only)
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
            self.signal_timestamp = dt.datetime.now(pytz.UTC)
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
    
    # Metadata (NEW NOV 12: sector tracking for diversification)
    sector: Optional[str] = None  # Stock sector (Energy, Tech, etc.)
    
    # Timestamp tracking (NEW - for accurate D+1 calculation)
    entry_timestamp: Optional[dt.datetime] = None  # When order was filled by broker
    filled_at: Optional[dt.datetime] = None  # Alpaca fill timestamp
    order_id: Optional[str] = None  # Broker order ID for tracking
    
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
    
    # Trailing stop tracking (NEW)
    trailing_stop_enabled: bool = False
    trailing_stop_price: Optional[float] = None
    highest_price_since_entry: Optional[float] = None
    trailing_stop_activated_at: Optional[dt.datetime] = None
    
    def update_current_price(self, price: float):
        """Update current price and unrealized P&L"""
        self.current_price = price
        if self.status == PositionStatus.ENTERED:
            self.unrealized_pnl = (price - self.entry_price) * self.position_size_shares
    
    def should_force_exit(self, current_date: dt.date) -> bool:
        """Check if position should be force-exited due to D+1 rule"""
        return current_date >= self.exit_date
    
    def is_d1_eligible(self, current_datetime: dt.datetime, cash_account_mode: bool = False) -> bool:
        """
        Check if position is eligible for exit on current trading day.
        
        Rules:
        - Margin/PDT Account: If bought before close on Day T, eligible for exit on Day T+1 (next trading day)
        - Cash Account: Can exit same day (no PDT restrictions)
        
        Args:
            current_datetime: Current date/time to check
            cash_account_mode: If True, allow same-day exits (no PDT restrictions)
        
        Returns: True if eligible for exit today
        """
        # CASH ACCOUNT MODE: Always eligible to exit (no PDT restrictions)
        if cash_account_mode:
            return True
        
        # MARGIN ACCOUNT MODE: Original PDT-compliant logic
        if not self.entry_timestamp and not self.filled_at:
            # Fallback to old date-based logic if no timestamp
            return current_datetime.date() >= self.exit_date
        
        # Use actual fill timestamp
        fill_time = self.filled_at if self.filled_at else self.entry_timestamp
        
        # Check if we're on a different trading day
        # (Simple implementation - could enhance with market calendar)
        fill_date = fill_time.date()
        current_date = current_datetime.date()
        
        # INTRADAY MODE: If cash account, no D+1 requirement - can exit same day
        # If filled today, can exit immediately based on profit/loss targets
        if cash_account_mode:
            return True  # Always eligible in cash account mode
        
        # Legacy mode: If filled before close on Day T, eligible on Day T+1
        return current_date > fill_date
    
    def should_smart_exit(self, current_date: dt.date, current_price: float, current_time: dt.datetime = None, cash_account_mode: bool = False, market_data: Optional[pd.DataFrame] = None) -> tuple[bool, str]:
        """
        ENHANCED Smart exit logic optimized for mean reversion RSI (Nov 22, 2025)
        
        Strategy:
        - PRIMARY EXIT: RSI > 50 (neutral) - mean reversion complete
        - SECONDARY EXIT: Profit target >= 2%
        - EMERGENCY EXIT: Stop loss <= -2%
        - FRIDAY EXIT: Force exit at 3:45 PM (prevent weekend holding)
        
        Args:
            current_date: Current date
            current_price: Current stock price
            current_time: Current datetime (defaults to now)
            cash_account_mode: IGNORED - always use margin account rules (D+1 minimum hold)
            market_data: Current market data DataFrame with OHLCV (for RSI calculation)
        
        Returns: (should_exit, reason)
        """
        if current_time is None:
            current_time = dt.datetime.now(pytz.UTC)
        
        # INTRADAY MODE: Check if eligible for exit (cash account allows same-day)
        if not self.is_d1_eligible(current_time, cash_account_mode):
            return False, "NOT_ELIGIBLE_YET"
        
        # Past exit date - force exit immediately (should not happen in intraday mode)
        if current_date > self.exit_date:
            return True, "FORCED_EXIT_LATE"
        
        # Validate price data
        if current_price is None or self.entry_price is None:
            return False, "INVALID_PRICE_DATA"
        
        # Calculate profit/loss percentage
        pnl_pct = (current_price - self.entry_price) / self.entry_price
        
        # Market time calculation
        market_hour = current_time.hour
        market_minute = current_time.minute
        time_fraction = market_hour + market_minute / 60.0
        
        # EMERGENCY RULES (HIGHEST PRIORITY - CHECK FIRST)
        # Stop Loss: Down >=2% any time
        if pnl_pct <= -0.02:
            return True, "EMERGENCY_STOP_LOSS"
        
        # MEAN REVERSION RSI EXIT STRATEGY (Nov 22, 2025)
        # Optimization Test #2852: 19.17% weekly, 62.7% win rate
        
        # PRIMARY EXIT: RSI neutral (mean reversion complete)
        if market_data is not None and len(market_data) >= 7:
            try:
                from core.indicators import calculate_rsi
                df_with_rsi = calculate_rsi(market_data, window=7)
                current_rsi = df_with_rsi['rsi'].iloc[-1]
                
                # Exit when RSI crosses back to neutral (mean reversion complete)
                if current_rsi > 50:
                    return True, f"RSI_NEUTRAL_{current_rsi:.1f}"
            except Exception as e:
                # If RSI calculation fails, fall back to profit target only
                pass
        
        # SECONDARY EXIT: Profit target >= 2%
        if pnl_pct >= 0.02:
            return True, "PROFIT_TARGET_2PCT"
        
        # FRIDAY WEEKEND EXIT LOGIC (prevent weekend holding)
        if current_time.weekday() == 4:  # Friday
            # Force exit all positions at 3:45 PM to avoid weekend risk
            if time_fraction >= 15.75:  # 3:45 PM or later
                return True, "FRIDAY_FORCE_EXIT_WEEKEND_RISK"
        
        # OPENING PATIENCE: Don't exit losing positions in first 30 min (avoid volatility)
        # Let gaps recover before making exit decisions
        if time_fraction < 10.0:  # Before 10:00 AM
            # Exception: Allow profit-taking and emergency stops
            if pnl_pct < 0 and pnl_pct > -0.02:  # Losing but not emergency
                return False, "OPENING_PATIENCE_HOLD"
        
        return False, "WAITING_FOR_SIGNAL"
    
    def is_stopped_out(self, current_price: float) -> bool:
        """Check if position should be stopped out"""
        if self.status != PositionStatus.ENTERED:
            return False
        # Handle None stop_price or current_price gracefully
        if self.stop_price is None or current_price is None:
            return False
        return current_price <= self.stop_price
    
    def update_trailing_stop(self, current_price: float, trailing_stop_pct: float = 0.025, logger=None) -> tuple[bool, Optional[str]]:
        """
        Update trailing stop for winners and check if stop hit
        OPTIMIZED (Nov 22, 2025): Based on parameter optimization results
        
        Strategy:
        - Activate trailing stop when position is up >3% (was 1%)
        - Trail stop 2.5% below highest price (was 1.5%)
        - Adaptive distance 1.5-3.0% based on momentum (was 1.2-1.8%)
        - Once activated, stop follows price up but never down
        
        Args:
            current_price: Current market price
            trailing_stop_pct: Trailing distance (default 2.5%, optimized)
            logger: Optional logger for output
            
        Returns:
            (should_exit, reason) - True if trailing stop hit
        """
        if self.status != PositionStatus.ENTERED or current_price is None:
            return False, None
        
        # Calculate current P&L percentage
        pnl_pct = (current_price - self.entry_price) / self.entry_price
        
        # Activate trailing stop if up >3% and not yet activated (optimized from 1%)
        if not self.trailing_stop_enabled and pnl_pct >= 0.03:
            self.trailing_stop_enabled = True
            self.highest_price_since_entry = current_price
            # Start with base trailing distance (2.5% optimized)
            self.trailing_stop_price = current_price * (1 - trailing_stop_pct)
            self.trailing_stop_activated_at = dt.datetime.now(pytz.UTC)
            if logger:
                logger.info(
                    f"🎯 {self.symbol}: Trailing stop ACTIVATED at ${current_price:.2f} "
                    f"(+{pnl_pct*100:.1f}%), stop=${self.trailing_stop_price:.2f}"
                )
            return False, None
        
        # Update trailing stop if already activated
        if self.trailing_stop_enabled:
            # OPTIMIZED: Calculate momentum-adaptive trailing distance
            # Use 5-min momentum proxy: compare current vs highest price
            momentum_pct = (current_price - self.highest_price_since_entry) / self.highest_price_since_entry
            
            # Adaptive trailing distance based on momentum (OPTIMIZED ranges)
            if momentum_pct > 0.005:  # Strong momentum up (>0.5% from peak)
                adaptive_trail_pct = 0.025  # 2.5% - wider trail (was 1.8%)
            elif momentum_pct < -0.003:  # Weakening (>0.3% below peak)
                adaptive_trail_pct = 0.015  # 1.5% - tighter trail (was 1.2%)
            else:
                adaptive_trail_pct = 0.025  # 2.5% - standard trail (was 1.5%)
            
            # Update highest price if new high reached
            if current_price > self.highest_price_since_entry:
                self.highest_price_since_entry = current_price
                new_stop = current_price * (1 - adaptive_trail_pct)
                
                # Only move stop up, never down
                if new_stop > self.trailing_stop_price:
                    old_stop = self.trailing_stop_price
                    self.trailing_stop_price = new_stop
                    if logger:
                        logger.info(
                            f"📈 {self.symbol}: Trailing stop raised ${old_stop:.2f} → ${new_stop:.2f} "
                            f"(price=${current_price:.2f}, trail={adaptive_trail_pct*100:.1f}%, +{pnl_pct*100:.1f}%)"
                        )
            
            # Check if trailing stop hit
            if current_price <= self.trailing_stop_price:
                locked_profit = self.trailing_stop_price - self.entry_price
                locked_profit_pct = locked_profit / self.entry_price * 100
                if logger:
                    logger.info(
                        f"🛑 {self.symbol}: Trailing stop HIT at ${current_price:.2f} "
                        f"(stop=${self.trailing_stop_price:.2f}, locked profit: +{locked_profit_pct:.1f}%)"
                    )
                return True, f"TRAILING_STOP (profit locked: +{locked_profit_pct:.1f}%)"
        
        return False, None
    
    def calculate_realized_pnl(self, exit_price: float) -> float:
        """Calculate realized P&L on exit"""
        return (exit_price - self.entry_price) * self.position_size_shares


class AISignalGenerator:
    """AI-powered signal generation with multi-source inputs and confidence scoring"""
    
    def __init__(self, config: ShortCycleConfig, price_fetcher=None):
        self.config = config
        self.logger = logging.getLogger(__name__ + ".AISignalGenerator")
        self.price_fetcher = price_fetcher  # Function to fetch real-time prices
        
        # Model placeholders (Sprint 1 implementation)
        self.model = None
        self.feature_pipeline = None
        
        # Enhanced quality scoring
        try:
            self.quality_scorer = IntradayQualityScorer()
            self.logger.info("✅ Enhanced quality scorer initialized")
        except Exception as e:
            self.logger.warning(f"⚠️ Could not initialize quality scorer: {e}")
            self.quality_scorer = None
        
        # Entry quality screening (observation mode - logs but doesn't block)
        try:
            self.entry_screener = EntryQualityScreener(strict_mode=False)
            self.screening_enabled = True  # Feature flag
            self.logger.info("✅ Entry quality screener initialized (OBSERVATION MODE)")
            self.logger.info("   📊 Screening will log quality but NOT block entries")
        except Exception as e:
            self.logger.warning(f"⚠️ Could not initialize entry screener: {e}")
            self.entry_screener = None
            self.screening_enabled = False
        
        # Sector-specific exit manager
        try:
            self.exit_manager = SectorSpecificExitManager()
            self.logger.info("✅ Sector-specific exit manager initialized")
        except Exception as e:
            self.logger.warning(f"⚠️ Could not initialize exit manager: {e}")
            self.exit_manager = None
        
        # Temporary rule-based system for Sprint 0
        self.momentum_lookback = 4
        self.volume_threshold = 1.0
        
    def generate_signals(self, universe: List[str], market_data: Dict[str, pd.DataFrame], 
                        active_positions: Optional[List] = None) -> List[AISignal]:
        """Generate AI signals for given universe
        
        Args:
            universe: List of candidate symbols
            market_data: Historical price data for each symbol
            active_positions: List of currently active positions (for PDT validation)
        """
        # CRITICAL FIX #1: Validate entry candidates to prevent PDT violations
        validated_universe = self._validate_entry_candidates(universe, active_positions or [])
        
        signals = []
        
        for symbol in validated_universe:
            try:
                signal = self._analyze_symbol(symbol, market_data.get(symbol))
                if signal and signal.confidence >= self.config.confidence_threshold:
                    signals.append(signal)
            except Exception as e:
                self.logger.error(f"Error analyzing {symbol}: {e}")
        
        # Sort by confidence and limit to max positions
        signals.sort(key=lambda x: x.confidence, reverse=True)
        return signals[:self.config.max_positions_per_day]
    
    def generate_signal(self, symbol: str, market_data: pd.DataFrame, 
                       current_positions: Optional[List] = None) -> Optional[AISignal]:
        """Generate a single AI signal for a symbol (used for late-entry scanning)
        
        Args:
            symbol: Symbol to analyze
            market_data: Historical price data for the symbol
            current_positions: List of currently active positions (for PDT validation)
            
        Returns:
            AISignal if valid signal found, None otherwise
        """
        try:
            # Validate entry candidate (check PDT/D+1 rules)
            active_symbols = {pos.symbol.upper() for pos in (current_positions or [])
                            if pos.status == PositionStatus.ENTERED}
            
            if symbol.upper() in active_symbols:
                self.logger.debug(f"{symbol}: Skipped - active position exists (D+1 rule)")
                return None
            
            # Analyze symbol
            return self._analyze_symbol(symbol, market_data)
            
        except Exception as e:
            self.logger.error(f"Error generating signal for {symbol}: {e}")
            return None
    
    def _validate_entry_candidates(self, candidates: List[str], active_positions: List) -> List[str]:
        """
        CRITICAL: Remove any symbols that already have active positions (D+1 rule enforcement)
        This prevents PDT violations like the CRM issue on Oct 22.
        
        Args:
            candidates: List of candidate symbols to validate
            active_positions: List of currently active positions
        """
        active_symbols = {pos.symbol.upper() for pos in active_positions 
                         if pos.status == PositionStatus.ENTERED}
        
        valid = [sym for sym in candidates if sym.upper() not in active_symbols]
        
        filtered = set(c.upper() for c in candidates) - set(v.upper() for v in valid)
        if filtered:
            self.logger.warning(
                f"⚠️ D+1 Rule: Filtered {len(filtered)} symbols with active positions: {filtered}"
            )
            self.logger.warning(
                f"   These symbols cannot be re-entered until existing positions are closed"
            )
        
        return valid
    
    def _analyze_symbol(self, symbol: str, data: Optional[pd.DataFrame]) -> Optional[AISignal]:
        """Analyze individual symbol with enhanced quality scoring"""
        if data is None or len(data) < self.momentum_lookback + 1:
            return None

        try:
            # Normalize column names (handle both upper and lowercase)
            data_normalized = data.copy()
            data_normalized.columns = [col.lower() for col in data_normalized.columns]
            
            # TREND FILTER: 20-day SMA - Only buy stocks in uptrends (Nov 20 addition)
            # This prevents buying "cheap stocks that are actually crashing"
            if len(data_normalized) >= 20:
                sma_20 = data_normalized['close'].rolling(20).mean().iloc[-1]
                current_price = data_normalized['close'].iloc[-1]
                
                if current_price < sma_20:
                    price_below_pct = ((sma_20 - current_price) / sma_20) * 100
                    self.logger.info(
                        f"❌ REJECT {symbol}: Price ${current_price:.2f} below 20-SMA ${sma_20:.2f} "
                        f"({price_below_pct:.1f}% below - downtrend)"
                    )
                    return None
            
            # ═══════════════════════════════════════════════════════════════
            # 3-STRATEGY STACK FOR D+1 SWING TRADING (Nov 24, 2025)
            # ═══════════════════════════════════════════════════════════════
            # Based on comprehensive backtest (15 strategies, 2011-2024):
            # 
            # STRATEGY 1: Mean Reversion RSI - +2.62%, 56.2% WR, 0.92 tr/wk
            # STRATEGY 2: Gap & Go - +2.78%, 45.2% WR, 1.71 tr/wk
            # STRATEGY 3: Double Bottom - +3.17%, 46% WR, 1.11 tr/wk
            #
            # Expected on 500 stocks: 40-90 trades/week, 5-8% monthly return
            # ═══════════════════════════════════════════════════════════════
            
            # Import RSI calculation
            from core.indicators import calculate_rsi
            
            # Calculate RSI(7) - optimal period from optimization
            df_with_rsi = calculate_rsi(data_normalized, window=7)
            current_rsi = df_with_rsi['rsi'].iloc[-1]
            
            # Volume confirmation (used by all strategies)
            volume_surge = data_normalized['volume'].iloc[-1] / data_normalized['volume'].tail(20).mean()
            volume_ratio = volume_surge / max(self.volume_threshold, 1e-6)
            volume_ratio_capped = min(volume_ratio, 2.5)
            
            # ───────────────────────────────────────────────────────────────
            # STRATEGY 1: MEAN REVERSION RSI (PRIMARY)
            # ───────────────────────────────────────────────────────────────
            # Backtest: +2.62% (5 years), 56.2% win rate, 1.54 profit factor
            # Entry: RSI(7) <= 30 (oversold) + 1.5x volume
            # Exit: RSI >= 70 (overbought) OR +3% profit OR -3% stop
            # Frequency: 0.92 trades/week on 11 stocks → ~42 trades/week on 500 stocks
            
            mean_reversion_signal = False
            mean_reversion_confidence = 0.0
            
            # Entry: RSI <= 30 = oversold (matches backtest threshold)
            if current_rsi <= 30:
                # More oversold = higher confidence
                # RSI 10 = 1.0, RSI 20 = 0.5, RSI 30 = 0.0
                rsi_confidence = (30 - current_rsi) / 20.0  # 10-30 RSI → 0-1.0 confidence
                volume_confidence = min(volume_ratio / 1.5, 1.0)  # 1.5x volume → 1.0 conf
                mean_reversion_confidence = min(rsi_confidence * volume_confidence, 1.0)
                mean_reversion_signal = volume_ratio >= 1.5  # Require 1.5x volume minimum
            
            # ───────────────────────────────────────────────────────────────
            # STRATEGY 2: GAP & GO (SECONDARY)
            # ───────────────────────────────────────────────────────────────
            # Backtest: +2.78% (5 years), 45.2% win rate, 1.52 profit factor
            # Entry: 2%+ gap up with volume confirmation
            # Exit: Gap fill OR +3% profit OR -2% stop OR D+1
            # Frequency: 1.71 trades/week on 11 stocks → ~78 trades/week on 500 stocks
            
            gap_and_go_signal = False
            gap_and_go_confidence = 0.0
            
            # Detect gap up: compare today's open to yesterday's close
            if len(data_normalized) >= 2:
                today_open = data_normalized['open'].iloc[-1]
                yesterday_close = data_normalized['close'].iloc[-2]
                gap_pct = (today_open - yesterday_close) / yesterday_close
                
                # Gap & Go entry: 2%+ gap up with volume
                if gap_pct >= 0.02:  # 2% minimum gap
                    # Larger gap = higher confidence (up to 5% gap)
                    # 2% gap = 0.0, 3.5% gap = 0.5, 5% gap = 1.0
                    gap_confidence = min((gap_pct - 0.02) / 0.03, 1.0)  # 2-5% → 0-1.0
                    volume_confidence = min(volume_ratio / 1.5, 1.0)  # 1.5x volume → 1.0 conf
                    gap_and_go_confidence = min(gap_confidence * volume_confidence, 1.0)
                    gap_and_go_signal = volume_ratio >= 1.5 and gap_pct <= 0.05  # Max 5% gap (avoid blow-off)
            
            # ───────────────────────────────────────────────────────────────
            # STRATEGY 3: DOUBLE BOTTOM PATTERN (TERTIARY)
            # ───────────────────────────────────────────────────────────────
            # Backtest: +3.17% (5 years), 45.7% win rate, 1.38 profit factor
            # Entry: Second test of support + RSI <= 35 + volume
            # Exit: +5% profit OR -2% stop OR D+1
            # Frequency: 1.11 trades/week on 11 stocks → ~50 trades/week on 500 stocks
            
            double_bottom_signal = False
            double_bottom_confidence = 0.0
            
            # Detect double bottom: find support level tested twice in last 20 days
            if len(data_normalized) >= 20:
                recent_lows = data_normalized['low'].tail(20)
                current_price = data_normalized['close'].iloc[-1]
                
                # Find significant lows (within 2% of each other)
                min_low = recent_lows.min()
                support_tests = (recent_lows <= min_low * 1.02).sum()  # Count lows within 2% of minimum
                
                # Double bottom: 2+ tests of support + RSI oversold + volume
                if support_tests >= 2 and current_rsi <= 35:
                    # More tests + lower RSI = higher confidence
                    support_confidence = min(support_tests / 3.0, 1.0)  # 2 tests = 0.67, 3+ tests = 1.0
                    rsi_confidence = (35 - current_rsi) / 20.0  # RSI 15 = 1.0, RSI 30 = 0.25
                    volume_confidence = min(volume_ratio / 1.5, 1.0)
                    double_bottom_confidence = min(support_confidence * rsi_confidence * volume_confidence, 1.0)
                    double_bottom_signal = volume_ratio >= 1.5
            
            # ───────────────────────────────────────────────────────────────
            # STRATEGY SELECTION: Choose best signal from 3 strategies
            # ───────────────────────────────────────────────────────────────
            # Priority: Highest confidence wins
            # This allows all 3 strategies to run in parallel on 500-stock universe
            
            strategies = [
                ('MEAN_REVERSION_RSI', mean_reversion_signal, mean_reversion_confidence),
                ('GAP_AND_GO', gap_and_go_signal, gap_and_go_confidence),
                ('DOUBLE_BOTTOM', double_bottom_signal, double_bottom_confidence)
            ]
            
            # Find best strategy (highest confidence among valid signals)
            best_strategy = None
            best_signal = False
            base_confidence = 0.0
            
            for strategy_name, signal, confidence in strategies:
                if signal and confidence > base_confidence:
                    best_strategy = strategy_name
                    best_signal = True
                    base_confidence = confidence

            # Enhance with quality scoring if available
            if best_signal and self.quality_scorer and len(data_normalized) >= 100:
                try:
                    quality_result = self.quality_scorer.score_signal(
                        symbol=symbol,
                        current_data=data_normalized,
                        current_price=data_normalized['close'].iloc[-1]
                    )
                    
                    quality_score = quality_result['total_score']
                    quality_tier = quality_result['quality_tier']
                    
                    # Convert quality score (0-100) to confidence boost
                    # Strong quality (70+) → 2x-3x confidence
                    # Medium quality (40-70) → 1.5x-2x confidence
                    # Weak quality (<40) → 1x confidence (no boost)
                    quality_multiplier = 1.0 + (quality_score / 50.0)  # 0→1x, 50→2x, 100→3x
                    enhanced_confidence = min(base_confidence * quality_multiplier, 1.0)
                    
                    self.logger.info(
                        f"🎯 {symbol} [{best_strategy}]: base_conf={base_confidence:.3f}, "
                        f"quality={quality_score:.1f} ({quality_tier}), "
                        f"multiplier={quality_multiplier:.2f}x → final={enhanced_confidence:.3f}"
                    )
                    confidence = enhanced_confidence
                except Exception as e:
                    self.logger.debug(f"Quality scoring failed for {symbol}: {e}")
                    confidence = base_confidence
            else:
                confidence = base_confidence

            # Strategy diagnostics logging
            if best_signal:
                self.logger.info(
                    f"🎯 {symbol} [{best_strategy}]: RSI={current_rsi:.1f}, "
                    f"vol_surge={volume_surge:.2f}x, confidence={confidence:.3f}"
                )
                
                # Log strategy-specific details
                if best_strategy == 'GAP_AND_GO' and len(data_normalized) >= 2:
                    today_open = data_normalized['open'].iloc[-1]
                    yesterday_close = data_normalized['close'].iloc[-2]
                    gap_pct = (today_open - yesterday_close) / yesterday_close
                    self.logger.info(f"   📈 Gap: {gap_pct*100:+.1f}% (${yesterday_close:.2f} → ${today_open:.2f})")
                elif best_strategy == 'DOUBLE_BOTTOM' and len(data_normalized) >= 20:
                    recent_lows = data_normalized['low'].tail(20)
                    min_low = recent_lows.min()
                    support_tests = (recent_lows <= min_low * 1.02).sum()
                    self.logger.info(f"   🔄 Support tests: {support_tests} at ${min_low:.2f}")
                elif best_strategy == 'MEAN_REVERSION_RSI':
                    self.logger.info(f"   📉 RSI oversold: {current_rsi:.1f} (threshold: 30)")

            # Entry signal generation (if best strategy found)
            if best_signal and confidence >= self.config.confidence_threshold:
                # Entry quality screening (observation mode - log but don't block)
                if self.screening_enabled and self.entry_screener:
                    try:
                        # Note: momentum_score not calculated for all strategies
                        # Using RSI as proxy for screening
                        should_enter, quality_level, reason = self.entry_screener.screen_entry(
                            symbol=symbol,
                            momentum=0.0,  # Not used for mean reversion/double bottom
                            volume_surge=volume_surge,
                            sector=None  # TODO: Add sector lookup
                        )
                        
                        # Log screening result with emoji indicators
                        quality_emoji = {
                            'IDEAL': '🟢',
                            'GOOD': '🟡', 
                            'ACCEPTABLE': '🟠',
                            'REJECT': '🔴'
                        }.get(quality_level, '⚪')
                        
                        self.logger.info(
                            f"📊 ENTRY SCREENING: {symbol} [{best_strategy}] → {quality_emoji} {quality_level}: {reason}"
                        )
                        
                        # Observation mode: Log only, don't block trades
                        # Future: Add soft enforcement option (block only REJECT quality)
                        
                    except Exception as e:
                        self.logger.warning(f"⚠️ Entry screening failed for {symbol}: {e}")
                
                # CRITICAL FIX (Nov 19): Get REAL-TIME price from Alpaca, not cached historical data
                # Bug discovered: MSTZ showed $10.59 (cached), actual fill $12.56 (18.6% slippage!)
                # Solution: Always fetch live price before creating signal
                realtime_price = None
                if self.price_fetcher:
                    try:
                        realtime_price = self.price_fetcher(symbol)
                    except Exception as e:
                        self.logger.debug(f"Price fetcher failed for {symbol}: {e}")
                
                if realtime_price is None:
                    # Fallback to historical if real-time fetch fails
                    realtime_price = data_normalized['close'].iloc[-1]
                    self.logger.debug(f"{symbol}: Using cached price ${realtime_price:.2f}")
                else:
                    # Log price source for transparency
                    cached_price = data_normalized['close'].iloc[-1]
                    price_diff_pct = abs(realtime_price - cached_price) / cached_price
                    if price_diff_pct > 0.02:  # >2% difference
                        self.logger.warning(
                            f"⚠️ {symbol}: Price mismatch - cached: ${cached_price:.2f}, "
                            f"real-time: ${realtime_price:.2f} ({price_diff_pct:.1%} diff)"
                        )
                
                # Create signal with strategy-specific metadata
                return AISignal(
                    symbol=symbol,
                    action="BUY",
                    confidence=confidence,
                    time_horizon_days=1.5,
                    entry_price=realtime_price,
                    features_used={
                        "rsi": current_rsi,
                        "volume_surge": volume_surge,
                        "volume_ratio": volume_ratio,
                        "base_confidence": base_confidence,
                        "quality_enhanced": confidence > base_confidence,
                        "strategy": best_strategy.lower(),
                        "entry_reason": f"{best_strategy}_SIGNAL",
                        # Strategy-specific features
                        "mean_reversion_conf": mean_reversion_confidence,
                        "gap_and_go_conf": gap_and_go_confidence,
                        "double_bottom_conf": double_bottom_confidence
                    }
                )
            else:
                # DETAILED REJECTION LOGGING
                # Show exactly why no signal was generated
                rejection_reasons = []
                
                if not best_signal:
                    rejection_reasons.append("No strategy triggered")
                    rejection_reasons.append(f"(MR: {mean_reversion_signal}, GG: {gap_and_go_signal}, DB: {double_bottom_signal})")
                
                if best_signal and confidence < self.config.confidence_threshold:
                    rejection_reasons.append(f"Confidence {confidence:.3f} < {self.config.confidence_threshold:.3f}")
                
                rejection_msg = " AND ".join(rejection_reasons)
                self.logger.info(f"   ❌ REJECT {symbol}: {rejection_msg}")
                
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
        self._vix_multiplier = None  # Cache VIX multiplier for the day
        self._vix_fetch_time = None
    
    def _get_vix_regime_multiplier(self) -> float:
        """Get VIX-based position size multiplier with daily caching"""
        from datetime import datetime, timedelta
        
        # Return cached value if fetched today
        if self._vix_multiplier is not None and self._vix_fetch_time is not None:
            if datetime.now() - self._vix_fetch_time < timedelta(hours=6):
                return self._vix_multiplier
        
        try:
            import yfinance as yf
            vix = yf.Ticker("^VIX").history(period='1d')['Close'].iloc[-1]
            
            if vix > 30:
                self.logger.warning(f"⚠️ EXTREME FEAR: VIX={vix:.1f} - Cutting positions by 50%")
                multiplier = 0.5
            elif vix > 25:
                self.logger.warning(f"⚠️ HIGH VOLATILITY: VIX={vix:.1f} - Reducing positions by 25%")
                multiplier = 0.75
            elif vix > 20:
                self.logger.info(f"✅ ELEVATED VIX: VIX={vix:.1f} - Normal positions")
                multiplier = 1.0
            else:
                self.logger.info(f"✅ LOW VIX: VIX={vix:.1f} - Normal positions")
                multiplier = 1.0
            
            # Cache result
            self._vix_multiplier = multiplier
            self._vix_fetch_time = datetime.now()
            
            return multiplier
            
        except Exception as e:
            self.logger.error(f"Failed to fetch VIX: {e} - Using normal position sizing")
            return 1.0
    
    def calculate_position_size(self, signal: AISignal, stop_price: float, 
                              current_portfolio_value: float) -> Tuple[float, float]:
        """
        Calculate optimal position size based on confidence and risk
        NEW OCT 29 2025: Enhanced with dynamic sizing based on signal strength
        Returns: (shares, position_value) - shares can be fractional for small positions
        """
        try:
            entry_price = signal.entry_price
            
            # DEBUG: Log input values
            self.logger.info(f"DEBUG {signal.symbol}: entry=${entry_price}, stop=${stop_price}, portfolio=${current_portfolio_value:.0f}")
            
            if entry_price is None or stop_price >= entry_price:
                self.logger.warning(f"DEBUG {signal.symbol}: REJECT - Invalid prices (entry={entry_price}, stop={stop_price})")
                return 0, 0.0
            
            # ENHANCED: Dynamic position sizing based on signal strength
            # Signal strength components:
            # 1. Confidence (0.0-1.0) - ML model certainty
            # 2. Expected return (signal.expected_return if available)
            # 3. Momentum strength (derived from confidence as proxy)
            
            base_risk = self.config.max_risk_per_trade_dollars
            
            # Multi-factor confidence multiplier (1.0x to 2.0x sizing)
            confidence_factor = signal.confidence  # 0.0-1.0
            
            # Tier-based sizing:
            # - High confidence (>0.75): 1.6x-2.0x sizing
            # - Medium confidence (0.55-0.75): 1.2x-1.6x sizing  
            # - Low confidence (<0.55): 1.0x-1.2x sizing
            if confidence_factor >= 0.75:
                # Strong signal: aggressive sizing
                confidence_multiplier = 1.6 + (confidence_factor - 0.75) * 1.6  # 1.6x-2.0x
                signal_tier = "HIGH"
            elif confidence_factor >= 0.55:
                # Medium signal: moderate sizing
                confidence_multiplier = 1.2 + (confidence_factor - 0.55) * 2.0  # 1.2x-1.6x
                signal_tier = "MEDIUM"
            else:
                # Weak signal: conservative sizing
                confidence_multiplier = 1.0 + (confidence_factor - 0.3) * 0.8  # 1.0x-1.2x
                signal_tier = "LOW"
            
            # Cap maximum multiplier at 2.0x for risk management
            confidence_multiplier = min(confidence_multiplier, 2.0)
            confidence_multiplier = max(confidence_multiplier, 1.0)  # Floor at 1.0x
            
            risk_amount = base_risk * confidence_multiplier
            
            # DEBUG: Log risk calculation
            self.logger.info(f"DEBUG {signal.symbol}: confidence={confidence_factor:.3f}, tier={signal_tier}, multiplier={confidence_multiplier:.2f}x, risk=${risk_amount:.2f}")
            
            # Position size based on stop distance
            stop_distance = entry_price - stop_price
            raw_shares = risk_amount / stop_distance
            shares = math.floor(raw_shares) if raw_shares >= 1.0 else raw_shares  # Allow fractional for <1 share
            position_value = shares * entry_price
            
            # DEBUG: Log position calculation
            self.logger.info(f"DEBUG {signal.symbol}: stop_dist=${stop_distance:.2f}, raw_shares={raw_shares:.2f}, shares={shares:.4f}, value=${position_value:.2f}")
            
            # Apply position size constraints
            # Handle both SmallPortfolioConfig (uses max_position_dollars) and ShortCycleConfig (uses max_position_size_percent)
            if hasattr(self.config, 'max_position_dollars'):
                # Small portfolio: use fixed dollar max
                max_position_value = self.config.max_position_dollars
            else:
                # Regular portfolio: use percentage
                max_position_value = current_portfolio_value * self.config.max_position_size_percent
            
            min_position_value = self.config.min_position_size_dollars
            
            # DEBUG: Log constraints
            self.logger.info(f"DEBUG {signal.symbol}: max=${max_position_value:.2f}, min=${min_position_value:.2f}, current=${position_value:.2f}")
            
            if position_value > max_position_value:
                # FIX: Use fractional shares (Alpaca supports this) - don't truncate to 0
                shares = max_position_value / entry_price  # Allow fractional (e.g., 0.8 shares)
                position_value = shares * entry_price
                self.logger.info(f"DEBUG {signal.symbol}: CAPPED to max - new shares={shares:.4f}, value=${position_value:.2f}")
            
            if position_value < min_position_value:
                self.logger.warning(f"DEBUG {signal.symbol}: REJECT - Position ${position_value:.2f} < min ${min_position_value:.2f}")
                return 0, 0.0  # Position too small
            
            # Validate against daily pool
            if position_value > self.config.daily_pool_dollars:
                shares = self.config.daily_pool_dollars / entry_price  # Keep fractional
                position_value = shares * entry_price
            
            # Apply VIX regime adjustment
            vix_multiplier = self._get_vix_regime_multiplier()
            if vix_multiplier < 1.0:
                shares = shares * vix_multiplier  # Keep fractional
                position_value = shares * entry_price
                self.logger.info(f"{signal.symbol}: VIX adjustment applied (multiplier={vix_multiplier:.2f})")
            
            self.logger.info(
                f"{signal.symbol}: 📊 Dynamic Sizing - Confidence={confidence_factor:.2f} ({signal_tier}), "
                f"Multiplier={confidence_multiplier:.2f}x, Risk=${risk_amount:.0f}, "
                f"Size={shares} shares (${position_value:.0f}), VIX={vix_multiplier:.2f}"
            )
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
    
    def _scan_morning_gaps(self) -> List[Dict]:
        """
        Scan for quality premarket gaps at 9:00 AM using fresh data.
        Returns list of gap candidates with fresh real-time data.
        """
        try:
            # Get base universe
            universe = self._get_trading_universe()
            
            # Use morning gap scanner for fresh 9 AM data
            gap_results = self.morning_gap_scanner.scan_premarket_gaps(universe)
            
            if not gap_results:
                self.logger.warning("⚠️ No premarket gaps found")
                return []
            
            # Filter to tradeable gaps only
            tradeable_gaps = self.morning_gap_scanner.filter_tradeable_gaps(
                gap_results,
                min_gap_pct=0.01,  # 1% minimum
                max_gap_pct=0.05,  # 5% maximum
                prefer_direction='up',  # Prefer gap ups
                max_results=8  # Top 8 candidates
            )
            
            if tradeable_gaps:
                self.logger.info(f"✨ {len(tradeable_gaps)} quality gaps identified:")
                for gap in tradeable_gaps[:5]:  # Log top 5
                    self.logger.info(
                        f"   • {gap['symbol']}: {gap['gap_pct']:+.2%} gap "
                        f"(${gap['prev_close']:.2f} → ${gap['current_price']:.2f}) "
                        f"Quality: {gap['quality']}, Score: {gap['score']}"
                    )
            
            return tradeable_gaps
            
        except Exception as e:
            self.logger.error(f"Morning gap scan error: {e}")
            return []
    
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
        
        # 🆕 PHASE 1: Friday cleanup on startup (if restarted after 3:45 PM)
        # Force exit any Friday same-day positions to prevent weekend holding
        startup_check_done = False
        
        while True:
            try:
                now = datetime.utcnow().replace(tzinfo=UTC)
                weekday = now.astimezone(ET).weekday()  # 0=Mon, 4=Fri
                is_open = market_hours.is_regular_session_now(now)
                sess = market_hours.rth_session_for_date(now)
                next_open = sess.open_utc
                next_close = sess.close_utc
                
                # Friday startup cleanup (run once on first loop iteration)
                if not startup_check_done and weekday == 4:  # Friday
                    now_et = now.astimezone(ET)
                    if now_et.hour >= 15 and now_et.minute >= 45:  # After 3:45 PM
                        logger.info("🧹 Friday startup cleanup: checking for same-day positions after 3:45 PM")
                        today = dt.date.today()
                        friday_exits = 0
                        
                        for position in self.positions:
                            if position.status == PositionStatus.ENTERED and position.entry_date >= today:
                                # Get current price and force exit
                                current_price = self._get_current_price(position.symbol)
                                if current_price:
                                    logger.info(f"⚠️ Friday cleanup: Force exiting {position.symbol} (entered today, after 3:45 PM)")
                                    self._exit_position(position, current_price, "FRIDAY_STARTUP_CLEANUP")
                                    friday_exits += 1
                        
                        if friday_exits > 0:
                            logger.info(f"✅ Friday cleanup: Exited {friday_exits} position(s)")
                            self._save_positions()
                
                startup_check_done = True

                # --- Post-market selection (immediately after close) ---
                if now > next_close and (now - next_close).total_seconds() < 3600:  # Within 1 hour of close
                    logger.info("🌙 Post-market: running watchlist refresh ONLY (NO TRADES)")
                    
                    # Run end-of-day self-monitoring
                    self._run_end_of_day_monitoring()
                    
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
                    logger.info("📊 09:00 ET Premarket: Portfolio summary & fresh gap scan (NO ORDERS)")
                    # Run analysis without placing orders - portfolio summary and watchlist prep
                    try:
                        self._generate_portfolio_summary()
                        
                        # ✨ NEW: Run morning gap scanner for fresh 9 AM data
                        logger.info("🔍 Scanning for fresh premarket gaps...")
                        gap_candidates = self._scan_morning_gaps()
                        if gap_candidates:
                            logger.info(f"✅ Found {len(gap_candidates)} fresh gap candidates")
                            # Store for entry window
                            self.morning_gap_candidates = gap_candidates
                        else:
                            logger.warning("⚠️ No quality gaps found, will use standard watchlist")
                            self.morning_gap_candidates = []
                        
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

                # --- Opening 15 min: allow new entries (except Friday unless emergency trades available) - 15 min after market opens ---
                if is_open:
                    open_et = next_open.astimezone(ET)
                    now_et = now.astimezone(ET)
                    minutes_since_open = (now_et - open_et).total_seconds() / 60
                    # Wait 15 minutes after market open before placing orders
                    if 15 <= minutes_since_open < 30:
                        if weekday == 4:
                            # Friday: check if emergency day trades available
                            emergency_remaining = self.day_trade_tracker.trades_remaining() if self.day_trade_tracker else 0
                            if emergency_remaining > 0:
                                logger.info(f"⚠️ Friday emergency mode: {emergency_remaining} day trades available - running entry logic")
                                self.run_daily_cycle()
                            else:
                                logger.info("🛑 Friday: entry freeze (no emergency day trades remaining)")
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

                    # --- Intraday: monitor for exits, risk, and late entry opportunities ---
                    logger.info("🔄 Intraday: monitoring positions for exits and risk...")
                    
                    # PDT COMPLIANCE: NO same-day exits for margin accounts
                    # Positions MUST be held overnight (D+1 minimum) to avoid PDT violations
                    # Force exit disabled - positions exit on D+1, D+2, or D+3 based on smart zones
                    # Emergency exits only: stop loss hit, major risk events
                    
                    # Normal position monitoring (only strategic D+1+ exits, no intraday closes)
                    self._process_existing_positions()
                    
                    # Check for late-entry opportunities if enabled and conditions met
                    if getattr(self.config, 'enable_all_day_entries', False):
                        open_et = next_open.astimezone(ET)
                        now_et = now.astimezone(ET)
                        minutes_since_open = (now_et - open_et).total_seconds() / 60
                        
                        # Get cutoff time
                        cutoff_str = getattr(self.config, 'all_day_entry_cutoff_time', '15:30')
                        cutoff_hour, cutoff_min = map(int, cutoff_str.split(':'))
                        cutoff_et = open_et.replace(hour=cutoff_hour, minute=cutoff_min, second=0, microsecond=0)
                        
                        # Get minimum minutes and check interval
                        min_minutes = getattr(self.config, 'allow_late_entries_after_minutes', 60)
                        check_interval = getattr(self.config, 'late_entry_check_interval_minutes', 15)
                        
                        # 🆕 SMART CONDITIONAL REFRESH at 10:30 AM (60 min after open)
                        if 58 <= minutes_since_open <= 62 and not getattr(self, '_watchlist_refreshed_today', False):
                            self._smart_conditional_watchlist_refresh()
                            self._watchlist_refreshed_today = True  # Only refresh once per day
                        
                        # Check if we're in late-entry window and on check interval
                        if (minutes_since_open >= min_minutes and 
                            now_et < cutoff_et and
                            int(minutes_since_open) % check_interval < 5):  # Check every interval
                            logger.info(f"🔍 Late entry window active ({minutes_since_open:.0f} min since open, cutoff: {cutoff_str})")
                            self._attempt_late_entries()
                    
                    # Sleep until close or next check
                    # PHASE 1: On Fridays, wake up at 3:45 PM for force exit
                    sleep_sec = min(300, market_hours.seconds_until_close(now))
                    
                    if weekday == 4:  # Friday
                        now_et = now.astimezone(ET)
                        # Calculate seconds until 3:45 PM ET
                        friday_exit_time = now_et.replace(hour=15, minute=45, second=0, microsecond=0)
                        if now_et < friday_exit_time:
                            seconds_until_friday_exit = (friday_exit_time - now_et).total_seconds()
                            if seconds_until_friday_exit > 0 and seconds_until_friday_exit < sleep_sec:
                                sleep_sec = max(60, seconds_until_friday_exit)
                                logger.info(f"⏳ Friday: sleeping {sleep_sec/60:.1f} min until 3:45 PM force exit check")
                    
                    if sleep_sec >= 300 or weekday != 4:  # Normal logging for non-Friday or long sleeps
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
    
    def __init__(self, config: ShortCycleConfig = None, launch_gui: bool = False, enable_intraday_analysis: bool = False, max_intraday_analyses_per_day: int = 0):
        self.config = config or ShortCycleConfig()
        self.logger = self._setup_logging()
        self.launch_gui = launch_gui
        
        # Initialize AI components
        self.signal_generator = AISignalGenerator(self.config, price_fetcher=self._get_current_price)
        self.stop_manager = AIStopLossManager(self.config)
        self.position_sizer = AIConfidencePositionSizer(self.config)
        self.risk_manager = AIPredictiveRiskManager(self.config)
        self.regime_detector = AIMarketRegimeDetector(self.config)
        
        # Initialize pattern recognition and morning scanner
        self.pattern_recognizer = PatternRecognizer()
        self.pattern_tracker = PatternTracker()
        self.morning_gap_scanner = MorningGapScanner()
        self.logger.info("🧠 Pattern recognition and morning gap scanner initialized")
        
        # Initialize earnings calendar (NEW: Earnings protection)
        self.earnings_calendar = EarningsCalendar(entry_blackout_days=3, exit_buffer_days=1)
        self.logger.info("📅 Earnings calendar initialized (3-day entry blackout, 1-day exit buffer)")
        
        # Trading state
        self.positions: List[ShortCyclePosition] = []
        self.daily_pnl = 0.0
        self.daily_realized_pnl = 0.0  # Realized P&L from exits today
        self.daily_unrealized_pnl = 0.0  # Unrealized P&L from open positions
        self.weekly_pnl = 0.0
        self.trades_today = 0
        self.late_entries_today = 0  # Track late entries separately for all-day trading
        self._signals_found_today = 0  # Track total signals for smart watchlist refresh
        self._watchlist_refreshed_today = False  # Track if we've done mid-morning refresh
        self.current_universe = []  # Track current trading universe
        self.recent_trades: List[Any] = []  # simple buffer of recent trade outcomes for safety
        # Day trade tracker: enforce 3 day trades per rolling 5-business-day window
        try:
            self.day_trade_tracker = DayTradeTracker()
        except Exception:
            self.day_trade_tracker = None
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
        self.enable_intraday_analysis = enable_intraday_analysis
        self.max_intraday_analyses_per_day = max_intraday_analyses_per_day
        
        # Kill switches
        self.kill_switches = {
            "daily_loss_exceeded": False,
            "weekly_loss_exceeded": False,
            "system_error": False
        }

        # Safety monitor (reinstated)
        try:
            # Use portfolio_size (correct attribute name) instead of portfolio_value
            portfolio_val = getattr(self.config, 'portfolio_value', None) or getattr(self.config, 'portfolio_size', 100000)
            self.safety_monitor = SafetyMonitor(SafetyConfig(), portfolio_val)
            self.logger.info(f"🛡️ Safety monitor active (portfolio: ${portfolio_val:,.0f})")
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
        
        # Self-monitoring system
        try:
            self.monitoring_system = SelfMonitoringSystem()
            self.logger.info("🤖 Self-monitoring system enabled")
        except Exception as e:
            self.logger.warning(f"Self-monitoring unavailable: {e}")
            self.monitoring_system = None
            
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
    
    def _smart_conditional_watchlist_refresh(self):
        """
        Smart conditional watchlist refresh at 10:30 AM
        Only refreshes if:
        1. No signals found today AND
        2. (Universe size < 8 OR No trades executed today)
        
        This saves API calls on active days, helps on slow market days
        """
        self.logger.info("🔍 Evaluating need for mid-morning watchlist refresh...")
        
        # Get current stats
        signals_today = getattr(self, '_signals_found_today', 0)
        universe_size = len(getattr(self, 'current_universe', []))
        trades_today = self.trades_today
        
        # Decision logic
        should_refresh = False
        reason = ""
        
        if signals_today == 0:
            if universe_size < 8:
                should_refresh = True
                reason = f"No signals + small universe ({universe_size} stocks)"
            elif trades_today == 0:
                should_refresh = True
                reason = f"No signals + no trades executed (universe: {universe_size})"
        
        if should_refresh:
            self.logger.info(f"🔄 SMART REFRESH TRIGGERED: {reason}")
            self.logger.info("   Scanning for fresh intraday momentum...")
            
            try:
                # Run the daily watchlist refresh script
                import subprocess
                import sys
                result = subprocess.run(
                    [sys.executable, 'daily_watchlist_refresh.py'],
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                
                if result.returncode == 0:
                    self.logger.info("✅ Watchlist refreshed with fresh candidates")
                    # Reload universe with new watchlist
                    self.current_universe = self._get_trading_universe()
                    self.logger.info(f"   New universe size: {len(self.current_universe)} stocks")
                else:
                    self.logger.warning(f"⚠️ Watchlist refresh had issues: {result.stderr[:200]}")
            except subprocess.TimeoutExpired:
                self.logger.error("❌ Watchlist refresh timed out")
            except Exception as e:
                self.logger.error(f"❌ Error refreshing watchlist: {e}")
        else:
            reason = "Signals found OR sufficient universe OR already trading"
            self.logger.info(f"✅ Smart refresh check: No refresh needed ({reason})")
            self.logger.info(f"   Stats: {signals_today} signals, {universe_size} stocks, {trades_today} trades")
    
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
    
    def _check_macro_regime(self) -> bool:
        """Check macro market conditions - return False to stop trading today"""
        try:
            import yfinance as yf
            
            # Check SPY 20-day trend
            spy = yf.Ticker('SPY').history(period='25d')
            if len(spy) < 20:
                self.logger.warning("⚠️ Insufficient SPY data - proceeding with caution")
                return True
            
            spy_trend = (spy['Close'].iloc[-1] - spy['Close'].iloc[0]) / spy['Close'].iloc[0]
            
            if spy_trend < -0.05:
                self.logger.error(f"🚨 MARKET CRASH DETECTED: SPY down {spy_trend:.1%} in 20 days - STOP TRADING TODAY")
                return False
            elif spy_trend < -0.03:
                self.logger.warning(f"⚠️ MARKET WEAKNESS: SPY down {spy_trend:.1%} - Reducing position sizes by 50%")
                # Store regime multiplier for position sizing
                if not hasattr(self, '_macro_regime_multiplier'):
                    self._macro_regime_multiplier = 0.5
            else:
                self.logger.info(f"✅ MARKET HEALTHY: SPY 20-day trend {spy_trend:+.1%}")
                if not hasattr(self, '_macro_regime_multiplier'):
                    self._macro_regime_multiplier = 1.0
            
            # Check VIX for extreme fear (double-check beyond position sizing)
            vix = yf.Ticker("^VIX").history(period='1d')['Close'].iloc[-1]
            if vix > 35:
                self.logger.error(f"🚨 EXTREME PANIC: VIX={vix:.1f} - STOP TRADING TODAY")
                return False
            elif vix > 30:
                self.logger.warning(f"⚠️ HIGH FEAR: VIX={vix:.1f} - Position sizing already reduced by VIX multiplier")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Macro regime check failed: {e} - Proceeding with caution")
            return True  # Fail-safe: allow trading if check fails
    
    def _check_morning_gaps(self):
        """
        Check open positions for large gaps at market open (9:30-9:45 AM only).
        Auto-exit gap downs >= -3% (limit damage) and gap ups >= +5% (take profits).
        
        This prevents:
        - Disaster gaps from holding overnight positions
        - Giving back profits on surprise gap ups
        
        Returns:
            int: Number of positions exited due to gaps
        """
        import pytz
        current_time = dt.datetime.now(pytz.timezone('US/Eastern'))
        
        # Only run during market open window (9:30-9:45 AM ET)
        market_open = current_time.replace(hour=9, minute=30, second=0, microsecond=0)
        gap_window_end = current_time.replace(hour=9, minute=45, second=0, microsecond=0)
        
        if current_time < market_open or current_time > gap_window_end:
            return 0  # Outside gap detection window
        
        gap_exits = 0
        today = dt.date.today()
        
        # Get live portfolio positions
        live_positions = self._get_live_portfolio_positions()
        
        for position in self.positions:
            if position.status != PositionStatus.ENTERED:
                continue
            
            # Skip same-day entries (PDT protection)
            if position.entry_date == today:
                continue
            
            # Get live position data
            live_data = live_positions.get(position.symbol.upper())
            if not live_data or abs(live_data.get("quantity", 0)) <= 1e-6:
                continue
            
            # Calculate current price
            actual_qty = abs(live_data.get("quantity", 0))
            market_value = live_data.get("market_value")
            if not market_value or actual_qty == 0:
                continue
            
            current_price = float(market_value) / actual_qty
            
            # Calculate gap from entry
            gap_pct = (current_price - position.entry_price) / position.entry_price
            
            # Check for gap down >= -3% (LIMIT DAMAGE)
            if gap_pct <= -0.03:
                self.logger.warning(
                    f"🚨 {position.symbol}: GAP DOWN {gap_pct:.1%} (${position.entry_price:.2f} → ${current_price:.2f}) - AUTO EXIT"
                )
                self._exit_position(position, current_price, f"GAP_DOWN_{gap_pct:.1%}")
                gap_exits += 1
                continue
            
            # Check for gap up >= +5% (TAKE PROFITS)
            if gap_pct >= 0.05:
                self.logger.warning(
                    f"💰 {position.symbol}: GAP UP {gap_pct:.1%} (${position.entry_price:.2f} → ${current_price:.2f}) - AUTO PROFIT"
                )
                self._exit_position(position, current_price, f"GAP_UP_{gap_pct:.1%}")
                gap_exits += 1
                continue
        
        if gap_exits > 0:
            self.logger.info(f"🎯 Morning gap exits: {gap_exits} positions")
            self._save_positions()  # Save after gap exits
        
        return gap_exits
    
    def run_daily_cycle(self):
        """Execute daily short-cycle trading logic"""
        self.logger.info("🚀 Starting daily short-cycle trading cycle")
        
        try:
            # Reset daily counters if starting a new trading day
            self._maybe_reset_daily_counters()
            
            # NEW: Check macro regime before trading
            if not self._check_macro_regime():
                self.logger.warning("⚠️ MACRO REGIME CHECK FAILED - Skipping trading today for safety")
                return
            
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
            
            # NEW: Check morning gaps (9:30-9:45 AM window only)
            gap_exits = self._check_morning_gaps()
            if gap_exits > 0:
                self.logger.info(f"✅ Morning gap risk management: {gap_exits} positions auto-exited")
            
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
        # Use timezone-aware datetime to match Alpaca timestamps
        import pytz
        current_time = dt.datetime.now(pytz.UTC)
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
            
            # PDT PROTECTION: Do NOT exit same-day positions EXCEPT for Friday force exit
            # Check if Friday 3:45 PM force exit applies (prevent weekend holding)
            is_friday_force_exit_time = (current_time.weekday() == 4 and 
                                         current_time.hour >= 15 and 
                                         current_time.minute >= 45)
            
            # Allow same-day exits ONLY for Friday force exit or emergency stops
            if position.entry_date >= today and not is_friday_force_exit_time:
                self.logger.debug(
                    f"🚫 PDT Protection: Skipping {position.symbol} - entered today ({position.entry_date}), "
                    f"exit not allowed until tomorrow to avoid PDT violation"
                )
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
                
                # IMPROVEMENT #3: Trailing stop for winners (let winners run!)
                pnl_pct = (current_price - position.entry_price) / position.entry_price
                
                # Initialize trailing stop when position is up 2%+
                if pnl_pct >= 0.02:  # 2% profit
                    if not hasattr(position, 'trailing_stop_price'):
                        # Activate trailing stop at 1% below current price
                        position.trailing_stop_price = current_price * 0.99
                        position.highest_price_since_entry = current_price
                        self.logger.info(
                            f"🎯 {position.symbol}: Trailing stop activated @ ${position.trailing_stop_price:.2f} "
                            f"(up {pnl_pct:.1%})"
                        )
                    else:
                        # Update trailing stop if new high reached
                        if current_price > position.highest_price_since_entry:
                            position.highest_price_since_entry = current_price
                            new_trailing = current_price * 0.99  # Trail by 1%
                            if new_trailing > position.trailing_stop_price:
                                position.trailing_stop_price = new_trailing
                                self.logger.info(
                                    f"📈 {position.symbol}: Trailing stop raised to ${position.trailing_stop_price:.2f} "
                                    f"(up {pnl_pct:.1%})"
                                )
                        
                        # Check if trailing stop hit
                        if current_price <= position.trailing_stop_price:
                            self.logger.info(
                                f"🎯 {position.symbol}: Trailing stop hit @ ${current_price:.2f}, "
                                f"locking in profit of {pnl_pct:.1%}"
                            )
                            self._exit_position(position, current_price, "TRAILING_STOP_PROFIT")
                            other_exits_processed += 1
                            continue
                
                # ✨ NEW: Update pattern recognition for dynamic exit timing
                if hasattr(position, 'entry_timestamp') and position.entry_timestamp:
                    minutes_held = (current_time - position.entry_timestamp).total_seconds() / 60
                    
                    # Get gap at open if available
                    gap_at_open = None
                    if hasattr(position, 'gap_at_open'):
                        gap_at_open = position.gap_at_open
                    
                    # Get price history if available
                    price_history = None
                    if hasattr(position, 'price_history'):
                        price_history = position.price_history
                    
                    # Update pattern
                    pattern = self.pattern_tracker.update_position_pattern(
                        symbol=position.symbol,
                        current_price=current_price,
                        entry_price=position.entry_price,
                        gap_at_open=gap_at_open,
                        minutes_held=int(minutes_held)
                    )
                    
                    # 🚀 NEW NOV 12: Peak detection for MOMENTUM_RUNNER patterns
                    if pattern == StockPattern.MOMENTUM_RUNNER and price_history and len(price_history) >= 5:
                        peak_detected, peak_reason = self.pattern_recognizer.detect_peak(
                            price_history=price_history,
                            current_price=current_price,
                            entry_price=position.entry_price
                        )
                        
                        if peak_detected and pnl_pct > 0.005:  # Profitable (>0.5%)
                            self.logger.info(
                                f"🏔️ {position.symbol} PEAK DETECTED: {peak_reason} "
                                f"(P&L: {pnl_pct:.1%}, held {minutes_held:.0f}min)"
                            )
                            self._exit_position(position, current_price, f"PEAK_{peak_reason}")
                            other_exits_processed += 1
                            continue
                    
                    # Check if it's optimal exit time for this pattern
                    should_exit, pattern_reason = self.pattern_recognizer.get_optimal_exit_time(
                        pattern=pattern,
                        current_time=current_time,
                        pnl_pct=pnl_pct
                    )
                    
                    if should_exit:
                        pattern_desc = self.pattern_recognizer.get_pattern_description(pattern)
                        self.logger.info(
                            f"🎯 {position.symbol} PATTERN EXIT: {pattern.value} "
                            f"({pattern_desc}) - {pattern_reason}"
                        )
                        self._exit_position(position, current_price, f"PATTERN_{pattern_reason}")
                        other_exits_processed += 1
                        continue
                
                # Update trailing stop if enabled (NEW)
                if self.config.enable_trailing_stops:
                    trailing_exit = self._update_and_check_trailing_stop(position, current_price)
                    if trailing_exit:
                        exit_price, exit_reason = trailing_exit
                        self._exit_position(position, exit_price, exit_reason)
                        other_exits_processed += 1
                        continue
                
                # Check for smart exit (but not D+1 as that's handled in Phase 1)
                cash_mode = getattr(self.config, 'cash_account_mode', False)
                
                # Fetch recent market data for RSI calculation (need 7+ bars)
                market_data = None
                try:
                    market_data = self.data_loader.get_historical_data(position.symbol, days=10)
                except Exception as e:
                    self.logger.debug(f"Could not fetch market data for {position.symbol}: {e}")
                
                should_exit, exit_reason = position.should_smart_exit(today, current_price, current_time, cash_account_mode=cash_mode, market_data=market_data)
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
        import pytz
        
        positions_to_exit = []
        today = dt.date.today()
        current_time = dt.datetime.now(pytz.UTC)
        
        # First pass: identify positions that need D+1 exit
        for position in self.positions:
            if position.status != PositionStatus.ENTERED:
                continue
            
            # CRITICAL: Earnings Protection - Force exit before earnings
            if self.earnings_calendar.should_exit_before_earnings(position.symbol):
                earnings_info = self.earnings_calendar.get_earnings_info(position.symbol)
                positions_to_exit.append({
                    'position': position,
                    'priority': 'EARNINGS_URGENT',
                    'entry_date': position.entry_date,
                    'target_exit': today,  # Exit today!
                    'days_held': (today - position.entry_date).days,
                    'reason': f"Earnings protection: {earnings_info['status']}"
                })
                self.logger.warning(f"⚠️ {position.symbol}: EARNINGS EXIT - {earnings_info['status']}")
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
        self.logger.info(f"🚀 Strategic exit sequence: {len(positions_to_exit)} positions")
        
        # Sort by priority: EARNINGS_URGENT first, then oldest positions
        positions_to_exit.sort(key=lambda x: (
            0 if x['priority'] == 'EARNINGS_URGENT' else 1,  # Earnings exits first!
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
                
                # Execute the exit using zone-based strategy
                self.logger.info(f"🎯 Evaluating D+1 exit {i+1}/{len(positions_to_exit)}: {position.symbol}")
                success = self._execute_strategic_position_exit(position, i+1)
                
                if success:
                    exit_count += 1
                    self.logger.info(f"✅ {position.symbol}: D+1 exit completed ({exit_count}/{len(positions_to_exit)})")
                else:
                    self.logger.warning(f"⚠️ {position.symbol}: D+1 exit failed, will retry")
                    
            except Exception as e:
                self.logger.error(f"❌ {position.symbol}: D+1 exit error: {e}")
        
        self.logger.info(f"🎉 Strategic D+1 exit sequence complete: {exit_count}/{len(positions_to_exit)} successful")
        return exit_count
    
    def _execute_strategic_position_exit(self, position: ShortCyclePosition, exit_sequence_num: int):
        """Execute a single position exit using smart zone-based strategy"""
        try:
            today = dt.date.today()
            current_time = dt.datetime.now(pytz.UTC)
            
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
            
            # Calculate P&L for logging
            unrealized_pnl = (current_price - position.entry_price) * position.position_size_shares
            unrealized_pnl_pct = ((current_price - position.entry_price) / position.entry_price) * 100
            
            # NEW OCT 29 2025: Check trailing stop for profit protection (>3% gains)
            trailing_stop_hit, trailing_reason = position.update_trailing_stop(current_price, logger=self.logger)
            if trailing_stop_hit:
                self.logger.info(f"🛑 {position.symbol}: Trailing stop triggered - {position.position_size_shares} shares @ ${current_price:.2f}")
                self.logger.info(f"💰 {position.symbol}: P&L: ${unrealized_pnl:.2f} ({unrealized_pnl_pct:+.2f}%) | Reason: {trailing_reason}")
                self._exit_position(position, current_price, trailing_reason)
                return True
            
            # CRITICAL FIX: Use should_smart_exit() to determine optimal exit timing
            # This ensures D+1 positions follow the mean reversion RSI strategy
            cash_mode = getattr(self.config, 'cash_account_mode', False)
            
            # Fetch recent market data for RSI calculation (need 7+ bars)
            market_data = None
            try:
                market_data = self.data_loader.get_historical_data(position.symbol, days=10)
            except Exception as e:
                self.logger.debug(f"Could not fetch market data for {position.symbol}: {e}")
            
            should_exit, zone_exit_reason = position.should_smart_exit(today, current_price, current_time, cash_account_mode=cash_mode, market_data=market_data)
            
            if should_exit:
                # Exit using the zone-determined reason (ZONE1_MORNING_PROFIT, etc.)
                self.logger.info(f"📤 {position.symbol}: Smart exit triggered - {position.position_size_shares} shares @ ${current_price:.2f}")
                self.logger.info(f"💰 {position.symbol}: P&L: ${unrealized_pnl:.2f} ({unrealized_pnl_pct:+.2f}%) | Zone: {zone_exit_reason}")
                
                # Use the zone-based exit reason instead of generic sequence number
                self._exit_position(position, current_price, zone_exit_reason)
                return True
            else:
                # Should not exit yet per zone logic - skip for now
                self.logger.info(f"⏳ {position.symbol}: Zone strategy says hold (P&L: ${unrealized_pnl:.2f}, {unrealized_pnl_pct:+.2f}%)")
                return False
                
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
            
            # Pass active positions for PDT validation
            signals = self.signal_generator.generate_signals(universe, market_data, self.positions)
            
            # Track signals for smart watchlist refresh
            self._signals_found_today += len(signals)
            self.current_universe = universe  # Track current universe
            
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
                
                # Dynamic position limits by day of week (Priority 4 - Nov 19)
                max_positions_today, max_portfolio_pct = self.get_max_positions_for_day()
                
                if self.trades_today >= max_positions_today:
                    current_day_name = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"][dt.datetime.now(pytz.UTC).weekday()]
                    self.logger.info(f"📊 {current_day_name}: Position limit reached ({self.trades_today}/{max_positions_today})")
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
            # CRITICAL: Market Hours Check - Block orders outside 9:30 AM - 4:00 PM ET (Nov 17 fix)
            from utils import market_hours
            now = dt.datetime.now(pytz.UTC)
            
            if not market_hours.is_regular_session_now(now):
                current_time_et = market_hours.to_et(now)
                self.logger.warning(
                    f"🚫 {signal.symbol}: BLOCKED - Market closed (current time: {current_time_et.strftime('%H:%M:%S ET')})"
                )
                self.logger.info(f"   Regular market hours: 9:30 AM - 4:00 PM ET")
                return
            
            # CRITICAL: Duplicate Position Check - Block if ANY position exists today (Nov 17 fix)
            # Prevents: Entry #1 → Exit (PORTFOLIO_MISMATCH) → Entry #2 (11 min later)
            today = dt.date.today()
            same_day_positions = [
                p for p in self.positions 
                if p.symbol == signal.symbol and p.entry_date == today
            ]
            
            if same_day_positions:
                active_count = sum(1 for p in same_day_positions if p.status in [PositionStatus.ENTERED, PositionStatus.PENDING])
                exited_count = len(same_day_positions) - active_count
                
                self.logger.warning(
                    f"🚫 {signal.symbol}: BLOCKED - Duplicate position prevention "
                    f"({active_count} active, {exited_count} exited today)"
                )
                return
            
            # CRITICAL: Earnings Protection - Block entries before earnings
            if self.earnings_calendar.should_avoid_entry(signal.symbol):
                earnings_info = self.earnings_calendar.get_earnings_info(signal.symbol)
                self.logger.warning(f"❌ {signal.symbol}: BLOCKED - {earnings_info['status']}")
                return
            
            # CRITICAL: PDT Protection - Block same-day activity
            if self._has_same_day_activity(signal.symbol):
                self.logger.warning(f"❌ {signal.symbol}: BLOCKED - Same-day activity detected (PDT protection)")
                return
            
            # CRITICAL: Daily Capital Limit Check - Prevent over-deployment (Nov 17 fix)
            # Dynamic portfolio percentage based on day of week (Priority 4 - Nov 19)
            current_portfolio_value = self._get_portfolio_value()
            active_positions = [p for p in self.positions if p.status in [PositionStatus.ENTERED, PositionStatus.PENDING]]
            total_deployed = sum(p.position_size_dollars for p in active_positions)
            
            # Get dynamic limit for today
            _, max_portfolio_pct = self.get_max_positions_for_day()
            daily_capital_limit = current_portfolio_value * max_portfolio_pct
            deployed_percent = (total_deployed / current_portfolio_value) * 100 if current_portfolio_value > 0 else 0
            
            # Estimate new position size (conservative estimate before exact calculation)
            estimated_position_size = min(
                self.config.max_position_dollars,
                current_portfolio_value * 0.15  # Rough 15% estimate
            )
            
            if total_deployed + estimated_position_size > daily_capital_limit:
                current_day_name = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"][dt.datetime.now(pytz.UTC).weekday()]
                self.logger.warning(
                    f"🚫 {signal.symbol}: BLOCKED - Daily capital limit reached"
                )
                self.logger.info(
                    f"   {current_day_name}: Portfolio: ${current_portfolio_value:.2f}, Daily limit: {max_portfolio_pct*100:.0f}% (${daily_capital_limit:.2f})"
                )
                self.logger.info(
                    f"   Currently deployed: ${total_deployed:.2f} ({deployed_percent:.1f}%), "
                    f"Available: ${daily_capital_limit - total_deployed:.2f}"
                )
                self.logger.info(
                    f"   Estimated new position: ${estimated_position_size:.2f} (would exceed limit)"
                )
                return
            
            # Calculate stop price
            stop_price, stop_pct = self.stop_manager.calculate_optimal_stop(signal, symbol_data)
            
            # Calculate position size (current_portfolio_value already calculated above in capital limit check)
            shares, position_value = self.position_sizer.calculate_position_size(
                signal, stop_price, current_portfolio_value
            )
            
            # CRITICAL: Validate shares is not None or 0
            if shares is None:
                self.logger.error(f"❌ {signal.symbol}: REJECTED - Position sizer returned None shares!")
                self.logger.error(f"   Signal confidence: {signal.confidence:.1%}, Stop price: ${stop_price:.2f}")
                return
            
            if shares == 0:
                self.logger.info(f"❌ {signal.symbol}: REJECTED - Position size too small (0 shares)")
                self.logger.info(f"   Signal confidence: {signal.confidence:.1%}, Portfolio: ${current_portfolio_value:.2f}")
                self.logger.info(f"   Stop: ${stop_price:.2f} ({stop_pct:.1%}), Min position: ${self.config.min_position_size_dollars}")
                return
            
            # Ensure shares is an integer
            shares = int(shares)
            if shares <= 0:
                self.logger.error(f"❌ {signal.symbol}: Invalid shares count: {shares}")
                return
            
            # Create position
            today = dt.date.today()
            exit_date = self._get_next_trading_day(today)  # D+1 exit
            
            # Get sector info for diversification tracking (NEW NOV 12)
            symbol_sector = None
            try:
                import json
                from pathlib import Path
                cache_file = Path("cache/dynamic_universe.json")
                if cache_file.exists():
                    with open(cache_file) as f:
                        universe_data = json.load(f)
                        for stock in universe_data.get('candidates', []):
                            if stock['symbol'] == signal.symbol:
                                symbol_sector = stock.get('sector', 'Unknown')
                                break
            except Exception as e:
                self.logger.debug(f"Could not load sector for {signal.symbol}: {e}")
            
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
                max_risk_dollars=self.config.max_risk_per_trade_dollars,
                sector=symbol_sector  # NEW NOV 12: Track sector
            )
            
            # ✨ NEW: Track gap at open for pattern recognition
            if hasattr(self, 'morning_gap_candidates') and self.morning_gap_candidates:
                for gap_data in self.morning_gap_candidates:
                    if gap_data['symbol'] == signal.symbol:
                        position.gap_at_open = gap_data['gap_pct']
                        self.logger.info(f"📊 {signal.symbol}: Tracking {gap_data['gap_pct']:+.2%} gap for pattern recognition")
                        break
            
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
    
    def _check_sector_concentration(self, symbol: str, sector: str) -> Tuple[bool, str]:
        """
        Smart sector concentration check with dynamic limits.
        
        NEW NOV 12 2025: Allows more positions in HOT sectors, limits in COLD sectors.
        
        Sector Rules:
        - HOT sectors (high volume, strong momentum): Allow up to 3 positions
        - Normal sectors (moderate activity): Max 2 positions  
        - Cold sectors (low activity): Max 1 position
        
        Args:
            symbol: Stock symbol to check
            sector: Sector classification (Energy, Tech, etc.)
            
        Returns:
            Tuple of (allowed: bool, reason: str)
        """
        try:
            if not sector or sector == "Unknown":
                # No sector info - allow (don't block on missing data)
                return True, "NO_SECTOR_DATA"
            
            # Count positions in this sector
            sector_positions = [p for p in self.positions 
                               if p.status == PositionStatus.ENTERED 
                               and hasattr(p, 'sector') 
                               and p.sector == sector]
            sector_count = len(sector_positions)
            
            # Calculate sector metrics (for dynamic limits)
            # In real implementation, this would query market data
            # For now, use simplified heuristics based on our holdings
            
            # Heuristic 1: Count sector volume across positions (proxy for sector heat)
            total_active = sum(1 for p in self.positions if p.status == PositionStatus.ENTERED)
            
            # Heuristic 2: If sector is already represented, it passed our filters recently (implies activity)
            sector_is_hot = sector_count >= 1  # Simplified: If we're already in it, it's active
            
            # Determine sector limit
            if sector_is_hot and total_active >= 3:
                # HOT sector with sufficient portfolio - allow up to 3
                sector_limit = 3
                sector_temp = "HOT"
            elif total_active >= 5:
                # Normal sector with larger portfolio - allow 2
                sector_limit = 2
                sector_temp = "NORMAL"
            else:
                # Small portfolio or cold sector - conservative limit
                sector_limit = 2  # Still allow 2 for small portfolios (need positions)
                sector_temp = "NORMAL"
            
            # Check limit
            if sector_count >= sector_limit:
                reason = f"SECTOR_LIMIT_{sector_temp}_{sector_count}/{sector_limit}"
                self.logger.info(
                    f"🔄 {symbol}: Sector {sector} at limit "
                    f"({sector_count}/{sector_limit} positions, temp: {sector_temp})"
                )
                return False, reason
            
            # Log approval
            self.logger.debug(
                f"✅ {symbol}: Sector {sector} OK "
                f"({sector_count + 1}/{sector_limit}, temp: {sector_temp})"
            )
            return True, f"SECTOR_OK_{sector_count + 1}/{sector_limit}"
            
        except Exception as e:
            self.logger.error(f"Error checking sector concentration: {e}")
            # Err on side of allowing trade if check fails
            return True, "SECTOR_CHECK_ERROR"
    
    def _check_diversification_limits(self, symbol: str) -> bool:
        """
        Check if we can add another position in this symbol without exceeding diversification limits.
        
        Diversification Rules:
        1. Max positions per symbol based on portfolio size (configurable)
        2. Max concentration percentage in any single symbol (configurable)
        3. Sector concentration limits (NEW NOV 12: smart limits based on sector activity)
        4. Prefer spreading across different sectors/stocks
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
            
            # Rule 3 (NEW NOV 12): Smart sector concentration check
            # Get sector for this symbol (if available in our data)
            symbol_sector = None
            for pos in self.positions:
                if pos.symbol == symbol and hasattr(pos, 'sector'):
                    symbol_sector = pos.sector
                    break
            
            # If we don't have sector from existing positions, try to get from signal/universe
            # (In production, this would query the dynamic universe or market data)
            if not symbol_sector:
                # Simplified: Look up from dynamic universe cache if available
                try:
                    import json
                    from pathlib import Path
                    cache_file = Path("cache/dynamic_universe.json")
                    if cache_file.exists():
                        with open(cache_file) as f:
                            universe_data = json.load(f)
                            for stock in universe_data.get('candidates', []):
                                if stock['symbol'] == symbol:
                                    symbol_sector = stock.get('sector', 'Unknown')
                                    break
                except Exception:
                    pass  # Sector lookup failed - will allow trade
            
            # Check sector concentration if we have sector data
            if symbol_sector and symbol_sector != "Unknown":
                sector_allowed, sector_reason = self._check_sector_concentration(symbol, symbol_sector)
                if not sector_allowed:
                    return False  # Sector limit exceeded
            
            # Rule 4: Log diversification info
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
        PDT-COMPLIANT ENTRY LOGIC (Updated Nov 13, 2025):
        
        Allows same-day re-entry after exit, BUT enforces overnight hold on re-entry.
        
        PDT Rules Applied:
        1. ✅ ALLOW: Re-entry same day after exit (will be marked for D+1 hold)
        2. 🚫 BLOCK: Multiple ACTIVE entries same symbol same day
        3. 🚫 BLOCK: Same-day exit of same-day re-entry (enforced in exit logic)
        
        Example ALLOWED scenario:
        - 9:30 AM: Buy QBTZ Position #1
        - 11:00 AM: Sell QBTZ Position #1 (exit) ← Day trade #1
        - 2:00 PM: Buy QBTZ Position #2 ← ALLOWED (but MUST hold overnight)
        - Next day: Sell QBTZ Position #2 ← D+1 exit (no day trade)
        Total: Only 1 day trade consumed
        
        CASH ACCOUNT MODE: If cash_account_mode=True, PDT rules don't apply - allow same-day trading.
        
        Returns True if symbol should be BLOCKED from trading.
        """
        # CASH ACCOUNT MODE: No PDT restrictions, allow all same-day activity
        cash_mode = getattr(self.config, 'cash_account_mode', False)
        enable_same_day_reentry = getattr(self.config, 'enable_same_day_reentry', False)
        
        if cash_mode and enable_same_day_reentry:
            # Cash account can trade freely, no PDT blocks
            return False
        
        # MARGIN ACCOUNT MODE: PDT-compliant logic with same-day re-entry
        today = dt.date.today()
        now = dt.datetime.now(pytz.UTC)
        
        # PDT Protection Rule #1: Prevent multiple ACTIVE positions same symbol same day
        # This prevents: Buy → Buy more (same symbol, same day, both active)
        same_day_active_entries = sum(1 for p in self.positions 
                                      if p.symbol == symbol 
                                      and p.entry_date == today
                                      and p.status in [PositionStatus.ENTERED, PositionStatus.PENDING])
        
        if same_day_active_entries > 0:
            self.logger.info(
                f"🚫 PDT BLOCK: {symbol} already has {same_day_active_entries} ACTIVE position(s) entered today "
                f"(can't add more same day)"
            )
            return True
        
        # ✅ ALLOW SAME-DAY RE-ENTRY AFTER EXIT (Nov 13 Update)
        # If position was exited earlier today, we CAN re-enter (it will be marked for D+1 hold)
        # The exit logic will prevent same-day exit of the re-entry
        
        # Check if there was a same-day exit (for logging purposes only)
        same_day_exit_found = False
        for position in self.positions:
            if (position.symbol == symbol and 
                hasattr(position, 'exit_timestamp') and position.exit_timestamp and 
                position.exit_timestamp.date() == today):
                same_day_exit_found = True
                break
        
        if same_day_exit_found:
            self.logger.info(
                f"✅ {symbol}: Same-day re-entry ALLOWED after earlier exit "
                f"(will enforce D+1 hold to prevent PDT violation)"
            )
            # Return False to ALLOW re-entry (not True to block)
        
        # All checks passed - allow entry
        return False

    def get_max_positions_for_day(self, current_day: int = None, emergency_trades_remaining: int = None) -> tuple:
        """
        Get dynamic position limits based on day of week
        
        Args:
            current_day: 0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri (defaults to today)
            emergency_trades_remaining: Number of day trades left this week
        
        Returns:
            (max_positions, max_portfolio_pct)
        """
        if current_day is None:
            try:
                current_day = dt.datetime.now(pytz.UTC).weekday()
            except Exception:
                current_day = dt.datetime.now().weekday()
        
        if emergency_trades_remaining is None:
            try:
                emergency_trades_remaining = self.day_trade_tracker.trades_remaining() if self.day_trade_tracker else 0
            except Exception:
                emergency_trades_remaining = 0
        
        # Mon-Wed: Conservative 3 positions max, 30% portfolio
        if current_day in [0, 1, 2]:
            return (3, 0.30)
        
        # Thursday: Aggressive - up to 90% portfolio
        elif current_day == 3:
            return (10, 0.90)
        
        # Friday: Allow Thursday carryovers + new emergency day trades
        # PHASE 1 FIX (Nov 21): Don't limit total positions, only new entries
        elif current_day == 4:
            if emergency_trades_remaining > 0:
                # Allow unlimited existing positions + up to 3 new emergency entries
                # Return high position limit (999) to not block carryovers
                # New entries limited by emergency_trades_remaining (max 3)
                return (999, 0.90)
            else:
                # No new entries allowed, but keep existing positions
                return (999, 0.0)
        
        # Default fallback
        return (3, 0.30)

    
    def _execute_trade(self, position: ShortCyclePosition) -> bool:
        """Execute actual trade using RealPaperTradingEngine"""
        try:
            # Log the trade decision with explainability
            self._log_trade_explanation(position)
            
            # Day trade enforcement: if operating in intraday (max_hold_days==0) mode,
            # refuse entries when the week window day-trade allowance is exhausted.
            try:
                intraday_mode = getattr(self.config, 'max_hold_days', None) == 0
            except Exception:
                intraday_mode = False

            if intraday_mode and getattr(self, 'day_trade_tracker', None):
                remaining = self.day_trade_tracker.trades_remaining()
                # Special Friday logic: allow only emergency intraday entries if remaining > 0
                try:
                    now = dt.datetime.now(pytz.UTC)
                    is_friday = now.weekday() == 4
                except Exception:
                    now = dt.datetime.now()
                    is_friday = now.weekday() == 4

                if is_friday:
                    if remaining <= 0:
                        self.logger.warning(
                            f"❌ Friday: no emergency day trades remaining; skipping entry for {position.symbol}"
                        )
                        return False
                    else:
                        # Force same-day exit for Friday emergency trades
                        try:
                            position.exit_date = now.date()
                            self.logger.info(f"⚠️ Friday emergency entry allowed for {position.symbol}; forcing same-day exit")
                        except Exception:
                            pass
                else:
                    if remaining <= 0:
                        self.logger.warning(
                            f"❌ Day trade limit reached ({self.day_trade_tracker.max_trades} in rolling {self.day_trade_tracker.window_business_days}-day window). Skipping entry for {position.symbol}"
                        )
                        return False

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
                    
                    # NEW: Capture timestamps from Alpaca for accurate D+1 tracking
                    if 'order_id' in order_result:
                        position.order_id = order_result['order_id']
                    
                    if 'submitted_at' in order_result and order_result['submitted_at']:
                        position.entry_timestamp = order_result['submitted_at']
                        self.logger.info(f"   Submitted: {order_result['submitted_at']}")
                    
                    if 'filled_at' in order_result and order_result['filled_at']:
                        position.filled_at = order_result['filled_at']
                        self.logger.info(f"   Filled: {order_result['filled_at']}")

                    # Record day trade in tracker when in intraday mode
                    try:
                        if intraday_mode and getattr(self, 'day_trade_tracker', None):
                            when = position.filled_at if position.filled_at else dt.datetime.now(pytz.UTC)
                            self.day_trade_tracker.record_trade(when)
                    except Exception:
                        pass
                    
                    # CRITICAL FIX (Nov 19): Update entry_price with ACTUAL fill price from Alpaca
                    # Bug: Bot was using calculated price, not actual fill price → wrong P&L calculations
                    filled_price = order_result.get('avg_fill_price') or order_result.get('filled_price') or order_result.get('fill_price')
                    if filled_price:
                        calculated_price = position.entry_price
                        filled_price = float(filled_price)
                        
                        # Calculate slippage
                        slippage_pct = abs(filled_price - calculated_price) / calculated_price
                        
                        # Update position with FILLED price (not calculated)
                        position.entry_price = filled_price
                        
                        # Log slippage warning if significant
                        if slippage_pct > 0.02:  # >2% slippage
                            self.logger.warning(
                                f"⚠️ HIGH SLIPPAGE: {position.symbol} - "
                                f"Calculated: ${calculated_price:.2f}, "
                                f"Filled: ${filled_price:.2f} ({slippage_pct:.1%})"
                            )
                        else:
                            self.logger.info(
                                f"   Fill Price: ${filled_price:.2f} "
                                f"(calc: ${calculated_price:.2f}, slip: {slippage_pct:.2%})"
                            )
                    
                    # If no filled_at yet (pending), we'll capture it on next check
                    if not position.entry_timestamp:
                        import pytz
                        position.entry_timestamp = dt.datetime.now(pytz.UTC)
                else:
                    self.logger.error(f"❌ FAILED to submit real trade for {position.symbol}")
                    return False
            else:
                # Fallback to paper trade logging only if no execution engine
                self.logger.info(f"📝 Paper trade: {position.symbol} {position.position_size_shares} shares")
                import pytz
                position.entry_timestamp = dt.datetime.now(pytz.UTC)
            
            # Notify dashboard about executed trade
            self._notify_trade_executed(position.symbol, {
                'action': 'BUY',  # Since we're entering a position
                'quantity': position.position_size_shares,
                'price': position.entry_price,  # Now using FILLED price
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
            
            # Use default handler for non-serializable types
            with open(log_file, "a") as f:
                f.write(json.dumps(explanation, default=str) + "\n")
                
        except Exception as e:
            self.logger.error(f"Failed to save explanation log: {e}")
    
    def _attempt_late_entries(self):
        """
        Attempt to enter new positions outside the morning entry window.
        Uses stricter filters and conservative position sizing for late-day opportunities.
        Only runs if enable_all_day_entries=True in config.
        """
        # Check if all-day entries are enabled
        if not getattr(self.config, 'enable_all_day_entries', False):
            return
        
        # Check late entry limits
        max_late = getattr(self.config, 'max_late_entries_per_day', 2)
        if self.late_entries_today >= max_late:
            self.logger.info(f"⏸️ Late entry limit reached: {self.late_entries_today}/{max_late}")
            return
        
        # Check if we still have capacity for new positions
        total_capacity = self.config.max_positions_per_day
        if self.trades_today >= total_capacity:
            self.logger.info(f"⏸️ Daily position limit reached: {self.trades_today}/{total_capacity}")
            return
        
        # Safety checks: kill switches, daily loss limits
        if any(self.kill_switches.values()):
            self.logger.info("🛑 Late entry blocked: kill switch active")
            return
        
        if self.safety_monitor:
            safety = self.safety_monitor.check_safety_conditions(
                current_positions=self.positions,
                daily_pnl=self.daily_pnl,
                weekly_pnl=self.weekly_pnl,
                recent_trades=self.recent_trades,
            )
            if not safety.get("safe_to_trade", True):
                self.logger.info("🛑 Late entry blocked: safety monitor")
                return
        
        try:
            self.logger.info(f"🔍 Scanning for late-day entry opportunities (attempt {self.late_entries_today + 1}/{max_late})...")
            
            # Get trading universe with stricter filters
            universe = self._get_trading_universe()
            
            # Apply stricter volume filter for late entries
            min_volume = getattr(self.config, 'require_min_avg_volume_for_late', 1_000_000)
            universe = [s for s in universe if self._check_volume_requirement(s, min_volume)]
            
            if not universe:
                self.logger.info("⚠️ No symbols passed late-entry filters")
                return
            
            self.logger.info(f"📊 Scanning {len(universe)} stocks: {', '.join(universe[:10])}{' ...' if len(universe) > 10 else ''}")
            
            # Get market data using internal method
            market_data = self._get_market_data()
            if not market_data:
                self.logger.warning("⚠️ No market data available for late entries")
                return
            
            # Generate signals with stricter confidence requirement
            base_threshold = self.config.confidence_threshold
            late_multiplier = getattr(self.config, 'late_entry_confidence_multiplier', 1.5)
            strict_threshold = base_threshold * late_multiplier
            
            self.logger.info(f"📊 Late entry confidence threshold: {strict_threshold:.1%} (base: {base_threshold:.1%} × {late_multiplier})")
            
            # Generate signals and track confidence scores
            signals = []
            confidence_scores = []  # Track all scores for summary
            
            for symbol in universe:
                try:
                    signal = self.signal_generator.generate_signal(
                        symbol=symbol,
                        market_data=market_data[symbol],
                        current_positions=self.positions
                    )
                    
                    if signal:
                        confidence_scores.append((symbol, signal.confidence))
                        
                        if signal.confidence >= strict_threshold:
                            signals.append(signal)
                            self.logger.info(f"✅ {symbol}: Late entry signal (confidence: {signal.confidence:.1%})")
                        else:
                            self.logger.info(f"💤 {symbol}: Signal confidence {signal.confidence:.1%} below threshold {strict_threshold:.1%}")
                    else:
                        # No signal generated (failed basic criteria)
                        confidence_scores.append((symbol, 0.0))
                        self.logger.info(f"❌ {symbol}: No signal generated (0.00%)")
                except Exception as e:
                    self.logger.debug(f"Signal generation failed for {symbol}: {e}")
                    confidence_scores.append((symbol, 0.0))
            
            # Scan summary
            total_scanned = len(universe)
            signals_found = len(signals)
            rejected_count = total_scanned - signals_found
            
            self.logger.info(f"� Scan complete: {total_scanned} stocks scanned, {signals_found} signals found")
            
            # Show confidence scores for all stocks
            if confidence_scores:
                self.logger.info(f"📈 Confidence scores:")
                # Sort by confidence descending
                confidence_scores.sort(key=lambda x: x[1], reverse=True)
                for symbol, conf in confidence_scores:
                    status = "✅ PASS" if conf >= strict_threshold else "❌ REJECT"
                    self.logger.info(f"   {status} {symbol}: {conf:.2%}")
            if rejected_count > 0:
                self.logger.info(f"   {rejected_count} stocks rejected (below {strict_threshold:.1%} confidence threshold)")
            
            if not signals:
                self.logger.info("💤 No high-confidence late-entry signals found")
                self.logger.info(f"   Tip: Signals may appear as momentum builds or market picks up")
                return
            
            # Sort by confidence and take best
            signals.sort(key=lambda s: s.confidence, reverse=True)
            
            # Execute up to remaining late entry capacity
            remaining_late = max_late - self.late_entries_today
            remaining_total = total_capacity - self.trades_today
            max_to_execute = min(remaining_late, remaining_total, len(signals))
            
            for signal in signals[:max_to_execute]:
                try:
                    # Apply reduced position sizing for late entries (75% for small portfolios, 50% for large)
                    # Small portfolios need less reduction to make trades viable
                    portfolio_value = self._get_portfolio_value()
                    if portfolio_value < 5000:
                        size_reduction = 0.75  # Less reduction for small accounts
                        min_position_for_late = 25  # Lower minimum for late entries
                    else:
                        size_reduction = getattr(self.config, 'late_entry_position_size_pct', 0.5)
                        min_position_for_late = getattr(self.config, 'min_position_size_dollars', 50)
                    
                    # Check diversification (same-day restrictions removed for intraday trading)
                    if not self._check_diversification_limits(signal.symbol):
                        continue
                    
                    # Calculate position with reduced sizing
                    # Need to calculate stop price first
                    market_data_for_symbol = market_data.get(signal.symbol)
                    if market_data_for_symbol is None or market_data_for_symbol.empty:
                        self.logger.info(f"❌ {signal.symbol}: No market data for stop calculation")
                        continue
                    
                    stop_price, _ = self.stop_manager.calculate_optimal_stop(signal, market_data_for_symbol)
                    
                    shares, position_dollars = self.position_sizer.calculate_position_size(
                        signal, stop_price, portfolio_value
                    )
                    
                    self.logger.info(f"   {signal.symbol}: Base sizing: {shares} shares, ${position_dollars:.2f} (before {size_reduction:.0%} reduction)")
                    
                    # Apply late-entry reduction (but keep single-share positions intact)
                    if shares > 1:
                        shares = int(shares * size_reduction)
                        position_dollars *= size_reduction
                        self.logger.info(f"   {signal.symbol}: After reduction: {shares} shares, ${position_dollars:.2f}")
                    else:
                        self.logger.info(f"   {signal.symbol}: Single share - no reduction applied (${position_dollars:.2f})")
                    
                    if position_dollars < min_position_for_late:
                        self.logger.info(f"❌ {signal.symbol}: Late entry position too small (${position_dollars:.0f}, min: ${min_position_for_late})")
                        self.logger.info(f"   Entry: ${signal.entry_price:.2f}, Stop: ${stop_price:.2f}, Risk: ${signal.entry_price - stop_price:.2f}/share")
                        continue
                    
                    # Create position for late entry
                    et_tz = pytz.timezone('US/Eastern')
                    today = dt.datetime.now(et_tz).date()
                    exit_date = self._get_next_trading_day(today)
                    
                    position = ShortCyclePosition(
                        symbol=signal.symbol,
                        entry_date=today,
                        exit_date=exit_date,
                        entry_price=signal.entry_price,
                        position_size_shares=shares,
                        position_size_dollars=position_dollars,
                        stop_price=stop_price,
                        target_price=signal.target_price,
                        status=PositionStatus.PENDING,
                        ai_signal=signal,
                        max_risk_dollars=self.config.max_risk_per_trade_dollars
                    )
                    
                    # Execute trade
                    success = self._execute_trade(position)
                    if success:
                        position.status = PositionStatus.ENTERED
                        self.positions.append(position)
                        self.trades_today += 1
                        self.late_entries_today += 1
                        self._save_positions()
                        
                        self.logger.info(f"✅ LATE ENTRY: {signal.symbol} {position.position_size_shares} shares @ ${signal.entry_price:.2f} "
                                       f"(confidence: {signal.confidence:.1%}, size: ${position_dollars:.0f})")
                    
                except Exception as e:
                    self.logger.error(f"Error executing late entry for {signal.symbol}: {e}")
            
            # Execution summary
            executed = self.late_entries_today
            attempted = min(len(signals), max_to_execute)
            rejected = attempted - executed
            
            self.logger.info(f"📊 Late entry execution complete:")
            self.logger.info(f"   Signals processed: {attempted}, Executed: {executed}, Rejected: {rejected}")
            self.logger.info(f"   Late entries today: {self.late_entries_today}/{max_late}")
            if rejected > 0:
                self.logger.info(f"   Rejection reasons: Same-day activity, position size, diversification limits")
            
        except Exception as e:
            self.logger.error(f"Error in late entry attempt: {e}")
    
    def _check_volume_requirement(self, symbol: str, min_volume: int) -> bool:
        """Check if symbol meets minimum volume requirement"""
        try:
            import yfinance as yf
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period='5d')
            if len(hist) == 0:
                return False
            avg_volume = hist['Volume'].mean()
            return avg_volume >= min_volume
        except Exception:
            return True  # Don't block on data errors
    
    def _exit_position(self, position: ShortCyclePosition, exit_price: float, reason: str):
        """Exit a position and update tracking"""
        try:
            # CRITICAL FIX #2: Use position's tracked share count, NOT portfolio total
            # This fixes the Oct 22 CRM bug where 45 shares were sold instead of 23
            shares_to_exit = position.position_size_shares
            
            self.logger.info(
                f"🔚 Exiting {position.symbol}: {shares_to_exit} shares from position "
                f"entered {position.entry_date} (reason: {reason})"
            )
            
            # CRITICAL: Submit actual SELL order to Alpaca via RealPaperTradingEngine
            if hasattr(self, 'execution_engine') and self.execution_engine:
                order_result = self.execution_engine.submit_order(
                    symbol=position.symbol,
                    quantity=shares_to_exit,  # Use position-specific count!
                    side='sell'
                )
                
                if order_result:
                    self.logger.info(f"✅ REAL SELL ORDER SUBMITTED: {position.symbol} {position.position_size_shares} shares")
                    self.logger.info(f"   Order ID: {order_result['order_id']}")
                    self.logger.info(f"   Status: {order_result['status']}")
                    
                    # CRITICAL FIX (Nov 19): Update exit_price with ACTUAL fill price from Alpaca
                    # Same as entry fix - ensures accurate P&L calculations
                    filled_price = order_result.get('avg_fill_price') or order_result.get('filled_price') or order_result.get('fill_price')
                    if filled_price:
                        calculated_exit = exit_price
                        filled_exit = float(filled_price)
                        
                        # Calculate slippage
                        slippage_pct = abs(filled_exit - calculated_exit) / calculated_exit
                        
                        # Update exit_price with FILLED price
                        exit_price = filled_exit
                        
                        # Log slippage warning if significant
                        if slippage_pct > 0.02:  # >2% slippage
                            self.logger.warning(
                                f"⚠️ EXIT SLIPPAGE: {position.symbol} - "
                                f"Calculated: ${calculated_exit:.2f}, "
                                f"Filled: ${filled_exit:.2f} ({slippage_pct:.1%})"
                            )
                        else:
                            self.logger.info(
                                f"   Exit Fill: ${filled_exit:.2f} "
                                f"(calc: ${calculated_exit:.2f}, slip: {slippage_pct:.2%})"
                            )
                else:
                    self.logger.error(f"❌ FAILED to submit real sell order for {position.symbol}")
                    return False
            else:
                # Fallback to paper trade logging only if no execution engine
                self.logger.info(f"📝 Paper sell: {position.symbol} {position.position_size_shares} shares")
            
            position.exit_price = exit_price
            position.exit_reason = reason
            position.exit_timestamp = dt.datetime.now(pytz.UTC)  # Record when exit occurred
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
    
    def _force_close_all_positions(self, reason: str = "FORCE_EXIT"):
        """
        Force close all open positions immediately (intraday end-of-day cleanup)
        Used at 3:45 PM to ensure no overnight holds
        """
        try:
            # Get all active positions
            active_positions = [p for p in self.positions if p.status == PositionStatus.ENTERED]
            
            if not active_positions:
                self.logger.info("✅ No positions to force close")
                return
            
            self.logger.warning(f"🚨 Force closing {len(active_positions)} positions: {reason}")
            
            # Close each position at current market price
            for position in active_positions:
                try:
                    # Get current price
                    current_price = self._get_current_price(position.symbol)
                    if not current_price:
                        self.logger.error(f"❌ Cannot get price for {position.symbol}, skipping force exit")
                        continue
                    
                    # Exit position
                    self._exit_position(position, current_price, reason)
                    
                except Exception as e:
                    self.logger.error(f"❌ Error force closing {position.symbol}: {e}")
            
            self.logger.info(f"✅ Force close complete - all positions closed")
            
        except Exception as e:
            self.logger.error(f"Error in force close all positions: {e}")
    
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
            self.late_entries_today = 0  # Reset late entry counter
            self._signals_found_today = 0  # Reset signal counter for smart refresh
            self._watchlist_refreshed_today = False  # Reset refresh flag
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
    
    def _update_and_check_trailing_stop(self, position: ShortCyclePosition, current_price: float) -> Optional[Tuple[float, str]]:
        """
        Update trailing stop for position and check if it should be triggered.
        
        Returns:
            Tuple of (exit_price, exit_reason) if stop triggered, None otherwise
        """
        try:
            # Track highest price since entry
            if position.highest_price_since_entry is None:
                position.highest_price_since_entry = max(current_price, position.entry_price)
            else:
                position.highest_price_since_entry = max(position.highest_price_since_entry, current_price)
            
            # Calculate current profit percentage
            profit_pct = (current_price - position.entry_price) / position.entry_price
            
            # Check if we should activate trailing stop
            if not position.trailing_stop_enabled:
                if profit_pct >= self.config.trailing_trigger_pct:
                    # Activate trailing stop
                    position.trailing_stop_enabled = True
                    position.trailing_stop_activated_at = dt.datetime.now(pytz.UTC)
                    
                    # Set initial trailing stop price
                    # Lock in minimum profit
                    min_profit_price = position.entry_price * (1 + self.config.trailing_min_profit_pct)
                    trailing_price = current_price * (1 - self.config.trailing_distance_pct)
                    position.trailing_stop_price = max(trailing_price, min_profit_price)
                    
                    self.logger.info(
                        f"🎯 {position.symbol}: Trailing stop ACTIVATED at ${current_price:.2f} "
                        f"(+{profit_pct*100:.1f}%) | Stop: ${position.trailing_stop_price:.2f}"
                    )
                    return None  # Don't exit yet, just activated
            
            # If trailing stop is active, update it
            if position.trailing_stop_enabled:
                # Calculate new trailing stop price
                new_trail_price = position.highest_price_since_entry * (1 - self.config.trailing_distance_pct)
                
                # Ensure minimum profit lock
                min_profit_price = position.entry_price * (1 + self.config.trailing_min_profit_pct)
                new_trail_price = max(new_trail_price, min_profit_price)
                
                # Only move stop up, never down
                if new_trail_price > position.trailing_stop_price:
                    old_stop = position.trailing_stop_price
                    position.trailing_stop_price = new_trail_price
                    self.logger.debug(
                        f"📈 {position.symbol}: Trailing stop raised: ${old_stop:.2f} → ${new_trail_price:.2f} "
                        f"(Current: ${current_price:.2f}, High: ${position.highest_price_since_entry:.2f})"
                    )
                
                # Check if current price hit trailing stop
                if current_price <= position.trailing_stop_price:
                    locked_profit_pct = (position.trailing_stop_price - position.entry_price) / position.entry_price
                    self.logger.info(
                        f"✅ {position.symbol}: TRAILING STOP HIT! "
                        f"Entry: ${position.entry_price:.2f} → Exit: ${current_price:.2f} "
                        f"(Locked profit: +{locked_profit_pct*100:.1f}%, Peak: ${position.highest_price_since_entry:.2f})"
                    )
                    return (current_price, f"TRAILING_STOP_+{locked_profit_pct*100:.1f}%")
            
            return None  # No exit triggered
            
        except Exception as e:
            self.logger.error(f"Error updating trailing stop for {position.symbol}: {e}")
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
                from dynamic_universe_generator import get_dynamic_universe
                
                # DYNAMIC UNIVERSE GENERATION (Nov 11, 2025)
                # Fetches ALL tradable stocks from Alpaca API in $10-45 range (Nov 18 - expanded)
                # Provides true sector diversification across all 11 GICS sectors
                # Updates daily, auto-discovers IPOs, auto-removes delisted stocks
                try:
                    candidates = get_dynamic_universe(
                        min_price=10.0,
                        max_price=45.0,  # Nov 18 - Expanded to $45 for growth stocks
                        min_volume=100_000,
                        max_candidates=500,  # Nov 18 - Increased to 500 for better diversity
                        save_to_file=True
                    )
                    self.logger.info(f"✅ Dynamic universe loaded: {len(candidates)} candidates from all sectors")
                    
                except Exception as dyn_err:
                    self.logger.warning(f"⚠️ Dynamic universe fetch failed: {dyn_err}")
                    self.logger.warning("   Using emergency mid-cap fallback list")
                    # Emergency fallback: Core mid-cap list
                    candidates = [
                        "PLTR","RIVN","LCID","NIO","XPEV","LI","GOEV","FSR",
                        "HOOD","SOFI","UPST","AFRM","SQ","OPEN","COIN",
                        "SNAP","PINS","MTCH","BMBL","RBLX","U","DKNG",
                        "PATH","SNOW","DDOG","CRWD","ZS","NET","MDB","FSLY",
                        "MRNA","NVAX","TDOC","PTON","DOCS","VCYT","SDGR",
                        "PLUG","BE","CHPT","BLNK","QS","MP","LAC",
                        "AMC","GME","WISH","CLOV","SKLZ","SPCE","ASTS","IONQ",
                        "F","NOK","BBD","VALE","BTG","GOLD","AUY","FCX"
                    ]
                # Fetch recent OHLCV from DataLoader for PreFilter input
                if self._prefilter is None:
                    self._prefilter = PreFilter(
                        simulation_mode=False,
                        data_loader=self.data_loader,
                        fast_mode=self.config.fast_mode if hasattr(self.config, 'fast_mode') else True,
                        enable_intraday_analysis=self.enable_intraday_analysis,
                        max_intraday_analyses_per_day=self.max_intraday_analyses_per_day
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
                
                # UPDATED Oct 21, 2025: Quality over quantity - no mandatory fallbacks
                # Accept PreFilter output if ANY stocks pass (targeting 10-15, accepting 5-20)
                if len(ranked_symbols) >= 1:
                    final_list: List[str]
                    if max_symbols is None:
                        final_list = ranked_symbols[:]
                    else:
                        final_list = ranked_symbols[:max_symbols]
                    
                    # NO FALLBACK LOGIC - Only use stocks that passed PreFilter
                    # Quality > Quantity: Better to trade 5-10 quality stocks than 30 mediocre ones
                    num_stocks = len(final_list)
                    if num_stocks < min_symbols:
                        self.logger.warning(
                            f"⚠️ PreFilter returned {num_stocks} stocks (below min {min_symbols}), "
                            f"but proceeding with quality-only universe (no fallbacks added)"
                        )
                    
                    self.logger.info(
                        f"✅ Using PreFilter universe: {num_stocks} quality stocks passed all filters"
                    )
                    return final_list if max_symbols is None else final_list[:max_symbols]
                else:
                    self.logger.warning(
                        f"⚠️ PreFilter returned zero symbols - check market conditions or filter settings"
                    )
                    # Return empty list rather than falling back to unvetted stocks
                    return []
            except Exception as e:
                self.logger.error(f"PreFilter failed: {e}")
                # Return empty rather than fall back to unvetted stocks
                return []

        except Exception as e:
            self.logger.error(f"Error building trading universe: {e}")
            # Return empty list to prevent trading with emergency fallback stocks
            self.logger.critical("⚠️ Critical: Unable to build universe - trading will be skipped")
            return []
    
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
                    position.exit_timestamp = dt.datetime.now(pytz.UTC)
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
                # CRITICAL: Create position object from Alpaca data so D+1 exits work!
                self.logger.info(
                    f"📊 Alpaca position detected: {symbol_key} ({live_data.get('quantity')} shares) - creating position tracker"
                )
                
                try:
                    # Get full position details from Alpaca
                    qty = int(round(abs(live_data.get('quantity', 0))))
                    avg_cost = float(live_data.get('avg_cost', 0))
                    
                    if qty > 0 and avg_cost > 0:
                        # Try to get actual fill time from Alpaca order history
                        entry_timestamp = None
                        entry_date = dt.date.today()  # Default fallback
                        
                        try:
                            # Get recent orders for this symbol
                            if hasattr(self, 'execution_engine') and self.execution_engine:
                                orders = self.execution_engine.get_order_history(days_back=5, status='closed')
                                
                                # Find the most recent BUY order for this symbol
                                for order in orders:
                                    if (order.get('symbol') == symbol_key and 
                                        order.get('side') == 'buy' and
                                        order.get('filled_at')):
                                        # Found the entry order!
                                        filled_at_str = order.get('filled_at')
                                        entry_timestamp = dt.datetime.fromisoformat(filled_at_str.replace('Z', '+00:00'))
                                        entry_date = entry_timestamp.date()
                                        self.logger.info(f"✅ {symbol_key}: Found entry order from {entry_date} at {entry_timestamp.strftime('%H:%M:%S')}")
                                        break
                        except Exception as e:
                            self.logger.warning(f"⚠️ Could not get order history for {symbol_key}: {e}, using today as entry date")
                        
                        # If we couldn't get timestamp from orders, use now
                        if not entry_timestamp:
                            entry_timestamp = dt.datetime.now(pytz.UTC)
                            entry_date = dt.date.today()
                            self.logger.info(f"ℹ️ {symbol_key}: Using today as entry date (no order history found)")
                        
                        # Calculate D+1 exit date
                        exit_date = self._get_next_trading_day(entry_date)
                        
                        # Create a minimal AI signal for the position
                        ai_signal = AISignal(
                            symbol=symbol_key,
                            action="BUY",
                            confidence=0.5,
                            time_horizon_days=1.5,
                            entry_price=avg_cost,
                            signal_timestamp=entry_timestamp
                        )
                        
                        # Create the position object
                        position = ShortCyclePosition(
                            symbol=symbol_key,
                            entry_date=entry_date,
                            exit_date=exit_date,
                            entry_price=avg_cost,
                            position_size_shares=qty,
                            position_size_dollars=qty * avg_cost,
                            stop_price=avg_cost * 0.975,  # 2.5% stop
                            target_price=None,
                            status=PositionStatus.ENTERED,
                            ai_signal=ai_signal,
                            max_risk_dollars=qty * avg_cost * 0.025,
                            entry_timestamp=entry_timestamp,
                            filled_at=entry_timestamp
                        )
                        
                        self.positions.append(position)
                        state_changed = True
                        self.logger.info(f"✅ {symbol_key}: Position tracker created (entry: {entry_date}, D+1 exit: {exit_date})")
                        
                except Exception as e:
                    self.logger.error(f"❌ Failed to create position tracker for {symbol_key}: {e}")
                    import traceback
                    self.logger.error(traceback.format_exc())

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
                    
                    # NEW: Parse timestamp fields for accurate D+1 tracking
                    entry_timestamp = None
                    if data.get('entry_timestamp'):
                        try:
                            entry_timestamp = dt.datetime.fromisoformat(data['entry_timestamp'])
                        except Exception:
                            pass
                    
                    filled_at = None
                    if data.get('filled_at'):
                        try:
                            filled_at = dt.datetime.fromisoformat(data['filled_at'])
                        except Exception:
                            pass

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
                        max_risk_dollars=data.get('max_risk_dollars', 0.0),
                        # NEW: Restore timestamp fields
                        entry_timestamp=entry_timestamp,
                        filled_at=filled_at,
                        order_id=data.get('order_id')
                    )
                    
                    # Restore exit data
                    if data.get('exit_price'):
                        position.exit_price = data['exit_price']
                    if data.get('exit_reason'):
                        position.exit_reason = data['exit_reason']
                    if data.get('realized_pnl') is not None:
                        position.realized_pnl = data['realized_pnl']
                    
                    # CRITICAL PDT FIX: Restore exit_timestamp for same-day activity detection
                    if data.get('exit_timestamp'):
                        try:
                            position.exit_timestamp = dt.datetime.fromisoformat(data['exit_timestamp'])
                        except Exception:
                            position.exit_timestamp = None
                    
                    self.positions.append(position)
                
                self.logger.info(f"📋 Loaded {len(self.positions)} positions from previous session")
            else:
                self.logger.info("📋 No previous positions found - starting fresh")
                
        except Exception as e:
            self.logger.error(f"Error loading positions: {e}")
            self.positions = []
    
    def _save_positions(self):
        """Save current positions to file (for backup/recovery only - Alpaca is source of truth)"""
        try:
            import json
            positions_file = "positions.json"
            
            # Skip saving if no positions (Alpaca is source of truth anyway)
            if not self.positions:
                return
            
            position_data = []
            for position in self.positions:
                # CRITICAL: Ensure shares is not None (sync from Alpaca if needed)
                shares = position.position_size_shares
                
                # Only attempt sync for ACTIVE positions (not exited/cancelled)
                if (shares is None or shares == 0) and position.status == PositionStatus.ENTERED:
                    # Try to get from Alpaca using the correct method
                    if hasattr(self, 'execution_engine') and self.execution_engine:
                        try:
                            live_positions = self._get_live_portfolio_positions()
                            live_data = live_positions.get(position.symbol.upper())
                            if live_data:
                                shares = int(abs(live_data.get('quantity', 0)))
                                position.position_size_shares = shares
                                self.logger.info(f"✅ {position.symbol}: Synced {shares} shares from Alpaca")
                            else:
                                self.logger.warning(f"⚠️  {position.symbol}: Active position but no shares found in Alpaca!")
                        except Exception as e:
                            self.logger.error(f"❌ Failed to sync {position.symbol} from Alpaca: {e}")
                elif (shares is None or shares == 0) and position.status != PositionStatus.ENTERED:
                    # For exited positions, just use 0 - it's already closed
                    shares = 0
                
                data = {
                    'symbol': position.symbol,
                    'entry_date': position.entry_date.isoformat(),
                    'exit_date': position.exit_date.isoformat(),
                    'entry_price': position.entry_price,
                    'position_size_shares': shares,  # Use validated/synced shares
                    'position_size_dollars': position.position_size_dollars,
                    'stop_price': position.stop_price,
                    'target_price': position.target_price,
                    'status': position.status.value if hasattr(position.status, 'value') else position.status,
                    'max_risk_dollars': position.max_risk_dollars,
                    # NEW: Timestamp fields for accurate D+1 tracking
                    'entry_timestamp': position.entry_timestamp.isoformat() if position.entry_timestamp else None,
                    'filled_at': position.filled_at.isoformat() if position.filled_at else None,
                    'exit_timestamp': position.exit_timestamp.isoformat() if hasattr(position, 'exit_timestamp') and position.exit_timestamp else None,  # CRITICAL PDT FIX
                    'order_id': str(position.order_id) if position.order_id else None,  # Convert UUID to string
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
                json.dump(position_data, f, indent=2, default=str)
                
            self.logger.info(f"💾 Saved {len(self.positions)} positions to {positions_file}")
            
        except Exception as e:
            self.logger.error(f"Error saving positions: {e}")

    def _run_end_of_day_monitoring(self):
        """Run self-monitoring at end of trading day"""
        if not self.monitoring_system:
            self.logger.debug("Self-monitoring not available")
            return
            
        try:
            self.logger.info("🤖 Running end-of-day self-monitoring...")
            results = self.monitoring_system.run_end_of_day_check()
            
            # Log report location
            if results.get('report_file'):
                self.logger.info(f"📄 Daily report saved: {results['report_file']}")
            
            # Alert on PDT violations
            if results.get('pdt_audit'):
                violations = results['pdt_audit'].get('violations_found', 0)
                if violations > 0:
                    self.logger.critical(f"🚨 PDT VIOLATIONS DETECTED: {violations}")
                    self.logger.critical("   ⚠️  Review report and reduce trading frequency!")
                else:
                    self.logger.info(f"✅ PDT Check: No violations (Score: {results['pdt_audit'].get('pdt_score', 100)}/100)")
            
            # Alert on health status
            if results.get('health_check'):
                status = results['health_check'].get('overall_status', 'UNKNOWN')
                score = results['health_check'].get('system_health_score', 0)
                
                if status == 'CRITICAL':
                    self.logger.critical(f"🚨 SYSTEM HEALTH CRITICAL ({score}/100)")
                    self.logger.critical("   ⚠️  Immediate attention required!")
                elif status == 'WARNING':
                    self.logger.warning(f"⚠️  System health degraded ({score}/100)")
                else:
                    self.logger.info(f"✅ System Health: {status} ({score}/100)")
            
            # Alert on auto-corrections
            if results.get('auto_correct'):
                adjustments = results['auto_correct'].get('adjustments_made', 0)
                if adjustments > 0:
                    self.logger.info(f"🔧 Auto-corrections applied: {adjustments}")
                    for adjustment in results['auto_correct'].get('details', []):
                        self.logger.info(f"   • {adjustment}")
                        
            self.logger.info("✅ End-of-day monitoring complete")
            
        except Exception as e:
            self.logger.error(f"❌ Self-monitoring failed: {e}")
            self.logger.error("   System will continue operating, but manual review recommended")


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

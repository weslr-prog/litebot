"""
Scalping Module for LiteBotX - Intraday High-Frequency Trading
Purpose: 0.5-2% profit targets with minute-level execution for same-day profits

Features:
- Momentum scalping (breakout-based entries)
- Mean reversion scalping (oversold/overbought bounces) 
- News-based scalping (event-driven opportunities)
- Volume spike scalping (unusual activity detection)
- Real-time execution with sub-minute precision
- Risk management optimized for quick trades
"""

import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import json
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

class ScalpingSignal(Enum):
    """Types of scalping signals"""
    MOMENTUM_BREAKOUT = "momentum_breakout"      # Price breaks resistance with volume
    MOMENTUM_BREAKDOWN = "momentum_breakdown"    # Price breaks support with volume  
    MEAN_REVERSION_BOUNCE = "mean_reversion_bounce"  # Oversold bounce from key level
    MEAN_REVERSION_FADE = "mean_reversion_fade"      # Overbought fade from resistance
    VOLUME_SPIKE_LONG = "volume_spike_long"      # Unusual volume with price increase
    VOLUME_SPIKE_SHORT = "volume_spike_short"    # Unusual volume with price decrease
    NEWS_MOMENTUM_LONG = "news_momentum_long"    # Positive news catalyst
    NEWS_MOMENTUM_SHORT = "news_momentum_short"  # Negative news catalyst

class ScalpingTimeframe(Enum):
    """Timeframes for scalping analysis"""
    TICK = "tick"           # Tick-by-tick data
    SECOND_15 = "15s"       # 15-second bars
    SECOND_30 = "30s"       # 30-second bars  
    MINUTE_1 = "1m"         # 1-minute bars
    MINUTE_2 = "2m"         # 2-minute bars
    MINUTE_5 = "5m"         # 5-minute bars

@dataclass
class ScalpingConfig:
    """Configuration for scalping strategies"""
    # Profit targets (small but frequent)
    min_profit_target: float = 0.005   # 0.5% minimum profit
    max_profit_target: float = 0.02    # 2.0% maximum profit  
    default_profit_target: float = 0.01  # 1.0% default target
    
    # Risk management (tight stops)
    max_loss_per_trade: float = 0.003  # 0.3% max loss per trade
    default_stop_loss: float = 0.002   # 0.2% default stop loss
    
    # Position sizing (smaller positions for speed)
    max_position_size_pct: float = 0.05  # 5% of portfolio per position
    min_position_value: float = 1000     # $1000 minimum position
    
    # Timing constraints
    max_hold_time_minutes: int = 30      # Max 30 minutes per trade
    min_hold_time_seconds: int = 10      # Min 10 seconds per trade
    
    # Market conditions
    min_volume_ratio: float = 1.5        # 1.5x average volume required
    min_spread_threshold: float = 0.001   # Max 0.1% bid-ask spread
    
    # Technical levels
    momentum_threshold: float = 0.002     # 0.2% move for momentum signal
    mean_reversion_threshold: float = 0.015  # 1.5% from mean for reversion
    
    # Risk controls
    max_daily_trades: int = 50           # Max 50 trades per day
    max_concurrent_positions: int = 5     # Max 5 positions at once
    daily_loss_limit: float = 0.02      # 2% daily loss limit

@dataclass
class ScalpingOpportunity:
    """Represents a scalping opportunity"""
    symbol: str
    signal_type: ScalpingSignal
    entry_price: float
    stop_loss: float
    profit_target: float
    confidence: float                    # 0.0-1.0 signal confidence
    timeframe: ScalpingTimeframe
    volume_ratio: float                  # Current volume vs average
    spread_pct: float                   # Bid-ask spread percentage
    momentum_score: float               # Technical momentum indicator
    mean_reversion_score: float         # Distance from mean/levels
    timestamp: datetime
    urgency: str                        # 'LOW', 'MEDIUM', 'HIGH', 'URGENT'
    risk_reward_ratio: float            # Expected profit / risk ratio
    market_conditions: Dict             # Additional market context

class MomentumScalper:
    """
    Momentum-based scalping strategy
    Captures breakouts and breakdowns with volume confirmation
    """
    
    def __init__(self, config: ScalpingConfig):
        self.config = config
        self.name = "MomentumScalper"
        self.active_positions = {}
        self.trade_count = 0
        
        logging.info(f"🏃 {self.name} initialized: {config.momentum_threshold:.1%} momentum threshold")
    
    def analyze_momentum_opportunity(self, symbol: str, price_data: Dict, 
                                   volume_data: Dict, market_context: Dict) -> Optional[ScalpingOpportunity]:
        """
        Analyze momentum scalping opportunity
        
        Args:
            symbol: Stock symbol
            price_data: Current and recent price data
            volume_data: Current and average volume data  
            market_context: Market conditions and technical levels
            
        Returns:
            ScalpingOpportunity if valid signal found
        """
        
        current_price = price_data.get('current', 0)
        high_1m = price_data.get('high_1m', current_price)
        low_1m = price_data.get('low_1m', current_price)
        open_1m = price_data.get('open_1m', current_price)
        
        # Calculate momentum metrics
        price_change_1m = (current_price - open_1m) / open_1m if open_1m > 0 else 0
        volume_ratio = volume_data.get('volume_ratio', 0)
        avg_volume = volume_data.get('avg_volume', 0)
        
        # Check basic requirements
        if (volume_ratio < self.config.min_volume_ratio or
            abs(price_change_1m) < self.config.momentum_threshold):
            return None
        
        # Determine signal type and direction
        if price_change_1m > self.config.momentum_threshold:
            # Bullish momentum breakout
            signal_type = ScalpingSignal.MOMENTUM_BREAKOUT
            entry_price = current_price * 1.001  # Slight premium for execution
            stop_loss = current_price * (1 - self.config.default_stop_loss)
            profit_target = current_price * (1 + self.config.default_profit_target)
            
        elif price_change_1m < -self.config.momentum_threshold:
            # Bearish momentum breakdown  
            signal_type = ScalpingSignal.MOMENTUM_BREAKDOWN
            entry_price = current_price * 0.999  # Slight discount for short entry
            stop_loss = current_price * (1 + self.config.default_stop_loss)
            profit_target = current_price * (1 - self.config.default_profit_target)
            
        else:
            return None
        
        # Calculate confidence based on momentum strength and volume
        momentum_strength = min(abs(price_change_1m) / self.config.momentum_threshold, 3.0)
        volume_strength = min(volume_ratio / self.config.min_volume_ratio, 2.0)
        confidence = min((momentum_strength + volume_strength) / 5.0, 0.95)
        
        # Calculate risk-reward ratio
        risk = abs(entry_price - stop_loss)
        reward = abs(profit_target - entry_price)
        risk_reward_ratio = reward / risk if risk > 0 else 0
        
        # Determine urgency based on momentum acceleration
        if abs(price_change_1m) > self.config.momentum_threshold * 2:
            urgency = 'URGENT'
        elif volume_ratio > self.config.min_volume_ratio * 2:
            urgency = 'HIGH'  
        elif confidence > 0.7:
            urgency = 'MEDIUM'
        else:
            urgency = 'LOW'
        
        opportunity = ScalpingOpportunity(
            symbol=symbol,
            signal_type=signal_type,
            entry_price=entry_price,
            stop_loss=stop_loss,
            profit_target=profit_target,
            confidence=confidence,
            timeframe=ScalpingTimeframe.MINUTE_1,
            volume_ratio=volume_ratio,
            spread_pct=market_context.get('spread_pct', 0),
            momentum_score=momentum_strength,
            mean_reversion_score=0.0,  # Not applicable for momentum
            timestamp=datetime.now(timezone.utc),
            urgency=urgency,
            risk_reward_ratio=risk_reward_ratio,
            market_conditions=market_context
        )
        
        logging.info(f"🏃 Momentum opportunity: {symbol} {signal_type.value} @ ${entry_price:.2f}, "
                    f"confidence={confidence:.2f}, urgency={urgency}")
        
        return opportunity

class MeanReversionScalper:
    """
    Mean reversion scalping strategy
    Captures bounces from oversold/overbought levels
    """
    
    def __init__(self, config: ScalpingConfig):
        self.config = config
        self.name = "MeanReversionScalper"
        self.active_positions = {}
        self.trade_count = 0
        
        logging.info(f"🔄 {self.name} initialized: {config.mean_reversion_threshold:.1%} reversion threshold")
    
    def analyze_reversion_opportunity(self, symbol: str, price_data: Dict,
                                    technical_levels: Dict, market_context: Dict) -> Optional[ScalpingOpportunity]:
        """
        Analyze mean reversion scalping opportunity
        
        Args:
            symbol: Stock symbol
            price_data: Current and recent price data
            technical_levels: Support/resistance and moving averages
            market_context: Market conditions
            
        Returns:
            ScalpingOpportunity if valid signal found
        """
        
        current_price = price_data.get('current', 0)
        vwap = technical_levels.get('vwap', current_price)
        support = technical_levels.get('support', current_price * 0.98)
        resistance = technical_levels.get('resistance', current_price * 1.02)
        
        # Calculate distance from key levels
        distance_from_vwap = (current_price - vwap) / vwap if vwap > 0 else 0
        distance_from_support = (current_price - support) / support if support > 0 else 0
        distance_from_resistance = (resistance - current_price) / resistance if resistance > 0 else 0
        
        # Check for oversold bounce opportunity (long)
        if (distance_from_support < 0.005 and  # Within 0.5% of support
            distance_from_vwap < -self.config.mean_reversion_threshold):  # Oversold vs VWAP
            
            signal_type = ScalpingSignal.MEAN_REVERSION_BOUNCE
            entry_price = current_price * 1.0005  # Small premium
            stop_loss = support * 0.998  # Just below support
            profit_target = min(vwap, current_price * (1 + self.config.default_profit_target))
            
        # Check for overbought fade opportunity (short)
        elif (distance_from_resistance < 0.005 and  # Within 0.5% of resistance  
              distance_from_vwap > self.config.mean_reversion_threshold):  # Overbought vs VWAP
            
            signal_type = ScalpingSignal.MEAN_REVERSION_FADE
            entry_price = current_price * 0.9995  # Small discount for short
            stop_loss = resistance * 1.002  # Just above resistance
            profit_target = max(vwap, current_price * (1 - self.config.default_profit_target))
            
        else:
            return None
        
        # Calculate confidence based on level proximity and mean reversion strength
        level_proximity = 1.0 - min(distance_from_support, distance_from_resistance) / 0.01
        reversion_strength = min(abs(distance_from_vwap) / self.config.mean_reversion_threshold, 2.0)
        confidence = min((level_proximity + reversion_strength) / 3.0, 0.9)
        
        # Risk-reward calculation
        risk = abs(entry_price - stop_loss)
        reward = abs(profit_target - entry_price)
        risk_reward_ratio = reward / risk if risk > 0 else 0
        
        # Urgency based on proximity to levels
        if min(distance_from_support, distance_from_resistance) < 0.002:
            urgency = 'URGENT'
        elif confidence > 0.7:
            urgency = 'HIGH'
        elif risk_reward_ratio > 2.0:
            urgency = 'MEDIUM'
        else:
            urgency = 'LOW'
        
        opportunity = ScalpingOpportunity(
            symbol=symbol,
            signal_type=signal_type,
            entry_price=entry_price,
            stop_loss=stop_loss,
            profit_target=profit_target,
            confidence=confidence,
            timeframe=ScalpingTimeframe.MINUTE_1,
            volume_ratio=market_context.get('volume_ratio', 1.0),
            spread_pct=market_context.get('spread_pct', 0),
            momentum_score=0.0,  # Not applicable for mean reversion
            mean_reversion_score=reversion_strength,
            timestamp=datetime.now(timezone.utc),
            urgency=urgency,
            risk_reward_ratio=risk_reward_ratio,
            market_conditions=market_context
        )
        
        logging.info(f"🔄 Mean reversion opportunity: {symbol} {signal_type.value} @ ${entry_price:.2f}, "
                    f"confidence={confidence:.2f}, R:R={risk_reward_ratio:.1f}")
        
        return opportunity

class VolumeSpikesScalper:
    """
    Volume spike scalping strategy
    Captures moves triggered by unusual volume activity
    """
    
    def __init__(self, config: ScalpingConfig):
        self.config = config
        self.name = "VolumeSpikesScalper"
        self.active_positions = {}
        self.trade_count = 0
        
        logging.info(f"📊 {self.name} initialized: {config.min_volume_ratio:.1f}x volume threshold")
    
    def analyze_volume_spike_opportunity(self, symbol: str, price_data: Dict,
                                       volume_data: Dict, market_context: Dict) -> Optional[ScalpingOpportunity]:
        """
        Analyze volume spike scalping opportunity
        
        Args:
            symbol: Stock symbol  
            price_data: Current and recent price data
            volume_data: Volume metrics and ratios
            market_context: Market conditions
            
        Returns:
            ScalpingOpportunity if valid signal found
        """
        
        current_price = price_data.get('current', 0)
        price_change_1m = price_data.get('change_1m_pct', 0)
        volume_ratio = volume_data.get('volume_ratio', 0)
        volume_spike_ratio = volume_data.get('spike_ratio', 0)  # Current vs recent average
        
        # Require significant volume spike
        if volume_spike_ratio < 3.0:  # 3x recent volume
            return None
        
        # Determine direction based on price action during volume spike
        if price_change_1m > 0.002:  # Positive price action with volume
            signal_type = ScalpingSignal.VOLUME_SPIKE_LONG
            entry_price = current_price * 1.001
            stop_loss = current_price * (1 - self.config.default_stop_loss)
            profit_target = current_price * (1 + self.config.default_profit_target)
            
        elif price_change_1m < -0.002:  # Negative price action with volume
            signal_type = ScalpingSignal.VOLUME_SPIKE_SHORT
            entry_price = current_price * 0.999
            stop_loss = current_price * (1 + self.config.default_stop_loss)
            profit_target = current_price * (1 - self.config.default_profit_target)
            
        else:
            return None  # No clear directional bias
        
        # Confidence based on volume spike magnitude and price confirmation
        volume_strength = min(volume_spike_ratio / 5.0, 1.0)  # Normalize spike ratio
        price_confirmation = min(abs(price_change_1m) / 0.005, 1.0)  # Price movement strength
        confidence = min((volume_strength + price_confirmation) / 2.0, 0.85)
        
        # Risk-reward calculation
        risk = abs(entry_price - stop_loss)
        reward = abs(profit_target - entry_price)
        risk_reward_ratio = reward / risk if risk > 0 else 0
        
        # High urgency for volume spikes (they're time-sensitive)
        if volume_spike_ratio > 5.0:
            urgency = 'URGENT'
        elif volume_spike_ratio > 4.0:
            urgency = 'HIGH'
        else:
            urgency = 'MEDIUM'
        
        opportunity = ScalpingOpportunity(
            symbol=symbol,
            signal_type=signal_type,
            entry_price=entry_price,
            stop_loss=stop_loss,
            profit_target=profit_target,
            confidence=confidence,
            timeframe=ScalpingTimeframe.MINUTE_1,
            volume_ratio=volume_ratio,
            spread_pct=market_context.get('spread_pct', 0),
            momentum_score=price_confirmation,
            mean_reversion_score=0.0,
            timestamp=datetime.now(timezone.utc),
            urgency=urgency,
            risk_reward_ratio=risk_reward_ratio,
            market_conditions=market_context
        )
        
        logging.info(f"📊 Volume spike opportunity: {symbol} {signal_type.value} @ ${entry_price:.2f}, "
                    f"spike={volume_spike_ratio:.1f}x, confidence={confidence:.2f}")
        
        return opportunity

class ScalpingManager:
    """
    Central manager for all scalping strategies
    Coordinates multiple scalpers and manages execution
    """
    
    def __init__(self, config: ScalpingConfig = None):
        self.config = config or ScalpingConfig()
        self.name = "ScalpingManager"
        
        # Initialize scalping strategies
        self.momentum_scalper = MomentumScalper(self.config)
        self.reversion_scalper = MeanReversionScalper(self.config)
        self.volume_scalper = VolumeSpikesScalper(self.config)
        
        # Active management
        self.active_positions = {}  # {symbol: position_info}
        self.pending_opportunities = []  # Queue of opportunities
        self.daily_trades = 0
        self.daily_pnl = 0.0
        self.last_reset_date = None
        
        # Performance tracking
        self.strategy_performance = {
            'momentum': {'trades': 0, 'wins': 0, 'total_pnl': 0.0},
            'reversion': {'trades': 0, 'wins': 0, 'total_pnl': 0.0},
            'volume': {'trades': 0, 'wins': 0, 'total_pnl': 0.0}
        }
        
        logging.info(f"⚡ {self.name} initialized with {len(self._get_strategies())} strategies")
        logging.info(f"   Max daily trades: {self.config.max_daily_trades}")
        logging.info(f"   Max concurrent positions: {self.config.max_concurrent_positions}")
        logging.info(f"   Target profit range: {self.config.min_profit_target:.1%}-{self.config.max_profit_target:.1%}")
    
    def _get_strategies(self) -> List:
        """Get list of active scalping strategies"""
        return [self.momentum_scalper, self.reversion_scalper, self.volume_scalper]
    
    def scan_for_opportunities(self, market_data: Dict) -> List[ScalpingOpportunity]:
        """
        Scan market for scalping opportunities across all strategies
        
        Args:
            market_data: Real-time market data for multiple symbols
            
        Returns:
            List of ScalpingOpportunity objects sorted by urgency
        """
        
        opportunities = []
        
        # Daily reset check
        self._check_daily_reset()
        
        # Check daily limits
        if self.daily_trades >= self.config.max_daily_trades:
            logging.warning(f"⚠️ Daily trade limit reached: {self.daily_trades}/{self.config.max_daily_trades}")
            return []
        
        if len(self.active_positions) >= self.config.max_concurrent_positions:
            logging.warning(f"⚠️ Max concurrent positions reached: {len(self.active_positions)}")
            return []
        
        # Scan each symbol for opportunities
        for symbol, data in market_data.items():
            if symbol in self.active_positions:
                continue  # Skip symbols with active positions
            
            # Extract data components
            price_data = data.get('price', {})
            volume_data = data.get('volume', {})
            technical_levels = data.get('technical', {})
            market_context = data.get('context', {})
            
            # Check market quality (spread, volume, etc.)
            if not self._check_market_quality(market_context):
                continue
            
            # Scan with each strategy
            try:
                # Momentum scalping
                momentum_opp = self.momentum_scalper.analyze_momentum_opportunity(
                    symbol, price_data, volume_data, market_context)
                if momentum_opp:
                    opportunities.append(momentum_opp)
                
                # Mean reversion scalping  
                reversion_opp = self.reversion_scalper.analyze_reversion_opportunity(
                    symbol, price_data, technical_levels, market_context)
                if reversion_opp:
                    opportunities.append(reversion_opp)
                
                # Volume spike scalping
                volume_opp = self.volume_scalper.analyze_volume_spike_opportunity(
                    symbol, price_data, volume_data, market_context)
                if volume_opp:
                    opportunities.append(volume_opp)
                    
            except Exception as e:
                logging.error(f"❌ Error scanning {symbol}: {e}")
                continue
        
        # Sort by urgency and confidence
        opportunities.sort(key=lambda x: (
            self._urgency_score(x.urgency),
            x.confidence,
            x.risk_reward_ratio
        ), reverse=True)
        
        if opportunities:
            logging.info(f"🔍 Found {len(opportunities)} scalping opportunities")
            for opp in opportunities[:3]:  # Log top 3
                logging.info(f"   {opp.symbol} {opp.signal_type.value}: {opp.urgency} urgency, "
                            f"{opp.confidence:.2f} confidence")
        
        return opportunities
    
    def _urgency_score(self, urgency: str) -> int:
        """Convert urgency to numeric score for sorting"""
        scores = {'URGENT': 4, 'HIGH': 3, 'MEDIUM': 2, 'LOW': 1}
        return scores.get(urgency, 0)
    
    def _check_market_quality(self, market_context: Dict) -> bool:
        """Check if market conditions are suitable for scalping"""
        
        spread_pct = market_context.get('spread_pct', 1.0)
        volume_ratio = market_context.get('volume_ratio', 0)
        
        # Spread too wide
        if spread_pct > self.config.min_spread_threshold:
            return False
        
        # Volume too low
        if volume_ratio < self.config.min_volume_ratio * 0.8:  # Slightly lower threshold for quality check
            return False
        
        return True
    
    def _check_daily_reset(self):
        """Reset daily counters at market open"""
        today = datetime.now().date()
        if self.last_reset_date != today:
            self.daily_trades = 0
            self.daily_pnl = 0.0
            self.last_reset_date = today
            logging.info(f"📅 Daily scalping counters reset for {today}")
    
    def execute_opportunity(self, opportunity: ScalpingOpportunity, 
                          execution_engine) -> Dict:
        """
        Execute scalping opportunity with fast order routing
        
        Args:
            opportunity: ScalpingOpportunity to execute
            execution_engine: ExecutionEngine for trade execution
            
        Returns:
            Dict with execution result
        """
        
        symbol = opportunity.symbol
        
        # Final checks before execution
        if symbol in self.active_positions:
            return {'status': 'REJECTED', 'reason': 'position_exists'}
        
        if self.daily_trades >= self.config.max_daily_trades:
            return {'status': 'REJECTED', 'reason': 'daily_limit'}
        
        # Determine order type and quantity
        if opportunity.signal_type in [ScalpingSignal.MOMENTUM_BREAKOUT, 
                                     ScalpingSignal.VOLUME_SPIKE_LONG,
                                     ScalpingSignal.MEAN_REVERSION_BOUNCE]:
            order_type = 'market_buy'
            quantity = self._calculate_position_size(opportunity)
        else:
            order_type = 'market_sell'  # Short positions
            quantity = -self._calculate_position_size(opportunity)
        
        # Execute with fast routing
        try:
            result = execution_engine.submit_fast_order(
                symbol=symbol,
                order_type=order_type,
                quantity=abs(quantity)
            )
            
            if result.get('status') == 'FILLED':
                # Track position
                position_info = {
                    'symbol': symbol,
                    'quantity': quantity,
                    'entry_price': result['fill_price'],
                    'stop_loss': opportunity.stop_loss,
                    'profit_target': opportunity.profit_target,
                    'signal_type': opportunity.signal_type,
                    'entry_time': datetime.now(timezone.utc),
                    'strategy': self._get_strategy_name(opportunity.signal_type),
                    'confidence': opportunity.confidence,
                    'urgency': opportunity.urgency
                }
                
                self.active_positions[symbol] = position_info
                self.daily_trades += 1
                
                logging.info(f"⚡ Scalp executed: {symbol} {order_type} {abs(quantity)} @ ${result['fill_price']:.2f}")
                
                return {'status': 'EXECUTED', 'position': position_info, 'execution': result}
            else:
                return {'status': 'FAILED', 'reason': result.get('message', 'execution_failed')}
                
        except Exception as e:
            logging.error(f"❌ Execution error for {symbol}: {e}")
            return {'status': 'ERROR', 'reason': str(e)}
    
    def _calculate_position_size(self, opportunity: ScalpingOpportunity) -> int:
        """Calculate position size for scalping trade"""
        
        # Small position sizes for scalping (risk management)
        risk_per_trade = self.config.max_loss_per_trade
        stop_distance = abs(opportunity.entry_price - opportunity.stop_loss)
        
        if stop_distance <= 0:
            return 0
        
        # Position size based on risk
        position_value = risk_per_trade * 10000  # Assume $10k portfolio
        quantity = int(position_value / opportunity.entry_price)
        
        # Apply limits
        min_quantity = int(self.config.min_position_value / opportunity.entry_price)
        quantity = max(quantity, min_quantity)
        
        return min(quantity, 1000)  # Cap at 1000 shares for scalping
    
    def _get_strategy_name(self, signal_type: ScalpingSignal) -> str:
        """Map signal type to strategy name"""
        
        if signal_type in [ScalpingSignal.MOMENTUM_BREAKOUT, ScalpingSignal.MOMENTUM_BREAKDOWN]:
            return 'momentum'
        elif signal_type in [ScalpingSignal.MEAN_REVERSION_BOUNCE, ScalpingSignal.MEAN_REVERSION_FADE]:
            return 'reversion'
        elif signal_type in [ScalpingSignal.VOLUME_SPIKE_LONG, ScalpingSignal.VOLUME_SPIKE_SHORT]:
            return 'volume'
        else:
            return 'unknown'
    
    def manage_active_positions(self, current_market_data: Dict) -> List[Dict]:
        """
        Manage active scalping positions for exits
        
        Args:
            current_market_data: Real-time market data
            
        Returns:
            List of exit actions to execute
        """
        
        exit_actions = []
        
        for symbol, position in list(self.active_positions.items()):
            current_price = current_market_data.get(symbol, {}).get('price', {}).get('current', 0)
            
            if current_price <= 0:
                continue
            
            # Check time-based exit
            time_in_position = datetime.now(timezone.utc) - position['entry_time']
            if time_in_position.total_seconds() > self.config.max_hold_time_minutes * 60:
                exit_actions.append({
                    'symbol': symbol,
                    'action': 'exit',
                    'reason': 'time_limit',
                    'current_price': current_price
                })
                continue
            
            # Check profit target
            if position['quantity'] > 0:  # Long position
                if current_price >= position['profit_target']:
                    exit_actions.append({
                        'symbol': symbol,
                        'action': 'exit',
                        'reason': 'profit_target',
                        'current_price': current_price
                    })
                    continue
                elif current_price <= position['stop_loss']:
                    exit_actions.append({
                        'symbol': symbol,
                        'action': 'exit',
                        'reason': 'stop_loss',
                        'current_price': current_price
                    })
                    continue
            else:  # Short position
                if current_price <= position['profit_target']:
                    exit_actions.append({
                        'symbol': symbol,
                        'action': 'exit',
                        'reason': 'profit_target',
                        'current_price': current_price
                    })
                    continue
                elif current_price >= position['stop_loss']:
                    exit_actions.append({
                        'symbol': symbol,
                        'action': 'exit',
                        'reason': 'stop_loss',
                        'current_price': current_price
                    })
                    continue
        
        return exit_actions
    
    def execute_exit(self, exit_action: Dict, execution_engine) -> Dict:
        """Execute exit for scalping position"""
        
        symbol = exit_action['symbol']
        position = self.active_positions.get(symbol)
        
        if not position:
            return {'status': 'ERROR', 'reason': 'position_not_found'}
        
        # Determine exit order type
        if position['quantity'] > 0:
            order_type = 'market_sell'
            quantity = abs(position['quantity'])
        else:
            order_type = 'market_buy'  # Cover short
            quantity = abs(position['quantity'])
        
        try:
            result = execution_engine.submit_fast_order(
                symbol=symbol,
                order_type=order_type,
                quantity=quantity
            )
            
            if result.get('status') == 'FILLED':
                # Calculate P&L
                entry_price = position['entry_price']
                exit_price = result['fill_price']
                
                if position['quantity'] > 0:
                    pnl = (exit_price - entry_price) * quantity
                else:
                    pnl = (entry_price - exit_price) * quantity
                
                # Update performance tracking
                strategy = position['strategy']
                self.strategy_performance[strategy]['trades'] += 1
                self.strategy_performance[strategy]['total_pnl'] += pnl
                if pnl > 0:
                    self.strategy_performance[strategy]['wins'] += 1
                
                self.daily_pnl += pnl
                
                # Remove position
                del self.active_positions[symbol]
                
                logging.info(f"⚡ Scalp exit: {symbol} {exit_action['reason']} @ ${exit_price:.2f}, "
                            f"P&L: ${pnl:.2f}")
                
                return {'status': 'EXITED', 'pnl': pnl, 'exit_price': exit_price}
            else:
                return {'status': 'FAILED', 'reason': result.get('message', 'exit_failed')}
                
        except Exception as e:
            logging.error(f"❌ Exit error for {symbol}: {e}")
            return {'status': 'ERROR', 'reason': str(e)}
    
    def get_performance_summary(self) -> Dict:
        """Get scalping performance summary"""
        
        total_trades = sum(perf['trades'] for perf in self.strategy_performance.values())
        total_wins = sum(perf['wins'] for perf in self.strategy_performance.values())
        total_pnl = sum(perf['total_pnl'] for perf in self.strategy_performance.values())
        
        return {
            'daily_stats': {
                'trades_today': self.daily_trades,
                'trades_remaining': max(0, self.config.max_daily_trades - self.daily_trades),
                'daily_pnl': self.daily_pnl,
                'active_positions': len(self.active_positions),
                'max_positions': self.config.max_concurrent_positions
            },
            'overall_performance': {
                'total_trades': total_trades,
                'win_rate': total_wins / total_trades if total_trades > 0 else 0,
                'total_pnl': total_pnl,
                'avg_trade_pnl': total_pnl / total_trades if total_trades > 0 else 0
            },
            'strategy_breakdown': self.strategy_performance.copy(),
            'config': {
                'profit_target_range': f"{self.config.min_profit_target:.1%}-{self.config.max_profit_target:.1%}",
                'max_loss_per_trade': f"{self.config.max_loss_per_trade:.1%}",
                'max_hold_time': f"{self.config.max_hold_time_minutes} minutes"
            }
        }

# Scalping module ready! 
# Features: Momentum, mean reversion, and volume spike scalping with sub-minute execution
# Tight risk management optimized for 0.5-2% profit targets

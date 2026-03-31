"""
Regime-Based Filter Adjustment Module
Automatically adjusts PreFilter thresholds based on market regime detection and performance feedback
"""

import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json
import os
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class MarketRegime(Enum):
    """Market regime classifications"""
    LOW_VOLATILITY = "low_vol"
    HIGH_VOLATILITY = "high_vol"
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    SIDEWAYS = "sideways"
    BREAKOUT = "breakout"

@dataclass
class RegimeConfig:
    """Configuration for regime-specific filter adjustments"""
    name: str
    vol_spike_min: float
    breakout_min: float
    min_momentum: float
    max_momentum: float
    min_volatility: float
    max_volatility: float
    breakout_window: int
    vol_avg_window: int
    adaptive_steps: int
    description: str

@dataclass
class RegimeMetrics:
    """Metrics for regime detection"""
    avg_volatility: float
    momentum_trend: float
    volume_surge_frequency: float
    breakout_frequency: float
    market_direction: float
    regime: MarketRegime

class RegimeBasedFilterAdjustment:
    """
    Dynamically adjusts PreFilter thresholds based on market regime and performance
    """
    
    def __init__(self, data_loader=None):
        """Initialize regime-based filter adjustment system"""
        self.data_loader = data_loader
        self.current_regime = MarketRegime.SIDEWAYS
        self.regime_history = []
        self.performance_history = []
        self.last_adjustment = None
        
        # Define regime-specific configurations optimized for profitability
        self.regime_configs = {
            MarketRegime.LOW_VOLATILITY: RegimeConfig(
                name="Low Volatility",
                vol_spike_min=0.9,        # More sensitive to small volume increases
                breakout_min=0.003,       # Lower breakout threshold (0.3%)
                min_momentum=0.015,       # Lower momentum requirement
                max_momentum=0.15,
                min_volatility=0.01,      # Accept lower volatility stocks
                max_volatility=0.20,
                breakout_window=15,       # Longer window for pattern detection
                vol_avg_window=15,
                adaptive_steps=6,         # Fewer relaxation steps needed
                description="Optimized for low-volatility environments with subtle signals"
            ),
            
            MarketRegime.HIGH_VOLATILITY: RegimeConfig(
                name="High Volatility", 
                vol_spike_min=1.3,        # Higher threshold to filter noise
                breakout_min=0.008,       # Higher breakout threshold (0.8%)
                min_momentum=0.025,       # Higher momentum requirement
                max_momentum=0.25,
                min_volatility=0.02,
                max_volatility=0.40,      # Accept higher volatility
                breakout_window=10,       # Shorter window for faster signals
                vol_avg_window=10,
                adaptive_steps=8,
                description="Optimized for high-volatility with stricter quality filters"
            ),
            
            MarketRegime.TRENDING_UP: RegimeConfig(
                name="Trending Up",
                vol_spike_min=1.0,
                breakout_min=0.004,       # Relaxed breakout for momentum plays
                min_momentum=0.02,        # Higher momentum bias for trends
                max_momentum=0.30,        # Allow strong momentum
                min_volatility=0.015,
                max_volatility=0.30,
                breakout_window=12,
                vol_avg_window=12,
                adaptive_steps=5,         # Quick adaptation in trends
                description="Optimized for uptrending markets with momentum bias"
            ),
            
            MarketRegime.TRENDING_DOWN: RegimeConfig(
                name="Trending Down",
                vol_spike_min=1.2,        # Higher quality requirements
                breakout_min=0.006,       # More stringent breakouts
                min_momentum=0.03,        # Strong momentum required against trend
                max_momentum=0.20,
                min_volatility=0.02,
                max_volatility=0.25,
                breakout_window=8,        # Shorter window for counter-trend
                vol_avg_window=8,
                adaptive_steps=10,        # More conservative adaptation
                description="Optimized for downtrending markets with defensive stance"
            ),
            
            MarketRegime.SIDEWAYS: RegimeConfig(
                name="Sideways",
                vol_spike_min=1.05,       # Moderate sensitivity
                breakout_min=0.005,       # Standard breakout threshold
                min_momentum=0.02,
                max_momentum=0.20,
                min_volatility=0.015,
                max_volatility=0.30,
                breakout_window=12,
                vol_avg_window=12,
                adaptive_steps=7,
                description="Balanced approach for range-bound markets"
            ),
            
            MarketRegime.BREAKOUT: RegimeConfig(
                name="Breakout",
                vol_spike_min=1.1,
                breakout_min=0.006,       # Focus on confirmed breakouts
                min_momentum=0.025,       # Strong momentum required
                max_momentum=0.35,        # Allow explosive moves
                min_volatility=0.02,
                max_volatility=0.35,
                breakout_window=8,        # Fast detection
                vol_avg_window=8,
                adaptive_steps=4,         # Quick adaptation for breakouts
                description="Optimized for breakout environments with rapid signal detection"
            )
        }
        
        logger.info("🎯 Regime-Based Filter Adjustment initialized")
    
    def detect_market_regime(self, market_data: pd.DataFrame, lookback_days: int = 20) -> RegimeMetrics:
        """
        Detect current market regime based on recent market behavior
        
        Args:
            market_data: DataFrame with OHLCV data for market proxy (SPY/QQQ)
            lookback_days: Days to analyze for regime detection
        """
        try:
            if market_data.empty or len(market_data) < lookback_days:
                logger.warning("Insufficient data for regime detection, defaulting to SIDEWAYS")
                return RegimeMetrics(
                    avg_volatility=0.02,
                    momentum_trend=0.0,
                    volume_surge_frequency=0.1,
                    breakout_frequency=0.05,
                    market_direction=0.0,
                    regime=MarketRegime.SIDEWAYS
                )
            
            # Calculate key metrics for regime detection
            recent_data = market_data.tail(lookback_days).copy()
            
            # 1. Volatility analysis
            recent_data['returns'] = recent_data['close'].pct_change()
            avg_volatility = recent_data['returns'].std() * np.sqrt(252)  # Annualized
            
            # 2. Momentum trend
            momentum_trend = (recent_data['close'].iloc[-1] / recent_data['close'].iloc[0] - 1)
            
            # 3. Volume surge frequency
            recent_data['volume_ma'] = recent_data['volume'].rolling(5).mean()
            volume_surges = (recent_data['volume'] > recent_data['volume_ma'] * 1.2).sum()
            volume_surge_frequency = volume_surges / len(recent_data)
            
            # 4. Breakout frequency (price moves >0.5% in day)
            breakouts = (abs(recent_data['returns']) > 0.005).sum()
            breakout_frequency = breakouts / len(recent_data)
            
            # 5. Market direction trend
            recent_data['sma_5'] = recent_data['close'].rolling(5).mean()
            recent_data['sma_20'] = recent_data['close'].rolling(20).mean()
            market_direction = 1 if recent_data['sma_5'].iloc[-1] > recent_data['sma_20'].iloc[-1] else -1
            
            # Determine regime based on metrics
            regime = self._classify_regime(
                avg_volatility, momentum_trend, volume_surge_frequency, 
                breakout_frequency, market_direction
            )
            
            metrics = RegimeMetrics(
                avg_volatility=avg_volatility,
                momentum_trend=momentum_trend,
                volume_surge_frequency=volume_surge_frequency,
                breakout_frequency=breakout_frequency,
                market_direction=market_direction,
                regime=regime
            )
            
            logger.info(f"📊 Regime Detection: {regime.value} | Vol: {avg_volatility:.3f} | Momentum: {momentum_trend:.3f} | Vol Surge: {volume_surge_frequency:.2f}")
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error in regime detection: {e}")
            # Default to sideways regime on error
            return RegimeMetrics(
                avg_volatility=0.02,
                momentum_trend=0.0,
                volume_surge_frequency=0.1,
                breakout_frequency=0.05,
                market_direction=0.0,
                regime=MarketRegime.SIDEWAYS
            )
    
    def _classify_regime(self, volatility: float, momentum: float, vol_surge_freq: float, 
                        breakout_freq: float, direction: float) -> MarketRegime:
        """Classify market regime based on metrics"""
        
        # High volatility regime
        if volatility > 0.25:
            return MarketRegime.HIGH_VOLATILITY
        
        # Low volatility regime  
        if volatility < 0.15:
            return MarketRegime.LOW_VOLATILITY
        
        # Breakout regime (high breakout frequency + volume surges)
        if breakout_freq > 0.3 and vol_surge_freq > 0.4:
            return MarketRegime.BREAKOUT
        
        # Trending regimes
        if abs(momentum) > 0.05:  # 5% move in lookback period
            if momentum > 0 and direction > 0:
                return MarketRegime.TRENDING_UP
            elif momentum < 0 and direction < 0:
                return MarketRegime.TRENDING_DOWN
        
        # Default to sideways
        return MarketRegime.SIDEWAYS
    
    def get_regime_adjusted_config(self, regime: MarketRegime, performance_feedback: Dict = None) -> Dict:
        """
        Get filter configuration adjusted for current regime and performance
        
        Args:
            regime: Detected market regime
            performance_feedback: Recent performance metrics for fine-tuning
        """
        base_config = self.regime_configs[regime]
        
        # Start with regime base configuration
        config = {
            'vol_spike_min': base_config.vol_spike_min,
            'breakout_min': base_config.breakout_min,
            'min_momentum': base_config.min_momentum,
            'max_momentum': base_config.max_momentum,
            'min_volatility': base_config.min_volatility,
            'max_volatility': base_config.max_volatility,
            'breakout_window': base_config.breakout_window,
            'vol_avg_window': base_config.vol_avg_window,
            'adaptive_steps': base_config.adaptive_steps
        }
        
        # Apply performance-based adjustments
        if performance_feedback:
            config = self._apply_performance_adjustments(config, performance_feedback, regime)
        
        logger.info(f"🎯 Regime Config ({regime.value}): vol_spike={config['vol_spike_min']:.2f}, breakout={config['breakout_min']:.3f}")
        
        return config
    
    def _apply_performance_adjustments(self, config: Dict, performance: Dict, regime: MarketRegime) -> Dict:
        """Apply performance-based fine-tuning to regime config"""
        
        win_rate = performance.get('win_rate', 0.5)
        trade_frequency = performance.get('trade_frequency', 1.0)  # trades per day
        avg_return = performance.get('avg_return', 0.0)
        
        # If win rate is low, relax filters to get more opportunities
        if win_rate < 0.4:
            config['vol_spike_min'] *= 0.9
            config['breakout_min'] *= 0.8
            config['min_momentum'] *= 0.9
            logger.info("📉 Low win rate detected - relaxing filters for more opportunities")
        
        # If trade frequency is too low, relax breakout requirements
        if trade_frequency < 0.5:  # Less than 0.5 trades per day
            config['vol_spike_min'] *= 0.85
            config['breakout_min'] *= 0.7
            logger.info("📊 Low trade frequency - relaxing breakout requirements")
        
        # If average returns are negative, tighten quality filters
        if avg_return < -0.01:  # Losing money on average
            config['vol_spike_min'] *= 1.1
            config['breakout_min'] *= 1.2
            config['min_momentum'] *= 1.1
            logger.info("📈 Negative returns - tightening quality filters")
        
        return config
    
    def update_prefilter_with_regime(self, prefilter, market_data: pd.DataFrame = None, 
                                   performance_feedback: Dict = None) -> Dict:
        """
        Update PreFilter with regime-appropriate settings
        
        Args:
            prefilter: PreFilter instance to update
            market_data: Market data for regime detection
            performance_feedback: Recent performance metrics
        """
        try:
            # Detect current regime
            if market_data is not None and not market_data.empty:
                regime_metrics = self.detect_market_regime(market_data)
                self.current_regime = regime_metrics.regime
            else:
                # Use existing regime or default
                regime_metrics = RegimeMetrics(
                    avg_volatility=0.02, momentum_trend=0.0, volume_surge_frequency=0.1,
                    breakout_frequency=0.05, market_direction=0.0, regime=self.current_regime
                )
            
            # Get regime-adjusted configuration
            regime_config = self.get_regime_adjusted_config(self.current_regime, performance_feedback)
            
            # Store adjustment for tracking
            self.last_adjustment = {
                'timestamp': datetime.now(),
                'regime': self.current_regime.value,
                'config': regime_config.copy(),
                'performance_feedback': performance_feedback
            }
            
            logger.info(f"🔄 PreFilter updated for {self.current_regime.value} regime")
            
            return {
                'regime': self.current_regime,
                'config': regime_config,
                'metrics': regime_metrics
            }
            
        except Exception as e:
            logger.error(f"Error updating prefilter with regime: {e}")
            return {
                'regime': MarketRegime.SIDEWAYS,
                'config': self.regime_configs[MarketRegime.SIDEWAYS].__dict__,
                'metrics': None
            }
    
    def get_adaptive_parameters_for_regime(self, regime: MarketRegime) -> Dict:
        """Get adaptive threshold parameters optimized for specific regime"""
        config = self.regime_configs[regime]
        
        return {
            # Base thresholds
            'vol_spike_min': config.vol_spike_min,
            'breakout_min': config.breakout_min,
            'min_momentum': config.min_momentum,
            'max_momentum': config.max_momentum,
            'min_volatility': config.min_volatility,
            'max_volatility': config.max_volatility,
            
            # Adaptive behavior
            'breakout_window': config.breakout_window,
            'vol_avg_window': config.vol_avg_window,
            'adaptive_steps': config.adaptive_steps,
            
            # Relaxation strategy based on regime
            'relaxation_steps': self._get_regime_relaxation_steps(regime)
        }
    
    def _get_regime_relaxation_steps(self, regime: MarketRegime) -> List[Dict]:
        """Get regime-specific relaxation steps for adaptive filtering"""
        
        base_steps = [
            {"breakout_min": 0.008},
            {"breakout_min": 0.004, "vol_spike_min": 0.95},
            {"min_momentum": 0.015},
            {"min_volatility": 0.01},
            {"min_momentum": 0.01, "vol_spike_min": 0.9}
        ]
        
        if regime == MarketRegime.LOW_VOLATILITY:
            # More aggressive relaxation for low vol environments
            return [
                {"breakout_min": 0.004},
                {"breakout_min": 0.002, "vol_spike_min": 0.8},
                {"min_momentum": 0.01},
                {"min_volatility": 0.005},
                {"vol_spike_min": 0.7}
            ]
        
        elif regime == MarketRegime.HIGH_VOLATILITY:
            # Conservative relaxation for high vol
            return [
                {"breakout_min": 0.010},
                {"breakout_min": 0.008, "vol_spike_min": 1.1},
                {"min_momentum": 0.02},
                {"min_volatility": 0.015},
                {"vol_spike_min": 1.0}
            ]
        
        elif regime == MarketRegime.TRENDING_UP:
            # Momentum-focused relaxation
            return [
                {"min_momentum": 0.015},
                {"breakout_min": 0.003, "vol_spike_min": 0.9},
                {"min_momentum": 0.01},
                {"vol_spike_min": 0.85}
            ]
        
        else:
            return base_steps
    
    def log_regime_performance(self, trades: List[Dict], regime: MarketRegime):
        """Log performance for current regime to improve future adjustments"""
        if not trades:
            return
        
        performance = {
            'regime': regime.value,
            'timestamp': datetime.now(),
            'trade_count': len(trades),
            'win_rate': sum(1 for t in trades if t.get('pnl', 0) > 0) / len(trades),
            'avg_return': np.mean([t.get('return_pct', 0) for t in trades]),
            'total_pnl': sum(t.get('pnl', 0) for t in trades)
        }
        
        self.performance_history.append(performance)
        
        # Keep only last 100 records
        if len(self.performance_history) > 100:
            self.performance_history = self.performance_history[-100:]
        
        logger.info(f"📊 Regime Performance Logged: {regime.value} | Trades: {len(trades)} | Win Rate: {performance['win_rate']:.1%}")
    
    def get_current_regime_info(self) -> Dict:
        """Get current regime information and configuration"""
        return {
            'current_regime': self.current_regime.value,
            'regime_config': self.regime_configs[self.current_regime].__dict__,
            'last_adjustment': self.last_adjustment,
            'performance_summary': self._get_performance_summary()
        }
    
    def _get_performance_summary(self) -> Dict:
        """Get performance summary across regimes"""
        if not self.performance_history:
            return {}
        
        recent_performance = self.performance_history[-10:]  # Last 10 entries
        
        return {
            'recent_win_rate': np.mean([p['win_rate'] for p in recent_performance]),
            'recent_avg_return': np.mean([p['avg_return'] for p in recent_performance]),
            'total_trades': sum(p['trade_count'] for p in recent_performance),
            'regime_distribution': {regime.value: sum(1 for p in recent_performance if p['regime'] == regime.value) 
                                   for regime in MarketRegime}
        }

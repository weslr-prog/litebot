"""
Adaptive Parameter Manager
Dynamically adjusts trading parameters based on market conditions and performance
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple, List, Optional
from datetime import datetime, timedelta
import logging
import pytz


# VIX Cache Configuration
VIX_CACHE_MARKET_HOURS_SECONDS = 900    # 15 minutes during market hours
VIX_CACHE_AFTER_HOURS_SECONDS = 21600   # 6 hours outside market hours


def _is_market_hours() -> bool:
    """Check if currently within market hours (9:30 AM - 4:00 PM ET)"""
    try:
        et_tz = pytz.timezone('US/Eastern')
        now_et = datetime.now(et_tz)
        market_open = now_et.replace(hour=9, minute=30, second=0, microsecond=0)
        market_close = now_et.replace(hour=16, minute=0, second=0, microsecond=0)
        return market_open <= now_et <= market_close and now_et.weekday() < 5
    except Exception:
        return True  # Default to shorter cache if timezone fails


class AdaptiveParameterManager:
    """
    Manages dynamic adjustment of trading parameters based on:
    - Market volatility (VIX proxy via SPY)
    - Recent performance (win rate, consecutive losses)
    - Market regime (trending, ranging, volatile)
    - Time factors (day of week, market conditions)
    """
    
    def __init__(self, config, data_loader=None):
        self.config = config
        self.data_loader = data_loader
        self.logger = logging.getLogger(__name__)
        
        # Performance tracking
        self.trade_history: List[Dict] = []
        self.current_regime = 'normal'
        self.last_regime_update = None
        
        # Cache for market indicators
        self._vix_proxy_cache = None
        self._vix_cache_time = None
        
        self.logger.info("🔧 Adaptive Parameter Manager initialized")
    
    def get_adaptive_parameters(self, symbol: str, market_data: pd.DataFrame) -> Dict:
        """
        Calculate adaptive parameters for a symbol
        
        Args:
            symbol: Stock symbol
            market_data: Recent price data for the symbol
            
        Returns:
            {
                'stop_loss_pct': float,
                'profit_target_pct': float,
                'rsi_entry': int,
                'rsi_exit': int,
                'confidence_threshold': float,
                'exit_time': str
            }
        """
        # Calculate current market conditions
        vix_proxy = self._get_vix_proxy()
        atr_pct = self._calculate_atr_pct(market_data)
        recent_win_rate = self._get_recent_win_rate()
        consecutive_losses = self._get_consecutive_losses()
        market_regime = self._detect_market_regime(market_data)
        
        # Calculate adaptive parameters
        params = {
            'stop_loss_pct': self._adaptive_stop_loss(atr_pct, vix_proxy),
            'profit_target_pct': self._adaptive_profit_target(atr_pct, recent_win_rate),
            'rsi_entry': self._adaptive_rsi_entry(market_regime),
            'rsi_exit': self._adaptive_rsi_exit(market_regime),
            'confidence_threshold': self._adaptive_confidence(recent_win_rate, consecutive_losses),
            'exit_time': self._adaptive_exit_time(vix_proxy, datetime.now())
        }
        
        self.logger.debug(f"{symbol} adaptive params: stop={params['stop_loss_pct']:.3f}, "
                         f"target={params['profit_target_pct']:.3f}, conf={params['confidence_threshold']:.2f}")
        
        return params
    
    def _get_vix_proxy(self) -> float:
        """
        Get VIX proxy from SPY volatility (free alternative to VIX)
        Uses 20-day realized volatility of SPY as VIX approximation
        
        Smart caching:
        - 15 min during market hours (volatility can change quickly)
        - 6 hours outside market hours (use last known value)
        """
        # Dynamic cache duration based on market hours
        cache_seconds = VIX_CACHE_MARKET_HOURS_SECONDS if _is_market_hours() else VIX_CACHE_AFTER_HOURS_SECONDS
        
        if self._vix_cache_time and (datetime.now() - self._vix_cache_time).seconds < cache_seconds:
            if self._vix_proxy_cache is not None:
                return self._vix_proxy_cache
        
        try:
            if self.data_loader:
                spy_data = self.data_loader.get_historical_data('SPY', days=30)
                if spy_data is not None and len(spy_data) >= 20:
                    # Calculate 20-day realized volatility (annualized)
                    returns = spy_data['close'].pct_change().dropna()
                    realized_vol = returns.tail(20).std() * np.sqrt(252) * 100
                    
                    self._vix_proxy_cache = realized_vol
                    self._vix_cache_time = datetime.now()
                    
                    self.logger.debug(f"VIX proxy (SPY 20-day vol): {realized_vol:.1f}")
                    return realized_vol
        except Exception as e:
            self.logger.warning(f"Failed to calculate VIX proxy: {e}")
        
        # Fallback to normal volatility assumption
        return 18.0
    
    def _calculate_atr_pct(self, market_data: pd.DataFrame) -> float:
        """Calculate ATR as percentage of price"""
        if market_data is None or len(market_data) < 14:
            return 0.03  # Default 3%
        
        try:
            # Calculate True Range
            high_low = market_data['high'] - market_data['low']
            high_close = abs(market_data['high'] - market_data['close'].shift(1))
            low_close = abs(market_data['low'] - market_data['close'].shift(1))
            
            true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            atr = true_range.tail(14).mean()
            
            # Convert to percentage
            current_price = market_data['close'].iloc[-1]
            atr_pct = atr / current_price if current_price > 0 else 0.03
            
            return atr_pct
        except Exception as e:
            self.logger.warning(f"Failed to calculate ATR: {e}")
            return 0.03
    
    def _get_recent_win_rate(self, lookback_trades: int = 20) -> float:
        """Calculate win rate from recent trades"""
        if not self.trade_history:
            return 0.56  # Default to strategy baseline
        
        recent = self.trade_history[-lookback_trades:]
        if not recent:
            return 0.56
        
        wins = sum(1 for trade in recent if trade.get('pnl', 0) > 0)
        win_rate = wins / len(recent)
        
        return win_rate
    
    def _get_consecutive_losses(self) -> int:
        """Count consecutive losses"""
        if not self.trade_history:
            return 0
        
        count = 0
        for trade in reversed(self.trade_history):
            if trade.get('pnl', 0) < 0:
                count += 1
            else:
                break
        
        return count
    
    def _detect_market_regime(self, market_data: pd.DataFrame) -> str:
        """
        Detect current market regime for the symbol
        
        Returns:
            'trending_up', 'trending_down', 'ranging', 'volatile', or 'normal'
        """
        if market_data is None or len(market_data) < 20:
            return 'normal'
        
        try:
            # Calculate 20-day SMA
            sma_20 = market_data['close'].rolling(20).mean()
            current_price = market_data['close'].iloc[-1]
            
            # Calculate recent volatility
            returns = market_data['close'].pct_change()
            recent_vol = returns.tail(10).std()
            normal_vol = returns.std()
            
            # Trending detection (price vs SMA)
            if len(sma_20) > 0 and not pd.isna(sma_20.iloc[-1]):
                deviation = (current_price - sma_20.iloc[-1]) / sma_20.iloc[-1]
                
                # Strong uptrend
                if deviation > 0.05:
                    return 'trending_up'
                # Strong downtrend
                elif deviation < -0.05:
                    return 'trending_down'
            
            # Volatile regime (recent vol > 1.5x normal)
            if recent_vol > normal_vol * 1.5:
                return 'volatile'
            
            # Ranging regime (low volatility)
            if recent_vol < normal_vol * 0.7:
                return 'ranging'
            
            return 'normal'
            
        except Exception as e:
            self.logger.warning(f"Failed to detect regime: {e}")
            return 'normal'
    
    def _adaptive_stop_loss(self, atr_pct: float, vix_proxy: float) -> float:
        """
        ATR and VIX-based adaptive stop loss
        
        Formula: stop = ATR × multiplier
        - Low VIX (<15): 1.5× ATR (tighter stops)
        - Normal VIX (15-25): 2.0× ATR
        - High VIX (>25): 2.5× ATR (wider stops)
        
        Bounds: 1.5% - 5.0%
        """
        # Determine multiplier based on VIX
        if vix_proxy < 15:
            multiplier = 1.5
        elif vix_proxy > 25:
            multiplier = 2.5
        else:
            multiplier = 2.0
        
        # Calculate stop
        stop_pct = atr_pct * multiplier
        
        # Apply bounds
        stop_pct = max(0.015, min(stop_pct, 0.05))
        
        return stop_pct
    
    def _adaptive_profit_target(self, atr_pct: float, win_rate: float) -> float:
        """
        ATR and performance-based profit target
        
        Formula: target = ATR × 2.5 × win_rate_adjustment
        - Win rate < 50%: 0.8× (lower targets)
        - Win rate 50-60%: 1.0× (normal)
        - Win rate > 60%: 1.2× (higher targets)
        
        Bounds: 2.0% - 8.0%
        """
        # Base target: 2.5× ATR
        base_target = atr_pct * 2.5
        
        # Win rate adjustment
        if win_rate < 0.50:
            adjustment = 0.8  # Lower targets when struggling
        elif win_rate > 0.60:
            adjustment = 1.2  # Higher targets when hot
        else:
            adjustment = 1.0  # Normal
        
        target_pct = base_target * adjustment
        
        # Apply bounds
        target_pct = max(0.02, min(target_pct, 0.08))
        
        return target_pct
    
    def _adaptive_rsi_entry(self, regime: str) -> int:
        """
        Market regime-based RSI entry threshold
        
        - trending_up: 40 (easier entry in uptrend)
        - trending_down: 25 (harder entry in downtrend)
        - ranging: 25 (more oversold needed)
        - volatile: 30 (normal)
        - normal: 30 (default)
        """
        thresholds = {
            'trending_up': 40,
            'trending_down': 25,
            'ranging': 25,
            'volatile': 30,
            'normal': 30
        }
        return thresholds.get(regime, 30)
    
    def _adaptive_rsi_exit(self, regime: str) -> int:
        """
        Market regime-based RSI exit threshold
        
        - trending_up: 60 (exit earlier in uptrend)
        - trending_down: 75 (hold longer in downtrend)
        - ranging: 75 (more overbought needed)
        - volatile: 65 (exit sooner in volatility)
        - normal: 70 (default)
        """
        thresholds = {
            'trending_up': 60,
            'trending_down': 75,
            'ranging': 75,
            'volatile': 65,
            'normal': 70
        }
        return thresholds.get(regime, 70)
    
    def _adaptive_confidence(self, win_rate: float, consecutive_losses: int) -> float:
        """
        Win rate and drawdown-based confidence threshold
        
        - Win rate < 50%: 0.65 (be more selective)
        - Win rate 50-60%: 0.60 (normal)
        - Win rate > 60%: 0.55 (take more opportunities)
        - Consecutive losses >= 3: +0.05 (tighten up)
        
        Bounds: 0.50 - 0.75
        """
        # Base threshold from win rate
        if win_rate < 0.50:
            base_threshold = 0.65
        elif win_rate > 0.60:
            base_threshold = 0.55
        else:
            base_threshold = 0.60
        
        # Consecutive losses adjustment
        if consecutive_losses >= 3:
            base_threshold += 0.05
        
        # Apply bounds
        threshold = max(0.50, min(base_threshold, 0.75))
        
        return threshold
    
    def _adaptive_exit_time(self, vix_proxy: float, current_date: datetime) -> str:
        """
        VIX and day-based exit time
        
        - Friday: 14:00 (always exit earlier)
        - High VIX (>25): 14:00 (avoid power hour chaos)
        - Low VIX (<15): 15:00 (ride afternoon rally)
        - Normal VIX: 14:30 (current default)
        """
        # Friday always earlier
        if current_date.weekday() == 4:
            return "14:00"
        
        # VIX-based
        if vix_proxy < 15:
            return "15:00"  # Low vol - safe to hold later
        elif vix_proxy > 25:
            return "14:00"  # High vol - exit early
        else:
            return "14:30"  # Normal
    
    def record_trade(self, symbol: str, entry_price: float, exit_price: float, 
                    shares: int, entry_time: datetime, exit_time: datetime):
        """Record a completed trade for performance tracking"""
        pnl = (exit_price - entry_price) * shares
        pnl_pct = (exit_price - entry_price) / entry_price if entry_price > 0 else 0
        
        trade = {
            'symbol': symbol,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'shares': shares,
            'pnl': pnl,
            'pnl_pct': pnl_pct,
            'entry_time': entry_time,
            'exit_time': exit_time,
            'hold_time': (exit_time - entry_time).total_seconds() / 3600  # hours
        }
        
        self.trade_history.append(trade)
        
        # Keep only last 100 trades
        if len(self.trade_history) > 100:
            self.trade_history = self.trade_history[-100:]
        
        self.logger.debug(f"Recorded trade: {symbol} PnL={pnl_pct:.2%}")
    
    def get_performance_summary(self) -> Dict:
        """Get current performance metrics"""
        if not self.trade_history:
            return {
                'total_trades': 0,
                'win_rate': 0.56,
                'avg_win': 0.0,
                'avg_loss': 0.0,
                'profit_factor': 0.0,
                'consecutive_losses': 0
            }
        
        trades = self.trade_history
        wins = [t for t in trades if t['pnl'] > 0]
        losses = [t for t in trades if t['pnl'] < 0]
        
        return {
            'total_trades': len(trades),
            'win_rate': len(wins) / len(trades) if trades else 0.56,
            'avg_win': np.mean([t['pnl_pct'] for t in wins]) if wins else 0.0,
            'avg_loss': np.mean([t['pnl_pct'] for t in losses]) if losses else 0.0,
            'profit_factor': abs(sum(t['pnl'] for t in wins) / sum(t['pnl'] for t in losses)) if losses else 0.0,
            'consecutive_losses': self._get_consecutive_losses()
        }

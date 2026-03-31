"""
Intraday Signal Quality Scorer
Purpose: Score entry signals 0-100 based on multi-timeframe alignment, volume quality, 
         momentum consistency, and statistical quality
Created: November 4, 2025
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
import yfinance as yf

logger = logging.getLogger(__name__)


class IntradayQualityScorer:
    """
    Scores intraday signals on a 0-100 scale using:
    - Multi-timeframe alignment (5m, 15m, 1h, 4h): 0-40 points
    - Volume quality (surge + consistency): 0-30 points
    - Momentum quality (strength + consistency): 0-20 points
    - Statistical quality (clean breakout vs chop): 0-10 points
    
    Tiers:
    - STRONG (75+): High probability, let runners run to +5%
    - MEDIUM (55-74): Standard probability, target +3.5%
    - WEAK (<55): Lower probability, scalp for +2%
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__ + ".IntradayQualityScorer")
        
        # Scoring thresholds
        self.STRONG_THRESHOLD = 75
        self.MEDIUM_THRESHOLD = 55
        
        # Multi-timeframe parameters
        self.timeframes = {
            '5m': {'period': '5d', 'interval': '5m', 'lookback': 12},   # 1 hour
            '15m': {'period': '5d', 'interval': '15m', 'lookback': 16},  # 4 hours
            '1h': {'period': '1mo', 'interval': '1h', 'lookback': 24},   # 1 day
            '4h': {'period': '3mo', 'interval': '1d', 'lookback': 20}    # Proxy with daily
        }
        
        # Volume parameters
        self.volume_surge_strong = 2.0      # 2x average = strong
        self.volume_surge_medium = 1.5      # 1.5x average = medium
        self.volume_consistency_high = 0.7  # 70%+ bars above avg
        
        # Momentum parameters
        self.momentum_lookback = 10
        self.momentum_strong = 0.005        # 0.5% average return
        self.momentum_consistency_high = 0.8  # 80%+ positive bars
        
        # Cache for efficiency
        self.cache = {}
        self.cache_expiry = timedelta(minutes=5)
    
    def score_signal(self, symbol: str, current_data: pd.DataFrame, 
                     current_price: float) -> Dict:
        """
        Score a signal for the given symbol
        
        Args:
            symbol: Stock symbol
            current_data: Recent price/volume data (at least 20 bars)
            current_price: Current price for the symbol
            
        Returns:
            Dict with:
                - total_score (0-100)
                - quality_tier ('STRONG', 'MEDIUM', 'WEAK')
                - component_scores (breakdown)
                - reasoning (explanation)
        """
        try:
            # Component scores
            mtf_score = self._score_multi_timeframe(symbol, current_price)
            volume_score = self._score_volume_quality(current_data)
            momentum_score = self._score_momentum_quality(current_data)
            statistical_score = self._score_statistical_quality(current_data)
            
            # Total score
            total_score = mtf_score + volume_score + momentum_score + statistical_score
            total_score = min(total_score, 100)  # Cap at 100
            
            # Determine quality tier
            if total_score >= self.STRONG_THRESHOLD:
                quality_tier = "STRONG"
            elif total_score >= self.MEDIUM_THRESHOLD:
                quality_tier = "MEDIUM"
            else:
                quality_tier = "WEAK"
            
            # Generate reasoning
            reasoning = self._generate_reasoning(
                mtf_score, volume_score, momentum_score, statistical_score, quality_tier
            )
            
            result = {
                'total_score': total_score,
                'quality_tier': quality_tier,
                'component_scores': {
                    'multi_timeframe': mtf_score,
                    'volume_quality': volume_score,
                    'momentum_quality': momentum_score,
                    'statistical_quality': statistical_score
                },
                'reasoning': reasoning
            }
            
            self.logger.info(
                f"📊 {symbol} Quality Score: {total_score:.0f}/100 ({quality_tier}) - "
                f"MTF:{mtf_score:.0f} Vol:{volume_score:.0f} Mom:{momentum_score:.0f} Stat:{statistical_score:.0f}"
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error scoring {symbol}: {e}")
            return {
                'total_score': 0,
                'quality_tier': 'WEAK',
                'component_scores': {},
                'reasoning': f"Error: {e}"
            }
    
    def _score_multi_timeframe(self, symbol: str, current_price: float) -> float:
        """
        Score multi-timeframe alignment (0-40 points)
        
        Checks if momentum is aligned across 5m, 15m, 1h, 4h timeframes
        - All 4 aligned = 40 points
        - 3 aligned = 30 points
        - 2 aligned = 15 points
        - 1 or 0 = 5 points
        """
        try:
            aligned_count = 0
            timeframe_results = {}
            
            for tf_name, tf_params in self.timeframes.items():
                is_bullish = self._check_timeframe_bullish(
                    symbol, tf_params['period'], tf_params['interval'], 
                    tf_params['lookback']
                )
                timeframe_results[tf_name] = is_bullish
                if is_bullish:
                    aligned_count += 1
            
            # Score based on alignment
            if aligned_count == 4:
                score = 40
            elif aligned_count == 3:
                score = 30
            elif aligned_count == 2:
                score = 15
            else:
                score = 5
            
            self.logger.debug(
                f"  MTF Alignment: {aligned_count}/4 timeframes = {score} pts "
                f"({timeframe_results})"
            )
            
            return score
            
        except Exception as e:
            self.logger.warning(f"MTF scoring error for {symbol}: {e}")
            return 5  # Default low score
    
    def _check_timeframe_bullish(self, symbol: str, period: str, 
                                  interval: str, lookback: int) -> bool:
        """Check if a specific timeframe shows bullish momentum"""
        try:
            # Check cache first
            cache_key = f"{symbol}_{interval}"
            if cache_key in self.cache:
                cached_time, cached_result = self.cache[cache_key]
                if datetime.now() - cached_time < self.cache_expiry:
                    return cached_result
            
            # Fetch data
            df = yf.download(symbol, period=period, interval=interval, 
                           progress=False)
            
            if df is None or len(df) < lookback:
                return False
            
            # Check for bullish momentum
            recent_data = df.tail(lookback)
            returns = recent_data['Close'].pct_change().dropna()
            
            # Bullish criteria:
            # 1. Average return > 0
            # 2. Most recent return > 0
            # 3. Majority of periods positive
            avg_return = returns.mean()
            latest_return = returns.iloc[-1] if len(returns) > 0 else 0
            positive_pct = (returns > 0).sum() / len(returns) if len(returns) > 0 else 0
            
            is_bullish = (avg_return > 0 and latest_return > 0 and positive_pct > 0.5)
            
            # Cache result
            self.cache[cache_key] = (datetime.now(), is_bullish)
            
            return is_bullish
            
        except Exception as e:
            self.logger.debug(f"Error checking {interval} timeframe for {symbol}: {e}")
            return False
    
    def _score_volume_quality(self, data: pd.DataFrame) -> float:
        """
        Score volume quality (0-30 points)
        
        Checks:
        - Volume surge (current vs 20-day average)
        - Volume consistency (% of bars above average)
        
        30 pts: 2x surge + 70%+ consistency
        20 pts: 1.5x surge + moderate consistency
        10 pts: Some volume, but weak
        """
        try:
            if 'volume' not in data.columns or len(data) < 20:
                return 10  # Default medium score
            
            # Calculate volume metrics
            current_volume = data['volume'].iloc[-1]
            avg_volume = data['volume'].tail(20).mean()
            volume_surge = current_volume / avg_volume if avg_volume > 0 else 1.0
            
            # Volume consistency (% bars above average)
            above_avg = (data['volume'].tail(20) > avg_volume).sum()
            consistency = above_avg / 20.0
            
            # Score based on surge + consistency
            if volume_surge >= self.volume_surge_strong and consistency >= self.volume_consistency_high:
                score = 30
            elif volume_surge >= self.volume_surge_medium:
                score = 20
            elif volume_surge >= 1.0:
                score = 10
            else:
                score = 5  # Below average volume
            
            self.logger.debug(
                f"  Volume Quality: {volume_surge:.2f}x surge, {consistency:.0%} consistency = {score} pts"
            )
            
            return score
            
        except Exception as e:
            self.logger.warning(f"Volume scoring error: {e}")
            return 10
    
    def _score_momentum_quality(self, data: pd.DataFrame) -> float:
        """
        Score momentum quality (0-20 points)
        
        Checks:
        - Momentum strength (average return over lookback)
        - Momentum consistency (% positive bars)
        
        20 pts: Strong momentum (0.5%+) + 80%+ consistency
        15 pts: Good momentum + moderate consistency
        10 pts: Positive momentum, but inconsistent
        5 pts: Weak or negative momentum
        """
        try:
            if len(data) < self.momentum_lookback:
                return 10
            
            # Calculate momentum metrics
            returns = data['close'].pct_change().tail(self.momentum_lookback)
            avg_return = returns.mean()
            positive_bars = (returns > 0).sum()
            consistency = positive_bars / len(returns)
            
            # Score based on strength + consistency
            if avg_return >= self.momentum_strong and consistency >= self.momentum_consistency_high:
                score = 20
            elif avg_return >= self.momentum_strong * 0.5 and consistency >= 0.6:
                score = 15
            elif avg_return > 0:
                score = 10
            else:
                score = 5
            
            self.logger.debug(
                f"  Momentum Quality: {avg_return:.3%} avg return, {consistency:.0%} positive = {score} pts"
            )
            
            return score
            
        except Exception as e:
            self.logger.warning(f"Momentum scoring error: {e}")
            return 10
    
    def _score_statistical_quality(self, data: pd.DataFrame) -> float:
        """
        Score statistical quality (0-10 points)
        
        Checks for clean breakout vs choppy action using ATR ratio
        - Expanding volatility (ATR increasing) = clean move
        - Contracting volatility = choppy/indecisive
        
        10 pts: ATR ratio > 1.2 (expanding volatility)
        5 pts: ATR ratio > 1.0 (stable)
        0 pts: ATR ratio <= 1.0 (contracting)
        """
        try:
            if len(data) < 20:
                return 5
            
            # Calculate ATR ratio (recent vs average)
            high_low = data['high'] - data['low']
            atr_recent = high_low.tail(5).mean()
            atr_avg = high_low.tail(20).mean()
            atr_ratio = atr_recent / atr_avg if atr_avg > 0 else 1.0
            
            # Score based on ATR expansion
            if atr_ratio > 1.2:
                score = 10  # Expanding volatility = clean move
            elif atr_ratio > 1.0:
                score = 5   # Stable volatility
            else:
                score = 0   # Contracting volatility = chop
            
            self.logger.debug(
                f"  Statistical Quality: ATR ratio {atr_ratio:.2f} = {score} pts"
            )
            
            return score
            
        except Exception as e:
            self.logger.warning(f"Statistical scoring error: {e}")
            return 5
    
    def _generate_reasoning(self, mtf: float, volume: float, momentum: float, 
                           statistical: float, tier: str) -> str:
        """Generate human-readable reasoning for the score"""
        reasons = []
        
        # Multi-timeframe
        if mtf >= 30:
            reasons.append("strong multi-timeframe alignment")
        elif mtf >= 15:
            reasons.append("partial timeframe alignment")
        else:
            reasons.append("weak timeframe alignment")
        
        # Volume
        if volume >= 20:
            reasons.append("high volume surge")
        elif volume >= 10:
            reasons.append("moderate volume")
        else:
            reasons.append("low volume")
        
        # Momentum
        if momentum >= 15:
            reasons.append("consistent momentum")
        elif momentum >= 10:
            reasons.append("positive momentum")
        else:
            reasons.append("weak momentum")
        
        # Statistical
        if statistical >= 8:
            reasons.append("clean breakout pattern")
        elif statistical >= 4:
            reasons.append("stable volatility")
        else:
            reasons.append("choppy action")
        
        return f"{tier} signal: " + ", ".join(reasons)
    
    def clear_cache(self):
        """Clear the cache (call this at market close)"""
        self.cache.clear()
        self.logger.info("Quality scorer cache cleared")


# Quick test
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    scorer = IntradayQualityScorer()
    
    # Test with sample data
    print("\n🧪 Testing IntradayQualityScorer...\n")
    
    # Generate sample data
    dates = pd.date_range(end=datetime.now(), periods=50, freq='1min')
    sample_data = pd.DataFrame({
        'close': np.random.randn(50).cumsum() + 100,
        'high': np.random.randn(50).cumsum() + 101,
        'low': np.random.randn(50).cumsum() + 99,
        'volume': np.random.randint(100000, 500000, 50)
    }, index=dates)
    
    result = scorer.score_signal("TEST", sample_data, 100.0)
    
    print(f"\n✅ Quality Score: {result['total_score']:.0f}/100")
    print(f"✅ Quality Tier: {result['quality_tier']}")
    print(f"✅ Reasoning: {result['reasoning']}")
    print(f"\n✅ Component Breakdown:")
    for component, score in result['component_scores'].items():
        print(f"   - {component}: {score:.0f} pts")
    
    print("\n✅ IntradayQualityScorer test complete!")

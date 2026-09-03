#!/usr/bin/env python3
"""
Enhanced Risk-Adjusted Momentum Calculator
Implements regime-aware, risk-adjusted momentum scoring for superior stock selection

Key Features:
- Risk-adjusted momentum (Sharpe-based scoring)
- Regime-specific momentum weightings
- Multiple momentum timeframes
- Volatility-adjusted returns
- Quality momentum filters
"""

import numpy as np
import pandas as pd
import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass 
class MomentumConfig:
    """Enhanced configuration for aggressive swing trading momentum"""
    # Aggressive swing trading periods
    short_period: int = 10           # 10-day short-term (was 5)
    medium_period: int = 21          # 21-day medium-term 
    long_period: int = 63            # 63-day long-term (was 42)
    
    # Volatility and risk parameters
    volatility_lookback: int = 21
    min_sharpe_threshold: float = -0.5   # More lenient for momentum (was 0.0)
    
    # Quality filters for aggressive swing trading
    min_volume: float = 5_000_000        # Higher volume for liquid swing trades
    min_price: float = 20.0              # Higher minimum for quality (was 5.0)
    max_price: float = 750.0
    max_volatility: float = 2.0          # Allow higher volatility stocks (was 1.0)
    
    # NEW: Breakout detection parameters
    breakout_volume_multiplier: float = 2.0    # 2x average volume for breakouts
    breakout_momentum_threshold: float = 0.15   # 15% momentum for breakout classification
    price_consolidation_days: int = 10          # Days to check for consolidation breakout
    relative_strength_threshold: float = 1.2   # 20% outperformance vs market


class EnhancedMomentumCalculator:
    """
    Risk-adjusted momentum calculator with regime awareness
    
    Momentum Quality Hierarchy:
    1. Risk-Adjusted Return (Sharpe ratio over period)
    2. Consistency Score (low volatility of returns)
    3. Trend Strength (R-squared of price trend)
    4. Volume Confirmation (momentum + volume surge)
    """
    
    def __init__(self, config: Optional[MomentumConfig] = None):
        self.config = config or MomentumConfig()
        self.regime_weights = self._get_regime_momentum_weights()
        
        logging.info("📊 Enhanced Risk-Adjusted Momentum Calculator initialized")
        logging.info(f"   Periods: {self.config.short_period}/{self.config.medium_period}/{self.config.long_period}d")
        logging.info(f"   Risk Adj: {self.config.volatility_lookback}d volatility, {self.config.min_sharpe_threshold:.1f} min Sharpe")
    
    def _get_regime_momentum_weights(self) -> Dict[str, Dict[str, float]]:
        """Get momentum period weightings optimized for each regime"""
        return {
            # Bull markets: favor shorter-term momentum (trend acceleration)
            'UP_LOWVOL': {
                'short': 0.5,    # 50% - catch acceleration  
                'medium': 0.35,  # 35% - confirm trend
                'long': 0.15     # 15% - background trend
            },
            'bull': {
                'short': 0.45,
                'medium': 0.4,
                'long': 0.15
            },
            
            # Volatile uptrends: balance short and medium term
            'UP_HIGHVOL': {
                'short': 0.3,    # 30% - reduce noise sensitivity
                'medium': 0.45,  # 45% - main signal
                'long': 0.25     # 25% - stability check
            },
            'volatile': {
                'short': 0.25,
                'medium': 0.45,
                'long': 0.3
            },
            
            # Sideways: favor longer-term for breakouts
            'sideways': {
                'short': 0.2,    # 20% - minimize whipsaws
                'medium': 0.4,   # 40% - trend development
                'long': 0.4      # 40% - strong foundation
            },
            
            # Bear markets: heavy emphasis on long-term momentum
            'bear': {
                'short': 0.1,    # 10% - avoid dead cat bounces
                'medium': 0.25,  # 25% - trend confirmation
                'long': 0.65     # 65% - only strong reversals
            },
            'DOWN_LOWVOL': {
                'short': 0.15,
                'medium': 0.3,
                'long': 0.55
            },
            'DOWN_HIGHVOL': {
                'short': 0.05,   # 5% - almost ignore short-term
                'medium': 0.2,   # 20% - minimal medium-term
                'long': 0.75     # 75% - only major reversals
            }
        }
    
    def detect_breakout_pattern(self, prices: pd.Series, volumes: pd.Series) -> Dict[str, any]:
        """
        Detect breakout patterns for aggressive swing trading
        
        Returns:
            Dict with is_breakout, breakout_type, volume_surge, consolidation_break
        """
        try:
            if len(prices) < self.config.price_consolidation_days + 5:
                return {'is_breakout': False, 'reason': 'Insufficient data'}
            
            current_price = prices.iloc[-1]
            recent_prices = prices.iloc[-self.config.price_consolidation_days:]
            recent_volumes = volumes.iloc[-5:] if len(volumes) >= 5 else volumes
            avg_volume = volumes.iloc[-21:].mean() if len(volumes) >= 21 else volumes.mean()
            
            # 1. Volume surge detection
            current_volume = volumes.iloc[-1] if len(volumes) > 0 else 0
            volume_surge = current_volume > (avg_volume * self.config.breakout_volume_multiplier)
            
            # 2. Consolidation breakout
            consolidation_high = recent_prices.max()
            consolidation_low = recent_prices.min()
            consolidation_range = (consolidation_high - consolidation_low) / consolidation_low
            
            # Tight consolidation = less than 8% range
            tight_consolidation = consolidation_range < 0.08
            breakout_above_resistance = current_price > consolidation_high * 1.02  # 2% above high
            
            # 3. Momentum strength
            momentum_5d = (current_price / prices.iloc[-6]) - 1 if len(prices) >= 6 else 0
            strong_momentum = momentum_5d > self.config.breakout_momentum_threshold
            
            # 4. Price pattern confirmation
            recent_close_above_ma = current_price > recent_prices.mean()
            
            # Determine breakout type
            breakout_signals = 0
            breakout_type = "none"
            
            if volume_surge:
                breakout_signals += 1
            if tight_consolidation and breakout_above_resistance:
                breakout_signals += 2  # Weight consolidation breaks more heavily
            if strong_momentum:
                breakout_signals += 1
            if recent_close_above_ma:
                breakout_signals += 1
            
            # Classify breakout strength
            is_breakout = breakout_signals >= 3
            if breakout_signals >= 4:
                breakout_type = "strong_breakout"
            elif breakout_signals == 3:
                breakout_type = "moderate_breakout"
            
            return {
                'is_breakout': is_breakout,
                'breakout_type': breakout_type,
                'breakout_score': breakout_signals,
                'volume_surge': volume_surge,
                'volume_ratio': current_volume / avg_volume if avg_volume > 0 else 0,
                'consolidation_break': tight_consolidation and breakout_above_resistance,
                'momentum_strength': momentum_5d,
                'price_above_ma': recent_close_above_ma,
                'consolidation_range_pct': consolidation_range
            }
            
        except Exception as e:
            logging.warning(f"Error detecting breakout pattern: {e}")
            return {'is_breakout': False, 'reason': 'Error in breakout detection'}
    
    def calculate_relative_strength(self, prices: pd.Series, market_prices: pd.Series = None) -> float:
        """Calculate relative strength vs market for swing trading"""
        try:
            if market_prices is None or len(prices) < 21 or len(market_prices) < 21:
                return 1.0  # Neutral if no market data
            
            # 21-day relative performance
            stock_return = (prices.iloc[-1] / prices.iloc[-21]) - 1
            market_return = (market_prices.iloc[-1] / market_prices.iloc[-21]) - 1
            
            relative_strength = (1 + stock_return) / (1 + market_return)
            return relative_strength
            
        except Exception as e:
            logging.warning(f"Error calculating relative strength: {e}")
            return 1.0
        """
        Calculate comprehensive risk-adjusted momentum score
        
        Returns:
            Dict with momentum components and final score
        """
        if len(price_data) < self.config.long_period:
            return {'score': np.nan, 'quality': 'insufficient_data'}
        
        try:
            prices = price_data['close']
            
            # 1. Calculate raw returns for different periods
            returns = self._calculate_period_returns(prices)
            
            # 2. Calculate risk-adjusted returns (Sharpe ratios)
            risk_adjusted = self._calculate_risk_adjusted_returns(prices, returns)
            
            # 3. Calculate trend quality metrics
            quality_metrics = self._calculate_trend_quality(prices)
            
            # 4. Volume confirmation (if available)
            volume_confirmation = self._calculate_volume_confirmation(
                prices, volume_data
            ) if volume_data is not None else 1.0
            
            # 5. Apply regime-specific weightings
            weighted_score = self._apply_regime_weighting(
                risk_adjusted, regime
            )
            
            # 6. Apply quality adjustments
            final_score = weighted_score * quality_metrics['quality_multiplier'] * volume_confirmation
            
            # 7. Determine momentum quality
            quality_rating = self._rate_momentum_quality(
                risk_adjusted, quality_metrics, volume_confirmation
            )
            
            return {
                'score': final_score,
                'quality': quality_rating,
                'components': {
                    'raw_returns': returns,
                    'risk_adjusted': risk_adjusted,
                    'quality_metrics': quality_metrics,
                    'volume_confirmation': volume_confirmation,
                    'regime_weighted': weighted_score
                },
                'regime': regime
            }
            
        except Exception as e:
            logging.warning(f"Error calculating risk-adjusted momentum: {e}")
            return {'score': np.nan, 'quality': 'error'}
    
    def _calculate_period_returns(self, prices: pd.Series) -> Dict[str, float]:
        """Calculate returns for different momentum periods"""
        current_price = prices.iloc[-1]
        
        returns = {}
        for period_name, days in [
            ('short', self.config.short_period),
            ('medium', self.config.medium_period), 
            ('long', self.config.long_period)
        ]:
            if len(prices) >= days:
                past_price = prices.iloc[-days]
                returns[period_name] = (current_price / past_price) - 1
            else:
                returns[period_name] = np.nan
                
    def _apply_aggressive_regime_weighting(self, risk_adjusted: Dict, quality_metrics: Dict, 
                                          volume_confirmation: Dict, breakout_analysis: Dict,
                                          relative_strength: float, regime: str) -> Dict[str, float]:
        """Apply aggressive regime weighting for swing trading"""
        weights = self._get_aggressive_regime_weights(regime)
        
        # Base weighted score
        weighted = {}
        for period in ['short', 'medium', 'long']:
            if period in risk_adjusted and not np.isnan(risk_adjusted[period]):
                weighted[period] = risk_adjusted[period] * weights[period]
            else:
                weighted[period] = 0
        
        # Breakout boost
        if breakout_analysis.get('is_breakout', False):
            breakout_multiplier = 1.5 if breakout_analysis.get('breakout_type') == 'strong_breakout' else 1.2
            for period in weighted:
                weighted[period] *= breakout_multiplier
        
        # Relative strength boost
        if relative_strength > self.config.relative_strength_threshold:
            rs_multiplier = min(1.3, relative_strength)  # Cap at 30% boost
            for period in weighted:
                weighted[period] *= rs_multiplier
        
        return weighted
    
    def _get_aggressive_regime_weights(self, regime: str) -> Dict[str, float]:
        """Get aggressive weighting for different regimes optimized for swing trading"""
        regime_weights = {
            'bull_trending': {'short': 0.2, 'medium': 0.3, 'long': 0.5},     # Favor longer momentum
            'bear_trending': {'short': 0.4, 'medium': 0.4, 'long': 0.2},     # Shorter timeframes
            'high_volatility': {'short': 0.5, 'medium': 0.3, 'long': 0.2},   # Quick moves
            'low_volatility': {'short': 0.1, 'medium': 0.4, 'long': 0.5},    # Patient approach
            'sideways': {'short': 0.6, 'medium': 0.3, 'long': 0.1},          # Breakout focus
            'breakout': {'short': 0.4, 'medium': 0.4, 'long': 0.2},          # Balanced for breakouts
            'breakdown': {'short': 0.2, 'medium': 0.3, 'long': 0.5},         # Avoid false breakdowns
            'recovery': {'short': 0.3, 'medium': 0.4, 'long': 0.3}           # Balanced recovery
        }
        return regime_weights.get(regime, {'short': 0.3, 'medium': 0.4, 'long': 0.3})
    
    def _calculate_aggressive_final_score(self, weighted_score: Dict, quality_metrics: Dict,
                                        breakout_analysis: Dict, relative_strength: float) -> Tuple[float, str]:
        """Calculate final aggressive momentum score for swing trading"""
        # Base momentum score
        valid_scores = [score for score in weighted_score.values() if not np.isnan(score)]
        if not valid_scores:
            return np.nan, 'no_valid_data'
        
        base_score = np.mean(valid_scores)
        
        # Quality adjustments for swing trading
        quality_multiplier = 1.0
        
        # Trend strength boost (important for swing trades)
        if quality_metrics.get('trend_strength', 0) > 0.7:
            quality_multiplier *= 1.2
        
        # Consistency boost (but less important than trend strength)
        if quality_metrics.get('consistency_score', 0) > 0.6:
            quality_multiplier *= 1.1
        
        # Volume confirmation (critical for breakouts)
        if quality_metrics.get('volume_trend', 0) > 0.5:
            quality_multiplier *= 1.15
        
        # Breakout premium (major boost for swing trading)
        if breakout_analysis.get('is_breakout', False):
            if breakout_analysis.get('breakout_type') == 'strong_breakout':
                quality_multiplier *= 1.4  # 40% boost for strong breakouts
            else:
                quality_multiplier *= 1.2  # 20% boost for moderate breakouts
        
        # Relative strength premium
        if relative_strength > self.config.relative_strength_threshold:
            quality_multiplier *= min(1.2, relative_strength * 0.8)
        
        final_score = base_score * quality_multiplier
        
        # Determine quality rating for swing trading
        if breakout_analysis.get('is_breakout') and final_score > 0.6:
            quality = 'breakout_candidate'
        elif final_score > 0.8:
            quality = 'excellent'
        elif final_score > 0.6:
            quality = 'good'
        elif final_score > 0.4:
            quality = 'moderate'
        elif final_score > 0.2:
            quality = 'weak'
        else:
            quality = 'poor'
        
        return final_score, quality
    
    def _calculate_risk_adjusted_returns(self, prices: pd.Series, 
                                       returns: Dict[str, float]) -> Dict[str, float]:
        """Calculate Sharpe-like ratios for each momentum period"""
        risk_adjusted = {}
        
        for period_name, period_return in returns.items():
            if np.isnan(period_return):
                risk_adjusted[period_name] = np.nan
                continue
                
            # Get period length
            period_days = getattr(self.config, f"{period_name}_period")
            
            if len(prices) < period_days:
                risk_adjusted[period_name] = np.nan
                continue
            
            # Calculate volatility over the period
            period_prices = prices.iloc[-period_days:]
            period_returns = period_prices.pct_change().dropna()
            
            if len(period_returns) < 5:  # Need minimum returns for volatility
                risk_adjusted[period_name] = np.nan
                continue
                
            # Annualized volatility
            volatility = period_returns.std() * np.sqrt(252)
            
            if volatility == 0:
                risk_adjusted[period_name] = 0
            else:
                # Risk-adjusted return (Sharpe-like, assuming 0% risk-free rate)
                annualized_return = period_return * (252 / period_days)
                risk_adjusted[period_name] = annualized_return / volatility
                
        return risk_adjusted
    
    def _calculate_trend_quality(self, prices: pd.Series) -> Dict:
        """Calculate trend strength and consistency metrics"""
        try:
            # Use medium period for trend quality
            period_prices = prices.iloc[-self.config.medium_period:]
            
            if len(period_prices) < 10:
                return {'quality_multiplier': 1.0, 'trend_strength': 0}
            
            # R-squared of price trend (how linear is the trend)
            x = np.arange(len(period_prices))
            correlation_matrix = np.corrcoef(x, period_prices)
            r_squared = correlation_matrix[0, 1] ** 2
            
            # Volatility of returns (consistency)
            returns = period_prices.pct_change().dropna()
            return_volatility = returns.std()
            
            # Quality multiplier based on trend strength and consistency
            trend_quality = r_squared  # 0 to 1
            consistency_quality = max(0, 1 - (return_volatility * 10))  # Penalty for high volatility
            
            quality_multiplier = 0.7 + 0.3 * (trend_quality * consistency_quality)
            
            return {
                'quality_multiplier': quality_multiplier,
                'trend_strength': r_squared,
                'consistency': consistency_quality
            }
            
        except Exception as e:
            logging.warning(f"Error calculating trend quality: {e}")
            return {'quality_multiplier': 1.0, 'trend_strength': 0}
    
    def _calculate_volume_confirmation(self, prices: pd.Series, 
                                     volume_data: pd.DataFrame) -> float:
        """Calculate volume confirmation of momentum"""
        try:
            if volume_data is None or volume_data.empty:
                return 1.0
            
            volumes = volume_data['volume'].iloc[-self.config.medium_period:]
            period_prices = prices.iloc[-self.config.medium_period:]
            
            if len(volumes) < 10 or len(period_prices) < 10:
                return 1.0
            
            # Volume trend
            volume_trend = np.corrcoef(np.arange(len(volumes)), volumes)[0, 1]
            
            # Price-volume correlation
            price_volume_corr = np.corrcoef(period_prices, volumes)[0, 1]
            
            # Volume surge (recent vs historical average)
            recent_volume = volumes.iloc[-5:].mean()
            avg_volume = volumes.mean()
            volume_surge = recent_volume / avg_volume if avg_volume > 0 else 1
            
            # Confirmation score (1.0 = neutral, >1.0 = positive confirmation)
            confirmation = 1.0 + 0.1 * volume_trend + 0.1 * abs(price_volume_corr) + 0.05 * (volume_surge - 1)
            
            return min(1.5, max(0.8, confirmation))  # Cap between 0.8 and 1.5
            
        except Exception as e:
            logging.warning(f"Error calculating volume confirmation: {e}")
            return 1.0
    
    def _apply_regime_weighting(self, risk_adjusted: Dict[str, float], 
                              regime: str) -> float:
        """Apply regime-specific weightings to momentum periods"""
        weights = self.regime_weights.get(regime, self.regime_weights['sideways'])
        
        weighted_sum = 0
        total_weight = 0
        
        for period, weight in weights.items():
            ra_score = risk_adjusted.get(period, np.nan)
            if not np.isnan(ra_score):
                weighted_sum += weight * ra_score
                total_weight += weight
        
        if total_weight == 0:
            return 0
            
        return weighted_sum / total_weight
    
    def _rate_momentum_quality(self, risk_adjusted: Dict, 
                             quality_metrics: Dict, 
                             volume_confirmation: float) -> str:
        """Rate the overall quality of the momentum signal"""
        
        # Average risk-adjusted score
        valid_scores = [score for score in risk_adjusted.values() if not np.isnan(score)]
        if not valid_scores:
            return 'poor'
            
        avg_sharpe = np.mean(valid_scores)
        trend_strength = quality_metrics.get('trend_strength', 0)
        consistency = quality_metrics.get('consistency', 0)
        
        # Quality scoring
        if (avg_sharpe > 1.0 and trend_strength > 0.8 and 
            consistency > 0.7 and volume_confirmation > 1.1):
            return 'excellent'
        elif (avg_sharpe > 0.5 and trend_strength > 0.6 and 
              consistency > 0.5 and volume_confirmation > 1.0):
            return 'good'
        elif avg_sharpe > 0.2 and trend_strength > 0.3:
            return 'fair'
        else:
            return 'poor'
    
    def rank_stocks_by_momentum_quality(self, stock_data: Dict[str, pd.DataFrame],
                                      regime: str = 'sideways',
                                      max_selections: int = 20) -> List[Dict]:
        """
        Rank stocks by risk-adjusted momentum quality
        
        Returns:
            List of stocks ranked by momentum quality
        """
        momentum_scores = []
        
        for symbol, data in stock_data.items():
            if data.empty or len(data) < self.config.long_period:
                continue
                
            # Calculate momentum score
            momentum_result = self.calculate_risk_adjusted_momentum(
                data, regime=regime
            )
            
            if not np.isnan(momentum_result['score']):
                momentum_scores.append({
                    'symbol': symbol,
                    'momentum_score': momentum_result['score'],
                    'quality': momentum_result['quality'],
                    'components': momentum_result['components'],
                    'regime': regime
                })
        
        # Sort by momentum score (descending)
        momentum_scores.sort(key=lambda x: x['momentum_score'], reverse=True)
        
        # Filter by quality and return top selections
        quality_filtered = [
            stock for stock in momentum_scores 
            if stock['quality'] in ['excellent', 'good', 'fair']
        ]
        
        return quality_filtered[:max_selections]


# Testing and demonstration
if __name__ == "__main__":
    # Test the enhanced momentum calculator
    import matplotlib.pyplot as plt
    
    calculator = EnhancedMomentumCalculator()
    
    # Create test data - trending stock
    dates = pd.date_range('2025-01-01', periods=100, freq='D')
    trend_prices = np.cumsum(np.random.normal(0.01, 0.02, 100)) + 100
    
    test_data = pd.DataFrame({
        'close': trend_prices,
        'volume': np.random.normal(1000000, 200000, 100)
    })
    
    # Test different regimes
    regimes = ['UP_LOWVOL', 'bull', 'volatile', 'sideways', 'bear', 'DOWN_HIGHVOL']
    
    print("📊 ENHANCED MOMENTUM SCORING DEMONSTRATION")
    print("=" * 60)
    print(f"{'Regime':<15} {'Score':<8} {'Quality':<12} {'Weighting'}")
    print("=" * 60)
    
    for regime in regimes:
        result = calculator.calculate_risk_adjusted_momentum(
            test_data, test_data, regime
        )
        score = result['score']
        quality = result['quality']
        
        weights = calculator.regime_weights[regime]
        weight_str = f"{weights['short']:.1f}/{weights['medium']:.1f}/{weights['long']:.1f}"
        
        print(f"{regime:<15} {score:>7.3f} {quality:<12} {weight_str}")
    
    print("\n✅ Enhanced risk-adjusted momentum with regime awareness ready!")

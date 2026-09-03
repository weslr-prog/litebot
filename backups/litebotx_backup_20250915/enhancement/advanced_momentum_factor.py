#!/usr/bin/env python3
"""
Advanced Momentum Factor Calculator
Enhanced momentum calculation with risk-adjusted scoring and regime-dependent weightings

Key Features:
1. Multiple momentum timeframes with optimized weightings
2. Risk-adjusted momentum (Sharpe-like scoring)
3. Regime-dependent momentum calculations
4. Volatility-adjusted momentum metrics
5. Quality momentum filters
"""

import numpy as np
import pandas as pd
import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class AdvancedMomentumConfig:
    """Advanced configuration for momentum factor calculation"""
    
    # Multiple momentum periods
    short_period: int = 10           # 10-day short-term momentum
    medium_period: int = 21          # 21-day medium-term momentum  
    long_period: int = 63            # 63-day long-term momentum
    volatility_period: int = 21      # 21-day volatility calculation
    
    # Risk-adjusted momentum parameters
    min_sharpe_threshold: float = -0.5    # Minimum Sharpe ratio
    momentum_decay_factor: float = 0.95   # Decay factor for recent performance
    
    # Regime-dependent weightings
    regime_weightings = {
        'bull': {
            'short_weight': 0.5,     # Strong trends favor short-term momentum
            'medium_weight': 0.35,   # Medium-term confirmation
            'long_weight': 0.15,     # Less weight on long-term
            'vol_adjustment': 0.8    # Moderate volatility adjustment
        },
        'UP_LOWVOL': {
            'short_weight': 0.6,     # Maximum short-term weighting
            'medium_weight': 0.3,
            'long_weight': 0.1,
            'vol_adjustment': 0.5    # Lower volatility adjustment
        },
        'sideways': {
            'short_weight': 0.2,     # Reduce short-term noise
            'medium_weight': 0.4,    # Focus on medium-term
            'long_weight': 0.4,      # Include long-term stability
            'vol_adjustment': 1.2    # Higher volatility adjustment
        },
        'volatile': {
            'short_weight': 0.15,    # Minimize short-term noise
            'medium_weight': 0.35,
            'long_weight': 0.5,      # Emphasize long-term trends
            'vol_adjustment': 1.5    # High volatility adjustment
        },
        'bear': {
            'short_weight': 0.4,     # Focus on recent weakness
            'medium_weight': 0.4,
            'long_weight': 0.2,
            'vol_adjustment': 1.3    # Moderate volatility adjustment
        },
        'DOWN_HIGHVOL': {
            'short_weight': 0.3,
            'medium_weight': 0.4,
            'long_weight': 0.3,
            'vol_adjustment': 1.8    # Maximum volatility adjustment
        },
        'crash': {
            'short_weight': 0.5,     # Recent performance critical
            'medium_weight': 0.35,
            'long_weight': 0.15,
            'vol_adjustment': 2.0    # Maximum volatility penalty
        },
        'recovery': {
            'short_weight': 0.45,    # Recovery momentum important
            'medium_weight': 0.35,
            'long_weight': 0.2,
            'vol_adjustment': 1.0    # Neutral volatility adjustment
        }
    }
    
    # Quality filters
    min_volume: float = 1_000_000        # Minimum daily volume
    min_price: float = 10.0              # Minimum stock price
    max_price: float = 1000.0            # Maximum stock price
    max_volatility: float = 2.5          # Maximum volatility threshold


class AdvancedMomentumCalculator:
    """
    Advanced momentum calculator with risk-adjusted scoring
    
    Implements sophisticated momentum calculation that considers:
    1. Multiple timeframes with regime-dependent weightings
    2. Risk-adjusted returns (Sharpe-like scoring)
    3. Volatility penalties
    4. Momentum decay factors
    5. Quality filters
    """
    
    def __init__(self, config: AdvancedMomentumConfig = None):
        self.config = config or AdvancedMomentumConfig()
        self.logger = logging.getLogger(__name__)
        
        self.logger.info("🧮 Advanced Momentum Calculator initialized")
        self.logger.info(f"   Periods: {self.config.short_period}d/{self.config.medium_period}d/{self.config.long_period}d")
        self.logger.info(f"   Regime weightings: {len(self.config.regime_weightings)} regimes configured")
    
    def calculate_risk_adjusted_momentum(self,
                                       price_data: pd.Series,
                                       period: int,
                                       vol_adjustment: float = 1.0) -> float:
        """
        Calculate risk-adjusted momentum (Sharpe-like ratio)
        
        Args:
            price_data: Price series
            period: Lookback period
            vol_adjustment: Volatility adjustment factor
            
        Returns:
            Risk-adjusted momentum score
        """
        try:
            # Validate inputs
            if not isinstance(period, int) or period <= 0:
                self.logger.warning(f"⚠️ Invalid period type or value: {period}")
                return 0.0
                
            if len(price_data) < period + 5:
                return 0.0
            
            # Calculate returns
            returns = price_data.pct_change().dropna()
            
            if len(returns) < period:
                return 0.0
            
            # Get period returns
            period_returns = returns.tail(period)
            
            # Calculate momentum metrics
            total_return = (price_data.iloc[-1] / price_data.iloc[-period-1] - 1) if len(price_data) > period else 0
            avg_return = period_returns.mean()
            volatility = period_returns.std()
            
            if volatility <= 0 or np.isnan(volatility):
                return 0.0
            
            # Risk-adjusted momentum (Sharpe-like)
            risk_adjusted = (avg_return / volatility) * np.sqrt(252)  # Annualized
            
            # Apply volatility adjustment
            risk_adjusted *= (1 / vol_adjustment)
            
            # Apply momentum decay (recent performance matters more)
            decay_weights = np.array([self.config.momentum_decay_factor ** i for i in range(period)])[::-1]
            decay_weights /= decay_weights.sum()
            
            # Ensure we have the right number of weights for the returns
            num_returns = len(period_returns)
            if len(decay_weights) >= num_returns:
                weights_slice = decay_weights[-num_returns:]
            else:
                weights_slice = decay_weights
                
            # Ensure arrays have compatible shapes
            min_len = min(len(period_returns), len(weights_slice))
            weighted_returns = period_returns.iloc[-min_len:] * weights_slice[-min_len:]
            momentum_strength = weighted_returns.sum()
            
            # Combine risk-adjusted score with momentum strength
            final_score = risk_adjusted * (1 + momentum_strength * 10)  # Scale momentum strength
            
            return final_score
            
        except Exception as e:
            self.logger.warning(f"⚠️ Risk-adjusted momentum calculation failed: {e}")
            return 0.0
    
    def calculate_momentum_quality_score(self,
                                       price_data: pd.Series,
                                       volume_data: pd.Series) -> float:
        """
        Calculate momentum quality score based on volume and price action
        
        Args:
            price_data: Price series
            volume_data: Volume series
            
        Returns:
            Quality score (0-1)
        """
        try:
            if len(price_data) < 20 or len(volume_data) < 20:
                return 0.0
            
            # Volume trend (increasing volume with price increases)
            price_changes = price_data.pct_change().tail(10)
            volume_changes = volume_data.pct_change().tail(10)
            
            # Correlation between price and volume changes
            if len(price_changes) > 5 and len(volume_changes) > 5:
                correlation = np.corrcoef(price_changes.dropna(), volume_changes.dropna())[0, 1]
                if np.isnan(correlation):
                    correlation = 0
            else:
                correlation = 0
            
            # Volume ratio (current vs average)
            avg_volume = volume_data.tail(20).mean()
            recent_volume = volume_data.tail(5).mean()
            volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 1
            
            # Price momentum consistency
            returns = price_data.pct_change().tail(10)
            positive_days = (returns > 0).sum()
            consistency = positive_days / len(returns) if len(returns) > 0 else 0
            
            # Combine quality factors
            quality_score = (
                max(0, correlation) * 0.4 +           # Volume-price correlation
                min(1, volume_ratio / 2) * 0.3 +      # Volume strength
                consistency * 0.3                      # Momentum consistency
            )
            
            return max(0, min(1, quality_score))
            
        except Exception as e:
            self.logger.warning(f"⚠️ Quality score calculation failed: {e}")
            return 0.0
    
    def calculate_advanced_momentum_score(self,
                                        symbol: str,
                                        market_data: pd.DataFrame,
                                        regime: str = 'sideways') -> Dict:
        """
        Calculate advanced momentum score for a single stock
        
        Args:
            symbol: Stock symbol
            market_data: Market data DataFrame with OHLCV
            regime: Current market regime
            
        Returns:
            Dictionary with momentum scores and metrics
        """
        try:
            if len(market_data) < max(self.config.short_period, self.config.medium_period, self.config.long_period) + 10:
                return {'symbol': symbol, 'momentum_score': 0, 'quality': 'insufficient_data'}
            
            price_data = market_data['close']
            volume_data = market_data['volume']
            
            # Get regime weightings
            regime_weights = self.config.regime_weightings.get(regime, self.config.regime_weightings['sideways'])
            
            # Calculate momentum for each timeframe
            short_momentum = self.calculate_risk_adjusted_momentum(
                price_data, self.config.short_period, regime_weights['vol_adjustment']
            )
            
            medium_momentum = self.calculate_risk_adjusted_momentum(
                price_data, self.config.medium_period, regime_weights['vol_adjustment']
            )
            
            long_momentum = self.calculate_risk_adjusted_momentum(
                price_data, self.config.long_period, regime_weights['vol_adjustment']
            )
            
            # Calculate weighted composite momentum
            composite_momentum = (
                short_momentum * regime_weights['short_weight'] +
                medium_momentum * regime_weights['medium_weight'] +
                long_momentum * regime_weights['long_weight']
            )
            
            # Calculate quality score
            quality_score = self.calculate_momentum_quality_score(price_data, volume_data)
            
            # Apply quality filters
            current_price = price_data.iloc[-1]
            avg_volume = volume_data.tail(20).mean()
            
            # Volatility check
            returns = price_data.pct_change().tail(self.config.volatility_period)
            volatility = returns.std() * np.sqrt(252)  # Annualized
            
            # Quality classification
            if (current_price < self.config.min_price or 
                current_price > self.config.max_price or
                avg_volume < self.config.min_volume or
                volatility > self.config.max_volatility):
                quality = 'poor'
            elif quality_score > 0.7 and volatility < 0.4:
                quality = 'excellent'
            elif quality_score > 0.5 and volatility < 0.6:
                quality = 'good'
            else:
                quality = 'fair'
            
            # Final momentum score with quality adjustment
            if quality == 'excellent':
                quality_multiplier = 1.2
            elif quality == 'good':
                quality_multiplier = 1.1
            elif quality == 'fair':
                quality_multiplier = 1.0
            else:
                quality_multiplier = 0.7
            
            final_momentum = composite_momentum * quality_multiplier
            
            return {
                'symbol': symbol,
                'momentum_score': final_momentum,
                'short_momentum': short_momentum,
                'medium_momentum': medium_momentum,
                'long_momentum': long_momentum,
                'composite_momentum': composite_momentum,
                'quality_score': quality_score,
                'quality': quality,
                'volatility': volatility,
                'current_price': current_price,
                'volume': avg_volume,
                'regime': regime,
                'regime_weights': regime_weights
            }
            
        except Exception as e:
            self.logger.error(f"❌ Advanced momentum calculation failed for {symbol}: {e}")
            return {'symbol': symbol, 'momentum_score': 0, 'quality': 'error'}
    
    def rank_stocks_by_advanced_momentum(self,
                                       market_data: Dict[str, pd.DataFrame],
                                       regime: str = 'sideways',
                                       max_selections: int = 20,
                                       min_momentum_threshold: float = 0.1) -> List[Dict]:
        """
        Rank all stocks by advanced momentum scoring
        
        Args:
            market_data: Dictionary of market data by symbol
            regime: Current market regime
            max_selections: Maximum number of stocks to return
            min_momentum_threshold: Minimum momentum threshold
            
        Returns:
            List of top momentum stocks with scores
        """
        self.logger.info(f"🧮 Calculating advanced momentum scores for {len(market_data)} stocks")
        self.logger.info(f"   Regime: {regime}")
        self.logger.info(f"   Max selections: {max_selections}")
        
        momentum_scores = []
        
        for symbol, data in market_data.items():
            score_data = self.calculate_advanced_momentum_score(symbol, data, regime)
            
            if (score_data['momentum_score'] > min_momentum_threshold and 
                score_data['quality'] != 'poor'):
                momentum_scores.append(score_data)
        
        # Sort by momentum score (descending)
        momentum_scores.sort(key=lambda x: x['momentum_score'], reverse=True)
        
        # Apply diversification and selection logic
        selected_stocks = []
        quality_counts = {'excellent': 0, 'good': 0, 'fair': 0}
        
        for stock in momentum_scores:
            if len(selected_stocks) >= max_selections:
                break
            
            quality = stock['quality']
            
            # Prefer higher quality stocks but maintain diversity
            if quality == 'excellent' or len(selected_stocks) < max_selections // 2:
                selected_stocks.append(stock)
                quality_counts[quality] += 1
            elif quality == 'good' and quality_counts['good'] < max_selections // 3:
                selected_stocks.append(stock)
                quality_counts[quality] += 1
            elif quality == 'fair' and quality_counts['fair'] < max_selections // 4:
                selected_stocks.append(stock)
                quality_counts[quality] += 1
        
        self.logger.info(f"📊 Advanced Momentum Selection Results:")
        self.logger.info(f"   Analyzed: {len(momentum_scores)} stocks")
        self.logger.info(f"   Selected: {len(selected_stocks)} stocks")
        self.logger.info(f"   Quality breakdown: {quality_counts}")
        
        if selected_stocks:
            avg_momentum = np.mean([s['momentum_score'] for s in selected_stocks])
            self.logger.info(f"   Average momentum: {avg_momentum:.3f}")
            self.logger.info(f"   Top stock: {selected_stocks[0]['symbol']} ({selected_stocks[0]['momentum_score']:.3f})")
        
        return selected_stocks
    
    def get_regime_momentum_parameters(self,
                                     base_short: int = 21,
                                     base_medium: int = 42,
                                     regime: str = 'sideways') -> Tuple[int, int, Dict]:
        """
        Get regime-adjusted momentum parameters
        
        Args:
            base_short: Base short-term period
            base_medium: Base medium-term period  
            regime: Current market regime
            
        Returns:
            Tuple of (adjusted_short, adjusted_medium, regime_info)
        """
        regime_weights = self.config.regime_weightings.get(regime, self.config.regime_weightings['sideways'])
        
        # Adjust periods based on regime
        if regime in ['bull', 'UP_LOWVOL']:
            # Faster periods in trending markets
            adj_short = max(10, int(base_short * 0.7))
            adj_medium = max(21, int(base_medium * 0.8))
        elif regime in ['sideways', 'volatile']:
            # Longer periods in choppy markets
            adj_short = int(base_short * 1.2)
            adj_medium = int(base_medium * 1.3)
        elif regime in ['bear', 'DOWN_HIGHVOL', 'crash']:
            # Medium periods for bear markets
            adj_short = int(base_short * 0.9)
            adj_medium = int(base_medium * 1.1)
        else:  # recovery
            adj_short = base_short
            adj_medium = base_medium
        
        return adj_short, adj_medium, regime_weights


def demo_advanced_momentum():
    """Demonstrate advanced momentum calculation"""
    print("📊 ADVANCED MOMENTUM FACTOR DEMONSTRATION")
    print("=" * 80)
    
    calculator = AdvancedMomentumCalculator()
    
    # Show regime weightings
    print("Regime-Dependent Momentum Weightings:")
    print(f"{'Regime':<12} {'Short':<8} {'Medium':<8} {'Long':<8} {'Vol Adj':<8}")
    print("-" * 50)
    
    for regime, weights in calculator.config.regime_weightings.items():
        print(f"{regime:<12} {weights['short_weight']:<8.1f} {weights['medium_weight']:<8.1f} "
              f"{weights['long_weight']:<8.1f} {weights['vol_adjustment']:<8.1f}")
    
    print("\n💡 KEY FEATURES:")
    print("• Risk-adjusted momentum scoring (Sharpe-like ratios)")
    print("• Regime-dependent timeframe weightings")
    print("• Quality filters based on volume and price action")
    print("• Volatility adjustments for different market conditions")
    print("• Momentum decay factors (recent performance weighted more)")
    
    print("\n🎯 IMPROVEMENTS OVER BASIC MOMENTUM:")
    print("• Bull markets: Favor short-term momentum (50-60% weight)")
    print("• Sideways markets: Balance all timeframes, increase volatility penalty")
    print("• Bear markets: Focus on recent weakness with longer-term context")
    print("• Quality scoring: Volume-price correlation and momentum consistency")


if __name__ == "__main__":
    demo_advanced_momentum()

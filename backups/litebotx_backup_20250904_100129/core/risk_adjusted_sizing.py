#!/usr/bin/env python3
"""
Risk-Adjusted Position Sizing Module
Implements volatility-based position sizing for optimal risk-adjusted returns
"""

import numpy as np
import pandas as pd
import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

@dataclass
class PositionSizingConfig:
    """Configuration for position sizing parameters"""
    target_volatility: float = 0.15  # Target portfolio volatility (15%)
    max_position_weight: float = 0.10  # Maximum single position (10%)
    min_position_weight: float = 0.01  # Minimum single position (1%)
    volatility_lookback: int = 21  # Days to calculate volatility
    correlation_lookback: int = 63  # Days for correlation calculation
    max_correlation: float = 0.7  # Maximum correlation between positions
    cash_buffer: float = 0.05  # Keep 5% cash buffer
    rebalance_threshold: float = 0.02  # Rebalance if drift > 2%

class VolatilityAdjustedSizer:
    """
    Advanced position sizing based on:
    1. Individual stock volatility
    2. Portfolio-level risk budgeting
    3. Correlation constraints
    4. Maximum position limits
    """
    
    def __init__(self, config: PositionSizingConfig = None):
        """Initialize the volatility-adjusted sizer"""
        self.config = config or PositionSizingConfig()
        self.logger = logging.getLogger(__name__)
        
        # Risk metrics cache
        self.volatility_cache = {}
        self.correlation_cache = {}
        self.last_update = {}
        
        self.logger.info(f"🎯 VolatilityAdjustedSizer initialized")
        self.logger.info(f"   Target Portfolio Vol: {self.config.target_volatility:.1%}")
        self.logger.info(f"   Max Position Weight: {self.config.max_position_weight:.1%}")
        self.logger.info(f"   Volatility Lookback: {self.config.volatility_lookback}d")
        
    def calculate_volatility(self, price_data: pd.DataFrame, symbol: str) -> float:
        """Calculate annualized volatility for a symbol"""
        try:
            if len(price_data) < self.config.volatility_lookback:
                self.logger.warning(f"⚠️ Insufficient data for {symbol} volatility calculation")
                return 0.25  # Default high volatility
            
            # Use close prices for returns calculation
            prices = price_data['close'].iloc[-self.config.volatility_lookback:]
            returns = prices.pct_change().dropna()
            
            if len(returns) < 10:
                return 0.25  # Default if insufficient returns
            
            # Annualized volatility (252 trading days)
            daily_vol = returns.std()
            annual_vol = daily_vol * np.sqrt(252)
            
            # Cache the result
            self.volatility_cache[symbol] = {
                'volatility': annual_vol,
                'timestamp': datetime.now()
            }
            
            return annual_vol
            
        except Exception as e:
            self.logger.error(f"❌ Error calculating volatility for {symbol}: {e}")
            return 0.25  # Conservative default
    
    def get_risk_budget_weights(self, signals: List[Dict], market_data: Dict[str, pd.DataFrame]) -> Dict[str, float]:
        """
        Calculate risk-budgeted weights based on:
        1. Inverse volatility weighting
        2. Momentum signal strength
        3. Correlation constraints
        """
        try:
            self.logger.info("🎯 Calculating risk-budgeted position weights...")
            
            # Calculate volatilities for all symbols
            volatilities = {}
            for signal in signals:
                symbol = signal['symbol']
                if symbol in market_data:
                    vol = self.calculate_volatility(market_data[symbol], symbol)
                    volatilities[symbol] = vol
                    self.logger.debug(f"   {symbol}: volatility = {vol:.2%}")
            
            if not volatilities:
                self.logger.error("❌ No volatility data available")
                return {}
            
            # Calculate inverse volatility weights
            inv_vol_weights = {}
            total_inv_vol = 0
            
            for signal in signals:
                symbol = signal['symbol']
                if symbol in volatilities:
                    # Inverse volatility weight adjusted by momentum strength
                    momentum_score = signal.get('momentum_score', 0)
                    
                    # Base weight from inverse volatility
                    inv_vol = 1.0 / volatilities[symbol]
                    
                    # Adjust by momentum strength (stronger momentum = higher weight)
                    momentum_adj = 1.0 + momentum_score  # Positive momentum increases weight
                    
                    # Combined weight
                    weight = inv_vol * momentum_adj
                    inv_vol_weights[symbol] = weight
                    total_inv_vol += weight
            
            # Normalize to sum to 1 (before applying constraints)
            if total_inv_vol > 0:
                for symbol in inv_vol_weights:
                    inv_vol_weights[symbol] /= total_inv_vol
            
            # Apply position size constraints
            final_weights = {}
            total_constrained = 0
            
            for symbol, weight in inv_vol_weights.items():
                # Apply min/max constraints
                constrained_weight = max(
                    self.config.min_position_weight,
                    min(weight, self.config.max_position_weight)
                )
                final_weights[symbol] = constrained_weight
                total_constrained += constrained_weight
            
            # Renormalize to account for cash buffer
            target_invested = 1.0 - self.config.cash_buffer
            if total_constrained > 0:
                scale_factor = target_invested / total_constrained
                for symbol in final_weights:
                    final_weights[symbol] *= scale_factor
            
            # Log final weights
            self.logger.info("📊 Risk-adjusted position weights:")
            for symbol, weight in sorted(final_weights.items(), key=lambda x: x[1], reverse=True):
                vol = volatilities.get(symbol, 0)
                self.logger.info(f"   {symbol}: {weight:.2%} (vol: {vol:.2%})")
            
            total_weight = sum(final_weights.values())
            cash_weight = 1.0 - total_weight
            self.logger.info(f"   CASH: {cash_weight:.2%}")
            
            return final_weights
            
        except Exception as e:
            self.logger.error(f"❌ Error calculating risk budget weights: {e}")
            return {}
    
    def calculate_position_sizes(self, 
                               signals: List[Dict], 
                               market_data: Dict[str, pd.DataFrame], 
                               portfolio_value: float) -> List[Dict]:
        """
        Main method to calculate volatility-adjusted position sizes
        
        Args:
            signals: List of momentum signals with symbol and momentum_score
            market_data: Dictionary of price data for each symbol
            portfolio_value: Total portfolio value
            
        Returns:
            List of signals with updated position_value and shares
        """
        try:
            self.logger.info("🚀 Calculating volatility-adjusted position sizes...")
            self.logger.info(f"   Portfolio Value: ${portfolio_value:,.2f}")
            self.logger.info(f"   Number of Signals: {len(signals)}")
            
            if not signals:
                return []
            
            # Get risk-budgeted weights
            weights = self.get_risk_budget_weights(signals, market_data)
            
            if not weights:
                self.logger.error("❌ Failed to calculate position weights")
                return signals  # Return original signals
            
            # Calculate position sizes
            updated_signals = []
            total_allocated = 0
            
            for signal in signals:
                symbol = signal['symbol']
                
                if symbol in weights and symbol in market_data:
                    weight = weights[symbol]
                    position_value = portfolio_value * weight
                    
                    # Get current price for share calculation
                    try:
                        current_price = market_data[symbol]['close'].iloc[-1]
                        shares = int(position_value / current_price)
                        actual_value = shares * current_price
                        
                        # Update signal with new position sizing
                        updated_signal = signal.copy()
                        updated_signal.update({
                            'position_value': actual_value,
                            'shares': shares,
                            'weight': weight,
                            'volatility': self.volatility_cache.get(symbol, {}).get('volatility', 0),
                            'target_weight': weight,
                            'current_price': current_price
                        })
                        
                        updated_signals.append(updated_signal)
                        total_allocated += actual_value
                        
                        self.logger.info(f"   💰 {symbol}: {shares} shares @ ${current_price:.2f} = ${actual_value:,.0f} ({weight:.2%})")
                        
                    except Exception as e:
                        self.logger.error(f"❌ Error calculating shares for {symbol}: {e}")
                        updated_signals.append(signal)  # Keep original
                else:
                    updated_signals.append(signal)  # Keep original if no weight
            
            cash_remaining = portfolio_value - total_allocated
            cash_percent = cash_remaining / portfolio_value
            
            self.logger.info("📊 Position Sizing Summary:")
            self.logger.info(f"   Total Allocated: ${total_allocated:,.2f}")
            self.logger.info(f"   Cash Remaining: ${cash_remaining:,.2f} ({cash_percent:.1%})")
            self.logger.info(f"   Number of Positions: {len(updated_signals)}")
            
            return updated_signals
            
        except Exception as e:
            self.logger.error(f"❌ Error in position sizing calculation: {e}")
            return signals  # Return original signals as fallback
    
    def get_portfolio_risk_metrics(self, 
                                 positions: Dict[str, Dict], 
                                 market_data: Dict[str, pd.DataFrame]) -> Dict[str, float]:
        """Calculate current portfolio risk metrics"""
        try:
            if not positions:
                return {}
            
            # Calculate individual position volatilities
            position_vols = {}
            position_weights = {}
            total_value = sum(pos['market_value'] for pos in positions.values())
            
            for symbol, pos in positions.items():
                if symbol in market_data:
                    vol = self.calculate_volatility(market_data[symbol], symbol)
                    weight = pos['market_value'] / total_value
                    position_vols[symbol] = vol
                    position_weights[symbol] = weight
            
            # Calculate portfolio volatility (simplified)
            portfolio_vol = 0
            for symbol, weight in position_weights.items():
                vol = position_vols.get(symbol, 0)
                portfolio_vol += (weight * vol) ** 2
            
            portfolio_vol = np.sqrt(portfolio_vol)
            
            # Additional metrics
            max_weight = max(position_weights.values()) if position_weights else 0
            num_positions = len(positions)
            concentration = sum(w**2 for w in position_weights.values())  # Herfindahl index
            
            return {
                'portfolio_volatility': portfolio_vol,
                'max_position_weight': max_weight,
                'num_positions': num_positions,
                'concentration_index': concentration,
                'average_position_volatility': np.mean(list(position_vols.values())) if position_vols else 0
            }
            
        except Exception as e:
            self.logger.error(f"❌ Error calculating portfolio risk metrics: {e}")
            return {}

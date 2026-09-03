#!/usr/bin/env python3
"""
Weekend Risk Manager - Manages Friday trading decisions
"""

import pandas as pd
import numpy as np
from datetime import datetime, time as dt_time
from typing import Dict, List, Tuple
import logging

class WeekendRiskManager:
    """
    Manages weekend risk by adjusting position sizes and holdings on Fridays
    """
    
    def __init__(self, config: Dict = None):
        """
        Initialize weekend risk manager
        
        Args:
            config: Configuration dictionary with risk parameters
        """
        self.config = config or {
            'max_weekend_exposure': 0.7,  # Max 70% exposure over weekend
            'high_vol_threshold': 0.4,     # Consider high if vol > 40%
            'momentum_threshold': 0.1,     # Strong momentum threshold
            'vix_threshold': 25,           # Market fear threshold
            'friday_hour_cutoff': 15,      # Stop new positions after 3 PM
        }
        
        self.logger = logging.getLogger(__name__)
    
    def should_reduce_positions_friday(self, current_time: datetime, 
                                     portfolio_data: Dict, 
                                     market_data: Dict) -> Tuple[bool, float]:
        """
        Determine if positions should be reduced on Friday
        
        Returns:
            (should_reduce, target_exposure_ratio)
        """
        # Check if it's Friday
        if current_time.weekday() != 4:  # 4 = Friday
            return False, 1.0
        
        # Calculate risk factors
        risk_score = self._calculate_weekend_risk_score(portfolio_data, market_data)
        
        # Determine action based on risk score
        if risk_score > 0.8:  # High risk
            self.logger.warning(f"🔴 High weekend risk detected (score: {risk_score:.2f})")
            return True, 0.3  # Reduce to 30% exposure
        elif risk_score > 0.6:  # Medium risk
            self.logger.info(f"🟡 Medium weekend risk detected (score: {risk_score:.2f})")
            return True, 0.5  # Reduce to 50% exposure
        elif risk_score > 0.4:  # Low-medium risk
            self.logger.info(f"🟠 Low-medium weekend risk detected (score: {risk_score:.2f})")
            return True, 0.7  # Reduce to 70% exposure
        else:
            self.logger.info(f"🟢 Low weekend risk detected (score: {risk_score:.2f})")
            return False, 1.0  # Keep full exposure
    
    def _calculate_weekend_risk_score(self, portfolio_data: Dict, 
                                    market_data: Dict) -> float:
        """
        Calculate a risk score from 0.0 (safe) to 1.0 (risky)
        """
        risk_factors = []
        
        # Factor 1: Portfolio volatility
        portfolio_vol = portfolio_data.get('portfolio_volatility', 0.15)
        vol_risk = min(portfolio_vol / 0.5, 1.0)  # Normalize to 50% vol
        risk_factors.append(('portfolio_vol', vol_risk, 0.3))
        
        # Factor 2: Market volatility (average of holdings)
        positions = portfolio_data.get('positions', {})
        if positions:
            avg_vol = np.mean([pos.get('volatility', 0.2) 
                              for pos in positions.values() if pos.get('volatility')])
        else:
            avg_vol = 0.2
        
        vix_risk = min(avg_vol / 0.4, 1.0)  # Normalize to 40%
        risk_factors.append(('market_vol', vix_risk, 0.25))
        
        # Factor 3: Concentration risk
        max_position = portfolio_data.get('max_position_weight', 0.1)
        concentration_risk = min(max_position / 0.2, 1.0)  # Normalize to 20%
        risk_factors.append(('concentration', concentration_risk, 0.2))
        
        # Factor 4: Momentum strength (strong momentum = reversal risk)
        if positions:
            momentum_scores = [pos.get('momentum_score', 0) 
                             for pos in positions.values() if pos.get('momentum_score') is not None]
            avg_momentum = np.mean(momentum_scores) if momentum_scores else 0
        else:
            avg_momentum = 0
        
        momentum_risk = min(abs(avg_momentum) / 0.3, 1.0)  # Strong momentum = reversal risk
        risk_factors.append(('momentum', momentum_risk, 0.15))
        
        # Factor 5: Number of positions (diversification)
        num_positions = len(positions)
        diversification_risk = max(0, (10 - num_positions) / 10)  # Less than 10 = risk
        risk_factors.append(('diversification', diversification_risk, 0.1))
        
        # Calculate weighted risk score
        total_risk = sum(risk * weight for _, risk, weight in risk_factors)
        
        # Log risk breakdown
        self.logger.info("📊 Weekend Risk Breakdown:")
        for factor, risk, weight in risk_factors:
            self.logger.info(f"   {factor}: {risk:.2f} (weight: {weight:.1%})")
        self.logger.info(f"   Total Risk Score: {total_risk:.2f}")
        
        return total_risk
    
    def get_friday_position_adjustments(self, current_positions: Dict, 
                                      target_exposure: float) -> List[Dict]:
        """
        Calculate position adjustments needed for Friday risk management
        
        Returns:
            List of trade adjustments needed
        """
        adjustments = []
        
        if target_exposure >= 1.0:
            return adjustments  # No adjustments needed
        
        self.logger.info(f"📉 Calculating position adjustments for {target_exposure:.0%} target exposure")
        
        # Sort positions by risk (highest vol first)
        sorted_positions = sorted(
            current_positions.items(),
            key=lambda x: x[1].get('volatility', 0.2),
            reverse=True
        )
        
        # Calculate how much to reduce each position
        for symbol, position in sorted_positions:
            current_shares = position.get('shares', 0)
            if current_shares <= 0:
                continue
            
            # Reduce higher volatility positions more aggressively
            vol = position.get('volatility', 0.2)
            if vol > self.config['high_vol_threshold']:
                # High vol stocks: reduce by (1 - target_exposure) * 1.5
                reduction_factor = (1 - target_exposure) * 1.5
            else:
                # Normal vol stocks: reduce by (1 - target_exposure)
                reduction_factor = (1 - target_exposure)
            
            reduction_factor = min(reduction_factor, 0.8)  # Max 80% reduction
            shares_to_sell = int(current_shares * reduction_factor)
            
            if shares_to_sell > 0:
                adjustments.append({
                    'symbol': symbol,
                    'action': 'sell',
                    'shares': shares_to_sell,
                    'reason': f'weekend_risk_reduction_{vol:.1%}_vol',
                    'priority': vol  # Higher vol = higher priority
                })
        
        # Sort by priority (highest vol first)
        adjustments.sort(key=lambda x: x['priority'], reverse=True)
        
        return adjustments
    
    def should_avoid_new_positions(self, current_time: datetime) -> bool:
        """
        Check if new positions should be avoided (late Friday)
        """
        if current_time.weekday() != 4:  # Not Friday
            return False
        
        # Avoid new positions after cutoff hour on Friday
        cutoff_time = dt_time(self.config['friday_hour_cutoff'], 0)
        return current_time.time() >= cutoff_time
    
    def apply_friday_filters(self, signals: List[Dict], current_time: datetime) -> List[Dict]:
        """
        Apply Friday-specific filters to trading signals
        """
        if current_time.weekday() != 4:  # Not Friday
            return signals
        
        # Avoid new positions after cutoff
        if self.should_avoid_new_positions(current_time):
            self.logger.info("🚫 Friday cutoff: No new positions after 3 PM")
            return []
        
        # Filter out high volatility signals on Friday
        filtered_signals = []
        for signal in signals:
            vol = signal.get('volatility', 0.2)
            if vol > self.config['high_vol_threshold']:
                self.logger.info(f"🚫 Friday filter: Skipping {signal['symbol']} (vol: {vol:.1%})")
                continue
            
            # Reduce position size for remaining signals
            if 'shares' in signal:
                signal['shares'] = int(signal['shares'] * 0.7)  # 30% reduction
                signal['friday_reduced'] = True
            
            filtered_signals.append(signal)
        
        return filtered_signals

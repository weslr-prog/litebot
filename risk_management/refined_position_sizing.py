#!/usr/bin/env python3
"""
Refined Position Sizing Module
Enhanced risk-per-trade with regime-dependent risk percentages and better limits

Key Improvements:
1. Regime-dependent risk percentages (0.5-2% based on market regime)
2. Better position limits based on volatility
3. More precise risk calculations
4. Enhanced validation and safety checks
"""

import numpy as np
import pandas as pd
import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class RefinedRiskConfig:
    """Refined risk configuration with regime-dependent parameters"""
    
    # Base risk percentages by regime
    regime_risk_percentages = {
        'bull': 0.015,           # 1.5% - slightly more aggressive in bull markets
        'UP_LOWVOL': 0.020,      # 2.0% - max aggressive in low vol uptrends
        'sideways': 0.010,       # 1.0% - conservative in choppy markets
        'volatile': 0.008,       # 0.8% - very conservative in high volatility
        'bear': 0.005,           # 0.5% - minimal risk in bear markets
        'DOWN_HIGHVOL': 0.005,   # 0.5% - minimal risk in volatile downtrends
        'crash': 0.003,          # 0.3% - ultra-conservative in crashes
        'recovery': 0.012        # 1.2% - moderate in recovery phases
    }
    
    # Position size limits
    max_position_pct: float = 0.20      # 20% max position size
    min_position_pct: float = 0.03      # 3% min position size
    max_concurrent_positions: int = 5   # 5 concentrated positions
    
    # Stop-loss parameters
    default_stop_loss_pct: float = 0.025  # 2.5% default stop
    min_stop_loss_pct: float = 0.015      # 1.5% minimum stop
    max_stop_loss_pct: float = 0.06       # 6% maximum stop
    
    # Safety limits
    max_total_portfolio_risk: float = 0.08  # 8% max total portfolio risk
    max_single_position_risk: float = 0.03  # 3% max risk per position


class RefinedPositionSizer:
    """
    Refined position sizing with regime-dependent risk management
    
    Core Formula: Position Size = (Risk_Amount) / (Entry_Price - Stop_Price)
    
    Enhancements:
    1. Regime-dependent risk percentages
    2. Volatility-adjusted position limits
    3. Better correlation with stop distances
    4. Enhanced safety checks
    """
    
    def __init__(self, config: RefinedRiskConfig = None):
        self.config = config or RefinedRiskConfig()
        self.logger = logging.getLogger(__name__)
        
        self.logger.info("🎯 Refined Position Sizer initialized")
        self.logger.info(f"   Regime Risk Range: {min(self.config.regime_risk_percentages.values()):.1%} - {max(self.config.regime_risk_percentages.values()):.1%}")
        self.logger.info(f"   Position Range: {self.config.min_position_pct:.1%} - {self.config.max_position_pct:.1%}")
    
    def get_regime_risk_percentage(self, regime: str) -> float:
        """Get risk percentage for current regime"""
        return self.config.regime_risk_percentages.get(regime, 0.01)  # Default 1%
    
    def calculate_volatility_adjusted_stop(self, 
                                         market_data: pd.DataFrame,
                                         base_stop_pct: float,
                                         lookback: int = 20) -> float:
        """Calculate volatility-adjusted stop-loss percentage"""
        try:
            # Calculate recent volatility
            returns = market_data['close'].pct_change().dropna()
            recent_vol = returns.tail(lookback).std() * np.sqrt(252)  # Annualized
            
            # Adjust stop based on volatility
            vol_adjustment = min(2.0, max(0.5, recent_vol / 0.20))  # Normalize to 20% baseline vol
            adjusted_stop = base_stop_pct * vol_adjustment
            
            # Apply limits
            adjusted_stop = max(self.config.min_stop_loss_pct, 
                              min(self.config.max_stop_loss_pct, adjusted_stop))
            
            return adjusted_stop
            
        except Exception as e:
            self.logger.warning(f"⚠️ Volatility adjustment failed: {e}")
            return base_stop_pct
    
    def calculate_refined_position_size(self,
                                      entry_price: float,
                                      stop_loss_price: float,
                                      portfolio_value: float,
                                      regime: str,
                                      symbol: str = None,
                                      market_data: pd.DataFrame = None) -> Dict:
        """
        Calculate refined position size with regime-dependent risk
        
        Args:
            entry_price: Entry price for the stock
            stop_loss_price: Stop-loss price
            portfolio_value: Total portfolio value
            regime: Current market regime
            symbol: Stock symbol (for logging)
            market_data: Market data for volatility analysis
            
        Returns:
            Dict with position sizing details
        """
        # Get regime-specific risk percentage
        risk_per_trade_pct = self.get_regime_risk_percentage(regime)
        risk_amount = portfolio_value * risk_per_trade_pct
        
        # Calculate risk per share
        risk_per_share = entry_price - stop_loss_price
        
        if risk_per_share <= 0:
            return {
                'shares': 0,
                'position_value': 0,
                'risk_amount': 0,
                'position_pct': 0,
                'error': 'Invalid stop-loss price',
                'regime_risk_pct': risk_per_trade_pct
            }
        
        # Calculate base position size
        shares = int(risk_amount / risk_per_share)
        position_value = shares * entry_price
        position_pct = position_value / portfolio_value
        
        # Apply position size limits
        max_position_value = portfolio_value * self.config.max_position_pct
        if position_value > max_position_value:
            shares = int(max_position_value / entry_price)
            position_value = shares * entry_price
            position_pct = position_value / portfolio_value
            
        # Check minimum position size
        min_position_value = portfolio_value * self.config.min_position_pct
        if position_value < min_position_value:
            return {
                'shares': 0,
                'position_value': 0,
                'risk_amount': 0,
                'position_pct': 0,
                'error': f'Below minimum position size: ${position_value:,.0f} < ${min_position_value:,.0f}',
                'regime_risk_pct': risk_per_trade_pct
            }
        
        # Calculate actual risk amount
        actual_risk = shares * risk_per_share
        actual_risk_pct = actual_risk / portfolio_value
        
        # Check single position risk limit
        if actual_risk_pct > self.config.max_single_position_risk:
            # Reduce shares to respect risk limit
            max_risk_amount = portfolio_value * self.config.max_single_position_risk
            shares = int(max_risk_amount / risk_per_share)
            position_value = shares * entry_price
            actual_risk = shares * risk_per_share
            position_pct = position_value / portfolio_value
        
        stop_loss_pct = (entry_price - stop_loss_price) / entry_price
        
        result = {
            'shares': shares,
            'position_value': position_value,
            'risk_amount': actual_risk,
            'position_pct': position_pct,
            'stop_loss_pct': stop_loss_pct,
            'risk_per_share': risk_per_share,
            'regime_risk_pct': risk_per_trade_pct,
            'entry_price': entry_price,
            'stop_loss_price': stop_loss_price,
            'regime': regime
        }
        
        # Log the calculation
        if symbol:
            self.logger.info(f"📊 {symbol} Refined Position Sizing:")
            self.logger.info(f"   Regime: {regime} → Risk: {risk_per_trade_pct:.2%}")
            self.logger.info(f"   Entry: ${entry_price:.2f}, Stop: ${stop_loss_price:.2f} ({stop_loss_pct:.1%})")
            self.logger.info(f"   Position: {shares} shares = ${position_value:,.0f} ({position_pct:.1%})")
            self.logger.info(f"   Risk: ${actual_risk:.0f} ({actual_risk_pct:.2%})")
        
        return result
    
    def calculate_positions_for_signals(self,
                                      signals: List[Dict],
                                      market_data: Dict[str, pd.DataFrame],
                                      portfolio_value: float,
                                      current_regime: str,
                                      adaptive_risk_manager = None) -> List[Dict]:
        """
        Calculate refined position sizes for all signals
        
        Args:
            signals: List of trading signals
            market_data: Market data for price and volatility analysis
            portfolio_value: Total portfolio value
            current_regime: Current market regime
            adaptive_risk_manager: Optional adaptive risk manager
            
        Returns:
            Updated signals with refined position sizing
        """
        self.logger.info("🎯 Calculating refined position sizes...")
        self.logger.info(f"   Portfolio: ${portfolio_value:,.0f}")
        self.logger.info(f"   Regime: {current_regime}")
        self.logger.info(f"   Regime Risk: {self.get_regime_risk_percentage(current_regime):.2%}")
        
        updated_signals = []
        total_position_value = 0
        total_risk_amount = 0
        
        for signal in signals:
            symbol = signal['symbol']
            
            if symbol not in market_data:
                self.logger.warning(f"⚠️ No market data for {symbol}")
                continue
            
            try:
                # Get current price
                entry_price = market_data[symbol]['close'].iloc[-1]
                
                # Get stop-loss percentage
                if adaptive_risk_manager:
                    base_stop_pct = adaptive_risk_manager.get_current_parameters().stop_loss_pct
                else:
                    base_stop_pct = self.config.default_stop_loss_pct
                
                # Apply volatility adjustment to stop-loss
                adjusted_stop_pct = self.calculate_volatility_adjusted_stop(
                    market_data[symbol], base_stop_pct
                )
                
                stop_loss_price = entry_price * (1 - adjusted_stop_pct)
                
                # Calculate refined position size
                position_data = self.calculate_refined_position_size(
                    entry_price=entry_price,
                    stop_loss_price=stop_loss_price,
                    portfolio_value=portfolio_value,
                    regime=current_regime,
                    symbol=symbol,
                    market_data=market_data[symbol]
                )
                
                if position_data['shares'] > 0:
                    # Update signal with refined position data
                    updated_signal = signal.copy()
                    updated_signal.update(position_data)
                    updated_signal['sizing_method'] = 'refined_risk_per_trade'
                    updated_signal['volatility_adjusted_stop'] = adjusted_stop_pct
                    
                    updated_signals.append(updated_signal)
                    total_position_value += position_data['position_value']
                    total_risk_amount += position_data['risk_amount']
                    
                else:
                    error = position_data.get('error', 'Unknown error')
                    self.logger.warning(f"⚠️ {symbol}: Position sizing failed - {error}")
                    
            except Exception as e:
                self.logger.error(f"❌ Error calculating position for {symbol}: {e}")
                continue
        
        # Final validation
        total_portfolio_pct = total_position_value / portfolio_value
        total_risk_pct = total_risk_amount / portfolio_value
        
        self.logger.info(f"📊 Refined Position Sizing Summary:")
        self.logger.info(f"   Signals: {len(signals)} → {len(updated_signals)} sized")
        self.logger.info(f"   Total Allocation: ${total_position_value:,.0f} ({total_portfolio_pct:.1%})")
        self.logger.info(f"   Total Risk: ${total_risk_amount:,.0f} ({total_risk_pct:.2%})")
        
        # Check total risk limit
        if total_risk_pct > self.config.max_total_portfolio_risk:
            self.logger.warning(f"⚠️ Total portfolio risk {total_risk_pct:.2%} exceeds limit {self.config.max_total_portfolio_risk:.2%}")
            # Scale down positions proportionally
            scale_factor = self.config.max_total_portfolio_risk / total_risk_pct
            
            for signal in updated_signals:
                signal['shares'] = int(signal['shares'] * scale_factor)
                signal['position_value'] = signal['shares'] * signal['entry_price']
                signal['risk_amount'] = signal['shares'] * signal['risk_per_share']
                signal['position_pct'] = signal['position_value'] / portfolio_value
            
            self.logger.info(f"✅ Positions scaled down by {scale_factor:.2f} to respect risk limits")
        
        return updated_signals
    
    def validate_position_sizing(self, signals: List[Dict], portfolio_value: float) -> bool:
        """Enhanced validation of position sizing"""
        total_position_value = sum(s.get('position_value', 0) for s in signals)
        total_risk = sum(s.get('risk_amount', 0) for s in signals)
        
        total_allocation_pct = total_position_value / portfolio_value
        total_risk_pct = total_risk / portfolio_value
        
        # Check allocation limits (more conservative)
        if total_allocation_pct > 0.90:  # Don't allocate more than 90%
            self.logger.error(f"❌ Over-allocation: {total_allocation_pct:.1%} > 90%")
            return False
        
        # Check risk limits
        if total_risk_pct > self.config.max_total_portfolio_risk:
            self.logger.error(f"❌ Excessive risk: {total_risk_pct:.2%} > {self.config.max_total_portfolio_risk:.2%}")
            return False
        
        # Check individual position risks
        for signal in signals:
            position_risk_pct = signal.get('risk_amount', 0) / portfolio_value
            if position_risk_pct > self.config.max_single_position_risk:
                self.logger.error(f"❌ Excessive single position risk for {signal.get('symbol', 'Unknown')}: {position_risk_pct:.2%}")
                return False
        
        self.logger.info(f"✅ Refined position sizing validation passed")
        self.logger.info(f"   Total allocation: {total_allocation_pct:.1%}")
        self.logger.info(f"   Total risk: {total_risk_pct:.2%}")
        
        return True


def demo_refined_sizing():
    """Demonstrate refined position sizing improvements"""
    print("📊 REFINED POSITION SIZING DEMONSTRATION")
    print("=" * 80)
    
    sizer = RefinedPositionSizer()
    portfolio_value = 1000000
    
    # Test scenarios with different regimes
    test_scenarios = [
        {'regime': 'bull', 'stock_price': 150, 'stop_pct': 0.03},
        {'regime': 'UP_LOWVOL', 'stock_price': 100, 'stop_pct': 0.025},
        {'regime': 'sideways', 'stock_price': 80, 'stop_pct': 0.04},
        {'regime': 'volatile', 'stock_price': 200, 'stop_pct': 0.05},
        {'regime': 'bear', 'stock_price': 50, 'stop_pct': 0.06}
    ]
    
    print(f"Portfolio Value: ${portfolio_value:,}")
    print(f"{'Regime':<12} {'Price':<8} {'Stop%':<8} {'Risk%':<8} {'Position':<12} {'Risk$':<10}")
    print("-" * 70)
    
    for scenario in test_scenarios:
        regime = scenario['regime']
        price = scenario['stock_price']
        stop_pct = scenario['stop_pct']
        stop_price = price * (1 - stop_pct)
        
        result = sizer.calculate_refined_position_size(
            entry_price=price,
            stop_loss_price=stop_price,
            portfolio_value=portfolio_value,
            regime=regime
        )
        
        print(f"{regime:<12} ${price:<7} {stop_pct:<7.1%} {result['regime_risk_pct']:<7.1%} "
              f"${result['position_value']:<11,.0f} ${result['risk_amount']:<9,.0f}")
    
    print("\n💡 KEY IMPROVEMENTS:")
    print("• Regime-dependent risk percentages (0.3% - 2.0%)")
    print("• Volatility-adjusted stop-losses")
    print("• Enhanced position size limits")
    print("• Better total portfolio risk management")


if __name__ == "__main__":
    demo_refined_sizing()

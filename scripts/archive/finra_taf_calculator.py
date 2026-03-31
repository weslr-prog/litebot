#!/usr/bin/env python3
"""
FINRA TAF Fee Calculator and Strategy Adjustment
Effective October 4, 2025 - New fee structure integration
"""

from datetime import datetime, date
from typing import Dict, List, Tuple
import logging

class FINRATAFCalculator:
    """
    FINRA Trading Activity Fee calculator for Alpaca
    Effective October 4, 2025
    """
    
    def __init__(self):
        self.taf_rate = 0.000166  # $0.000166 per share for sell orders
        self.max_fee_per_trade = 8.30  # $8.30 maximum per individual trade
        self.effective_date = date(2025, 10, 4)
        self.fee_threshold_shares = 50000  # Shares where max fee kicks in
        
        self.logger = logging.getLogger('FINRATAFCalculator')
        
    def is_new_fee_structure_active(self) -> bool:
        """Check if new fee structure is in effect"""
        return date.today() >= self.effective_date
    
    def calculate_taf_fee(self, shares: int, is_sell_order: bool = True) -> float:
        """
        Calculate TAF fee for a trade
        
        Args:
            shares: Number of shares in the trade
            is_sell_order: Whether this is a sell order (TAF only applies to sells)
            
        Returns:
            TAF fee in dollars
        """
        if not is_sell_order:
            return 0.0
            
        if not self.is_new_fee_structure_active():
            # Old structure - Alpaca subsidizes, return 0
            return 0.0
            
        # New structure - per-trade basis
        base_fee = shares * self.taf_rate
        actual_fee = min(base_fee, self.max_fee_per_trade)
        
        return round(actual_fee, 2)
    
    def calculate_breakeven_impact(self, shares: int, price: float) -> Dict:
        """
        Calculate how TAF fee affects breakeven price
        
        Args:
            shares: Number of shares
            price: Price per share
            
        Returns:
            Dictionary with fee impact analysis
        """
        taf_fee = self.calculate_taf_fee(shares, is_sell_order=True)
        trade_value = shares * price
        
        # Fee as percentage of trade value
        fee_percentage = (taf_fee / trade_value) * 100 if trade_value > 0 else 0
        
        # Additional price movement needed to overcome fee
        breakeven_adjustment = taf_fee / shares if shares > 0 else 0
        
        return {
            'taf_fee': taf_fee,
            'fee_percentage': round(fee_percentage, 4),
            'breakeven_adjustment': round(breakeven_adjustment, 4),
            'is_high_impact': fee_percentage > 0.1,  # Flag if fee > 0.1% of trade
            'recommended_min_gain': round(breakeven_adjustment * 2, 4)  # 2x fee to be profitable
        }
    
    def optimize_position_size(self, target_value: float, price: float) -> Dict:
        """
        Optimize position size considering TAF fees
        
        Args:
            target_value: Target dollar amount to invest
            price: Current stock price
            
        Returns:
            Optimized position recommendations
        """
        base_shares = int(target_value / price)
        
        # Analyze different position sizes
        options = []
        
        # Check current size
        current_analysis = self.calculate_breakeven_impact(base_shares, price)
        options.append({
            'shares': base_shares,
            'value': base_shares * price,
            'analysis': current_analysis,
            'type': 'target'
        })
        
        # Check if we're near the fee threshold (50k shares)
        if base_shares > 45000:  # Within 5k of threshold
            # Option 1: Stay under threshold
            under_threshold = 49999
            under_analysis = self.calculate_breakeven_impact(under_threshold, price)
            options.append({
                'shares': under_threshold,
                'value': under_threshold * price,
                'analysis': under_analysis,
                'type': 'under_threshold'
            })
            
            # Option 2: Go well over threshold to amortize fee
            over_threshold = max(base_shares, 60000)
            over_analysis = self.calculate_breakeven_impact(over_threshold, price)
            options.append({
                'shares': over_threshold,
                'value': over_threshold * price,
                'analysis': over_analysis,
                'type': 'over_threshold'
            })
        
        # Find most cost-efficient option
        best_option = min(options, key=lambda x: x['analysis']['fee_percentage'])
        
        return {
            'options': options,
            'recommended': best_option,
            'fee_optimization_active': self.is_new_fee_structure_active()
        }

class TAFAwareRiskManager:
    """
    Enhanced risk manager that considers TAF fees in position sizing
    """
    
    def __init__(self, base_risk_manager, portfolio_size: float = 100000):
        self.base_risk_manager = base_risk_manager
        self.portfolio_size = portfolio_size
        self.taf_calculator = FINRATAFCalculator()
        self.logger = logging.getLogger('TAFAwareRiskManager')
        
    def assess_risk_with_fees(self, symbol: str, df, current_price: float, 
                             intended_shares: int) -> Dict:
        """
        Assess risk including TAF fee impact
        
        Args:
            symbol: Stock symbol
            df: Price data DataFrame
            current_price: Current stock price
            intended_shares: Intended position size
            
        Returns:
            Enhanced risk assessment including fee impact
        """
        # Get base risk assessment
        base_risk = self.base_risk_manager.assess_risk(symbol, df)
        
        # Calculate TAF impact
        fee_impact = self.taf_calculator.calculate_breakeven_impact(
            intended_shares, current_price
        )
        
        # Adjust confidence based on fee impact
        original_confidence = base_risk.get('confidence', 0.5)
        
        # Reduce confidence if fees are high relative to expected returns
        if fee_impact['fee_percentage'] > 0.05:  # If fee > 0.05% of trade
            fee_penalty = min(0.2, fee_impact['fee_percentage'] / 100)
            adjusted_confidence = original_confidence - fee_penalty
        else:
            adjusted_confidence = original_confidence
            
        # Enhanced risk assessment
        enhanced_risk = {
            **base_risk,
            'adjusted_confidence': max(0.1, adjusted_confidence),
            'taf_fee_impact': fee_impact,
            'fee_adjusted': True,
            'trade_recommended': adjusted_confidence > 0.4 and fee_impact['fee_percentage'] < 0.15
        }
        
        return enhanced_risk
    
    def optimize_position_size_with_fees(self, symbol: str, target_value: float, 
                                       current_price: float) -> Dict:
        """
        Optimize position size considering both risk and TAF fees
        
        Args:
            symbol: Stock symbol
            target_value: Target investment amount
            current_price: Current stock price
            
        Returns:
            Optimized position size recommendation
        """
        # Get TAF-optimized position sizing
        optimization = self.taf_calculator.optimize_position_size(target_value, current_price)
        
        # Apply risk management constraints
        max_position_value = self.portfolio_size * 0.1  # Max 10% per position
        
        # Filter options by risk constraints
        valid_options = []
        for option in optimization['options']:
            if option['value'] <= max_position_value:
                valid_options.append(option)
                
        if not valid_options:
            # If no options fit risk constraints, scale down
            max_shares = int(max_position_value / current_price)
            fallback_analysis = self.taf_calculator.calculate_breakeven_impact(
                max_shares, current_price
            )
            valid_options = [{
                'shares': max_shares,
                'value': max_shares * current_price,
                'analysis': fallback_analysis,
                'type': 'risk_constrained'
            }]
        
        # Select best option
        recommended = min(valid_options, key=lambda x: x['analysis']['fee_percentage'])
        
        self.logger.info(f"Position optimization for {symbol}: "
                        f"{recommended['shares']} shares, "
                        f"TAF fee: ${recommended['analysis']['taf_fee']:.2f} "
                        f"({recommended['analysis']['fee_percentage']:.3f}%)")
        
        return {
            'recommended_shares': recommended['shares'],
            'recommended_value': recommended['value'],
            'taf_fee': recommended['analysis']['taf_fee'],
            'fee_percentage': recommended['analysis']['fee_percentage'],
            'all_options': valid_options,
            'optimization_applied': True
        }

def create_taf_aware_strategy_summary() -> str:
    """Create a summary of TAF-aware trading strategy adjustments"""
    
    summary = """
🎯 FINRA TAF Fee Integration Strategy (Effective Oct 4, 2025)

📊 Fee Structure:
• Rate: $0.000166 per share (sell orders only)
• Cap: $8.30 per individual trade (not daily cumulative)
• Threshold: 50,000+ shares hit maximum fee

💡 Strategic Adjustments:

1. POSITION SIZING OPTIMIZATION
   • Avoid 45,000-50,000 share range (inefficient fee zone)
   • Either stay under 50k shares OR go significantly over
   • Target 49,999 shares max for smaller positions
   • For large positions, consider 60k+ shares to amortize fee

2. TRADE TIMING
   • Combine smaller sells into larger single trades when possible
   • Avoid multiple large sells in same day (each gets $8.30 cap)
   • Consider partial position management strategy

3. PROFIT TARGETS
   • Add TAF fee to breakeven calculations
   • Minimum profit target = 2x TAF fee per share
   • For 50k+ shares: need $0.00033+ per share extra profit

4. RISK MANAGEMENT
   • Reduce position confidence if TAF fee > 0.05% of trade value
   • Flag trades where fee > 0.15% as high-cost
   • Prioritize longer hold periods for large positions

📈 Implementation in Sprint 1:
✅ Automatic fee calculation for all sell orders
✅ Position size optimization recommendations  
✅ Risk assessment adjusted for fee impact
✅ Dashboard integration showing fee costs
✅ Export includes fee analysis data

🎯 Expected Impact:
• Small positions (<50k shares): Minimal impact
• Large positions (50k+ shares): $8.30 per sell trade
• Strategy: Favor quality over quantity trades
• Focus: Higher conviction, longer duration trades
"""
    
    return summary

# Integration test
def test_taf_integration():
    """Test the TAF fee integration"""
    
    calculator = FINRATAFCalculator()
    
    print("🧪 Testing FINRA TAF Fee Integration")
    print("=" * 50)
    
    # Test different trade sizes
    test_cases = [
        (1000, 50.00, "Small trade"),
        (25000, 100.00, "Medium trade"),
        (49999, 75.00, "Just under threshold"),
        (50000, 60.00, "At threshold"),
        (75000, 40.00, "Large trade"),
        (100000, 25.00, "Very large trade")
    ]
    
    for shares, price, description in test_cases:
        fee = calculator.calculate_taf_fee(shares, is_sell_order=True)
        impact = calculator.calculate_breakeven_impact(shares, price)
        
        print(f"\n{description}:")
        print(f"  Shares: {shares:,}")
        print(f"  Price: ${price:.2f}")
        print(f"  Trade Value: ${shares * price:,.2f}")
        print(f"  TAF Fee: ${fee:.2f}")
        print(f"  Fee %: {impact['fee_percentage']:.4f}%")
        print(f"  Breakeven Adjustment: ${impact['breakeven_adjustment']:.4f}")
        print(f"  High Impact: {'⚠️ Yes' if impact['is_high_impact'] else '✅ No'}")
    
    print(f"\n📊 Strategy Summary:")
    print(create_taf_aware_strategy_summary())

if __name__ == "__main__":
    test_taf_integration()

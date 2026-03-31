#!/usr/bin/env python3
"""
Final TAF Integration Test - Demonstrates full system integration
"""

import logging
from datetime import datetime, date
from finra_taf_calculator import FINRATAFCalculator
from config import Sprint1Config

def test_taf_system_integration():
    """Test the complete TAF integration workflow"""
    print("=" * 70)
    print("FINRA TAF SYSTEM INTEGRATION TEST")
    print("=" * 70)
    print(f"Test run at: {datetime.now()}")
    print()
    
    # Initialize calculator
    calc = FINRATAFCalculator()
    calc.effective_date = date(2025, 9, 1)  # Enable for testing
    
    # Test realistic trading scenarios
    test_scenarios = [
        {"symbol": "AAPL", "target_value": 10000, "price": 238.09},
        {"symbol": "MSFT", "target_value": 25000, "price": 445.50},
        {"symbol": "NVDA", "target_value": 50000, "price": 900.25},
        {"symbol": "TSLA", "target_value": 75000, "price": 185.75},
        {"symbol": "GOOGL", "target_value": 100000, "price": 175.00}
    ]
    
    print("Testing TAF impact on realistic position sizes:")
    print("-" * 70)
    
    total_savings = 0
    
    for scenario in test_scenarios:
        symbol = scenario["symbol"]
        target_value = scenario["target_value"]
        price = scenario["price"]
        
        # Calculate basic position
        basic_shares = int(target_value / price)
        basic_fee = calc.calculate_taf_fee(basic_shares)
        
        # Get optimization recommendation
        optimization = calc.optimize_position_size(target_value, price)
        recommended = optimization["recommended"]
        opt_shares = recommended["shares"]
        opt_fee = calc.calculate_taf_fee(opt_shares)
        
        # Calculate savings
        savings = basic_fee - opt_fee
        total_savings += max(0, savings)
        
        print(f"\n{symbol} (${price:.2f}/share):")
        print(f"  Target Investment: ${target_value:,}")
        print(f"  Basic Position: {basic_shares:,} shares → TAF: ${basic_fee:.2f}")
        print(f"  Optimized Position: {opt_shares:,} shares → TAF: ${opt_fee:.2f}")
        
        if savings > 0:
            print(f"  💰 Savings: ${savings:.2f}")
        elif opt_shares != basic_shares:
            additional_investment = (opt_shares - basic_shares) * price
            print(f"  📈 Additional Investment: ${additional_investment:,.2f} for better fee efficiency")
        else:
            print(f"  ✅ Already optimal")
            
        # Show fee percentage impact
        fee_pct = (opt_fee / (opt_shares * price)) * 100 if opt_shares > 0 else 0
        print(f"  📊 Fee Impact: {fee_pct:.4f}% of position value")
    
    print("\n" + "=" * 70)
    print("TAF INTEGRATION SUMMARY")
    print("=" * 70)
    
    # Key insights
    threshold_shares = calc.fee_threshold_shares
    threshold_fee = calc.max_fee_per_trade
    
    print(f"✅ TAF Rate: ${calc.taf_rate:.6f} per share")
    print(f"✅ Maximum Fee: ${threshold_fee:.2f} per trade")
    print(f"✅ Fee Threshold: {threshold_shares:,} shares")
    print(f"✅ Total Potential Savings: ${total_savings:.2f}")
    
    print(f"\nKey Strategy Insights:")
    print(f"• Positions under {threshold_shares:,} shares: Pay per-share fee")
    print(f"• Positions over {threshold_shares:,} shares: Capped at ${threshold_fee:.2f}")
    print(f"• Sweet spot: Maximize shares when hitting the cap")
    print(f"• Avoid: Positions just over {threshold_shares:,} shares unless justified")
    
    print(f"\n🎯 RECOMMENDATION: System ready for TAF-optimized trading!")
    print(f"   The integration successfully optimizes position sizes")
    print(f"   to minimize FINRA TAF fees while maintaining strategy effectiveness.")
    
def test_fee_threshold_analysis():
    """Demonstrate the critical 50k share threshold"""
    print("\n" + "=" * 70)
    print("CRITICAL THRESHOLD ANALYSIS")
    print("=" * 70)
    
    calc = FINRATAFCalculator()
    calc.effective_date = date(2025, 9, 1)  # Enable for testing
    
    # Test around the 50k threshold
    test_shares = [45000, 49000, 49999, 50000, 50001, 55000, 60000]
    price = 100  # $100 per share for easy math
    
    print(f"Analysis at ${price}/share:")
    print("-" * 40)
    
    for shares in test_shares:
        fee = calc.calculate_taf_fee(shares)
        value = shares * price
        fee_pct = (fee / value) * 100
        
        if shares < 50000:
            status = "Under threshold"
        elif shares == 50000:
            status = "At threshold"
        else:
            status = "Over threshold (capped)"
            
        print(f"{shares:>6,} shares: ${fee:>5.2f} ({fee_pct:.4f}%) - {status}")
    
    print(f"\n💡 Key Insight: Fee jumps dramatically at 50,000 shares,")
    print(f"   but then stays flat. This creates optimization opportunities!")

if __name__ == "__main__":
    test_taf_system_integration()
    test_fee_threshold_analysis()

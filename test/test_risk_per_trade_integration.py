#!/usr/bin/env python3
"""
Test: Risk-Per-Trade Position Sizing Implementation
Demonstrates the superior risk management approach integrated into the trading bot
"""

import sys
import os
sys.path.append('/home/wes/Desktop/litebotx-usb-deployment')

import numpy as np
import pandas as pd
from risk_per_trade_sizer import RiskPerTradeSizer, RiskPerTradeConfig
from adaptive_risk_manager import AdaptiveRiskManager


def create_test_market_data():
    """Create test market data for different types of stocks"""
    stocks = {
        'AAPL': {'price': 175, 'volatility': 0.25},   # High price, moderate vol
        'TSLA': {'price': 250, 'volatility': 0.45},   # High price, high vol  
        'AMD': {'price': 100, 'volatility': 0.35},    # Moderate price, high vol
        'KO': {'price': 60, 'volatility': 0.15},      # Low price, low vol
        'NVDA': {'price': 450, 'volatility': 0.40}    # Very high price, high vol
    }
    
    market_data = {}
    for symbol, data in stocks.items():
        # Create 100 days of synthetic price data
        base_price = data['price']
        volatility = data['volatility']
        
        # Generate returns
        returns = np.random.normal(0.001, volatility/np.sqrt(252), 100)  # Daily returns
        
        # Generate prices
        prices = [base_price]
        for ret in returns:
            prices.append(prices[-1] * (1 + ret))
            
        # Create DataFrame
        market_data[symbol] = pd.DataFrame({
            'close': prices[1:],  # Skip first price
            'volume': np.random.randint(1000000, 5000000, 100)
        })
        
    return market_data


def test_risk_per_trade_sizing():
    """Test the risk-per-trade sizing with real-world scenarios"""
    print("🧪 TESTING RISK-PER-TRADE POSITION SIZING INTEGRATION")
    print("=" * 80)
    
    # Setup
    portfolio_value = 500000  # $500k portfolio
    
    # Initialize components
    risk_config = RiskPerTradeConfig(
        risk_per_trade_pct=0.005,    # 0.5% risk per trade
        max_position_pct=0.15,       # 15% max position
        min_position_value=2000,     # $2k minimum
        default_stop_loss_pct=0.03   # 3% default stop
    )
    
    sizer = RiskPerTradeSizer(risk_config)
    
    # Initialize adaptive risk manager for dynamic stops
    adaptive_risk = AdaptiveRiskManager(portfolio_value)
    
    # Create test signals
    signals = [
        {'symbol': 'AAPL', 'momentum_score': 1.2, 'quality': 'good'},
        {'symbol': 'TSLA', 'momentum_score': 0.8, 'quality': 'fair'},
        {'symbol': 'AMD', 'momentum_score': 1.5, 'quality': 'excellent'},
        {'symbol': 'KO', 'momentum_score': 0.6, 'quality': 'fair'},
        {'symbol': 'NVDA', 'momentum_score': 1.0, 'quality': 'good'}
    ]
    
    # Create market data
    market_data = create_test_market_data()
    
    print(f"📊 TEST SCENARIO:")
    print(f"   Portfolio Value: ${portfolio_value:,}")
    print(f"   Risk Per Trade: {risk_config.risk_per_trade_pct:.2%} = ${portfolio_value * risk_config.risk_per_trade_pct:,.0f}")
    print(f"   Signals to Size: {len(signals)}")
    
    # Get current adaptive risk parameters
    adaptive_params = adaptive_risk.get_current_parameters()
    print(f"   Adaptive Stop-Loss: {adaptive_params.stop_loss_pct:.1%}")
    
    print(f"\n🔍 INDIVIDUAL STOCK ANALYSIS:")
    print("-" * 80)
    
    for signal in signals:
        symbol = signal['symbol']
        entry_price = market_data[symbol]['close'].iloc[-1]
        stop_loss_pct = adaptive_params.stop_loss_pct
        stop_loss_price = entry_price * (1 - stop_loss_pct)
        
        # Calculate position using risk-per-trade method
        position_data = sizer.calculate_position_size_by_risk(
            entry_price=entry_price,
            stop_loss_price=stop_loss_price,
            portfolio_value=portfolio_value
        )
        
        risk_per_share = entry_price - stop_loss_price
        
        print(f"{symbol:<5} | ${entry_price:>7.2f} entry | ${stop_loss_price:>7.2f} stop ({stop_loss_pct:.1%}) | ${risk_per_share:>5.2f}/share")
        if position_data['shares'] > 0:
            print(f"      | {position_data['shares']:>4} shares | ${position_data['position_value']:>8,.0f} position ({position_data['position_pct']:.1%})")
            print(f"      | Risk: ${position_data['risk_amount']:>6.0f} | Quality: {signal['quality']}")
        else:
            print(f"      | ❌ {position_data.get('error', 'Position sizing failed')}")
        print()
    
    # Calculate complete portfolio allocation
    print("🎯 COMPLETE PORTFOLIO ALLOCATION:")
    print("-" * 80)
    
    sized_signals = sizer.calculate_positions_for_signals(
        signals, market_data, portfolio_value, adaptive_risk
    )
    
    # Validation
    if sizer.validate_position_sizing(sized_signals, portfolio_value):
        print("✅ Portfolio allocation validation passed")
    else:
        print("❌ Portfolio allocation validation failed")
    
    # Summary comparison with old method
    print(f"\n📈 RISK-PER-TRADE vs. PORTFOLIO % COMPARISON:")
    print("-" * 80)
    
    total_risk = sum(s.get('risk_amount', 0) for s in sized_signals)
    total_positions = sum(s.get('position_value', 0) for s in sized_signals)
    avg_position_pct = (total_positions / len(sized_signals) / portfolio_value) if sized_signals else 0
    
    print(f"Risk-Per-Trade Method:")
    print(f"   Total Risk: ${total_risk:,.0f} ({total_risk/portfolio_value:.2%})")
    print(f"   Total Allocation: ${total_positions:,.0f} ({total_positions/portfolio_value:.1%})")
    print(f"   Avg Position Size: {avg_position_pct:.1%}")
    print(f"   Position Count: {len(sized_signals)}")
    
    # Compare with fixed 8% method
    fixed_position_value = portfolio_value * 0.08  # Old 8% method
    print(f"\nOld Portfolio % Method (8% each):")
    print(f"   Each Position: ${fixed_position_value:,.0f} (8.0%)")
    print(f"   Total If All Filled: ${fixed_position_value * len(signals):,.0f} ({8 * len(signals):.0%})")
    print(f"   Risk Varies by Stop Distance: Unknown/Inconsistent")
    
    print(f"\n💡 IMPROVEMENTS:")
    print("   ✅ Consistent risk exposure across all trades")
    print("   ✅ Position size reflects actual risk (stop distance)")
    print("   ✅ Better capital allocation efficiency")
    print("   ✅ Reduced risk of oversized positions in volatile stocks")
    print("   ✅ Adaptive stop-loss integration")
    
    return sized_signals


if __name__ == "__main__":
    test_risk_per_trade_sizing()

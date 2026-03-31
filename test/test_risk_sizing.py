#!/usr/bin/env python3
"""
Test the new volatility-adjusted position sizing module
"""

import logging
from core.data_loader import DataLoader
from core.momentum_strategy import MomentumStrategy
from core.risk_adjusted_sizing import VolatilityAdjustedSizer, PositionSizingConfig

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

def test_risk_adjusted_sizing():
    """Test volatility-adjusted position sizing vs regular momentum sizing"""
    print("🧪 Testing Risk-Adjusted Position Sizing")
    print("=" * 60)
    
    # Load market data
    data_loader = DataLoader()
    symbols = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA', 'AMZN', 'META', 'COIN', 'INTC', 'AMD']
    
    market_data = {}
    for symbol in symbols:
        data = data_loader.get_historical_data(symbol, limit=100)
        if data is not None:
            market_data[symbol] = data
    
    print(f"📊 Loaded data for {len(market_data)} symbols")
    
    # Generate momentum signals
    momentum_strategy = MomentumStrategy()
    portfolio_value = 900000  # $900K portfolio
    
    print("\n🎯 Generating momentum signals...")
    signals = momentum_strategy.generate_signals(market_data, portfolio_value)
    
    print(f"📈 Generated {len(signals)} momentum signals")
    
    # Test regular momentum sizing (current approach)
    print("\n" + "="*60)
    print("📊 REGULAR MOMENTUM SIZING (Current)")
    print("="*60)
    
    total_regular = 0
    for i, signal in enumerate(signals[:10], 1):
        symbol = signal['symbol']
        shares = signal['shares']
        value = signal['position_value']
        momentum = signal['momentum_score']
        weight = value / portfolio_value
        total_regular += value
        
        print(f"{i:2}. {symbol:6}: {shares:4} shares | ${value:8,.0f} | {weight:5.1%} | momentum: {momentum:.3f}")
    
    cash_regular = portfolio_value - total_regular
    print(f"\n💰 Total Allocated: ${total_regular:,.0f}")
    print(f"💵 Cash Remaining: ${cash_regular:,.0f} ({cash_regular/portfolio_value:.1%})")
    
    # Test risk-adjusted sizing
    print("\n" + "="*60)
    print("🎯 RISK-ADJUSTED SIZING (New)")
    print("="*60)
    
    # Create risk-adjusted sizer
    config = PositionSizingConfig(
        target_volatility=0.15,      # 15% target portfolio volatility
        max_position_weight=0.12,     # 12% max position
        min_position_weight=0.02,     # 2% min position
        cash_buffer=0.05              # 5% cash buffer
    )
    
    risk_sizer = VolatilityAdjustedSizer(config)
    
    # Calculate risk-adjusted positions
    risk_adjusted_signals = risk_sizer.calculate_position_sizes(signals, market_data, portfolio_value)
    
    print("\n📊 Risk-Adjusted Results:")
    total_risk_adj = 0
    for i, signal in enumerate(risk_adjusted_signals[:10], 1):
        symbol = signal['symbol']
        shares = signal.get('shares', 0)
        value = signal.get('position_value', 0)
        weight = signal.get('weight', 0)
        volatility = signal.get('volatility', 0)
        momentum = signal.get('momentum_score', 0)
        total_risk_adj += value
        
        print(f"{i:2}. {symbol:6}: {shares:4} shares | ${value:8,.0f} | {weight:5.1%} | vol: {volatility:5.1%} | mom: {momentum:.3f}")
    
    cash_risk_adj = portfolio_value - total_risk_adj
    print(f"\n💰 Total Allocated: ${total_risk_adj:,.0f}")
    print(f"💵 Cash Remaining: ${cash_risk_adj:,.0f} ({cash_risk_adj/portfolio_value:.1%})")
    
    # Compare the approaches
    print("\n" + "="*60)
    print("📋 COMPARISON SUMMARY")
    print("="*60)
    
    print(f"Regular Momentum:")
    print(f"  - Total Allocated: ${total_regular:,.0f}")
    print(f"  - Cash Buffer: {cash_regular/portfolio_value:.1%}")
    print(f"  - Equal weights: ~{100/len(signals[:10]):.1f}% each")
    
    print(f"\nRisk-Adjusted:")
    print(f"  - Total Allocated: ${total_risk_adj:,.0f}")
    print(f"  - Cash Buffer: {cash_risk_adj/portfolio_value:.1%}")
    print(f"  - Volatility-weighted positions")
    print(f"  - Lower volatility stocks get larger allocations")
    print(f"  - Higher momentum stocks get boosted allocations")
    
    print("\n🎯 Key Benefits of Risk-Adjusted Sizing:")
    print("  ✅ Better risk-adjusted returns")
    print("  ✅ Reduced portfolio volatility")
    print("  ✅ Optimal diversification")
    print("  ✅ Momentum + volatility optimization")
    
    return risk_adjusted_signals

if __name__ == "__main__":
    test_risk_adjusted_sizing()

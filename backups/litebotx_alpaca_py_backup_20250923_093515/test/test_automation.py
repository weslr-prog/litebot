#!/usr/bin/env python3
"""Quick test of automated trading features"""

from automated_momentum_trader import AutomatedMomentumTrader

def main():
    print("🧪 Testing Automated Momentum Trader")
    print("=" * 50)
    
    # Create trader
    trader = AutomatedMomentumTrader()
    
    # Show portfolio summary
    print("\n📊 Current Portfolio:")
    trader.portfolio_summary()
    
    print("\n🧪 Testing one momentum cycle...")
    trader.execute_momentum_cycle()
    
    print("\n✅ Test complete!")

if __name__ == "__main__":
    main()

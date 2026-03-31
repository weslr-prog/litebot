#!/usr/bin/env python3

"""Test portfolio value extraction from real Alpaca engine"""

from traders.short_cycle_trader import ShortCycleTrader, ShortCycleConfig

def test_portfolio_fix():
    print("🧪 Testing Portfolio Value Fix")
    print("=" * 50)
    
    try:
        config = ShortCycleConfig()
        trader = ShortCycleTrader(config)
        
        # Test direct engine access
        if hasattr(trader, 'execution_engine'):
            portfolio_summary = trader.execution_engine.get_portfolio_summary()
            print(f"📊 Raw portfolio summary: {portfolio_summary}")
            
            if portfolio_summary and 'account' in portfolio_summary:
                account_info = portfolio_summary['account']
                print(f"💰 Account portfolio value: ${account_info.get('portfolio_value', 0):,.2f}")
                print(f"💵 Account cash: ${account_info.get('cash', 0):,.2f}")
                print(f"⚡ Account buying power: ${account_info.get('buying_power', 0):,.2f}")
        
        # Test trader's portfolio value method
        portfolio_value = trader._get_portfolio_value()
        print(f"\n✅ Trader portfolio value: ${portfolio_value:,.2f}")
        
        # Test risk limit updates
        trader._update_risk_limits()
        print(f"🛑 Daily loss limit: ${trader.config.max_daily_loss_dollars:.2f}")
        print(f"🛑 Weekly loss limit: ${trader.config.max_weekly_loss_dollars:.2f}")
        
    except Exception as e:
        print(f"❌ Error testing portfolio: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_portfolio_fix()
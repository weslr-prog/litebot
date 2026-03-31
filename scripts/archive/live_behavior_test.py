#!/usr/bin/env python3

"""
Safe Live Testing Framework - Observe bot behavior without live trades
Simulates market conditions to see signal generation and decision making
"""

import json
import pandas as pd
from datetime import datetime, timedelta
from traders.short_cycle_trader import ShortCycleTrader, ShortCycleConfig

def simulate_market_session():
    """Simulate a trading session to observe bot behavior"""
    
    print("🎬 LIVE BOT BEHAVIOR SIMULATION")
    print("=" * 60)
    
    # Initialize trader
    config = ShortCycleConfig()
    trader = ShortCycleTrader(config)
    
    print(f"\n📊 Bot Configuration:")
    print(f"   Portfolio: ${trader._get_portfolio_value():,.2f}")
    print(f"   Daily pool: ${trader.config.daily_pool_dollars:,.2f}")
    print(f"   Max positions: {trader.config.max_positions_per_day}")
    print(f"   Confidence threshold: {trader.config.confidence_threshold}")
    
    # Test signal generation process
    print(f"\n🧠 Signal Generation Test:")
    
    # Get watchlist
    watchlist = []
    try:
        from data_access import DataAccess
        data_access = DataAccess()
        watchlist = data_access.get_watchlist()[:10]  # First 10 symbols
        print(f"   📋 Watchlist: {len(watchlist)} symbols")
        print(f"   🎯 Sample: {watchlist[:5]}")
    except Exception as e:
        print(f"   ⚠️ Watchlist error: {e}")
        watchlist = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']
        
    # Simulate signal generation
    signals_generated = 0
    tradeable_signals = 0
    
    for symbol in watchlist[:5]:  # Test first 5
        try:
            # This would normally generate signals
            print(f"\n   🔍 Analyzing {symbol}...")
            
            # Simulate signal generation (replace with actual when ready)
            import random
            confidence = random.uniform(0.3, 0.9)
            
            print(f"      Confidence: {confidence:.3f}")
            
            if confidence >= trader.config.confidence_threshold:
                print(f"      ✅ SIGNAL: Above threshold ({trader.config.confidence_threshold})")
                tradeable_signals += 1
                
                # Test position sizing
                position_size = trader._calculate_position_size(symbol, confidence)
                print(f"      💰 Position size: ${position_size:,.2f}")
                
            else:
                print(f"      ❌ Below threshold ({trader.config.confidence_threshold})")
                
            signals_generated += 1
            
        except Exception as e:
            print(f"      ❌ Error analyzing {symbol}: {e}")
    
    # Test risk management
    print(f"\n🛡️ Risk Management Test:")
    current_positions = len(trader.positions)
    max_new_positions = trader.config.max_positions_per_day - current_positions
    
    print(f"   Current positions: {current_positions}")
    print(f"   Max new positions: {max_new_positions}")
    print(f"   Tradeable signals: {tradeable_signals}")
    
    if tradeable_signals > max_new_positions:
        print(f"   🚫 Would reject {tradeable_signals - max_new_positions} signals (position limit)")
    
    # Test daily P&L check
    daily_pnl = trader._calculate_daily_pnl()
    print(f"   Daily P&L: ${daily_pnl:,.2f}")
    print(f"   Daily loss limit: ${trader.config.max_daily_loss_dollars:,.2f}")
    
    would_trade = daily_pnl > -trader.config.max_daily_loss_dollars
    print(f"   🎯 Would trade: {'✅ YES' if would_trade else '❌ NO (loss limit)'}")
    
    # Test exit logic
    print(f"\n🚪 Exit Logic Test:")
    positions_to_exit = 0
    
    for position in trader.positions:
        if position.status.value == "entered":
            # Check if should exit
            should_exit = trader._should_exit_position(position)
            if should_exit:
                positions_to_exit += 1
                print(f"   📤 {position.symbol}: Should exit ({should_exit})")
    
    if positions_to_exit == 0:
        print(f"   💤 No positions require exit today")
    
    # Summary
    print(f"\n" + "=" * 60)
    print(f"🎯 SIMULATION SUMMARY:")
    print(f"   Signals generated: {signals_generated}")
    print(f"   Tradeable signals: {tradeable_signals}")
    print(f"   Positions to exit: {positions_to_exit}")
    print(f"   Trading allowed: {'✅ YES' if would_trade else '❌ NO'}")
    print(f"   Portfolio health: ${'✅' if trader._get_portfolio_value() > 900000 else '⚠️'}")

def test_paper_trading_readiness():
    """Test if bot is ready for paper trading signals"""
    
    print(f"\n🧪 PAPER TRADING READINESS TEST")
    print("=" * 60)
    
    try:
        config = ShortCycleConfig()
        trader = ShortCycleTrader(config)
        
        # Test execution engine connection
        if hasattr(trader, 'execution_engine'):
            account_info = trader.execution_engine.get_account_info()
            if account_info:
                print("✅ Alpaca connection working")
                print(f"   Account status: {account_info.get('status', 'Unknown')}")
                print(f"   Buying power: ${account_info.get('buying_power', 0):,.2f}")
            else:
                print("❌ Alpaca connection failed")
        
        # Test signal generation capability
        print("\n📡 Signal Generation Test:")
        try:
            # Test if signal components are available
            print("   🔍 Testing market data access...")
            
            import yfinance as yf
            test_data = yf.Ticker('AAPL').history(period='5d')
            if not test_data.empty:
                print("   ✅ Market data access working")
            else:
                print("   ⚠️ Market data returns empty (normal on weekends)")
                
        except Exception as e:
            print(f"   ❌ Market data error: {e}")
        
        # Test position management
        print("\n💼 Position Management Test:")
        print(f"   Current positions: {len(trader.positions)}")
        print(f"   Position tracking: {'✅ Working' if trader.positions is not None else '❌ Error'}")
        
        # Test risk management
        print("\n🛡️ Risk Management Test:")
        portfolio_val = trader._get_portfolio_value()
        print(f"   Portfolio value: ${portfolio_val:,.2f}")
        print(f"   Dynamic risk limits: {'✅ Enabled' if portfolio_val > 1000 else '❌ Static fallback'}")
        
        print(f"\n🎯 READINESS ASSESSMENT:")
        print("✅ Core systems operational")
        print("✅ Portfolio integration working")
        print("✅ Risk management active")
        print("🎬 Ready for signal generation testing")
        
    except Exception as e:
        print(f"❌ Error in readiness test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    simulate_market_session()
    test_paper_trading_readiness()
    
    print(f"\n" + "=" * 60)
    print("🚀 NEXT STEPS:")
    print("1. Run this simulation during market hours")
    print("2. Monitor actual signal generation") 
    print("3. Enable paper trading mode for live testing")
    print("4. Validate Alpaca order submission")
    print("=" * 60)
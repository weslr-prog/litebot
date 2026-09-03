#!/usr/bin/env python3
"""
Test LiteBotX Momentum Strategy with Real Paper Trading
Generate signals and place actual paper trades
"""

import logging
from datetime import datetime
from connect_real_trading import RealPaperTradingEngine
from core.momentum_strategy import MomentumStrategy
from core.data_loader import DataLoader

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def test_momentum_with_real_trading():
    """Test momentum strategy with real paper trading"""
    
    print("🚀 Testing LiteBotX Momentum Strategy with Real Paper Trading")
    print("=" * 60)
    
    # Initialize components
    print("📊 Initializing components...")
    data_loader = DataLoader()
    momentum_strategy = MomentumStrategy()
    execution_engine = RealPaperTradingEngine()
    
    # Get current account status
    print("\n💰 Current Account Status:")
    account_info = execution_engine.get_account_info()
    if account_info:
        print(f"   Portfolio Value: ${account_info['portfolio_value']:,.2f}")
        print(f"   Cash Available: ${account_info['cash']:,.2f}")
        print(f"   Buying Power: ${account_info['buying_power']:,.2f}")
    
    # Get current positions
    print("\n📈 Current Positions:")
    positions = execution_engine.get_positions()
    if positions:
        for symbol, pos in positions.items():
            pnl = pos['unrealized_pnl']
            print(f"   {symbol}: {pos['quantity']} shares @ ${pos['avg_cost']:.2f} (P&L: ${pnl:+.2f})")
    else:
        print("   No current positions")
    
    # Generate momentum signals
    print("\n🎯 Generating Momentum Signals...")
    try:
        # Load universe data for signal generation
        print("   📚 Loading universe data...")
        universe_data = data_loader.load_universe_data()
        
        if not universe_data:
            print("   ❌ Failed to load universe data")
            return
        
        account_value = account_info["portfolio_value"] if account_info else 10000
        signals = momentum_strategy.generate_signals(universe_data, account_value)        
        if signals and len(signals) > 0:
            print(f"✅ Generated {len(signals)} momentum signals:")
            
            for signal in signals[:5]:  # Show first 5 signals
                symbol = signal['symbol']
                position_size = signal['position_size']
                signal_strength = signal.get('signal_strength', 'N/A')
                
                print(f"   📊 {symbol}: {position_size} shares (strength: {signal_strength})")
            
            # Ask user if they want to place trades
            print(f"\n📋 Ready to place {len(signals)} momentum trades")
            print("   This will place actual paper trades in your Alpaca account")
            
            response = input("\n❓ Place these trades? (y/N): ").strip().lower()
            
            if response == 'y':
                print("\n🔄 Placing trades...")
                successful_trades = 0
                
                for signal in signals:
                    symbol = signal['symbol']
                    quantity = signal['position_size']
                    
                    if quantity > 0:
                        print(f"   📤 Buying {quantity} shares of {symbol}...")
                        
                        result = execution_engine.submit_order(
                            symbol=symbol,
                            quantity=quantity,
                            side='buy'
                        )
                        
                        if result:
                            print(f"   ✅ Order placed: {result['order_id']}")
                            successful_trades += 1
                        else:
                            print(f"   ❌ Failed to place order for {symbol}")
                        
                        # Small delay between orders
                        import time
                        time.sleep(1)
                
                print(f"\n📊 Trading Summary:")
                print(f"   ✅ Successful trades: {successful_trades}/{len(signals)}")
                print(f"   📈 Your bot is now actively paper trading!")
                
            else:
                print("   ⏸️  Trading cancelled - no orders placed")
                
        else:
            print("❌ No momentum signals generated")
            
    except Exception as e:
        print(f"❌ Error generating signals: {e}")
        logging.error(f"Signal generation error: {e}", exc_info=True)
    
    print("\n" + "=" * 60)
    print("🎯 Test Complete - Your momentum strategy is ready for real paper trading!")

if __name__ == "__main__":
    test_momentum_with_real_trading()

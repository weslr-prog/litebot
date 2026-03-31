#!/usr/bin/env python3
"""
Buy Test Positions for Tomorrow's D+1 Exit Testing
"""

import sys
import os
import datetime as dt

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def buy_test_positions():
    """Buy small test positions for tomorrow's D+1 exit testing"""
    print("🛒 Buying Test Positions for Tomorrow's D+1 Exit Testing")
    print("="*60)
    
    try:
        from connect_real_trading import RealPaperTradingEngine
        from traders.short_cycle_trader import ShortCycleTrader, ShortCycleConfig
        
        # Initialize trading engine
        engine = RealPaperTradingEngine()
        print("✅ Connected to Alpaca Paper Trading")
        
        # Check account status
        account = engine.get_account_info()
        print(f"💰 Portfolio Value: ${account['portfolio_value']:,.2f}")
        print(f"💵 Buying Power: ${account['buying_power']:,.2f}")
        
        # Define test positions to buy
        test_positions = [
            {"symbol": "AAPL", "quantity": 2, "reason": "Large cap momentum test"},
            {"symbol": "TSLA", "quantity": 1, "reason": "High volatility test"},
            {"symbol": "MSFT", "quantity": 1, "reason": "Stable momentum test"}
        ]
        
        print(f"\n📊 Planning to buy {len(test_positions)} test positions:")
        for pos in test_positions:
            print(f"   {pos['symbol']}: {pos['quantity']} shares - {pos['reason']}")
        
        # Confirm with user
        # Auto-confirm purchase for test positions
        print("\n✅ Auto-proceeding with test purchases...")
        confirm = 'y'
        
        # Execute purchases
        successful_orders = []
        failed_orders = []
        
        for pos in test_positions:
            print(f"\n🛒 Buying {pos['quantity']} shares of {pos['symbol']}...")
            
            try:
                order_result = engine.submit_order(
                    symbol=pos['symbol'],
                    quantity=pos['quantity'],
                    side='buy',
                    order_type='market'
                )
                
                if order_result:
                    print(f"✅ Order submitted: {order_result['order_id']}")
                    successful_orders.append({
                        'symbol': pos['symbol'],
                        'quantity': pos['quantity'],
                        'order_id': order_result['order_id'],
                        'reason': pos['reason']
                    })
                else:
                    print(f"❌ Order failed for {pos['symbol']}")
                    failed_orders.append(pos)
                    
            except Exception as e:
                print(f"❌ Error buying {pos['symbol']}: {e}")
                failed_orders.append(pos)
        
        # Summary
        print(f"\n📊 Purchase Summary:")
        print(f"   ✅ Successful: {len(successful_orders)}")
        print(f"   ❌ Failed: {len(failed_orders)}")
        
        if successful_orders:
            print(f"\n✅ Successfully purchased positions:")
            for order in successful_orders:
                print(f"   {order['symbol']}: {order['quantity']} shares (Order: {order['order_id']})")
            
            # Now create position tracking entries for the bot
            print(f"\n🔄 Creating position tracking entries for bot...")
            create_position_entries(successful_orders)
        
        if failed_orders:
            print(f"\n❌ Failed purchases:")
            for order in failed_orders:
                print(f"   {order['symbol']}: {order['quantity']} shares")
        
        return len(successful_orders) > 0
        
    except Exception as e:
        print(f"❌ Purchase test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def create_position_entries(successful_orders):
    """Create position entries in positions.json for bot tracking"""
    try:
        from traders.short_cycle_trader import ShortCycleTrader, ShortCycleConfig
        from connect_real_trading import RealPaperTradingEngine
        
        # Create trader to manage positions
        config = ShortCycleConfig()
        trader = ShortCycleTrader(config)
        
        # Load existing positions
        trader._load_positions()
        print(f"📋 Loaded {len(trader.positions)} existing positions")
        
        # Get current Alpaca positions to get actual prices
        engine = RealPaperTradingEngine()
        alpaca_positions = engine.get_positions()
        
        # Create position entries for new purchases
        for order in successful_orders:
            symbol = order['symbol']
            quantity = order['quantity']
            
            # Get actual entry price from Alpaca
            if symbol in alpaca_positions:
                entry_price = float(alpaca_positions[symbol]['avg_cost'])
                position_value = entry_price * quantity
                
                print(f"📊 Creating tracking entry for {symbol}:")
                print(f"   Entry Price: ${entry_price:.2f}")
                print(f"   Quantity: {quantity}")
                print(f"   Position Value: ${position_value:.2f}")
                print(f"   Exit Date: {dt.date.today() + dt.timedelta(days=1)} (D+1)")
                
                # The position will be automatically synced by the bot's _sync_alpaca_positions method
                # when it runs next, so we don't need to manually create entries here
                
        print(f"✅ Position tracking will be handled by bot's Alpaca sync")
        print(f"💡 When bot runs tomorrow, it will:")
        print(f"   1. Detect these new Alpaca positions")
        print(f"   2. Add them to tracking system")
        print(f"   3. Schedule D+1 exits for tomorrow")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating position entries: {e}")
        return False

def verify_positions():
    """Verify the purchased positions are visible"""
    print(f"\n🔍 Verifying purchased positions...")
    
    try:
        from connect_real_trading import RealPaperTradingEngine
        
        engine = RealPaperTradingEngine()
        positions = engine.get_positions()
        
        print(f"📊 Current Alpaca positions: {len(positions)}")
        total_value = 0
        
        for symbol, pos_data in positions.items():
            quantity = pos_data['quantity']
            avg_cost = pos_data['avg_cost']
            market_value = pos_data['market_value']
            unrealized_pnl = pos_data['unrealized_pnl']
            
            print(f"   {symbol}: {quantity} shares @ ${avg_cost:.2f}")
            print(f"      Market Value: ${market_value:.2f}")
            print(f"      Unrealized P&L: ${unrealized_pnl:+.2f}")
            
            total_value += market_value
        
        print(f"\n💰 Total Position Value: ${total_value:.2f}")
        print(f"✅ These positions will be tracked for D+1 exits tomorrow")
        
        return True
        
    except Exception as e:
        print(f"❌ Position verification failed: {e}")
        return False

def main():
    """Main function to buy test positions"""
    print("🚀 Test Position Purchase Script")
    print("This will buy small positions for tomorrow's D+1 exit testing")
    print("="*60)
    
    # Buy positions
    success = buy_test_positions()
    
    if success:
        # Verify positions
        verify_positions()
        
        print(f"\n🎉 Test positions purchased successfully!")
        print(f"📅 Tomorrow ({dt.date.today() + dt.timedelta(days=1)}):")
        print(f"   1. Run the bot: bash scripts/launch_paper_testing.sh → 3")
        print(f"   2. Bot will detect these positions")
        print(f"   3. Bot will force-exit them with D+1_FORCED_EXIT")
        print(f"   4. Dashboard will show the exit trades")
        
    else:
        print(f"\n❌ Test position purchase failed")
        print(f"💡 Check Alpaca connection and account status")
    
    return success

if __name__ == "__main__":
    main()
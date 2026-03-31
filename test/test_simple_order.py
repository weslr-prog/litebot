#!/usr/bin/env python3
"""
Simple test to place one small order and verify order placement is working
"""

from connect_real_trading import RealPaperTradingEngine

def test_simple_order():
    print("🧪 Testing Simple Order Placement")
    print("=" * 40)
    
    engine = RealPaperTradingEngine()
    
    # Get account info
    account = engine.get_account_info()
    print(f"💰 Account Value: ${account['portfolio_value']:,.2f}")
    print(f"💸 Available Cash: ${account['cash']:,.2f}")
    
    # Test placing a very small order
    print(f"\n📤 Testing small order placement...")
    
    # Place a small order for 1 share of AAPL
    test_symbol = "AAPL"
    test_quantity = 1
    
    print(f"   Placing order: BUY {test_quantity} shares of {test_symbol}")
    
    try:
        result = engine.submit_order(
            symbol=test_symbol,
            quantity=test_quantity,
            side='buy'
        )
        
        if result:
            print(f"   ✅ Order successful!")
            print(f"   📋 Order ID: {result['order_id']}")
            print(f"   📊 Status: {result['status']}")
            print(f"   🎯 Order Details: {result}")
        else:
            print(f"   ❌ Order failed - no result returned")
            
    except Exception as e:
        print(f"   ❌ Order failed with error: {e}")
        import traceback
        traceback.print_exc()
    
    # Check positions after
    print(f"\n📈 Checking positions after order...")
    positions = engine.get_positions()
    
    if test_symbol in positions:
        pos = positions[test_symbol]
        print(f"   ✅ {test_symbol} position found: {pos['quantity']} shares")
    else:
        print(f"   ⚠️ No {test_symbol} position found (may take time to settle)")
    
    print(f"\n📊 Total positions: {len(positions)}")

if __name__ == "__main__":
    test_simple_order()

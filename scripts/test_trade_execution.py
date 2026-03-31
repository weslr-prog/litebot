#!/usr/bin/env python3
"""
Test script to verify bot can execute real trades
Places a small test order (1 share) and immediately cancels it
"""
import os
import sys
import time
from dotenv import load_dotenv

load_dotenv('.env')

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

def test_trade_execution():
    """Test that we can submit and cancel an order"""
    
    api_key = os.getenv('APCA_API_KEY_ID')
    secret = os.getenv('APCA_API_SECRET_KEY')
    
    if not api_key or not secret:
        print("❌ API credentials not found in .env")
        return False
    
    print(f"🔑 Using API Key: {api_key[:8]}...")
    
    client = TradingClient(api_key, secret, paper=True)
    
    # Check account
    account = client.get_account()
    print(f"\n💰 Account Status:")
    print(f"   Cash: ${float(account.cash):,.2f}")
    print(f"   Buying Power: ${float(account.buying_power):,.2f}")
    print(f"   Trading Blocked: {account.trading_blocked}")
    
    if account.trading_blocked:
        print("❌ Trading is blocked on this account")
        return False
    
    # Check market status
    clock = client.get_clock()
    if not clock.is_open:
        print(f"⚠️ Market is closed. Opens at {clock.next_open}")
        print("   Test will use limit order (won't fill immediately)")
    else:
        print("✅ Market is open")
    
    # Test symbol - use a liquid stock
    test_symbol = "SPY"  # S&P 500 ETF - very liquid
    test_qty = 1
    
    print(f"\n📝 Test: Submit 1-share limit order for {test_symbol}")
    print(f"   (Will be cancelled immediately - no actual trade)")
    
    try:
        # Get current price
        from alpaca.data.historical import StockHistoricalDataClient
        from alpaca.data.requests import StockLatestQuoteRequest
        
        data_client = StockHistoricalDataClient(api_key, secret)
        quote_request = StockLatestQuoteRequest(symbol_or_symbols=test_symbol)
        quote = data_client.get_stock_latest_quote(quote_request)
        current_price = float(quote[test_symbol].ask_price)
        
        # Submit limit order well below market (won't fill)
        limit_price = round(current_price * 0.95, 2)  # 5% below market
        
        print(f"   Current price: ${current_price:.2f}")
        print(f"   Limit price: ${limit_price:.2f} (5% below - won't fill)")
        
        order_data = LimitOrderRequest(
            symbol=test_symbol,
            qty=test_qty,
            side=OrderSide.BUY,
            time_in_force=TimeInForce.DAY,
            limit_price=limit_price
        )
        
        print(f"\n🚀 Submitting order...")
        order = client.submit_order(order_data)
        
        print(f"✅ Order submitted successfully!")
        print(f"   Order ID: {order.id}")
        print(f"   Symbol: {order.symbol}")
        print(f"   Side: {order.side}")
        print(f"   Qty: {order.qty}")
        print(f"   Status: {order.status}")
        print(f"   Limit Price: ${order.limit_price}")
        
        # Wait a moment
        time.sleep(1)
        
        # Get order status
        print(f"\n🔍 Checking order status...")
        order_status = client.get_order_by_id(order.id)
        print(f"   Current Status: {order_status.status}")
        
        # Cancel the order
        print(f"\n🛑 Cancelling test order...")
        client.cancel_order_by_id(order.id)
        print(f"✅ Order cancelled successfully")
        
        # Verify cancellation
        time.sleep(1)
        try:
            cancelled_order = client.get_order_by_id(order.id)
            print(f"   Final Status: {cancelled_order.status}")
        except:
            print(f"   Order removed from system (cancelled)")
        
        print(f"\n✅ TRADE EXECUTION TEST PASSED")
        print(f"   ✓ Bot can submit orders to Alpaca")
        print(f"   ✓ Bot can check order status")
        print(f"   ✓ Bot can cancel orders")
        print(f"   ✓ API credentials working correctly")
        
        return True
        
    except Exception as e:
        print(f"\n❌ TRADE EXECUTION TEST FAILED")
        print(f"   Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_actual_fill():
    """Test with a market order that will actually fill (if market open)"""
    
    api_key = os.getenv('APCA_API_KEY_ID')
    secret = os.getenv('APCA_API_SECRET_KEY')
    
    client = TradingClient(api_key, secret, paper=True)
    
    clock = client.get_clock()
    if not clock.is_open:
        print("\n⏸️ Skipping actual fill test - market closed")
        return True
    
    print("\n" + "="*60)
    print("OPTIONAL: Test actual market order (will fill immediately)")
    print("="*60)
    response = input("Execute 1-share SPY market order? (yes/no): ").strip().lower()
    
    if response != 'yes':
        print("⏭️ Skipping actual fill test")
        return True
    
    test_symbol = "SPY"
    test_qty = 1
    
    print(f"\n🚀 Submitting MARKET order for {test_qty} share of {test_symbol}...")
    
    try:
        order_data = MarketOrderRequest(
            symbol=test_symbol,
            qty=test_qty,
            side=OrderSide.BUY,
            time_in_force=TimeInForce.DAY
        )
        
        order = client.submit_order(order_data)
        print(f"✅ Market order submitted: {order.id}")
        
        # Wait for fill
        print(f"⏳ Waiting for fill...")
        for i in range(10):
            time.sleep(1)
            order_status = client.get_order_by_id(order.id)
            print(f"   Status: {order_status.status}")
            
            if order_status.status == 'filled':
                print(f"\n✅ ORDER FILLED!")
                print(f"   Filled Qty: {order_status.filled_qty}")
                print(f"   Filled Price: ${order_status.filled_avg_price}")
                print(f"   Cost: ${float(order_status.filled_avg_price) * float(order_status.filled_qty):.2f}")
                
                # Immediately sell it back
                print(f"\n🔄 Selling position back...")
                sell_order = MarketOrderRequest(
                    symbol=test_symbol,
                    qty=test_qty,
                    side=OrderSide.SELL,
                    time_in_force=TimeInForce.DAY
                )
                sell = client.submit_order(sell_order)
                print(f"✅ Sell order submitted: {sell.id}")
                
                time.sleep(2)
                sell_status = client.get_order_by_id(sell.id)
                if sell_status.status == 'filled':
                    print(f"✅ Position closed")
                    print(f"   Sell Price: ${sell_status.filled_avg_price}")
                
                break
        
        return True
        
    except Exception as e:
        print(f"❌ Market order test failed: {e}")
        return False


if __name__ == "__main__":
    print("="*60)
    print("🧪 LITEBOTX TRADE EXECUTION TEST")
    print("="*60)
    
    # Test 1: Submit and cancel (safe test)
    success = test_trade_execution()
    
    if not success:
        print("\n❌ Basic trade execution test failed")
        sys.exit(1)
    
    # Test 2: Actual fill (optional, if market open)
    test_actual_fill()
    
    print("\n" + "="*60)
    print("✅ ALL TESTS COMPLETED")
    print("="*60)
    print("\n🎉 Bot is ready to trade!")

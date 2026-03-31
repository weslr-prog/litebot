#!/usr/bin/env python3
"""
Test Real Trade Execution to Alpaca
Debug why trades aren't reaching Alpaca
"""

import sys
import os
sys.path.append('/home/wes/Desktop/litebotx-usb-deployment')

from connect_real_trading import RealPaperTradingEngine
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def test_alpaca_connection():
    """Test basic Alpaca connection and account access"""
    print("🧪 Testing Alpaca Connection")
    print("=" * 50)
    
    try:
        engine = RealPaperTradingEngine()
        
        # Test account info
        account_info = engine.get_account_info()
        if account_info:
            print(f"✅ Connected to Alpaca paper trading")
            print(f"   Portfolio Value: ${account_info['portfolio_value']:,.2f}")
            print(f"   Cash: ${account_info['cash']:,.2f}")
            print(f"   Status: {account_info['status']}")
        else:
            print("❌ Failed to get account info")
            return False
        
        # Test positions
        positions = engine.get_positions()
        print(f"📊 Current positions: {len(positions)}")
        for symbol, pos in positions.items():
            print(f"   {symbol}: {pos['quantity']} shares, PnL: ${pos['unrealized_pnl']:.2f}")
        
        return True
        
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return False

def test_small_trade():
    """Test submitting a small trade to Alpaca"""
    print("\n🧪 Testing Small Trade Submission")
    print("=" * 50)
    
    try:
        engine = RealPaperTradingEngine()
        
        # Submit a small test order (1 share of AAPL)
        print("📝 Submitting test order: 1 share AAPL")
        result = engine.submit_order("AAPL", 1, "buy")
        
        if result:
            print("✅ Test order submitted successfully!")
            print(f"   Order ID: {result['order_id']}")
            print(f"   Symbol: {result['symbol']}")
            print(f"   Quantity: {result['quantity']}")
            print(f"   Status: {result['status']}")
            return True
        else:
            print("❌ Test order submission failed")
            return False
            
    except Exception as e:
        print(f"❌ Trade test failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Alpaca Real Trading Debug Test")
    print("=" * 60)
    
    # Test connection
    if test_alpaca_connection():
        print("\n" + "="*60)
        
        # Ask user if they want to test a trade
        response = input("Do you want to test a small trade (1 share AAPL)? (y/n): ")
        if response.lower() == 'y':
            test_small_trade()
        else:
            print("Skipping trade test")
    
    print("\n🏁 Debug test complete")
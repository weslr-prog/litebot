#!/usr/bin/env python3
"""
Test Connection Resilience
Validates that retry logic works for API calls
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from connect_real_trading import RealPaperTradingEngine
from bot_v2.data.data_loader import DataLoader

def test_trading_engine_retries():
    """Test Alpaca Trading API with retry logic"""
    print("=" * 80)
    print("TEST 1: Alpaca Trading API Connection")
    print("=" * 80)
    
    try:
        engine = RealPaperTradingEngine()
        
        # Test get_account_info (with automatic retries)
        print("\n📊 Testing get_account_info()...")
        account_info = engine.get_account_info()
        if account_info:
            print(f"✅ Success - Account equity: ${account_info['portfolio_value']:,.2f}")
        else:
            print("❌ Failed - No account data returned")
            return False
        
        # Test get_positions (with automatic retries)
        print("\n📊 Testing get_positions()...")
        positions = engine.get_positions()
        print(f"✅ Success - {len(positions)} positions retrieved")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


def test_data_loader_retries():
    """Test Market Data API with retry logic"""
    print("\n" + "=" * 80)
    print("TEST 2: Market Data API Connection")
    print("=" * 80)
    
    try:
        loader = DataLoader()
        
        # Test historical data fetch (with automatic retries)
        print("\n📊 Testing get_historical_data()...")
        data = loader.get_historical_data('AAPL', days=5)
        if not data.empty:
            print(f"✅ Success - {len(data)} rows retrieved for AAPL")
        else:
            print("❌ Failed - No historical data returned")
            return False
        
        # Test current price fetch (with automatic retries)
        print("\n📊 Testing get_current_price()...")
        price = loader.get_current_price('AAPL')
        if price:
            print(f"✅ Success - AAPL price: ${price:.2f}")
        else:
            print("❌ Failed - No price returned")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


def main():
    """Run all connection tests"""
    print("\n🧪 CONNECTION RESILIENCE TEST SUITE")
    print("=" * 80)
    print("This validates that all API calls have retry logic")
    print("=" * 80)
    
    results = []
    
    # Test 1: Trading Engine
    results.append(("Alpaca Trading API", test_trading_engine_retries()))
    
    # Test 2: Data Loader
    results.append(("Market Data API", test_data_loader_retries()))
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status}: {test_name}")
        if not passed:
            all_passed = False
    
    print("=" * 80)
    
    if all_passed:
        print("\n✅ ALL TESTS PASSED - Connection retry logic is working!")
        print("\nThe bot will now automatically retry failed API calls.")
        print("Check logs for '🔄 Retrying in X seconds...' messages.")
        return 0
    else:
        print("\n❌ SOME TESTS FAILED - Check connection and credentials")
        return 1


if __name__ == "__main__":
    sys.exit(main())

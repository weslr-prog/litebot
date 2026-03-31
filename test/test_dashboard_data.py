#!/usr/bin/env python3
"""
Test Dashboard Position Data - Verify what data the dashboard is actually getting
"""

import sys
import os

# Add project paths
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append('gui')

def test_dashboard_data():
    """Test what data the dashboard gets from trading engine"""
    print("🧪 Testing Dashboard Data Sources")
    print("="*60)
    
    try:
        from connect_real_trading import RealPaperTradingEngine
        
        # Initialize trading engine (same as dashboard)
        engine = RealPaperTradingEngine()
        print("✅ RealPaperTradingEngine initialized")
        
        # Test account info (same as dashboard)
        print("\n📊 Account Information:")
        account_info = engine.get_account_info()
        if account_info:
            for key, value in account_info.items():
                print(f"   {key}: {value}")
        else:
            print("❌ No account info")
        
        # Test positions (same as dashboard)
        print("\n📊 Alpaca Positions:")
        positions = engine.get_positions()
        print(f"Found {len(positions)} position(s)")
        
        for symbol, pos_data in positions.items():
            print(f"\n   {symbol}:")
            for key, value in pos_data.items():
                print(f"      {key}: {value}")
        
        # Test portfolio summary (dashboard might use this)
        print("\n📊 Portfolio Summary:")
        portfolio = engine.get_portfolio_summary()
        if portfolio:
            print(f"   Position Count: {portfolio['position_count']}")
            print(f"   Total Unrealized P&L: ${portfolio['total_unrealized_pnl']:+.2f}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing dashboard data: {e}")
        return False

def test_position_json_vs_alpaca():
    """Compare positions.json vs Alpaca positions"""
    print("\n" + "="*60)
    print("🧪 Comparing positions.json vs Alpaca Positions")
    print("="*60)
    
    # Read positions.json
    import json
    try:
        with open('positions.json', 'r') as f:
            local_positions = json.load(f)
        print(f"📄 positions.json contains {len(local_positions)} position(s):")
        for pos in local_positions:
            print(f"   {pos.get('symbol', 'Unknown')}: {pos.get('status', 'Unknown')} - Entry: ${pos.get('entry_price', 0)}")
    except Exception as e:
        print(f"❌ Error reading positions.json: {e}")
        local_positions = []
    
    # Get Alpaca positions
    try:
        from connect_real_trading import RealPaperTradingEngine
        engine = RealPaperTradingEngine()
        alpaca_positions = engine.get_positions()
        
        print(f"\n🏦 Alpaca contains {len(alpaca_positions)} position(s):")
        for symbol, pos_data in alpaca_positions.items():
            print(f"   {symbol}: {pos_data.get('quantity', 0)} shares @ ${pos_data.get('avg_cost', 0):.2f}")
    except Exception as e:
        print(f"❌ Error getting Alpaca positions: {e}")
        alpaca_positions = {}
    
    # Compare
    print(f"\n🔍 Comparison:")
    local_symbols = {pos.get('symbol') for pos in local_positions}
    alpaca_symbols = set(alpaca_positions.keys())
    
    print(f"   Local symbols: {local_symbols}")
    print(f"   Alpaca symbols: {alpaca_symbols}")
    print(f"   Common symbols: {local_symbols & alpaca_symbols}")
    print(f"   Only local: {local_symbols - alpaca_symbols}")
    print(f"   Only Alpaca: {alpaca_symbols - local_symbols}")

def test_dashboard_position_processing():
    """Test how dashboard processes position data"""
    print("\n" + "="*60)
    print("🧪 Testing Dashboard Position Processing Logic")
    print("="*60)
    
    try:
        from connect_real_trading import RealPaperTradingEngine
        
        # Simulate dashboard's get_real_or_sample_data method
        engine = RealPaperTradingEngine()
        account_info = engine.get_account_info()
        positions = engine.get_positions()
        
        print(f"📊 Raw Alpaca positions: {len(positions)}")
        
        # Process positions like the dashboard does
        real_positions = []
        for pos in positions:
            if isinstance(pos, str):
                # Position is just a symbol name
                real_positions.append({
                    'ticker': pos,
                    'qty': 1,
                    'entry': 0.0,
                    'current': 0.0,
                    'sector': 'Unknown'
                })
                print(f"   String position: {pos}")
                continue
                
            # Handle position as dictionary (this is what we expect)
            print(f"   Processing position: {pos}")
            
        print(f"📊 Processed positions: {len(real_positions)}")
        
        # The issue might be here - let's see the actual data structure
        print(f"\n🔍 Raw positions data structure:")
        for symbol, pos_data in positions.items():
            print(f"   {symbol}: {type(pos_data)} = {pos_data}")
            
            # Try to extract data like the dashboard does
            qty = float(pos_data.get('quantity', 0))
            if qty == 0:
                print(f"      ⚠️  Zero quantity - would be skipped")
                continue
                
            processed_pos = {
                'ticker': symbol,
                'qty': int(qty),
                'entry': float(pos_data.get('avg_cost', 0)),
                'current': float(pos_data.get('market_value', 0)) / abs(qty) if qty != 0 else 0,
                'sector': 'Unknown'
            }
            real_positions.append(processed_pos)
            print(f"      ✅ Processed: {processed_pos}")
        
        print(f"\n📊 Final processed positions for GUI: {len(real_positions)}")
        
        return real_positions
        
    except Exception as e:
        print(f"❌ Error testing dashboard processing: {e}")
        return []

def main():
    """Run dashboard data tests"""
    print("🚀 Dashboard Data Test Suite")
    
    success = True
    
    try:
        success &= test_dashboard_data()
        test_position_json_vs_alpaca()
        processed_positions = test_dashboard_position_processing()
        
        print("\n" + "="*60)
        print("📊 Summary:")
        print(f"   Dashboard data access: {'✅ Working' if success else '❌ Failed'}")
        print(f"   Processed positions count: {len(processed_positions)}")
        
        if len(processed_positions) == 0:
            print("🔍 Issue identified: No positions are being processed for GUI display")
            print("   This explains why the dashboard shows no positions despite Alpaca connection")
        else:
            print("✅ Positions should be visible in dashboard")
            
    except Exception as e:
        print(f"❌ Test suite error: {e}")
        success = False
    
    return success

if __name__ == "__main__":
    main()
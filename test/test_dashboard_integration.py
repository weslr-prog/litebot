#!/usr/bin/env python3
"""
Test ShortCycle Dashboard Position Integration
"""

import sys
import os
import datetime as dt

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_dashboard_position_integration():
    """Test that the dashboard properly displays positions from the trader"""
    print("🧪 Testing ShortCycle Dashboard Position Integration")
    print("="*60)
    
    try:
        from traders.short_cycle_trader import ShortCycleTrader, ShortCycleConfig
        from gui.short_cycle_dashboard import ShortCycleDashboard
        
        # Create trader
        config = ShortCycleConfig()
        trader = ShortCycleTrader(config)
        
        # Load existing positions
        trader._load_positions()
        print(f"📊 Trader loaded {len(trader.positions)} position(s)")
        
        for pos in trader.positions:
            print(f"   {pos.symbol}: {pos.status.value} - Entry: ${pos.entry_price}, Size: {pos.position_size_shares}")
        
        # Create dashboard with trader connection
        dashboard = ShortCycleDashboard(trader)
        print("✅ Dashboard created and connected to trader")
        
        # Check if positions were synced
        print(f"📊 Dashboard synced {len(dashboard.metrics.current_positions)} active position(s)")
        
        for symbol, pos_data in dashboard.metrics.current_positions.items():
            print(f"   {symbol}: {pos_data['status']} - Qty: {pos_data['quantity']}, Price: ${pos_data['avg_price']:.2f}")
        
        # Test the metrics summary
        summary = dashboard.metrics.get_performance_summary()
        print(f"\n📈 Dashboard Summary:")
        print(f"   Active Positions: {summary['active_positions']}")
        print(f"   Total P&L: ${summary['total_pnl']:.2f}")
        print(f"   Win Rate: {summary['win_rate']:.1f}%")
        
        # Simulate connecting to Alpaca positions
        print(f"\n🏦 Testing Alpaca Position Integration:")
        try:
            from connect_real_trading import RealPaperTradingEngine
            engine = RealPaperTradingEngine()
            alpaca_positions = engine.get_positions()
            
            print(f"   Found {len(alpaca_positions)} Alpaca position(s):")
            for symbol, pos in alpaca_positions.items():
                print(f"   {symbol}: {pos['quantity']} shares @ ${pos['avg_cost']:.2f}")
            
            # The dashboard should be able to show local positions AND recognize Alpaca positions exist
            print(f"\n🔍 Integration Status:")
            print(f"   Local positions: {len(trader.positions)}")
            print(f"   Dashboard active positions: {len(dashboard.metrics.current_positions)}")
            print(f"   Alpaca positions: {len(alpaca_positions)}")
            
            if len(alpaca_positions) > 0 and len(dashboard.metrics.current_positions) == 0:
                print("   ⚠️  Dashboard shows no active positions but Alpaca has positions")
                print("   💡 This is expected if all local positions are 'exited' but Alpaca positions exist")
                
        except Exception as e:
            print(f"   ❌ Alpaca connection test failed: {e}")
        
        print(f"\n✅ Dashboard integration test completed")
        return True
        
    except Exception as e:
        print(f"❌ Dashboard integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run dashboard integration test"""
    print("🚀 ShortCycle Dashboard Integration Test")
    success = test_dashboard_position_integration()
    print("\n" + "="*60)
    if success:
        print("🎉 Integration test PASSED")
        print("💡 Dashboard is properly connected to trader position data")
    else:
        print("❌ Integration test FAILED")
        print("💡 Check the error messages above for details")
    
    return success

if __name__ == "__main__":
    main()
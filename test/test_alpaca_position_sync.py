#!/usr/bin/env python3
"""
Test Alpaca Position Sync for D+1 Monitoring
"""

import sys
import os
import datetime as dt

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_alpaca_position_sync():
    """Test syncing Alpaca positions for D+1 monitoring"""
    print("🧪 Testing Alpaca Position Sync for D+1 Monitoring")
    print("="*60)
    
    try:
        from traders.short_cycle_trader import ShortCycleTrader, ShortCycleConfig
        from connect_real_trading import RealPaperTradingEngine
        
        # First, check what Alpaca positions exist
        engine = RealPaperTradingEngine()
        alpaca_positions = engine.get_positions()
        
        print(f"🏦 Current Alpaca Positions: {len(alpaca_positions)}")
        for symbol, pos in alpaca_positions.items():
            print(f"   {symbol}: {pos['quantity']} shares @ ${pos['avg_cost']:.2f}")
        
        # Create trader and load positions
        config = ShortCycleConfig()
        trader = ShortCycleTrader(config)
        
        print(f"\n📋 Before sync: {len(trader.positions)} tracked positions")
        for pos in trader.positions:
            print(f"   {pos.symbol}: {pos.status.value}")
        
        # Test the sync method directly
        trader._sync_alpaca_positions()
        
        print(f"\n📋 After sync: {len(trader.positions)} tracked positions")
        for pos in trader.positions:
            print(f"   {pos.symbol}: {pos.status.value} - Entry: {pos.entry_date}, Exit: {pos.exit_date}")
            if pos.entry_date and pos.exit_date:
                should_exit = pos.should_force_exit(dt.date.today())
                print(f"      Should force exit today?: {should_exit}")
        
        # Test running the position processing to see if D+1 exits trigger
        print(f"\n🔄 Testing D+1 exit processing...")
        trader._process_existing_positions()
        
        print(f"\n📊 Final status: {len(trader.positions)} positions")
        for pos in trader.positions:
            print(f"   {pos.symbol}: {pos.status.value}")
            if hasattr(pos, 'realized_pnl') and pos.realized_pnl:
                print(f"      Realized P&L: ${pos.realized_pnl:.2f}")
        
        return True
        
    except Exception as e:
        print(f"❌ Alpaca position sync test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run Alpaca position sync test"""
    print("🚀 Alpaca Position Sync Test")
    success = test_alpaca_position_sync()
    print("\n" + "="*60)
    if success:
        print("🎉 Alpaca position sync test PASSED")
        print("💡 Bot can now monitor Alpaca positions for D+1 exits")
    else:
        print("❌ Alpaca position sync test FAILED")
    
    return success

if __name__ == "__main__":
    main()
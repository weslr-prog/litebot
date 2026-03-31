#!/usr/bin/env python3

"""
Live paper trading session - See the bot make real decisions
Connects to Alpaca and makes actual paper trades
"""

import time
import logging
from datetime import datetime, timedelta
from traders.short_cycle_trader import ShortCycleTrader, ShortCycleConfig

def market_session_demo():
    """
    30-minute live session showing bot's actual behavior
    Makes real paper trades with Alpaca
    """
    
    print("🎪 LiteBotX Live Paper Trading Session")
    print("=" * 60)
    print("⏱️  Duration: 30 minutes")
    print("🎯 Goal: Show live signal generation & Alpaca trades")
    print("🔴 REAL PAPER TRADES will be made!")
    print("")
    
    input("Press Enter to start live session (Ctrl+C to abort)...")
    
    # Initialize
    config = ShortCycleConfig()
    trader = ShortCycleTrader(config)
    
    print(f"🚀 Starting live session at {datetime.now().strftime('%H:%M:%S')}")
    
    session_start = time.time()
    cycle_count = 0
    
    try:
        while time.time() - session_start < 1800:  # 30 minutes
            cycle_count += 1
            cycle_start = time.time()
            
            print(f"\n📈 === CYCLE {cycle_count} at {datetime.now().strftime('%H:%M:%S')} ===")
            
            # Check current portfolio status
            portfolio_val = trader._get_portfolio_value()
            open_positions = len([p for p in trader.positions if p.status.value == "entered"])
            
            print(f"💰 Portfolio: ${portfolio_val:,.0f} | Positions: {open_positions}/{config.max_positions_per_day}")
            
            # Generate signals (this is where the magic happens)
            print("🧠 Scanning for signals...")
            
            try:
                # Let the bot run its signal generation
                trader._check_new_opportunities()
                
                # Check for exits
                trader._check_exit_opportunities()
                
            except Exception as e:
                print(f"❌ Error in trading cycle: {e}")
            
            # Check for recent activity based on available timestamp fields
            recent_trades = []
            for p in trader.positions:
                # Check exit timestamp for recent exits
                if p.exit_timestamp and (datetime.now() - p.exit_timestamp).total_seconds() < 300:
                    recent_trades.append(p)
                # Check entry date for today's entries
                elif p.entry_date == datetime.now().date() and p.status.value == "entered":
                    recent_trades.append(p)
            
            if recent_trades:
                print(f"🎯 New activity: {len(recent_trades)} trades")
                for trade in recent_trades[-3:]:  # Show last 3
                    action = trade.ai_signal.action if trade.ai_signal else "BUY"
                    print(f"   📊 {trade.symbol}: {action} at ${trade.entry_price:.2f}")
            else:
                print("💤 No new signals this cycle")
            
            # Wait for next cycle (stagger to avoid rate limits)
            cycle_duration = time.time() - cycle_start
            wait_time = max(30 - cycle_duration, 5)  # At least 5 seconds between cycles
            
            print(f"⏱️  Cycle took {cycle_duration:.1f}s, waiting {wait_time:.1f}s...")
            time.sleep(wait_time)
    
    except KeyboardInterrupt:
        print("\n\n🛑 Session interrupted by user")
    
    except Exception as e:
        print(f"\n\n❌ Session error: {e}")
    
    # Session summary
    session_duration = (time.time() - session_start) / 60
    final_portfolio = trader._get_portfolio_value()
    final_positions = len([p for p in trader.positions if p.status.value == "entered"])
    
    print("\n" + "=" * 60)
    print("📊 LIVE SESSION SUMMARY:")
    print(f"⏱️  Duration: {session_duration:.1f} minutes")
    print(f"🔄 Cycles completed: {cycle_count}")
    print(f"💰 Final portfolio: ${final_portfolio:,.0f}")
    print(f"📈 Active positions: {final_positions}")
    
    # Show recent trades
    recent_trades = []
    for p in trader.positions:
        # Check for recent activity (same day entries or recent exits)
        if p.entry_date == datetime.now().date() or (p.exit_timestamp and (datetime.now() - p.exit_timestamp).total_seconds() < session_duration * 60):
            recent_trades.append(p)
    
    if recent_trades:
        print(f"\n🎯 Trades made during session: {len(recent_trades)}")
        for trade in recent_trades:
            if trade.exit_timestamp:
                age_minutes = (datetime.now() - trade.exit_timestamp).total_seconds() / 60
                status = f"EXITED ({age_minutes:.0f}m ago)"
            else:
                status = "OPEN"
            action = trade.ai_signal.action if trade.ai_signal else "BUY"
            print(f"   📊 {trade.symbol}: {action} ${trade.entry_price:.2f} ({status})")
    else:
        print("\n💤 No trades made this session")
    
    print("\n🎪 Dynamic behaviors observed:")
    print(f"   📈 Portfolio-scaled position sizing")
    print(f"   🛡️ Real-time risk management")
    print(f"   🎯 Live signal confidence filtering")
    print(f"   📊 Alpaca paper trade execution")

if __name__ == "__main__":
    market_session_demo()
#!/usr/bin/env python3

"""
LiteBotX Continuous Live Trading Mode
Runs the bot continuously during market hours with proper scheduling
"""

import time
import signal
import sys
from datetime import datetime, time as dt_time
from traders.short_cycle_trader import ShortCycleTrader, ShortCycleConfig

class ContinuousTrader:
    def __init__(self):
        self.config = ShortCycleConfig()
        self.trader = None
        self.running = False
        
        # Market hours (Eastern Time)
        self.market_open = dt_time(9, 30)   # 9:30 AM
        self.market_close = dt_time(16, 0)  # 4:00 PM
        
        # Trading cycle frequency (seconds)
        self.cycle_interval = 60  # Check for opportunities every minute
        
    def signal_handler(self, signum, frame):
        """Handle Ctrl+C gracefully"""
        print(f"\n🛑 Received signal {signum}, shutting down gracefully...")
        self.running = False
        
    def is_market_hours(self):
        """Check if we're in market hours"""
        now = datetime.now()
        current_time = now.time()
        
        # Check if weekend
        if now.weekday() >= 5:  # Saturday=5, Sunday=6
            return False
        
        # Check if within market hours
        return self.market_open <= current_time <= self.market_close
    
    def initialize_trader(self):
        """Initialize the trading system"""
        try:
            print("🔧 Initializing LiteBotX trading system...")
            self.trader = ShortCycleTrader(self.config)
            
            # Get initial status
            portfolio_val = self.trader._get_portfolio_value()
            open_positions = len([p for p in self.trader.positions if p.status.value == "entered"])
            
            print(f"✅ System initialized successfully")
            print(f"💰 Portfolio value: ${portfolio_val:,.2f}")
            print(f"📊 Open positions: {open_positions}/{self.config.max_positions_per_day}")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to initialize trader: {e}")
            return False
    
    def run_trading_cycle(self):
        """Execute one trading cycle"""
        try:
            cycle_start = time.time()
            
            print(f"\n🔄 Trading cycle at {datetime.now().strftime('%H:%M:%S')}")
            
            # Check portfolio status
            portfolio_val = self.trader._get_portfolio_value()
            open_positions = len([p for p in self.trader.positions if p.status.value == "entered"])
            
            print(f"💰 Portfolio: ${portfolio_val:,.0f} | Positions: {open_positions}/{self.config.max_positions_per_day}")
            
            # Run the daily cycle (entry and exit opportunities)
            self.trader.run_daily_cycle()
            
            # Report what happened this cycle
            # Check for new positions (entered today)
            today = datetime.now().date()
            new_positions = [p for p in self.trader.positions 
                           if p.entry_date == today and p.status.value == "entered"]
            
            # Check for recent exits (last 5 minutes based on exit timestamp)
            recent_exits = [p for p in self.trader.positions 
                          if p.exit_timestamp and (datetime.now() - p.exit_timestamp).total_seconds() < 300]
            
            if new_positions or recent_exits:
                total_activity = len(new_positions) + len(recent_exits)
                print(f"🎯 Activity this cycle: {total_activity} trades")
                
                for pos in new_positions[-2:]:  # Show last 2 new positions
                    action = pos.ai_signal.action if pos.ai_signal else "BUY"
                    print(f"   � NEW: {pos.symbol} {action} at ${pos.entry_price:.2f}")
                
                for pos in recent_exits[-2:]:  # Show last 2 exits
                    print(f"   📉 EXIT: {pos.symbol} at ${pos.exit_price:.2f} ({pos.exit_reason})")
            else:
                print("💤 No new signals this cycle")
            
            cycle_duration = time.time() - cycle_start
            print(f"⏱️  Cycle completed in {cycle_duration:.1f}s")
            
        except Exception as e:
            print(f"❌ Error in trading cycle: {e}")
    
    def run_continuous(self):
        """Run continuous trading with proper market hours handling"""
        print("🚀 LiteBotX Continuous Live Trading Mode")
        print("=" * 60)
        print(f"⏰ Market hours: {self.market_open.strftime('%H:%M')} - {self.market_close.strftime('%H:%M')} ET")
        print(f"🔄 Cycle interval: {self.cycle_interval} seconds")
        print("🛑 Press Ctrl+C to stop")
        print()
        
        # Set up signal handler for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        # Initialize trading system
        if not self.initialize_trader():
            print("❌ Failed to initialize. Exiting.")
            return
        
        self.running = True
        last_market_check = datetime.now()
        
        print("✅ Continuous trading mode started")
        
        try:
            while self.running:
                current_time = datetime.now()
                
                # Check market hours every minute
                if (current_time - last_market_check).total_seconds() >= 60:
                    last_market_check = current_time
                    
                    if not self.is_market_hours():
                        if current_time.weekday() >= 5:
                            print(f"📅 Weekend - Market closed. Next session: Monday {self.market_open.strftime('%H:%M')} ET")
                        elif current_time.time() < self.market_open:
                            minutes_to_open = ((datetime.combine(current_time.date(), self.market_open) - current_time).total_seconds() / 60)
                            print(f"🕘 Pre-market: {minutes_to_open:.0f} minutes until market open")
                        else:
                            print(f"🌙 After-hours: Market closed until tomorrow {self.market_open.strftime('%H:%M')} ET")
                        
                        # Sleep longer when market is closed
                        time.sleep(300)  # 5 minutes
                        continue
                
                # Market is open - run trading cycle
                if self.is_market_hours():
                    self.run_trading_cycle()
                    
                    # Wait for next cycle
                    time.sleep(self.cycle_interval)
                else:
                    # Quick check if market just closed
                    time.sleep(30)
        
        except KeyboardInterrupt:
            print("\n🛑 Interrupted by user")
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources"""
        print("\n🧹 Cleaning up...")
        
        if self.trader:
            # Get final status
            try:
                portfolio_val = self.trader._get_portfolio_value()
                open_positions = len([p for p in self.trader.positions if p.status.value == "entered"])
                
                print(f"📊 Final portfolio: ${portfolio_val:,.2f}")
                print(f"📈 Open positions: {open_positions}")
                
                # Save any pending data
                print("💾 Saving trader state...")
                
            except Exception as e:
                print(f"⚠️  Error during cleanup: {e}")
        
        print("✅ Cleanup complete")
        print("👋 LiteBotX continuous trading stopped")

def main():
    """Main entry point"""
    trader = ContinuousTrader()
    trader.run_continuous()

if __name__ == "__main__":
    main()
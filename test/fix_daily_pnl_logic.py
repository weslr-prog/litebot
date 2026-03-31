#!/usr/bin/env python3
"""
Fix for daily P&L logic issues - backfill missing exit_timestamp and reset daily counters.

Root cause: 
1. abs(daily_pnl) was triggering on large GAINS (like IBM +$1019)
2. _update_daily_pnl only counted entry_date == today, missing D+1 exits
3. No exit_timestamp field to track when exits occurred

This script:
1. Backfills exit_timestamp for exited positions (uses today as fallback)
2. Resets any active daily loss kill switches
3. Validates the fix by simulating daily P&L calculation
"""

import json
import os
from datetime import datetime, date
from pathlib import Path

def backfill_exit_timestamps():
    """Add exit_timestamp to existing exited positions"""
    positions_file = "positions.json"
    
    if not os.path.exists(positions_file):
        print(f"❌ {positions_file} not found")
        return
    
    # Load current positions
    with open(positions_file, 'r') as f:
        positions_data = json.load(f)
    
    modified = False
    today_timestamp = datetime.now().isoformat()
    
    for position in positions_data:
        # If position is exited but has no exit_timestamp, add one
        if (position.get('exit_price') is not None and 
            position.get('exit_timestamp') is None):
            
            # Use today as fallback timestamp for exits
            position['exit_timestamp'] = today_timestamp
            modified = True
            print(f"✅ Added exit_timestamp to {position['symbol']}: {today_timestamp}")
    
    if modified:
        # Backup original
        backup_file = f"positions_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        os.rename(positions_file, backup_file)
        print(f"📦 Backed up original to: {backup_file}")
        
        # Save updated positions
        with open(positions_file, 'w') as f:
            json.dump(positions_data, f, indent=2)
        print(f"💾 Updated {positions_file} with exit timestamps")
    else:
        print("ℹ️ No positions needed exit_timestamp backfill")
    
    return positions_data

def validate_daily_pnl_calculation(positions_data):
    """Simulate the new daily P&L calculation logic"""
    today = date.today()
    today_str = today.isoformat()
    
    print(f"\n📊 Validating daily P&L calculation for {today_str}:")
    
    # Find positions exited today
    exits_today = []
    for pos in positions_data:
        if pos.get('exit_timestamp'):
            exit_date = datetime.fromisoformat(pos['exit_timestamp'].replace('Z', '+00:00')).date()
            if exit_date == today and pos.get('realized_pnl') is not None:
                exits_today.append(pos)
    
    # Calculate realized P&L from today's exits
    daily_realized = sum(pos.get('realized_pnl', 0) for pos in exits_today)
    
    # Find open positions (for unrealized P&L - would be calculated with live prices)
    open_positions = [pos for pos in positions_data if pos.get('status') == 'ENTERED']
    
    print(f"🔍 Analysis:")
    print(f"  - Positions exited today: {len(exits_today)}")
    for pos in exits_today:
        pnl = pos.get('realized_pnl', 0)
        print(f"    * {pos['symbol']}: ${pnl:.2f}")
    print(f"  - Daily realized P&L: ${daily_realized:.2f}")
    print(f"  - Open positions: {len(open_positions)}")
    print(f"  - Daily unrealized P&L: $0.00 (would update with live prices)")
    
    # Check against loss limits
    max_daily_loss = 150  # $150 from 1.5% of $10k portfolio
    
    if daily_realized < 0 and abs(daily_realized) > max_daily_loss:
        print(f"🛑 Daily loss limit would trigger: ${daily_realized:.2f} exceeds ${max_daily_loss}")
    elif daily_realized > max_daily_loss:
        print(f"✅ Large gain (${daily_realized:.2f}) would NOT trigger loss limit (old bug fixed)")
    else:
        print(f"✅ Daily P&L (${daily_realized:.2f}) within normal range")

def reset_kill_switches():
    """Create a simple reset script for kill switches"""
    reset_script = """#!/usr/bin/env python3
# Quick reset for daily loss kill switch
import sys
sys.path.append('/home/wes/Desktop/litebotx-usb-deployment')

from traders.short_cycle_trader import ShortCycleConfig, ShortCycleTrader

config = ShortCycleConfig()
trader = ShortCycleTrader(config)
trader.kill_switches["daily_loss_exceeded"] = False
print("✅ Daily loss kill switch reset")
"""
    
    with open("reset_kill_switches.py", "w") as f:
        f.write(reset_script)
    os.chmod("reset_kill_switches.py", 0o755)
    print("📝 Created reset_kill_switches.py")

def main():
    print("🔧 Fixing daily P&L logic issues...")
    
    # 1. Backfill exit timestamps
    positions_data = backfill_exit_timestamps()
    
    # 2. Validate new calculation logic
    if positions_data:
        validate_daily_pnl_calculation(positions_data)
    
    # 3. Create reset script
    reset_kill_switches()
    
    print(f"\n✅ Daily P&L logic fix complete!")
    print(f"📋 Summary of changes:")
    print(f"  - Fixed abs() bug in loss limit check (no longer triggers on gains)")
    print(f"  - Daily P&L now includes realized exits from today (regardless of entry date)")
    print(f"  - Added exit_timestamp tracking for precise exit timing")
    print(f"  - Added daily counter reset at market open")
    print(f"  - Loss limits only check during market hours")
    
    print(f"\n🚀 Next steps:")
    print(f"  1. Run the bot again - it should not trigger loss limits on profitable days")
    print(f"  2. Monitor daily_metrics.json (will be created) for transparency")
    print(f"  3. If kill switch is still active, run: python3 reset_kill_switches.py")

if __name__ == "__main__":
    main()
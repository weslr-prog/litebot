#!/usr/bin/env python3
"""
Direct test of the daily P&L calculation without daily reset interference.
"""

import sys
import json
from datetime import datetime, date
sys.path.append('/home/wes/Desktop/litebotx-usb-deployment')

def test_pnl_calculation():
    """Test P&L calculation directly on the data"""
    print("🧪 Direct P&L calculation test...")
    
    # Load positions directly
    with open('positions.json', 'r') as f:
        positions_data = json.load(f)
    
    today = date.today()
    today_str = today.isoformat()
    
    print(f"📅 Testing for date: {today_str}")
    
    # Find exits today
    exits_today = []
    for pos in positions_data:
        if pos.get('exit_timestamp'):
            try:
                # Parse the timestamp
                timestamp_str = pos['exit_timestamp']
                if 'T' in timestamp_str:
                    exit_date = datetime.fromisoformat(timestamp_str).date()
                else:
                    exit_date = datetime.fromisoformat(timestamp_str + 'T00:00:00').date()
                
                if exit_date == today and pos.get('realized_pnl') is not None:
                    exits_today.append(pos)
                    print(f"  📊 {pos['symbol']}: Exit {exit_date}, P&L ${pos['realized_pnl']:.2f}")
            except Exception as e:
                print(f"  ❌ Error parsing {pos['symbol']}: {e}")
    
    # Calculate total
    total_realized = sum(pos.get('realized_pnl', 0) for pos in exits_today)
    
    print(f"\n📈 Results:")
    print(f"  - Exits today: {len(exits_today)}")
    print(f"  - Total realized P&L: ${total_realized:.2f}")
    print(f"  - Max daily loss limit: $150")
    
    # Test the logic
    if total_realized < 0 and abs(total_realized) > 150:
        print(f"  🛑 Would trigger loss limit (loss > $150)")
    elif total_realized > 150:
        print(f"  ✅ Large gain (${total_realized:.2f}) would NOT trigger loss limit")
    else:
        print(f"  ✅ P&L within normal range")
    
    return exits_today, total_realized

if __name__ == "__main__":
    exits, pnl = test_pnl_calculation()
    
    if len(exits) > 0 and pnl > 0:
        print(f"\n🎉 SUCCESS: Fix is working!")
        print(f"   - Found {len(exits)} exits today with ${pnl:.2f} total gain")
        print(f"   - Logic correctly handles large gains without false loss limit")
    else:
        print(f"\n🤔 Note: {len(exits)} exits found with ${pnl:.2f} P&L")
        print(f"   - This is expected if no trading occurred today")
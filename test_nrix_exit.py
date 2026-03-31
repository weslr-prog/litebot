#!/usr/bin/env python3
"""
Test NRIX exit logic
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from bot_v2.config.trading_config import ShortCycleConfig
from bot_v2.execution.position_tracker import AIPositionTracker
from bot_v2.execution.exit_manager import AIExitManager
from bot_v2.execution.order_manager import AIOrderManager
from bot_v2.risk_management.stop_loss_manager import AIStopLossManager
from execution_engine import ExecutionEngine
from data_loader import DataLoader
import yfinance as yf

print("=" * 80)
print("Testing NRIX Exit Logic")
print("=" * 80)

# Initialize components
config = ShortCycleConfig()
position_tracker = AIPositionTracker(config=config)
stop_manager = AIStopLossManager(config=config)
order_manager = AIOrderManager(config=config, execution_engine=ExecutionEngine())
exit_manager = AIExitManager(config=config, stop_manager=stop_manager, order_manager=order_manager)

# Load positions
positions = position_tracker.load_positions()
print(f"\nLoaded {len(positions)} positions from positions.json")

# Find NRIX
nrix_pos = None
for pos in positions:
    if pos.symbol == "NRIX" and pos.status.value == "entered":
        nrix_pos = pos
        break

if not nrix_pos:
    print("❌ No active NRIX position found")
    sys.exit(1)

print(f"\n✅ Found NRIX position:")
print(f"   Entry: ${nrix_pos.entry_price:.2f}")
print(f"   Shares: {nrix_pos.position_size_shares}")
print(f"   Stop: ${nrix_pos.stop_price:.2f}")
print(f"   Entry Date: {nrix_pos.entry_date}")

# Get current price
data_loader = DataLoader()
ticker = yf.Ticker("NRIX")
hist = ticker.history(period="1d")
current_price = hist['Close'].iloc[-1] if not hist.empty else nrix_pos.entry_price

print(f"\n📊 Current Status:")
print(f"   Current Price: ${current_price:.2f}")

# Update position with current price
nrix_pos.current_price = current_price

pnl = (current_price - nrix_pos.entry_price) * nrix_pos.position_size_shares
pnl_pct = ((current_price - nrix_pos.entry_price) / nrix_pos.entry_price) * 100

print(f"   P&L: ${pnl:.2f} ({pnl_pct:+.2f}%)")

# Calculate days held
from datetime import datetime
entry_dt = datetime.fromisoformat(str(nrix_pos.entry_date))
days_held = (datetime.now() - entry_dt).days
print(f"   Days Held: {days_held}")

# Check exit conditions
print(f"\n🔍 Exit Condition Check:")
should_exit, exit_reason = exit_manager.should_exit(nrix_pos)

if should_exit:
    print(f"✅ SHOULD EXIT: {exit_reason}")
else:
    print(f"⏸️ HOLD: No exit conditions met")
    
    # Show individual conditions
    print(f"\nDetailed Checks:")
    print(f"   Stop Loss ({nrix_pos.stop_price:.2f}): {'❌ HIT' if current_price <= nrix_pos.stop_price else '✅ OK'}")
    print(f"   Profit Target (3%): {'❌ HIT' if pnl_pct >= 3.0 else f'✅ OK ({pnl_pct:.2f}%)'}")
    print(f"   D+1 Exit (2 days): {'❌ DUE' if days_held >= 2 else f'✅ OK ({days_held} days)'}")
    
print("\n" + "=" * 80)

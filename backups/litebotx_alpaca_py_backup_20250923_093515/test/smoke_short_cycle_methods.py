#!/usr/bin/env python3
import sys
import inspect

try:
    from traders.short_cycle_trader import ShortCycleTrader
except Exception as e:
    print(f"IMPORT_ERROR: {e}")
    sys.exit(2)

missing = []
required = [
    'run_continuous_cycle',
    'run_daily_cycle',
    '_process_existing_positions',
    '_update_daily_pnl',
    '_save_positions',
]
for name in required:
    if not hasattr(ShortCycleTrader, name):
        missing.append(name)

print("ShortCycleTrader loaded from:", inspect.getsourcefile(ShortCycleTrader))
print("Missing methods:", missing)

if missing:
    sys.exit(1)
else:
    sys.exit(0)

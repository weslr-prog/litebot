#!/usr/bin/env python3

from traders.short_cycle_trader import PositionStatus

# Test enum values
print("Valid PositionStatus values:")
for status in PositionStatus:
    print(f"  {status.name} = '{status.value}'")

# Test specific values
test_values = ["stopped_out", "STOPPED_OUT", "exited", "EXITED", "entered", "ENTERED"]

for value in test_values:
    try:
        status = PositionStatus(value)
        print(f"✅ PositionStatus('{value}') = {status}")
    except ValueError as e:
        print(f"❌ PositionStatus('{value}') failed: {e}")
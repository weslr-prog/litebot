#!/usr/bin/env python3

import json
from traders.short_cycle_trader import PositionStatus

# Load positions.json
try:
    with open('positions.json', 'r') as f:
        positions_data = json.load(f)
    
    print(f"Loaded {len(positions_data)} positions from positions.json")
    
    # Check each position status
    for i, pos in enumerate(positions_data):
        status_value = pos.get('status', 'MISSING')
        print(f"Position {i+1} ({pos.get('symbol', 'UNKNOWN')}): status = '{status_value}'")
        
        try:
            status_enum = PositionStatus(status_value)
            print(f"  ✅ Converted to {status_enum}")
        except ValueError as e:
            print(f"  ❌ Failed: {e}")
        print()
        
        # Stop after first few to avoid spam
        if i >= 5:
            break
            
except Exception as e:
    print(f"Error loading positions: {e}")
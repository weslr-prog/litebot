#!/usr/bin/env python3
"""
Fix positions.json for missing numeric fields
- Fills missing stop_price, max_risk_dollars, etc. with safe defaults for all 'entered' positions
- Ensures bot can operate without NoneType errors
"""
import json
import sys

SAFE_STOP_LOSS_PCT = 0.95  # 5% stop loss
SAFE_MAX_RISK = 30.0

with open('positions.json', 'r') as f:
    positions = json.load(f)

for pos in positions:
    if pos.get('status') == 'entered':
        entry_price = pos.get('entry_price')
        # Fix stop_price
        if pos.get('stop_price') is None and entry_price is not None:
            pos['stop_price'] = round(entry_price * SAFE_STOP_LOSS_PCT, 4)
        # Fix max_risk_dollars
        if pos.get('max_risk_dollars') is None:
            pos['max_risk_dollars'] = SAFE_MAX_RISK
        # Fix target_price (optional, leave as null if not used)
        # Add more fields as needed

with open('positions.json', 'w') as f:
    json.dump(positions, f, indent=2)

print('✅ positions.json fixed for safe bot operation.')

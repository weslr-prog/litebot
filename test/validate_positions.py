#!/usr/bin/env python3

"""
Position Data Validator
Ensures positions.json is compatible with ShortCyclePosition class
"""

import json
from datetime import datetime, date
from typing import List, Dict, Any

def validate_positions_file(file_path: str = "positions.json") -> bool:
    """Validate and optionally fix positions.json format"""
    
    print("🔍 Validating positions.json format...")
    
    try:
        with open(file_path, 'r') as f:
            positions_data = json.load(f)
        
        print(f"📊 Found {len(positions_data)} positions")
        
        issues_found = []
        fixed_positions = []
        
        for i, pos in enumerate(positions_data):
            position_issues = []
            
            # Check required fields
            required_fields = [
                'symbol', 'entry_date', 'exit_date', 'entry_price', 
                'position_size_shares', 'position_size_dollars', 'status'
            ]
            
            for field in required_fields:
                if field not in pos:
                    position_issues.append(f"Missing required field: {field}")
            
            # Check data types
            if 'entry_date' in pos:
                try:
                    # Ensure it's a valid date format
                    if isinstance(pos['entry_date'], str):
                        date.fromisoformat(pos['entry_date'])
                except ValueError:
                    position_issues.append(f"Invalid entry_date format: {pos['entry_date']}")
            
            if 'exit_date' in pos:
                try:
                    if isinstance(pos['exit_date'], str):
                        date.fromisoformat(pos['exit_date'])
                except ValueError:
                    position_issues.append(f"Invalid exit_date format: {pos['exit_date']}")
            
            # Check for problematic fields that might cause attribute errors
            problematic_fields = ['entry_time', 'action']  # These don't exist in ShortCyclePosition
            for field in problematic_fields:
                if field in pos:
                    position_issues.append(f"Deprecated field found: {field}")
            
            if position_issues:
                issues_found.extend([f"Position {i} ({pos.get('symbol', 'UNKNOWN')}): {issue}" for issue in position_issues])
            
            fixed_positions.append(pos)
        
        if issues_found:
            print(f"⚠️  Found {len(issues_found)} issues:")
            for issue in issues_found[:10]:  # Show first 10
                print(f"   - {issue}")
            if len(issues_found) > 10:
                print(f"   ... and {len(issues_found) - 10} more")
        else:
            print("✅ No critical issues found")
        
        # Test loading with actual ShortCyclePosition class
        print("\n🧪 Testing compatibility with ShortCyclePosition...")
        
        try:
            from traders.short_cycle_trader import ShortCycleTrader, ShortCycleConfig
            
            # Try to load positions using the actual trader
            config = ShortCycleConfig()
            trader = ShortCycleTrader(config)
            
            print(f"✅ Successfully loaded {len(trader.positions)} positions")
            print(f"📊 Position statuses:")
            
            status_counts = {}
            for pos in trader.positions:
                status = pos.status.value if hasattr(pos.status, 'value') else str(pos.status)
                status_counts[status] = status_counts.get(status, 0) + 1
            
            for status, count in status_counts.items():
                print(f"   - {status}: {count}")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to load positions with ShortCycleTrader: {e}")
            return False
    
    except FileNotFoundError:
        print(f"❌ File not found: {file_path}")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON format: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def main():
    print("🔧 LiteBotX Position Data Validator")
    print("=" * 50)
    
    success = validate_positions_file()
    
    if success:
        print("\n✅ Position data is compatible with ShortCycleTrader")
        print("🚀 Bot should run without attribute errors")
    else:
        print("\n❌ Position data needs fixing")
        print("💡 Consider backing up and regenerating positions.json")
    
    return success

if __name__ == "__main__":
    main()
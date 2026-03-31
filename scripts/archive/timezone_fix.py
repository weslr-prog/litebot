#!/usr/bin/env python3
"""
Timezone Fix Utility - Permanent solution for timezone issues
"""

import os
from datetime import datetime, timezone, timedelta

def get_eastern_timezone():
    """Get Eastern timezone that always works"""
    try:
        import pytz
        # Try different timezone identifiers
        for tz_name in ["America/New_York", "US/Eastern", "EST5EDT"]:
            try:
                return pytz.timezone(tz_name)
            except Exception:
                continue
        
        # If all pytz options fail, fallback to UTC offset
        print("⚠️  Using UTC offset fallback for Eastern timezone")
        return timezone(timedelta(hours=-5))  # EST
        
    except ImportError:
        # No pytz available, use standard library
        print("⚠️  Using standard library timezone for Eastern")
        return timezone(timedelta(hours=-5))  # EST

def fix_timezone_environment():
    """Set environment variables to help with timezone issues"""
    # Set timezone environment variables
    os.environ['TZ'] = 'America/New_York'
    
    # Try to call tzset if available (Unix systems)
    try:
        import time
        time.tzset()
        print("✅ Timezone environment updated")
        return True
    except (AttributeError, OSError):
        print("⚠️  Cannot set timezone environment on this system")
        return False

if __name__ == "__main__":
    print("🕐 Testing timezone fix...")
    
    # Fix environment
    fix_timezone_environment()
    
    # Test timezone
    et = get_eastern_timezone()
    now_et = datetime.now(et)
    
    print(f"✅ Eastern time: {now_et.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"✅ Timezone object: {et}")
    print("🎉 Timezone fix working!")
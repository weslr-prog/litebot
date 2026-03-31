#!/usr/bin/env python3
"""
Check Watchlist Freshness
Verifies the watchlist is recent and has enough candidates
"""
import json
from datetime import datetime, timedelta
import pytz

def check_watchlist_health():
    """Check if watchlist is fresh and healthy"""
    
    print("\n" + "="*60)
    print("🔍 WATCHLIST HEALTH CHECK")
    print("="*60 + "\n")
    
    try:
        # Load watchlist
        with open('logs/current_watchlist.json', 'r') as f:
            watchlist = json.load(f)
        
        # Parse generation time
        generated_str = watchlist.get('generated_at', '')
        generated_at = datetime.fromisoformat(generated_str)
        
        # Check age
        et_tz = pytz.timezone('US/Eastern')
        now = datetime.now(et_tz)
        age = now - generated_at
        age_hours = age.total_seconds() / 3600
        
        print(f"📅 Generated: {generated_at.strftime('%Y-%m-%d %I:%M %p ET')}")
        print(f"⏰ Age: {age_hours:.1f} hours")
        
        # Check symbol count
        symbols = watchlist.get('symbols', [])
        count = len(symbols)
        
        print(f"📊 Symbol Count: {count}")
        print(f"🎯 Min Required: 8")
        print(f"🎯 Target: 15")
        
        # Determine health status
        issues = []
        warnings = []
        
        # Age check (should be < 24 hours)
        if age_hours > 24:
            issues.append(f"Watchlist is {age_hours:.1f} hours old (should be < 24h)")
        elif age_hours > 18:
            warnings.append(f"Watchlist is {age_hours:.1f} hours old (getting stale)")
        
        # Count check
        if count < 8:
            issues.append(f"Only {count} symbols (need minimum 8)")
        elif count < 12:
            warnings.append(f"Only {count} symbols (target is 15)")
        
        # Show symbols
        print(f"\n📋 Symbols:")
        for i, symbol in enumerate(symbols, 1):
            print(f"   {i:2d}. {symbol}")
        
        # Report status
        print("\n" + "="*60)
        if issues:
            print("❌ WATCHLIST HAS ISSUES:")
            for issue in issues:
                print(f"   • {issue}")
            print("\n💡 Action: Run daily_watchlist_refresh.py to fix")
            return False
        elif warnings:
            print("⚠️  WATCHLIST HAS WARNINGS:")
            for warning in warnings:
                print(f"   • {warning}")
            print("\n💡 Consider: Running daily_watchlist_refresh.py")
            return True
        else:
            print("✅ WATCHLIST IS HEALTHY")
            print(f"   • Fresh: {age_hours:.1f} hours old")
            print(f"   • Full: {count} symbols")
            return True
        
    except FileNotFoundError:
        print("❌ ERROR: current_watchlist.json not found!")
        print("\n💡 Action: Run daily_watchlist_refresh.py to create")
        return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False
    finally:
        print("="*60 + "\n")


if __name__ == "__main__":
    import sys
    success = check_watchlist_health()
    sys.exit(0 if success else 1)

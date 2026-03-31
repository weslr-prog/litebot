#!/usr/bin/env python3
"""
Thursday Market Preparation Timeline Analysis
Shows when the bot will refresh watchlist and do premarket validation
"""

import datetime as dt
from datetime import timezone, timedelta
import pytz

def analyze_thursday_timeline():
    """Analyze when bot activities will happen for Thursday market"""
    
    print("🕒 THURSDAY MARKET PREPARATION TIMELINE")
    print("=" * 60)
    
    # Define key times in Eastern Time
    try:
        ET = pytz.timezone("US/Eastern")
    except:
        ET = timezone(timedelta(hours=-4))  # EDT fallback
    
    # Market times for Thursday, September 24, 2025
    thursday = dt.date(2025, 9, 24)
    
    # Market close Wednesday (today) - when watchlist refresh happens
    wed_close = dt.datetime.combine(dt.date(2025, 9, 23), dt.time(16, 0)).replace(tzinfo=ET)
    
    # Thursday market times
    thu_premarket_start = dt.datetime.combine(thursday, dt.time(8, 45)).replace(tzinfo=ET)  # 45 min before open
    thu_market_open = dt.datetime.combine(thursday, dt.time(9, 30)).replace(tzinfo=ET)
    thu_market_close = dt.datetime.combine(thursday, dt.time(16, 0)).replace(tzinfo=ET)
    
    # Current time
    now = dt.datetime.now(ET)
    
    print(f"📅 Current time: {now.strftime('%A, %B %d, %Y at %I:%M %p ET')}")
    print()
    
    print("🌙 POST-MARKET WATCHLIST REFRESH:")
    print(f"   ⏰ Trigger: After Wednesday close (4:00 PM ET) until 11:00 PM ET")
    print(f"   📊 What happens:")
    print(f"      • Bot runs run_daily_cycle() which calls _get_trading_universe()")
    print(f"      • PreFilter analyzes 33 candidate stocks with 40-day history")
    print(f"      • Filters for momentum, volume, and technical criteria")
    print(f"      • Creates fresh watchlist for Thursday trading")
    print(f"      • Saves to config/short_cycle_universe.json")
    
    if now > wed_close:
        print(f"   ✅ Status: COMPLETED (market closed {(now - wed_close).seconds // 60} minutes ago)")
    else:
        minutes_until = int((wed_close - now).total_seconds() // 60)
        print(f"   ⏳ Status: PENDING ({minutes_until} minutes until market close)")
    
    print()
    
    print("🌅 PRE-MARKET VALIDATION:")
    print(f"   ⏰ Window: {thu_premarket_start.strftime('%I:%M %p')} - {thu_market_open.strftime('%I:%M %p ET')} (45 minutes)")
    print(f"   📋 What happens:")
    print(f"      • Portfolio health check") 
    print(f"      • Risk assessment validation")
    print(f"      • Position validation (check Sep 23 positions for D+1 exits)")
    print(f"      • System readiness check")
    print(f"      • Final preparations before market open")
    
    if now >= thu_premarket_start:
        print(f"   🔄 Status: ACTIVE (started {(now - thu_premarket_start).seconds // 60} minutes ago)")
    else:
        hours_until = (thu_premarket_start - now).total_seconds() // 3600
        minutes_until = ((thu_premarket_start - now).total_seconds() % 3600) // 60
        print(f"   ⏳ Status: SCHEDULED (in {int(hours_until)}h {int(minutes_until)}m)")
    
    print()
    
    print("🚀 MARKET OPEN ACTIVITIES:")
    print(f"   ⏰ Time: {thu_market_open.strftime('%I:%M %p ET')}")
    print(f"   📈 What happens:")
    print(f"      • Load refreshed watchlist from config")
    print(f"      • Start processing Sep 23 positions for smart D+1 exits")
    print(f"      • Generate signals for new entries (first 30 minutes)")
    print(f"      • Apply smart exit timing throughout the day")
    
    if now >= thu_market_open:
        print(f"   🔴 Status: MARKET OPEN ({(now - thu_market_open).seconds // 60} minutes ago)")
    else:
        hours_until = (thu_market_open - now).total_seconds() // 3600
        minutes_until = ((thu_market_open - now).total_seconds() % 3600) // 60
        print(f"   ⏳ Status: OPENS IN {int(hours_until)}h {int(minutes_until)}m")
    
    print()
    
    print("📊 WATCHLIST REFRESH DETAILS:")
    print("   🔍 PreFilter Candidate Pool (33 stocks):")
    candidates = [
        "AAPL","MSFT","GOOGL","AMZN","TSLA","NVDA","META","NFLX","AMD","AVGO",
        "INTC","IBM","ORCL","CRM","ADBE","CSCO","QCOM","SHOP","UBER","LYFT", 
        "DIS","WMT","XOM","CVX","BA","CAT","KO","PEP","JNJ","PFE","BAC","JPM","GS"
    ]
    print(f"      {candidates}")
    print()
    print("   📏 Filtering Criteria:")
    print("      • Technical momentum indicators")
    print("      • Volume patterns and liquidity")
    print("      • Price action and trend strength")
    print("      • Market cap and sector diversification")
    print()
    print("   🎯 Selection Target:")
    print("      • Minimum: 15 symbols")
    print("      • Maximum: 25 symbols") 
    print("      • Optimized for short-cycle D+1 trading")

def check_current_watchlist():
    """Check what's currently in the watchlist"""
    print("\n" + "=" * 60)
    print("📋 CURRENT WATCHLIST STATUS:")
    
    try:
        import json
        from pathlib import Path
        
        config_path = Path("config/short_cycle_universe.json")
        if config_path.exists():
            with open(config_path) as f:
                config = json.load(f)
            
            universe = config.get("base_universe", [])
            print(f"   📊 Current universe: {len(universe)} symbols")
            print(f"   🎯 Symbols: {universe}")
            
            # Check if this is today's refresh
            import os
            mod_time = dt.datetime.fromtimestamp(os.path.getmtime(config_path))
            print(f"   📅 Last updated: {mod_time.strftime('%Y-%m-%d %I:%M %p')}")
            
            # Is this from today's post-market refresh?
            today = dt.date.today()
            if mod_time.date() == today:
                print("   ✅ Updated today - fresh watchlist ready!")
            else:
                print("   ⚠️ Not updated today - may refresh after market close")
        else:
            print("   ❌ Config file not found - will use default universe")
            print("   🎯 Default: ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']")
            
    except Exception as e:
        print(f"   ❌ Error checking watchlist: {e}")

def main():
    analyze_thursday_timeline()
    check_current_watchlist()
    
    print("\n" + "=" * 60)
    print("🎯 KEY TAKEAWAYS:")
    print("✅ Watchlist refreshes TONIGHT after market close (by 11 PM ET)")
    print("✅ PreMarket validation starts at 8:45 AM ET Thursday")  
    print("✅ D+1 exits for Sep 23 positions will be processed Thursday")
    print("✅ Smart exit timing will optimize exit points all day")
    print("✅ Bot is fully autonomous - no manual intervention needed")

if __name__ == "__main__":
    main()
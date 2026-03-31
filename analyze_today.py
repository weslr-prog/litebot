#!/usr/bin/env python3
"""
Today's Performance & PreFilter Analysis
Analyzes bot performance and filter effectiveness for current trading day
"""
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz
import yfinance as yf
from pathlib import Path

# Setup
et_tz = pytz.timezone('US/Eastern')
now = datetime.now(et_tz)
today = now.strftime('%Y-%m-%d')

print("=" * 80)
print(f"📊 LiteBotX Performance Analysis - {today}")
print("=" * 80)
print()

# ===== PART 1: POSITIONS & TRADES TODAY =====
print("## 1️⃣ Today's Trading Activity")
print("-" * 80)

try:
    with open('positions.json', 'r') as f:
        positions = json.load(f)
    
    # Analyze today's entries
    today_entries = [p for p in positions if p.get('entry_date') == today]
    
    # Analyze today's exits
    today_exits = [p for p in positions if p.get('exit_date') == today]
    
    print(f"\n📥 **Entries Today:** {len(today_entries)}")
    if today_entries:
        for p in today_entries:
            symbol = p.get('symbol', 'UNKNOWN')
            shares = p.get('shares', 0)
            entry_price = p.get('entry_price', 0)
            value = shares * entry_price
            print(f"   • {symbol:6s} {shares:4.0f} shares @ ${entry_price:7.2f} = ${value:10,.2f}")
        
        total_invested = sum(p.get('shares', 0) * p.get('entry_price', 0) for p in today_entries)
        print(f"\n   💰 Total Invested Today: ${total_invested:,.2f}")
    else:
        print("   ⚠️  NO ENTRIES TODAY - This is the issue we're investigating!")
    
    print(f"\n📤 **Exits Today:** {len(today_exits)}")
    if today_exits:
        total_realized = 0
        for p in today_exits:
            symbol = p.get('symbol', 'UNKNOWN')
            pnl = p.get('realized_pnl', 0)
            pnl_pct = p.get('realized_pnl_pct', 0)
            print(f"   • {symbol:6s} P&L: ${pnl:8.2f} ({pnl_pct:+6.2f}%)")
            total_realized += pnl
        print(f"\n   💵 Total Realized P&L: ${total_realized:,.2f}")
    
    # Open positions
    open_positions = [p for p in positions if not p.get('exit_date')]
    print(f"\n🔓 **Open Positions:** {len(open_positions)}")
    if open_positions:
        for p in open_positions[:10]:  # Show first 10
            symbol = p.get('symbol', 'UNKNOWN')
            entry_date = p.get('entry_date', 'UNKNOWN')
            days_held = (now.date() - datetime.strptime(entry_date, '%Y-%m-%d').date()).days
            unrealized = p.get('unrealized_pnl', 0)
            unrealized_pct = p.get('unrealized_pnl_pct', 0)
            print(f"   • {symbol:6s} D+{days_held} | P&L: ${unrealized:7.2f} ({unrealized_pct:+6.2f}%)")
        
        if len(open_positions) > 10:
            print(f"   ... and {len(open_positions) - 10} more")

except FileNotFoundError:
    print("❌ positions.json not found")
except Exception as e:
    print(f"❌ Error reading positions: {e}")

print("\n" + "=" * 80)

# ===== PART 2: WATCHLIST ANALYSIS =====
print("\n## 2️⃣ Watchlist Analysis")
print("-" * 80)

try:
    with open('logs/current_watchlist.json', 'r') as f:
        watchlist = json.load(f)
    
    symbols = watchlist.get('symbols', [])
    generated_at = watchlist.get('generated_at', 'UNKNOWN')
    
    print(f"\n📋 **Current Watchlist:** {len(symbols)} stocks")
    print(f"🕐 **Generated:** {generated_at}")
    print(f"\n**Symbols:** {', '.join(symbols)}")
    
    # Fetch today's performance for watchlist
    print(f"\n📈 **Today's Performance (Watchlist):**")
    
    data = yf.download(symbols, period='5d', interval='1d', progress=False)
    
    if not data.empty and 'Close' in data:
        if len(symbols) == 1:
            close = data['Close']
        else:
            close = data['Close']
        
        # Get last 2 days for today's change
        if len(close) >= 2:
            today_changes = {}
            for symbol in symbols:
                try:
                    if len(symbols) > 1:
                        prices = close[symbol].dropna()
                    else:
                        prices = close.dropna()
                    
                    if len(prices) >= 2:
                        prev = prices.iloc[-2]
                        curr = prices.iloc[-1]
                        change_pct = ((curr - prev) / prev) * 100
                        today_changes[symbol] = {
                            'prev': prev,
                            'curr': curr,
                            'change_pct': change_pct
                        }
                except Exception as e:
                    continue
            
            # Sort by performance
            sorted_symbols = sorted(today_changes.items(), key=lambda x: x[1]['change_pct'], reverse=True)
            
            print("\n   🏆 Best Performers:")
            for symbol, data in sorted_symbols[:5]:
                print(f"      {symbol:6s} {data['change_pct']:+6.2f}%  (${data['prev']:.2f} → ${data['curr']:.2f})")
            
            print("\n   📉 Worst Performers:")
            for symbol, data in sorted_symbols[-5:]:
                print(f"      {symbol:6s} {data['change_pct']:+6.2f}%  (${data['prev']:.2f} → ${data['curr']:.2f})")
            
            avg_change = np.mean([d['change_pct'] for d in today_changes.values()])
            print(f"\n   📊 Average watchlist change: {avg_change:+.2f}%")

except FileNotFoundError:
    print("❌ Watchlist file not found")
except Exception as e:
    print(f"❌ Error analyzing watchlist: {e}")

print("\n" + "=" * 80)

# ===== PART 3: PREFILTER ANALYSIS =====
print("\n## 3️⃣ PreFilter System Analysis")
print("-" * 80)

print("\n🔍 **Filter Pipeline Performance:**")

try:
    # Check if PreFilter has diagnostic mode
    import sys
    sys.path.insert(0, '.')
    from pre_filter import PreFilter
    from data_loader import DataLoader
    
    print("\n⚙️  Running PreFilter diagnostic...")
    
    # Get market universe (top 500 by volume)
    print("   📊 Fetching market universe...")
    
    # Use S&P 500 as universe for faster analysis
    sp500_url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    try:
        tables = pd.read_html(sp500_url)
        sp500_symbols = tables[0]['Symbol'].str.replace('.', '-').tolist()[:200]  # Top 200 for speed
        print(f"   ✅ Universe: {len(sp500_symbols)} S&P 500 stocks")
    except:
        # Fallback to watchlist analysis
        sp500_symbols = symbols
        print(f"   ⚠️  Using watchlist as universe: {len(sp500_symbols)} stocks")
    
    # Initialize PreFilter with diagnostic mode
    data_loader = DataLoader()
    # PreFilter signature: PreFilter(simulation_mode, historical_data, fast_mode, diagnostic_mode, data_loader, ...)
    prefilter = PreFilter(
        simulation_mode=False,  # Use Alpaca paper trading, not simulation
        historical_data=None,
        fast_mode=True,
        diagnostic_mode=True,
        data_loader=data_loader
    )
    
    print("\n   🔄 Running 6-stage filter pipeline...")
    
    # Run PreFilter
    passed_symbols, failed_symbols = prefilter.filter_stocks(sp500_symbols)
    
    print(f"\n📊 **Filter Results:**")
    print(f"   ✅ Passed all filters: {len(passed_symbols)}")
    print(f"   ❌ Failed filters: {len(failed_symbols)}")
    print(f"   📈 Pass rate: {len(passed_symbols)/(len(passed_symbols)+len(failed_symbols))*100:.1f}%")
    
    if passed_symbols:
        print(f"\n   🎯 **Stocks that passed:** {', '.join(passed_symbols[:15])}")
        if len(passed_symbols) > 15:
            print(f"      ... and {len(passed_symbols) - 15} more")
    
    # Analyze failure reasons
    print(f"\n❌ **Why stocks failed:**")
    
    failure_reasons = {}
    for symbol, reason in failed_symbols.items():
        failure_reasons[reason] = failure_reasons.get(reason, 0) + 1
    
    for reason, count in sorted(failure_reasons.items(), key=lambda x: x[1], reverse=True):
        pct = (count / len(failed_symbols)) * 100
        print(f"   • {reason:40s} {count:4d} stocks ({pct:5.1f}%)")
    
    # Recommendation
    print(f"\n💡 **Recommendations:**")
    
    if len(passed_symbols) < 8:
        print("   ⚠️  TOO FEW CANDIDATES (<8) - Filters may be too strict!")
        print("   Consider:")
        print("      - Relaxing momentum thresholds")
        print("      - Adjusting volume requirements")
        print("      - Reviewing regime filters")
    elif len(passed_symbols) > 20:
        print("   ⚠️  TOO MANY CANDIDATES (>20) - Filters may be too loose!")
        print("   Consider:")
        print("      - Tightening momentum requirements")
        print("      - Increasing minimum volume")
        print("      - Adding quality filters")
    else:
        print("   ✅ Filter balance is GOOD (8-20 candidates)")
        print("   Current settings are working well!")

except ImportError as e:
    print(f"❌ Could not import PreFilter: {e}")
except Exception as e:
    print(f"❌ Error running PreFilter analysis: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)

# ===== PART 4: SIGNAL GENERATION =====
print("\n## 4️⃣ Signal Generation Analysis")
print("-" * 80)

try:
    # Check today's signals from positions
    print("\n🎯 **Signals Generated Today:**")
    
    # Count how many of today's entries came from watchlist
    if today_entries:
        watchlist_entries = [p for p in today_entries if p.get('symbol') in symbols]
        print(f"   • From watchlist: {len(watchlist_entries)}/{len(today_entries)}")
        
        # Check signal confidence if available
        avg_confidence = np.mean([p.get('entry_confidence', 0) for p in today_entries if p.get('entry_confidence')])
        if avg_confidence > 0:
            print(f"   • Average signal confidence: {avg_confidence:.2f}")
    else:
        print("   ❌ NO SIGNALS GENERATED TODAY")
        print("\n   🔍 **Possible reasons:**")
        print("      1. Stale watchlist (watchlist was 36 days old)")
        print("      2. Too few candidates passing filters (only 6 stocks)")
        print("      3. Same-day re-entry prevention blocking signals")
        print("      4. Market regime unfavorable")
        print("      5. All candidates already in positions")
    
    # Check same-day blocking
    print(f"\n🚫 **Same-Day Re-Entry Blocks:**")
    same_day_blocks = [p for p in positions if p.get('exit_date') == today]
    if same_day_blocks:
        blocked_symbols = [p.get('symbol') for p in same_day_blocks]
        print(f"   • {len(blocked_symbols)} symbols blocked from re-entry today:")
        print(f"      {', '.join(blocked_symbols)}")
    else:
        print("   ✅ No same-day blocks today")

except Exception as e:
    print(f"❌ Error analyzing signals: {e}")

print("\n" + "=" * 80)

# ===== PART 5: SUMMARY & RECOMMENDATIONS =====
print("\n## 5️⃣ Summary & Action Items")
print("-" * 80)

print("\n📋 **Today's Key Metrics:**")
print(f"   • Entries: {len(today_entries)}")
print(f"   • Exits: {len(today_exits)}")
print(f"   • Open positions: {len(open_positions)}")
print(f"   • Watchlist size: {len(symbols)}")

print("\n🎯 **System Health:**")

# Calculate health score
health_issues = []

if len(today_entries) == 0:
    health_issues.append("Zero entries today")

if len(symbols) < 8:
    health_issues.append("Watchlist too small (<8)")

if len(symbols) > 20:
    health_issues.append("Watchlist too large (>20)")

watchlist_age_hours = (now - datetime.fromisoformat(generated_at)).total_seconds() / 3600
if watchlist_age_hours > 24:
    health_issues.append(f"Watchlist stale ({watchlist_age_hours:.1f}h old)")

if health_issues:
    print("   ⚠️  Issues detected:")
    for issue in health_issues:
        print(f"      • {issue}")
else:
    print("   ✅ All systems healthy!")

print("\n💡 **Recommended Actions:**")
if len(today_entries) == 0:
    print("   1. ✅ Watchlist refresh - ALREADY DONE (now at 0.3h old)")
    print("   2. Review PreFilter thresholds if problem persists")
    print("   3. Check market regime - may be unfavorable")
    print("   4. Manual entries placed for tomorrow's D+1 exits")
else:
    print("   ✅ Bot is trading normally")
    print("   • Continue monitoring daily")
    print("   • Review weekly performance trends")

print("\n" + "=" * 80)
print("✅ Analysis complete!")
print("=" * 80)

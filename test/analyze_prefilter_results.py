#!/usr/bin/env python3
"""
Analyze what PreFilter ACTUALLY selected vs what got added as backups
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pre_filter import PreFilter
from data_loader import DataLoader
import pandas as pd
import json

print("=" * 80)
print("🔍 PREFILTER ANALYSIS - What Actually Passed vs Backups")
print("=" * 80)

# Load config
with open('config/short_cycle_universe.json', 'r') as f:
    config = json.load(f)

print(f"\n📋 Config Settings:")
print(f"   min_symbols: {config['min_symbols']}")
print(f"   max_symbols: {config['max_symbols']}")
print(f"   base_universe: {len(config['base_universe'])} stocks")

# Candidate pool (from short_cycle_trader.py)
candidates = [
    "AAPL","MSFT","GOOGL","AMZN","TSLA","NVDA","META","NFLX","AMD","AVGO",
    "INTC","IBM","ORCL","CRM","ADBE","CSCO","QCOM","SHOP","UBER","LYFT",
    "DIS","WMT","XOM","CVX","BA","CAT","KO","PEP","JNJ","PFE","BAC","JPM","GS",
    "V","MA","HD","UNH","MCD","NKE","ABBV","TMO","ACN","TXN","LLY","COST",
    "HON","UPS","BMY","SBUX","MDT","GILD","MMM","GE","F","GM","T","VZ"
]

print(f"\n📊 PreFilter Candidate Pool: {len(candidates)} stocks")

# Initialize PreFilter
print("\n🔄 Running PreFilter analysis...")
data_loader = DataLoader()
prefilter = PreFilter(
    simulation_mode=False,
    data_loader=data_loader,
    fast_mode=True,
    enable_intraday_analysis=False,
    max_intraday_analyses_per_day=50
)

# Fetch data and filter
history_df = prefilter.fetch_history(candidates, days=40, use_cache=True)
print(f"   ✅ Fetched {len(history_df)} rows of historical data")

filtered = prefilter.filter_assets(history_df)
print(f"   ✅ PreFilter returned {len(filtered)} rows")

# Get latest snapshot and rank by score
snap = filtered.groupby('symbol').tail(1)
if 'pf_score' in snap.columns:
    ranked = snap.sort_values('pf_score', ascending=False)
else:
    ranked = snap.sort_values('volume', ascending=False)

ranked_symbols = ranked['symbol'].tolist()

print(f"\n✅ PreFilter Results: {len(ranked_symbols)} stocks PASSED all filters")
print("\n" + "=" * 80)
print("🏆 STOCKS THAT PASSED PREFILTER (ranked by score):")
print("=" * 80)

for idx, symbol in enumerate(ranked_symbols, 1):
    row = snap[snap['symbol'] == symbol].iloc[0]
    score = row.get('pf_score', 'N/A')
    momentum = row.get('momentum', 0) * 100 if 'momentum' in row else 0
    volatility = row.get('volatility', 0) * 100 if 'volatility' in row else 0
    volume = row.get('avg_volume_20', row.get('volume', 0))
    price = row.get('close', 0)
    
    print(f"{idx:2d}. {symbol:6s} - Score: {score:6.2f} | "
          f"Price: ${price:7.2f} | Mom: {momentum:+6.2f}% | "
          f"Vol: {volatility:5.2f}% | AvgVol: {volume:,.0f}")

# Now simulate the backup logic
min_symbols = config['min_symbols']
max_symbols = config['max_symbols']
base_universe = config['base_universe']

print(f"\n" + "=" * 80)
print(f"📦 BACKUP LOGIC (min_symbols={min_symbols}):")
print("=" * 80)

if len(ranked_symbols) < min_symbols:
    print(f"\n⚠️  PreFilter only returned {len(ranked_symbols)} stocks")
    print(f"⚠️  Need {min_symbols - len(ranked_symbols)} backups to reach minimum")
    
    # Simulate the top-up process
    final_list = ranked_symbols[:max_symbols] if max_symbols else ranked_symbols[:]
    backups_added = []
    
    for sym in base_universe:
        if sym not in final_list:
            backups_added.append(sym)
            final_list.append(sym)
            if len(final_list) >= min_symbols:
                break
    
    print(f"\n📋 Backups Added ({len(backups_added)}):")
    for idx, sym in enumerate(backups_added, 1):
        print(f"   {idx:2d}. {sym}")
    
    print(f"\n❌ CRITICAL ISSUE: These {len(backups_added)} backups were added WITHOUT passing PreFilter!")
    print(f"   They may NOT meet the quality criteria:")
    print(f"   - Liquidity: $10M+ daily volume")
    print(f"   - Volatility: 2-8% ATR sweet spot")
    print(f"   - Momentum: 3%+ recent move")
    print(f"   - Volume surge: 1.5x average")
    
    # Check which backups failed which criteria
    print(f"\n🔍 Analyzing why backups didn't pass PreFilter...")
    
    for backup in backups_added[:10]:  # Check first 10
        # Try to find this symbol in original history
        sym_data = history_df[history_df['symbol'] == backup]
        if len(sym_data) == 0:
            print(f"\n   ❌ {backup}: NO DATA (likely delisted or API issue)")
            continue
        
        latest = sym_data.iloc[-1]
        price = latest.get('close', 0)
        volume = latest.get('volume', 0)
        
        # Calculate metrics
        issues = []
        if price < 20:
            issues.append(f"Price too low (${price:.2f} < $20)")
        if price > 500:
            issues.append(f"Price too high (${price:.2f} > $500)")
        
        # Check volume
        avg_vol = sym_data['volume'].tail(20).mean() if len(sym_data) >= 20 else volume
        dollar_vol = avg_vol * price
        if dollar_vol < 10_000_000:
            issues.append(f"Low liquidity (${dollar_vol/1e6:.1f}M < $10M)")
        
        # Check momentum (simplified)
        if len(sym_data) >= 10:
            momentum = (latest['close'] - sym_data.iloc[-10]['close']) / sym_data.iloc[-10]['close']
            if abs(momentum) < 0.03:
                issues.append(f"Low momentum ({momentum*100:.1f}% < 3%)")
        
        if issues:
            print(f"\n   ⚠️  {backup}:")
            for issue in issues:
                print(f"      - {issue}")
        else:
            print(f"\n   ✅ {backup}: Met criteria (may have failed on other metrics)")

else:
    print(f"\n✅ PreFilter returned {len(ranked_symbols)} stocks (>= {min_symbols} minimum)")
    print(f"   No backups needed!")

print("\n" + "=" * 80)
print("💡 RECOMMENDATIONS:")
print("=" * 80)

print("""
1. **ISSUE: Diluting quality with unvetted backups**
   - PreFilter only passed 8 high-quality stocks
   - Bot added 22 random stocks from config to reach min=30
   - These 22 may not meet momentum/volatility/liquidity criteria
   - Signal generator wastes API calls analyzing bad candidates

2. **SOLUTION A: Trust PreFilter (Recommended)**
   - Change min_symbols from 30 to 8 (or even 5)
   - Only trade stocks that PASS all PreFilter criteria
   - Quality over quantity
   - Better to have 8 great candidates than 30 mediocre ones

3. **SOLUTION B: Improve PreFilter thresholds**
   - Current filters may be too strict
   - Consider relaxing:
     * Min momentum: 3% → 2%
     * Min volatility: 2% → 1.5%
     * Volume surge: 1.5x → 1.3x
   - Would pass more stocks while maintaining quality

4. **SOLUTION C: Two-tier system**
   - Tier 1: PreFilter passed (8 stocks) - HIGH PRIORITY
   - Tier 2: Config backups (22 stocks) - LOW PRIORITY
   - Signal generator focuses on Tier 1 first
   - Only uses Tier 2 if Tier 1 produces <8 signals

5. **PRICE FILTER: $20 minimum**
   - Current: $20 minimum
   - Your question: Lower to $10?
   - ❌ NOT RECOMMENDED because:
     * $10-20 stocks often have:
       - Lower institutional interest
       - Higher bid-ask spreads
       - More manipulation/volatility
       - Less predictable patterns
     * D+1 strategy needs PREDICTABLE movers
     * Better to stick with $20+ for quality
   
   **Exception:** If you want to lower it:
   - Set minimum to $15 (middle ground)
   - Add tighter volatility control (max 6% ATR instead of 8%)
   - Increase minimum volume to 100k shares/day
   - This balances opportunity vs risk

6. **IMMEDIATE ACTION:**
   - Set min_symbols to 10 in config (from 30)
   - This allows PreFilter to control quality
   - If only 8 pass, you get 8 (not diluted with backups)
   - Signal generator will be more efficient
""")

print("\n" + "=" * 80)
print("✅ Analysis Complete")
print("=" * 80)

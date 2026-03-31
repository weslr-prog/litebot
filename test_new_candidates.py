#!/usr/bin/env python3
"""
Test New Mid-Cap Candidate Pool
================================

Verifies that the new hardcoded candidate list
contains stocks in the $10-30 range.
"""

# Mid-cap candidates from the updated code
candidates = [
    # EV & Tech Mid-Caps ($10-30)
    "PLTR","RIVN","LCID","NIO","XPEV","LI","GOEV","FSR",
    # Fintech & Apps ($10-30)
    "HOOD","SOFI","UPST","AFRM","SQ","OPEN","COIN",
    # Social/Media ($10-30)
    "SNAP","PINS","MTCH","BMBL","RBLX","U","DKNG",
    # Cloud/SaaS ($10-30)
    "PATH","SNOW","DDOG","CRWD","ZS","NET","MDB","FSLY",
    # Biotech/Health ($10-30)
    "MRNA","NVAX","TDOC","PTON","DOCS","VCYT","SDGR",
    # Energy/Materials ($10-30)
    "PLUG","BE","CHPT","BLNK","QS","MP","LAC",
    # Other Volatiles ($10-30)
    "AMC","GME","WISH","CLOV","SKLZ","SPCE","ASTS","IONQ",
    # Added for liquidity
    "F","NOK","BBD","VALE","BTG","GOLD","AUY","FCX"
]

print("\n" + "="*70)
print("MID-CAP CANDIDATE POOL TEST")
print("="*70)
print(f"\nTotal candidates: {len(candidates)}")
print(f"Expected range: $10-30")
print("\nCandidate categories:")
print(f"  • EV & Tech: PLTR, RIVN, LCID, NIO, XPEV, LI, GOEV, FSR")
print(f"  • Fintech: HOOD, SOFI, UPST, AFRM, SQ, OPEN, COIN")
print(f"  • Social/Media: SNAP, PINS, MTCH, BMBL, RBLX, U, DKNG")
print(f"  • Cloud/SaaS: PATH, SNOW, DDOG, CRWD, ZS, NET, MDB, FSLY")
print(f"  • Biotech: MRNA, NVAX, TDOC, PTON, DOCS, VCYT, SDGR")
print(f"  • Energy: PLUG, BE, CHPT, BLNK, QS, MP, LAC")
print(f"  • Volatiles: AMC, GME, WISH, CLOV, SKLZ, SPCE, ASTS, IONQ")
print(f"  • Liquidity: F, NOK, BBD, VALE, BTG, GOLD, AUY, FCX")

print("\n" + "="*70)
print("WHAT CHANGED")
print("="*70)
print("\n❌ OLD CANDIDATES (Large-Caps):")
print("   AAPL, MSFT, GOOGL, AMZN, TSLA, NVDA, META, NFLX, AMD")
print("   SHOP, XOM, UPS, CSCO - ALL > $30")
print("\n✅ NEW CANDIDATES (Mid-Caps):")
print("   PLTR, RIVN, SNAP, HOOD, SOFI - Most in $10-30 range")

print("\n" + "="*70)
print("EXPECTED BEHAVIOR AFTER RESTART")
print("="*70)
print("\n1. PreFilter will scan these 64 mid-cap candidates")
print("2. Filter for $10-30 price range (many will pass)")
print("3. Filter for 3-12% volatility (volatile mid-caps)")
print("4. Select top 10-15 stocks by momentum/quality")
print("\n✅ Result: Universe of PLTR, RIVN, SNAP, HOOD, SOFI type stocks")
print("❌ Gone: AMD, SHOP, XOM, UPS, CSCO (not in candidate list)")

print("\n" + "="*70)
print("RESTART REQUIRED")
print("="*70)
print("\nThe bot must be restarted to use the new candidate list:")
print("  pkill -f start_small_portfolio_trader.py")
print("  python3 start_small_portfolio_trader.py")
print("\n" + "="*70)

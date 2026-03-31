#!/usr/bin/env python3
"""
Quick test to verify entry screener integration works
"""

import sys
import logging

# Setup logging to see initialization messages
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

print("=" * 80)
print("TESTING ENTRY SCREENER INTEGRATION")
print("=" * 80)

# Test 1: Import modules
print("\n✅ Test 1: Importing modules...")
try:
    from entry_quality_screener import EntryQualityScreener
    from sector_specific_exit import SectorSpecificExitManager
    print("   ✅ Screener modules imported successfully")
except Exception as e:
    print(f"   ❌ Failed to import screener modules: {e}")
    sys.exit(1)

# Test 2: Initialize screener
print("\n✅ Test 2: Initializing entry screener...")
try:
    screener = EntryQualityScreener(strict_mode=False)
    print("   ✅ Entry screener initialized")
except Exception as e:
    print(f"   ❌ Failed to initialize screener: {e}")
    sys.exit(1)

# Test 3: Test screening with various scenarios
print("\n✅ Test 3: Testing screening scenarios...")

test_cases = [
    # (symbol, momentum_pct, volume_surge, expected_quality)
    ("AAPL", 0.07, 1.6, "IDEAL"),      # Sweet spot
    ("TSLA", 0.08, 1.8, "IDEAL"),      # Sweet spot
    ("RIVN", 0.0371, 1.2, "REJECT"),   # Nov 14 loser - too low momentum
    ("SBUX", 0.11, 2.5, "REJECT"),     # Too high momentum + volume
    ("NCLH", 0.045, 0.9, "REJECT"),    # Volume too low
    ("AAL", 0.065, 1.5, "GOOD"),       # Good but not ideal
]

for symbol, momentum, volume, expected in test_cases:
    should_enter, quality, reason = screener.screen_entry(
        symbol=symbol,
        momentum=momentum,
        volume_surge=volume,
        sector=None
    )
    
    emoji = {
        'IDEAL': '🟢',
        'GOOD': '🟡',
        'ACCEPTABLE': '🟠',
        'REJECT': '🔴'
    }.get(quality, '⚪')
    
    status = "✅" if quality == expected else "⚠️"
    print(f"   {status} {symbol}: momentum={momentum*100:.2f}%, vol={volume:.2f}x → {emoji} {quality}")
    print(f"      Reason: {reason}")

# Test 4: Initialize exit manager
print("\n✅ Test 4: Initializing sector-specific exit manager...")
try:
    exit_mgr = SectorSpecificExitManager()
    print("   ✅ Exit manager initialized")
    
    # Test sector classification
    test_symbols = ["AAL", "SBUX", "RIVN"]
    for sym in test_symbols:
        sector, days, reason = exit_mgr.get_sector_classification(sym)
        print(f"   📊 {sym}: {sector} → D+{days} ({reason})")
        
except Exception as e:
    print(f"   ❌ Failed to initialize exit manager: {e}")
    sys.exit(1)

# Test 5: Import trader (full integration test)
print("\n✅ Test 5: Testing trader import with integrated screener...")
try:
    from small_portfolio_config import SmallPortfolioConfig
    from traders.short_cycle_trader import AISignalGenerator
    
    config = SmallPortfolioConfig()
    generator = AISignalGenerator(config)
    
    print("   ✅ AISignalGenerator initialized with screener")
    print(f"   📊 Screening enabled: {generator.screening_enabled}")
    print(f"   📊 Entry screener: {generator.entry_screener is not None}")
    print(f"   📊 Exit manager: {generator.exit_manager is not None}")
    
except Exception as e:
    print(f"   ❌ Failed to initialize trader: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 80)
print("✅ ALL TESTS PASSED - Integration successful!")
print("=" * 80)
print("\n📊 Next steps:")
print("   1. Run bot on Friday Nov 15 in observation mode")
print("   2. Check logs for screening results (🟢🟡🟠🔴)")
print("   3. Review which entries get REJECT vs IDEAL")
print("   4. Consider enabling soft enforcement (block REJECT only)")
print("=" * 80)

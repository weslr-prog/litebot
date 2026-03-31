#!/usr/bin/env python3
"""
Test Universe Health Checker
Demonstrates quarterly review system without waiting for actual quarter
"""

import sys
from pathlib import Path
import datetime as dt

# Add project root
sys.path.insert(0, str(Path(__file__).parent))

from bot_v2.maintenance import UniverseHealthChecker
from bot_v2.config.trading_config import ShortCycleConfig
from bot_v2.data.data_loader import DataLoader
from logger import setup_logger

def main():
    print("=" * 80)
    print("🏥 UNIVERSE HEALTH CHECKER TEST")
    print("=" * 80)
    print()
    
    # Initialize
    config = ShortCycleConfig()
    data_loader = DataLoader()
    logger = setup_logger("health_check_test")
    
    checker = UniverseHealthChecker(config, data_loader, logger)
    
    # Check if quarterly review is due
    print("📅 Checking if quarterly review is due...")
    should_run, reason = checker.should_run_check()
    
    print(f"   Status: {reason}")
    print(f"   Should run: {'✅ Yes' if should_run else '❌ No'}")
    print()
    
    if not should_run:
        print("ℹ️  Quarterly reviews run automatically during first week of:")
        print("   • January (Q1)")
        print("   • April (Q2)")
        print("   • July (Q3)")
        print("   • October (Q4)")
        print()
        print("📋 Current date:", dt.date.today())
        print()
    
    # Offer to run anyway for testing
    print("Would you like to run the health check anyway? (for testing)")
    response = input("Run check? (y/n): ").strip().lower()
    
    if response == 'y':
        print()
        print("🔄 Running health check on 280 stocks...")
        print("⚠️  This may take 2-3 minutes (checking price, volume, delisting)")
        print()
        
        results = checker.run_health_check()
        
        print()
        print("=" * 80)
        print("📊 SUMMARY")
        print("=" * 80)
        print(f"Total stocks: {results['total_stocks']}")
        print(f"Issues found: {results['issues_found']}")
        print()
        print(f"Delistings: {len(results['delisted'])}")
        print(f"Low volume: {len(results['low_volume'])}")
        print(f"Price violations: {len(results['price_violations'])}")
        print(f"Data errors: {len(results['data_errors'])}")
        print()
        print(f"Recommendation: {results['recommendation']}")
        print("=" * 80)
        
        # Ask if we should mark as complete
        print()
        print("Mark this check as complete? (will prevent prompts until next quarter)")
        mark = input("Mark complete? (y/n): ").strip().lower()
        
        if mark == 'y':
            checker.mark_check_complete()
            print("✅ Check marked complete")
        else:
            print("⏭️  Check not marked (will prompt again)")
    else:
        print("⏭️  Skipping health check")
    
    print()
    print("=" * 80)
    print("✅ Test complete")
    print("=" * 80)

if __name__ == '__main__':
    main()

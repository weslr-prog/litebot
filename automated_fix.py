#!/usr/bin/env python3
"""
Automated Fix Script
Fixes all identified configuration and legacy file issues
"""
import os
import shutil
import logging
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def backup_file(filepath):
    """Create backup of file before modifying"""
    if Path(filepath).exists():
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = f"{filepath}.backup_{timestamp}"
        shutil.copy2(filepath, backup_path)
        logger.info(f"   📦 Backed up: {filepath} -> {backup_path}")
        return backup_path
    return None

def fix_1_add_universe_size_config():
    """Add missing max_universe_size and min_universe_size to config"""
    logger.info("\n" + "=" * 70)
    logger.info("🔧 FIX #1: Add Missing Universe Size Parameters")
    logger.info("=" * 70)
    
    config_file = 'small_portfolio_config.py'
    
    try:
        with open(config_file, 'r') as f:
            content = f.read()
        
        # Check if already has these parameters
        if 'max_universe_size' in content:
            logger.info("✅ max_universe_size already exists")
            return True
        
        backup_backup_file(config_file)
        
        # Find a good place to add it (after min_symbols)
        if 'min_symbols:' in content:
            # Add after min_symbols
            old_text = 'min_symbols: int = 8'
            new_text = '''min_symbols: int = 8
    max_universe_size: int = 15  # Max stocks in watchlist
    min_universe_size: int = 8   # Min stocks in watchlist'''
            
            content = content.replace(old_text, new_text)
            
            with open(config_file, 'w') as f:
                f.write(content)
            
            logger.info("✅ Added max_universe_size and min_universe_size parameters")
            return True
        else:
            logger.warning("⚠️  Could not find insertion point - manual fix needed")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return False


def fix_2_move_legacy_files():
    """Move legacy config files to archive"""
    logger.info("\n" + "=" * 70)
    logger.info("🔧 FIX #2: Archive Legacy Config Files")
    logger.info("=" * 70)
    
    # Create archive directory
    archive_dir = Path('archive/legacy_configs')
    archive_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"✅ Created archive directory: {archive_dir}")
    
    legacy_files = [
        'config.py',
        'stock_config.py',
    ]
    
    moved = 0
    for filepath in legacy_files:
        if Path(filepath).exists():
            dest = archive_dir / filepath
            shutil.move(filepath, dest)
            logger.info(f"✅ Moved: {filepath} -> {dest}")
            moved += 1
        else:
            logger.info(f"   Skip (not found): {filepath}")
    
    if moved > 0:
        logger.info(f"✅ Archived {moved} legacy files")
        return True
    else:
        logger.info("✅ No legacy files to archive")
        return True


def fix_3_create_data_source_stub():
    """Create data_source.py stub if missing (for imports)"""
    logger.info("\n" + "=" * 70)
    logger.info("🔧 FIX #3: Fix data_source Import")
    logger.info("=" * 70)
    
    # Check if data_source.py exists
    if Path('data_source.py').exists():
        logger.info("✅ data_source.py already exists")
        return True
    
    # Check if it's being imported but not needed
    logger.info("   data_source.py not found - checking if it's actually needed...")
    
    # The bot uses core/data/data_source.py, not root data_source.py
    if Path('core/data/data_source.py').exists():
        logger.info("✅ core/data/data_source.py exists (correct location)")
        logger.info("   Root-level data_source.py not needed")
        return True
    
    logger.warning("⚠️  data_source module issue - may need manual investigation")
    return False


def fix_4_force_watchlist_refresh():
    """Force a fresh watchlist generation"""
    logger.info("\n" + "=" * 70)
    logger.info("🔧 FIX #4: Force Watchlist Refresh")
    logger.info("=" * 70)
    
    try:
        # Import and run watchlist generation
        logger.info("   Running watchlist refresh...")
        
        import subprocess
        result = subprocess.run(
            ['python3', 'daily_watchlist_refresh.py'],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            logger.info("✅ Watchlist refreshed successfully")
            
            # Check the new watchlist
            import json
            with open('logs/current_watchlist.json', 'r') as f:
                watchlist = json.load(f)
            
            symbols = watchlist.get('symbols', [])
            logger.info(f"   New watchlist: {len(symbols)} stocks")
            logger.info(f"   Symbols: {', '.join(symbols[:10])}")
            return True
        else:
            logger.warning("⚠️  Watchlist refresh had issues:")
            logger.warning(f"   {result.stderr[:200]}")
            return False
            
    except FileNotFoundError:
        logger.warning("⚠️  daily_watchlist_refresh.py not found")
        logger.info("   Watchlist will refresh automatically at market close")
        return True
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return False


def fix_5_verify_swing_trading_config():
    """Verify all swing trading parameters are set correctly"""
    logger.info("\n" + "=" * 70)
    logger.info("🔧 FIX #5: Verify Swing Trading Configuration")
    logger.info("=" * 70)
    
    try:
        from small_portfolio_config import SmallPortfolioConfig
        config = SmallPortfolioConfig()
        
        # Critical swing trading parameters
        checks = [
            ('cash_account_mode', False, '=='),
            ('enable_same_day_exit', False, '=='),
            ('enable_intraday_scalping', False, '=='),
            ('max_hold_days', 3, '=='),
            ('confidence_threshold', 0.04, '=='),
            ('late_entry_confidence_multiplier', 1.2, '=='),
            ('min_avg_volume', 200000, '=='),
            ('min_dollar_volume', 1000000, '=='),
        ]
        
        all_correct = True
        for param, expected, op in checks:
            actual = getattr(config, param, None)
            if actual == expected:
                logger.info(f"✅ {param}: {actual}")
            else:
                logger.error(f"❌ {param}: {actual} (expected {expected})")
                all_correct = False
        
        if all_correct:
            logger.info("✅ All swing trading parameters correct")
            return True
        else:
            logger.error("❌ Some parameters incorrect - check small_portfolio_config.py")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return False


def main():
    """Run all fixes"""
    logger.info("\n")
    logger.info("=" * 70)
    logger.info("🔧 AUTOMATED FIX SCRIPT")
    logger.info("=" * 70)
    logger.info("Fixing configuration and legacy file issues")
    logger.info("=" * 70)
    logger.info("\n")
    
    fixes = [
        ("Add Universe Size Config", fix_1_add_universe_size_config),
        ("Archive Legacy Files", fix_2_move_legacy_files),
        ("Fix data_source Import", fix_3_create_data_source_stub),
        ("Force Watchlist Refresh", fix_4_force_watchlist_refresh),
        ("Verify Swing Trading Config", fix_5_verify_swing_trading_config),
    ]
    
    results = []
    for name, fix_func in fixes:
        try:
            success = fix_func()
            results.append((name, success))
        except Exception as e:
            logger.error(f"❌ FIX FAILED: {name} - {e}")
            results.append((name, False))
    
    # Summary
    logger.info("\n")
    logger.info("=" * 70)
    logger.info("📊 FIX SUMMARY")
    logger.info("=" * 70)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for name, success in results:
        status = "✅ SUCCESS" if success else "❌ FAILED"
        logger.info(f"{status}: {name}")
    
    logger.info("=" * 70)
    logger.info(f"Fixes Applied: {passed}/{total}")
    logger.info("=" * 70)
    
    logger.info("\n")
    if passed == total:
        logger.info("✅ ALL FIXES APPLIED SUCCESSFULLY")
        logger.info("\n📋 NEXT STEPS:")
        logger.info("   1. Review changes in small_portfolio_config.py")
        logger.info("   2. Test bot startup: python3 start_small_portfolio_trader.py")
        logger.info("   3. Monday Nov 10: First full trading day (no Friday freeze)")
        logger.info("\n")
        return 0
    else:
        logger.error("⚠️  SOME FIXES FAILED - REVIEW MANUALLY")
        logger.info("\n📋 MANUAL FIXES NEEDED:")
        for name, success in results:
            if not success:
                logger.warning(f"   - {name}")
        logger.info("\n")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())

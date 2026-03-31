#!/usr/bin/env python3
"""
Organize LiteBotX Workspace
Moves documentation, tests, and unused files to appropriate directories
"""
import os
import shutil
from pathlib import Path
from datetime import datetime

# Core files that must stay in root
KEEP_IN_ROOT = {
    # Production entry points
    'start_litebotx.py',
    'stop_litebotx.py',
    
    # Core configuration
    'config.py',
    'stock_config.py',
    
    # Core modules
    'data_loader.py',
    'data_source.py',
    'data_access.py',
    'execution_engine.py',
    'risk.py',
    'indicators.py',
    'pre_filter.py',
    'logger.py',
    
    # Active automation
    'daily_watchlist_refresh.py',
    'check_watchlist_health.py',
    
    # Package files
    '__init__.py',
    'requirements.txt',
    
    # Directories
    'traders/',
    'logs/',
    'backtest/',
    'cache/',
    'core/',
    'data/',
    'docs/',
    'market/',
    'results/',
    'scripts/',
    'test/',
    'utils/',
    'validators/',
    '__pycache__/',
    'litebotx_env/',
    
    # Service files
    'litebotx.service',
    'litebotx.code-workspace',
    
    # Data files
    'positions.json',
    
    # Shell scripts (check usage)
    'start_ubuntu.sh',
    'ubuntu_setup.sh',
    'install_linux.sh',
}

# Documentation to move to docs/
DOCS_TO_MOVE = [
    'ADAPTIVE_THRESHOLD_USAGE_GUIDE.md',
    'CRYPTO_ROADMAP.md',
    'deployment_checklist.md',
    'PHASE3B_COMPLETION_REPORT.md',
    'README_DEPLOYMENT.md',
    'README.md',
    'ROADMAP.md',
    'STOCK_DASHBOARD_PROMPT.md',
    'UBUNTU_DEPLOYMENT_README.md',
    'ZERO_BUY_PREVENTION.md',
]

# Test/diagnostic scripts to move to test/
TEST_SCRIPTS_TO_MOVE = [
    'test_adaptive_threshold_manager.py',
    'test_phase3a_comprehensive.py',
    'verify_phase3a.py',
    'quick_health_check.py',
]

# Analysis/diagnostic scripts to move to scripts/archive/
ANALYSIS_TO_ARCHIVE = [
    'quick_watchlist_gen.py',  # Used once for emergency, keep as backup
    'manual_buy_for_tomorrow.py',  # Emergency tool, archive it
]

# Old/unused scripts to DELETE
TO_DELETE = [
    'automated_momentum_trader.py',  # Old version
    'automated_momentum_trader_v2.py',  # Old version
    'backtester.py',  # If in backtest/ folder
    'backup_system.py',  # Unused
    'connect_real_trading.py',  # Redundant
    'emergency_monitor.py',  # Old monitoring
    'enhanced_momentum_strategy.py',  # Old strategy
    'enhanced_regime_detector.py',  # Superseded
    'enhanced_trading_dashboard.py',  # Old dashboard
    'gui_components.py',  # Old GUI
    'integrate_adaptive_thresholds.py',  # One-time integration
    'launch_dashboard.py',  # Old launcher
    'launch_dual_dashboards.py',  # Old launcher
    'meta_learner.py',  # Unused ML
    'ml_signal_enhancer.py',  # Unused ML
    'momentum_strategy.py',  # Old strategy
    'multi_timeframe_analyzer.py',  # Old analyzer
    'phase3_dashboard.py',  # Old phase
    'phase3a_enhanced_strategy.py',  # Old phase
    'refresh_universe.py',  # Replaced by daily_watchlist_refresh.py
    'regime_detector.py',  # Old version
    'reinforcement.py',  # Unused
    'rl_position_optimizer.py',  # Unused
    'simple_stock_launcher.py',  # Old launcher
    'smart_threshold_strategy.py',  # Old strategy
    'start_automated_trading.py',  # Replaced by start_litebotx.py
    'stock_dashboard.py',  # Old dashboard
    'strategy_manager.py',  # Old manager
    'strategy.py',  # Old strategy
    'trade_executor.py',  # Old executor
    'trader.py',  # Old trader (use traders/short_cycle_trader.py)
    'tuner.py',  # Unused
]

# Shell scripts to check
SHELL_TO_CHECK = [
    'create_backup.sh',
    'dashboard_only.sh',
    'setup_daily_refresh_cron.sh',
    'vscode_ubuntu_setup.sh',
]


def backup_before_cleanup():
    """Create backup before making changes"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = f"backup_before_cleanup_{timestamp}"
    
    print(f"📦 Creating backup: {backup_dir}/")
    os.makedirs(backup_dir, exist_ok=True)
    
    # Backup files we're about to move/delete
    files_to_backup = (
        DOCS_TO_MOVE + 
        TEST_SCRIPTS_TO_MOVE + 
        ANALYSIS_TO_ARCHIVE + 
        TO_DELETE
    )
    
    for filename in files_to_backup:
        if os.path.exists(filename):
            shutil.copy2(filename, backup_dir)
    
    print(f"✅ Backup created with {len(os.listdir(backup_dir))} files\n")
    return backup_dir


def move_docs():
    """Move documentation to docs/"""
    print("📚 Moving documentation to docs/...")
    os.makedirs('docs', exist_ok=True)
    
    moved = 0
    for doc in DOCS_TO_MOVE:
        if os.path.exists(doc):
            dest = f"docs/{doc}"
            if os.path.exists(dest):
                print(f"   ⚠️  {doc} already exists in docs/, skipping")
            else:
                shutil.move(doc, dest)
                print(f"   ✅ {doc} → docs/")
                moved += 1
    
    print(f"✅ Moved {moved} documentation files\n")


def move_tests():
    """Move test scripts to test/"""
    print("🧪 Moving tests to test/...")
    os.makedirs('test', exist_ok=True)
    
    moved = 0
    for test in TEST_SCRIPTS_TO_MOVE:
        if os.path.exists(test):
            dest = f"test/{test}"
            if os.path.exists(dest):
                print(f"   ⚠️  {test} already exists in test/, skipping")
            else:
                shutil.move(test, dest)
                print(f"   ✅ {test} → test/")
                moved += 1
    
    print(f"✅ Moved {moved} test files\n")


def archive_analysis():
    """Archive old analysis/diagnostic scripts"""
    print("📁 Archiving analysis scripts to scripts/archive/...")
    os.makedirs('scripts/archive', exist_ok=True)
    
    moved = 0
    for script in ANALYSIS_TO_ARCHIVE:
        if os.path.exists(script):
            dest = f"scripts/archive/{script}"
            if os.path.exists(dest):
                print(f"   ⚠️  {script} already exists in archive/, skipping")
            else:
                shutil.move(script, dest)
                print(f"   ✅ {script} → scripts/archive/")
                moved += 1
    
    print(f"✅ Archived {moved} analysis files\n")


def delete_unused():
    """Delete unused/old scripts"""
    print("🗑️  Deleting unused scripts...")
    
    deleted = 0
    for filename in TO_DELETE:
        if os.path.exists(filename):
            os.remove(filename)
            print(f"   ✅ Deleted {filename}")
            deleted += 1
    
    print(f"✅ Deleted {deleted} unused files\n")


def check_shell_scripts():
    """Check shell scripts for usage"""
    print("🔍 Checking shell scripts...")
    
    for script in SHELL_TO_CHECK:
        if os.path.exists(script):
            print(f"   📄 {script} - Review manually for usage")
    
    print()


def show_remaining_root_files():
    """Show what's left in root after cleanup"""
    print("📋 Remaining files in root directory:")
    
    root_files = [f for f in os.listdir('.') if os.path.isfile(f) and not f.startswith('.')]
    root_files.sort()
    
    for f in root_files:
        size_kb = os.path.getsize(f) / 1024
        print(f"   • {f:50s} ({size_kb:>8.1f} KB)")
    
    print(f"\n✅ {len(root_files)} files remain in root\n")


def main():
    """Main cleanup sequence"""
    print("=" * 70)
    print("🧹 LiteBotX Workspace Cleanup")
    print("=" * 70)
    print()
    
    # 1. Create backup
    backup_dir = backup_before_cleanup()
    
    # 2. Move docs
    move_docs()
    
    # 3. Move tests
    move_tests()
    
    # 4. Archive analysis scripts
    archive_analysis()
    
    # 5. Delete unused files
    delete_unused()
    
    # 6. Check shell scripts
    check_shell_scripts()
    
    # 7. Show what remains
    show_remaining_root_files()
    
    print("=" * 70)
    print("✅ Workspace cleanup complete!")
    print(f"📦 Backup saved to: {backup_dir}/")
    print("=" * 70)
    print()
    print("Next steps:")
    print("1. Review remaining shell scripts manually")
    print("2. Test bot startup: python3 start_litebotx.py")
    print("3. If issues, restore from backup")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Cleanup failed: {e}")
        import traceback
        traceback.print_exc()

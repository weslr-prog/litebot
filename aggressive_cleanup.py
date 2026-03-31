#!/usr/bin/env python3
"""
Aggressive Workspace Cleanup - Phase 2
Moves ALL documentation and test files out of root
"""
import os
import shutil
from pathlib import Path

def move_all_md_docs():
    """Move all .md files to docs/"""
    print("📚 Moving ALL .md files to docs/...")
    os.makedirs('docs', exist_ok=True)
    
    moved = 0
    for file in Path('.').glob('*.md'):
        if file.name in ['README.md']:  # Keep main README
            continue
        
        dest = f"docs/{file.name}"
        if not os.path.exists(dest):
            shutil.move(str(file), dest)
            print(f"   ✅ {file.name}")
            moved += 1
    
    print(f"✅ Moved {moved} documentation files\n")


def move_all_test_files():
    """Move ALL test/debug/analyze/check scripts to test/"""
    print("🧪 Moving ALL test/debug/analyze scripts to test/...")
    os.makedirs('test', exist_ok=True)
    
    test_prefixes = [
        'test_', 'debug_', 'analyze_', 'check_', 
        'validate_', 'verify_', 'diagnostic_',
        'comprehensive_', 'investigate_', 'fix_',
        'critical_issue_', 'simulate_', 'manual_test',
    ]
    
    moved = 0
    for file in Path('.').glob('*.py'):
        filename = file.name
        
        # Skip core files
        if filename in [
            'start_litebotx.py', 'stop_litebotx.py',
            'config.py', 'stock_config.py',
            'data_loader.py', 'execution_engine.py', 
            'risk.py', 'indicators.py', 'pre_filter.py', 
            'logger.py', 'daily_watchlist_refresh.py',
            'organize_workspace.py', 'aggressive_cleanup.py',
            '__init__.py', 'module_interface.py',
        ]:
            continue
        
        # Move if matches test pattern
        if any(filename.startswith(prefix) for prefix in test_prefixes):
            dest = f"test/{filename}"
            if not os.path.exists(dest):
                shutil.move(str(file), dest)
                print(f"   ✅ {filename}")
                moved += 1
    
    print(f"✅ Moved {moved} test files\n")


def move_old_scripts():
    """Move old analysis/implementation scripts to scripts/archive/"""
    print("📁 Archiving old implementation/analysis scripts...")
    os.makedirs('scripts/archive', exist_ok=True)
    
    archive_patterns = [
        'phase1_', 'implement_', 'integration_',
        'enhancement_', 'optimization_', 'regime_',
        'parameter_', 'scaling_', 'strategy_',
        'signal_', 'intraday_', 'dynamic_',
        'enhanced_', 'morning_', 'evening_',
        'monday_', 'thursday_', 'todays_',
        'nightly_', 'weekly_', 'daily_performance',
        'pre_flight', 'pre_implementation',
        'pattern_', 'gap_', 'rs_sector',
        'free_data_', 'risk_adjusted_',
        'short_cycle_safety', 'emergency_',
        'litebotx_launcher', 'live_',
        'final_', 'honest_', 'simple_',
        'sprint1_', 'buy_test_', 'execute_',
        'force_', 'sync_', 'connect_',
        'continuous_', 'manual_', 'quick_',
        'create_backup_', 'show_',
        'finra_', 'strategic_',
        'weekend_', 'walkforward_',
        'trade_log_', 'timezone_',
        'backtest_d1_', 'implementation_safety',
    ]
    
    moved = 0
    for file in Path('.').glob('*.py'):
        filename = file.name
        
        # Skip core files
        if filename in [
            'start_litebotx.py', 'stop_litebotx.py',
            'config.py', 'stock_config.py',
            'data_loader.py', 'execution_engine.py',
            'risk.py', 'indicators.py', 'pre_filter.py',
            'logger.py', 'daily_watchlist_refresh.py',
            'organize_workspace.py', 'aggressive_cleanup.py',
            '__init__.py', 'module_interface.py',
            'adaptive_threshold_manager.py',
            'indicator_cache.py', 'indicator_calculator.py',
            'signal_confidence.py', 'signal_generator.py',
            'stock_api.py', 'stock_metrics.py',
            'data_access.py', 'data_source.py',
        ]:
            continue
        
        # Move if matches archive pattern
        if any(filename.startswith(prefix) for prefix in archive_patterns):
            dest = f"scripts/archive/{filename}"
            if not os.path.exists(dest):
                shutil.move(str(file), dest)
                print(f"   ✅ {filename}")
                moved += 1
    
    print(f"✅ Archived {moved} scripts\n")


def move_log_files():
    """Move .log files to logs/"""
    print("📄 Moving log files to logs/...")
    os.makedirs('logs', exist_ok=True)
    
    moved = 0
    for file in Path('.').glob('*.log'):
        dest = f"logs/{file.name}"
        if not os.path.exists(dest):
            shutil.move(str(file), dest)
            print(f"   ✅ {file.name}")
            moved += 1
    
    print(f"✅ Moved {moved} log files\n")


def move_json_backups():
    """Move JSON backup files to backups/"""
    print("💾 Moving JSON backups...")
    os.makedirs('backups', exist_ok=True)
    
    moved = 0
    for file in Path('.').glob('*.json'):
        filename = file.name
        
        # Keep active files
        if filename in ['positions.json', 'risk_override.json', 
                       'performance_history.json', 'optimization_log.json']:
            continue
        
        # Move backups and old files
        if ('backup' in filename.lower() or 
            'baseline' in filename.lower() or
            '20250' in filename or '20251' in filename):
            dest = f"backups/{filename}"
            if not os.path.exists(dest):
                shutil.move(str(file), dest)
                print(f"   ✅ {filename}")
                moved += 1
    
    print(f"✅ Moved {moved} backup files\n")


def move_shell_scripts():
    """Move shell scripts to scripts/"""
    print("📜 Moving shell scripts...")
    os.makedirs('scripts', exist_ok=True)
    
    moved = 0
    for file in Path('.').glob('*.sh'):
        dest = f"scripts/{file.name}"
        if not os.path.exists(dest):
            shutil.move(str(file), dest)
            print(f"   ✅ {file.name}")
            moved += 1
    
    print(f"✅ Moved {moved} shell scripts\n")


def show_remaining():
    """Show what's left"""
    print("=" * 70)
    print("📋 Remaining files in root:")
    print("=" * 70)
    
    root_files = sorted([f for f in os.listdir('.') if os.path.isfile(f) and not f.startswith('.')])
    
    print("\n🐍 Python files:")
    py_files = [f for f in root_files if f.endswith('.py')]
    for f in py_files:
        print(f"   • {f}")
    
    print("\n📄 Data files:")
    data_files = [f for f in root_files if f.endswith(('.json', '.csv', '.txt'))]
    for f in data_files:
        print(f"   • {f}")
    
    print("\n📦 Archives:")
    archive_files = [f for f in root_files if f.endswith(('.tar.gz', '.zip'))]
    for f in archive_files:
        print(f"   • {f}")
    
    print("\n❓ Other:")
    other_files = [f for f in root_files if not any(f.endswith(ext) for ext in ['.py', '.json', '.csv', '.txt', '.tar.gz', '.zip', '.md', '.log', '.sh'])]
    for f in other_files:
        print(f"   • {f}")
    
    print(f"\n✅ Total: {len(root_files)} files in root\n")


def main():
    print("=" * 70)
    print("🧹 AGGRESSIVE Workspace Cleanup - Phase 2")
    print("=" * 70)
    print()
    
    move_all_md_docs()
    move_all_test_files()
    move_old_scripts()
    move_log_files()
    move_json_backups()
    move_shell_scripts()
    
    show_remaining()
    
    print("=" * 70)
    print("✅ Aggressive cleanup complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()

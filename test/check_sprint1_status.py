#!/usr/bin/env python3
"""
Sprint 1 System Status Checker
Quick validation of all Sprint 1 components
"""

import os
import sys
import importlib.util
from datetime import datetime

def check_component(name, path):
    """Check if a component can be imported successfully"""
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return True, "✅ OK"
    except Exception as e:
        return False, f"❌ ERROR: {str(e)[:50]}..."

def main():
    """Check Sprint 1 system status"""
    print("🔍 Sprint 1 System Status Check")
    print("=" * 40)
    print(f"Timestamp: {datetime.now()}")
    print()
    
    components = [
        ("Config", "config.py"),
        ("Minimal Test", "sprint1_minimal_test.py"),
        ("Real Data Integration", "sprint1_real_data_integration_clean.py"),
        ("ML Training", "sprint1_ml_training.py")
    ]
    
    all_good = True
    
    for name, path in components:
        if os.path.exists(path):
            success, message = check_component(name, path)
            print(f"{name:<25}: {message}")
            if not success:
                all_good = False
        else:
            print(f"{name:<25}: ❌ FILE NOT FOUND")
            all_good = False
    
    print()
    print("📊 Required Packages:")
    
    packages = ['pandas', 'numpy', 'yfinance', 'sklearn', 'xgboost']
    for pkg in packages:
        try:
            __import__(pkg)
            print(f"{pkg:<15}: ✅ Available")
        except ImportError:
            print(f"{pkg:<15}: ❌ Missing")
            all_good = False
    
    print()
    if all_good:
        print("🎉 Sprint 1 System Status: ALL SYSTEMS OPERATIONAL")
        print("✅ Ready for paper testing")
        print()
        print("To start paper testing:")
        print("  ./launch_paper_testing.sh")
    else:
        print("⚠️  Sprint 1 System Status: ISSUES DETECTED")
        print("❌ Fix issues before paper testing")
    
    print()
    print("📋 System Configuration:")
    try:
        from config import Sprint1Config
        config = Sprint1Config()
        print(f"Portfolio Size: ${config.portfolio_size:,.0f}")
        print(f"Risk Per Trade: {config.risk_per_trade:.1%}")
        print(f"Max Positions: {config.max_positions}")
        print(f"Test Symbols: {', '.join(config.test_symbols)}")
    except Exception as e:
        print(f"❌ Config Error: {e}")

if __name__ == "__main__":
    main()

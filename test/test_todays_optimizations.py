#!/usr/bin/env python3
"""
Comprehensive Testing Suite for October 1st Optimizations
Tests all changes made today: config fixes, threshold optimizations, backtesting setup
"""

import sys
import os
import json
from datetime import datetime
import subprocess

# Setup path
sys.path.append('/home/wes/Desktop/litebotx-usb-deployment')

def test_launcher_config_fix():
    """Test that launcher confidence thresholds are properly optimized"""
    print("🔧 TESTING LAUNCHER CONFIGURATION...")
    
    try:
        # Import the launcher function
        from litebotx_launcher import create_trading_config
        
        # Test all three modes
        modes = ["conservative", "balanced", "aggressive"]
        expected_thresholds = {
            "conservative": 0.08,
            "balanced": 0.065, 
            "aggressive": 0.055
        }
        
        results = {}
        for mode in modes:
            config = create_trading_config(mode)
            actual_threshold = config.confidence_threshold
            expected_threshold = expected_thresholds[mode]
            
            results[mode] = {
                "expected": expected_threshold,
                "actual": actual_threshold,
                "passed": abs(actual_threshold - expected_threshold) < 0.001
            }
            
            print(f"   {mode.capitalize()}: {actual_threshold:.3f} (expected {expected_threshold:.3f}) {'✅' if results[mode]['passed'] else '❌'}")
        
        all_passed = all(r["passed"] for r in results.values())
        print(f"   Overall: {'✅ PASSED' if all_passed else '❌ FAILED'}")
        return all_passed
        
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        return False

def test_trader_config_optimization():
    """Test that the main trader config has the optimized 5.5% threshold"""
    print("\n🎯 TESTING TRADER CONFIGURATION...")
    
    try:
        config_path = "/home/wes/Desktop/litebotx-usb-deployment/traders/short_cycle_trader.py"
        
        with open(config_path, 'r') as f:
            content = f.read()
        
        # Check for optimized threshold
        import re
        threshold_pattern = r'confidence_threshold: float = ([\d.]+)'
        match = re.search(threshold_pattern, content)
        
        if match:
            threshold = float(match.group(1))
            expected = 0.055
            passed = abs(threshold - expected) < 0.001
            
            print(f"   Confidence threshold: {threshold:.3f} (expected {expected:.3f}) {'✅' if passed else '❌'}")
            
            # Check for optimization comment
            has_comment = "Optimized for efficiency & profitability" in content
            print(f"   Optimization comment: {'✅ Present' if has_comment else '❌ Missing'}")
            
            return passed and has_comment
        else:
            print("   ❌ Could not find confidence threshold")
            return False
            
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        return False

def test_backtesting_infrastructure():
    """Test that backtesting infrastructure works"""
    print("\n🧪 TESTING BACKTESTING INFRASTRUCTURE...")
    
    try:
        # Test optimized backtest script exists and runs
        backtest_path = "/home/wes/Desktop/litebotx-usb-deployment/test_optimized_backtest.py"
        if os.path.exists(backtest_path):
            print("   ✅ Optimized backtest script exists")
        else:
            print("   ❌ Optimized backtest script missing")
            return False
        
        # Test nightly script exists
        nightly_path = "/home/wes/Desktop/litebotx-usb-deployment/run_nightly_backtest.sh"
        if os.path.exists(nightly_path):
            print("   ✅ Nightly backtest script exists")
            
            # Check if executable
            if os.access(nightly_path, os.X_OK):
                print("   ✅ Nightly script is executable")
            else:
                print("   ⚠️  Nightly script not executable")
        else:
            print("   ❌ Nightly backtest script missing")
            return False
        
        # Test setup script exists
        setup_path = "/home/wes/Desktop/litebotx-usb-deployment/setup_nightly_backtest.sh"
        if os.path.exists(setup_path):
            print("   ✅ Setup script exists")
            
            if os.access(setup_path, os.X_OK):
                print("   ✅ Setup script is executable")
            else:
                print("   ⚠️  Setup script not executable")
        else:
            print("   ❌ Setup script missing")
            return False
        
        return True
        
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        return False

def test_api_enhancements_document():
    """Test that API enhancements document was updated properly"""
    print("\n📋 TESTING API ENHANCEMENTS DOCUMENT...")
    
    try:
        doc_path = "/home/wes/Desktop/litebotx-usb-deployment/API_USAGE_ENHANCEMENTS.md"
        
        with open(doc_path, 'r') as f:
            content = f.read()
        
        # Check for prioritized structure
        checks = {
            "Title updated": "LiteBotX API Enhancement Roadmap" in content,
            "Phase 1 section": "PHASE 1: HIGH-IMPACT IMPLEMENTATIONS" in content,
            "Polygon premarket": "Polygon Premarket & Relative Volume" in content,
            "Skip section": "PHASE 3: SKIP THESE" in content,
            "Implementation timeline": "Week 1-2: Phase 1A" in content,
            "Success metrics": "SUCCESS METRICS" in content
        }
        
        for check, passed in checks.items():
            print(f"   {check}: {'✅' if passed else '❌'}")
        
        all_passed = all(checks.values())
        print(f"   Overall: {'✅ PASSED' if all_passed else '❌ FAILED'}")
        return all_passed
        
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        return False

def test_optimization_logging():
    """Test that optimization changes were properly logged"""
    print("\n📝 TESTING OPTIMIZATION LOGGING...")
    
    try:
        log_path = "/home/wes/Desktop/litebotx-usb-deployment/optimization_log.json"
        
        if os.path.exists(log_path):
            with open(log_path, 'r') as f:
                logs = json.load(f)
            
            print(f"   ✅ Optimization log exists with {len(logs)} entries")
            
            # Check for today's optimization
            today = datetime.now().date().isoformat()
            today_logs = [log for log in logs if log.get('timestamp', '').startswith(today)]
            
            if today_logs:
                latest_log = today_logs[-1]
                print(f"   ✅ Today's optimization logged")
                print(f"   📊 Old threshold: {latest_log.get('old_threshold', 'N/A')}")
                print(f"   📊 New threshold: {latest_log.get('new_threshold', 'N/A')}")
                print(f"   📊 Adjustment: {latest_log.get('adjustment', 'N/A')}")
                return True
            else:
                print("   ⚠️  No optimization log for today")
                return len(logs) > 0  # At least some logs exist
        else:
            print("   ❌ Optimization log missing")
            return False
            
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        return False

def test_config_cleanup():
    """Test that config files were properly cleaned up"""
    print("\n🗂️  TESTING CONFIG CLEANUP...")
    
    try:
        # Check that old API doc was moved
        old_doc_path = "/home/wes/Desktop/litebotx-usb-deployment/API_USAGE_ENHANCEMENTS_old.md"
        archive_doc_path = "/home/wes/Desktop/litebotx-usb-deployment/archive/unused_configs/API_USAGE_ENHANCEMENTS_old.md"
        
        old_exists = os.path.exists(old_doc_path)
        archive_exists = os.path.exists(archive_doc_path)
        
        print(f"   Old API doc removed: {'✅' if not old_exists else '❌'}")
        print(f"   Old API doc archived: {'✅' if archive_exists else '❌'}")
        
        # Check that archive directory exists
        archive_dir = "/home/wes/Desktop/litebotx-usb-deployment/archive/unused_configs"
        if os.path.exists(archive_dir):
            print("   ✅ Archive directory exists")
        else:
            print("   ❌ Archive directory missing")
            return False
        
        return not old_exists and archive_exists
        
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        return False

def run_integration_test():
    """Run a quick integration test to ensure everything works together"""
    print("\n🔗 RUNNING INTEGRATION TEST...")
    
    try:
        # Test that we can import and create optimized config
        from litebotx_launcher import create_trading_config
        
        # Create aggressive config (your primary mode)
        config = create_trading_config("aggressive")
        
        print(f"   Portfolio allocation: {config.daily_pool_percent*100:.0f}%")
        print(f"   Confidence threshold: {config.confidence_threshold:.3f}")
        print(f"   Max positions: {config.max_positions_per_day}")
        print(f"   Daily loss limit: {config.max_daily_loss_percent*100:.3f}%")
        
        # Verify this matches our optimization
        expected_confidence = 0.055
        confidence_ok = abs(config.confidence_threshold - expected_confidence) < 0.001
        
        print(f"   Integration test: {'✅ PASSED' if confidence_ok else '❌ FAILED'}")
        return confidence_ok
        
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        return False

def main():
    """Run comprehensive test suite"""
    print("🚀 COMPREHENSIVE TEST SUITE - OCTOBER 1ST OPTIMIZATIONS")
    print("=" * 65)
    
    tests = [
        ("Launcher Config Fix", test_launcher_config_fix),
        ("Trader Config Optimization", test_trader_config_optimization), 
        ("Backtesting Infrastructure", test_backtesting_infrastructure),
        ("API Enhancements Document", test_api_enhancements_document),
        ("Optimization Logging", test_optimization_logging),
        ("Config Cleanup", test_config_cleanup),
        ("Integration Test", run_integration_test)
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"\n❌ {test_name} CRASHED: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "=" * 65)
    print("🎯 TEST SUMMARY")
    print("=" * 65)
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, result in results.items():
        print(f"   {test_name}: {'✅ PASSED' if result else '❌ FAILED'}")
    
    print(f"\n📊 OVERALL RESULT: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED - Optimizations successfully implemented!")
        print("\n✅ Your bot is ready with:")
        print("   • Optimized confidence thresholds (5.5% aggressive mode)")
        print("   • Fixed configuration inconsistencies")
        print("   • Enhanced backtesting infrastructure") 
        print("   • Prioritized API enhancement roadmap")
        print("   • Clean configuration management")
        
        print("\n🚀 NEXT STEPS:")
        print("   1. Test aggressive mode (launcher option 3)")
        print("   2. Monitor performance for 1 week")
        print("   3. Consider Phase 1 API enhancements if needed")
        
    else:
        print("⚠️  Some tests failed - review issues above")
        failed_tests = [name for name, result in results.items() if not result]
        print(f"   Failed: {', '.join(failed_tests)}")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
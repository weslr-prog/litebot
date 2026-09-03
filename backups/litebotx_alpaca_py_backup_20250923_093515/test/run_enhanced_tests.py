#!/usr/bin/env python3
"""
Test runner for Enhanced Multi-Sector Momentum Trading System
Runs comprehensive unit tests and integration tests
"""

import unittest
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def run_all_enhanced_tests():
    """Run all tests for the enhanced trading system"""
    print("🧪 Running Enhanced Multi-Sector Momentum Trading Tests")
    print("=" * 60)
    
    # Discover and load all test modules
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Test modules to run
    test_modules = [
        'test_sector_analyzer',
        'test_enhanced_momentum_strategy', 
        'test_enhanced_trading_integration'
    ]
    
    # Load each test module
    for module_name in test_modules:
        try:
            print(f"📋 Loading tests from {module_name}...")
            module_suite = loader.loadTestsFromName(module_name)
            suite.addTest(module_suite)
        except Exception as e:
            print(f"⚠️  Warning: Could not load {module_name}: {e}")
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(
        verbosity=2,
        descriptions=True,
        failfast=False
    )
    
    print(f"\n🚀 Running {suite.countTestCases()} tests...")
    print("-" * 60)
    
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 Test Results Summary:")
    print(f"   ✅ Tests run: {result.testsRun}")
    print(f"   ❌ Failures: {len(result.failures)}")
    print(f"   💥 Errors: {len(result.errors)}")
    print(f"   ⏭️  Skipped: {len(result.skipped) if hasattr(result, 'skipped') else 0}")
    
    if result.failures:
        print(f"\n💔 Failed Tests:")
        for test, traceback in result.failures:
            print(f"   - {test}")
    
    if result.errors:
        print(f"\n💥 Error Tests:")
        for test, traceback in result.errors:
            print(f"   - {test}")
    
    # Overall result
    if result.wasSuccessful():
        print(f"\n🎉 All tests passed! Enhanced trading system is ready.")
        return True
    else:
        print(f"\n🚨 Some tests failed. Please review and fix issues.")
        return False

def run_specific_test(test_name):
    """Run a specific test module"""
    print(f"🧪 Running specific test: {test_name}")
    print("-" * 40)
    
    loader = unittest.TestLoader()
    runner = unittest.TextTestRunner(verbosity=2)
    
    try:
        suite = loader.loadTestsFromName(test_name)
        result = runner.run(suite)
        return result.wasSuccessful()
    except Exception as e:
        print(f"❌ Error running {test_name}: {e}")
        return False

if __name__ == '__main__':
    if len(sys.argv) > 1:
        # Run specific test
        test_name = sys.argv[1]
        success = run_specific_test(test_name)
    else:
        # Run all tests
        success = run_all_enhanced_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

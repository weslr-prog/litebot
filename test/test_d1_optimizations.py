#!/usr/bin/env python3
"""
Comprehensive Test Suite for D+1 Optimizations
Tests all three new features before Monday morning trading
"""

import sys
import logging
from datetime import datetime, timedelta
from typing import List, Dict

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# Test results tracking
test_results = {
    'passed': [],
    'failed': [],
    'warnings': []
}

def log_test_result(test_name: str, passed: bool, message: str = ""):
    """Log and track test results"""
    if passed:
        logger.info(f"✅ {test_name}: PASSED {message}")
        test_results['passed'].append(test_name)
    else:
        logger.error(f"❌ {test_name}: FAILED {message}")
        test_results['failed'].append(test_name)

def log_warning(test_name: str, message: str):
    """Log warning"""
    logger.warning(f"⚠️ {test_name}: {message}")
    test_results['warnings'].append(f"{test_name}: {message}")

print("\n" + "="*80)
print("🧪 COMPREHENSIVE D+1 OPTIMIZATION TEST SUITE")
print("="*80 + "\n")

# ============================================================================
# TEST 1: Import Tests
# ============================================================================
print("📦 TEST SUITE 1: Module Imports and Initialization")
print("-" * 80)

try:
    from morning_gap_scanner import MorningGapScanner
    scanner = MorningGapScanner()
    log_test_result("1.1 MorningGapScanner import", True)
except Exception as e:
    log_test_result("1.1 MorningGapScanner import", False, str(e))

try:
    from pattern_recognizer import (
        PatternRecognizer, 
        PatternTracker, 
        StockPattern
    )
    recognizer = PatternRecognizer()
    tracker = PatternTracker()
    
    # Check all patterns exist
    patterns = [p.value for p in StockPattern]
    expected_patterns = [
        'morning_gapper', 'momentum_runner', 'late_bloomer', 
        'range_bound', 'reversal', 'unknown'
    ]
    
    if all(p in patterns for p in expected_patterns):
        log_test_result("1.2 PatternRecognizer import", True, f"All {len(patterns)} patterns available")
    else:
        log_test_result("1.2 PatternRecognizer import", False, "Missing expected patterns")
        
except Exception as e:
    log_test_result("1.2 PatternRecognizer import", False, str(e))

try:
    sys.path.insert(0, 'traders')
    from short_cycle_trader import ShortCycleConfig, ShortCyclePosition
    config = ShortCycleConfig()
    log_test_result("1.3 Short cycle trader integration", True)
except Exception as e:
    log_test_result("1.3 Short cycle trader integration", False, str(e))

# ============================================================================
# TEST 2: Morning Gap Scanner Functionality
# ============================================================================
print("\n📊 TEST SUITE 2: Morning Gap Scanner Functionality")
print("-" * 80)

try:
    # Test gap quality assessment
    test_cases = [
        (0.02, 150, 147, 1000, "EXCELLENT"),   # 2% gap
        (0.015, 150, 147.8, 1000, "EXCELLENT"),  # 1.5% gap
        (0.012, 150, 148.2, 1000, "GOOD"),       # 1.2% gap
        (0.035, 150, 145, 1000, "GOOD"),       # 3.5% gap
        (0.008, 150, 148.8, 1000, "MODERATE"),   # 0.8% gap
        (0.048, 150, 142.8, 1000, "MODERATE"),   # 4.8% gap
        (0.003, 150, 149.55, 1000, "POOR"),       # 0.3% gap
        (0.06, 150, 141, 1000, "POOR"),        # 6% gap
    ]
    
    all_correct = True
    for gap_pct, current, prev_close, volume, expected_quality in test_cases:
        quality = scanner._assess_gap_quality(gap_pct, current, prev_close, volume)
        if quality != expected_quality:
            all_correct = False
            log_warning("2.1 Gap quality assessment", 
                       f"Gap {gap_pct:.1%} rated {quality}, expected {expected_quality}")
    
    if all_correct:
        log_test_result("2.1 Gap quality assessment", True, "All 8 test cases correct")
    else:
        log_test_result("2.1 Gap quality assessment", False, "Some ratings incorrect")
        
except Exception as e:
    log_test_result("2.1 Gap quality assessment", False, str(e))

try:
    # Test opportunity scoring - using gap_analysis format
    test_gap_analysis = {
        'AAPL': {
            'gap_pct': 0.025,
            'gap_quality': 'EXCELLENT',
            'gap_direction': 'UP',
            'current_price': 153.75,
            'prev_close': 150.0
        },
        'MSFT': {
            'gap_pct': 0.012,
            'gap_quality': 'GOOD',
            'gap_direction': 'UP',
            'current_price': 303.6,
            'prev_close': 300.0
        },
        'GOOGL': {
            'gap_pct': 0.008,
            'gap_quality': 'MODERATE',
            'gap_direction': 'DOWN',
            'current_price': 141.12,
            'prev_close': 142.25
        }
    }
    
    # Test filtering returns symbols in score order
    selected = scanner.filter_tradeable_gaps(test_gap_analysis, max_selections=3)
    
    # AAPL (EXCELLENT) should be first, GOOGL (MODERATE + DOWN) should be last
    if len(selected) == 3 and selected[0] == 'AAPL':
        log_test_result("2.2 Gap opportunity scoring", True, 
                       f"Correct ordering: {selected}")
    else:
        log_test_result("2.2 Gap opportunity scoring", False,
                       f"Incorrect ordering: {selected}")
        
except Exception as e:
    log_test_result("2.2 Gap opportunity scoring", False, str(e))

try:
    # Test filtering logic - using proper gap_analysis format
    test_gap_analysis = {
        'AAPL': {'gap_pct': 0.025, 'gap_quality': 'EXCELLENT', 'gap_direction': 'UP', 
                 'current_price': 153.75, 'prev_close': 150},
        'MSFT': {'gap_pct': 0.012, 'gap_quality': 'GOOD', 'gap_direction': 'UP',
                 'current_price': 303.6, 'prev_close': 300},
        'GOOGL': {'gap_pct': 0.008, 'gap_quality': 'MODERATE', 'gap_direction': 'UP',
                  'current_price': 141.12, 'prev_close': 140},
        'TSLA': {'gap_pct': 0.003, 'gap_quality': 'POOR', 'gap_direction': 'UP',
                 'current_price': 250.75, 'prev_close': 250},
        'NVDA': {'gap_pct': 0.018, 'gap_quality': 'EXCELLENT', 'gap_direction': 'UP',
                 'current_price': 458.1, 'prev_close': 450},
    }
    
    filtered = scanner.filter_tradeable_gaps(test_gap_analysis, max_selections=3)
    
    # Should return top 3 gaps (excluding POOR quality)
    # Should be AAPL, NVDA, MSFT based on scores
    if len(filtered) == 3 and 'TSLA' not in filtered:
        log_test_result("2.3 Gap filtering", True, f"Returned {len(filtered)} quality gaps: {filtered}")
    else:
        log_test_result("2.3 Gap filtering", False, 
                       f"Expected 3 gaps without POOR quality, got {filtered}")
        
except Exception as e:
    log_test_result("2.3 Gap filtering", False, str(e))

# ============================================================================
# TEST 3: Pattern Recognition Functionality
# ============================================================================
print("\n🧠 TEST SUITE 3: Pattern Recognition Functionality")
print("-" * 80)

try:
    # Test pattern identification - MORNING_GAPPER
    pattern = recognizer.identify_pattern(
        current_price=101.5,
        entry_price=100.0,
        gap_at_open=0.02,  # 2% gap
        minutes_held=45,
        price_history=[100.0, 101.8, 101.6, 101.5]  # Fading
    )
    
    if pattern == StockPattern.MORNING_GAPPER:
        log_test_result("3.1 MORNING_GAPPER detection", True)
    else:
        log_test_result("3.1 MORNING_GAPPER detection", False, 
                       f"Expected MORNING_GAPPER, got {pattern.value}")
        
except Exception as e:
    log_test_result("3.1 MORNING_GAPPER detection", False, str(e))

try:
    # Test pattern identification - MOMENTUM_RUNNER
    pattern = recognizer.identify_pattern(
        current_price=101.0,
        entry_price=100.0,
        gap_at_open=None,  # No gap
        minutes_held=60,
        price_history=[100.0, 100.3, 100.5, 100.7, 100.9, 101.0]  # Steady climb
    )
    
    if pattern == StockPattern.MOMENTUM_RUNNER:
        log_test_result("3.2 MOMENTUM_RUNNER detection", True)
    else:
        log_test_result("3.2 MOMENTUM_RUNNER detection", False,
                       f"Expected MOMENTUM_RUNNER, got {pattern.value}")
        
except Exception as e:
    log_test_result("3.2 MOMENTUM_RUNNER detection", False, str(e))

try:
    # Test pattern identification - LATE_BLOOMER
    pattern = recognizer.identify_pattern(
        current_price=100.5,
        entry_price=100.0,
        gap_at_open=None,
        minutes_held=90,  # 90 minutes held
        price_history=[100.0, 100.1, 100.2, 100.3, 100.4, 100.5]  # Slow climb
    )
    
    if pattern == StockPattern.LATE_BLOOMER:
        log_test_result("3.3 LATE_BLOOMER detection", True)
    else:
        log_test_result("3.3 LATE_BLOOMER detection", False,
                       f"Expected LATE_BLOOMER, got {pattern.value}")
        
except Exception as e:
    log_test_result("3.3 LATE_BLOOMER detection", False, str(e))

try:
    # Test pattern identification - RANGE_BOUND
    pattern = recognizer.identify_pattern(
        current_price=100.3,
        entry_price=100.0,
        gap_at_open=None,
        minutes_held=60,
        price_history=[100.0, 100.2, 100.1, 100.3, 100.2, 100.3]  # Choppy
    )
    
    if pattern == StockPattern.RANGE_BOUND:
        log_test_result("3.4 RANGE_BOUND detection", True)
    else:
        log_test_result("3.4 RANGE_BOUND detection", False,
                       f"Expected RANGE_BOUND, got {pattern.value}")
        
except Exception as e:
    log_test_result("3.4 RANGE_BOUND detection", False, str(e))

try:
    # Test pattern identification - REVERSAL
    pattern = recognizer.identify_pattern(
        current_price=99.3,
        entry_price=100.0,
        gap_at_open=0.02,  # Gapped up 2%
        minutes_held=30,
        price_history=[100.0, 99.8, 99.5, 99.3]  # But going down = reversal
    )
    
    if pattern == StockPattern.REVERSAL:
        log_test_result("3.5 REVERSAL detection", True)
    else:
        log_test_result("3.5 REVERSAL detection", False,
                       f"Expected REVERSAL, got {pattern.value}")
        
except Exception as e:
    log_test_result("3.5 REVERSAL detection", False, str(e))

# ============================================================================
# TEST 4: Exit Timing Logic
# ============================================================================
print("\n⏰ TEST SUITE 4: Dynamic Exit Timing")
print("-" * 80)

try:
    # Test MORNING_GAPPER exit timing (should exit 10-11 AM)
    test_time = datetime.now().replace(hour=10, minute=30)  # 10:30 AM
    should_exit, reason = recognizer.get_optimal_exit_time(
        pattern=StockPattern.MORNING_GAPPER,
        current_time=test_time,
        pnl_pct=0.008  # 0.8% profit
    )
    
    if should_exit and "GAPPER" in reason:
        log_test_result("4.1 MORNING_GAPPER exit timing", True, 
                       f"Exits at 10:30 AM: {reason}")
    else:
        log_test_result("4.1 MORNING_GAPPER exit timing", False,
                       f"Should exit but got: {should_exit}, {reason}")
        
except Exception as e:
    log_test_result("4.1 MORNING_GAPPER exit timing", False, str(e))

try:
    # Test MOMENTUM_RUNNER exit timing (should exit 11:30 AM-1:30 PM)
    test_time = datetime.now().replace(hour=12, minute=0)  # 12:00 PM
    should_exit, reason = recognizer.get_optimal_exit_time(
        pattern=StockPattern.MOMENTUM_RUNNER,
        current_time=test_time,
        pnl_pct=0.012  # 1.2% profit
    )
    
    if should_exit and "MOMENTUM" in reason:
        log_test_result("4.2 MOMENTUM_RUNNER exit timing", True,
                       f"Exits at 12:00 PM: {reason}")
    else:
        log_test_result("4.2 MOMENTUM_RUNNER exit timing", False,
                       f"Should exit but got: {should_exit}, {reason}")
        
except Exception as e:
    log_test_result("4.2 MOMENTUM_RUNNER exit timing", False, str(e))

try:
    # Test LATE_BLOOMER exit timing (should exit 2-3:30 PM)
    test_time = datetime.now().replace(hour=14, minute=30)  # 2:30 PM
    should_exit, reason = recognizer.get_optimal_exit_time(
        pattern=StockPattern.LATE_BLOOMER,
        current_time=test_time,
        pnl_pct=0.006  # 0.6% profit
    )
    
    if should_exit and "BLOOMER" in reason:
        log_test_result("4.3 LATE_BLOOMER exit timing", True,
                       f"Exits at 2:30 PM: {reason}")
    else:
        log_test_result("4.3 LATE_BLOOMER exit timing", False,
                       f"Should exit but got: {should_exit}, {reason}")
        
except Exception as e:
    log_test_result("4.3 LATE_BLOOMER exit timing", False, str(e))

try:
    # Test that patterns DON'T exit at wrong times
    test_time = datetime.now().replace(hour=9, minute=30)  # 9:30 AM (too early)
    should_exit, reason = recognizer.get_optimal_exit_time(
        pattern=StockPattern.MOMENTUM_RUNNER,
        current_time=test_time,
        pnl_pct=0.005  # Small profit
    )
    
    if not should_exit:
        log_test_result("4.4 Pattern timing boundaries", True,
                       "Correctly holds MOMENTUM_RUNNER at 9:30 AM")
    else:
        log_test_result("4.4 Pattern timing boundaries", False,
                       f"Should NOT exit at 9:30 AM but got: {reason}")
        
except Exception as e:
    log_test_result("4.4 Pattern timing boundaries", False, str(e))

# ============================================================================
# TEST 5: Pattern Tracking
# ============================================================================
print("\n📈 TEST SUITE 5: Pattern Tracking Over Time")
print("-" * 80)

try:
    # Test position pattern tracking
    test_tracker = PatternTracker()
    
    # Update pattern multiple times
    pattern1 = test_tracker.update_position_pattern(
        symbol='AAPL',
        current_price=101.0,
        entry_price=100.0,
        gap_at_open=0.015,
        minutes_held=15
    )
    
    pattern2 = test_tracker.update_position_pattern(
        symbol='AAPL',
        current_price=101.3,
        entry_price=100.0,
        gap_at_open=0.015,
        minutes_held=30
    )
    
    # Get stored pattern
    stored_pattern = test_tracker.get_pattern('AAPL')
    
    if stored_pattern is not None:
        log_test_result("5.1 Pattern tracking", True,
                       f"Pattern tracked: {stored_pattern.value}")
    else:
        log_test_result("5.1 Pattern tracking", False,
                       "Pattern not stored")
        
except Exception as e:
    log_test_result("5.1 Pattern tracking", False, str(e))

try:
    # Test pattern history
    test_tracker = PatternTracker()
    
    # Add multiple price points
    for i, price in enumerate([100.0, 100.5, 101.0, 101.5, 102.0]):
        test_tracker.update_position_pattern(
            symbol='MSFT',
            current_price=price,
            entry_price=100.0,
            gap_at_open=None,
            minutes_held=i*15
        )
    
    # Check history exists
    if 'MSFT' in test_tracker.pattern_history:
        history_length = len(test_tracker.pattern_history['MSFT'])
        if history_length == 5:
            log_test_result("5.2 Pattern history tracking", True,
                           f"Tracked {history_length} price points")
        else:
            log_test_result("5.2 Pattern history tracking", False,
                           f"Expected 5 points, got {history_length}")
    else:
        log_test_result("5.2 Pattern history tracking", False,
                       "No history stored")
        
except Exception as e:
    log_test_result("5.2 Pattern history tracking", False, str(e))

try:
    # Test clearing positions
    test_tracker = PatternTracker()
    test_tracker.update_position_pattern(
        symbol='GOOGL',
        current_price=141.0,
        entry_price=140.0,
        gap_at_open=None,
        minutes_held=30
    )
    
    test_tracker.clear_position('GOOGL')
    
    pattern = test_tracker.get_pattern('GOOGL')
    if pattern is None:
        log_test_result("5.3 Pattern cleanup", True,
                       "Position cleared successfully")
    else:
        log_test_result("5.3 Pattern cleanup", False,
                       "Position not cleared")
        
except Exception as e:
    log_test_result("5.3 Pattern cleanup", False, str(e))

# ============================================================================
# TEST 6: Integration Tests
# ============================================================================
print("\n🔗 TEST SUITE 6: Integration and Workflow")
print("-" * 80)

try:
    # Test complete workflow simulation
    # 1. Morning scan
    test_universe = ['AAPL', 'MSFT', 'GOOGL']
    
    # 2. Pattern recognition after entry
    test_tracker = PatternTracker()
    pattern = test_tracker.update_position_pattern(
        symbol='AAPL',
        current_price=152.0,
        entry_price=150.0,
        gap_at_open=0.018,  # 1.8% gap
        minutes_held=45
    )
    
    # 3. Exit timing decision
    test_time = datetime.now().replace(hour=10, minute=30)
    pnl_pct = (152.0 - 150.0) / 150.0
    should_exit, reason = recognizer.get_optimal_exit_time(
        pattern=pattern,
        current_time=test_time,
        pnl_pct=pnl_pct
    )
    
    if pattern is not None and should_exit:
        log_test_result("6.1 Complete workflow", True,
                       f"Pattern: {pattern.value}, Exit: {reason}")
    else:
        log_test_result("6.1 Complete workflow", False,
                       f"Workflow incomplete: pattern={pattern}, should_exit={should_exit}")
        
except Exception as e:
    log_test_result("6.1 Complete workflow", False, str(e))

try:
    # Test pattern descriptions
    descriptions = []
    for pattern in [StockPattern.MORNING_GAPPER, StockPattern.MOMENTUM_RUNNER, 
                   StockPattern.LATE_BLOOMER, StockPattern.RANGE_BOUND, 
                   StockPattern.REVERSAL]:
        desc = recognizer.get_pattern_description(pattern)
        descriptions.append(desc)
    
    if all(len(d) > 10 for d in descriptions):
        log_test_result("6.2 Pattern descriptions", True,
                       "All patterns have descriptions")
    else:
        log_test_result("6.2 Pattern descriptions", False,
                       "Some descriptions missing")
        
except Exception as e:
    log_test_result("6.2 Pattern descriptions", False, str(e))

try:
    # Test recommended check times
    check_times = recognizer.get_recommended_check_times(StockPattern.MOMENTUM_RUNNER)
    
    if isinstance(check_times, list) and len(check_times) > 0:
        log_test_result("6.3 Recommended check times", True,
                       f"Got {len(check_times)} check times")
    else:
        log_test_result("6.3 Recommended check times", False,
                       "No check times returned")
        
except Exception as e:
    log_test_result("6.3 Recommended check times", False, str(e))

# ============================================================================
# TEST 7: Edge Cases and Error Handling
# ============================================================================
print("\n⚠️ TEST SUITE 7: Edge Cases and Error Handling")
print("-" * 80)

try:
    # Test with None values
    pattern = recognizer.identify_pattern(
        current_price=None,
        entry_price=100.0,
        gap_at_open=None,
        minutes_held=30,
        price_history=None
    )
    
    if pattern == StockPattern.UNKNOWN:
        log_test_result("7.1 Null value handling", True,
                       "Returns UNKNOWN for bad data")
    else:
        log_test_result("7.1 Null value handling", False,
                       f"Should return UNKNOWN, got {pattern.value}")
        
except Exception as e:
    log_test_result("7.1 Null value handling", False, str(e))

try:
    # Test with minimal data
    pattern = recognizer.identify_pattern(
        current_price=100.5,
        entry_price=100.0,
        gap_at_open=None,
        minutes_held=5,  # Very short
        price_history=[100.0]  # Minimal history
    )
    
    # Should not crash
    log_test_result("7.2 Minimal data handling", True,
                   f"Handled minimal data, returned {pattern.value}")
        
except Exception as e:
    log_test_result("7.2 Minimal data handling", False, str(e))

try:
    # Test with extreme values
    pattern = recognizer.identify_pattern(
        current_price=150.0,
        entry_price=100.0,
        gap_at_open=0.5,  # 50% gap (extreme)
        minutes_held=300,
        price_history=[100.0, 120.0, 140.0, 150.0]
    )
    
    # Should not crash
    log_test_result("7.3 Extreme value handling", True,
                   f"Handled extreme gap, returned {pattern.value}")
        
except Exception as e:
    log_test_result("7.3 Extreme value handling", False, str(e))

# ============================================================================
# FINAL REPORT
# ============================================================================
print("\n" + "="*80)
print("📊 FINAL TEST REPORT")
print("="*80)

total_tests = len(test_results['passed']) + len(test_results['failed'])
pass_rate = len(test_results['passed']) / total_tests * 100 if total_tests > 0 else 0

print(f"\n✅ PASSED: {len(test_results['passed'])}/{total_tests} ({pass_rate:.1f}%)")
print(f"❌ FAILED: {len(test_results['failed'])}/{total_tests}")
print(f"⚠️ WARNINGS: {len(test_results['warnings'])}")

if test_results['failed']:
    print("\n❌ FAILED TESTS:")
    for test in test_results['failed']:
        print(f"   • {test}")

if test_results['warnings']:
    print("\n⚠️ WARNINGS:")
    for warning in test_results['warnings']:
        print(f"   • {warning}")

print("\n" + "="*80)

if len(test_results['failed']) == 0:
    print("🎉 ALL TESTS PASSED! System ready for Monday morning trading.")
    print("="*80 + "\n")
    sys.exit(0)
else:
    print("⚠️ SOME TESTS FAILED. Please review and fix before Monday.")
    print("="*80 + "\n")
    sys.exit(1)

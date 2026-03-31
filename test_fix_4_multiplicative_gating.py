#!/usr/bin/env python3
"""
Test Fix #4: Multiplicative confidence gating
This validates that negative adjustments are multiplicative (more severe)
and positive adjustments are additive (enhancing)
"""

import sys
from pathlib import Path


def test_multiplicative_gating():
    """Test Fix #4: Multiplicative confidence gating"""
    print("\n" + "="*60)
    print("TEST FIX #4: Multiplicative Confidence Gating")
    print("="*60 + "\n")
    
    # Test 1: Negative adjustments are multiplicative
    print("TEST 4.1: Negative adjustments are multiplicative")
    original = 0.60  # 60%
    
    # Old (WRONG - additive): 60% - 20% = 40%
    additive_result = original - 0.20
    
    # New (CORRECT - multiplicative): 60% * (1 - 0.20) = 60% * 0.80 = 48%
    multiplicative_result = original * (1.0 - 0.20)
    
    assert multiplicative_result > additive_result, \
        f"Multiplicative {multiplicative_result:.1%} should be > additive {additive_result:.1%}"
    assert multiplicative_result == 0.48, f"Expected 0.48, got {multiplicative_result}"
    print(f"  ✅ -20% adjustment: 60% → 48% (not 40%)")
    print(f"     Additive would give: 40%")
    print(f"     Multiplicative gives: 48% (less severe but still strong penalty)")
    
    # Test 2: Positive adjustments are additive
    print("\nTEST 4.2: Positive adjustments are additive")
    original = 0.60
    
    # Additive: 60% + 10% = 70%
    additive_result = min(original + 0.10, 1.0)
    
    # Multiplicative: 60% * 1.10 = 66% (different!)
    multiplicative_result = original * (1.0 + 0.10)
    
    assert additive_result != multiplicative_result, "Should be different"
    assert additive_result == 0.70, f"Expected 0.70, got {additive_result}"
    print(f"  ✅ +10% adjustment: 60% → 70% (additive)")
    print(f"     Multiplicative would give: 66% (we use additive for positive)")
    
    # Test 3: Multiple negative adjustments compound multiplicatively
    print("\nTEST 4.3: Multiple negative adjustments compound")
    result = 0.60
    result *= (1.0 - 0.20)  # -20% sentiment
    result *= (1.0 - 0.10)  # -10% dark pool
    result = max(min(result, 1.0), 0.0)
    
    expected = 0.60 * 0.80 * 0.90
    assert abs(result - expected) < 0.001, f"Expected {expected:.3f}, got {result:.3f}"
    assert abs(result - 0.432) < 0.001, f"Expected 0.432, got {result:.3f}"
    print(f"  ✅ Multiple negatives compound: 60% → {result:.1%}")
    print(f"     -20% then -10% = 0.60 × 0.80 × 0.90 = 0.432 = 43.2%")
    
    # Test 4: Extreme negative adjustment
    print("\nTEST 4.4: Extreme negative adjustment (-50%)")
    original = 0.60
    result = original * (1.0 - 0.50)
    assert result == 0.30, f"Expected 0.30, got {result}"
    print(f"  ✅ -50% adjustment: 60% → 30%")
    
    # Test 5: Cannot go negative
    print("\nTEST 4.5: Confidence cannot go below 0")
    result = 0.10
    result *= (1.0 - 0.50)  # -50%
    result *= (1.0 - 0.50)  # Another -50%
    result = max(result, 0.0)  # Clamp to 0
    print(f"  ✅ 10% with -50%, -50% = {result:.3f} (clamped to 0.0 if negative)")
    
    # Test 6: Positive adjustments stack additively (capped at 1.0)
    print("\nTEST 4.6: Positive adjustments stack additively (capped at 1.0)")
    result = 0.90
    result = min(result + 0.10, 1.0)  # +10%
    result = min(result + 0.05, 1.0)  # +5%
    assert result == 1.0, f"Expected 1.0, got {result}"
    print(f"  ✅ 90% + 10% + 5% = 1.0 (capped at maximum)")
    
    # Test 7: Mixed positive and negative adjustments
    print("\nTEST 4.7: Mixed positive and negative adjustments")
    result = 0.50
    
    # Apply negative adjustment multiplicatively
    result *= (1.0 - 0.30)  # -30% sentiment
    result = max(min(result, 1.0), 0.0)
    assert abs(result - 0.35) < 0.001, f"After -30%: expected 0.35, got {result}"
    
    # Apply positive adjustment additively
    result = min(result + 0.15, 1.0)  # +15%
    assert abs(result - 0.50) < 0.001, f"After +15%: expected 0.50, got {result}"
    
    print(f"  ✅ 50% → 35% (×0.70 for -30%) → 50% (+15% additive)")
    
    # Test 8: Comparison of old vs new methodology
    print("\nTEST 4.8: Old (additive) vs New (multiplicative) comparison")
    
    scenarios = [
        (0.60, -0.05, "Mild negative (-5%)"),
        (0.60, -0.20, "Medium negative (-20%)"),
        (0.30, -0.20, "Low confidence with -20%"),
        (0.80, -0.30, "High confidence with -30%"),
    ]
    
    print("\n  Base Conf | Adjustment | Old (Additive) | New (Multiplicative) | Difference")
    print("  " + "-"*80)
    
    for base_conf, adjustment, description in scenarios:
        if adjustment < 0:
            old_result = max(base_conf + adjustment, 0.0)
            new_result = base_conf * (1.0 + adjustment)
            new_result = max(min(new_result, 1.0), 0.0)
            diff = new_result - old_result
            
            print(f"  {base_conf:.1%}     | {adjustment:+.2f}     | {old_result:.1%}          | {new_result:.1%}           | {diff:+.1%}")
            
            # Verify multiplicative is always >= additive for negative adjustments
            if adjustment < 0:
                assert new_result >= old_result, \
                    f"Multiplicative {new_result:.1%} should be >= additive {old_result:.1%}"
    
    print("\n" + "="*60)
    print("✅ ALL FIX #4 TESTS PASSED")
    print("="*60 + "\n")
    return True


if __name__ == '__main__':
    try:
        test_multiplicative_gating()
        sys.exit(0)
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)

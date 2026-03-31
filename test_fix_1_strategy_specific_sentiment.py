#!/usr/bin/env python3
"""
Test Fix #1: Strategy-specific sentiment scoring
This validates that sentiment adjustments are now strategy-aware
"""

import sys
from pathlib import Path

# Add bot_v2 to path
sys.path.insert(0, str(Path(__file__).parent / 'bot_v2'))

from data_sources.news_sentiment import NewsSentimentAnalyzer


def test_strategy_specific_sentiment():
    """Test Fix #1: Strategy-specific adjustments"""
    print("\n" + "="*60)
    print("TEST FIX #1: Strategy-Specific Sentiment Scoring")
    print("="*60 + "\n")
    
    analyzer = NewsSentimentAnalyzer()
    
    # Test 1: Gap & Go + BEAR should penalize heavily (-25%)
    print("TEST 1.1: Gap & Go + BEAR sentiment")
    gap_go_bear = analyzer.get_sentiment_adjustment(
        {'signal': 'BEAR'},
        strategy='gap_go'
    )
    assert gap_go_bear == -0.25, f"Expected -0.25, got {gap_go_bear}"
    print(f"  ✅ Gap & Go + BEAR = {gap_go_bear:.2f} (-25%)")
    
    # Test 2: Gap & Go + STRONG_BULL should boost (+20%)
    print("\nTEST 1.2: Gap & Go + STRONG_BULL sentiment")
    gap_go_bull = analyzer.get_sentiment_adjustment(
        {'signal': 'STRONG_BULL'},
        strategy='gap_go'
    )
    assert gap_go_bull == 0.20, f"Expected 0.20, got {gap_go_bull}"
    print(f"  ✅ Gap & Go + STRONG_BULL = {gap_go_bull:.2f} (+20%)")
    
    # Test 3: Fade/Short + STRONG_BULL should penalize heavily (-25%)
    print("\nTEST 1.3: Fade/Short + STRONG_BULL sentiment")
    fade_bull = analyzer.get_sentiment_adjustment(
        {'signal': 'STRONG_BULL'},
        strategy='fade_short'
    )
    assert fade_bull == -0.25, f"Expected -0.25, got {fade_bull}"
    print(f"  ✅ Fade/Short + STRONG_BULL = {fade_bull:.2f} (-25%)")
    
    # Test 4: Fade/Short + BEAR should be neutral (0%)
    print("\nTEST 1.4: Fade/Short + BEAR sentiment")
    fade_bear = analyzer.get_sentiment_adjustment(
        {'signal': 'BEAR'},
        strategy='fade_short'
    )
    assert fade_bear == 0.0, f"Expected 0.0, got {fade_bear}"
    print(f"  ✅ Fade/Short + BEAR = {fade_bear:.2f} (0% - stock weakness helps shorts)")
    
    # Test 5: Mean Reversion + BEAR + dark pool should boost (+20%)
    print("\nTEST 1.5: Mean Reversion + BEAR + Dark Pool")
    mr_bear_dp = analyzer.get_sentiment_adjustment(
        {'signal': 'BEAR'},
        strategy='mean_reversion',
        has_dark_pool_buying=True
    )
    assert mr_bear_dp == 0.20, f"Expected 0.20, got {mr_bear_dp}"
    print(f"  ✅ Mean Reversion + BEAR + DP = {mr_bear_dp:.2f} (+20% - smart money buying dip)")
    
    # Test 6: Mean Reversion + BEAR without dark pool should penalize (-5%)
    print("\nTEST 1.6: Mean Reversion + BEAR without Dark Pool")
    mr_bear_no_dp = analyzer.get_sentiment_adjustment(
        {'signal': 'BEAR'},
        strategy='mean_reversion',
        has_dark_pool_buying=False
    )
    assert mr_bear_no_dp == -0.05, f"Expected -0.05, got {mr_bear_no_dp}"
    print(f"  ✅ Mean Reversion + BEAR (no DP) = {mr_bear_no_dp:.2f} (-5% - risky without institutional support)")
    
    # Test 7: All strategies skip on STRONG_BEAR
    print("\nTEST 1.7: All strategies skip on STRONG_BEAR")
    for strat in ['gap_go', 'fade_short', 'mean_reversion']:
        adj = analyzer.get_sentiment_adjustment(
            {'signal': 'STRONG_BEAR'},
            strategy=strat
        )
        assert adj == -1.0, f"Expected -1.0 for {strat}, got {adj}"
        print(f"  ✅ {strat.upper()} + STRONG_BEAR = {adj:.2f} (hard skip)")
    
    # Test 8: Backward compatibility - get_contrarian_adjustment still works
    print("\nTEST 1.8: Backward compatibility (get_contrarian_adjustment)")
    old_method = analyzer.get_contrarian_adjustment(
        {'signal': 'BEAR'},
        has_dark_pool_buying=True
    )
    new_method = analyzer.get_sentiment_adjustment(
        {'signal': 'BEAR'},
        strategy='mean_reversion',
        has_dark_pool_buying=True
    )
    assert old_method == new_method, f"Backward compat failed: {old_method} != {new_method}"
    print(f"  ✅ Old get_contrarian_adjustment() returns same as new method: {old_method:.2f}")
    
    print("\n" + "="*60)
    print("✅ ALL FIX #1 TESTS PASSED")
    print("="*60 + "\n")
    return True


if __name__ == '__main__':
    try:
        test_strategy_specific_sentiment()
        sys.exit(0)
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)

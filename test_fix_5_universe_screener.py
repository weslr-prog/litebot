#!/usr/bin/env python3
"""
Test Fix #5: Universe-level sentiment screening
This validates that the screener can classify stocks as safe/risky/blocked
"""

import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock

# Add bot_v2 to path
sys.path.insert(0, str(Path(__file__).parent / 'bot_v2'))

from screening.universe_sentiment_screener import UniverseSentimentScreener
from safety.sentiment_veto import SentimentVetoGate


def test_universe_screener():
    """Test Fix #5: Universe sentiment screener"""
    print("\n" + "="*60)
    print("TEST FIX #5: Universe-Level Sentiment Screening")
    print("="*60 + "\n")
    
    # Create mock sentiment analyzer and veto gate
    mock_analyzer = Mock()
    veto = SentimentVetoGate()
    
    # Test 1: Screener initialization
    print("TEST 5.1: Screener initialization")
    screener = UniverseSentimentScreener(mock_analyzer, veto)
    assert screener is not None
    assert screener.sentiment_analyzer == mock_analyzer
    assert screener.veto_gate == veto
    print(f"  ✅ UniverseSentimentScreener initialized successfully")
    
    # Test 2: Results structure
    print("\nTEST 5.2: Results structure")
    
    # Mock the sentiment analyzer to return test data
    def mock_get_sentiment(symbol, hours_lookback=24):
        sentiments = {
            'SAFE_BULL': {
                'signal': 'STRONG_BULL',
                'article_count': 3,
                'sentiment_score': 0.8,
                'headlines': [],
                'data_quality': 'high',
                'quality_confidence': 0.9,
                'stale_penalty': 0.0,
            },
            'SAFE_NEUTRAL': {
                'signal': 'NEUTRAL',
                'article_count': 0,
                'sentiment_score': 0.0,
                'headlines': [],
                'data_quality': 'missing',
                'quality_confidence': 0.0,
                'stale_penalty': 0.0,
            },
            'RISKY_BEAR': {
                'signal': 'BEAR',
                'article_count': 2,
                'sentiment_score': -0.35,
                'headlines': [],
                'data_quality': 'medium',
                'quality_confidence': 0.7,
                'stale_penalty': 0.0,
            },
            'BLOCKED_BANKRUPTCY': {
                'signal': 'STRONG_BEAR',
                'article_count': 1,
                'sentiment_score': -0.9,
                'headlines': [{'headline': 'Bankruptcy Filed', 'summary': ''}],
                'data_quality': 'high',
                'quality_confidence': 1.0,
                'stale_penalty': 0.0,
            },
        }
        return sentiments.get(symbol, sentiments['SAFE_NEUTRAL'])
    
    mock_analyzer.get_sentiment = mock_get_sentiment
    mock_analyzer.client = Mock()  # Pretend client exists
    
    # Create test universe
    test_universe = [
        'SAFE_BULL',
        'SAFE_NEUTRAL',
        'RISKY_BEAR',
        'BLOCKED_BANKRUPTCY'
    ]
    
    # Run screening
    results = screener.screen_universe(test_universe)
    
    # Verify structure
    assert 'safe' in results, "Missing 'safe' key"
    assert 'risky' in results, "Missing 'risky' key"
    assert 'blocked' in results, "Missing 'blocked' key"
    assert isinstance(results['safe'], list), "'safe' should be list"
    assert isinstance(results['risky'], dict), "'risky' should be dict"
    assert isinstance(results['blocked'], list), "'blocked' should be list"
    print(f"  ✅ Results structure correct: {results}")
    
    # Test 3: Safe stocks classification
    print("\nTEST 5.3: Safe stocks classification")
    assert 'SAFE_BULL' in results['safe'], "SAFE_BULL should be in safe list"
    assert 'SAFE_NEUTRAL' in results['safe'], "SAFE_NEUTRAL should be in safe list"
    print(f"  ✅ Safe stocks: {results['safe']}")
    
    # Test 4: Risky stocks classification
    print("\nTEST 5.4: Risky stocks classification")
    assert 'RISKY_BEAR' in results['risky'], "RISKY_BEAR should be in risky dict"
    assert results['risky']['RISKY_BEAR']['sentiment']['signal'] == 'BEAR'
    print(f"  ✅ Risky stocks: {list(results['risky'].keys())}")
    
    # Test 5: Blocked stocks classification
    print("\nTEST 5.5: Blocked stocks classification")
    blocked_symbols = [s[0] for s in results['blocked']]
    assert 'BLOCKED_BANKRUPTCY' in blocked_symbols, "BLOCKED_BANKRUPTCY should be blocked"
    print(f"  ✅ Blocked stocks: {blocked_symbols}")
    
    # Test 6: Get safe universe (includes risky)
    print("\nTEST 5.6: Get safe universe (safe + risky)")
    safe_universe = screener.get_safe_universe(results)
    assert len(safe_universe) == 3, f"Expected 3 tradeable stocks, got {len(safe_universe)}"
    assert 'SAFE_BULL' in safe_universe
    assert 'SAFE_NEUTRAL' in safe_universe
    assert 'RISKY_BEAR' in safe_universe
    assert 'BLOCKED_BANKRUPTCY' not in safe_universe
    print(f"  ✅ Safe universe (can trade): {safe_universe}")
    
    # Test 7: Get very safe universe (safe only)
    print("\nTEST 5.7: Get very safe universe (safe only)")
    very_safe = screener.get_very_safe_universe(results)
    assert len(very_safe) == 2, f"Expected 2 very safe stocks, got {len(very_safe)}"
    assert 'SAFE_BULL' in very_safe
    assert 'SAFE_NEUTRAL' in very_safe
    assert 'RISKY_BEAR' not in very_safe
    assert 'BLOCKED_BANKRUPTCY' not in very_safe
    print(f"  ✅ Very safe universe (no risk): {very_safe}")
    
    # Test 8: Get blocked universe with reasons
    print("\nTEST 5.8: Get blocked stocks with reasons")
    blocked_with_reasons = screener.get_blocked_universe(results)
    assert len(blocked_with_reasons) == 1
    symbol, reason = blocked_with_reasons[0]
    assert symbol == 'BLOCKED_BANKRUPTCY'
    assert 'bankruptcy' in reason.lower() or 'disaster' in reason.lower()
    print(f"  ✅ Blocked stocks: {blocked_with_reasons}")
    
    # Test 9: Screener handles disabled sentiment analyzer
    print("\nTEST 5.9: Handle disabled sentiment analyzer")
    mock_disabled = Mock()
    mock_disabled.client = None  # No client = disabled
    screener_disabled = UniverseSentimentScreener(mock_disabled, veto)
    results_disabled = screener_disabled.screen_universe(['ABC', 'DEF'])
    assert len(results_disabled['safe']) == 2, "Should treat all as safe when analyzer disabled"
    assert len(results_disabled['risky']) == 0
    assert len(results_disabled['blocked']) == 0
    print(f"  ✅ Disabled analyzer defaults all to safe")
    
    # Test 10: Empty universe
    print("\nTEST 5.10: Empty universe handling")
    results_empty = screener.screen_universe([])
    assert results_empty['safe'] == []
    assert results_empty['risky'] == {}
    assert results_empty['blocked'] == []
    print(f"  ✅ Empty universe handled correctly")
    
    print("\n" + "="*60)
    print("✅ ALL FIX #5 TESTS PASSED")
    print("="*60 + "\n")
    return True


if __name__ == '__main__':
    try:
        test_universe_screener()
        sys.exit(0)
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)

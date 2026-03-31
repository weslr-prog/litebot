#!/usr/bin/env python3
"""
Test Fix #3: Hard veto rules for disaster news
This validates that hard exclusion rules work correctly
"""

import sys
from pathlib import Path

# Add bot_v2 to path
sys.path.insert(0, str(Path(__file__).parent / 'bot_v2'))

from safety.sentiment_veto import SentimentVetoGate


def test_hard_veto_gate():
    """Test Fix #3: Hard veto rules"""
    print("\n" + "="*60)
    print("TEST FIX #3: Hard Veto Gate for Disaster News")
    print("="*60 + "\n")
    
    veto = SentimentVetoGate()
    
    # Test 1: Bankruptcy keyword should trigger hard veto
    print("TEST 3.1: Bankruptcy keyword triggers hard veto")
    sentiment_bankruptcy = {
        'signal': 'STRONG_BEAR',
        'article_count': 1,
        'sentiment_score': -0.9,
        'headlines': [
            {'headline': 'XYZ Files for Bankruptcy Protection', 'summary': 'Company seeking bankruptcy'}
        ]
    }
    should_veto, reason, sev = veto.check_veto(sentiment_bankruptcy, 'XYZ')
    assert should_veto == True, "Expected veto for bankruptcy keyword"
    assert sev == 'hard', f"Expected 'hard' severity, got {sev}"
    assert 'bankruptcy' in reason.lower(), f"Expected 'bankruptcy' in reason, got {reason}"
    print(f"  ✅ Bankruptcy keyword triggers hard veto: {reason}")
    
    # Test 2: Fraud keyword should trigger hard veto
    print("\nTEST 3.2: Fraud keyword triggers hard veto")
    sentiment_fraud = {
        'signal': 'STRONG_BEAR',
        'article_count': 1,
        'sentiment_score': -0.95,
        'headlines': [
            {'headline': 'SEC Charges XYZ with Fraud', 'summary': 'Accounting fraud allegations'}
        ]
    }
    should_veto, reason, sev = veto.check_veto(sentiment_fraud, 'XYZ')
    assert should_veto == True, "Expected veto for fraud keyword"
    assert sev == 'hard', f"Expected 'hard' severity, got {sev}"
    print(f"  ✅ Fraud keyword triggers hard veto: {reason}")
    
    # Test 3: STRONG_BEAR + multiple articles should veto
    print("\nTEST 3.3: STRONG_BEAR + multiple articles triggers veto")
    sentiment_strong_bear = {
        'signal': 'STRONG_BEAR',
        'article_count': 3,
        'sentiment_score': -0.85,
        'headlines': []
    }
    should_veto, reason, sev = veto.check_veto(sentiment_strong_bear, 'ABC')
    assert should_veto == True, "Expected veto for STRONG_BEAR + multiple articles"
    assert sev == 'hard', f"Expected 'hard' severity, got {sev}"
    print(f"  ✅ STRONG_BEAR + multiple articles triggers veto: {reason}")
    
    # Test 4: STRONG_BEAR + single article with extreme negative should veto
    print("\nTEST 3.4: STRONG_BEAR + single extreme negative article triggers veto")
    sentiment_extreme = {
        'signal': 'STRONG_BEAR',
        'article_count': 1,
        'sentiment_score': -0.95,
        'headlines': [
            {'headline': 'Stock Down 50% on Missed Earnings', 'summary': ''}
        ]
    }
    should_veto, reason, sev = veto.check_veto(sentiment_extreme, 'DEF')
    assert should_veto == True, "Expected veto for extreme negative"
    assert sev == 'hard', f"Expected 'hard' severity, got {sev}"
    print(f"  ✅ Extreme negative score triggers veto: {reason}")
    
    # Test 5: BEAR alone should NOT veto
    print("\nTEST 3.5: BEAR sentiment alone does not trigger veto")
    sentiment_bear = {
        'signal': 'BEAR',
        'article_count': 1,
        'sentiment_score': -0.4,
        'headlines': [
            {'headline': 'Stock Down on Earnings Miss', 'summary': ''}
        ]
    }
    should_veto, reason, sev = veto.check_veto(sentiment_bear, 'GHI')
    assert should_veto == False, "BEAR alone should not veto"
    assert sev == 'none', f"Expected 'none' severity, got {sev}"
    print(f"  ✅ BEAR alone does not veto: severity={sev}")
    
    # Test 6: Neutral sentiment should NOT veto
    print("\nTEST 3.6: NEUTRAL sentiment does not veto")
    sentiment_neutral = {
        'signal': 'NEUTRAL',
        'article_count': 2,
        'sentiment_score': 0.05,
        'headlines': [
            {'headline': 'Stock Announcement', 'summary': ''}
        ]
    }
    should_veto, reason, sev = veto.check_veto(sentiment_neutral, 'JKL')
    assert should_veto == False, "NEUTRAL should not veto"
    print(f"  ✅ NEUTRAL does not veto: severity={sev}")
    
    # Test 7: Multiple negative articles with bad score should veto
    print("\nTEST 3.7: Multiple negative articles with bad average score vetos")
    sentiment_multi_neg = {
        'signal': 'BEAR',
        'article_count': 6,
        'sentiment_score': -0.5,
        'headlines': [
            {'headline': 'Earnings Miss', 'summary': 'Bad earnings'},
            {'headline': 'Guidance Down', 'summary': 'Lower guidance'},
            {'headline': 'Analyst Downgrade', 'summary': 'Sell rating'},
        ]
    }
    should_veto, reason, sev = veto.check_veto(sentiment_multi_neg, 'MNO')
    assert should_veto == True, "Expected veto for multiple negative articles"
    assert sev == 'hard', f"Expected 'hard' severity, got {sev}"
    print(f"  ✅ Multiple negatives with bad score veto: {reason}")
    
    # Test 8: Delisting keyword should trigger hard veto
    print("\nTEST 3.8: Delisting keyword triggers hard veto")
    sentiment_delisting = {
        'signal': 'STRONG_BEAR',
        'article_count': 1,
        'sentiment_score': -0.9,
        'headlines': [
            {'headline': 'NYSE Delisting XYZ Stock Effective immediately', 'summary': ''}
        ]
    }
    should_veto, reason, sev = veto.check_veto(sentiment_delisting, 'PQR')
    assert should_veto == True, "Expected veto for delisting keyword"
    assert 'delisting' in reason.lower(), f"Expected 'delisting' in reason, got {reason}"
    print(f"  ✅ Delisting keyword triggers hard veto: {reason}")
    
    # Test 9: Soft veto keyword should log warning but not block
    print("\nTEST 3.9: Soft veto triggers warning but not block")
    sentiment_soft = {
        'signal': 'NEUTRAL',
        'article_count': 1,
        'sentiment_score': -0.1,
        'headlines': [
            {'headline': 'Analyst Downgrade on XYZ', 'summary': 'Price target cut'}
        ]
    }
    should_veto, reason, sev = veto.check_veto(sentiment_soft, 'STU')
    assert should_veto == False, "Soft veto should not block"
    assert sev == 'soft', f"Expected 'soft' severity, got {sev}"
    assert 'downgrade' in reason.lower(), f"Expected 'downgrade' in reason, got {reason}"
    print(f"  ✅ Soft veto triggers warning: {reason} (severity={sev})")
    
    # Test 10: Format veto message correctly
    print("\nTEST 3.10: Veto message formatting")
    hard_msg = veto.format_veto_message('TEST', (True, 'Hard veto reason', 'hard'))
    assert '🚫' in hard_msg, "Hard veto should have veto emoji"
    assert 'TEST' in hard_msg, "Message should include symbol"
    print(f"  ✅ Hard veto message: {hard_msg}")
    
    soft_msg = veto.format_veto_message('TEST', (True, 'Soft veto reason', 'soft'))
    assert '⚠️' in soft_msg, "Soft veto should have warning emoji"
    print(f"  ✅ Soft veto message: {soft_msg}")
    
    print("\n" + "="*60)
    print("✅ ALL FIX #3 TESTS PASSED")
    print("="*60 + "\n")
    return True


if __name__ == '__main__':
    try:
        test_hard_veto_gate()
        sys.exit(0)
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)

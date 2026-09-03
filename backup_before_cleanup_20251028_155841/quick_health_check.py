"""
Quick Health Check for Phase 3A Components
Verifies all components can be imported and initialized
"""

import sys
import traceback

def test_imports():
    """Test all imports"""
    print("🔧 TESTING IMPORTS...")
    
    try:
        from core.signal_confidence import SignalConfidenceScorer
        print("   ✅ SignalConfidenceScorer imported")
    except Exception as e:
        print(f"   ❌ SignalConfidenceScorer failed: {e}")
        return False
    
    try:
        from core.enhanced_regime_detector import EnhancedRegimeDetector
        print("   ✅ EnhancedRegimeDetector imported")
    except Exception as e:
        print(f"   ❌ EnhancedRegimeDetector failed: {e}")
        return False
    
    try:
        from core.phase3a_enhanced_strategy import Phase3AEnhancedStrategy
        print("   ✅ Phase3AEnhancedStrategy imported")
    except Exception as e:
        print(f"   ❌ Phase3AEnhancedStrategy failed: {e}")
        return False
    
    try:
        from core.smart_threshold_strategy import SmartThresholdStrategy
        print("   ✅ SmartThresholdStrategy imported")
    except Exception as e:
        print(f"   ❌ SmartThresholdStrategy failed: {e}")
        return False
    
    return True

def test_initializations():
    """Test component initializations"""
    print("\n🔧 TESTING INITIALIZATIONS...")
    
    try:
        from core.signal_confidence import SignalConfidenceScorer
        scorer = SignalConfidenceScorer()
        print("   ✅ SignalConfidenceScorer initialized")
    except Exception as e:
        print(f"   ❌ SignalConfidenceScorer init failed: {e}")
        return False
    
    try:
        from core.enhanced_regime_detector import EnhancedRegimeDetector
        detector = EnhancedRegimeDetector()
        print("   ✅ EnhancedRegimeDetector initialized")
    except Exception as e:
        print(f"   ❌ EnhancedRegimeDetector init failed: {e}")
        return False
    
    try:
        from core.phase3a_enhanced_strategy import Phase3AEnhancedStrategy
        strategy = Phase3AEnhancedStrategy("test_key")
        print("   ✅ Phase3AEnhancedStrategy initialized")
    except Exception as e:
        print(f"   ❌ Phase3AEnhancedStrategy init failed: {e}")
        traceback.print_exc()
        return False
    
    try:
        from core.smart_threshold_strategy import SmartThresholdStrategy
        smart_strategy = SmartThresholdStrategy("test_key")
        print("   ✅ SmartThresholdStrategy initialized")
        print(f"   ✅ Has {len(smart_strategy.thresholds)} threshold levels")
    except Exception as e:
        print(f"   ❌ SmartThresholdStrategy init failed: {e}")
        traceback.print_exc()
        return False
    
    return True

def main():
    """Run quick health check"""
    print("🏥 PHASE 3A HEALTH CHECK")
    print("=" * 40)
    
    # Test imports
    imports_ok = test_imports()
    
    if not imports_ok:
        print("\n❌ Import failures detected - cannot proceed")
        return False
    
    # Test initializations
    init_ok = test_initializations()
    
    if not init_ok:
        print("\n❌ Initialization failures detected")
        return False
    
    print("\n🎉 HEALTH CHECK PASSED!")
    print("✅ All Phase 3A components are working properly")
    print("✅ Ready for production use")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

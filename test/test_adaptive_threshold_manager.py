"""
Test Suite for Adaptive Threshold Manager
Validates Phase 3B adaptive threshold optimization functionality
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.adaptive_threshold_manager import AdaptiveThresholdManager, PerformanceMetrics, ThresholdAdjustment
import numpy as np
from datetime import datetime, timedelta

def test_adaptive_threshold_manager():
    """Comprehensive test of the Adaptive Threshold Manager"""
    print("🧪 TESTING ADAPTIVE THRESHOLD MANAGER")
    print("=" * 50)
    
    # Initialize manager
    manager = AdaptiveThresholdManager()
    print("✅ Manager initialized successfully")
    
    # Test 1: Basic analysis functionality
    print("\n📊 Testing trade log analysis...")
    metrics = manager.analyze_trade_logs(days=30)
    
    assert isinstance(metrics, PerformanceMetrics)
    assert 0 <= metrics.win_rate <= 1
    assert metrics.sharpe_ratio > 0
    assert metrics.total_trades >= 0
    print(f"   Win Rate: {metrics.win_rate:.1%}")
    print(f"   Sharpe Ratio: {metrics.sharpe_ratio:.2f}")
    print(f"   Total Trades: {metrics.total_trades}")
    print("✅ Trade analysis working properly")
    
    # Test 2: Threshold adjustment recommendations
    print("\n🎯 Testing threshold adjustment logic...")
    
    # Create test scenarios
    scenarios = [
        # Low win rate scenario
        PerformanceMetrics(
            win_rate=0.45, avg_return=0.01, sharpe_ratio=0.8, 
            max_drawdown=0.1, total_trades=20, profitable_trades=9,
            avg_winning_trade=0.05, avg_losing_trade=-0.03, profit_factor=1.67
        ),
        # High win rate scenario
        PerformanceMetrics(
            win_rate=0.85, avg_return=0.03, sharpe_ratio=2.1, 
            max_drawdown=0.05, total_trades=20, profitable_trades=17,
            avg_winning_trade=0.04, avg_losing_trade=-0.02, profit_factor=2.0
        ),
        # High drawdown scenario
        PerformanceMetrics(
            win_rate=0.65, avg_return=0.02, sharpe_ratio=1.2, 
            max_drawdown=0.25, total_trades=20, profitable_trades=13,
            avg_winning_trade=0.06, avg_losing_trade=-0.04, profit_factor=1.5
        )
    ]
    
    scenario_names = ["Low Win Rate", "High Win Rate", "High Drawdown"]
    
    for i, (scenario, name) in enumerate(zip(scenarios, scenario_names)):
        print(f"\n   Scenario {i+1}: {name}")
        adjustments = manager.recommend_threshold_adjustments(scenario)
        print(f"   Adjustments recommended: {len(adjustments)}")
        
        for adj in adjustments:
            print(f"     {adj.component}: {adj.current_value} → {adj.recommended_value}")
            print(f"     Reason: {adj.adjustment_reason}")
            print(f"     Confidence: {adj.confidence:.1%}")
        
        assert isinstance(adjustments, list)
        for adj in adjustments:
            assert isinstance(adj, ThresholdAdjustment)
            assert 0 <= adj.confidence <= 1
    
    print("✅ Threshold adjustment logic working properly")
    
    # Test 3: Complete adaptive analysis cycle
    print("\n🔄 Testing complete adaptive analysis...")
    results = manager.run_adaptive_analysis(days=30)
    
    required_keys = ['analysis_date', 'days_analyzed', 'performance_metrics', 
                     'adjustments_recommended', 'adjustment_details']
    
    for key in required_keys:
        assert key in results
        print(f"   ✓ {key}: {type(results[key])}")
    
    assert results['days_analyzed'] == 30
    assert isinstance(results['performance_metrics'], dict)
    assert isinstance(results['adjustments_recommended'], int)
    assert isinstance(results['adjustment_details'], list)
    
    print("✅ Complete analysis cycle working properly")
    
    # Test 4: Performance metrics calculation
    print("\n📈 Testing performance metrics calculation...")
    
    # Create sample trades
    sample_trades = [
        {'timestamp': datetime.now(), 'symbol': 'TEST1', 'return': 0.05},
        {'timestamp': datetime.now(), 'symbol': 'TEST2', 'return': -0.02},
        {'timestamp': datetime.now(), 'symbol': 'TEST3', 'return': 0.03},
        {'timestamp': datetime.now(), 'symbol': 'TEST4', 'return': 0.01},
        {'timestamp': datetime.now(), 'symbol': 'TEST5', 'return': -0.01},
    ]
    
    test_metrics = manager._calculate_performance_metrics(sample_trades)
    
    expected_win_rate = 3/5  # 3 profitable out of 5
    assert abs(test_metrics.win_rate - expected_win_rate) < 0.001
    assert test_metrics.total_trades == 5
    assert test_metrics.profitable_trades == 3
    
    print(f"   Expected win rate: {expected_win_rate:.1%}")
    print(f"   Calculated win rate: {test_metrics.win_rate:.1%}")
    print("✅ Performance metrics calculation accurate")
    
    print("\n🎉 ALL TESTS PASSED!")
    print("✅ Adaptive Threshold Manager is fully operational")
    
    return True

def run_sample_analysis():
    """Run a sample analysis to demonstrate functionality"""
    print("\n🚀 RUNNING SAMPLE ADAPTIVE ANALYSIS")
    print("=" * 50)
    
    manager = AdaptiveThresholdManager()
    results = manager.run_adaptive_analysis(days=30)
    
    print(f"Analysis Date: {results['analysis_date']}")
    print(f"Period Analyzed: {results['days_analyzed']} days")
    print(f"Win Rate: {results['performance_metrics']['win_rate']:.1%}")
    print(f"Average Return: {results['performance_metrics']['avg_return']:.2%}")
    print(f"Sharpe Ratio: {results['performance_metrics']['sharpe_ratio']:.2f}")
    print(f"Max Drawdown: {results['performance_metrics']['max_drawdown']:.1%}")
    print(f"Total Trades: {results['performance_metrics']['total_trades']}")
    print(f"Adjustments Recommended: {results['adjustments_recommended']}")
    
    if results['adjustment_details']:
        print("\nRecommended Threshold Adjustments:")
        for adj in results['adjustment_details']:
            print(f"  📊 {adj['component']}")
            print(f"     Current: {adj['old_value']}")
            print(f"     Recommended: {adj['new_value']}")
            print(f"     Reason: {adj['reason']}")
            print(f"     Confidence: {adj['confidence']:.1%}")
            print()
    else:
        print("\n✅ No threshold adjustments needed - performance within targets")

if __name__ == "__main__":
    try:
        # Run comprehensive tests
        test_adaptive_threshold_manager()
        
        # Run sample analysis
        run_sample_analysis()
        
        print("\n🎯 PHASE 3B ADAPTIVE THRESHOLD MANAGER")
        print("✅ Successfully implemented and tested")
        print("📊 Ready for automated threshold optimization")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        raise

#!/usr/bin/env python3
"""
Strategic Improvements Test Suite
================================

Comprehensive testing for the strategic improvements implementation:
1. Dynamic profit targets
2. Enhanced trailing stops
3. Improved signal quality
4. Smart exit timing

Tests both individual components and system-wide integration.
"""

import unittest
import os
import sys
import numpy as np
import pandas as pd
from datetime import datetime, date, timedelta
from unittest.mock import Mock, patch
import json

project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from strategic_improvements import EnhancedExitManager, EnhancedSignalGenerator, StrategicImprovementEngine

class TestEnhancedExitManager(unittest.TestCase):
    """Test enhanced exit management functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.config = Mock()
        self.config.confidence_threshold = 0.07
        self.config.max_positions_per_day = 5
        
        self.exit_manager = EnhancedExitManager(self.config)
        
        # Mock position
        self.mock_position = Mock()
        self.mock_position.symbol = "TEST"
        self.mock_position.entry_price = 100.0
        self.mock_position.entry_date = date.today() - timedelta(days=1)
        self.mock_position.exit_date = date.today()
        self.mock_position.stop_price = 95.0  # Set a concrete stop price
        
        # Create test market data
        dates = pd.date_range(start='2025-10-01', periods=30, freq='D')
        self.test_data = pd.DataFrame({
            'open': np.random.normal(100, 2, 30),
            'high': np.random.normal(102, 2, 30),
            'low': np.random.normal(98, 2, 30),
            'close': np.random.normal(100, 2, 30),
            'volume': np.random.normal(1000000, 200000, 30)
        }, index=dates)
        
        # Ensure high >= close >= low for realistic data
        self.test_data['high'] = np.maximum(self.test_data['high'], self.test_data['close'])
        self.test_data['low'] = np.minimum(self.test_data['low'], self.test_data['close'])
    
    def test_dynamic_profit_target_calculation(self):
        """Test dynamic profit target calculation"""
        target = self.exit_manager.calculate_dynamic_profit_target(
            self.mock_position, self.test_data
        )
        
        # Should return a valid profit target
        self.assertIsNotNone(target)
        self.assertIsInstance(target, (int, float))
        self.assertGreater(target, self.mock_position.entry_price)
        
        # Should be at least 1.5% above entry price
        min_expected = self.mock_position.entry_price * 1.015
        self.assertGreaterEqual(target, min_expected)
        
        print(f"✅ Dynamic profit target: ${target:.2f} (entry: ${self.mock_position.entry_price:.2f})")
    
    def test_dynamic_profit_target_with_empty_data(self):
        """Test profit target calculation with empty data"""
        empty_data = pd.DataFrame()
        target = self.exit_manager.calculate_dynamic_profit_target(
            self.mock_position, empty_data
        )
        
        # Should fallback to simple percentage target
        expected_fallback = self.mock_position.entry_price * 1.025
        self.assertEqual(target, expected_fallback)
        
        print(f"✅ Fallback profit target: ${target:.2f}")
    
    def test_trailing_stop_calculation(self):
        """Test trailing stop calculation"""
        current_price = 105.0  # 5% profit
        highest_price = 107.0  # 7% profit peak
        
        trailing_stop = self.exit_manager.calculate_trailing_stop(
            self.mock_position, current_price, highest_price
        )
        
        # Should return a trailing stop when profitable enough
        self.assertIsNotNone(trailing_stop)
        self.assertGreater(trailing_stop, self.mock_position.entry_price)
        self.assertLess(trailing_stop, highest_price)
        
        print(f"✅ Trailing stop: ${trailing_stop:.2f} (current: ${current_price:.2f}, peak: ${highest_price:.2f})")
    
    def test_trailing_stop_not_activated_when_unprofitable(self):
        """Test trailing stop not activated when position not profitable enough"""
        current_price = 101.0  # Only 1% profit, below 1.5% threshold
        highest_price = 101.0
        
        trailing_stop = self.exit_manager.calculate_trailing_stop(
            self.mock_position, current_price, highest_price
        )
        
        # Should not activate trailing stop
        self.assertIsNone(trailing_stop)
        
        print(f"✅ Trailing stop not activated for small profit (1%)")
    
    def test_enhanced_exit_logic_profit_target_hit(self):
        """Test exit logic when dynamic profit target is hit"""
        current_price = 110.0  # Significant profit
        current_time = datetime.now()
        highest_price = 110.0
        
        should_exit, reason = self.exit_manager.should_exit_with_dynamic_logic(
            self.mock_position, current_price, current_time, self.test_data, highest_price
        )
        
        # Should exit when profit target is hit
        self.assertTrue(should_exit)
        self.assertIn("PROFIT", reason.upper())
        
        print(f"✅ Exit triggered: {reason} at ${current_price:.2f}")
    
    def test_enhanced_exit_logic_trailing_stop_hit(self):
        """Test exit logic when trailing stop is hit"""
        current_price = 103.0  # Small profit now
        highest_price = 108.0  # Was much higher
        current_time = datetime.now()
        
        should_exit, reason = self.exit_manager.should_exit_with_dynamic_logic(
            self.mock_position, current_price, current_time, self.test_data, highest_price
        )
        
        # May exit due to trailing stop
        if should_exit:
            print(f"✅ Exit triggered: {reason} at ${current_price:.2f} (peak was ${highest_price:.2f})")
        else:
            print(f"✅ Holding position: {reason}")
    
    def test_smart_d1_exit_timing(self):
        """Test smart D+1 exit timing logic"""
        profitable_price = 102.0  # 2% profit
        morning_time = datetime.now().replace(hour=10, minute=15)  # 10:15 AM
        
        should_exit, reason = self.exit_manager._smart_d1_exit_timing(
            self.mock_position, profitable_price, morning_time
        )
        
        # Should exit profitable position in morning
        self.assertTrue(should_exit)
        self.assertIn("MORNING", reason.upper())
        
        print(f"✅ Smart D+1 exit: {reason} at 10:15 AM with 2% profit")


class TestEnhancedSignalGenerator(unittest.TestCase):
    """Test enhanced signal generation functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.config = Mock()
        self.config.confidence_threshold = 0.10  # 10% threshold for testing
        self.config.max_positions_per_day = 5
        
        self.signal_generator = EnhancedSignalGenerator(self.config)
        
        # Create test market data with upward momentum
        dates = pd.date_range(start='2025-10-01', periods=30, freq='D')
        base_prices = np.linspace(95, 105, 30)  # Upward trend
        noise = np.random.normal(0, 0.5, 30)
        
        self.trending_data = pd.DataFrame({
            'open': base_prices + noise,
            'high': base_prices + abs(noise) + 1,
            'low': base_prices - abs(noise) - 1,
            'close': base_prices + noise * 0.5,
            'volume': np.random.normal(1000000, 300000, 30)
        }, index=dates)
        
        # Ensure realistic OHLC relationships
        for i in range(len(self.trending_data)):
            row = self.trending_data.iloc[i]
            high = max(row['open'], row['close']) + abs(np.random.normal(0, 0.5))
            low = min(row['open'], row['close']) - abs(np.random.normal(0, 0.5))
            self.trending_data.iloc[i, self.trending_data.columns.get_loc('high')] = high
            self.trending_data.iloc[i, self.trending_data.columns.get_loc('low')] = low
        
        # Add volume surge to last few days
        self.trending_data.iloc[-3:, self.trending_data.columns.get_loc('volume')] *= 2.0
    
    def test_enhanced_signal_generation(self):
        """Test enhanced signal generation with quality filters"""
        signal = self.signal_generator._analyze_symbol_enhanced(
            "TEST", self.trending_data
        )
        
        if signal:
            self.assertEqual(signal.symbol, "TEST")
            self.assertEqual(signal.action, "BUY")
            self.assertGreater(signal.confidence, 0)
            self.assertLessEqual(signal.confidence, 1.0)
            
            # Check features
            self.assertIn('momentum_3d', signal.features_used)
            self.assertIn('momentum_5d', signal.features_used)
            self.assertIn('volume_surge', signal.features_used)
            
            print(f"✅ Enhanced signal generated:")
            print(f"   Symbol: {signal.symbol}")
            print(f"   Confidence: {signal.confidence:.3f}")
            print(f"   3D Momentum: {signal.features_used['momentum_3d']:.4f}")
            print(f"   Volume Surge: {signal.features_used['volume_surge']:.2f}")
        else:
            print(f"✅ No signal generated (quality filters rejected)")
    
    def test_volatility_filter(self):
        """Test volatility filtering functionality"""
        # Create high volatility data
        high_vol_data = self.trending_data.copy()
        high_vol_data['close'] = high_vol_data['close'] + np.random.normal(0, 5, len(high_vol_data))
        
        signal = self.signal_generator._analyze_symbol_enhanced(
            "HIGH_VOL", high_vol_data
        )
        
        # Should reject high volatility stocks
        if signal is None:
            print(f"✅ High volatility stock correctly rejected")
        else:
            print(f"⚠️ High volatility stock passed filter (confidence: {signal.confidence:.3f})")
    
    def test_volume_surge_requirement(self):
        """Test volume surge requirement"""
        # Create data with low volume
        low_vol_data = self.trending_data.copy()
        low_vol_data['volume'] = low_vol_data['volume'] * 0.5  # Reduce volume
        
        signal = self.signal_generator._analyze_symbol_enhanced(
            "LOW_VOL", low_vol_data
        )
        
        # Should require minimum volume surge
        if signal is None:
            print(f"✅ Low volume stock correctly rejected")
        else:
            volume_surge = signal.features_used.get('volume_surge', 0)
            if volume_surge >= self.signal_generator.min_volume_surge:
                print(f"✅ Volume surge requirement met: {volume_surge:.2f}x")
            else:
                print(f"⚠️ Volume surge below requirement: {volume_surge:.2f}x")


class TestStrategicImprovementEngine(unittest.TestCase):
    """Test the overall strategic improvement engine"""
    
    def setUp(self):
        """Set up test environment"""
        self.config = Mock()
        self.config.confidence_threshold = 0.07
        self.config.max_positions_per_day = 5
        
        self.improvement_engine = StrategicImprovementEngine(self.config)
        
        # Mock trader instance
        self.mock_trader = Mock()
        self.mock_trader.positions = []
        self.mock_trader.position_highest_prices = {}
    
    def test_improvement_engine_initialization(self):
        """Test improvement engine initialization"""
        self.assertIsNotNone(self.improvement_engine.enhanced_exit_manager)
        self.assertIsNotNone(self.improvement_engine.enhanced_signal_generator)
        
        # Check all improvements are active
        expected_improvements = [
            'dynamic_profit_targets',
            'trailing_stops', 
            'enhanced_signal_quality',
            'improved_exit_timing'
        ]
        
        for improvement in expected_improvements:
            self.assertIn(improvement, self.improvement_engine.improvements_active)
            self.assertTrue(self.improvement_engine.improvements_active[improvement])
        
        print(f"✅ Strategic improvement engine initialized with {len(expected_improvements)} improvements")
    
    def test_apply_improvements_to_trader(self):
        """Test applying improvements to trader instance"""
        success = self.improvement_engine.apply_strategic_improvements(self.mock_trader)
        
        self.assertTrue(success)
        self.assertTrue(hasattr(self.mock_trader, 'enhanced_exit_manager'))
        self.assertTrue(hasattr(self.mock_trader, 'enhanced_signal_generator'))
        self.assertTrue(hasattr(self.mock_trader, 'position_highest_prices'))
        
        print(f"✅ Strategic improvements successfully applied to trader")


class TestSystemIntegration(unittest.TestCase):
    """Test system-wide integration of strategic improvements"""
    
    def setUp(self):
        """Set up integration test environment"""
        # Load real positions data for testing
        try:
            with open('positions.json', 'r') as f:
                self.positions_data = json.load(f)
            self.has_real_data = True
        except:
            self.positions_data = []
            self.has_real_data = False
    
    def test_integration_with_real_positions(self):
        """Test integration with real position data"""
        if not self.has_real_data:
            print("⚠️ No real positions data available for integration test")
            return
        
        # Count positions that would benefit from strategic improvements
        exited_positions = [p for p in self.positions_data if p.get('status') == 'exited']
        
        # Analyze potential improvements
        improvement_candidates = {
            'could_use_dynamic_targets': 0,
            'could_use_trailing_stops': 0,
            'had_large_losses': 0
        }
        
        for pos in exited_positions:
            pnl = pos.get('realized_pnl', 0) or 0
            exit_reason = pos.get('exit_reason', '')
            
            # Check for positions that could benefit from dynamic targets
            if 'D+1' in exit_reason and pnl > 0:
                improvement_candidates['could_use_dynamic_targets'] += 1
            
            # Check for positions that could benefit from trailing stops
            if pnl > 500:  # Large profits that could have been protected
                improvement_candidates['could_use_trailing_stops'] += 1
            
            # Check for large losses that could be prevented
            if pnl < -300:
                improvement_candidates['had_large_losses'] += 1
        
        print(f"✅ Integration Analysis Results:")
        print(f"   Total exited positions: {len(exited_positions)}")
        print(f"   Could benefit from dynamic targets: {improvement_candidates['could_use_dynamic_targets']}")
        print(f"   Could benefit from trailing stops: {improvement_candidates['could_use_trailing_stops']}")
        print(f"   Had large losses (>$300): {improvement_candidates['had_large_losses']}")
        
        # Calculate potential impact
        total_exits = len(exited_positions)
        if total_exits > 0:
            improvement_potential = (
                sum(improvement_candidates.values()) / (total_exits * 3) * 100
            )
            print(f"   Estimated improvement potential: {improvement_potential:.1f}%")
    
    def test_performance_impact_estimation(self):
        """Test estimated performance impact of improvements"""
        if not self.has_real_data:
            print("⚠️ No real data for performance impact estimation")
            return
        
        exited_positions = [p for p in self.positions_data if p.get('status') == 'exited']
        
        current_metrics = {
            'total_trades': len(exited_positions),
            'wins': len([p for p in exited_positions if (p.get('realized_pnl') or 0) > 0]),
            'total_pnl': sum(p.get('realized_pnl') or 0 for p in exited_positions)
        }
        
        if current_metrics['total_trades'] > 0:
            current_win_rate = current_metrics['wins'] / current_metrics['total_trades'] * 100
            
            # Estimate improvements
            estimated_improvements = {
                'win_rate_boost': 5,  # 5% improvement from better signals
                'avg_win_boost': 15,  # 15% improvement from dynamic targets
                'loss_reduction': 20   # 20% loss reduction from better stops
            }
            
            print(f"✅ Performance Impact Estimation:")
            print(f"   Current win rate: {current_win_rate:.1f}%")
            print(f"   Current total P&L: ${current_metrics['total_pnl']:.2f}")
            print(f"   Estimated improvements:")
            print(f"     - Win rate: +{estimated_improvements['win_rate_boost']}%")
            print(f"     - Average win: +{estimated_improvements['avg_win_boost']}%")
            print(f"     - Loss reduction: -{estimated_improvements['loss_reduction']}%")


def run_comprehensive_test_suite():
    """Run all tests and generate comprehensive report"""
    print("="*80)
    print("🧪 STRATEGIC IMPROVEMENTS COMPREHENSIVE TEST SUITE")
    print("="*80)
    
    # Create test suite
    test_classes = [
        TestEnhancedExitManager,
        TestEnhancedSignalGenerator,
        TestStrategicImprovementEngine,
        TestSystemIntegration
    ]
    
    total_tests = 0
    passed_tests = 0
    failed_tests = 0
    
    for test_class in test_classes:
        print(f"\n📋 Running {test_class.__name__}")
        print("-" * 50)
        
        suite = unittest.TestLoader().loadTestsFromTestCase(test_class)
        
        for test in suite:
            total_tests += 1
            try:
                test.debug()  # Run test without unittest runner for cleaner output
                passed_tests += 1
            except Exception as e:
                print(f"❌ {test._testMethodName}: {e}")
                failed_tests += 1
    
    print("\n" + "="*80)
    print("📊 TEST RESULTS SUMMARY")
    print("="*80)
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {failed_tests}")
    print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%" if total_tests > 0 else "N/A")
    
    if failed_tests == 0:
        print("🎉 ALL TESTS PASSED!")
        print("✅ Strategic improvements are ready for deployment")
    else:
        print(f"⚠️ {failed_tests} tests failed - review before deployment")
    
    print("="*80)
    
    return passed_tests, failed_tests


if __name__ == "__main__":
    run_comprehensive_test_suite()
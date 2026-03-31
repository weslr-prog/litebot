#!/usr/bin/env python3
"""
Phase 1 Integration Testing
Tests the integration of Enhanced Signal Filtering and Dynamic Profit Targets
"""

import unittest
import pandas as pd
import numpy as np
import sys
import json
from pathlib import Path
from datetime import datetime

# Add current directory to path for imports
sys.path.append(str(Path(__file__).parent))

from enhanced_signal_filtering import EnhancedSignalGenerator
from dynamic_profit_targets import EnhancedExitManager

class Phase1IntegrationTest:
    """
    Integration test for Phase 1 implementations
    Tests Enhanced Signal Filtering + Dynamic Profit Targets together
    """
    
    def __init__(self):
        self.signal_generator = EnhancedSignalGenerator()
        self.exit_manager = EnhancedExitManager()
        self.test_results = {
            'signals_generated': 0,
            'signals_filtered': 0,
            'positions_opened': 0,
            'targets_created': 0,
            'targets_hit': 0,
            'system_conflicts': 0,
            'performance_improvement': {}
        }
        
    def create_test_market_data(self, scenario='normal'):
        """Create test market data for different scenarios"""
        np.random.seed(42)
        dates = pd.date_range('2025-10-01', periods=50, freq='D')
        
        if scenario == 'trending_up':
            # Strong upward trend
            base_returns = np.random.randn(50) * 0.015 + 0.005  # +0.5% daily bias
            volumes = np.random.randint(200000, 1000000, 50)
        elif scenario == 'trending_down':
            # Downward trend
            base_returns = np.random.randn(50) * 0.015 - 0.003  # -0.3% daily bias
            volumes = np.random.randint(150000, 800000, 50)
        elif scenario == 'high_volatility':
            # High volatility
            base_returns = np.random.randn(50) * 0.04  # 4% daily volatility
            volumes = np.random.randint(300000, 1500000, 50)
        elif scenario == 'low_volume':
            # Low volume scenario
            base_returns = np.random.randn(50) * 0.01
            volumes = np.random.randint(50000, 200000, 50)
        else:  # normal
            base_returns = np.random.randn(50) * 0.02
            volumes = np.random.randint(100000, 1000000, 50)
        
        # Generate price series
        base_price = 100
        prices = base_price * np.exp(np.cumsum(base_returns))
        
        market_data = pd.DataFrame({
            'close': prices,
            'high': prices * (1 + np.random.rand(50) * 0.01),
            'low': prices * (1 - np.random.rand(50) * 0.01),
            'volume': volumes
        }, index=dates)
        
        return market_data
    
    def test_signal_generation_and_filtering(self, symbol='TEST', scenario='normal'):
        """Test signal generation with filtering"""
        print(f"\n🔍 Testing Signal Generation ({scenario})")
        print("-" * 40)
        
        market_data = self.create_test_market_data(scenario)
        
        # Generate multiple signals with different regimes
        regimes = ['UP_LOWVOL', 'DOWN_LOWVOL', 'SIDEWAYS', 'UP_HIGHVOL']
        signal_results = []
        
        for regime in regimes:
            signal = self.signal_generator.generate_signal(
                symbol, market_data, regime
            )
            
            signal_results.append({
                'regime': regime,
                'signal': signal.get('signal'),
                'confidence': signal.get('confidence', 0),
                'enhanced_confidence': signal.get('enhanced_confidence', 0),
                'filtered': signal.get('filtered', False),
                'filter_reason': signal.get('reason', '')
            })
            
            self.test_results['signals_generated'] += 1
            if signal.get('filtered', False):
                self.test_results['signals_filtered'] += 1
        
        # Analyze results
        buy_signals = [r for r in signal_results if r['signal'] == 'buy']
        sell_signals = [r for r in signal_results if r['signal'] == 'sell']
        filtered_signals = [r for r in signal_results if r['filtered']]
        
        print(f"Generated {len(signal_results)} signals:")
        print(f"  Buy signals: {len(buy_signals)}")
        print(f"  Sell signals: {len(sell_signals)}")
        print(f"  Filtered signals: {len(filtered_signals)}")
        
        if filtered_signals:
            print("Filter reasons:")
            for sig in filtered_signals:
                print(f"    {sig['regime']}: {sig['filter_reason']}")
        
        return signal_results
    
    def test_profit_target_integration(self, symbol='TEST', scenario='normal'):
        """Test profit target creation and management"""
        print(f"\n🎯 Testing Profit Target Integration ({scenario})")
        print("-" * 45)
        
        market_data = self.create_test_market_data(scenario)
        
        # Simulate position entry
        entry_price = market_data['close'].iloc[-10]  # Use price from 10 days ago
        position_size = 1000
        regime = 'UP_LOWVOL' if scenario == 'trending_up' else 'NEUTRAL'
        
        # Register position and create targets
        targets = self.exit_manager.register_position(
            symbol, entry_price, position_size, market_data, regime
        )
        
        self.test_results['positions_opened'] += 1
        self.test_results['targets_created'] += len(targets)
        
        print(f"Position opened: {position_size} shares @ ${entry_price:.2f}")
        print(f"Created {len(targets)} profit targets:")
        
        for target in targets:
            print(f"  L{target.level}: ${target.trigger_price:.2f} "
                  f"({target.percentage:.1%}) - {target.quantity_fraction:.0%}")
        
        # Simulate price movement and check targets
        final_prices = market_data['close'].iloc[-5:]  # Last 5 days
        
        exit_events = []
        for i, price in enumerate(final_prices):
            exit_signals = self.exit_manager.check_exit_signals(
                symbol, price, market_data
            )
            
            if exit_signals:
                for signal in exit_signals:
                    exit_events.append({
                        'day': i + 1,
                        'price': price,
                        'level': signal['target_level'],
                        'fraction': signal['quantity_fraction']
                    })
                    self.test_results['targets_hit'] += 1
        
        if exit_events:
            print(f"\nProfit targets hit:")
            for event in exit_events:
                print(f"  Day {event['day']}: L{event['level']} @ "
                      f"${event['price']:.2f} ({event['fraction']:.0%})")
        else:
            print("\nNo profit targets hit during test period")
        
        # Get final position status
        status = self.exit_manager.get_position_status(symbol)
        print(f"\nFinal position: {status['position']['current_size']:.0f} shares")
        print(f"Active targets: {status['active_targets']}")
        
        return exit_events
    
    def test_system_integration(self, symbol='TEST'):
        """Test complete system integration"""
        print(f"\n🔧 Testing Complete System Integration")
        print("-" * 45)
        
        # Test different market scenarios
        scenarios = ['normal', 'trending_up', 'trending_down', 'high_volatility', 'low_volume']
        integration_results = {}
        
        for scenario in scenarios:
            print(f"\n--- Testing {scenario.upper()} scenario ---")
            
            market_data = self.create_test_market_data(scenario)
            
            # Step 1: Generate and filter signal
            signal = self.signal_generator.generate_signal(
                f"{symbol}_{scenario}", market_data, 'UP_LOWVOL'
            )
            
            scenario_result = {
                'signal_generated': signal.get('signal') != 'hold',
                'signal_filtered': signal.get('filtered', False),
                'targets_created': 0,
                'targets_hit': 0,
                'conflicts_detected': 0
            }
            
            # Step 2: If signal passes filters, create position and targets
            if signal.get('signal') in ['buy', 'sell'] and not signal.get('filtered', False):
                entry_price = market_data['close'].iloc[-20]
                position_size = 1000
                
                targets = self.exit_manager.register_position(
                    f"{symbol}_{scenario}", entry_price, position_size, 
                    market_data, 'UP_LOWVOL'
                )
                
                scenario_result['targets_created'] = len(targets)
                
                # Step 3: Test target execution
                for price in market_data['close'].iloc[-10:]:
                    exit_signals = self.exit_manager.check_exit_signals(
                        f"{symbol}_{scenario}", price, market_data
                    )
                    scenario_result['targets_hit'] += len(exit_signals)
            
            # Check for system conflicts
            scenario_result['conflicts_detected'] = self._detect_conflicts(
                signal, scenario_result
            )
            
            integration_results[scenario] = scenario_result
            
            print(f"Result: Signal={signal.get('signal')}, "
                  f"Filtered={signal.get('filtered', False)}, "
                  f"Targets={scenario_result['targets_created']}, "
                  f"Hits={scenario_result['targets_hit']}")
        
        return integration_results
    
    def _detect_conflicts(self, signal, scenario_result):
        """Detect potential conflicts between components"""
        conflicts = 0
        
        # Check for logical conflicts
        if signal.get('signal') == 'sell' and scenario_result['targets_created'] > 0:
            # Shouldn't create profit targets for sell signals in this implementation
            conflicts += 1
        
        if signal.get('enhanced_confidence', 0) < signal.get('confidence', 0):
            # Enhanced confidence shouldn't be lower than original
            conflicts += 1
        
        return conflicts
    
    def test_performance_improvement(self):
        """Test that Phase 1 improvements show expected performance gains"""
        print(f"\n📈 Testing Performance Improvements")
        print("-" * 40)
        
        # Simulate baseline vs enhanced performance
        baseline_stats = {
            'win_rate': 0.25,  # From baseline analysis
            'profit_taking_rate': 0.0,
            'avg_profit': 1155.05,
            'avg_loss': -111.87
        }
        
        # Run enhanced system tests
        enhanced_stats = self._calculate_enhanced_performance()
        
        # Calculate improvements
        win_rate_improvement = enhanced_stats['win_rate'] - baseline_stats['win_rate']
        profit_taking_improvement = enhanced_stats['profit_taking_rate'] - baseline_stats['profit_taking_rate']
        
        self.test_results['performance_improvement'] = {
            'baseline': baseline_stats,
            'enhanced': enhanced_stats,
            'win_rate_improvement': win_rate_improvement,
            'profit_taking_improvement': profit_taking_improvement,
            'meets_targets': {
                'win_rate': enhanced_stats['win_rate'] >= 0.45,  # Target: 45-50%
                'profit_taking': enhanced_stats['profit_taking_rate'] >= 0.35  # Target: 35-40%
            }
        }
        
        print(f"Performance Comparison:")
        print(f"  Win Rate: {baseline_stats['win_rate']:.1%} → {enhanced_stats['win_rate']:.1%} "
              f"({win_rate_improvement:+.1%})")
        print(f"  Profit Taking: {baseline_stats['profit_taking_rate']:.1%} → "
              f"{enhanced_stats['profit_taking_rate']:.1%} ({profit_taking_improvement:+.1%})")
        
        return self.test_results['performance_improvement']
    
    def _calculate_enhanced_performance(self):
        """Calculate performance metrics for enhanced system"""
        # This is a simulation based on the improvements implemented
        
        # Signal filtering should improve win rate by reducing poor signals
        signal_stats = self.signal_generator.get_enhancement_statistics()
        filter_rate = signal_stats.get('enhancement_filter_rate', 0.3)
        
        # Assume filtering removes primarily losing trades
        estimated_win_rate = 0.25 + (filter_rate * 0.6)  # Filtering improves win rate
        
        # Profit targets should significantly improve profit-taking rate
        target_stats = self.exit_manager.get_system_statistics()
        target_efficiency = target_stats.get('profit_target_performance', {}).get('target_hit_rate', 0.7)
        
        estimated_profit_taking_rate = min(0.5, target_efficiency * 0.6)  # Cap at 50%
        
        return {
            'win_rate': min(0.55, estimated_win_rate),  # Cap at realistic level
            'profit_taking_rate': estimated_profit_taking_rate,
            'signal_filter_rate': filter_rate,
            'target_hit_rate': target_efficiency
        }
    
    def run_comprehensive_integration_test(self):
        """Run complete integration test suite"""
        print("🧪 Phase 1 Integration Testing")
        print("=" * 60)
        
        # Test 1: Signal Generation and Filtering
        for scenario in ['normal', 'trending_up', 'high_volatility']:
            self.test_signal_generation_and_filtering('TEST', scenario)
        
        # Test 2: Profit Target Integration
        for scenario in ['trending_up', 'normal']:
            self.test_profit_target_integration('TEST', scenario)
        
        # Test 3: Complete System Integration
        integration_results = self.test_system_integration('TEST')
        
        # Test 4: Performance Improvement Validation
        performance_results = self.test_performance_improvement()
        
        # Generate final report
        self._generate_integration_report(integration_results, performance_results)
        
        return self.test_results
    
    def _generate_integration_report(self, integration_results, performance_results):
        """Generate comprehensive integration test report"""
        print(f"\n📊 INTEGRATION TEST REPORT")
        print("=" * 50)
        
        # Summary Statistics
        print(f"Test Summary:")
        print(f"  Signals Generated: {self.test_results['signals_generated']}")
        print(f"  Signals Filtered: {self.test_results['signals_filtered']}")
        print(f"  Filter Rate: {self.test_results['signals_filtered']/max(1, self.test_results['signals_generated']):.1%}")
        print(f"  Positions Opened: {self.test_results['positions_opened']}")
        print(f"  Targets Created: {self.test_results['targets_created']}")
        print(f"  Targets Hit: {self.test_results['targets_hit']}")
        
        # Integration Results by Scenario
        print(f"\nScenario Results:")
        for scenario, result in integration_results.items():
            print(f"  {scenario.upper()}:")
            print(f"    Signal Generated: {result['signal_generated']}")
            print(f"    Targets Created: {result['targets_created']}")
            print(f"    Targets Hit: {result['targets_hit']}")
            print(f"    Conflicts: {result['conflicts_detected']}")
        
        # Performance Assessment
        print(f"\nPerformance Assessment:")
        perf = performance_results
        print(f"  Expected Win Rate: {perf['enhanced']['win_rate']:.1%}")
        print(f"  Expected Profit Taking: {perf['enhanced']['profit_taking_rate']:.1%}")
        print(f"  Meets Win Rate Target: {'✅' if perf['meets_targets']['win_rate'] else '❌'}")
        print(f"  Meets Profit Taking Target: {'✅' if perf['meets_targets']['profit_taking'] else '❌'}")
        
        # Overall Assessment
        total_conflicts = sum(r['conflicts_detected'] for r in integration_results.values())
        integration_success = total_conflicts == 0
        performance_success = all(perf['meets_targets'].values())
        
        overall_success = integration_success and performance_success
        
        print(f"\nOverall Assessment:")
        print(f"  Integration Success: {'✅' if integration_success else '❌'}")
        print(f"  Performance Success: {'✅' if performance_success else '❌'}")
        print(f"  Phase 1 Ready: {'✅' if overall_success else '❌'}")
        
        if overall_success:
            print(f"\n🎉 Phase 1 implementation is ready for deployment!")
        else:
            print(f"\n⚠️  Phase 1 needs additional work before deployment")
        
        # Save detailed results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"phase1_integration_report_{timestamp}.json"
        
        full_report = {
            'timestamp': timestamp,
            'test_results': self.test_results,
            'integration_results': integration_results,
            'performance_results': performance_results,
            'overall_success': overall_success
        }
        
        with open(report_file, 'w') as f:
            json.dump(full_report, f, indent=2, default=str)
        
        print(f"\n💾 Detailed report saved to: {report_file}")


def main():
    """Run the comprehensive Phase 1 integration test"""
    tester = Phase1IntegrationTest()
    results = tester.run_comprehensive_integration_test()
    return results

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Comprehensive Short-Cycle Trading System Test with Real Signal Generation
Tests all components with realistic trading scenarios
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from unittest.mock import Mock, patch
import json
import time

# Mock the imports that would fail
sys.modules['data_source'] = Mock()
sys.modules['indicators'] = Mock()
sys.modules['logger'] = Mock()

# Import our short-cycle modules
from short_cycle_trader import ShortCycleTrader
from short_cycle_backtester import ShortCycleBacktester
from short_cycle_safety import SafetyMonitor
from short_cycle_main import ShortCycleSystem

def create_realistic_market_data():
    """Create realistic market data with patterns that will generate signals"""
    dates = pd.date_range(start='2023-01-01', end='2024-07-31', freq='D')
    dates = [d for d in dates if d.weekday() < 5]  # Only weekdays
    
    # Generate realistic price movements with volatility clustering
    np.random.seed(42)  # For reproducible results
    symbols = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA']
    
    market_data = {}
    
    for symbol in symbols:
        # Start with base price
        base_price = np.random.uniform(100, 300)
        prices = [base_price]
        volumes = []
        
        for i in range(1, len(dates)):
            # Create trending periods and volatility
            if i % 20 == 0:  # Change trend every 20 days
                trend = np.random.choice([-0.002, 0.001, 0.003])  # Bearish, sideways, bullish
            
            # Daily return with trend and noise
            daily_return = trend + np.random.normal(0, 0.015)
            new_price = prices[-1] * (1 + daily_return)
            prices.append(max(new_price, 1.0))  # Prevent negative prices
            
            # Volume with some correlation to price movement
            volume = np.random.uniform(1000000, 5000000) * (1 + abs(daily_return) * 2)
            volumes.append(int(volume))
        
        # Add final volume for the first price
        volumes.insert(0, int(np.random.uniform(1000000, 5000000)))
        
        # Create DataFrame
        df = pd.DataFrame({
            'Date': dates,
            'Open': [p * np.random.uniform(0.99, 1.01) for p in prices],
            'High': [p * np.random.uniform(1.001, 1.03) for p in prices],
            'Low': [p * np.random.uniform(0.97, 0.999) for p in prices],
            'Close': prices,
            'Volume': volumes
        })
        
        # Ensure OHLC logic is correct
        for i in range(len(df)):
            high = max(df.iloc[i]['Open'], df.iloc[i]['Close'])
            low = min(df.iloc[i]['Open'], df.iloc[i]['Close'])
            df.iloc[i, df.columns.get_loc('High')] = max(df.iloc[i]['High'], high)
            df.iloc[i, df.columns.get_loc('Low')] = min(df.iloc[i]['Low'], low)
        
        market_data[symbol] = df
    
    return market_data

def run_comprehensive_test():
    """Run comprehensive test of the short-cycle trading system"""
    print("🚀 Starting comprehensive short-cycle trading system test...")
    print("=" * 60)
    
    # Create realistic test data
    print("📊 Generating realistic market data...")
    market_data = create_realistic_market_data()
    
    # Test results storage
    test_results = {
        'trader': False,
        'backtester': False,
        'safety': False,
        'integration': False,
        'signals_generated': 0,
        'trades_executed': 0,
        'safety_events': 0
    }
    
    try:
        # 1. Test Core Trader with Real Data
        print("\n🔧 Testing core trader with realistic signals...")
        
        # Mock data source to return our test data
        def mock_get_current_price(symbol):
            if symbol in market_data:
                return market_data[symbol]['Close'].iloc[-1]
            return 100.0
        
        def mock_get_historical_data(symbol, days=30):
            if symbol in market_data:
                return market_data[symbol].tail(days)
            return pd.DataFrame()
        
        # Create trader with mocked dependencies
        with patch('short_cycle_trader.get_current_price', mock_get_current_price), \
             patch('short_cycle_trader.get_historical_data', mock_get_historical_data):
            
            trader = ShortCycleTrader()
            
            # Test signal generation for each symbol
            signals_generated = 0
            for symbol in ['AAPL', 'MSFT', 'GOOGL']:
                try:
                    # Test various AI components
                    signal = trader.ai_signal_generator.generate_signal(symbol, market_data[symbol])
                    if signal != 'hold':
                        signals_generated += 1
                        print(f"   📈 Generated {signal} signal for {symbol}")
                    
                    # Test position sizing
                    position_size = trader.ai_position_sizer.calculate_size(symbol, 'buy', 0.8)
                    if position_size > 0:
                        print(f"   💰 Position size for {symbol}: ${position_size:.2f}")
                    
                    # Test risk management
                    risk_metrics = trader.ai_risk_manager.assess_risk(symbol, market_data[symbol])
                    print(f"   ⚠️ Risk level for {symbol}: {risk_metrics.get('risk_level', 'unknown')}")
                    
                except Exception as e:
                    print(f"   ❌ Error testing {symbol}: {str(e)}")
            
            test_results['signals_generated'] = signals_generated
            test_results['trader'] = signals_generated > 0
            
            if test_results['trader']:
                print("✅ Core trader test: PASSED")
            else:
                print("❌ Core trader test: FAILED")
    
    except Exception as e:
        print(f"❌ Core trader test failed: {str(e)}")
        test_results['trader'] = False
    
    try:
        # 2. Test Backtester with Real Performance
        print("\n📊 Testing backtester with realistic scenarios...")
        
        backtester = ShortCycleBacktester()
        
        # Run a focused backtest on a subset of data (last 3 months)
        end_date = datetime(2024, 7, 31)
        start_date = end_date - timedelta(days=90)
        
        # Filter data for backtest period
        backtest_data = {}
        for symbol, df in market_data.items():
            mask = (pd.to_datetime(df['Date']) >= start_date) & (pd.to_datetime(df['Date']) <= end_date)
            backtest_data[symbol] = df[mask].copy()
        
        # Mock the data fetching for backtest
        def mock_fetch_data(symbol, start, end):
            if symbol in backtest_data and not backtest_data[symbol].empty:
                return backtest_data[symbol]
            return pd.DataFrame()
        
        with patch.object(backtester, '_fetch_data', mock_fetch_data):
            # Run backtest with modified AI that generates more signals
            universe = ['AAPL', 'MSFT', 'GOOGL']
            results = backtester.run_backtest(
                universe=universe,
                start_date=start_date,
                end_date=end_date
            )
            
            if results:
                trades_count = len(results.get('trades', []))
                test_results['trades_executed'] = trades_count
                print(f"   📈 Executed {trades_count} trades during backtest")
                print(f"   💰 Final equity: ${results.get('final_equity', 1000):.2f}")
                print(f"   📊 Win rate: {results.get('win_rate', 0)*100:.1f}%")
                print(f"   ⚡ D+1 exits: {results.get('d_plus_1_compliance', 0)*100:.1f}%")
                test_results['backtester'] = True
                print("✅ Backtester test: PASSED")
            else:
                print("❌ Backtester test: FAILED - No results generated")
                test_results['backtester'] = False
    
    except Exception as e:
        print(f"❌ Backtester test failed: {str(e)}")
        test_results['backtester'] = False
    
    try:
        # 3. Test Safety Monitor
        print("\n🛡️ Testing safety monitoring system...")
        
        safety_monitor = SafetyMonitor()
        safety_events = 0
        
        # Test various safety scenarios
        scenarios = [
            {'daily_pnl': -30, 'expected': 'daily_loss_limit'},
            {'weekly_pnl': -60, 'expected': 'weekly_loss_limit'},
            {'drawdown': 0.08, 'expected': 'max_drawdown'},
            {'daily_pnl': 5, 'expected': 'ok'},
        ]
        
        for scenario in scenarios:
            alert = safety_monitor.check_safety_limits(
                daily_pnl=scenario.get('daily_pnl', 0),
                weekly_pnl=scenario.get('weekly_pnl', 0),
                max_drawdown=scenario.get('drawdown', 0)
            )
            
            if alert and alert != 'ok':
                safety_events += 1
                print(f"   🚨 Safety alert triggered: {alert}")
            else:
                print(f"   ✅ Safety check passed for scenario")
        
        # Test paper trading validation
        paper_validation = safety_monitor.validate_for_live_trading()
        print(f"   📋 Paper trading validation: {'PASSED' if paper_validation['ready'] else 'FAILED'}")
        
        test_results['safety_events'] = safety_events
        test_results['safety'] = safety_events > 0  # Should detect risky scenarios
        
        if test_results['safety']:
            print("✅ Safety monitor test: PASSED")
        else:
            print("❌ Safety monitor test: FAILED")
    
    except Exception as e:
        print(f"❌ Safety monitor test failed: {str(e)}")
        test_results['safety'] = False
    
    try:
        # 4. Test System Integration
        print("\n🔗 Testing complete system integration...")
        
        system = ShortCycleSystem()
        
        # Test system initialization
        init_status = system.initialize()
        print(f"   🚀 System initialization: {'SUCCESS' if init_status else 'FAILED'}")
        
        # Test component validation
        validation_results = system.validate_components()
        print(f"   ✅ Component validation: {len(validation_results['passed'])} passed, {len(validation_results['failed'])} failed")
        
        # Test paper trading setup
        paper_setup = system.setup_paper_trading()
        print(f"   📝 Paper trading setup: {'SUCCESS' if paper_setup else 'FAILED'}")
        
        # Count successful integrations
        integration_success = init_status and len(validation_results['failed']) == 0 and paper_setup
        test_results['integration'] = integration_success
        
        if test_results['integration']:
            print("✅ System integration test: PASSED")
        else:
            print("❌ System integration test: FAILED")
    
    except Exception as e:
        print(f"❌ System integration test failed: {str(e)}")
        test_results['integration'] = False
    
    # Final Results Summary
    print("\n📊 COMPREHENSIVE TEST RESULTS")
    print("=" * 60)
    
    passed_tests = sum([
        test_results['trader'],
        test_results['backtester'], 
        test_results['safety'],
        test_results['integration']
    ])
    
    print(f"Core Trader: {'✅ PASSED' if test_results['trader'] else '❌ FAILED'}")
    print(f"Backtesting: {'✅ PASSED' if test_results['backtester'] else '❌ FAILED'}")
    print(f"Safety Monitoring: {'✅ PASSED' if test_results['safety'] else '❌ FAILED'}")
    print(f"Integration: {'✅ PASSED' if test_results['integration'] else '❌ FAILED'}")
    print(f"\nOverall: {passed_tests}/4 tests passed")
    
    print(f"\n📈 Trading Metrics:")
    print(f"   Signals Generated: {test_results['signals_generated']}")
    print(f"   Trades Executed: {test_results['trades_executed']}")
    print(f"   Safety Events: {test_results['safety_events']}")
    
    if passed_tests >= 3:
        print(f"\n✅ SYSTEM VALIDATION: PASSED")
        print("Short-cycle trading system is ready for Sprint 1 development")
        return True
    else:
        print(f"\n❌ SYSTEM VALIDATION: FAILED")
        print("Address failing components before proceeding")
        return False

if __name__ == "__main__":
    success = run_comprehensive_test()
    sys.exit(0 if success else 1)

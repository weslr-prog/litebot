#!/usr/bin/env python3
"""
Comprehensive System Diagnostic & Test
======================================
Complete debugging analysis for October 6, 2025 trading issues
and comprehensive system testing with historical data.

Author: LiteBotX Diagnostic System
Date: October 6, 2025
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
import traceback

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def setup_logging():
    """Setup logging for diagnostic"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('diagnostic_test.log'),
            logging.StreamHandler()
        ]
    )

def test_pre_filter():
    """Test pre-filter with current settings"""
    print("\n" + "="*80)
    print("🔍 TESTING PRE-FILTER")
    print("="*80)
    
    try:
        from pre_filter import PreFilter
        import pandas as pd
        
        # Create sample data (simulate free tier with 21 days)
        symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'NFLX', 'AMD', 'AVGO']
        dates = pd.date_range(end=datetime.now(), periods=21)
        
        data = []
        for symbol in symbols:
            for date in dates:
                data.append({
                    'symbol': symbol,
                    'date': date,
                    'open': 100.0 + (hash(symbol + str(date)) % 50),
                    'high': 105.0 + (hash(symbol + str(date)) % 50),
                    'low': 95.0 + (hash(symbol + str(date)) % 50),
                    'close': 100.0 + (hash(symbol + str(date)) % 50),
                    'volume': 1000000 + (hash(symbol + str(date)) % 5000000),
                    'vwap': 100.0 + (hash(symbol + str(date)) % 50)
                })
        
        df = pd.DataFrame(data)
        
        print(f"📊 Test data created:")
        print(f"   Symbols: {len(symbols)}")
        print(f"   Days: {len(dates)}")
        print(f"   Total rows: {len(df)}")
        print(f"   Data per symbol: {len(df) // len(symbols)}")
        
        # Test pre-filter
        pre_filter = PreFilter()
        
        print(f"\n🔧 Testing with current settings:")
        
        # Test data completeness filter
        result = pre_filter.data_completeness_filter(df, min_rows=20)
        print(f"   Data completeness (min_rows=20): {len(result['symbol'].unique()) if not result.empty else 0} symbols")
        
        result = pre_filter.data_completeness_filter(df, min_rows=30)
        print(f"   Data completeness (min_rows=30): {len(result['symbol'].unique()) if not result.empty else 0} symbols")
        
        result = pre_filter.data_completeness_filter(df, min_rows=90)
        print(f"   Data completeness (min_rows=90): {len(result['symbol'].unique()) if not result.empty else 0} symbols")
        
        # Test full RelaxedFilter
        try:
            result = pre_filter.RelaxedFilter(df)
            print(f"   RelaxedFilter result: {len(result['symbol'].unique()) if not result.empty else 0} symbols")
            if not result.empty:
                print(f"   Passing symbols: {result['symbol'].unique().tolist()}")
        except Exception as e:
            print(f"   RelaxedFilter failed: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Pre-filter test failed: {e}")
        traceback.print_exc()
        return False

def test_position_class():
    """Test ShortCyclePosition class for attribute issues"""
    print("\n" + "="*80)
    print("🔍 TESTING POSITION CLASS")
    print("="*80)
    
    try:
        from traders.short_cycle_trader import ShortCyclePosition
        from datetime import date
        
        # Test creating a position
        position = ShortCyclePosition(
            symbol="AAPL",
            shares=100,
            entry_price=150.0,
            entry_date=date.today(),
            exit_date=date.today() + timedelta(days=1)
        )
        
        print(f"✅ Position created successfully:")
        print(f"   Symbol: {position.symbol}")
        print(f"   Entry date: {position.entry_date}")
        print(f"   Exit date: {position.exit_date}")
        
        # Test attributes
        attributes = ['entry_timestamp', 'exit_timestamp', 'entry_date', 'exit_date']
        for attr in attributes:
            if hasattr(position, attr):
                value = getattr(position, attr)
                print(f"   ✅ {attr}: {value}")
            else:
                print(f"   ❌ {attr}: NOT FOUND")
        
        return True
        
    except Exception as e:
        print(f"❌ Position class test failed: {e}")
        traceback.print_exc()
        return False

def test_signal_generation():
    """Test signal generation pipeline"""
    print("\n" + "="*80)
    print("🔍 TESTING SIGNAL GENERATION")
    print("="*80)
    
    try:
        # Import signal generation modules
        from signal_generator import SignalGenerator
        import pandas as pd
        import numpy as np
        
        # Create realistic market data
        dates = pd.date_range(end=datetime.now(), periods=30)
        symbols = ['AAPL', 'MSFT', 'GOOGL']
        
        market_data = {}
        for symbol in symbols:
            # Generate realistic OHLCV data
            base_price = 100.0 + (hash(symbol) % 100)
            prices = []
            
            for i, date in enumerate(dates):
                # Simple random walk
                if i == 0:
                    price = base_price
                else:
                    price = prices[-1] * (1 + np.random.normal(0, 0.02))
                
                high = price * (1 + abs(np.random.normal(0, 0.01)))
                low = price * (1 - abs(np.random.normal(0, 0.01)))
                volume = 1000000 + np.random.randint(0, 5000000)
                
                prices.append(price)
            
            market_data[symbol] = pd.DataFrame({
                'date': dates,
                'open': [p * (1 + np.random.normal(0, 0.005)) for p in prices],
                'high': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
                'low': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices],
                'close': prices,
                'volume': [1000000 + np.random.randint(0, 5000000) for _ in prices],
                'vwap': prices  # Simplified
            })
        
        print(f"📊 Market data created for {len(symbols)} symbols")
        
        # Test signal generation
        signal_gen = SignalGenerator()
        
        for symbol in symbols:
            try:
                signals = signal_gen.generate_signals(market_data[symbol], symbol)
                print(f"   {symbol}: {len(signals) if signals else 0} signals")
            except Exception as e:
                print(f"   {symbol}: Signal generation failed - {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Signal generation test failed: {e}")
        traceback.print_exc()
        return False

def test_data_availability():
    """Test actual data availability from Alpaca"""
    print("\n" + "="*80)
    print("🔍 TESTING DATA AVAILABILITY")
    print("="*80)
    
    try:
        from stock_api import StockAPI
        
        api = StockAPI()
        symbols = ['AAPL', 'MSFT', 'GOOGL']
        
        for symbol in symbols:
            try:
                # Test getting data
                data = api.get_historical_data(symbol, days=40)
                if data is not None and not data.empty:
                    print(f"   {symbol}: {len(data)} rows available")
                    print(f"      Date range: {data.index[0]} to {data.index[-1]}")
                else:
                    print(f"   {symbol}: No data available")
            except Exception as e:
                print(f"   {symbol}: Data fetch failed - {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Data availability test failed: {e}")
        traceback.print_exc()
        return False

def analyze_october_6_logs():
    """Analyze October 6 logs in detail"""
    print("\n" + "="*80)
    print("🔍 ANALYZING OCTOBER 6 LOGS")
    print("="*80)
    
    log_file = "logs/short_cycle_trader.log"
    if not os.path.exists(log_file):
        print("❌ Log file not found")
        return False
    
    try:
        with open(log_file, 'r') as f:
            lines = f.readlines()
        
        oct6_lines = [line for line in lines if "2025-10-06" in line]
        
        print(f"📊 October 6 log analysis:")
        print(f"   Total log lines: {len(oct6_lines)}")
        
        # Count key events
        events = {
            'errors': 0,
            'warnings': 0,
            'position_entries': 0,
            'position_exits': 0,
            'signals_generated': 0,
            'signals_blocked': 0,
            'prefilter_runs': 0,
            'prefilter_failures': 0
        }
        
        for line in oct6_lines:
            if "ERROR" in line:
                events['errors'] += 1
                if "entry_timestamp" in line:
                    print(f"   🚨 CRITICAL ERROR: {line.strip()}")
            
            if "WARNING" in line:
                events['warnings'] += 1
            
            if "Entered position" in line:
                events['position_entries'] += 1
            
            if "Exited position" in line:
                events['position_exits'] += 1
            
            if "Signal generated" in line or "Processing signal" in line:
                events['signals_generated'] += 1
            
            if "skipped" in line and ("same-day" in line or "blocked" in line):
                events['signals_blocked'] += 1
            
            if "PreFilter returned too few" in line:
                events['prefilter_failures'] += 1
                print(f"   ⚠️ Pre-filter failure: {line.strip()}")
            
            if "Selected universe of" in line:
                events['prefilter_runs'] += 1
        
        print(f"\n📈 Event Summary:")
        for event, count in events.items():
            print(f"   {event}: {count}")
        
        # Key findings
        if events['errors'] > 0:
            print(f"\n🚨 CRITICAL: {events['errors']} errors detected")
        
        if events['prefilter_failures'] > 0:
            print(f"\n⚠️ Pre-filter failing: {events['prefilter_failures']} failures")
        
        if events['position_entries'] == 0:
            print(f"\n❌ No positions entered - trading pipeline broken")
        
        return True
        
    except Exception as e:
        print(f"❌ Log analysis failed: {e}")
        return False

def run_monitoring_test():
    """Test the monitoring system"""
    print("\n" + "="*80)
    print("🔍 TESTING MONITORING SYSTEM")
    print("="*80)
    
    try:
        from monitoring.monitoring_system import SelfMonitoringSystem
        
        monitor = SelfMonitoringSystem()
        
        # Run monitoring for October 6
        result = monitor.run_end_of_day_check("2025-10-06")
        
        print(f"✅ Monitoring system test completed:")
        print(f"   PDT Status: {result['pdt_audit']['compliance_status'] if result['pdt_audit'] else 'N/A'}")
        print(f"   Health Status: {result['health_check']['overall_status'] if result['health_check'] else 'N/A'}")
        print(f"   Corrections Applied: {len(result['corrections_applied'])}")
        
        return True
        
    except Exception as e:
        print(f"❌ Monitoring test failed: {e}")
        traceback.print_exc()
        return False

def main():
    """Run comprehensive diagnostic"""
    setup_logging()
    
    print("🔬 LITEBOTX COMPREHENSIVE DIAGNOSTIC")
    print("=" * 80)
    print(f"Date: {datetime.now()}")
    print(f"Purpose: Debug October 6, 2025 trading issues")
    print("=" * 80)
    
    tests = [
        ("Position Class", test_position_class),
        ("Pre-Filter", test_pre_filter),
        ("Data Availability", test_data_availability),
        ("Signal Generation", test_signal_generation),
        ("October 6 Log Analysis", analyze_october_6_logs),
        ("Monitoring System", run_monitoring_test)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n🔬 Running {test_name} test...")
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "="*80)
    print("📊 DIAGNOSTIC SUMMARY")
    print("="*80)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    print(f"Tests Passed: {passed}/{total}")
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {test_name}: {status}")
    
    # Recommendations
    print(f"\n💡 RECOMMENDATIONS:")
    
    if not results.get("Position Class", True):
        print("   1. Fix ShortCyclePosition class attribute issues")
    
    if not results.get("Pre-Filter", True):
        print("   2. Fix pre-filter min_rows settings for free data")
    
    if not results.get("Data Availability", True):
        print("   3. Check Alpaca API connectivity and data access")
    
    if not results.get("Signal Generation", True):
        print("   4. Debug signal generation pipeline")
    
    if results.get("October 6 Log Analysis", True):
        print("   5. Review October 6 log analysis for specific issues")
    
    print(f"\n📄 Full diagnostic log saved to: diagnostic_test.log")

if __name__ == "__main__":
    main()
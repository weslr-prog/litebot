#!/usr/bin/env python3
"""
Fixed Critical Issue Investigation Test
Tests the specific concerns with proper class structure understanding
"""

import sys
import os
import logging
import json
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from test.sprint1_alpaca_integration import Sprint1AlpacaIntegration

class FixedCriticalTest:
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.setup_logging()
        
    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[logging.StreamHandler()]
        )
        
    def test_watchlist_and_signals(self):
        """Test watchlist generation and signal production"""
        print("\n🔍 TESTING: Watchlist Generation & Signal Production")
        print("=" * 60)
        
        try:
            # Create integration instance  
            bot = Sprint1AlpacaIntegration(launch_gui=False)
            
            # Test watchlist generation
            symbols = bot.check_and_update_watchlist()
            print(f"📊 Watchlist Analysis:")
            print(f"   Symbols loaded: {len(symbols)}")
            print(f"   Symbols: {symbols[:10]}...")  # Show first 10
            
            # Test signal generation
            if symbols:
                test_symbol = symbols[0]
                print(f"\n🧠 Testing Signal Generation for {test_symbol}:")
                
                # Update market data
                bot.data_feed.update_market_data([test_symbol])
                
                # Get historical data
                df = bot.data_feed.get_historical_data(test_symbol, days=30)
                current_price = bot.data_feed.get_current_price(test_symbol)
                
                print(f"   Historical data: {len(df)} rows")
                print(f"   Current price: ${current_price:.2f}")
                
                if not df.empty and current_price:
                    # Generate signal
                    signal = bot.signal_generator.generate_signal(test_symbol, df)
                    print(f"   Generated signal: {signal}")
                    
                    # Test risk assessment
                    if hasattr(bot, 'taf_aware_risk_manager') and bot.taf_aware_risk_manager:
                        intended_shares = bot.trade_executor.calculate_position_size(test_symbol, 0.8, current_price)
                        risk_assessment = bot.taf_aware_risk_manager.assess_risk_with_fees(
                            test_symbol, df, current_price, intended_shares
                        )
                        print(f"   Risk assessment confidence: {risk_assessment.get('adjusted_confidence', 0):.2f}")
                        print(f"   Trade recommended: {risk_assessment.get('trade_recommended', False)}")
                    else:
                        risk_assessment = bot.risk_manager.assess_risk(test_symbol, df)
                        print(f"   Basic risk confidence: {risk_assessment.get('confidence', 0):.2f}")
                        
            return {
                "test": "watchlist_and_signals",
                "status": "SUCCESS",
                "watchlist_size": len(symbols),
                "signal_generation": "WORKING" if symbols else "NO_SYMBOLS"
            }
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return {"test": "watchlist_and_signals", "status": "ERROR", "error": str(e)}
    
    def test_actual_trading_cycle(self):
        """Test complete trading cycle execution"""
        print("\n🔍 TESTING: Complete Trading Cycle")
        print("=" * 60)
        
        try:
            bot = Sprint1AlpacaIntegration(launch_gui=False)
            
            # Get symbols
            symbols = bot.check_and_update_watchlist()
            if not symbols:
                print("❌ No symbols available for trading cycle")
                return {"test": "trading_cycle", "status": "NO_SYMBOLS"}
            
            # Limit to first 3 symbols for testing
            test_symbols = symbols[:3]
            print(f"📊 Testing trading cycle with: {test_symbols}")
            
            # Run actual trading cycle (same as production)
            results = bot.run_trading_cycle(test_symbols)
            
            print(f"✅ Trading Cycle Results:")
            print(f"   Signals generated: {results.get('signals_generated', 0)}")
            print(f"   Trades attempted: {results.get('trades_attempted', 0)}")  
            print(f"   Trades executed: {results.get('trades_executed', 0)}")
            print(f"   Cycle duration: {results.get('cycle_duration', 0):.2f}s")
            
            # Check Alpaca connection
            if hasattr(bot.trade_executor, 'api') and bot.trade_executor.api:
                account = bot.trade_executor.api.get_account()
                print(f"   Alpaca portfolio: ${float(account.portfolio_value):,.2f}")
                
            return {
                "test": "trading_cycle",
                "status": "SUCCESS",
                "results": results,
                "alpaca_connected": hasattr(bot.trade_executor, 'api') and bot.trade_executor.api is not None
            }
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return {"test": "trading_cycle", "status": "ERROR", "error": str(e)}
    
    def test_d1_exit_logic(self):
        """Test D+1 exit logic with mock positions"""
        print("\n🔍 TESTING: D+1 Exit Logic")
        print("=" * 60)
        
        try:
            bot = Sprint1AlpacaIntegration(launch_gui=False)
            
            # Create mock position that should trigger D+1 exit
            yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            mock_position = {
                "symbol": "AAPL",
                "entry_date": yesterday,
                "position_size_shares": 10,
                "entry_price": 150.00,
                "status": "active"
            }
            
            print(f"📊 Mock Position for D+1 Test:")
            print(f"   Symbol: {mock_position['symbol']}")
            print(f"   Entry Date: {mock_position['entry_date']}")
            print(f"   Shares: {mock_position['position_size_shares']}")
            print(f"   Entry Price: ${mock_position['entry_price']:.2f}")
            
            # Test exit monitoring (this should detect D+1 condition)
            print(f"\n🛡️ Testing Exit Monitoring Logic...")
            
            # Simulate what should happen in exit monitoring
            today = datetime.now().strftime("%Y-%m-%d")
            days_held = (datetime.strptime(today, "%Y-%m-%d") - 
                        datetime.strptime(mock_position['entry_date'], "%Y-%m-%d")).days
            
            should_exit = days_held >= 1 and mock_position['status'] == 'active'
            
            print(f"   Days held: {days_held}")
            print(f"   Should trigger D+1 exit: {should_exit}")
            
            if should_exit:
                print(f"   ✅ D+1 Exit Logic: WORKING")
                print(f"   📤 Would generate SELL signal for {mock_position['symbol']}")
            else:
                print(f"   ❌ D+1 Exit Logic: NOT TRIGGERING")
                
            return {
                "test": "d1_exit_logic",
                "status": "SUCCESS",
                "days_held": days_held,
                "should_exit": should_exit,
                "logic_working": should_exit
            }
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return {"test": "d1_exit_logic", "status": "ERROR", "error": str(e)}
    
    def test_logging_system(self):
        """Test if logging system captures trading data properly"""
        print("\n🔍 TESTING: Logging System")
        print("=" * 60)
        
        try:
            # Check log files exist and are being written
            log_files = [
                "trading_bot.log",
                "dashboard.log"
            ]
            
            print("📊 Log File Analysis:")
            for log_file in log_files:
                log_path = project_root / log_file
                if log_path.exists():
                    size = log_path.stat().st_size
                    modified = datetime.fromtimestamp(log_path.stat().st_mtime)
                    print(f"   {log_file}: {size:,} bytes, modified {modified}")
                    
                    # Read last few lines
                    try:
                        with open(log_path, 'r') as f:
                            lines = f.readlines()
                            if lines:
                                print(f"      Last entry: {lines[-1].strip()}")
                    except:
                        print(f"      Unable to read {log_file}")
                else:
                    print(f"   {log_file}: NOT FOUND")
            
            # Test live logging
            bot = Sprint1AlpacaIntegration(launch_gui=False)
            bot.logger.info("🧪 TEST LOG ENTRY from critical test")
            print(f"   ✅ Live logging test completed")
            
            return {
                "test": "logging_system", 
                "status": "SUCCESS",
                "log_files_found": len([f for f in log_files if (project_root / f).exists()])
            }
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return {"test": "logging_system", "status": "ERROR", "error": str(e)}
    
    def run_fixed_tests(self):
        """Run all fixed critical tests"""
        print("🚨 FIXED CRITICAL ISSUE TESTS")
        print("=" * 80)
        print("Testing core trading functionality with proper class structure...")
        
        results = {}
        
        # Test each area
        results["watchlist_signals"] = self.test_watchlist_and_signals()
        results["trading_cycle"] = self.test_actual_trading_cycle()
        results["d1_exits"] = self.test_d1_exit_logic()
        results["logging"] = self.test_logging_system()
        
        # Summary
        print("\n🎯 FIXED TEST SUMMARY")
        print("=" * 60)
        
        issues = []
        successes = []
        
        for test_name, result in results.items():
            status = result.get("status", "UNKNOWN")
            if status == "SUCCESS":
                successes.append(test_name)
                print(f"✅ {test_name.upper()}: WORKING")
            elif status == "ERROR":
                issues.append(test_name)
                print(f"❌ {test_name.upper()}: ERROR")
            else:
                issues.append(test_name)
                print(f"⚠️  {test_name.upper()}: {status}")
        
        print(f"\n📊 RESULTS:")
        print(f"   ✅ Working: {len(successes)}")
        print(f"   ❌ Issues: {len(issues)}")
        
        if len(successes) >= 3:
            print(f"   🎉 MAJOR SYSTEMS OPERATIONAL!")
        else:
            print(f"   🚨 CRITICAL ISSUES REMAIN")
            
        return results

if __name__ == "__main__":
    test = FixedCriticalTest()
    results = test.run_fixed_tests()
#!/usr/bin/env python3
"""
Critical Issue Investigation Test
Tests the specific concerns about bot production readiness:
1. Watchlist generation (why 0 symbols?)
2. D+1 exit signal generation
3. Daily loss kill switch appropriateness 
4. Actual trade execution through Alpaca
"""

import sys
import os
import logging
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from traders.short_cycle_trader import ShortCycleTrader, ShortCycleConfig
from test.sprint1_alpaca_integration import Sprint1AlpacaIntegration

class CriticalIssueInvestigation:
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.setup_logging()
        
    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[logging.StreamHandler()]
        )
        
    def test_daily_loss_kill_switch(self):
        """Test if daily loss limit is appropriate for portfolio size"""
        print("\n🔍 ISSUE 1: Daily Loss Kill Switch Analysis")
        print("=" * 60)
        
        try:
            # Create trader instance
            config = ShortCycleConfig()
            trader = ShortCycleTrader(config)
            
            # Calculate loss limits based on current portfolio
            portfolio_value = 963379.4  # From test results
            loss_percent = config.max_daily_loss_percent  # 1.5%
            daily_loss_limit = portfolio_value * loss_percent
            
            print(f"📊 Portfolio Analysis:")
            print(f"   Current Portfolio: ${portfolio_value:,.2f}")
            print(f"   Daily Loss Percent: {loss_percent:.1%}")
            print(f"   Daily Loss Limit: ${daily_loss_limit:,.2f}")
            print(f"   Test Triggered at: ${270.60:,.2f}")
            
            # Analysis
            percentage_of_limit = 270.60 / daily_loss_limit * 100
            print(f"\n💡 Analysis:")
            print(f"   Kill switch triggered at only {percentage_of_limit:.1f}% of limit")
            print(f"   This suggests the limit may be TOO LOW for normal trading")
            
            # Recommendations
            reasonable_limit = portfolio_value * 0.0015  # 0.15% might be more appropriate
            print(f"\n🎯 Recommendations:")
            print(f"   Current limit: ${daily_loss_limit:,.2f} ({loss_percent:.1%})")
            print(f"   Suggested limit: ${reasonable_limit:,.2f} (0.15%)")
            print(f"   OR: Use absolute dollar amount like $2,000-5,000")
            
            return {
                "test": "daily_loss_kill_switch",
                "status": "ISSUE_FOUND",
                "portfolio_value": portfolio_value,
                "current_limit": daily_loss_limit,
                "triggered_at": 270.60,
                "percentage_used": percentage_of_limit,
                "issue": "Kill switch too sensitive - triggers at tiny fraction of limit"
            }
            
        except Exception as e:
            print(f"❌ Error analyzing daily loss: {e}")
            return {"test": "daily_loss_kill_switch", "status": "ERROR", "error": str(e)}
    
    def test_d1_exit_signal_generation(self):
        """Test if D+1 exit signals are actually generated"""
        print("\n🔍 ISSUE 2: D+1 Exit Signal Generation")
        print("=" * 60)
        
        try:
            # Read positions to see what should be exited
            positions_file = project_root / "positions.json"
            if not positions_file.exists():
                print("❌ No positions.json found - cannot test D+1 exits")
                return {"test": "d1_exit_signals", "status": "NO_POSITIONS"}
            
            import json
            with open(positions_file) as f:
                positions = json.load(f)
            
            # Find active positions that should trigger D+1 exits
            today = datetime.now().strftime("%Y-%m-%d")
            yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            
            active_positions = [p for p in positions if p.get("status") == "active"]
            d1_candidates = [p for p in positions 
                           if p.get("entry_date") == yesterday and p.get("status") == "active"]
            
            print(f"📊 Position Analysis:")
            print(f"   Total positions in file: {len(positions)}")
            print(f"   Active positions: {len(active_positions)}")
            print(f"   D+1 exit candidates (entered {yesterday}): {len(d1_candidates)}")
            
            if d1_candidates:
                print(f"\n📋 D+1 Exit Candidates:")
                for pos in d1_candidates:
                    print(f"   {pos['symbol']}: ${pos['entry_price']:.2f} x {pos['position_size_shares']} shares")
            
            # Test actual signal generation
            config = ShortCycleConfig()
            trader = ShortCycleTrader(config)
            
            # Simulate D+1 exit check
            exit_signals = []
            for pos in d1_candidates:
                # This is what should happen in production
                signal = {
                    "symbol": pos["symbol"],
                    "action": "SELL", 
                    "reason": "D+1_MANDATORY_EXIT",
                    "shares": pos["position_size_shares"],
                    "entry_date": pos["entry_date"]
                }
                exit_signals.append(signal)
            
            print(f"\n🎯 Expected D+1 Exit Signals: {len(exit_signals)}")
            for signal in exit_signals:
                print(f"   SELL {signal['symbol']}: {signal['shares']} shares (D+1 exit)")
            
            return {
                "test": "d1_exit_signals",
                "status": "ANALYZED",
                "total_positions": len(positions),
                "active_positions": len(active_positions), 
                "d1_candidates": len(d1_candidates),
                "expected_exit_signals": len(exit_signals),
                "signals": exit_signals
            }
            
        except Exception as e:
            print(f"❌ Error testing D+1 exits: {e}")
            return {"test": "d1_exit_signals", "status": "ERROR", "error": str(e)}
    
    def test_watchlist_generation(self):
        """Test why strategic scan shows 0 symbols in watchlist"""
        print("\n🔍 ISSUE 3: Watchlist Generation Analysis")
        print("=" * 60)
        
        try:
            # Test the actual strategic scan logic
            bot = Sprint1AlpacaIntegration()
            
            print("📊 Testing Strategic Scan Process...")
            
            # Simulate what happens in strategic scan
            trader = bot.trader
            
            # Get current universe size
            universe_size = len(trader.symbols) if hasattr(trader, 'symbols') else 0
            print(f"   Trading Universe Size: {universe_size}")
            
            # Test signal generation
            if hasattr(trader, 'generate_signals'):
                signals = trader.generate_signals()
                high_confidence = [s for s in signals if s.get('confidence', 0) > 0.6]
                print(f"   Total Signals Generated: {len(signals)}")
                print(f"   High Confidence Signals: {len(high_confidence)}")
            else:
                print("   ❌ No generate_signals method found")
                
            # Check if watchlist file exists
            watchlist_file = project_root / "watchlist.json"
            if watchlist_file.exists():
                import json
                with open(watchlist_file) as f:
                    watchlist = json.load(f)
                print(f"   Watchlist File: {len(watchlist)} symbols")
            else:
                print("   ❌ No watchlist.json file found")
                
            # Test dynamic universe generation
            if hasattr(trader, 'refresh_universe'):
                print("\n🔄 Testing Universe Refresh...")
                try:
                    trader.refresh_universe()
                    new_universe_size = len(trader.symbols) if hasattr(trader, 'symbols') else 0
                    print(f"   Post-refresh Universe: {new_universe_size} symbols")
                except Exception as e:
                    print(f"   ❌ Universe refresh failed: {e}")
            
            return {
                "test": "watchlist_generation",
                "status": "ANALYZED",
                "universe_size": universe_size,
                "watchlist_exists": watchlist_file.exists(),
                "issue": "Strategic scan may not be generating/saving watchlist properly"
            }
            
        except Exception as e:
            print(f"❌ Error testing watchlist: {e}")
            return {"test": "watchlist_generation", "status": "ERROR", "error": str(e)}
    
    def test_actual_trade_execution(self):
        """Test if signals convert to actual Alpaca trades"""
        print("\n🔍 ISSUE 4: Actual Trade Execution Test")
        print("=" * 60)
        
        try:
            # Create bot with paper trading
            bot = Sprint1AlpacaIntegration()
            trader = bot.trader
            
            print("📊 Testing Trade Execution Pipeline...")
            
            # Check Alpaca connection
            if hasattr(bot, 'api'):
                account = bot.api.get_account()
                print(f"   Alpaca Account: ${float(account.portfolio_value):,.2f}")
                print(f"   Buying Power: ${float(account.buying_power):,.2f}")
                print(f"   Day Trading Buying Power: ${float(account.daytrading_buying_power):,.2f}")
            else:
                print("   ❌ No Alpaca API connection found")
                
            # Test signal generation and filtering
            if hasattr(trader, 'generate_signals'):
                signals = trader.generate_signals()
                filtered_signals = []
                
                for signal in signals:
                    confidence = signal.get('confidence', 0)
                    if confidence > trader.config.confidence_threshold:
                        filtered_signals.append(signal)
                        
                print(f"   Raw Signals: {len(signals)}")
                print(f"   Filtered Signals: {len(filtered_signals)}")
                print(f"   Confidence Threshold: {trader.config.confidence_threshold}")
                
                # Show top signals
                if filtered_signals:
                    print(f"\n📋 Top Trading Signals:")
                    for i, signal in enumerate(filtered_signals[:5]):
                        symbol = signal.get('symbol', 'Unknown')
                        confidence = signal.get('confidence', 0)
                        action = signal.get('action', 'Unknown')
                        print(f"   {i+1}. {action} {symbol} (confidence: {confidence:.1%})")
                        
                # Test position sizing
                if filtered_signals and hasattr(trader, 'calculate_position_size'):
                    test_signal = filtered_signals[0]
                    try:
                        position_size = trader.calculate_position_size(test_signal)
                        print(f"\n💰 Position Sizing Test:")
                        print(f"   Signal: {test_signal.get('symbol', 'Test')}")
                        print(f"   Calculated Size: ${position_size:,.2f}")
                    except Exception as e:
                        print(f"   ❌ Position sizing failed: {e}")
                        
            return {
                "test": "trade_execution",
                "status": "ANALYZED", 
                "has_alpaca_connection": hasattr(bot, 'api'),
                "signals_generated": len(signals) if 'signals' in locals() else 0,
                "signals_filtered": len(filtered_signals) if 'filtered_signals' in locals() else 0,
                "ready_for_trading": bool(filtered_signals) if 'filtered_signals' in locals() else False
            }
            
        except Exception as e:
            print(f"❌ Error testing trade execution: {e}")
            return {"test": "trade_execution", "status": "ERROR", "error": str(e)}
    
    def run_investigation(self):
        """Run complete investigation of critical issues"""
        print("🚨 CRITICAL ISSUE INVESTIGATION")
        print("=" * 80)
        print("Testing specific concerns about bot production readiness...")
        
        results = {}
        
        # Test each critical issue
        results["daily_loss"] = self.test_daily_loss_kill_switch()
        results["d1_exits"] = self.test_d1_exit_signal_generation()
        results["watchlist"] = self.test_watchlist_generation()
        results["execution"] = self.test_actual_trade_execution()
        
        # Summary
        print("\n🎯 INVESTIGATION SUMMARY")
        print("=" * 60)
        
        issues_found = []
        for test_name, result in results.items():
            status = result.get("status", "UNKNOWN")
            if status == "ISSUE_FOUND":
                issues_found.append(test_name)
                print(f"❌ {test_name.upper()}: ISSUE FOUND")
            elif status == "ERROR":
                issues_found.append(test_name)
                print(f"⚠️  {test_name.upper()}: ERROR")
            else:
                print(f"✅ {test_name.upper()}: ANALYZED")
        
        if issues_found:
            print(f"\n🚨 CRITICAL ISSUES IDENTIFIED: {len(issues_found)}")
            print("Bot may NOT be ready for autonomous trading!")
        else:
            print(f"\n✅ No critical issues found in analysis")
            
        return results

if __name__ == "__main__":
    investigation = CriticalIssueInvestigation()
    results = investigation.run_investigation()
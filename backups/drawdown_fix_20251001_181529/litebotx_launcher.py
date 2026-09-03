#!/usr/bin/env python3
"""
LiteBotX Unified Trading Launcher
=====================================
Complete real-money trading system with:
- Live Alpaca integration (no paper trading restrictions)
- D+1 exit strategy with real sell orders
- Dynamic portfolio management
- Safety monitoring
- Comprehensive menu system

Author: LiteBotX Team
Version: 2.0 (Unified)
"""

import sys
import os
import time
from datetime import datetime, timedelta
import logging

# Add the project directory to Python path
sys.path.append('/home/wes/Desktop/litebotx-usb-deployment')

from traders.short_cycle_trader import ShortCycleTrader, ShortCycleConfig
from connect_real_trading import RealPaperTradingEngine

def setup_logging():
    """Setup logging for the trading system"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('/home/wes/Desktop/litebotx-usb-deployment/unified_trading.log'),
            logging.StreamHandler()
        ]
    )

def print_banner():
    """Print LiteBotX banner"""
    print("""
================================================================
                LiteBotX Unified Launcher                 
                Live Trading System v2.0                   
================================================================
    """)

def get_real_portfolio_info():
    """Get real portfolio information from Alpaca"""
    try:
        engine = RealPaperTradingEngine()
        account_info = engine.get_account_info()
        
        if account_info:
            return {
                'portfolio_value': account_info['portfolio_value'],
                'cash': account_info['cash'],
                'status': account_info.get('status', 'active')
            }
        else:
            return None
    except Exception as e:
        print(f"❌ Error getting portfolio info: {e}")
        return None

def create_trading_config(profile="balanced"):
    """Create trading configuration based on selected profile"""
    
    # Get real portfolio value
    portfolio_info = get_real_portfolio_info()
    if not portfolio_info:
        print("❌ Cannot connect to Alpaca. Please check your connection.")
        return None
    
    portfolio_value = portfolio_info['portfolio_value']
    
    profiles = {
        "conservative": {
            'daily_pool_percent': 0.10,  # 10% of portfolio
            'max_risk_per_trade_dollars': 50.0,
            'max_positions_per_day': 3,
            'max_daily_loss_percent': 0.002,  # 0.2% daily
            'max_weekly_loss_percent': 0.01,  # 1.0% weekly
            'confidence_threshold': 0.08,  # Conservative but optimized (vacation mode)
            'max_position_size_percent': 0.02  # 2% max per position
        },
        "balanced": {
            'daily_pool_percent': 0.30,  # 30% of portfolio
            'max_risk_per_trade_dollars': 100.0,
            'max_positions_per_day': 5,
            'max_daily_loss_percent': 0.005,  # 0.5% daily
            'max_weekly_loss_percent': 0.02,  # 2.0% weekly
            'confidence_threshold': 0.065,  # Balanced with optimization benefit
            'max_position_size_percent': 0.03  # 3% max per position
        },
        "aggressive": {
            'daily_pool_percent': 0.80,  # 80% of portfolio
            'max_risk_per_trade_dollars': 200.0,
            'max_positions_per_day': 8,
            'max_daily_loss_percent': 0.01,  # 1.0% daily
            'max_weekly_loss_percent': 0.03,  # 3.0% weekly
            'confidence_threshold': 0.055,  # Optimized primary mode (5.5%)
            'max_position_size_percent': 0.05  # 5% max per position
        }
    }
    
    settings = profiles[profile]
    
    return ShortCycleConfig(
        portfolio_value=portfolio_value,
        daily_pool_percent=settings['daily_pool_percent'],
        max_risk_per_trade_dollars=settings['max_risk_per_trade_dollars'],
        max_positions_per_day=settings['max_positions_per_day'],
        min_position_size_dollars=25.0,
        max_position_size_percent=settings['max_position_size_percent'],
        max_daily_loss_percent=settings['max_daily_loss_percent'],
        max_weekly_loss_percent=settings['max_weekly_loss_percent'],
        confidence_threshold=settings['confidence_threshold'],
        trading_days=["monday", "tuesday", "wednesday", "thursday", "friday"]
    )

def display_config_summary(config):
    """Display configuration summary"""
    daily_limit = config.portfolio_value * config.max_daily_loss_percent
    weekly_limit = config.portfolio_value * config.max_weekly_loss_percent
    daily_pool = config.portfolio_value * config.daily_pool_percent
    max_position = config.portfolio_value * config.max_position_size_percent
    
    print(f"\\n📊 Configuration Summary:")
    print(f"💰 Portfolio Value: ${config.portfolio_value:,.2f}")
    print(f"🎯 Daily Trading Pool: ${daily_pool:,.2f} ({config.daily_pool_percent:.1%})")
    print(f"🛡️  Daily Loss Limit: ${daily_limit:,.2f} ({config.max_daily_loss_percent:.1%})")
    print(f"🛡️  Weekly Loss Limit: ${weekly_limit:,.2f} ({config.max_weekly_loss_percent:.1%})")
    print(f"📈 Max Position Size: ${max_position:,.2f} ({config.max_position_size_percent:.1%})")
    print(f"🎲 Max Risk Per Trade: ${config.max_risk_per_trade_dollars:,.2f}")
    print(f"🔍 Confidence Threshold: {config.confidence_threshold:.1%}")
    print(f"📊 Max Positions/Day: {config.max_positions_per_day}")

def show_menu():
    """Display main menu"""
    print("\\n" + "="*60)
    print("🚀 LiteBotX Trading Options:")
    print("="*60)
    print("1. 🟢 Start Conservative Trading (10% portfolio, low risk)")
    print("2. 🟡 Start Balanced Trading (30% portfolio, moderate risk)")
    print("3. 🔴 Start Aggressive Trading (80% portfolio, high risk)")
    print("4. 📊 View Portfolio Status")
    print("5. 📈 View Current Positions")
    print("6. 🧪 Test Connection")
    print("7. 📝 View Recent Logs")
    print("8. 🎛️  Launch Dashboard")
    print("9. 🛑 Exit")
    print("="*60)

def test_connection():
    """Test Alpaca connection"""
    print("\\n🔍 Testing Alpaca Connection...")
    portfolio_info = get_real_portfolio_info()
    
    if portfolio_info:
        print(f"✅ Connection Successful!")
        print(f"   Portfolio Value: ${portfolio_info['portfolio_value']:,.2f}")
        print(f"   Available Cash: ${portfolio_info['cash']:,.2f}")
        print(f"   Account Status: {portfolio_info['status']}")
        return True
    else:
        print(f"❌ Connection Failed!")
        return False

def view_positions():
    """View current positions"""
    print("\\n📋 Loading Current Positions...")
    try:
        from traders.short_cycle_trader import ShortCycleTrader
        temp_config = create_trading_config("balanced")
        if not temp_config:
            return
            
        trader = ShortCycleTrader(temp_config)
        trader._load_positions()
        
        positions = trader.positions
        active_positions = [p for p in positions if p.status == "entered"]
        
        if active_positions:
            print(f"\\n📊 Active Positions ({len(active_positions)}):")
            print("-" * 80)
            print(f"{'Symbol':<10} {'Entry Date':<12} {'Exit Date':<12} {'Entry Price':<12} {'Size':<8} {'P&L':<12}")
            print("-" * 80)
            
            total_pnl = 0
            for pos in active_positions:
                current_price = trader._get_current_price(pos.symbol)
                unrealized_pnl = (current_price - pos.entry_price) * pos.position_size_shares if current_price else 0
                total_pnl += unrealized_pnl
                
                print(f"{pos.symbol:<10} {pos.entry_date.strftime('%Y-%m-%d'):<12} "
                      f"{pos.exit_date.strftime('%Y-%m-%d'):<12} ${pos.entry_price:<11.2f} "
                      f"{pos.position_size_shares:<8} ${unrealized_pnl:<11.2f}")
            
            print("-" * 80)
            print(f"Total Unrealized P&L: ${total_pnl:.2f}")
        else:
            print("📭 No active positions")
            
    except Exception as e:
        print(f"❌ Error loading positions: {e}")

def run_trading_system(profile):
    """Run the trading system with selected profile"""
    print(f"\\n🚀 Starting {profile.title()} Trading System...")
    
    config = create_trading_config(profile)
    if not config:
        return
    
    display_config_summary(config)
    
    print("\\n⚠️  LIVE TRADING WARNING:")
    print("   - This system trades with REAL MONEY")
    print("   - All trades are executed on Alpaca")
    print("   - D+1 exits will automatically sell positions")
    print("   - Safety limits are active but not guaranteed")
    
    confirm = input("\\n✅ Confirm start live trading? (yes/y): ").lower().strip()
    if confirm not in ['yes', 'y']:
        print("🛑 Trading cancelled by user")
        return
    
    try:
        # Initialize trader
        trader = ShortCycleTrader(config)
        
        # Verify connection
        account_info = trader.execution_engine.get_account_info()
        if not account_info:
            print("❌ Failed to connect to Alpaca")
            return
        
        print(f"\\n✅ Connected to Alpaca - LIVE MODE ENABLED")
        print(f"💰 Portfolio Value: ${account_info['portfolio_value']:,.2f}")
        print(f"💵 Cash: ${account_info['cash']:,.2f}")
        print(f"🔴 LIVE TRADING ACTIVE - Press Ctrl+C to stop")
        
        cycle_count = 0
        
        # Run the continuous market-hours aware cycle
        try:
            trader.run_continuous_cycle()
        except Exception as e:
            print(f"❌ Continuous cycle error: {e}")
            logging.error(f"Continuous cycle error: {e}")
            
    except KeyboardInterrupt:
        print("\\n🛑 Trading stopped by user")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        logging.error(f"Fatal error: {e}")

def view_logs():
    """View recent log entries"""
    print("\\n📝 Recent Trading Logs:")
    try:
        log_file = '/home/wes/Desktop/litebotx-usb-deployment/unified_trading.log'
        if os.path.exists(log_file):
            with open(log_file, 'r') as f:
                lines = f.readlines()
                recent_lines = lines[-20:]  # Last 20 lines
                for line in recent_lines:
                    print(line.strip())
        else:
            print("📭 No log file found")
    except Exception as e:
        print(f"❌ Error reading logs: {e}")

def launch_dashboard():
    """Launch the trading dashboard"""
    print("\\n🎛️  Launching Trading Dashboard...")
    try:
        dashboard_path = '/home/wes/Desktop/litebotx-usb-deployment/gui/enhanced_trading_dashboard.py'
        if os.path.exists(dashboard_path):
            import subprocess
            subprocess.Popen(['python3', dashboard_path])
            print("✅ Dashboard launched in separate window")
        else:
            print("❌ Dashboard file not found")
    except Exception as e:
        print(f"❌ Error launching dashboard: {e}")

def main():
    """Main menu loop"""
    setup_logging()
    print_banner()
    
    while True:
        show_menu()
        
        try:
            choice = input("\\n🎯 Select option (1-9): ").strip()
            
            if choice == '1':
                run_trading_system("conservative")
            elif choice == '2':
                run_trading_system("balanced")
            elif choice == '3':
                run_trading_system("aggressive")
            elif choice == '4':
                portfolio_info = get_real_portfolio_info()
                if portfolio_info:
                    print(f"\\n💰 Portfolio Status:")
                    print(f"   Value: ${portfolio_info['portfolio_value']:,.2f}")
                    print(f"   Cash: ${portfolio_info['cash']:,.2f}")
                    print(f"   Status: {portfolio_info['status']}")
            elif choice == '5':
                view_positions()
            elif choice == '6':
                test_connection()
            elif choice == '7':
                view_logs()
            elif choice == '8':
                launch_dashboard()
            elif choice == '9':
                print("\\n👋 Goodbye!")
                break
            else:
                print("❌ Invalid choice. Please select 1-9.")
                
        except KeyboardInterrupt:
            print("\\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
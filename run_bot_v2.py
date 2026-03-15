#!/usr/bin/env python3
"""
Run bot_v2 ProductionTradingEngine with real Alpaca connection
Loads credentials from .env file
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import bot_v2
from bot_v2.core import ProductionTradingEngine
from bot_v2.config import ShortCycleConfig

# Use Alpaca adapter for live trading
from alpaca_adapter import AlpacaAdapter

# Import data loader
from data_loader import DataLoader

def main():
    """Run bot_v2 daily trading cycle"""
    
    print("="*70)
    print("bot_v2 ProductionTradingEngine - Daily Trading Cycle")
    print("="*70)
    print()
    
    # Get credentials from environment variables
    # Note: Using APCA_ prefix (Alpaca's standard naming)
    alpaca_api_key = os.getenv('APCA_API_KEY_ID') or os.getenv('ALPACA_API_KEY')
    alpaca_secret_key = os.getenv('APCA_API_SECRET_KEY') or os.getenv('ALPACA_SECRET_KEY')
    alpaca_base_url = os.getenv('APCA_API_BASE_URL')
    alpaca_paper = os.getenv('ALPACA_PAPER', 'true').lower() == 'true'
    
    if not alpaca_api_key or not alpaca_secret_key:
        print("❌ ERROR: Alpaca credentials not found in .env file")
        print("   Please ensure .env contains:")
        print("   APCA_API_KEY_ID=your_key_here")
        print("   APCA_API_SECRET_KEY=your_secret_here")
        print("   APCA_API_BASE_URL=https://paper-api.alpaca.markets  # for paper trading")
        print("   # OR")
        print("   ALPACA_API_KEY=your_key_here")
        print("   ALPACA_SECRET_KEY=your_secret_here")
        print("   ALPACA_PAPER=true  # (optional, defaults to true)")
        sys.exit(1)
    
    # Determine if paper trading based on base URL or explicit flag
    if alpaca_base_url:
        is_paper = 'paper' in alpaca_base_url.lower()
    else:
        is_paper = alpaca_paper
    
    print(f"✅ Loaded credentials from .env")
    print(f"   Mode: {'PAPER TRADING' if is_paper else 'LIVE TRADING'}")
    if alpaca_base_url:
        print(f"   Base URL: {alpaca_base_url}")
    print()
    
    # Initialize configuration
    config = ShortCycleConfig()
    print(f"📋 Configuration:")
    print(f"   Portfolio Value: ${config.portfolio_value:,.0f}")
    print(f"   Daily Pool: ${config.daily_pool_dollars:,.0f} ({config.daily_pool_percent:.0%})")
    print(f"   Confidence Threshold: {config.confidence_threshold:.0%}")
    print(f"   Max Positions/Day: {config.max_positions_per_day}")
    print(f"   Max Daily Loss: ${config.max_daily_loss_dollars:,.0f} ({config.max_daily_loss_percent:.0%})")
    print()
    
    # Initialize Alpaca adapter (provides bot_v2-compatible interface)
    print("🔌 Connecting to Alpaca...")
    try:
        execution_engine = AlpacaAdapter(
            api_key=alpaca_api_key,
            secret_key=alpaca_secret_key,
            paper=is_paper
        )
        
        # Test connection and get account info
        portfolio = execution_engine.get_portfolio_summary()
        account_value = portfolio['account']['portfolio_value']
        buying_power = portfolio['account']['buying_power']
        
        print("✅ Connected to Alpaca")
        print(f"   Account Value: ${account_value:,.2f}")
        print(f"   Buying Power: ${buying_power:,.2f}")
    except Exception as e:
        print(f"❌ Failed to connect to Alpaca: {e}")
        sys.exit(1)
    
    # Initialize data loader
    print("📊 Initializing data loader...")
    try:
        data_loader = DataLoader()
        print("✅ Data loader ready")
    except Exception as e:
        print(f"❌ Failed to initialize data loader: {e}")
        sys.exit(1)
    
    print()
    
    # Initialize bot_v2
    print("🤖 Initializing bot_v2 ProductionTradingEngine...")
    try:
        bot = ProductionTradingEngine(
            config=config,
            execution_engine=execution_engine,
            data_loader=data_loader
        )
        print("✅ bot_v2 initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize bot: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    print()
    print("="*70)
    print("Starting Daily Trading Cycle")
    print("="*70)
    print()
    
    # Run daily trading cycle
    try:
        bot.run_daily_cycle()
        print()
        print("="*70)
        print("✅ Daily Trading Cycle Complete")
        print("="*70)
        
        # Display summary
        summary = bot.get_portfolio_summary()
        print()
        print("📊 Portfolio Summary:")
        print(f"   Portfolio Value: ${summary.get('portfolio_value', 0):,.2f}")
        print(f"   Open Positions: {summary.get('open_positions', 0)}")
        print(f"   Trades Today: {summary.get('trades_today', 0)}")
        print(f"   Daily P&L: ${summary.get('daily_pnl', 0):,.2f}")
        print()
        
    except KeyboardInterrupt:
        print()
        print("⚠️  Trading cycle interrupted by user")
        sys.exit(0)
    except Exception as e:
        print()
        print(f"❌ Error during trading cycle: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

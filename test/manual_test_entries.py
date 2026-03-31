#!/usr/bin/env python3
"""
Manual Entry Script for Testing
Bypasses Thursday freeze to place test entries with the top candidates
"""

import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from connect_real_trading import RealPaperTradingEngine
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Top candidates from Oct 22 watchlist refresh
TEST_CANDIDATES = [
    {"symbol": "AMD", "score": 5.00, "rs": 1.465},
    {"symbol": "AVGO", "score": 3.18, "rs": 1.001},
    {"symbol": "MMM", "score": 1.94, "rs": 1.056},
    {"symbol": "CRM", "score": -1.49, "rs": 1.066},
]

def calculate_position_size(portfolio_value: float, symbol: str, current_price: float) -> int:
    """Calculate position size using 6.25% of portfolio (max 16 positions)"""
    target_allocation = 0.0625  # 6.25% per position
    position_value = portfolio_value * target_allocation
    shares = int(position_value / current_price)
    return max(1, shares)  # At least 1 share

def main():
    print("=" * 80)
    print("🧪 MANUAL TEST ENTRY SCRIPT")
    print("=" * 80)
    print()
    print("⚠️  WARNING: This bypasses Thursday freeze logic for testing purposes")
    print("    These positions will exit Friday (tomorrow) before market close")
    print()
    
    # Confirm action
    response = input("Do you want to place test entries? (yes/no): ").strip().lower()
    if response != 'yes':
        print("❌ Cancelled by user")
        return 1
    
    print()
    print("=" * 80)
    
    try:
        # Initialize engine
        engine = RealPaperTradingEngine()
        
        # Get account info
        account_info = engine.get_account_info()
        if not account_info:
            logger.error("❌ Failed to get account info")
            return 1
            
        portfolio_value = account_info['portfolio_value']
        cash = account_info['cash']
        
        logger.info(f"💰 Portfolio Value: ${portfolio_value:,.2f}")
        logger.info(f"💵 Cash Available: ${cash:,.2f}")
        print()
        
        # Check current positions
        current_positions = engine.get_positions()
        if current_positions:
            logger.warning(f"⚠️  {len(current_positions)} positions already open:")
            for symbol, pos in current_positions.items():
                logger.info(f"   - {symbol}: {pos['quantity']} shares")
            print()
            response = input("Continue anyway? (yes/no): ").strip().lower()
            if response != 'yes':
                print("❌ Cancelled by user")
                return 1
            print()
        
        # Place orders for test candidates
        successful_entries = []
        failed_entries = []
        
        for candidate in TEST_CANDIDATES:
            symbol = candidate['symbol']
            
            try:
                # Get current price from Alpaca
                from alpaca.data.historical import StockHistoricalDataClient
                from alpaca.data.requests import StockLatestBarRequest
                import os
                from dotenv import load_dotenv
                
                load_dotenv()
                data_client = StockHistoricalDataClient(
                    os.getenv("APCA_API_KEY_ID"),
                    os.getenv("APCA_API_SECRET_KEY")
                )
                
                request_params = StockLatestBarRequest(symbol_or_symbols=symbol)
                latest_bars = data_client.get_stock_latest_bar(request_params)
                current_price = float(latest_bars[symbol].close)
                
                # Calculate position size
                shares = calculate_position_size(portfolio_value, symbol, current_price)
                position_value = shares * current_price
                
                logger.info(f"📊 {symbol}: ${current_price:.2f} | RS={candidate['rs']:.3f} | Score={candidate['score']:.2f}")
                logger.info(f"   → Buying {shares} shares (${position_value:,.2f})")
                
                # Place market order
                order = engine.submit_order(
                    symbol=symbol,
                    quantity=shares,
                    side='buy',
                    order_type='market'
                )
                
                if order and order.get('status') not in ['rejected', 'canceled']:
                    logger.info(f"   ✅ Order submitted: {order.get('order_id')}")
                    successful_entries.append({
                        'symbol': symbol,
                        'shares': shares,
                        'price': current_price,
                        'value': position_value,
                        'order_id': order.get('order_id')
                    })
                else:
                    logger.error(f"   ❌ Order failed: {order.get('status') if order else 'No response'}")
                    failed_entries.append(symbol)
                
                print()
                
            except Exception as e:
                logger.error(f"❌ Error placing order for {symbol}: {e}")
                failed_entries.append(symbol)
                print()
        
        # Summary
        print("=" * 80)
        print("📋 ORDER SUMMARY")
        print("=" * 80)
        
        if successful_entries:
            total_invested = sum(e['value'] for e in successful_entries)
            logger.info(f"✅ {len(successful_entries)} orders submitted:")
            for entry in successful_entries:
                logger.info(f"   {entry['symbol']}: {entry['shares']} shares @ ${entry['price']:.2f} = ${entry['value']:,.2f}")
            logger.info(f"   Total: ${total_invested:,.2f}")
        
        if failed_entries:
            logger.error(f"❌ {len(failed_entries)} orders failed: {', '.join(failed_entries)}")
        
        print()
        print("=" * 80)
        print("⏰ IMPORTANT: These positions will exit TOMORROW (Friday) before close")
        print("    Monitor the bot logs for automatic Friday exits")
        print("=" * 80)
        
        # Save entry info to positions.json for tracking
        if successful_entries:
            print()
            logger.info("💾 Positions will sync with bot on next run")
            logger.info("   Bot will detect these from Alpaca and create trackers")
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())

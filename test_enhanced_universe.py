#!/usr/bin/env python3
"""
Enhanced Small Portfolio Universe Generator
Tests expanded candidate list with relaxed breakout filters for 5-10 stock universe
"""

import sys
import os
import logging
from datetime import datetime, timedelta

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Import modules
from small_portfolio_config import SmallPortfolioConfig
from pre_filter import PreFilter

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

def test_enhanced_universe():
    """Test universe generation with expanded sectors and relaxed filters"""
    
    try:
        logger.info("🎯 Enhanced Small Portfolio Universe Generation")
        logger.info("=" * 60)
        
        # Create configuration
        config = SmallPortfolioConfig()
        logger.info(f"Portfolio: ${config.portfolio_value:,.0f}")
        logger.info(f"Price range: ${config.min_price}-${config.max_price}")
        logger.info(f"Relaxed breakout: vol_spike≥{config.vol_spike_min}x, breakout≥{config.breakout_min:.1%}")
        
        # Create PreFilter with small portfolio optimizations
        prefilter = PreFilter()
        
        # Cleaned candidate list (removed delisted stocks)
        candidates = [
            # Tech/Software (mid-cap focus $10-35)
            "PINS","SNAP","ROKU","ZM","DOCU","CRWD","NET","DDOG","SNOW","PLTR",
            "RBLX","HOOD","COIN","PYPL","EBAY","ETSY","SPOT","TDOC","PTON",
            "TWLO","ZS","OKTA","MDB","VEEV","WDAY","CRM","ADBE","TEAM",
            
            # EV/Clean Energy 
            "RIVN","LCID","CHPT","NIO","XPEV","LI","BLNK","ENPH","SEDG","FSLR",
            "PLUG","BE","BLDP","HYLN","WKHS","GOEV",
            
            # Cannabis/Biotech
            "TLRY","CGC","ACB","SNDL","CRON","OGI","MRNA","BNTX",
            "NVAX","VXRT","INO","GILD","REGN","VRTX","ILMN","BMY","ABBV","PFE",
            
            # Travel/Leisure/Gaming
            "AAL","DAL","UAL","LUV","CCL","NCLH","RCL","MGM","LVS","PENN",
            "WYNN","BYD","CZR","DKNG","BKNG","EXPE","TRIP","MAR","HLT",
            
            # Financials (regional banks & fintech)
            "BAC","WFC","C","JPM","GS","MS","USB","PNC","TFC","COF",
            "ALLY","SOFI","UPST","AFRM","LC","V","MA","AXP","SYF",
            
            # Energy/Commodities 
            "XOM","CVX","COP","EOG","MPC","VLO","PSX","SLB","HAL",
            "OXY","DVN","FANG","APA","MTDR","SM","RIG","VAL",
            
            # Consumer/Retail
            "F","GM","FORD","NKE","LULU","CHWY","TGT","HD","LOW","COST",
            "DG","DLTR","ANF","UAA","CROX","SBUX","CMG","MCD","YUM",
            
            # Industrial/Materials
            "BA","CAT","GE","MMM","HON","UPS","FDX","DE","LMT","RTX",
            "ALB","LAC","MP","VALE","FCX","NEM","AEM","KGC","HL",
            
            # Communication/Media
            "T","VZ","NFLX","DIS","CMCSA","TMUS","WBD","AMC",
            "SIRI","IRDM","GOGO","SPCE","RKLB","PL","ASTS"
        ]
        
        logger.info(f"📊 Testing {len(candidates)} candidates across 8 sectors")
        
        # Fetch recent data (reduced to 30 days for faster processing)
        history_df = prefilter.fetch_history(candidates, days=30, use_cache=True)
        if history_df.empty:
            logger.error("❌ No historical data available")
            return []
        
        logger.info(f"✅ Retrieved data for {history_df['symbol'].nunique()} symbols")
        
        # Apply PreFilter with manual relaxed settings
        logger.info("\n🔧 Applying relaxed filters for small portfolio...")
        
        # Filter by price range first
        latest_prices = history_df.groupby('symbol')['close'].last()
        price_qualified = latest_prices[
            (latest_prices >= config.min_price) & 
            (latest_prices <= config.max_price)
        ].index.tolist()
        
        logger.info(f"✅ Price filter (${config.min_price}-${config.max_price}): {len(price_qualified)} stocks")
        
        if len(price_qualified) >= 10:
            # Apply PreFilter to price-qualified stocks
            price_filtered_df = history_df[history_df['symbol'].isin(price_qualified)]
            
            # Use PreFilter's standard filtering
            result = prefilter.filter_assets(price_filtered_df)
            
            if not result.empty and 'symbol' in result.columns:
                final_symbols = result['symbol'].unique().tolist()
                
                logger.info(f"\n🎯 Final Universe: {len(final_symbols)} stocks")
                for i, symbol in enumerate(final_symbols, 1):
                    price = latest_prices.get(symbol, 0)
                    shares = int(config.get_position_size(price) / price) if price > 0 else 0
                    position_value = shares * price
                    logger.info(f"   {i}. {symbol}: ${price:.2f} → {shares} shares = ${position_value:.2f}")
                
                # Show position sizing examples
                daily_pool = config.get_daily_pool('monday')  # 33% pool example
                logger.info(f"\n💰 Monday Pool (33%): ${daily_pool:.2f}")
                logger.info(f"🏆 Thursday Pool (100%): ${config.portfolio_value:.2f}")
                
                return final_symbols
            else:
                logger.warning("⚠️ No stocks passed final filtering")
                return []
        else:
            logger.warning(f"⚠️ Only {len(price_qualified)} stocks in price range, need more candidates")
            return []
            
    except Exception as e:
        logger.error(f"❌ Error during enhanced universe generation: {e}")
        import traceback
        traceback.print_exc()
        return []

if __name__ == "__main__":
    universe = test_enhanced_universe()
    
    if universe and len(universe) >= 5:
        print(f"\n✅ SUCCESS: Generated {len(universe)}-stock universe")
        print(f"📈 Symbols: {universe}")
        print(f"🎯 Ready for 5-10 position small portfolio management")
    else:
        print(f"\n⚠️ WARNING: Only {len(universe)} stocks found")
        print(f"💡 Consider further relaxing filters or expanding candidate list")

def generate_enhanced_small_portfolio_universe():
    """Wrapper function for integration testing"""
    return test_enhanced_universe()
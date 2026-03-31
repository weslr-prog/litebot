#!/usr/bin/env python3
"""
Test Small Portfolio Universe Generation
Uses SmallPortfolioConfig filters to generate mid-cap focused watchlist
"""

import sys
import os

# Add repo root to path
REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from small_portfolio_config import SmallPortfolioConfig
from traders.short_cycle_trader import ShortCycleTrader
from pre_filter import PreFilter
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_small_portfolio_universe():
    """Test universe generation with small portfolio filters"""
    
    # Create small portfolio config
    config = SmallPortfolioConfig()
    logger.info("=== Small Portfolio Universe Test ===")
    config.log_configuration()
    
    # Initialize trader and prefilter
    trader = ShortCycleTrader()
    
    try:
        # Initialize PreFilter with small portfolio settings
        prefilter = PreFilter(
            simulation_mode=False,
            data_loader=trader.data_loader,
            fast_mode=True,
            enable_intraday_analysis=False,
            max_intraday_analyses_per_day=0
        )
        
                # Expanded candidate list with more sectors for 5-10 stock universe
        candidates = [
            # Tech/Software (mid-cap focus $10-35)
            "PINS","SNAP","ROKU","ZM","DOCU","CRWD","NET","DDOG","SNOW","PLTR",
            "RBLX","HOOD","COIN","SQ","PYPL","EBAY","ETSY","SPOT","TDOC","PTON",
            "TWLO","ZS","OKTA","MDB","SPLK","VEEV","WDAY","NOW","CRM","ADBE",
            
            # EV/Clean Energy 
            "RIVN","LCID","CHPT","NIO","XPEV","LI","BLNK","ENPH","SEDG","FSLR",
            "PLUG","BE","BLDP","FUEL","HYLN","RIDE","WKHS","FSR","GOEV","NKLA",
            
            # Cannabis/Biotech
            "TLRY","CGC","ACB","SNDL","CRON","HEXO","OGI","APHA","MRNA","BNTX",
            "NVAX","VXRT","INO","GILD","REGN","VRTX","ILMN","ISRG","BMY","ABBV",
            
            # Travel/Leisure/Gaming
            "AAL","DAL","UAL","LUV","CCL","NCLH","RCL","MGM","LVS","PENN",
            "WYNN","BYD","ERI","CZR","DKNG","BKNG","EXPE","TRIP","MAR","HLT",
            
            # Financials (regional banks & fintech)
            "JPM","BAC","WFC","C","GS","MS","USB","PNC","TFC","COF",
            "ALLY","SOFI","UPST","AFRM","LC","PYPL","SQ","V","MA","AXP",
            
            # Energy/Commodities 
            "XOM","CVX","COP","EOG","PXD","MPC","VLO","PSX","SLB","HAL",
            "OXY","DVN","FANG","MRO","APA","CLR","MTDR","SM","RIG","VAL",
            
            # Consumer/Retail
            "F","GM","FORD","NKE","LULU","PTON","CHWY","AMZN","WMT","TGT",
            "HD","LOW","COST","DG","DLTR","BBBY","GPS","ANF","UAA","CROX",
            
            # Industrial/Materials
            "BA","CAT","GE","MMM","HON","UPS","FDX","DE","LMT","RTX",
            "ALB","LAC","MP","VALE","FCX","NEM","GOLD","AEM","KGC","HL",
            
            # Communication/Media (Cleaned Nov 12: Removed ASTR - delisted)
            "T","VZ","NFLX","DIS","CMCSA","TMUS","DISH","PARA","WBD","AMC",
            "SIRI","IRDM","GOGO","SPCE","RKLB","PL","ASTS","MAXR","SPIR"
        ]
        
        logger.info(f"Testing {len(candidates)} candidates with small portfolio filters")
        logger.info(f"Price range: ${config.min_price}-${config.max_price}")
        logger.info(f"Relaxed breakout params: vol_spike≥{config.vol_spike_min}x, breakout≥{config.breakout_min:.1%}")
        
        # Fetch recent data
        history_df = prefilter.fetch_history(candidates, days=40, use_cache=True)
        if history_df.empty:
            logger.error("No historical data available")
            return []
        
        logger.info(f"Retrieved data for {history_df['symbol'].nunique()} symbols")
        
        # Apply small portfolio filters manually
        logger.info("\n=== Applying Small Portfolio Filters ===")
        
        # Get latest prices to filter by range
        latest_prices = history_df.groupby('symbol')['close'].last()
        logger.info(f"Price range filter: ${config.min_price}-${config.max_price}")
        
        price_filtered = latest_prices[
            (latest_prices >= config.min_price) & 
            (latest_prices <= config.max_price)
        ]
        
        logger.info(f"✅ Price filter: {len(latest_prices)} → {len(price_filtered)} stocks")
        if len(price_filtered) > 0:
            logger.info("Price-filtered stocks:")
            for symbol, price in price_filtered.sort_values().items():
                logger.info(f"  {symbol}: ${price:.2f}")
        
        # Apply PreFilter to price-filtered stocks
        if len(price_filtered) > 0:
            price_filtered_symbols = price_filtered.index.tolist()
            filtered_df = history_df[history_df['symbol'].isin(price_filtered_symbols)]
            
            # Use PreFilter with enhanced settings for small portfolio
            logger.info(f"\nApplying PreFilter to {len(price_filtered_symbols)} price-qualified stocks...")
            
            # Temporarily override PreFilter settings for more aggressive filtering
            original_settings = {}
            aggressive_settings = {
                'min_vol': config.min_volatility,
                'max_vol': config.max_volatility,
                'min_mom': config.min_momentum / 100,  # Convert percentage
                'max_mom': config.max_momentum / 100,
                'min_avg_volume': config.min_avg_volume,
                'min_dollar_volume': config.min_dollar_volume,
                'vol_spike_min': config.vol_spike_min,
                'breakout_min': config.breakout_min
            }
            
            # Apply aggressive filters
            filtered_result = prefilter.filter_assets(filtered_df)
            
            if not filtered_result.empty:
                # Get latest snapshot and rank
                snap = filtered_result.groupby('symbol').tail(1)
                if 'pf_score' in snap.columns:
                    ranked = snap.sort_values('pf_score', ascending=False)
                else:
                    ranked = snap.sort_values('volume', ascending=False)
                
                final_symbols = ranked['symbol'].tolist()
                
                logger.info(f"\n🎯 Final Small Portfolio Universe: {len(final_symbols)} stocks")
                for i, symbol in enumerate(final_symbols, 1):
                    price = ranked[ranked['symbol'] == symbol]['close'].iloc[0]
                    volume = ranked[ranked['symbol'] == symbol]['volume'].iloc[0]
                    logger.info(f"  {i}. {symbol}: ${price:.2f} (vol: {volume:,.0f})")
                
                # Calculate position sizes for $1K portfolio
                logger.info(f"\n💰 Position Sizing Examples (33% pool = $330):")
                for symbol in final_symbols[:5]:  # Show first 5
                    price = ranked[ranked['symbol'] == symbol]['close'].iloc[0]
                    shares = int(300 / price)  # $300 max position
                    position_value = shares * price
                    logger.info(f"  {symbol}: {shares} shares × ${price:.2f} = ${position_value:.2f}")
                
                return final_symbols
            else:
                logger.warning("No stocks passed PreFilter - filters may be too strict")
                return []
        else:
            logger.warning("No stocks in target price range")
            return []
            
    except Exception as e:
        logger.error(f"Error during universe generation: {e}")
        return []

if __name__ == "__main__":
    universe = test_small_portfolio_universe()
    print(f"\nFinal universe size: {len(universe)}")
    if universe:
        print("Symbols:", universe)
    else:
        print("No suitable stocks found - consider relaxing filters")

def generate_small_portfolio_universe():
    """Wrapper function for integration testing"""
    return test_small_portfolio_universe()
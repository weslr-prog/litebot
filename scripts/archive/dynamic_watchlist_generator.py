#!/usr/bin/env python3
"""
Dynamic Watchlist Generator
Integrates pre_filter module to create daily watchlists for swing trading
Runs after market close to prepare for next trading day
"""

import os
import sys
import pandas as pd
import numpy as np
import yfinance as yf
import logging
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass

# Import existing modules
from core.pre_filter import PreFilter
from core.config import Sprint1Config

@dataclass
class WatchlistConfig:
    """Configuration for dynamic watchlist generation"""
    # Stock universe sources
    sp500_symbols: bool = True  # Use S&P 500 as base universe
    nasdaq100_symbols: bool = True  # Add NASDAQ 100
    custom_symbols: List[str] = None  # Additional custom symbols
    
    # Filtering parameters
    max_watchlist_size: int = 20  # Maximum symbols in final watchlist
    min_watchlist_size: int = 5   # Minimum symbols (fallback)
    
    # Data requirements
    min_data_days: int = 60  # Minimum days of historical data
    
    # Timing
    run_after_market_close: bool = True  # Run after 4:00 PM ET
    market_close_delay_minutes: int = 30  # Wait 30 min after close for data
    
    # Output
    save_to_config: bool = True  # Update config.py automatically
    save_to_file: bool = True    # Save to JSON file
    backup_previous: bool = True # Keep backup of previous watchlist

class DynamicWatchlistGenerator:
    """Generates dynamic watchlists using pre_filter module"""
    
    def __init__(self, config: WatchlistConfig = None):
        self.config = config or WatchlistConfig()
        self.logger = self._setup_logging()
        self.pre_filter = PreFilter()
        self.sprint_config = Sprint1Config()
        
        # State tracking
        self.last_generated = None
        self.current_watchlist = []
        self.generation_history = []
        
        self.logger.info("🎯 Dynamic Watchlist Generator initialized")
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for watchlist generator"""
        logger = logging.getLogger('DynamicWatchlistGenerator')
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        
        return logger
    
    def get_stock_universe(self) -> List[str]:
        """Get the universe of stocks to filter from"""
        symbols = set()
        
        try:
            # S&P 500 symbols (using a representative list)
            if self.config.sp500_symbols:
                sp500_symbols = [
                    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'BRK-B',
                    'UNH', 'XOM', 'JNJ', 'JPM', 'V', 'PG', 'HD', 'CVX', 'MA', 'PFE',
                    'ABBV', 'KO', 'AVGO', 'COST', 'DIS', 'MRK', 'PEP', 'TMO', 'WMT',
                    'BAC', 'CSCO', 'ABT', 'LIN', 'ACN', 'ADBE', 'TXN', 'DHR', 'NEE',
                    'NKE', 'RTX', 'ORCL', 'CRM', 'WFC', 'AMD', 'T', 'QCOM', 'MDT',
                    'VZ', 'UPS', 'PM', 'LOW', 'SPGI', 'CAT', 'HON', 'INTU', 'GS',
                    'AXP', 'BKNG', 'BMY', 'IBM', 'BLK', 'GILD', 'BA', 'AMGN', 'LMT',
                    'MMM', 'SYK', 'ADP', 'TJX', 'VRTX', 'MO', 'MDLZ', 'CVS', 'LRCX',
                    'ZTS', 'ISRG', 'ADI', 'TMUS', 'CI', 'CB', 'NOW', 'DUK', 'CME',
                    'SLB', 'BDX', 'SO', 'REGN', 'NOC', 'CL', 'BSX', 'GE', 'MMC',
                    'FIS', 'AMAT', 'ATVI', 'USB', 'ICE', 'AON', 'APD', 'CSX', 'PYPL',
                    'EQIX', 'ITW', 'WM', 'FCX', 'COP', 'EMR', 'NSC', 'SHW', 'MU',
                    'PNC', 'KLAC', 'GM', 'FISV', 'TGT', 'ECL', 'F', 'D', 'MCO'
                ]
                symbols.update(sp500_symbols)
                self.logger.info(f"Added {len(sp500_symbols)} S&P 500 symbols")
            
            # NASDAQ 100 symbols (representative tech-heavy list)
            if self.config.nasdaq100_symbols:
                nasdaq100_symbols = [
                    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'AVGO',
                    'COST', 'ADBE', 'PEP', 'CSCO', 'TXN', 'NFLX', 'QCOM', 'CMCSA',
                    'INTU', 'AMD', 'HON', 'AMGN', 'SBUX', 'GILD', 'BKNG', 'ADP',
                    'VRTX', 'LRCX', 'ADI', 'ISRG', 'TMUS', 'REGN', 'AMAT', 'ATVI',
                    'PYPL', 'CHTR', 'MNST', 'CSX', 'KLAC', 'MU', 'FISV', 'MRVL',
                    'ORLY', 'WDAY', 'ASML', 'DXCM', 'SNPS', 'CDNS', 'TEAM', 'MRNA',
                    'FTNT', 'ILMN', 'EXC', 'KDP', 'CRWD', 'LULU', 'CTAS', 'PAYX',
                    'ROST', 'ODFL', 'NXPI', 'ALGN', 'CPRT', 'MCHP', 'XEL', 'CTSH',
                    'VRSK', 'PCAR', 'FAST', 'ANSS', 'VRSN', 'DLTR', 'SGEN', 'SWKS',
                    'IDXX', 'MTCH', 'ZM', 'LCID', 'DOCU', 'OKTA', 'ZS', 'DDOG'
                ]
                symbols.update(nasdaq100_symbols)
                self.logger.info(f"Added {len(nasdaq100_symbols)} NASDAQ 100 symbols")
            
            # Custom symbols
            if self.config.custom_symbols:
                symbols.update(self.config.custom_symbols)
                self.logger.info(f"Added {len(self.config.custom_symbols)} custom symbols")
            
            # Remove duplicates and convert to sorted list
            universe = sorted(list(symbols))
            self.logger.info(f"📊 Total stock universe: {len(universe)} symbols")
            
            return universe
            
        except Exception as e:
            self.logger.error(f"Error building stock universe: {e}")
            # Fallback to current config symbols
            return self.sprint_config.test_symbols
    
    def fetch_market_data(self, symbols: List[str]) -> pd.DataFrame:
        """Fetch market data for the symbol universe"""
        self.logger.info(f"📈 Fetching market data for {len(symbols)} symbols...")
        
        all_data = []
        batch_size = 50  # Process in batches to avoid API limits
        
        try:
            for i in range(0, len(symbols), batch_size):
                batch = symbols[i:i + batch_size]
                self.logger.info(f"Processing batch {i//batch_size + 1}: {len(batch)} symbols")
                
                try:
                    # Fetch data for batch
                    tickers = yf.Tickers(' '.join(batch))
                    
                    for symbol in batch:
                        try:
                            ticker = yf.Ticker(symbol)
                            # Use explicit start/end dates with correct year (2024, not 2025)
                            end_date = datetime(2024, 9, 10)  # Current date in 2024
                            start_date = end_date - timedelta(days=90)  # 3 months back
                            hist = ticker.history(start=start_date, end=end_date, interval='1d')
                            
                            if not hist.empty and len(hist) >= self.config.min_data_days:
                                # Prepare data for pre_filter
                                df = hist.reset_index()
                                df.columns = [col.lower() for col in df.columns]
                                df['symbol'] = symbol
                                
                                # Ensure required columns exist
                                required_cols = ['date', 'open', 'high', 'low', 'close', 'volume']
                                if all(col in df.columns for col in required_cols):
                                    all_data.append(df)
                                else:
                                    self.logger.warning(f"Missing columns for {symbol}")
                            else:
                                self.logger.warning(f"Insufficient data for {symbol}: {len(hist) if not hist.empty else 0} days")
                                
                        except Exception as e:
                            self.logger.warning(f"Error fetching {symbol}: {e}")
                            continue
                    
                    # Rate limiting
                    time.sleep(1)  # 1 second between batches
                    
                except Exception as e:
                    self.logger.error(f"Error processing batch: {e}")
                    continue
            
            if all_data:
                combined_df = pd.concat(all_data, ignore_index=True)
                self.logger.info(f"✅ Fetched data for {len(combined_df['symbol'].unique())} symbols")
                self.logger.info(f"📊 Combined DataFrame shape: {combined_df.shape}")
                self.logger.info(f"📅 Date range: {combined_df['date'].min()} to {combined_df['date'].max()}")
                self.logger.info(f"📈 Sample data per symbol:")
                for symbol in combined_df['symbol'].unique()[:5]:
                    symbol_data = combined_df[combined_df['symbol'] == symbol]
                    self.logger.info(f"  {symbol}: {len(symbol_data)} rows, date range: {symbol_data['date'].min()} to {symbol_data['date'].max()}")
                return combined_df
            else:
                self.logger.error("No data fetched successfully")
                return pd.DataFrame()
                
        except Exception as e:
            self.logger.error(f"Error in fetch_market_data: {e}")
            return pd.DataFrame()
    
    def generate_watchlist(self, breakout_params: Dict = None) -> List[str]:
        """Generate the daily watchlist using pre_filter with customizable breakout parameters"""
        self.logger.info("🎯 Starting watchlist generation...")
        
        try:
            # Step 1: Get stock universe
            universe = self.get_stock_universe()
            
            # Step 2: Fetch market data
            market_data = self.fetch_market_data(universe)
            
            if market_data.empty:
                self.logger.error("No market data available - using fallback watchlist")
                return self.sprint_config.test_symbols
            
            # Step 3: Apply pre_filter high-return pipeline with custom breakout parameters
            self.logger.info("🔍 Applying high-return filter pipeline...")
            
            # Use default parameters if none provided
            if breakout_params is None:
                breakout_params = {
                    'volume_multiplier': 1.2,  # More lenient than default 1.5
                    'price_breakout_pct': 0.3,  # Much more lenient 0.3% instead of 1.0%
                    'lookback_days': 15  # More lenient than default 10
                }
            
            self.logger.info(f"💥 Using breakout parameters: {breakout_params}")
            
            # Apply the pipeline with custom parameters
            filtered_data = self.apply_custom_pipeline(market_data, breakout_params)
            
            if filtered_data.empty:
                self.logger.warning("No symbols passed filters - using fallback")
                return self.sprint_config.test_symbols
            
            # Step 4: Extract final watchlist
            watchlist_symbols = filtered_data['symbol'].unique().tolist()
            
            # Step 5: Limit to max size
            if len(watchlist_symbols) > self.config.max_watchlist_size:
                # Sort by some criteria (e.g., recent volume) and take top N
                latest_data = filtered_data.groupby('symbol').tail(1)
                top_symbols = latest_data.nlargest(self.config.max_watchlist_size, 'volume')['symbol'].tolist()
                watchlist_symbols = top_symbols
            
            # Step 6: Ensure minimum size
            if len(watchlist_symbols) < self.config.min_watchlist_size:
                # Add fallback symbols
                fallback_needed = self.config.min_watchlist_size - len(watchlist_symbols)
                fallback_symbols = [s for s in self.sprint_config.test_symbols 
                                  if s not in watchlist_symbols][:fallback_needed]
                watchlist_symbols.extend(fallback_symbols)
            
            self.logger.info(f"🎯 Generated watchlist: {len(watchlist_symbols)} symbols")
            self.logger.info(f"📋 Watchlist: {watchlist_symbols}")
            
            # Update state
            self.current_watchlist = watchlist_symbols
            self.last_generated = datetime.now()
            
            return watchlist_symbols
            
        except Exception as e:
            self.logger.error(f"Error generating watchlist: {e}")
            return self.sprint_config.test_symbols
    
    def apply_custom_pipeline(self, market_data: pd.DataFrame, breakout_params: Dict) -> pd.DataFrame:
        """Apply the high-return filter pipeline with custom breakout parameters"""
        try:
            # Apply individual filters step by step
            
            # Data completeness
            filtered_data = self.pre_filter.data_completeness_filter(market_data, min_rows=60)
            self.logger.info(f"📊 After data completeness: {len(filtered_data['symbol'].unique())} symbols")
            self.logger.info(f"📊 Data completeness DataFrame shape: {filtered_data.shape}")
            
            # Liquidity and volatility (combined filter - tightened)
            filtered_data = self.pre_filter.liquidity_volatility_filter(filtered_data)
            self.logger.info(f"💰 After liquidity/volatility: {len(filtered_data['symbol'].unique())} symbols")
            self.logger.info(f"💰 Liquidity/volatility DataFrame shape: {filtered_data.shape}")
            
            # Price range
            filtered_data = self.pre_filter.price_range_filter(filtered_data, 15, 200)
            self.logger.info(f"💵 After price range: {len(filtered_data['symbol'].unique())} symbols")
            self.logger.info(f"💵 Price range DataFrame shape: {filtered_data.shape}")
            
            # Momentum
            filtered_data = self.pre_filter.momentum_filter(filtered_data)
            self.logger.info(f"🚀 After momentum: {len(filtered_data['symbol'].unique())} symbols")
            
            # Custom breakout filter with parameters (loosened)
            filtered_data = self.pre_filter.breakout_filter(
                filtered_data,
                volume_spike_min=breakout_params.get('volume_spike_min', 1.2),
                price_breakout_min=breakout_params.get('price_breakout_min', 0.003)  # 0.3% as decimal
            )
            self.logger.info(f"💥 After custom breakout: {len(filtered_data['symbol'].unique())} symbols")
            
            return filtered_data
            
        except Exception as e:
            self.logger.error(f"Error in custom pipeline: {e}")
            return pd.DataFrame()
    
    def test_breakout_configurations(self) -> Dict:
        """Test different breakout filter configurations and return results"""
        self.logger.info("🧪 Testing breakout filter configurations...")
        
        # Define test configurations
        test_configs = [
            {
                'name': 'Original Strict',
                'params': {'volume_spike_min': 1.5, 'price_breakout_min': 2.0}
            },
            {
                'name': 'Medium Lenient',
                'params': {'volume_spike_min': 1.2, 'price_breakout_min': 1.0}
            },
            {
                'name': 'Very Lenient',
                'params': {'volume_spike_min': 1.1, 'price_breakout_min': 0.5}
            }
        ]
        
        results = {}
        
        try:
            # Get stock universe and market data once
            universe = self.get_stock_universe()
            market_data = self.fetch_market_data(universe[:50])  # Test with smaller set for speed
            
            if market_data.empty:
                self.logger.error("No market data for testing")
                return results
            
            for config in test_configs:
                self.logger.info(f"Testing: {config['name']}")
                
                # Apply pipeline with this configuration
                filtered_data = self.apply_custom_pipeline(market_data, config['params'])
                symbols = filtered_data['symbol'].unique().tolist()
                
                results[config['name']] = {
                    'symbols': symbols,
                    'count': len(symbols),
                    'params': config['params']
                }
                
                self.logger.info(f"✅ {config['name']}: {len(symbols)} symbols")
        
        except Exception as e:
            self.logger.error(f"Error in breakout testing: {e}")
        
        return results
    
    def save_watchlist(self, watchlist: List[str]) -> bool:
        """Save watchlist to files and update config"""
        try:
            timestamp = datetime.now()
            
            # Save to JSON file
            if self.config.save_to_file:
                watchlist_data = {
                    'generated_at': timestamp.isoformat(),
                    'symbols': watchlist,
                    'count': len(watchlist),
                    'config': {
                        'max_size': self.config.max_watchlist_size,
                        'min_size': self.config.min_watchlist_size,
                        'pipeline': 'high_return_filter_pipeline'
                    }
                }
                
                # Ensure logs directory exists
                os.makedirs('logs', exist_ok=True)
                
                # Save current watchlist
                with open('logs/current_watchlist.json', 'w') as f:
                    json.dump(watchlist_data, f, indent=2)
                
                # Save timestamped backup
                backup_filename = f"logs/watchlist_{timestamp.strftime('%Y%m%d_%H%M%S')}.json"
                with open(backup_filename, 'w') as f:
                    json.dump(watchlist_data, f, indent=2)
                
                self.logger.info(f"💾 Watchlist saved to files")
            
            # Update config.py (if enabled)
            if self.config.save_to_config:
                success = self.update_config_file(watchlist)
                if success:
                    self.logger.info("🔄 Config.py updated successfully")
                else:
                    self.logger.warning("⚠️ Failed to update config.py")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving watchlist: {e}")
            return False
    
    def update_config_file(self, watchlist: List[str]) -> bool:
        """Update the config.py file with new watchlist"""
        try:
            config_path = 'config.py'
            
            # Read current config file
            with open(config_path, 'r') as f:
                config_content = f.read()
            
            # Create backup
            if self.config.backup_previous:
                backup_path = f"config_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
                with open(backup_path, 'w') as f:
                    f.write(config_content)
            
            # Update the test_symbols line
            # Look for the pattern and replace it
            import re
            
            # Pattern to match the test_symbols assignment
            pattern = r"self\.test_symbols = \[.*?\]"
            replacement = f"self.test_symbols = {repr(watchlist)}"
            
            updated_content = re.sub(pattern, replacement, config_content, flags=re.DOTALL)
            
            # Write updated content
            with open(config_path, 'w') as f:
                f.write(updated_content)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating config file: {e}")
            return False
    
    def is_market_closed(self) -> bool:
        """Check if market is closed (after 4:00 PM ET)"""
        try:
            from datetime import datetime
            import pytz
            
            et_tz = pytz.timezone('US/Eastern')
            now_et = datetime.now(et_tz)
            
            # Market closes at 4:00 PM ET
            market_close = now_et.replace(hour=16, minute=0, second=0, microsecond=0)
            
            # Add delay after close
            run_time = market_close + timedelta(minutes=self.config.market_close_delay_minutes)
            
            return now_et >= run_time
            
        except Exception as e:
            self.logger.error(f"Error checking market hours: {e}")
            return True  # Default to allowing run
    
    def should_generate_today(self) -> bool:
        """Check if watchlist should be generated today"""
        if self.last_generated is None:
            return True
        
        # Generate once per day
        last_date = self.last_generated.date()
        today = datetime.now().date()
        
        return today > last_date
    
    def run_daily_generation(self, breakout_params: Dict = None) -> Dict:
        """Main method to run daily watchlist generation with custom breakout parameters"""
        self.logger.info("🚀 Starting daily watchlist generation...")
        
        result = {
            'success': False,
            'watchlist': [],
            'timestamp': datetime.now().isoformat(),
            'message': ''
        }
        
        try:
            # Check if we should run today
            if not self.should_generate_today():
                result['message'] = "Watchlist already generated today"
                result['watchlist'] = self.current_watchlist
                self.logger.info("✅ Watchlist already current for today")
                return result
            
            # Check market timing
            if self.config.run_after_market_close and not self.is_market_closed():
                result['message'] = "Waiting for market close + delay"
                self.logger.info("⏰ Waiting for market close and delay period")
                return result
            
            # Generate watchlist with custom parameters
            watchlist = self.generate_watchlist(breakout_params)
            
            # Save watchlist
            save_success = self.save_watchlist(watchlist)
            
            result['success'] = True
            result['watchlist'] = watchlist
            result['message'] = f"Generated watchlist with {len(watchlist)} symbols"
            
            self.logger.info(f"✅ Daily watchlist generation complete: {len(watchlist)} symbols")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error in daily generation: {e}")
            result['message'] = f"Error: {str(e)}"
            result['watchlist'] = self.sprint_config.test_symbols  # Fallback
            return result

def main():
    """Test the dynamic watchlist generator with breakout configuration testing"""
    print("🎯 Dynamic Watchlist Generator Test")
    print("=" * 50)
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Create generator with test config
    config = WatchlistConfig(
        max_watchlist_size=10,
        min_watchlist_size=5,
        save_to_config=False,  # Don't update config during test
        save_to_file=True
    )
    
    generator = DynamicWatchlistGenerator(config)
    
    # Test different breakout configurations
    print("\n🧪 Testing Breakout Filter Configurations:")
    print("-" * 50)
    
    test_results = generator.test_breakout_configurations()
    
    for config_name, result in test_results.items():
        print(f"\n📊 {config_name}:")
        print(f"   Parameters: {result['params']}")
        print(f"   Symbols found: {result['count']}")
        print(f"   Sample symbols: {result['symbols'][:5]}")
    
    # Run generation with medium lenient parameters (recommended)
    print("\n🚀 Generating watchlist with Medium Lenient parameters...")
    result = generator.run_daily_generation(
        breakout_params={'volume_multiplier': 1.2, 'price_breakout_pct': 1.0, 'lookback_days': 15}
    )
    
    print(f"\n📊 Generation Result:")
    print(f"Success: {result['success']}")
    print(f"Message: {result['message']}")
    print(f"Watchlist ({len(result['watchlist'])}): {result['watchlist']}")
    
    return result

if __name__ == "__main__":
    main()

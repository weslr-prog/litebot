"""
Quarterly Universe Health Checker
Validates stock universe for delistings, volume issues, price range violations
"""

import json
import datetime as dt
from pathlib import Path
from typing import Dict, List, Tuple
import logging


class UniverseHealthChecker:
    """Checks universe health quarterly and prompts for review"""
    
    def __init__(self, config, data_source, logger=None):
        self.config = config
        self.data_source = data_source
        self.logger = logger or logging.getLogger(__name__)
        
        self.universe_file = Path(__file__).parent.parent / 'data' / 'mid_cap_universe.json'
        self.last_check_file = Path(__file__).parent.parent / 'data' / '.last_universe_check'
        
        # Criteria from universe JSON
        self.min_price = 5.0
        self.max_price = 50.0
        self.min_volume = 100_000
        
    def should_run_check(self) -> Tuple[bool, str]:
        """
        Check if quarterly review is due
        
        Returns:
            (should_run, reason)
        """
        today = dt.date.today()
        
        # Check if we've run this quarter
        last_check = self._get_last_check_date()
        
        if last_check:
            # Check if we're in a new quarter
            last_quarter = (last_check.year, (last_check.month - 1) // 3)
            current_quarter = (today.year, (today.month - 1) // 3)
            
            if current_quarter <= last_quarter:
                return (False, f"Already checked this quarter (last: {last_check})")
        
        # Check if it's first week of quarter (Jan, Apr, Jul, Oct)
        if today.month in [1, 4, 7, 10] and today.day <= 7:
            quarter = {1: "Q1", 4: "Q2", 7: "Q3", 10: "Q4"}[today.month]
            return (True, f"{quarter} {today.year} quarterly review due")
        
        return (False, "Not in quarterly review window")
    
    def run_health_check(self) -> Dict:
        """
        Run comprehensive health check on universe
        
        Returns:
            {
                'total_stocks': int,
                'issues_found': int,
                'delisted': List[str],
                'low_volume': List[Tuple[str, int]],
                'price_violations': List[Tuple[str, float]],
                'data_errors': List[str],
                'recommendation': str
            }
        """
        self.logger.info("=" * 80)
        self.logger.info("🏥 UNIVERSE HEALTH CHECK")
        self.logger.info("=" * 80)
        
        results = {
            'total_stocks': 0,
            'issues_found': 0,
            'delisted': [],
            'low_volume': [],
            'price_violations': [],
            'data_errors': [],
            'recommendation': ''
        }
        
        try:
            # Load universe
            with open(self.universe_file) as f:
                data = json.load(f)
            
            # Get all stocks (excluding REITs)
            all_stocks = []
            for key, value in data.items():
                if isinstance(value, list) and 'reit' not in key.lower():
                    all_stocks.extend(value)
            
            results['total_stocks'] = len(all_stocks)
            self.logger.info(f"📊 Checking {len(all_stocks)} stocks...")
            
            # Check each stock
            for symbol in all_stocks:
                try:
                    # Get recent data
                    bars = self.data_source.get_bars(
                        symbol, 
                        timeframe='1D',
                        limit=5
                    )
                    
                    if not bars or len(bars) == 0:
                        results['delisted'].append(symbol)
                        results['issues_found'] += 1
                        continue
                    
                    latest = bars[-1]
                    
                    # Check price range
                    if latest['close'] < self.min_price or latest['close'] > self.max_price:
                        results['price_violations'].append((symbol, latest['close']))
                        results['issues_found'] += 1
                    
                    # Check volume (average last 5 days)
                    avg_volume = sum(bar['volume'] for bar in bars) / len(bars)
                    if avg_volume < self.min_volume:
                        results['low_volume'].append((symbol, int(avg_volume)))
                        results['issues_found'] += 1
                
                except Exception as e:
                    results['data_errors'].append(f"{symbol}: {str(e)}")
                    results['issues_found'] += 1
            
            # Generate recommendation
            if results['issues_found'] == 0:
                results['recommendation'] = "✅ Universe is healthy - no action needed"
            elif results['issues_found'] < 5:
                results['recommendation'] = "⚠️ Minor issues found - review suggested"
            else:
                results['recommendation'] = "🚨 Significant issues found - review required"
            
            self._log_results(results)
            
        except Exception as e:
            self.logger.error(f"❌ Health check failed: {e}")
            results['recommendation'] = f"❌ Check failed: {e}"
        
        return results
    
    def _log_results(self, results: Dict):
        """Log health check results"""
        self.logger.info("")
        self.logger.info("📋 HEALTH CHECK RESULTS")
        self.logger.info("-" * 80)
        self.logger.info(f"Total stocks checked: {results['total_stocks']}")
        self.logger.info(f"Issues found: {results['issues_found']}")
        self.logger.info("")
        
        if results['delisted']:
            self.logger.warning(f"⚠️ Potentially delisted ({len(results['delisted'])}):")
            for symbol in results['delisted'][:10]:  # Show first 10
                self.logger.warning(f"   • {symbol} - No recent data")
            if len(results['delisted']) > 10:
                self.logger.warning(f"   ... and {len(results['delisted']) - 10} more")
        
        if results['low_volume']:
            self.logger.warning(f"⚠️ Low volume ({len(results['low_volume'])}):")
            for symbol, vol in results['low_volume'][:10]:
                self.logger.warning(f"   • {symbol} - {vol:,} shares/day (min: {self.min_volume:,})")
            if len(results['low_volume']) > 10:
                self.logger.warning(f"   ... and {len(results['low_volume']) - 10} more")
        
        if results['price_violations']:
            self.logger.warning(f"⚠️ Price range violations ({len(results['price_violations'])}):")
            for symbol, price in results['price_violations'][:10]:
                if price < self.min_price:
                    self.logger.warning(f"   • {symbol} - ${price:.2f} (below ${self.min_price})")
                else:
                    self.logger.warning(f"   • {symbol} - ${price:.2f} (above ${self.max_price})")
            if len(results['price_violations']) > 10:
                self.logger.warning(f"   ... and {len(results['price_violations']) - 10} more")
        
        if results['data_errors']:
            self.logger.warning(f"⚠️ Data errors ({len(results['data_errors'])}):")
            for error in results['data_errors'][:5]:
                self.logger.warning(f"   • {error}")
            if len(results['data_errors']) > 5:
                self.logger.warning(f"   ... and {len(results['data_errors']) - 5} more")
        
        self.logger.info("")
        self.logger.info(f"📊 {results['recommendation']}")
        self.logger.info("=" * 80)
    
    def mark_check_complete(self):
        """Record that quarterly check was completed"""
        today = dt.date.today()
        with open(self.last_check_file, 'w') as f:
            f.write(today.isoformat())
        self.logger.info(f"✅ Quarterly check recorded: {today}")
    
    def _get_last_check_date(self) -> dt.date:
        """Get date of last quarterly check"""
        try:
            if self.last_check_file.exists():
                with open(self.last_check_file) as f:
                    date_str = f.read().strip()
                    return dt.date.fromisoformat(date_str)
        except Exception as e:
            self.logger.debug(f"Could not read last check date: {e}")
        return None

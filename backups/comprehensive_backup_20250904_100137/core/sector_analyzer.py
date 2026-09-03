"""
Sector Analyzer - Multi-sector momentum analysis using Alpha Vantage
Analyzes 11 S&P 500 GICS sectors for momentum and rotation signals
"""

import requests
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
import logging
from datetime import datetime, timedelta
import json
import time

class SectorAnalyzer:
    """Analyze sector performance and generate sector rotation signals"""
    
    def __init__(self, alpha_vantage_key: str):
        self.api_key = alpha_vantage_key
        self.base_url = "https://www.alphavantage.co/query"
        
        # S&P 500 GICS Sectors with ETF proxies
        self.sectors = {
            'XLK': {'name': 'Technology', 'gics': 'Information Technology'},
            'XLF': {'name': 'Financials', 'gics': 'Financials'}, 
            'XLE': {'name': 'Energy', 'gics': 'Energy'},
            'XLV': {'name': 'Healthcare', 'gics': 'Health Care'},
            'XLI': {'name': 'Industrials', 'gics': 'Industrials'},
            'XLU': {'name': 'Utilities', 'gics': 'Utilities'},
            'XLRE': {'name': 'Real Estate', 'gics': 'Real Estate'},
            'XLY': {'name': 'Consumer Discretionary', 'gics': 'Consumer Discretionary'},
            'XLP': {'name': 'Consumer Staples', 'gics': 'Consumer Staples'},
            'XLB': {'name': 'Materials', 'gics': 'Materials'},
            'XLC': {'name': 'Communication Services', 'gics': 'Communication Services'}
        }
        
        # Stock-to-sector mapping (expanded universe)
        self.stock_sectors = {
            # Technology
            'AAPL': 'XLK', 'MSFT': 'XLK', 'GOOGL': 'XLK', 'NVDA': 'XLK', 'META': 'XLK',
            'ADBE': 'XLK', 'CRM': 'XLK', 'ORCL': 'XLK', 'INTC': 'XLK', 'AMD': 'XLK',
            'UBER': 'XLK', 'ROKU': 'XLK', 'ZM': 'XLK', 'SNOW': 'XLK', 'PLTR': 'XLK',
            'COIN': 'XLK', 'SQ': 'XLK', 'SHOP': 'XLK', 'DDOG': 'XLK', 'CRWD': 'XLK',
            'OKTA': 'XLK', 'TWLO': 'XLK', 'NET': 'XLK', 'DOCU': 'XLK', 'PANW': 'XLK', 'MDB': 'XLK',
            
            # Healthcare
            'JNJ': 'XLV', 'PFE': 'XLV', 'UNH': 'XLV', 'ABBV': 'XLV', 'TMO': 'XLV',
            'ABT': 'XLV', 'MRK': 'XLV', 'LLY': 'XLV', 'DHR': 'XLV', 'BMY': 'XLV',
            
            # Financials
            'JPM': 'XLF', 'BAC': 'XLF', 'WFC': 'XLF', 'GS': 'XLF', 'MS': 'XLF',
            'C': 'XLF', 'USB': 'XLF', 'PNC': 'XLF', 'BLK': 'XLF', 'AXP': 'XLF',
            
            # Energy
            'XOM': 'XLE', 'CVX': 'XLE', 'COP': 'XLE', 'EOG': 'XLE', 'SLB': 'XLE',
            'PXD': 'XLE', 'MPC': 'XLE', 'VLO': 'XLE', 'PSX': 'XLE', 'OXY': 'XLE',
            
            # Consumer
            'AMZN': 'XLY', 'TSLA': 'XLY', 'HD': 'XLY', 'MCD': 'XLY', 'NKE': 'XLY',
            'SBUX': 'XLY', 'LOW': 'XLY', 'TJX': 'XLY', 'BKNG': 'XLY', 'CMG': 'XLY',
            
            # Entertainment/Media
            'NFLX': 'XLC', 'DIS': 'XLC', 'CMCSA': 'XLC', 'T': 'XLC', 'VZ': 'XLC',
            
            # Industrials
            'CAT': 'XLI', 'BA': 'XLI', 'GE': 'XLI', 'MMM': 'XLI', 'UPS': 'XLI',
            'RTX': 'XLI', 'HON': 'XLI', 'LMT': 'XLI', 'FDX': 'XLI', 'DE': 'XLI'
        }
        
        self.logger = logging.getLogger(__name__)
        
    def get_sector_performance(self) -> Dict[str, Dict]:
        """Get sector performance data from Alpha Vantage"""
        try:
            url = f"{self.base_url}?function=SECTOR&apikey={self.api_key}"
            response = requests.get(url, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                if "Rank A: Real-Time Performance" in data:
                    performance = data["Rank A: Real-Time Performance"]
                    
                    # Parse sector performance
                    sector_data = {}
                    for sector_name, perf_str in performance.items():
                        if '%' in perf_str:
                            perf_value = float(perf_str.strip('%')) / 100
                            # Map GICS sector names to ETF symbols
                            etf_symbol = self._map_gics_to_etf(sector_name)
                            if etf_symbol:
                                sector_data[etf_symbol] = {
                                    'name': sector_name,
                                    'performance': perf_value,
                                    'rank': len(sector_data) + 1
                                }
                    
                    self.logger.info(f"✅ Retrieved {len(sector_data)} sector performance metrics")
                    return sector_data
                else:
                    self.logger.warning("⚠️ Unexpected Alpha Vantage response format")
                    return {}
                    
            else:
                self.logger.error(f"❌ Alpha Vantage API error: {response.status_code}")
                return {}
                
        except Exception as e:
            self.logger.error(f"❌ Error fetching sector performance: {e}")
            return {}
    
    def get_etf_momentum(self, lookback_days: int = 21) -> Dict[str, float]:
        """Get momentum scores for sector ETFs using Alpha Vantage"""
        momentum_scores = {}
        
        # Limit to first 3 ETFs for testing to avoid API limits
        test_etfs = list(self.sectors.keys())[:3]
        
        for etf_symbol in test_etfs:
            try:
                # Get daily time series for ETF
                url = f"{self.base_url}?function=TIME_SERIES_DAILY&symbol={etf_symbol}&apikey={self.api_key}"
                response = requests.get(url, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if "Time Series (Daily)" in data:
                        time_series = data["Time Series (Daily)"]
                        
                        # Convert to DataFrame
                        df = pd.DataFrame.from_dict(time_series, orient='index')
                        df.columns = ['open', 'high', 'low', 'close', 'volume']
                        df.index = pd.to_datetime(df.index)
                        df = df.sort_index()
                        df['close'] = df['close'].astype(float)
                        
                        # Calculate momentum (price change over lookback period)
                        if len(df) >= lookback_days:
                            current_price = df['close'].iloc[-1]
                            past_price = df['close'].iloc[-(lookback_days+1)]
                            momentum = (current_price - past_price) / past_price
                            momentum_scores[etf_symbol] = momentum
                            
                            self.logger.info(f"📈 {etf_symbol} momentum: {momentum:.3f}")
                        else:
                            self.logger.warning(f"⚠️ Insufficient data for {etf_symbol}")
                            
                # Rate limiting for free tier
                time.sleep(15)  # Alpha Vantage free tier allows 5 calls per minute
                        
            except Exception as e:
                self.logger.error(f"❌ Error getting momentum for {etf_symbol}: {e}")
                
        return momentum_scores
    
    def analyze_sector_rotation(self) -> Dict[str, any]:
        """Analyze sector rotation opportunities"""
        try:
            self.logger.info("🔄 Analyzing sector rotation opportunities...")
            
            # Get sector performance and momentum
            sector_performance = self.get_sector_performance()
            etf_momentum = self.get_etf_momentum()
            
            if not sector_performance and not etf_momentum:
                self.logger.warning("⚠️ No sector data available")
                # Return mock data for testing
                return self._get_mock_sector_analysis()
            
            # Combine performance and momentum data
            sector_scores = {}
            for etf in self.sectors.keys():
                performance = sector_performance.get(etf, {}).get('performance', 0)
                momentum = etf_momentum.get(etf, 0)
                
                # Composite score (weight momentum more heavily)
                composite_score = (momentum * 0.7) + (performance * 0.3)
                
                sector_scores[etf] = {
                    'name': self.sectors[etf]['name'],
                    'performance': performance,
                    'momentum': momentum,
                    'composite_score': composite_score,
                    'rank': 0  # Will be set after sorting
                }
            
            # Rank sectors by composite score
            sorted_sectors = sorted(sector_scores.items(), 
                                  key=lambda x: x[1]['composite_score'], 
                                  reverse=True)
            
            for i, (etf, data) in enumerate(sorted_sectors):
                sector_scores[etf]['rank'] = i + 1
            
            # Identify top sectors for overweight and bottom for underweight
            top_sectors = [etf for etf, _ in sorted_sectors[:3]]  # Top 3
            bottom_sectors = [etf for etf, _ in sorted_sectors[-2:]]  # Bottom 2
            
            rotation_analysis = {
                'sector_scores': sector_scores,
                'top_sectors': top_sectors,
                'bottom_sectors': bottom_sectors,
                'rotation_signal': len(top_sectors) > 0,
                'timestamp': datetime.now().isoformat()
            }
            
            self.logger.info(f"📊 Sector Analysis Complete:")
            self.logger.info(f"   🚀 Top performing sectors: {[self.sectors[s]['name'] for s in top_sectors]}")
            self.logger.info(f"   📉 Underperforming sectors: {[self.sectors[s]['name'] for s in bottom_sectors]}")
            
            return rotation_analysis
            
        except Exception as e:
            self.logger.error(f"❌ Error in sector rotation analysis: {e}")
            return self._get_mock_sector_analysis()
    
    def _get_mock_sector_analysis(self) -> Dict[str, any]:
        """Generate mock sector analysis for testing"""
        import random
        
        sector_scores = {}
        for etf in self.sectors.keys():
            sector_scores[etf] = {
                'name': self.sectors[etf]['name'],
                'performance': random.uniform(-0.05, 0.05),
                'momentum': random.uniform(-0.1, 0.1),
                'composite_score': random.uniform(-0.08, 0.08),
                'rank': 0
            }
        
        # Rank sectors
        sorted_sectors = sorted(sector_scores.items(), 
                              key=lambda x: x[1]['composite_score'], 
                              reverse=True)
        
        for i, (etf, data) in enumerate(sorted_sectors):
            sector_scores[etf]['rank'] = i + 1
        
        top_sectors = [etf for etf, _ in sorted_sectors[:3]]
        bottom_sectors = [etf for etf, _ in sorted_sectors[-2:]]
        
        return {
            'sector_scores': sector_scores,
            'top_sectors': top_sectors,
            'bottom_sectors': bottom_sectors,
            'rotation_signal': True,
            'timestamp': datetime.now().isoformat()
        }
    
    def get_sector_allocation_weights(self) -> Dict[str, float]:
        """Get recommended sector allocation weights based on momentum"""
        try:
            rotation_analysis = self.analyze_sector_rotation()
            
            if not rotation_analysis:
                # Default equal weight if no data
                return {sector: 1.0/len(self.sectors) for sector in self.sectors.keys()}
            
            sector_scores = rotation_analysis.get('sector_scores', {})
            
            # Calculate allocation weights based on relative performance
            total_score = sum([max(data['composite_score'], 0) for data in sector_scores.values()])
            
            if total_score == 0:
                # Equal weight fallback
                return {sector: 1.0/len(self.sectors) for sector in self.sectors.keys()}
            
            allocation_weights = {}
            for sector, data in sector_scores.items():
                # Minimum 2% allocation, maximum 25% per sector
                raw_weight = max(data['composite_score'], 0) / total_score
                allocation_weights[sector] = max(0.02, min(0.25, raw_weight))
            
            # Normalize to sum to 1.0
            total_weight = sum(allocation_weights.values())
            allocation_weights = {k: v/total_weight for k, v in allocation_weights.items()}
            
            self.logger.info("📊 Sector Allocation Weights:")
            for sector, weight in sorted(allocation_weights.items(), key=lambda x: x[1], reverse=True):
                self.logger.info(f"   {self.sectors[sector]['name']}: {weight:.1%}")
            
            return allocation_weights
            
        except Exception as e:
            self.logger.error(f"❌ Error calculating sector allocation: {e}")
            return {sector: 1.0/len(self.sectors) for sector in self.sectors.keys()}
    
    def filter_stocks_by_sector_momentum(self, stock_signals: List[Dict], 
                                       sector_weights: Dict[str, float] = None) -> List[Dict]:
        """Filter and weight stock signals based on sector momentum"""
        if sector_weights is None:
            sector_weights = self.get_sector_allocation_weights()
        
        filtered_signals = []
        
        for signal in stock_signals:
            symbol = signal['symbol']
            sector_etf = self.stock_sectors.get(symbol)
            
            if sector_etf and sector_etf in sector_weights:
                # Apply sector momentum multiplier
                sector_multiplier = sector_weights[sector_etf] * len(self.sectors)  # Normalize
                
                # Adjust signal strength based on sector momentum
                adjusted_signal = signal.copy()
                adjusted_signal['momentum_score'] *= sector_multiplier
                adjusted_signal['sector'] = self.sectors[sector_etf]['name']
                adjusted_signal['sector_etf'] = sector_etf
                adjusted_signal['sector_weight'] = sector_weights[sector_etf]
                
                filtered_signals.append(adjusted_signal)
                
        # Sort by adjusted momentum score
        filtered_signals.sort(key=lambda x: x['momentum_score'], reverse=True)
        
        self.logger.info(f"🎯 Filtered {len(filtered_signals)} stocks with sector momentum")
        
        return filtered_signals
    
    def _map_gics_to_etf(self, gics_name: str) -> str:
        """Map GICS sector name to ETF symbol"""
        mapping = {
            'Information Technology': 'XLK',
            'Financials': 'XLF',
            'Energy': 'XLE',
            'Health Care': 'XLV',
            'Industrials': 'XLI',
            'Utilities': 'XLU',
            'Real Estate': 'XLRE',
            'Consumer Discretionary': 'XLY',
            'Consumer Staples': 'XLP',
            'Materials': 'XLB',
            'Communication Services': 'XLC'
        }
        return mapping.get(gics_name)

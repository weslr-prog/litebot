"""
Relative Strength and Sector Rotation Module
Enhancement #5 & #6 for PreFilter
Adds market-relative performance and sector rotation analysis
"""

import pandas as pd
import numpy as np
import yfinance as yf
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

class RelativeStrengthAnalyzer:
    """Calculate relative strength vs SPY (market benchmark)"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__ + ".RelativeStrengthAnalyzer")
        self.spy_data = None
        self.spy_cache_time = None
        self.cache_duration = timedelta(hours=1)  # Cache SPY data for 1 hour
    
    def get_spy_returns(self, lookback_days: int = 20) -> Optional[pd.Series]:
        """Get SPY returns with caching"""
        now = datetime.now()
        
        # Check if cache is valid
        if (self.spy_data is not None and 
            self.spy_cache_time is not None and 
            (now - self.spy_cache_time) < self.cache_duration):
            return self.spy_data
        
        try:
            spy = yf.Ticker("SPY")
            hist = spy.history(period=f"{lookback_days+5}d")
            
            if hist.empty or len(hist) < lookback_days:
                self.logger.warning(f"⚠️ Insufficient SPY data: {len(hist)} days")
                return None
            
            spy_returns = hist['Close'].pct_change()
            self.spy_data = spy_returns
            self.spy_cache_time = now
            
            self.logger.info(f"✅ SPY returns cached: {len(spy_returns)} days")
            return spy_returns
            
        except Exception as e:
            self.logger.error(f"❌ Error fetching SPY data: {e}")
            return None
    
    def calculate_relative_strength(self, df: pd.DataFrame, lookback: int = 20) -> pd.DataFrame:
        """
        Calculate relative strength vs SPY for each symbol
        RS > 1.0 means outperforming market
        RS < 1.0 means underperforming market
        """
        self.logger.info(f"📊 Calculating relative strength vs SPY ({lookback}d lookback)")
        
        # Get SPY returns
        spy_returns = self.get_spy_returns(lookback)
        if spy_returns is None:
            self.logger.warning("⚠️ No SPY data, skipping relative strength filter")
            df['relative_strength'] = 1.0  # Neutral if can't calculate
            return df
        
        # Calculate stock returns and relative strength
        result_df = df.copy()
        result_df['relative_strength'] = np.nan
        
        for symbol in result_df['symbol'].unique():
            symbol_data = result_df[result_df['symbol'] == symbol].sort_values('date')
            
            if len(symbol_data) < lookback:
                continue
            
            # Calculate stock returns over lookback period
            stock_returns = symbol_data['close'].pct_change().tail(lookback)
            stock_total_return = (1 + stock_returns).prod() - 1
            
            # Calculate SPY total return over same period
            spy_total_return = (1 + spy_returns.tail(lookback)).prod() - 1
            
            # Relative strength = stock return / market return
            # RS > 1.0 = outperforming
            if spy_total_return != 0:
                rs = (1 + stock_total_return) / (1 + spy_total_return)
            else:
                rs = 1.0
            
            # Update all rows for this symbol
            result_df.loc[result_df['symbol'] == symbol, 'relative_strength'] = rs
        
        # Count strong stocks
        strong_stocks = result_df[result_df['relative_strength'] > 1.0]['symbol'].unique()
        self.logger.info(f"💪 {len(strong_stocks)} stocks outperforming SPY (RS > 1.0)")
        
        return result_df
    
    def filter_by_relative_strength(self, df: pd.DataFrame, min_rs: float = 1.0) -> pd.DataFrame:
        """Filter stocks by minimum relative strength"""
        if 'relative_strength' not in df.columns:
            self.logger.warning("⚠️ No relative_strength column, calculating now...")
            df = self.calculate_relative_strength(df)
        
        # Get latest RS per symbol
        latest = df.groupby('symbol').tail(1)
        strong_symbols = latest[latest['relative_strength'] >= min_rs]['symbol'].tolist()
        
        self.logger.info(f"📈 RS Filter: {len(strong_symbols)} stocks with RS ≥ {min_rs}")
        
        return df[df['symbol'].isin(strong_symbols)]


class SectorRotationAnalyzer:
    """Identify leading sectors and boost scores for stocks in strong sectors"""
    
    def __init__(self, sector_analyzer=None):
        self.logger = logging.getLogger(__name__ + ".SectorRotationAnalyzer")
        self.sector_analyzer = sector_analyzer
        
        # Stock-to-sector mapping (from sector_analyzer.py)
        self.stock_sectors = {
            # Technology
            'AAPL': 'Technology', 'MSFT': 'Technology', 'GOOGL': 'Technology', 'NVDA': 'Technology',
            'META': 'Technology', 'ADBE': 'Technology', 'CRM': 'Technology', 'ORCL': 'Technology',
            'INTC': 'Technology', 'AMD': 'Technology', 'AVGO': 'Technology', 'CSCO': 'Technology',
            'QCOM': 'Technology', 'SHOP': 'Technology', 'UBER': 'Technology', 'LYFT': 'Technology',
            
            # Healthcare
            'JNJ': 'Healthcare', 'PFE': 'Healthcare', 'UNH': 'Healthcare', 'ABBV': 'Healthcare',
            'TMO': 'Healthcare', 'LLY': 'Healthcare', 'BMY': 'Healthcare', 'GILD': 'Healthcare',
            'MDT': 'Healthcare',
            
            # Financials
            'JPM': 'Financials', 'BAC': 'Financials', 'WFC': 'Financials', 'GS': 'Financials',
            'MS': 'Financials', 'C': 'Financials', 'V': 'Financials', 'MA': 'Financials',
            
            # Energy
            'XOM': 'Energy', 'CVX': 'Energy',
            
            # Consumer
            'AMZN': 'Consumer Discretionary', 'TSLA': 'Consumer Discretionary', 
            'HD': 'Consumer Discretionary', 'MCD': 'Consumer Discretionary',
            'NKE': 'Consumer Discretionary', 'SBUX': 'Consumer Discretionary',
            'COST': 'Consumer Discretionary', 'WMT': 'Consumer Staples',
            'KO': 'Consumer Staples', 'PEP': 'Consumer Staples',
            
            # Communication Services
            'NFLX': 'Communication Services', 'DIS': 'Communication Services',
            'T': 'Communication Services', 'VZ': 'Communication Services',
            
            # Industrials
            'CAT': 'Industrials', 'BA': 'Industrials', 'GE': 'Industrials',
            'MMM': 'Industrials', 'UPS': 'Industrials', 'HON': 'Industrials',
            'F': 'Industrials', 'GM': 'Industrials',
            
            # Other
            'ACN': 'Technology', 'TXN': 'Technology'
        }
    
    def identify_leading_sectors(self, df: pd.DataFrame, top_n: int = 3) -> List[str]:
        """Identify top N performing sectors based on average stock performance"""
        self.logger.info(f"🎯 Identifying top {top_n} performing sectors")
        
        # Calculate average return by sector
        sector_performance = {}
        
        for symbol in df['symbol'].unique():
            sector = self.stock_sectors.get(symbol, 'Unknown')
            if sector == 'Unknown':
                continue
            
            symbol_data = df[df['symbol'] == symbol].sort_values('date')
            if len(symbol_data) < 2:
                continue
            
            # Calculate recent return (last 5 days)
            recent_return = (symbol_data['close'].iloc[-1] / symbol_data['close'].iloc[-5] - 1) if len(symbol_data) >= 5 else 0
            
            if sector not in sector_performance:
                sector_performance[sector] = []
            sector_performance[sector].append(recent_return)
        
        # Average performance per sector
        sector_avg = {sector: np.mean(returns) for sector, returns in sector_performance.items()}
        
        # Sort and get top N
        sorted_sectors = sorted(sector_avg.items(), key=lambda x: x[1], reverse=True)
        leading_sectors = [s[0] for s in sorted_sectors[:top_n]]
        
        self.logger.info(f"🏆 Leading sectors: {leading_sectors}")
        for sector, perf in sorted_sectors[:top_n]:
            self.logger.info(f"   {sector}: {perf:+.2%}")
        
        return leading_sectors
    
    def boost_scores_for_strong_sectors(self, df: pd.DataFrame, 
                                       leading_sectors: List[str],
                                       boost_factor: float = 1.2) -> pd.DataFrame:
        """Boost composite scores for stocks in leading sectors"""
        result_df = df.copy()
        
        if 'sector_boost' not in result_df.columns:
            result_df['sector_boost'] = 1.0
        
        for symbol in result_df['symbol'].unique():
            sector = self.stock_sectors.get(symbol, 'Unknown')
            if sector in leading_sectors:
                result_df.loc[result_df['symbol'] == symbol, 'sector_boost'] = boost_factor
                self.logger.debug(f"📈 {symbol}: Boosted for {sector} sector strength")
        
        boosted_count = len(result_df[result_df['sector_boost'] > 1.0]['symbol'].unique())
        self.logger.info(f"✨ Applied sector boost to {boosted_count} stocks in leading sectors")
        
        return result_df
    
    def add_sector_rotation_signal(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add sector rotation analysis to dataframe"""
        # Identify leading sectors
        leading_sectors = self.identify_leading_sectors(df, top_n=3)
        
        # Boost scores for stocks in leading sectors
        df = self.boost_scores_for_strong_sectors(df, leading_sectors)
        
        # Add sector labels
        df['sector'] = df['symbol'].map(self.stock_sectors)
        df['in_leading_sector'] = df['sector'].isin(leading_sectors)
        
        return df


def enhance_prefilter_with_rs_and_sectors(df: pd.DataFrame) -> pd.DataFrame:
    """
    Main function to enhance PreFilter results with:
    1. Relative strength vs SPY
    2. Sector rotation analysis
    """
    logging.info("=" * 60)
    logging.info("🚀 ENHANCEMENT #5 & #6: Relative Strength + Sector Rotation")
    logging.info("=" * 60)
    
    # Step 1: Calculate relative strength
    rs_analyzer = RelativeStrengthAnalyzer()
    df = rs_analyzer.calculate_relative_strength(df, lookback=20)
    df = rs_analyzer.filter_by_relative_strength(df, min_rs=0.98)  # Allow slight underperformance
    
    # Step 2: Add sector rotation signals
    sector_analyzer = SectorRotationAnalyzer()
    df = sector_analyzer.add_sector_rotation_signal(df)
    
    logging.info("=" * 60)
    logging.info("✅ Enhancement complete")
    logging.info("=" * 60)
    
    return df

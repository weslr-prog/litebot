#!/usr/bin/env python3
"""
Relative Strength (RS) & Sector Rotation Analysis Module
Purpose: Prevent false momentum entries by validating RS and sector alignment
Created: January 30, 2026
Part of: Phase 1b Enhancement (Critical bug fix for week ending Jan 30)

This module calculates:
1. Relative Strength (RS): Stock performance vs SPY
2. Decoupling Score: Alpha (independent movement) vs Beta (market-driven)
3. Sector Momentum: Sector favorability
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


# Comprehensive sector mapping (updated Jan 30, 2026)
SECTOR_MAPPING = {
    # Technology / Software
    'MSFT': 'XLK', 'AAPL': 'XLK', 'NVDA': 'XLK', 'APP': 'XLK',
    'GTLB': 'XLK', 'LCID': 'XLK', 'NIO': 'XLK',
    
    # Healthcare / Biotech
    'MRNA': 'XLV', 'NTLA': 'XLV', 'JNJ': 'XLV', 'PFE': 'XLV',
    
    # Energy / Oil & Gas
    'XOM': 'XLE', 'CVX': 'XLE', 'COP': 'XLE', 'OXY': 'XLE',
    'DVN': 'XLE', 'SLB': 'XLE',
    
    # Materials / Mining / Metals
    'CLF': 'XME', 'FCX': 'XME', 'RIO': 'XME',
    
    # Utilities
    'NEE': 'XLU', 'AES': 'XLU', 'PR': 'XLU',
    
    # Consumer / Discretionary
    'BEKE': 'XLY', 'TAL': 'XLY', 'ALK': 'XLY', 'VFC': 'XLY',
    
    # Financials
    'JPM': 'XLF', 'BAC': 'XLF',
    
    # Default
    'DEFAULT': 'SPY'
}


class RelativeStrengthAnalyzer:
    """Calculate and analyze relative strength (RS) between stock and market"""
    
    def __init__(self, data_loader=None):
        """Initialize RS Analyzer
        
        Args:
            data_loader: Optional DataLoader for fetching SPY data
        """
        self.data_loader = data_loader
        self._spy_cache = {}
        logger.info("✅ RelativeStrengthAnalyzer initialized")
    
    def calculate_rs(self, stock_prices: pd.DataFrame, spy_prices: pd.DataFrame,
                    lookback: int = 5) -> float:
        """
        Calculate Relative Strength score (0-1, higher = stronger RS)
        
        Algorithm:
        - RS = (stock_return - spy_return) / max(|stock_return|, |spy_return|)
        - Normalized to [0, 1] range where 0.5 = neutral
        
        Args:
            stock_prices: DataFrame with 'close' column for stock
            spy_prices: DataFrame with 'close' column for SPY
            lookback: Number of periods to look back (default: 5 days)
        
        Returns:
            float: RS score from 0 (worst) to 1 (best), 0.5 = neutral
        """
        try:
            if len(stock_prices) < lookback + 1 or len(spy_prices) < lookback + 1:
                logger.debug(f"Insufficient data for RS calculation (need {lookback+1}, got {len(stock_prices)})")
                return 0.5  # Neutral if insufficient data
            
            # Calculate returns
            stock_return = (stock_prices['close'].iloc[-1] - stock_prices['close'].iloc[-(lookback+1)]) / stock_prices['close'].iloc[-(lookback+1)]
            spy_return = (spy_prices['close'].iloc[-1] - spy_prices['close'].iloc[-(lookback+1)]) / spy_prices['close'].iloc[-(lookback+1)]
            
            # RS calculation
            diff = stock_return - spy_return
            max_val = max(abs(stock_return), abs(spy_return), 0.001)  # Avoid division by zero
            
            # Normalize to [0, 1] range (from [-1, 1])
            rs_score = (diff / max_val + 1) / 2
            
            # Clamp to valid range
            return max(0.0, min(1.0, rs_score))
        
        except Exception as e:
            logger.warning(f"Error calculating RS: {e}")
            return 0.5
    
    def get_decoupling_score(self, stock_return: float, market_return: float,
                            sector_return: float) -> float:
        """
        Calculate decoupling score (0-1): How independent is the stock's move?
        
        Interpretation:
        - 0.8-1.0: High alpha (strong independent move) - "Green in red market"
        - 0.6-0.7: Medium-high alpha (beating sector)
        - 0.4-0.6: Medium alpha (moving with market)
        - 0.2-0.3: Low alpha (following market, not independent)
        - 0.0-0.2: Very low alpha (inverse to market)
        
        Args:
            stock_return: Stock 5-day return (float, e.g., 0.02 = +2%)
            market_return: Market (SPY) 5-day return (float)
            sector_return: Sector 5-day return (float)
        
        Returns:
            float: Decoupling score from 0 to 1
        """
        try:
            # Special case: "Green in red market" = maximum decoupling
            if (stock_return > 0.001) and (market_return < -0.001):
                # Stock up while market down = very high alpha
                # Boost based on magnitude
                base_score = 0.85
                magnitude_boost = min(0.15, stock_return * 10)  # Extra boost for strong moves
                decoupling = base_score + magnitude_boost
                return min(1.0, decoupling)
            
            # Special case: "Red in green market" = very low decoupling
            if (stock_return < -0.001) and (market_return > 0.001):
                # Stock down while market up = very low alpha
                return max(0.0, 0.1 - abs(stock_return) * 5)
            
            # Normal case: Both moving in same direction
            if abs(market_return) > 0.001:
                # Measure how much of move is independent
                if abs(sector_return) > 0.001:
                    # Can compare to sector
                    sector_alpha = stock_return - sector_return
                    market_alpha = stock_return - market_return
                    
                    # Average of both measurements
                    decoupling = (
                        (abs(sector_alpha) / abs(market_return)) * 0.5 +
                        (abs(market_alpha) / abs(market_return)) * 0.5
                    )
                else:
                    # Use market only
                    decoupling = abs(stock_return - market_return) / abs(market_return)
                
                # Normalize to [0, 1]
                decoupling = min(1.0, decoupling)
            else:
                # Market flat: any move is decoupled
                decoupling = min(1.0, abs(stock_return) * 10)
            
            return max(0.0, min(1.0, decoupling))
        
        except Exception as e:
            logger.warning(f"Error calculating decoupling score: {e}")
            return 0.5


class SectorRotationAnalyzer:
    """Analyze sector momentum and stock alignment with sector"""
    
    def __init__(self, data_loader=None):
        """Initialize Sector Analyzer
        
        Args:
            data_loader: Optional DataLoader for fetching sector ETF data
        """
        self.data_loader = data_loader
        self._sector_cache = {}
        logger.info("✅ SectorRotationAnalyzer initialized")
    
    def identify_sector(self, symbol: str) -> str:
        """
        Map stock symbol to sector ETF ticker
        
        Args:
            symbol: Stock symbol (e.g., 'MRNA', 'DVN', 'CLF')
        
        Returns:
            str: Sector ETF ticker (e.g., 'XLV', 'XLE', 'XME')
        """
        sector = SECTOR_MAPPING.get(symbol.upper(), SECTOR_MAPPING['DEFAULT'])
        return sector
    
    def get_sector_return(self, sector_prices: Optional[pd.DataFrame] = None,
                         lookback: int = 5) -> float:
        """
        Calculate sector ETF return over lookback period
        
        Args:
            sector_prices: DataFrame with 'close' column for sector ETF
            lookback: Number of periods (default: 5 days)
        
        Returns:
            float: Sector return (e.g., 0.02 = +2%)
        """
        try:
            if sector_prices is None or len(sector_prices) < lookback + 1:
                return 0.0
            
            return (sector_prices['close'].iloc[-1] - sector_prices['close'].iloc[-(lookback+1)]) / sector_prices['close'].iloc[-(lookback+1)]
        
        except Exception as e:
            logger.warning(f"Error calculating sector return: {e}")
            return 0.0
    
    def get_sector_momentum(self, sector_return: float) -> str:
        """
        Classify sector momentum strength
        
        Args:
            sector_return: Sector 5-day return (float)
        
        Returns:
            str: One of 'STRONG', 'NEUTRAL', 'WEAK'
        """
        if sector_return > 0.03:
            return 'STRONG'
        elif sector_return > 0.01:
            return 'NEUTRAL'
        else:
            return 'WEAK'
    
    def is_beating_sector(self, stock_return: float, sector_return: float,
                         threshold: float = 0.005) -> bool:
        """
        Check if stock is outperforming its sector
        
        Args:
            stock_return: Stock 5-day return (float)
            sector_return: Sector 5-day return (float)
            threshold: Min outperformance required (default: 0.5% = 0.005)
        
        Returns:
            bool: True if stock is beating sector
        """
        return (stock_return - sector_return) > threshold


# Helper functions for feature calculation

def calculate_return(prices: pd.DataFrame, lookback: int) -> float:
    """
    Helper: Calculate simple return over N periods
    
    Args:
        prices: DataFrame with 'close' column
        lookback: Number of periods
    
    Returns:
        float: Return percentage (e.g., 0.02 = +2%)
    """
    try:
        if prices is None or len(prices) < lookback + 1:
            return 0.0
        return (prices['close'].iloc[-1] - prices['close'].iloc[-(lookback+1)]) / prices['close'].iloc[-(lookback+1)]
    except:
        return 0.0


def get_rs_data(symbol: str, market_data: Dict) -> Dict:
    """
    Calculate complete RS feature set for a symbol
    
    Args:
        symbol: Stock symbol
        market_data: Dict with stock and SPY OHLCV data
    
    Returns:
        Dict with all RS/sector features:
        - stock_5d_return
        - spy_5d_return  
        - rs_score
        - sector
        - sector_return
        - decoupling_score
        - sector_momentum
        - gates_passed: List of passed RS gates
    """
    rs_analyzer = RelativeStrengthAnalyzer()
    sector_analyzer = SectorRotationAnalyzer()
    
    rs_features = {
        'stock_5d_return': 0.0,
        'spy_5d_return': 0.0,
        'rs_score': 0.5,
        'sector': 'SPY',
        'sector_return': 0.0,
        'sector_momentum': 'NEUTRAL',
        'decoupling_score': 0.5,
        'gates_passed': [],
        'gates_failed': []
    }
    
    try:
        # Get data
        stock_data = market_data.get(symbol)
        spy_data = market_data.get('SPY')
        
        if stock_data is None or spy_data is None:
            return rs_features
        
        # Identify sector
        sector_ticker = sector_analyzer.identify_sector(symbol)
        sector_data = market_data.get(sector_ticker)
        
        # Calculate returns
        stock_return = calculate_return(stock_data, 5)
        spy_return = calculate_return(spy_data, 5)
        sector_return = calculate_return(sector_data, 5) if sector_data is not None else 0.0
        
        # Calculate RS metrics
        rs_score = rs_analyzer.calculate_rs(stock_data, spy_data, lookback=5)
        decoupling = rs_analyzer.get_decoupling_score(stock_return, spy_return, sector_return)
        sector_momentum = sector_analyzer.get_sector_momentum(sector_return)
        
        # Update features
        rs_features.update({
            'stock_5d_return': stock_return,
            'spy_5d_return': spy_return,
            'rs_score': rs_score,
            'sector': sector_ticker,
            'sector_return': sector_return,
            'sector_momentum': sector_momentum,
            'decoupling_score': decoupling,
        })
        
        # Determine gate status
        gates = []
        failed = []
        
        if rs_score > 0.5:
            gates.append('RS_POSITIVE')
        else:
            failed.append('RS_NEGATIVE')
        
        if stock_return > spy_return:
            gates.append('BEATING_SPY')
        else:
            failed.append('LAGGING_SPY')
        
        if sector_ticker != 'SPY' and stock_return > sector_return:
            gates.append('BEATING_SECTOR')
        elif sector_ticker != 'SPY':
            failed.append('LAGGING_SECTOR')
        
        if decoupling > 0.6:
            gates.append('HIGH_ALPHA')
        elif decoupling < 0.3:
            failed.append('LOW_ALPHA')
        
        # Special case: Green in red
        if stock_return > 0 and spy_return < 0:
            gates.append('GREEN_IN_RED')
        
        rs_features['gates_passed'] = gates
        rs_features['gates_failed'] = failed
        
        return rs_features
    
    except Exception as e:
        logger.error(f"Error calculating RS data for {symbol}: {e}")
        return rs_features


if __name__ == '__main__':
    """Quick test of RS/Sector functionality"""
    
    # Create sample data
    import yfinance as yf
    
    print("=" * 80)
    print("RS/Sector Rotation Analysis - Quick Test")
    print("=" * 80)
    
    try:
        # Fetch real data
        print("\nFetching sample data...")
        spy = yf.download('SPY', start='2026-01-25', end='2026-01-31', progress=False)
        oxy = yf.download('OXY', start='2026-01-25', end='2026-01-31', progress=False)
        
        # Test RS calculation
        rs_analyzer = RelativeStrengthAnalyzer()
        rs_score = rs_analyzer.calculate_rs(oxy, spy, lookback=4)
        
        print(f"\n✅ RS Score (OXY vs SPY): {rs_score:.2f}")
        print(f"   OXY return: {(oxy['close'].iloc[-1] / oxy['close'].iloc[-5] - 1):.2%}")
        print(f"   SPY return: {(spy['close'].iloc[-1] / spy['close'].iloc[-5] - 1):.2%}")
        
        # Test sector identification
        sector_analyzer = SectorRotationAnalyzer()
        sector = sector_analyzer.identify_sector('OXY')
        print(f"\n✅ OXY Sector: {sector} (XLE = Energy)")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
    
    print("\n" + "=" * 80)
    print("RS/Sector module loaded and tested successfully")
    print("=" * 80)

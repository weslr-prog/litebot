"""
Phase 1: Core Momentum Strategy Implementation
Focus: Cross-sectional momentum with simple, robust signals
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Tuple
from datetime import datetime, timedelta


class MomentumStrategy:
    """
    Phase 1 Momentum Strategy - Academic-validated cross-sectional momentum
    
    Key Features:
    - 1M/3M momentum ranking
    - Liquidity filtering
    - Sector diversification
    - ATR-based position sizing
    """
    
    def __init__(self, lookback_1m=21, lookback_2m=42, min_volume=10_000_000):
        self.lookback_1m = lookback_1m  # 1-month lookback
        self.lookback_2m = lookback_2m  # 2-month lookback (adjusted for available data)
        self.min_volume = min_volume    # Minimum daily volume
        self.max_positions = 10         # Maximum number of positions
        self.position_size_pct = 0.05   # 5% per position max
        
        logging.info(f"🎯 MomentumStrategy initialized: {lookback_1m}d/{lookback_2m}d lookbacks")
    
    def calculate_momentum_score(self, price_data: pd.DataFrame) -> float:
        """
        Calculate combined momentum score using academic methodology
        Adjusted for available data (2-month max lookback)
        
        Returns:
            float: Combined momentum score (higher = better momentum)
        """
        if len(price_data) < self.lookback_2m:
            return np.nan
            
        try:
            # Get recent prices
            current_price = price_data['close'].iloc[-1]
            price_1m_ago = price_data['close'].iloc[-self.lookback_1m]
            price_2m_ago = price_data['close'].iloc[-self.lookback_2m]
            
            # Calculate returns
            return_1m = (current_price / price_1m_ago) - 1
            return_2m = (current_price / price_2m_ago) - 1
            
            # Weighted combination (favor longer-term momentum slightly)
            momentum_score = 0.4 * return_1m + 0.6 * return_2m
            
            return momentum_score
            
        except Exception as e:
            logging.warning(f"Error calculating momentum: {e}")
            return np.nan
    
    def calculate_volatility(self, price_data: pd.DataFrame, lookback=20) -> float:
        """Calculate ATR-based volatility for position sizing"""
        if len(price_data) < lookback:
            return np.nan
            
        try:
            # Calculate True Range
            high = price_data['high'].iloc[-lookback:]
            low = price_data['low'].iloc[-lookback:]
            close = price_data['close'].iloc[-lookback:]
            prev_close = close.shift(1)
            
            tr1 = high - low
            tr2 = abs(high - prev_close)
            tr3 = abs(low - prev_close)
            
            true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = true_range.mean()
            
            return atr / price_data['close'].iloc[-1]  # Normalized ATR
            
        except Exception as e:
            logging.warning(f"Error calculating volatility: {e}")
            return np.nan
    
    def check_liquidity_filter(self, price_data: pd.DataFrame) -> bool:
        """Check if symbol meets liquidity requirements"""
        try:
            # Average volume over last 20 days
            avg_volume = price_data['volume'].iloc[-20:].mean()
            avg_price = price_data['close'].iloc[-20:].mean()
            
            # Dollar volume
            dollar_volume = avg_volume * avg_price
            
            return dollar_volume >= self.min_volume
            
        except Exception as e:
            logging.warning(f"Error checking liquidity: {e}")
            return False
    
    def rank_universe(self, universe_data: Dict[str, pd.DataFrame]) -> List[Dict]:
        """
        Rank entire universe by momentum score
        
        Args:
            universe_data: Dict of {symbol: price_dataframe}
            
        Returns:
            List of dicts with symbol, momentum_score, volatility, liquidity
        """
        candidates = []
        
        for symbol, price_data in universe_data.items():
            if price_data is None or len(price_data) < self.lookback_2m:
                continue
                
            # Calculate metrics
            momentum_score = self.calculate_momentum_score(price_data)
            volatility = self.calculate_volatility(price_data)
            liquidity_ok = self.check_liquidity_filter(price_data)
            
            if not np.isnan(momentum_score) and liquidity_ok:
                candidates.append({
                    'symbol': symbol,
                    'momentum_score': momentum_score,
                    'volatility': volatility,
                    'current_price': price_data['close'].iloc[-1],
                    'avg_volume': price_data['volume'].iloc[-20:].mean()
                })
        
        # Sort by momentum score (descending)
        candidates.sort(key=lambda x: x['momentum_score'], reverse=True)
        
        logging.info(f"📊 Ranked {len(candidates)} liquid symbols by momentum")
        
        return candidates
    
    def calculate_position_sizes(self, top_candidates: List[Dict], 
                                portfolio_value: float) -> List[Dict]:
        """
        Calculate position sizes using volatility scaling
        
        Args:
            top_candidates: List of top momentum candidates
            portfolio_value: Current portfolio value
            
        Returns:
            List of position recommendations with sizes
        """
        positions = []
        max_candidates = min(len(top_candidates), self.max_positions)
        
        # Calculate base position size
        base_size = portfolio_value * self.position_size_pct
        
        for i in range(max_candidates):
            candidate = top_candidates[i]
            
            # Volatility scaling (inverse relationship)
            vol_adjustment = 1.0 / max(candidate['volatility'], 0.01)  # Avoid division by zero
            vol_adjustment = min(vol_adjustment, 2.0)  # Cap at 2x
            
            # Final position size
            position_value = base_size * vol_adjustment
            position_value = min(position_value, portfolio_value * self.position_size_pct)
            
            shares = int(position_value / candidate['current_price'])
            
            if shares > 0:
                positions.append({
                    'symbol': candidate['symbol'],
                    'shares': shares,
                    'position_value': shares * candidate['current_price'],
                    'momentum_score': candidate['momentum_score'],
                    'volatility': candidate['volatility'],
                    'weight': (shares * candidate['current_price']) / portfolio_value
                })
        
        logging.info(f"🎯 Generated {len(positions)} position recommendations")
        
        return positions
    
    def generate_signals(self, universe_data: Dict[str, pd.DataFrame], 
                        portfolio_value: float = 10000) -> List[Dict]:
        """
        Main signal generation method for Phase 1
        
        Args:
            universe_data: Dict of {symbol: price_dataframe}
            portfolio_value: Current portfolio value
            
        Returns:
            List of trading signals with position sizes
        """
        logging.info("🚀 Generating Phase 1 momentum signals...")
        
        # Step 1: Rank universe by momentum
        ranked_candidates = self.rank_universe(universe_data)
        
        if not ranked_candidates:
            logging.warning("⚠️ No candidates passed momentum and liquidity filters")
            return []
        
        # Step 2: Take top candidates
        top_candidates = ranked_candidates[:self.max_positions]
        
        # Step 3: Calculate position sizes
        signals = self.calculate_position_sizes(top_candidates, portfolio_value)
        
        # Log top signals
        logging.info("📈 Top momentum signals:")
        for i, signal in enumerate(signals[:5]):
            logging.info(f"  {i+1}. {signal['symbol']}: "
                        f"momentum={signal['momentum_score']:.3f}, "
                        f"weight={signal['weight']:.2%}")
        
        return signals


if __name__ == "__main__":
    # Quick test
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    from core.data_loader import DataLoader
    
    logging.basicConfig(level=logging.INFO)
    
    # Initialize components
    data_loader = DataLoader()
    momentum_strategy = MomentumStrategy()
    
    # Load universe
    universe_df = pd.read_csv('data/universe.csv')
    symbols = universe_df['symbol'].tolist()[:10]  # Start with top 10 for speed
    
    # Load data for all symbols
    universe_data = {}
    for symbol in symbols:
        try:
            data = data_loader.get_historical_data(symbol, limit=200)
            if data is not None and len(data) > 100:
                universe_data[symbol] = data
                print(f"✅ Loaded {len(data)} bars for {symbol}")
        except Exception as e:
            print(f"❌ Could not load data for {symbol}: {e}")
    
    if universe_data:
        # Generate signals
        signals = momentum_strategy.generate_signals(universe_data)
        
        print(f"\n📊 Generated {len(signals)} momentum signals:")
        for signal in signals:
            print(f"  {signal['symbol']}: ${signal['position_value']:.0f} "
                  f"({signal['weight']:.1%}), momentum: {signal['momentum_score']:.3f}")
    else:
        print("❌ No data loaded for testing")

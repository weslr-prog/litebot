"""
Enhanced Momentum Strategy - Multi-sector momentum with rotation signals
Combines individual stock momentum with sector rotation analysis
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
import logging
from datetime import datetime

from .momentum_strategy import MomentumStrategy
from .sector_analyzer import SectorAnalyzer

class EnhancedMomentumStrategy(MomentumStrategy):
    """Enhanced momentum strategy with sector awareness"""
    
    def __init__(self, alpha_vantage_key: str, 
                 momentum_short: int = 21, 
                 momentum_long: int = 42,
                 sector_lookback: int = 21):
        """Initialize enhanced momentum strategy with sector analysis"""
        super().__init__(momentum_short, momentum_long)
        
        self.sector_analyzer = SectorAnalyzer(alpha_vantage_key)
        self.sector_lookback = sector_lookback
        self.logger = logging.getLogger(__name__)
        
        # Enhanced signal weights
        self.weights = {
            'individual_momentum': 0.4,    # 40% individual stock momentum
            'sector_momentum': 0.35,       # 35% sector momentum
            'sector_rotation': 0.15,       # 15% sector rotation signal  
            'relative_strength': 0.10      # 10% relative strength vs sector
        }
        
        self.logger.info("🎯 Enhanced Momentum Strategy with Sector Analysis initialized")
    
    def generate_enhanced_signals(self, market_data: Dict[str, pd.DataFrame], 
                                portfolio_value: float) -> List[Dict]:
        """Generate enhanced momentum signals with sector analysis"""
        try:
            self.logger.info("🚀 Generating Enhanced Multi-Sector Momentum Signals...")
            
            # 1. Get individual stock momentum signals
            individual_signals = super().generate_signals(market_data, portfolio_value)
            
            if not individual_signals:
                self.logger.warning("⚠️ No individual momentum signals generated")
                return []
            
            # 2. Get sector allocation weights
            sector_weights = self.sector_analyzer.get_sector_allocation_weights()
            
            # 3. Apply sector momentum filters
            sector_filtered_signals = self.sector_analyzer.filter_stocks_by_sector_momentum(
                individual_signals, sector_weights
            )
            
            # 4. Calculate relative strength vs sector
            enhanced_signals = self._calculate_relative_strength(
                sector_filtered_signals, market_data
            )
            
            # 5. Apply sector diversification limits
            diversified_signals = self._apply_sector_diversification(
                enhanced_signals, max_per_sector=3
            )
            
            # 6. Final composite scoring
            final_signals = self._calculate_composite_scores(diversified_signals)
            
            # Log results
            self.logger.info(f"📊 Enhanced Signal Generation Results:")
            self.logger.info(f"   📈 Individual signals: {len(individual_signals)}")
            self.logger.info(f"   🎯 Sector filtered: {len(sector_filtered_signals)}")
            self.logger.info(f"   🔄 Diversified signals: {len(diversified_signals)}")
            
            if final_signals:
                self.logger.info("🏆 Top Enhanced Signals:")
                for i, signal in enumerate(final_signals[:5], 1):
                    symbol = signal['symbol']
                    score = signal['composite_score']
                    sector = signal.get('sector', 'Unknown')
                    self.logger.info(f"   {i}. {symbol}: {score:.3f} ({sector})")
            
            return final_signals
            
        except Exception as e:
            self.logger.error(f"❌ Error generating enhanced signals: {e}")
            return individual_signals  # Fallback to basic signals
    
    def _calculate_relative_strength(self, signals: List[Dict], 
                                   market_data: Dict[str, pd.DataFrame]) -> List[Dict]:
        """Calculate relative strength of stocks vs their sector ETFs"""
        enhanced_signals = []
        
        for signal in signals:
            try:
                symbol = signal['symbol']
                sector_etf = signal.get('sector_etf')
                
                if symbol not in market_data or not sector_etf:
                    enhanced_signals.append(signal)
                    continue
                
                # Get stock and sector data
                stock_data = market_data[symbol]
                
                # Calculate stock momentum
                stock_returns = stock_data['close'].pct_change().fillna(0)
                stock_momentum = stock_returns.rolling(self.sector_lookback).mean().iloc[-1]
                
                # Use sector weight as proxy for sector momentum
                sector_momentum = signal.get('sector_weight', 0.1) - 0.1  # Rough proxy
                
                # Relative strength = stock momentum - sector momentum
                relative_strength = stock_momentum - sector_momentum
                
                # Enhance signal with relative strength
                enhanced_signal = signal.copy()
                enhanced_signal['relative_strength'] = relative_strength
                enhanced_signal['stock_momentum'] = stock_momentum
                enhanced_signal['sector_momentum'] = sector_momentum
                
                enhanced_signals.append(enhanced_signal)
                
            except Exception as e:
                self.logger.warning(f"⚠️ Error calculating relative strength for {signal['symbol']}: {e}")
                enhanced_signals.append(signal)
        
        return enhanced_signals
    
    def _apply_sector_diversification(self, signals: List[Dict], 
                                    max_per_sector: int = 3) -> List[Dict]:
        """Apply sector diversification limits"""
        sector_counts = {}
        diversified_signals = []
        
        # Sort by momentum score first
        sorted_signals = sorted(signals, key=lambda x: x['momentum_score'], reverse=True)
        
        for signal in sorted_signals:
            sector = signal.get('sector', 'Unknown')
            current_count = sector_counts.get(sector, 0)
            
            if current_count < max_per_sector:
                diversified_signals.append(signal)
                sector_counts[sector] = current_count + 1
            else:
                self.logger.debug(f"🚫 Skipping {signal['symbol']} - {sector} sector limit reached")
        
        return diversified_signals
    
    def _calculate_composite_scores(self, signals: List[Dict]) -> List[Dict]:
        """Calculate final composite scores using all factors"""
        final_signals = []
        
        for signal in signals:
            try:
                # Normalize individual components
                individual_momentum = signal.get('momentum_score', 0)
                sector_momentum = signal.get('sector_weight', 0.1) * 10 - 1  # Normalize to ~[-1,1]
                relative_strength = signal.get('relative_strength', 0)
                
                # Calculate composite score
                composite_score = (
                    individual_momentum * self.weights['individual_momentum'] +
                    sector_momentum * self.weights['sector_momentum'] +
                    relative_strength * self.weights['relative_strength']
                )
                
                # Create final signal
                final_signal = signal.copy()
                final_signal['composite_score'] = composite_score
                final_signal['individual_momentum'] = individual_momentum
                final_signal['sector_momentum_score'] = sector_momentum
                
                final_signals.append(final_signal)
                
            except Exception as e:
                self.logger.warning(f"⚠️ Error calculating composite score for {signal['symbol']}: {e}")
                final_signals.append(signal)
        
        # Sort by composite score
        final_signals.sort(key=lambda x: x.get('composite_score', 0), reverse=True)
        
        return final_signals

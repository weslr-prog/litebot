"""
Enhanced Risk Management for LiteBotX - Phase 3 Implementation
Purpose: Correlation-aware portfolio management for achieving weekly ROI safely
"""

import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
import json
import os
from dataclasses import dataclass
from enum import Enum

# Configure logging for Risk Management
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

@dataclass
class CorrelationConfig:
    """Configuration for correlation-aware portfolio management"""
    max_correlation_threshold: float = 0.7      # Max correlation between positions
    correlation_window_days: int = 30           # Days for correlation calculation
    sector_correlation_penalty: float = 0.8     # Size reduction for same-sector positions
    correlation_check_frequency: int = 5        # Check correlation every N positions
    min_correlation_data_points: int = 20       # Minimum data points for correlation calc
    
class PortfolioRiskLevel(Enum):
    """Portfolio risk levels for position sizing"""
    CONSERVATIVE = "conservative"  # 10-12 positions, low correlation
    MODERATE = "moderate"         # 13-16 positions, moderate correlation
    AGGRESSIVE = "aggressive"     # 17-20 positions, higher correlation allowed

@dataclass
class PositionCorrelationInfo:
    """Information about position correlation with portfolio"""
    symbol: str
    correlation_score: float       # Average correlation with existing positions
    max_individual_correlation: float  # Highest correlation with any single position
    correlated_symbols: List[str]  # Symbols with correlation > threshold
    sector_overlap_count: int      # Number of positions in same sector
    risk_adjustment_factor: float  # Multiplier for position size (0.5-1.0)

class RiskManager:
    """
    Enhanced Risk Management System with Correlation-Aware Portfolio Management
    
    Key Features:
    - Dynamic position sizing: Risk$ = 0.005 × β_regime × Equity × confidence × correlation_factor
    - Portfolio caps: 10-20 positions (correlation-aware), ≤2 per sector initially
    - Correlation limits: Max 0.7 correlation between positions
    - Loss limits: -1.5% daily, -3% weekly (auto-halt)
    - Regime-aware risk scaling with correlation adjustments
    """
    
    def __init__(self, initial_equity=10000.0, max_risk_per_trade=0.005, 
                 portfolio_risk_level: PortfolioRiskLevel = PortfolioRiskLevel.MODERATE):
        # Core settings for weekly ROI with correlation awareness
        self.initial_equity = initial_equity
        self.current_equity = initial_equity
        self.max_risk_per_trade = max_risk_per_trade  # 0.5% per trade
        self.portfolio_risk_level = portfolio_risk_level
        
        # Enhanced portfolio tracking
        self.positions = {}  # {symbol: position_info with correlation data}
        self.daily_pnl = 0.0
        self.weekly_pnl = 0.0
        
        # Correlation-aware position limits
        self.position_limits = {
            PortfolioRiskLevel.CONSERVATIVE: {'min': 10, 'max': 12, 'target': 11},
            PortfolioRiskLevel.MODERATE: {'min': 13, 'max': 16, 'target': 15},
            PortfolioRiskLevel.AGGRESSIVE: {'min': 17, 'max': 20, 'target': 18}
        }
        
        current_limits = self.position_limits[portfolio_risk_level]
        self.min_positions = current_limits['min']
        self.max_positions = current_limits['max']
        self.target_positions = current_limits['target']
        
        # Correlation configuration
        self.correlation_config = CorrelationConfig()
        self.correlation_matrix = pd.DataFrame()  # Symbol correlation matrix
        self.price_history = {}  # {symbol: price_series} for correlation calculation
        self.last_correlation_update = None
        
        # Loss limits (CRITICAL for risk management)
        self.daily_loss_limit = -0.015    # -1.5% daily
        self.weekly_loss_limit = -0.03    # -3% weekly  
        self.is_trading_halted = False
        
        # Enhanced sector exposure management
        self.max_positions_per_sector = 2  # Start conservative, can increase
        self.sector_positions = {}  # {sector: count}
        self.sector_correlation_matrix = pd.DataFrame()  # Sector-level correlations
        
        # Performance tracking
        self.trade_history = []
        self.risk_metrics = {
            'total_trades': 0,
            'winning_trades': 0,
            'avg_win': 0.0,
            'avg_loss': 0.0,
            'current_drawdown': 0.0,
            'max_drawdown': 0.0,
            'sharpe_ratio': 0.0,
            'portfolio_correlation': 0.0,
            'diversification_ratio': 0.0
        }
        
        # Regime-based risk multipliers (β_regime)
        self.regime_multipliers = {
            'bull': 1.2,        # Higher risk in trending up markets
            'bear': 0.6,        # Lower risk in downtrending markets  
            'sideways': 0.8,    # Moderate risk in range-bound markets
            'volatile': 1.0,    # Standard risk in volatile breakout markets
            'UP_LOWVOL': 1.1,   # Slightly higher risk in stable uptrends
            'DOWN_HIGHVOL': 0.5 # Very low risk in volatile downtrends
        }
        
        # Legacy compatibility (keep existing interface)
        self.max_drawdown_pct = 0.2
        self.stop_loss_pct = 0.03
        self.take_profit_pct = 0.06
        self.trailing_stop_pct = 0.03
        self.trading_hours = (9, 16)
        self.daily_loss = 0.0
        self.weekly_loss = 0.0
        self.last_reset_date = None
        self.last_reset_week = None
        
        logging.info(f"🛡️ Enhanced RiskManager with Correlation Awareness initialized:")
        logging.info(f"   💰 ${initial_equity:,.2f} equity, {self.max_risk_per_trade:.1%} max risk per trade")
        logging.info(f"   📊 Portfolio limits: {self.min_positions}-{self.max_positions} positions (target: {self.target_positions})")
        logging.info(f"   🔗 Correlation threshold: {self.correlation_config.max_correlation_threshold:.1%}")
        logging.info(f"   🏢 Sector limits: {self.max_positions_per_sector} per sector initially")
        logging.info(f"   🚨 Loss limits: {self.daily_loss_limit:.1%} daily, {self.weekly_loss_limit:.1%} weekly")
        logging.info(f"   📈 Risk level: {portfolio_risk_level.value}")

    def update_price_history(self, symbol: str, price: float, timestamp: datetime = None):
        """Update price history for correlation calculations"""
        
        if timestamp is None:
            timestamp = datetime.now()
        
        if symbol not in self.price_history:
            self.price_history[symbol] = []
        
        # Add new price point
        self.price_history[symbol].append({
            'timestamp': timestamp,
            'price': price
        })
        
        # Keep only last N days for correlation calculation
        cutoff_date = timestamp - timedelta(days=self.correlation_config.correlation_window_days)
        self.price_history[symbol] = [
            p for p in self.price_history[symbol] 
            if p['timestamp'] >= cutoff_date
        ]
        
        # Update correlation matrix if we have enough data points
        if len(self.price_history[symbol]) >= self.correlation_config.min_correlation_data_points:
            self._update_correlation_matrix()
    
    def _update_correlation_matrix(self):
        """Update correlation matrix from price history"""
        
        # Get symbols with sufficient data
        valid_symbols = [
            symbol for symbol, history in self.price_history.items()
            if len(history) >= self.correlation_config.min_correlation_data_points
        ]
        
        if len(valid_symbols) < 2:
            return
        
        # Create price DataFrame
        price_data = {}
        for symbol in valid_symbols:
            prices = [p['price'] for p in self.price_history[symbol]]
            price_data[symbol] = prices[-self.correlation_config.min_correlation_data_points:]
        
        # Calculate correlation matrix
        df = pd.DataFrame(price_data)
        returns_df = df.pct_change().dropna()
        
        if len(returns_df) > 5:  # Need minimum data for correlation
            self.correlation_matrix = returns_df.corr()
            self.last_correlation_update = datetime.now()
            
            # Update portfolio correlation metric
            if len(self.positions) > 1:
                portfolio_symbols = list(self.positions.keys())
                if all(s in self.correlation_matrix.index for s in portfolio_symbols):
                    correlations = []
                    for i, sym1 in enumerate(portfolio_symbols):
                        for sym2 in portfolio_symbols[i+1:]:
                            if sym1 in self.correlation_matrix.index and sym2 in self.correlation_matrix.columns:
                                correlations.append(abs(self.correlation_matrix.loc[sym1, sym2]))
                    
                    if correlations:
                        self.risk_metrics['portfolio_correlation'] = np.mean(correlations)
    
    def calculate_position_correlation(self, symbol: str) -> PositionCorrelationInfo:
        """Calculate correlation information for a potential position"""
        
        if symbol not in self.correlation_matrix.index or len(self.positions) == 0:
            return PositionCorrelationInfo(
                symbol=symbol,
                correlation_score=0.0,
                max_individual_correlation=0.0,
                correlated_symbols=[],
                sector_overlap_count=0,
                risk_adjustment_factor=1.0
            )
        
        # Calculate correlations with existing positions
        portfolio_symbols = [s for s in self.positions.keys() if s in self.correlation_matrix.columns]
        
        if not portfolio_symbols:
            return PositionCorrelationInfo(
                symbol=symbol,
                correlation_score=0.0,
                max_individual_correlation=0.0,
                correlated_symbols=[],
                sector_overlap_count=0,
                risk_adjustment_factor=1.0
            )
        
        correlations = []
        correlated_symbols = []
        
        for existing_symbol in portfolio_symbols:
            corr = abs(self.correlation_matrix.loc[symbol, existing_symbol])
            correlations.append(corr)
            
            if corr > self.correlation_config.max_correlation_threshold:
                correlated_symbols.append(existing_symbol)
        
        avg_correlation = np.mean(correlations) if correlations else 0.0
        max_correlation = max(correlations) if correlations else 0.0
        
        # Calculate sector overlap
        symbol_sector = self._get_symbol_sector(symbol)
        sector_overlap = sum(1 for pos in self.positions.values() 
                           if pos.get('sector', 'Unknown') == symbol_sector)
        
        # Calculate risk adjustment factor
        # Reduce position size based on correlation and sector overlap
        correlation_penalty = min(avg_correlation * 2, 0.5)  # Max 50% reduction
        sector_penalty = sector_overlap * 0.1  # 10% reduction per same-sector position
        
        risk_adjustment_factor = max(0.3, 1.0 - correlation_penalty - sector_penalty)
        
        return PositionCorrelationInfo(
            symbol=symbol,
            correlation_score=avg_correlation,
            max_individual_correlation=max_correlation,
            correlated_symbols=correlated_symbols,
            sector_overlap_count=sector_overlap,
            risk_adjustment_factor=risk_adjustment_factor
        )
    
    def _get_symbol_sector(self, symbol: str) -> str:
        """Get sector for symbol (placeholder - would integrate with real sector data)"""
        # This would integrate with real sector classification
        # For now, use simple heuristics or stored sector data
        if symbol in self.positions:
            return self.positions[symbol].get('sector', 'Unknown')
        return 'Unknown'

    def calculate_position_size(self, signal_confidence: float, stop_distance: float, 
                              regime: str = 'sideways', current_price: float = 100.0,
                              account_equity: Optional[float] = None, symbol: str = None,
                              sector: str = 'Unknown') -> Dict:
        """
        Calculate optimal position size with correlation-aware adjustments
        
        Enhanced Formula: Risk$ = 0.005 × β_regime × Equity × confidence × correlation_factor
        Where correlation_factor reduces size based on portfolio correlation
        
        Args:
            signal_confidence: 0.0-1.0 confidence in the signal (from ML/strategy)
            stop_distance: Distance to stop loss ($ per share)
            regime: Market regime (bull/bear/sideways/volatile/UP_LOWVOL/DOWN_HIGHVOL)
            current_price: Current stock price
            account_equity: Override equity (for legacy compatibility)
            symbol: Stock symbol for correlation analysis
            sector: GICS sector for sector analysis
            
        Returns:
            Dict with position size details including correlation adjustments
        """
        # Use current equity or override
        equity = account_equity if account_equity is not None else self.current_equity
        
        if self.is_trading_halted:
            logging.warning("🚨 Trading halted due to loss limits")
            return {'quantity': 0, 'risk_dollars': 0, 'reason': 'trading_halted'}
        
        # Get regime multiplier (β_regime)
        beta_regime = self.regime_multipliers.get(regime, 1.0)
        
        # Calculate correlation information if symbol provided
        correlation_info = None
        correlation_factor = 1.0
        
        if symbol:
            correlation_info = self.calculate_position_correlation(symbol)
            correlation_factor = correlation_info.risk_adjustment_factor
            
            # Check correlation limits
            if correlation_info.max_individual_correlation > self.correlation_config.max_correlation_threshold:
                logging.warning(f"🔗 High correlation detected: {symbol} has {correlation_info.max_individual_correlation:.2%} "
                              f"correlation with {correlation_info.correlated_symbols}")
                # Still allow trade but with reduced size
                correlation_factor *= 0.7  # Additional 30% reduction for high correlation
        
        # Enhanced risk calculation: Risk$ = 0.005 × β_regime × Equity × confidence × correlation_factor
        base_risk = self.max_risk_per_trade * equity
        risk_dollars = base_risk * beta_regime * signal_confidence * correlation_factor
        
        # Calculate quantity: Qty = Risk$ / Stop_Distance
        if stop_distance <= 0:
            logging.error(f"❌ Invalid stop distance: {stop_distance}")
            return {'quantity': 0, 'risk_dollars': 0, 'reason': 'invalid_stop_distance'}
        
        raw_quantity = risk_dollars / stop_distance
        quantity = round(raw_quantity, 2)  # Round down to 2 decimals as specified
        
        # Enhanced portfolio limit checks (correlation-aware)
        current_position_count = len(self.positions)
        
        # Dynamic position limits based on portfolio correlation
        if current_position_count >= self.max_positions:
            # Allow slight overage if correlations are low and we're below target
            avg_portfolio_correlation = self.risk_metrics.get('portfolio_correlation', 0.0)
            if (current_position_count < self.target_positions + 2 and 
                avg_portfolio_correlation < self.correlation_config.max_correlation_threshold * 0.8):
                logging.info(f"📊 Allowing position above max due to low correlation: "
                           f"{avg_portfolio_correlation:.2%} < {self.correlation_config.max_correlation_threshold * 0.8:.2%}")
            else:
                logging.warning(f"⚠️ Max positions reached: {current_position_count}/{self.max_positions}")
                return {'quantity': 0, 'risk_dollars': 0, 'reason': 'max_positions_reached'}
        
        # Minimum position check (for smaller portfolios, encourage diversification)
        if (current_position_count < self.min_positions and 
            correlation_factor > 0.8):  # Only if not too correlated
            # Slightly increase position size to reach minimum faster
            quantity *= 1.1
            risk_dollars *= 1.1
            logging.info(f"📈 Increasing position size to reach minimum diversification: "
                        f"{current_position_count}/{self.min_positions}")
        
        # Position value limit (adjusted for portfolio size)
        max_position_pct = 0.3 if current_position_count < 5 else 0.15  # Smaller positions for larger portfolio
        position_value = quantity * current_price
        max_position_value = equity * max_position_pct
        
        if position_value > max_position_value:
            quantity = max_position_value / current_price
            quantity = round(quantity, 2)
            risk_dollars = quantity * stop_distance
            logging.warning(f"⚠️ Position size reduced due to {max_position_pct:.0%} limit: {quantity} shares")
        
        # Ensure minimum position size
        if quantity < 1:
            logging.warning(f"⚠️ Position size too small: {quantity} shares")
            return {'quantity': 0, 'risk_dollars': 0, 'reason': 'position_too_small'}
        
        # Enhanced position info with correlation data
        position_info = {
            'quantity': quantity,
            'risk_dollars': risk_dollars,
            'position_value': quantity * current_price,
            'stop_distance': stop_distance,
            'confidence': signal_confidence,
            'regime': regime,
            'beta_regime': beta_regime,
            'correlation_factor': correlation_factor,
            'risk_percent': risk_dollars / equity,
            'sector': sector,
            'symbol': symbol,
            'reason': 'approved'
        }
        
        # Add correlation details if available
        if correlation_info:
            position_info.update({
                'correlation_score': correlation_info.correlation_score,
                'max_correlation': correlation_info.max_individual_correlation,
                'correlated_symbols': correlation_info.correlated_symbols,
                'sector_overlap_count': correlation_info.sector_overlap_count
            })
        
        logging.info(f"📏 Position size: {quantity} shares, ${risk_dollars:.2f} risk "
                    f"({position_info['risk_percent']:.2%}) in {regime} regime")
        
        if correlation_info and correlation_info.correlation_score > 0:
            logging.info(f"🔗 Correlation adjustment: {correlation_factor:.2f} factor, "
                        f"{correlation_info.correlation_score:.2%} avg correlation")
        
        # Legacy compatibility: return just the quantity as int if called with old parameters
        if account_equity is not None and symbol is None:
            return max(int(quantity), 1)
        
        return position_info

    def compute_risk_dollars(self, equity: float, beta_regime: float = 1.0) -> float:
        """
        Compute risk dollars for regime-based position sizing
        Used by attach_regime_and_size in backtester
        """
        return self.max_risk_per_trade * beta_regime * equity

    def check_sector_exposure(self, symbol: str, sector: str = 'Unknown') -> bool:
        """
        Enhanced sector exposure check with correlation awareness
        Max 2 positions per GICS sector initially, adjustable based on correlation
        """
        current_sector_count = self.sector_positions.get(sector, 0)
        
        # Dynamic sector limits based on portfolio size and correlation
        if len(self.positions) < 10:
            # Conservative: max 2 per sector for small portfolios
            max_sector_positions = self.max_positions_per_sector
        else:
            # Allow more sector concentration for larger portfolios if correlations are low
            avg_portfolio_correlation = self.risk_metrics.get('portfolio_correlation', 0.0)
            if avg_portfolio_correlation < 0.5:
                max_sector_positions = min(4, self.max_positions_per_sector + 2)
            else:
                max_sector_positions = self.max_positions_per_sector
        
        if current_sector_count >= max_sector_positions:
            logging.warning(f"🏢 Sector exposure limit: {sector} has {current_sector_count}/{max_sector_positions} positions")
            return False
        
        return True
    
    def get_portfolio_diversification_score(self) -> float:
        """
        Calculate portfolio diversification score (0-1, higher is better)
        Based on correlation matrix and sector distribution
        """
        if len(self.positions) < 2:
            return 1.0  # Single position is perfectly "diversified" in this context
        
        # Correlation-based diversification
        correlation_score = 1.0
        if self.correlation_matrix is not None and len(self.correlation_matrix) > 1:
            portfolio_symbols = [s for s in self.positions.keys() if s in self.correlation_matrix.index]
            
            if len(portfolio_symbols) > 1:
                correlations = []
                for i, sym1 in enumerate(portfolio_symbols):
                    for sym2 in portfolio_symbols[i+1:]:
                        if sym1 in self.correlation_matrix.index and sym2 in self.correlation_matrix.columns:
                            correlations.append(abs(self.correlation_matrix.loc[sym1, sym2]))
                
                if correlations:
                    avg_correlation = np.mean(correlations)
                    correlation_score = max(0, 1.0 - avg_correlation)  # Lower correlation = higher score
        
        # Sector-based diversification
        sector_counts = {}
        for pos in self.positions.values():
            sector = pos.get('sector', 'Unknown')
            sector_counts[sector] = sector_counts.get(sector, 0) + 1
        
        if len(sector_counts) > 1:
            # Calculate Herfindahl-Hirschman Index for sector concentration
            total_positions = len(self.positions)
            hhi = sum((count / total_positions) ** 2 for count in sector_counts.values())
            sector_score = max(0, 1.0 - hhi)  # Lower concentration = higher score
        else:
            sector_score = 0.5  # Single sector gets moderate score
        
        # Combined diversification score (weighted average)
        diversification_score = 0.6 * correlation_score + 0.4 * sector_score
        
        # Update risk metrics
        self.risk_metrics['diversification_ratio'] = diversification_score
        
        return diversification_score
    
    def rebalance_portfolio_recommendations(self) -> Dict:
        """
        Analyze current portfolio and recommend rebalancing actions
        Based on correlation analysis and position sizing
        """
        if len(self.positions) < 2:
            return {'recommendations': [], 'overall_score': 1.0}
        
        recommendations = []
        current_diversification = self.get_portfolio_diversification_score()
        
        # Check for over-correlated positions
        if self.correlation_matrix is not None:
            portfolio_symbols = [s for s in self.positions.keys() if s in self.correlation_matrix.index]
            
            for i, sym1 in enumerate(portfolio_symbols):
                for sym2 in portfolio_symbols[i+1:]:
                    if (sym1 in self.correlation_matrix.index and 
                        sym2 in self.correlation_matrix.columns):
                        corr = abs(self.correlation_matrix.loc[sym1, sym2])
                        
                        if corr > self.correlation_config.max_correlation_threshold:
                            recommendations.append({
                                'type': 'HIGH_CORRELATION',
                                'symbols': [sym1, sym2],
                                'correlation': corr,
                                'action': f'Consider reducing position in weaker performer',
                                'priority': 'HIGH' if corr > 0.8 else 'MEDIUM'
                            })
        
        # Check sector concentration
        sector_counts = {}
        for symbol, pos in self.positions.items():
            sector = pos.get('sector', 'Unknown')
            sector_counts[sector] = sector_counts.get(sector, 0) + 1
        
        for sector, count in sector_counts.items():
            if count > self.max_positions_per_sector:
                recommendations.append({
                    'type': 'SECTOR_CONCENTRATION',
                    'sector': sector,
                    'count': count,
                    'limit': self.max_positions_per_sector,
                    'action': f'Reduce exposure in {sector} sector',
                    'priority': 'MEDIUM'
                })
        
        # Check portfolio size vs targets
        current_size = len(self.positions)
        if current_size < self.min_positions:
            recommendations.append({
                'type': 'UNDER_DIVERSIFIED',
                'current_positions': current_size,
                'target_positions': self.min_positions,
                'action': f'Add {self.min_positions - current_size} more positions for diversification',
                'priority': 'LOW'
            })
        elif current_size > self.max_positions:
            recommendations.append({
                'type': 'OVER_CONCENTRATED',
                'current_positions': current_size,
                'target_positions': self.max_positions,
                'action': f'Consider closing {current_size - self.max_positions} weakest positions',
                'priority': 'MEDIUM'
            })
        
        return {
            'recommendations': recommendations,
            'overall_score': current_diversification,
            'portfolio_correlation': self.risk_metrics.get('portfolio_correlation', 0.0),
            'position_count': current_size,
            'target_range': f"{self.min_positions}-{self.max_positions}",
            'sector_distribution': sector_counts
        }
    
    def update_position(self, symbol: str, position_info: Dict):
        """Update position with correlation tracking"""
        self.positions[symbol] = position_info
        
        # Update sector tracking
        sector = position_info.get('sector', 'Unknown')
        self.sector_positions[sector] = self.sector_positions.get(sector, 0) + 1
        
        # Log portfolio state
        current_size = len(self.positions)
        diversification_score = self.get_portfolio_diversification_score()
        
        logging.info(f"� Portfolio updated: {current_size} positions, "
                    f"diversification score: {diversification_score:.2f}")
        
        # Rebalancing recommendations if portfolio is getting large
        if current_size % 5 == 0 and current_size >= 10:  # Every 5 positions after 10
            rebalance_info = self.rebalance_portfolio_recommendations()
            high_priority_recs = [r for r in rebalance_info['recommendations'] 
                                if r.get('priority') == 'HIGH']
            
            if high_priority_recs:
                logging.warning(f"⚠️ High priority rebalancing recommendations: {len(high_priority_recs)} items")
                for rec in high_priority_recs[:2]:  # Show top 2
                    logging.warning(f"   - {rec['type']}: {rec['action']}")
    
    def remove_position(self, symbol: str):
        """Remove position and update tracking"""
        if symbol in self.positions:
            position_info = self.positions[symbol]
            sector = position_info.get('sector', 'Unknown')
            
            # Update sector count
            if sector in self.sector_positions:
                self.sector_positions[sector] = max(0, self.sector_positions[sector] - 1)
                if self.sector_positions[sector] == 0:
                    del self.sector_positions[sector]
            
            # Remove position
            del self.positions[symbol]
            
            logging.info(f"📉 Position removed: {symbol}, {len(self.positions)} positions remaining")
            
            # Update diversification metrics
            self.get_portfolio_diversification_score()
    
    def get_correlation_matrix_summary(self) -> Dict:
        """Get summary of current correlation matrix"""
        if self.correlation_matrix.empty:
            return {'status': 'no_data', 'symbols': 0}
        
        portfolio_symbols = [s for s in self.positions.keys() if s in self.correlation_matrix.index]
        
        if len(portfolio_symbols) < 2:
            return {'status': 'insufficient_positions', 'symbols': len(portfolio_symbols)}
        
        # Calculate correlation statistics
        correlations = []
        for i, sym1 in enumerate(portfolio_symbols):
            for sym2 in portfolio_symbols[i+1:]:
                if sym1 in self.correlation_matrix.index and sym2 in self.correlation_matrix.columns:
                    correlations.append(self.correlation_matrix.loc[sym1, sym2])
        
        if not correlations:
            return {'status': 'no_correlations', 'symbols': len(portfolio_symbols)}
        
        return {
            'status': 'active',
            'symbols': len(portfolio_symbols),
            'avg_correlation': np.mean(correlations),
            'max_correlation': max(correlations),
            'min_correlation': min(correlations),
            'high_correlation_pairs': sum(1 for c in correlations if abs(c) > self.correlation_config.max_correlation_threshold),
            'last_updated': self.last_correlation_update.isoformat() if self.last_correlation_update else None
        }

    def check_loss_limits(self) -> bool:
        """
        Check daily and weekly loss limits
        Daily: -1.5%, Weekly: -3%
        """
        daily_loss_pct = self.daily_pnl / self.current_equity
        weekly_loss_pct = self.weekly_pnl / self.current_equity
        
        if daily_loss_pct <= self.daily_loss_limit:
            logging.error(f"🚨 DAILY LOSS LIMIT HIT: {daily_loss_pct:.2%} <= {self.daily_loss_limit:.2%}")
            self.is_trading_halted = True
            return False
        
        if weekly_loss_pct <= self.weekly_loss_limit:
            logging.error(f"🚨 WEEKLY LOSS LIMIT HIT: {weekly_loss_pct:.2%} <= {self.weekly_loss_limit:.2%}")
            self.is_trading_halted = True
            return False
        
        return True

    def should_trade(self, symbol: str, action: str, portfolio: List, account_equity: float, 
                    price: float, peak_equity: float, start_equity: Optional[float] = None, 
                    expected_price: Optional[float] = None, actual_price: Optional[float] = None,
                    signal_confidence: float = 0.5, regime: str = 'sideways', 
                    sector: str = 'Unknown') -> bool:
        """
        Enhanced trade approval system - ALL trades must pass through this
        Combines legacy interface with new 5% weekly ROI logic
        """
        if action == 'hold':
            logging.info(f"ℹ️ No trade for {symbol}: action is 'hold'")
            return False
        
        # Update current equity
        self.current_equity = account_equity
        
        # New loss limit checks (more strict)
        if not self.check_loss_limits():
            logging.warning(f"🚫 Trade blocked: loss limits exceeded")
            return False
        
        # New sector exposure check
        if not self.check_sector_exposure(symbol, sector):
            logging.warning(f"🚫 Trade blocked: sector exposure limit for {sector}")
            return False
        
        # Legacy checks (keep for compatibility)
        if not self.check_max_positions(portfolio):
            logging.warning(f"🚫 Trade blocked: max positions reached ({len(portfolio)}/{self.max_positions})")
            return False
        
        if not self.check_max_drawdown(account_equity, peak_equity):
            logging.warning(f"🚫 Trade blocked: max drawdown exceeded")
            return False
        
        if not self.check_trading_hours():
            logging.warning(f"🚫 Trade blocked: outside trading hours")
            return False
        
        if expected_price is not None and actual_price is not None:
            if not self.check_slippage(expected_price, actual_price):
                logging.warning(f"🚫 Trade blocked: slippage too high")
                return False
        
        # Calculate position size with new formula
        stop_distance = abs(price * self.stop_loss_pct)  # Default stop distance
        position_info = self.calculate_position_size(
            signal_confidence=signal_confidence,
            stop_distance=stop_distance,
            regime=regime,
            current_price=price
        )
        
        if isinstance(position_info, dict) and position_info['quantity'] <= 0:
            logging.warning(f"🚫 Trade blocked: {position_info['reason']}")
            return False
        
        logging.info(f"✅ Trade APPROVED: {symbol} {action} @ ${price:.2f}")
        return True

    def approve_trade(self, symbol: str, signal_type: str, signal_confidence: float,
                     entry_price: float, stop_loss: float, sector: str = 'Unknown',
                     regime: str = 'sideways') -> Dict:
        """
        Enhanced trade approval with correlation-aware position sizing
        """
        logging.info(f"🔍 Trade approval: {symbol} {signal_type} @ ${entry_price:.2f}, "
                    f"confidence={signal_confidence:.2f}, sector={sector}")
        
        # Update price history for correlation tracking
        self.update_price_history(symbol, entry_price)
        
        if not self.check_loss_limits():
            return {'approved': False, 'reason': 'loss_limits_exceeded', 'quantity': 0}
        
        if symbol in self.positions:
            return {'approved': False, 'reason': 'position_already_exists', 'quantity': 0}
        
        if not self.check_sector_exposure(symbol, sector):
            return {'approved': False, 'reason': 'sector_exposure_limit', 'quantity': 0}
        
        # Enhanced correlation analysis
        correlation_info = self.calculate_position_correlation(symbol)
        
        # Correlation warnings but don't block (size adjustment handles it)
        if correlation_info.max_individual_correlation > self.correlation_config.max_correlation_threshold:
            logging.warning(f"🔗 High correlation warning: {symbol} has "
                          f"{correlation_info.max_individual_correlation:.2%} correlation with "
                          f"{correlation_info.correlated_symbols}")
        
        # Calculate position size with correlation adjustments
        stop_distance = abs(entry_price - stop_loss)
        position_info = self.calculate_position_size(
            signal_confidence=signal_confidence,
            stop_distance=stop_distance,
            regime=regime,
            current_price=entry_price,
            symbol=symbol,
            sector=sector
        )
        
        if position_info['quantity'] <= 0:
            return {'approved': False, 'reason': position_info['reason'], 'quantity': 0}
        
        # Enhanced approval details with correlation data
        trade_approval = {
            'approved': True,
            'symbol': symbol,
            'signal_type': signal_type,
            'quantity': position_info['quantity'],
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'risk_dollars': position_info['risk_dollars'],
            'position_value': position_info['position_value'],
            'confidence': signal_confidence,
            'regime': regime,
            'sector': sector,
            'correlation_factor': position_info.get('correlation_factor', 1.0),
            'correlation_score': position_info.get('correlation_score', 0.0),
            'max_correlation': position_info.get('max_correlation', 0.0),
            'sector_overlap_count': position_info.get('sector_overlap_count', 0),
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'reason': 'approved'
        }
        
        # Store position info for tracking
        position_data = position_info.copy()
        position_data.update({
            'symbol': symbol,
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'signal_type': signal_type,
            'entry_timestamp': datetime.now(timezone.utc),
            'sector': sector
        })
        
        self.update_position(symbol, position_data)
        
        logging.info(f"✅ Trade APPROVED: {symbol} {position_info['quantity']} shares, "
                    f"${position_info['risk_dollars']:.2f} risk")
        
        if correlation_info.correlation_score > 0:
            logging.info(f"🔗 Correlation impact: {correlation_info.correlation_factor:.2f} size factor, "
                        f"{correlation_info.correlation_score:.2%} avg correlation")
        
        return trade_approval

    # Legacy methods (keep for compatibility)
    def get_stop_loss_price(self, entry_price):
        return round(entry_price * (1 - self.stop_loss_pct), 2)

    def get_take_profit_price(self, entry_price):
        return round(entry_price * (1 + self.take_profit_pct), 2)

    def get_trailing_stop_price(self, highest_price):
        return round(highest_price * (1 - self.trailing_stop_pct), 2)

    def check_max_positions(self, portfolio):
        return len(portfolio) < self.max_positions

    def check_max_drawdown(self, account_equity, peak_equity):
        drawdown = (peak_equity - account_equity) / peak_equity if peak_equity > 0 else 0
        return drawdown < self.max_drawdown_pct

    def check_daily_loss_limit(self, account_equity, start_equity):
        import datetime
        today = datetime.date.today()
        if self.last_reset_date != today:
            self.daily_loss = 0.0
            self.last_reset_date = today
        loss = start_equity - account_equity
        self.daily_loss = loss
        return (loss / start_equity) < self.daily_loss_limit_pct if start_equity > 0 else True

    def check_weekly_loss_limit(self, account_equity, start_equity):
        import datetime
        week = datetime.date.today().isocalendar()[1]
        if self.last_reset_week != week:
            self.weekly_loss = 0.0
            self.last_reset_week = week
        loss = start_equity - account_equity
        self.weekly_loss = loss
        return (loss / start_equity) < self.weekly_loss_limit_pct if start_equity > 0 else True

    def check_trading_hours(self):
        import datetime
        now = datetime.datetime.now().hour
        return self.trading_hours[0] <= now < self.trading_hours[1]

    def check_slippage(self, expected_price, actual_price, max_slippage_pct=0.01):
        slippage = abs(actual_price - expected_price) / expected_price
        return slippage <= max_slippage_pct

    def get_portfolio_summary(self) -> Dict:
        """Get enhanced portfolio status with correlation metrics"""
        
        diversification_score = self.get_portfolio_diversification_score()
        correlation_summary = self.get_correlation_matrix_summary()
        rebalance_info = self.rebalance_portfolio_recommendations()
        
        return {
            # Core metrics
            'current_equity': self.current_equity,
            'daily_pnl': self.daily_pnl,
            'weekly_pnl': self.weekly_pnl,
            'active_positions': len(self.positions),
            'is_trading_halted': self.is_trading_halted,
            
            # Portfolio structure
            'position_limits': {
                'min': self.min_positions,
                'max': self.max_positions,
                'target': self.target_positions,
                'current': len(self.positions)
            },
            'sector_breakdown': self.sector_positions.copy(),
            'max_positions_per_sector': self.max_positions_per_sector,
            
            # Correlation metrics
            'correlation_analysis': correlation_summary,
            'diversification_score': diversification_score,
            'portfolio_correlation': self.risk_metrics.get('portfolio_correlation', 0.0),
            'correlation_threshold': self.correlation_config.max_correlation_threshold,
            
            # Risk metrics
            'risk_metrics': self.risk_metrics.copy(),
            'daily_return': self.daily_pnl / self.current_equity if self.current_equity > 0 else 0,
            'weekly_return': self.weekly_pnl / self.current_equity if self.current_equity > 0 else 0,
            'weekly_target': 0.05,  # 5% weekly target
            'progress_to_target': (self.weekly_pnl / self.current_equity) / 0.05 if self.current_equity > 0 else 0,
            
            # Rebalancing recommendations
            'rebalancing': {
                'recommendations_count': len(rebalance_info['recommendations']),
                'high_priority_count': len([r for r in rebalance_info['recommendations'] 
                                          if r.get('priority') == 'HIGH']),
                'overall_score': rebalance_info['overall_score'],
                'needs_attention': len([r for r in rebalance_info['recommendations'] 
                                      if r.get('priority') in ['HIGH', 'MEDIUM']]) > 0
            },
            
            # Configuration
            'portfolio_risk_level': self.portfolio_risk_level.value,
            'max_risk_per_trade': self.max_risk_per_trade,
            'loss_limits': {
                'daily_limit': self.daily_loss_limit,
                'weekly_limit': self.weekly_loss_limit,
                'daily_used': self.daily_pnl / self.current_equity if self.current_equity > 0 else 0,
                'weekly_used': self.weekly_pnl / self.current_equity if self.current_equity > 0 else 0
            }
        }

# Enhanced RiskManager with correlation-aware portfolio management is now ready!
# Key features:
# - 10-20 position portfolio management with correlation limits
# - Dynamic position sizing based on correlation analysis  
# - Sector diversification with correlation-aware limits
# - Portfolio rebalancing recommendations
# - Real-time correlation matrix tracking

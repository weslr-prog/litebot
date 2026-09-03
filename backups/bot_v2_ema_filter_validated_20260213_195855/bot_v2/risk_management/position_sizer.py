"""
AI-powered position sizing based on confidence and risk constraints
Extracted from traders/short_cycle_trader.py
"""

import logging
import math
from typing import Tuple
from datetime import datetime, timedelta

from bot_v2.config.trading_config import ShortCycleConfig
from bot_v2.models.signals import AISignal


class AIConfidencePositionSizer:
    """AI-powered position sizing based on confidence and risk constraints"""
    
    def __init__(self, config: ShortCycleConfig):
        self.config = config
        self.logger = logging.getLogger(__name__ + ".AIConfidencePositionSizer")
        self._vix_multiplier = None  # Cache VIX multiplier for the day
        self._vix_fetch_time = None
    
    def _get_vix_regime_multiplier(self) -> float:
        """Get VIX-based position size multiplier with daily caching"""
        
        # Return cached value if fetched today
        if self._vix_multiplier is not None and self._vix_fetch_time is not None:
            if datetime.now() - self._vix_fetch_time < timedelta(hours=6):
                return self._vix_multiplier
        
        try:
            import yfinance as yf
            vix = yf.Ticker("^VIX").history(period='1d')['Close'].iloc[-1]
            
            if vix > 30:
                self.logger.warning(f"⚠️ EXTREME FEAR: VIX={vix:.1f} - Cutting positions by 50%")
                multiplier = 0.5
            elif vix > 25:
                self.logger.warning(f"⚠️ HIGH VOLATILITY: VIX={vix:.1f} - Reducing positions by 25%")
                multiplier = 0.75
            elif vix > 20:
                self.logger.info(f"✅ ELEVATED VIX: VIX={vix:.1f} - Normal positions")
                multiplier = 1.0
            else:
                self.logger.info(f"✅ LOW VIX: VIX={vix:.1f} - Normal positions")
                multiplier = 1.0
            
            # Cache result
            self._vix_multiplier = multiplier
            self._vix_fetch_time = datetime.now()
            
            return multiplier
            
        except Exception as e:
            self.logger.error(f"Failed to fetch VIX: {e} - Using normal position sizing")
            return 1.0
    
    def calculate_position_size(self, signal: AISignal, stop_price: float, 
                              current_portfolio_value: float) -> Tuple[float, float]:
        """
        Calculate optimal position size based on confidence and risk
        NEW OCT 29 2025: Enhanced with dynamic sizing based on signal strength
        Returns: (shares, position_value) - shares can be fractional for small positions
        """
        try:
            entry_price = signal.entry_price
            
            # DEBUG: Log input values
            self.logger.info(f"DEBUG {signal.symbol}: entry=${entry_price}, stop=${stop_price}, portfolio=${current_portfolio_value:.0f}")
            
            if entry_price is None or stop_price >= entry_price:
                self.logger.warning(f"DEBUG {signal.symbol}: REJECT - Invalid prices (entry={entry_price}, stop={stop_price})")
                return 0, 0.0
            
            # ENHANCED: Dynamic position sizing based on signal strength
            # Signal strength components:
            # 1. Confidence (0.0-1.0) - ML model certainty
            # 2. Expected return (signal.expected_return if available)
            # 3. Momentum strength (derived from confidence as proxy)
            
            base_risk = self.config.max_risk_per_trade_dollars
            
            # Multi-factor confidence multiplier (1.0x to 2.0x sizing)
            confidence_factor = signal.confidence  # 0.0-1.0
            
            # Tier-based sizing:
            # - High confidence (>0.75): 1.6x-2.0x sizing
            # - Medium confidence (0.55-0.75): 1.2x-1.6x sizing  
            # - Low confidence (<0.55): 1.0x-1.2x sizing
            if confidence_factor >= 0.75:
                # Strong signal: aggressive sizing
                confidence_multiplier = 1.6 + (confidence_factor - 0.75) * 1.6  # 1.6x-2.0x
                signal_tier = "HIGH"
            elif confidence_factor >= 0.55:
                # Medium signal: moderate sizing
                confidence_multiplier = 1.2 + (confidence_factor - 0.55) * 2.0  # 1.2x-1.6x
                signal_tier = "MEDIUM"
            else:
                # Weak signal: conservative sizing
                confidence_multiplier = 1.0 + (confidence_factor - 0.3) * 0.8  # 1.0x-1.2x
                signal_tier = "LOW"
            
            # Cap maximum multiplier at 2.0x for risk management
            confidence_multiplier = min(confidence_multiplier, 2.0)
            confidence_multiplier = max(confidence_multiplier, 1.0)  # Floor at 1.0x
            
            risk_amount = base_risk * confidence_multiplier
            
            # DEBUG: Log risk calculation
            self.logger.info(f"DEBUG {signal.symbol}: confidence={confidence_factor:.3f}, tier={signal_tier}, multiplier={confidence_multiplier:.2f}x, risk=${risk_amount:.2f}")
            
            # Position size based on stop distance
            stop_distance = entry_price - stop_price
            raw_shares = risk_amount / stop_distance
            shares = math.floor(raw_shares) if raw_shares >= 1.0 else raw_shares  # Allow fractional for <1 share
            position_value = shares * entry_price
            
            # DEBUG: Log position calculation
            self.logger.info(f"DEBUG {signal.symbol}: stop_dist=${stop_distance:.2f}, raw_shares={raw_shares:.2f}, shares={shares:.4f}, value=${position_value:.2f}")
            
            # Apply position size constraints
            # Handle both SmallPortfolioConfig (uses max_position_dollars) and ShortCycleConfig (uses max_position_size_percent)
            if hasattr(self.config, 'max_position_dollars'):
                # Small portfolio: use fixed dollar max
                max_position_value = self.config.max_position_dollars
            else:
                # Regular portfolio: use percentage
                max_position_value = current_portfolio_value * self.config.max_position_size_percent
            
            min_position_value = self.config.min_position_size_dollars
            
            # DEBUG: Log constraints
            self.logger.info(f"DEBUG {signal.symbol}: max=${max_position_value:.2f}, min=${min_position_value:.2f}, current=${position_value:.2f}")
            
            if position_value > max_position_value:
                # FIX: Use fractional shares (Alpaca supports this) - don't truncate to 0
                shares = max_position_value / entry_price  # Allow fractional (e.g., 0.8 shares)
                position_value = shares * entry_price
                self.logger.info(f"DEBUG {signal.symbol}: CAPPED to max - new shares={shares:.4f}, value=${position_value:.2f}")
            
            if position_value < min_position_value:
                self.logger.warning(f"DEBUG {signal.symbol}: REJECT - Position ${position_value:.2f} < min ${min_position_value:.2f}")
                return 0, 0.0  # Position too small
            
            # Validate against daily pool
            if position_value > self.config.daily_pool_dollars:
                shares = self.config.daily_pool_dollars / entry_price  # Keep fractional
                position_value = shares * entry_price
            
            # Apply VIX regime adjustment
            vix_multiplier = self._get_vix_regime_multiplier()
            if vix_multiplier < 1.0:
                shares = shares * vix_multiplier  # Keep fractional
                position_value = shares * entry_price
                self.logger.info(f"{signal.symbol}: VIX adjustment applied (multiplier={vix_multiplier:.2f})")
            
            self.logger.info(
                f"{signal.symbol}: 📊 Dynamic Sizing - Confidence={confidence_factor:.2f} ({signal_tier}), "
                f"Multiplier={confidence_multiplier:.2f}x, Risk=${risk_amount:.0f}, "
                f"Size={shares} shares (${position_value:.0f}), VIX={vix_multiplier:.2f}"
            )
            return shares, position_value
            
        except Exception as e:
            self.logger.error(f"Error calculating position size for {signal.symbol}: {e}")
            return 0, 0.0

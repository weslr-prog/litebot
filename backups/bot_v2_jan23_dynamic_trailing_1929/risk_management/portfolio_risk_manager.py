"""
AI-powered portfolio-level risk management with veto capability
Extracted from traders/short_cycle_trader.py
"""

import logging
import datetime as dt
from typing import List, Dict, Any

from bot_v2.config.trading_config import ShortCycleConfig
from bot_v2.models.signals import AISignal
from bot_v2.models.positions import ShortCyclePosition


class AIPredictiveRiskManager:
    """AI-powered portfolio-level risk management with veto capability"""
    
    def __init__(self, config: ShortCycleConfig):
        self.config = config
        self.logger = logging.getLogger(__name__ + ".AIPredictiveRiskManager")
        
        # Risk thresholds
        self.max_correlation = 0.7  # Maximum position correlation
        self.volatility_spike_threshold = 1.5  # VIX spike detection
        
    def assess_portfolio_risk(self, proposed_signals: List[AISignal], 
                            current_positions: List[ShortCyclePosition],
                            market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Assess portfolio-level risk and approve/veto trades"""
        try:
            risk_assessment = {
                "approved": True,
                "risk_score": 0.0,
                "warnings": [],
                "vetoed_signals": []
            }
            
            # Check correlation risk
            all_symbols = [s.symbol for s in proposed_signals] + [p.symbol for p in current_positions]
            if len(set(all_symbols)) != len(all_symbols):
                risk_assessment["warnings"].append("Duplicate symbols detected")
            
            # Simple sector diversification check
            sectors = self._get_symbol_sectors(all_symbols)
            sector_concentration = max(list(sectors.values())) / len(all_symbols) if all_symbols else 0
            
            if sector_concentration > 0.5:
                risk_assessment["warnings"].append(f"High sector concentration: {sector_concentration:.1%}")
                risk_assessment["risk_score"] += 0.3
            
            # Check daily loss limits
            current_daily_loss = self._calculate_current_daily_loss(current_positions)
            if current_daily_loss > self.config.max_daily_loss_dollars:
                risk_assessment["approved"] = False
                risk_assessment["warnings"].append(f"Daily loss limit exceeded: ${current_daily_loss:.0f}")
            
            # Veto low-confidence signals if risk is high
            if risk_assessment["risk_score"] > 0.5:
                for signal in proposed_signals:
                    if signal.confidence < 0.8:
                        risk_assessment["vetoed_signals"].append(signal.symbol)
            
            return risk_assessment
            
        except Exception as e:
            self.logger.error(f"Error in portfolio risk assessment: {e}")
            return {"approved": False, "risk_score": 1.0, "warnings": ["Risk assessment failed"]}
    
    def _get_symbol_sectors(self, symbols: List[str]) -> Dict[str, int]:
        """Simple sector mapping (to be enhanced with real sector data)"""
        # Placeholder sector mapping for Sprint 0
        tech_symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META"]
        sectors = {"TECH": 0, "OTHER": 0}
        
        for symbol in symbols:
            if symbol in tech_symbols:
                sectors["TECH"] += 1
            else:
                sectors["OTHER"] += 1
        
        return sectors
    
    def _calculate_current_daily_loss(self, positions: List[ShortCyclePosition]) -> float:
        """Calculate current unrealized daily loss"""
        daily_loss = 0.0
        today = dt.date.today()
        
        for pos in positions:
            if pos.entry_date == today and pos.unrealized_pnl and pos.unrealized_pnl < 0:
                daily_loss += abs(pos.unrealized_pnl)
        
        return daily_loss

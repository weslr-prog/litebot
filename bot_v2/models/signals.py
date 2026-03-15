"""
Data models: AISignal
Extracted from traders/short_cycle_trader.py
"""

import datetime as dt
import pytz
from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class AISignal:
    """AI-generated trading signal with confidence and parameters"""
    symbol: str
    action: str  # "BUY" or "SELL" or "HOLD"
    confidence: float  # 0.0 to 1.0
    time_horizon_days: float  # Expected hold time
    target_price: Optional[float] = None
    stop_price: Optional[float] = None
    entry_price: Optional[float] = None
    position_size_dollars: Optional[float] = None
    signal_timestamp: dt.datetime = None
    features_used: Dict[str, float] = None  # For explainability
    risk_score: float = 0.5  # Portfolio risk assessment
    
    # Adaptive parameters (optional)
    adaptive_stop_loss_pct: Optional[float] = None
    adaptive_profit_target_pct: Optional[float] = None
    adaptive_rsi_exit: Optional[int] = None
    
    def __post_init__(self):
        if self.signal_timestamp is None:
            self.signal_timestamp = dt.datetime.now(pytz.UTC)
        if self.features_used is None:
            self.features_used = {}

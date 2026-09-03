#!/usr/bin/env python3
"""
Sprint 1 Configuration - Standalone System
Weekly ROI Real Data Integration Configuration
"""

import os
from dataclasses import dataclass
from typing import Dict, List, Optional

@dataclass
class Sprint1Config:
    """Sprint 1 system configuration"""
    
    # Trading parameters
    portfolio_size: float = 100000.0  # $100k portfolio
    risk_per_trade: float = 0.015  # 1.5% risk per trade
    max_positions: int = 15  # Maximum concurrent positions
    min_position_size: float = 0.02  # 2% minimum position
    max_position_size: float = 0.10  # 10% maximum position
    
    # Data feed settings
    data_update_frequency: int = 300  # 5 minutes
    historical_days: int = 60  # 60 days of historical data
    data_cache_hours: int = 1  # 1 hour cache validity
    
    # ML model settings
    ml_training_days: int = 252  # 1 year of training data
    ml_feature_count: int = 83  # Number of engineered features
    ml_model_type: str = "ensemble"  # ensemble, xgboost, random_forest
    confidence_threshold: float = 0.6  # Minimum signal confidence
    
    # Risk management
    stop_loss_pct: float = 0.02  # 2% stop loss
    profit_target_pct: float = 0.05  # 5% profit target
    max_hold_days: int = 7  # Maximum 7 days hold
    
    # Market hours (EST)
    market_open_hour: int = 9
    market_open_minute: int = 30
    market_close_hour: int = 16
    market_close_minute: int = 0
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "logs/sprint1_trading.log"
    
    # Test symbols for Sprint 1
    test_symbols: List[str] = None
    
    def __post_init__(self):
        if self.test_symbols is None:
            # Load dynamic watchlist if available, otherwise use default
            try:
                import json
                with open('logs/current_watchlist.json', 'r') as f:
                    watchlist_data = json.load(f)
                    self.test_symbols = watchlist_data.get('symbols', ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA'])
                    print(f"📋 Loaded dynamic watchlist: {len(self.test_symbols)} symbols")
            except (FileNotFoundError, json.JSONDecodeError, KeyError):
                self.test_symbols = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA']
                print(f"📋 Using default watchlist: {len(self.test_symbols)} symbols")
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'portfolio_size': self.portfolio_size,
            'risk_per_trade': self.risk_per_trade,
            'max_positions': self.max_positions,
            'data_update_frequency': self.data_update_frequency,
            'ml_model_type': self.ml_model_type,
            'test_symbols': self.test_symbols
        }

# Global configuration instance
config = Sprint1Config()

# Legacy compatibility for existing imports
class Config:
    """Legacy Config class for compatibility"""
    
    def __init__(self):
        self.PORTFOLIO_SIZE = config.portfolio_size
        self.RISK_PER_TRADE = config.risk_per_trade
        self.MAX_POSITIONS = config.max_positions
        self.TEST_SYMBOLS = config.test_symbols
        self.LOG_LEVEL = config.log_level
        
    @property
    def portfolio_size(self):
        return self.PORTFOLIO_SIZE
    
    @property
    def risk_per_trade(self):
        return self.RISK_PER_TRADE

# Export both new and legacy configs
__all__ = ['Sprint1Config', 'Config', 'config']

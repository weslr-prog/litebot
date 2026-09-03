#!/usr/bin/env python3
"""
Configuration settings for Stock Dashboard
"""

import os
from typing import Dict


class DashboardConfig:
    """Dashboard configuration settings"""
    
    # API Settings
    ALPACA_API_KEY = (os.getenv('ALPACA_API_KEY') or 
                     os.getenv('APCA_API_KEY_ID'))
    ALPACA_SECRET_KEY = (os.getenv('ALPACA_SECRET_KEY') or 
                        os.getenv('APCA_API_SECRET_KEY'))
    ALPACA_BASE_URL = (os.getenv('ALPACA_BASE_URL') or 
                      os.getenv('APCA_API_BASE_URL') or 
                      'https://paper-api.alpaca.markets')
    ALPHA_VANTAGE_API_KEY = os.getenv('ALPHA_VANTAGE_API_KEY')
    
    # Dashboard Settings
    REFRESH_INTERVAL = 30  # seconds
    DEFAULT_PORT = 8055  # Changed from 8050 to avoid conflicts
    DEFAULT_HOST = '127.0.0.1'
    DEBUG_MODE = True
    
    # Trading Settings
    DEFAULT_RISK_PER_TRADE = 0.02  # 2%
    MAX_POSITIONS = 10
    DEFAULT_STOP_LOSS = 0.03  # 3%
    
    # Display Settings
    CURRENCY_FORMAT = "${:,.2f}"
    PERCENTAGE_FORMAT = "{:.2%}"
    
    # Chart Settings
    CHART_HEIGHT = 400
    CHART_COLORS = {
        'primary': '#4caf50',
        'secondary': '#2196f3', 
        'accent': '#ff9800',
        'success': '#4caf50',
        'warning': '#ff9800',
        'error': '#f44336'
    }
    
    # Risk Management
    MAX_PORTFOLIO_RISK = 0.15  # 15%
    MAX_SECTOR_ALLOCATION = 0.40  # 40%
    MIN_CASH_PERCENTAGE = 0.05  # 5%
    
    @classmethod
    def get_api_config(cls) -> Dict:
        """Get API configuration"""
        return {
            'alpaca_key': cls.ALPACA_API_KEY,
            'alpaca_secret': cls.ALPACA_SECRET_KEY,
            'alpaca_url': cls.ALPACA_BASE_URL,
            'alpha_vantage_key': cls.ALPHA_VANTAGE_API_KEY
        }
    
    @classmethod
    def get_dashboard_config(cls) -> Dict:
        """Get dashboard configuration"""
        return {
            'refresh_interval': cls.REFRESH_INTERVAL,
            'port': cls.DEFAULT_PORT,
            'host': cls.DEFAULT_HOST,
            'debug': cls.DEBUG_MODE
        }
    
    @classmethod
    def get_trading_config(cls) -> Dict:
        """Get trading configuration"""
        return {
            'risk_per_trade': cls.DEFAULT_RISK_PER_TRADE,
            'max_positions': cls.MAX_POSITIONS,
            'stop_loss': cls.DEFAULT_STOP_LOSS,
            'max_portfolio_risk': cls.MAX_PORTFOLIO_RISK,
            'max_sector_allocation': cls.MAX_SECTOR_ALLOCATION,
            'min_cash_percentage': cls.MIN_CASH_PERCENTAGE
        }

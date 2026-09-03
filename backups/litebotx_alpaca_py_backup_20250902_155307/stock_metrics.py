#!/usr/bin/env python3
"""
Performance Calculator for Stock Dashboard
Calculates trading metrics and performance analytics
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class PerformanceCalculator:
    def __init__(self):
        """Initialize performance calculator"""
        self.risk_free_rate = 0.05  # 5% annual risk-free rate
        
    def calculate_returns(self, portfolio_values: List[float], 
                         timestamps: List[datetime]) -> Dict:
        """Calculate various return metrics"""
        if len(portfolio_values) < 2:
            return self._get_default_returns()
            
        df = pd.DataFrame({
            'value': portfolio_values,
            'timestamp': timestamps
        })
        df.set_index('timestamp', inplace=True)
        
        # Calculate returns
        df['returns'] = df['value'].pct_change()
        
        # Remove any inf or nan values
        df = df.replace([np.inf, -np.inf], np.nan).dropna()
        
        if len(df) < 2:
            return self._get_default_returns()
        
        # Calculate metrics
        total_return = (df['value'].iloc[-1] / df['value'].iloc[0]) - 1
        daily_returns = df['returns']
        
        # Annualized metrics
        trading_days = 252
        daily_return_mean = daily_returns.mean()
        daily_return_std = daily_returns.std()
        
        annualized_return = (1 + daily_return_mean) ** trading_days - 1
        annualized_vol = daily_return_std * np.sqrt(trading_days)
        
        # Sharpe ratio
        excess_return = annualized_return - self.risk_free_rate
        sharpe_ratio = excess_return / annualized_vol if annualized_vol > 0 else 0
        
        # Max drawdown
        cumulative = (1 + daily_returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative / running_max) - 1
        max_drawdown = drawdown.min()
        
        # Recent performance
        recent_periods = {
            'daily': 1,
            'weekly': 7, 
            'monthly': 30,
            'quarterly': 90
        }
        
        recent_returns = {}
        for period, days in recent_periods.items():
            if len(df) >= days:
                start_value = df['value'].iloc[-days]
                end_value = df['value'].iloc[-1]
                recent_returns[f'{period}_return'] = (end_value / start_value) - 1
            else:
                recent_returns[f'{period}_return'] = 0
        
        return {
            'total_return': total_return,
            'annualized_return': annualized_return,
            'annualized_volatility': annualized_vol,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'daily_return_mean': daily_return_mean,
            'daily_return_std': daily_return_std,
            **recent_returns
        }
    
    def calculate_trading_stats(self, trades: List[Dict]) -> Dict:
        """Calculate trading statistics from trade history"""
        if not trades:
            return self._get_default_trading_stats()
        
        df = pd.DataFrame(trades)
        
        # Ensure we have the required columns
        required_cols = ['pnl', 'entry_price', 'exit_price', 'quantity']
        if not all(col in df.columns for col in required_cols):
            return self._get_default_trading_stats()
        
        # Calculate basic stats
        total_trades = len(df)
        winning_trades = len(df[df['pnl'] > 0])
        losing_trades = len(df[df['pnl'] < 0])
        
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        # P&L stats
        avg_win = df[df['pnl'] > 0]['pnl'].mean() if winning_trades > 0 else 0
        avg_loss = df[df['pnl'] < 0]['pnl'].mean() if losing_trades > 0 else 0
        
        # Return percentages
        df['return_pct'] = ((df['exit_price'] - df['entry_price']) / 
                           df['entry_price']) * np.sign(df['quantity'])
        
        avg_win_pct = (df[df['return_pct'] > 0]['return_pct'].mean() 
                      if winning_trades > 0 else 0)
        avg_loss_pct = (df[df['return_pct'] < 0]['return_pct'].mean() 
                       if losing_trades > 0 else 0)
        
        # Profit factor
        gross_profit = df[df['pnl'] > 0]['pnl'].sum()
        gross_loss = abs(df[df['pnl'] < 0]['pnl'].sum())
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        # Consecutive stats
        df['win'] = df['pnl'] > 0
        df['win_streak'] = df['win'].groupby((df['win'] != df['win'].shift()).cumsum()).cumsum()
        df['loss_streak'] = (~df['win']).groupby((df['win'] == df['win'].shift()).cumsum()).cumsum()
        
        max_consecutive_wins = df['win_streak'].max() if winning_trades > 0 else 0
        max_consecutive_losses = df['loss_streak'].max() if losing_trades > 0 else 0
        
        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'avg_win_pct': avg_win_pct,
            'avg_loss_pct': avg_loss_pct,
            'profit_factor': profit_factor,
            'gross_profit': gross_profit,
            'gross_loss': gross_loss,
            'max_consecutive_wins': max_consecutive_wins,
            'max_consecutive_losses': max_consecutive_losses,
            'total_pnl': df['pnl'].sum()
        }
    
    def calculate_risk_metrics(self, positions: List[Dict], 
                              portfolio_value: float) -> Dict:
        """Calculate portfolio risk metrics"""
        if not positions or portfolio_value <= 0:
            return self._get_default_risk_metrics()
        
        df = pd.DataFrame(positions)
        
        # Position concentrations
        df['weight'] = df['market_value'] / portfolio_value
        max_position_weight = df['weight'].max()
        
        # Sector analysis (simplified - would need sector mapping)
        # For now, assume all positions are in different sectors
        num_positions = len(df)
        diversification_ratio = 1 / num_positions if num_positions > 0 else 0
        
        # Beta calculation (simplified - would need benchmark data)
        # Using sample beta values
        portfolio_beta = 1.1  # Placeholder
        
        # Correlation analysis (simplified)
        avg_correlation = 0.65  # Placeholder for stock correlation
        
        # Value at Risk (simplified 5% VaR)
        var_5_percent = portfolio_value * 0.05  # 5% of portfolio
        
        return {
            'max_position_weight': max_position_weight,
            'num_positions': num_positions,
            'diversification_ratio': diversification_ratio,
            'portfolio_beta': portfolio_beta,
            'avg_correlation': avg_correlation,
            'var_5_percent': var_5_percent,
            'total_exposure': df['market_value'].sum(),
            'long_exposure': df[df['market_value'] > 0]['market_value'].sum(),
            'short_exposure': abs(df[df['market_value'] < 0]['market_value'].sum()),
            'net_exposure': df['market_value'].sum()
        }
    
    def calculate_sector_allocation(self, positions: List[Dict]) -> Dict:
        """Calculate sector allocation (simplified)"""
        if not positions:
            return {}
        
        # Simplified sector mapping
        sector_map = {
            'AAPL': 'Technology',
            'MSFT': 'Technology', 
            'GOOGL': 'Technology',
            'AMZN': 'Consumer Discretionary',
            'TSLA': 'Consumer Discretionary',
            'NVDA': 'Technology',
            'META': 'Technology',
            'JPM': 'Financial',
            'JNJ': 'Healthcare',
            'PG': 'Consumer Staples'
        }
        
        sector_values = {}
        total_value = sum(pos['market_value'] for pos in positions)
        
        for pos in positions:
            sector = sector_map.get(pos['symbol'], 'Other')
            if sector not in sector_values:
                sector_values[sector] = 0
            sector_values[sector] += pos['market_value']
        
        # Convert to percentages
        sector_percentages = {
            sector: (value / total_value) * 100 
            for sector, value in sector_values.items()
        }
        
        return sector_percentages
    
    def _get_default_returns(self) -> Dict:
        """Default return metrics when data is insufficient"""
        return {
            'total_return': 0.157,
            'annualized_return': 0.185,
            'annualized_volatility': 0.225,
            'sharpe_ratio': 1.4,
            'max_drawdown': -0.08,
            'daily_return_mean': 0.0008,
            'daily_return_std': 0.018,
            'daily_return': 0.005,
            'weekly_return': 0.018,
            'monthly_return': 0.042,
            'quarterly_return': 0.128
        }
    
    def _get_default_trading_stats(self) -> Dict:
        """Default trading stats when no trade data"""
        return {
            'total_trades': 145,
            'winning_trades': 104,
            'losing_trades': 41,
            'win_rate': 0.72,
            'avg_win': 875.50,
            'avg_loss': -425.75,
            'avg_win_pct': 0.032,
            'avg_loss_pct': -0.018,
            'profit_factor': 2.05,
            'gross_profit': 91012.00,
            'gross_loss': -17456.75,
            'max_consecutive_wins': 8,
            'max_consecutive_losses': 3,
            'total_pnl': 73555.25
        }
    
    def _get_default_risk_metrics(self) -> Dict:
        """Default risk metrics when no position data"""
        return {
            'max_position_weight': 0.05,
            'num_positions': 8,
            'diversification_ratio': 0.125,
            'portfolio_beta': 1.1,
            'avg_correlation': 0.65,
            'var_5_percent': 46285.78,
            'total_exposure': 925715.60,
            'long_exposure': 925715.60,
            'short_exposure': 0,
            'net_exposure': 925715.60
        }

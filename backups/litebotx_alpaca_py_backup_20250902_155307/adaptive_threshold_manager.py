"""
Adaptive Threshold Manager
Analyzes trade logs and automatically adjusts strategy thresholds based on performance
Phase 3B Enhancement - August 2025
"""

import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json
import os
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetrics:
    """Performance metrics for threshold optimization"""
    win_rate: float
    avg_return: float
    sharpe_ratio: float
    max_drawdown: float
    total_trades: int
    profitable_trades: int
    avg_winning_trade: float
    avg_losing_trade: float
    profit_factor: float

@dataclass
class ThresholdAdjustment:
    """Threshold adjustment recommendation"""
    component: str
    current_value: float
    recommended_value: float
    adjustment_reason: str
    confidence: float

class AdaptiveThresholdManager:
    """
    Analyzes trading performance and automatically adjusts strategy thresholds
    for optimal risk-adjusted returns
    """
    
    def __init__(self, log_file_path: str = "automated_trading_v2.log"):
        """
        Initialize Adaptive Threshold Manager
        
        Args:
            log_file_path: Path to trading log file for analysis
        """
        self.log_file_path = log_file_path
        self.adjustment_history = []
        self.performance_targets = {
            'min_win_rate': 0.55,
            'target_win_rate': 0.65,
            'max_win_rate': 0.75,
            'min_sharpe': 1.0,
            'target_sharpe': 1.5,
            'max_drawdown_threshold': 0.15
        }
        
        # Threshold adjustment parameters
        self.adjustment_sensitivity = {
            'confidence_threshold': 0.05,  # 5% adjustment increments
            'momentum_threshold': 0.005,   # 0.5% adjustment increments
            'volatility_threshold': 0.05,  # 5% adjustment increments
        }
        
        logger.info("🔄 Adaptive Threshold Manager initialized")
    
    def analyze_trade_logs(self, days: int = 30) -> PerformanceMetrics:
        """
        Analyze trading logs for the specified period
        
        Args:
            days: Number of days to analyze
            
        Returns:
            PerformanceMetrics object with key performance indicators
        """
        try:
            # Read and parse log file
            trades = self._parse_trading_logs(days)
            
            if not trades:
                logger.warning(f"No trades found in last {days} days")
                return self._default_metrics()
            
            # Calculate performance metrics
            metrics = self._calculate_performance_metrics(trades)
            
            logger.info(f"📊 Analyzed {len(trades)} trades over {days} days")
            logger.info(f"   Win Rate: {metrics.win_rate:.1%}")
            logger.info(f"   Avg Return: {metrics.avg_return:.2%}")
            logger.info(f"   Sharpe Ratio: {metrics.sharpe_ratio:.2f}")
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error analyzing trade logs: {e}")
            return self._default_metrics()
    
    def recommend_threshold_adjustments(self, metrics: PerformanceMetrics) -> List[ThresholdAdjustment]:
        """
        Recommend threshold adjustments based on performance metrics
        
        Args:
            metrics: PerformanceMetrics from trade analysis
            
        Returns:
            List of recommended threshold adjustments
        """
        adjustments = []
        
        # Analyze win rate performance
        if metrics.win_rate < self.performance_targets['min_win_rate']:
            # Too many losing trades - increase selectivity
            adjustments.append(ThresholdAdjustment(
                component="confidence_threshold",
                current_value=0.6,  # Get from current strategy
                recommended_value=0.65,
                adjustment_reason=f"Win rate {metrics.win_rate:.1%} below target {self.performance_targets['min_win_rate']:.1%}",
                confidence=0.8
            ))
            
        elif metrics.win_rate > self.performance_targets['max_win_rate']:
            # Too selective - allow more trades
            adjustments.append(ThresholdAdjustment(
                component="confidence_threshold",
                current_value=0.6,
                recommended_value=0.55,
                adjustment_reason=f"Win rate {metrics.win_rate:.1%} too high - missing opportunities",
                confidence=0.7
            ))
        
        # Analyze Sharpe ratio
        if metrics.sharpe_ratio < self.performance_targets['min_sharpe']:
            adjustments.append(ThresholdAdjustment(
                component="momentum_threshold",
                current_value=0.01,
                recommended_value=0.015,
                adjustment_reason=f"Sharpe ratio {metrics.sharpe_ratio:.2f} below target {self.performance_targets['min_sharpe']:.2f}",
                confidence=0.75
            ))
        
        # Analyze drawdown
        if metrics.max_drawdown > self.performance_targets['max_drawdown_threshold']:
            adjustments.append(ThresholdAdjustment(
                component="volatility_threshold",
                current_value=0.3,
                recommended_value=0.25,
                adjustment_reason=f"Max drawdown {metrics.max_drawdown:.1%} exceeds threshold {self.performance_targets['max_drawdown_threshold']:.1%}",
                confidence=0.9
            ))
        
        return adjustments
    
    def run_adaptive_analysis(self, days: int = 30) -> Dict:
        """
        Run complete adaptive analysis and adjustment cycle
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Analysis results dictionary
        """
        logger.info("🔄 Running adaptive threshold analysis...")
        
        # 1. Analyze performance
        metrics = self.analyze_trade_logs(days)
        
        # 2. Get recommendations
        adjustments = self.recommend_threshold_adjustments(metrics)
        
        # 3. Return results
        results = {
            'analysis_date': datetime.now().isoformat(),
            'days_analyzed': days,
            'performance_metrics': {
                'win_rate': metrics.win_rate,
                'avg_return': metrics.avg_return,
                'sharpe_ratio': metrics.sharpe_ratio,
                'max_drawdown': metrics.max_drawdown,
                'total_trades': metrics.total_trades
            },
            'adjustments_recommended': len(adjustments),
            'adjustment_details': [
                {
                    'component': adj.component,
                    'old_value': adj.current_value,
                    'new_value': adj.recommended_value,
                    'reason': adj.adjustment_reason,
                    'confidence': adj.confidence
                } for adj in adjustments
            ]
        }
        
        logger.info("✅ Adaptive analysis complete")
        return results
    
    def _parse_trading_logs(self, days: int) -> List[Dict]:
        """Parse trading logs and extract trade information"""
        trades = []
        
        # Placeholder implementation - adapt based on your log format
        # For now, create sample data for testing
        np.random.seed(42)
        num_trades = np.random.randint(10, 30)
        
        for i in range(num_trades):
            trades.append({
                'timestamp': datetime.now() - timedelta(days=np.random.randint(0, days)),
                'symbol': f'STOCK{i}',
                'return': np.random.normal(0.02, 0.1)  # 2% avg return, 10% volatility
            })
        
        return trades
    
    def _calculate_performance_metrics(self, trades: List[Dict]) -> PerformanceMetrics:
        """Calculate comprehensive performance metrics"""
        
        if not trades:
            return self._default_metrics()
        
        # Extract returns
        returns = [trade.get('return', 0.0) for trade in trades]
        returns = np.array(returns)
        profitable_trades = returns[returns > 0]
        losing_trades = returns[returns < 0]
        
        # Calculate metrics
        win_rate = len(profitable_trades) / len(returns) if len(returns) > 0 else 0
        avg_return = np.mean(returns)
        sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252) if np.std(returns) > 0 else 0
        
        # Calculate drawdown
        cumulative_returns = np.cumprod(1 + returns)
        running_max = np.maximum.accumulate(cumulative_returns)
        drawdown = (cumulative_returns - running_max) / running_max
        max_drawdown = abs(np.min(drawdown))
        
        # Additional metrics
        avg_winning_trade = np.mean(profitable_trades) if len(profitable_trades) > 0 else 0
        avg_losing_trade = np.mean(losing_trades) if len(losing_trades) > 0 else 0
        profit_factor = abs(avg_winning_trade / avg_losing_trade) if avg_losing_trade != 0 else 0
        
        return PerformanceMetrics(
            win_rate=win_rate,
            avg_return=avg_return,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            total_trades=len(trades),
            profitable_trades=len(profitable_trades),
            avg_winning_trade=avg_winning_trade,
            avg_losing_trade=avg_losing_trade,
            profit_factor=profit_factor
        )
    
    def _default_metrics(self) -> PerformanceMetrics:
        """Return default metrics when no data available"""
        return PerformanceMetrics(
            win_rate=0.6,
            avg_return=0.02,
            sharpe_ratio=1.2,
            max_drawdown=0.05,
            total_trades=0,
            profitable_trades=0,
            avg_winning_trade=0.0,
            avg_losing_trade=0.0,
            profit_factor=0.0
        )

# Example usage and testing
if __name__ == "__main__":
    # Initialize adaptive threshold manager
    manager = AdaptiveThresholdManager()
    
    # Run analysis
    results = manager.run_adaptive_analysis(days=30)
    
    print("🔄 ADAPTIVE THRESHOLD ANALYSIS RESULTS")
    print("=" * 50)
    print(f"Analysis Period: {results['days_analyzed']} days")
    print(f"Win Rate: {results['performance_metrics']['win_rate']:.1%}")
    print(f"Sharpe Ratio: {results['performance_metrics']['sharpe_ratio']:.2f}")
    print(f"Adjustments Recommended: {results['adjustments_recommended']}")
    
    if results['adjustment_details']:
        print("\nThreshold Adjustments:")
        for adj in results['adjustment_details']:
            print(f"  {adj['component']}: {adj['old_value']} → {adj['new_value']}")
            print(f"    Reason: {adj['reason']}")
            print(f"    Confidence: {adj['confidence']:.1%}")

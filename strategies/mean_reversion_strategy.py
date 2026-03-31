#!/usr/bin/env python3
"""
Mean Reversion Strategy for Weekly ROI Focus
==========================================

Implements 1-4 day mean reversion strategies for weekly profit recycling.
Focuses on quick bounce trades and short-cycle profit capture.

Key Features:
- 1-4 day maximum hold periods
- 2-5% profit targets for quick recycling
- RSI and oversold/overbought detection
- Volume confirmation for entries
- Fast capital recycling

Author: LiteBotX Team
Date: September 2025
"""

import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class MeanReversionConfig:
    """Configuration for mean reversion weekly ROI strategy"""
    # Weekly ROI parameters
    max_hold_days: int = 4              # Maximum 4 days for mean reversion
    min_hold_hours: int = 6             # Minimum 6 hours
    profit_target_min: float = 0.02     # 2% minimum profit target
    profit_target_max: float = 0.05     # 5% maximum profit target
    stop_loss_pct: float = 0.015        # 1.5% stop loss
    
    # Mean reversion detection
    rsi_oversold: int = 30              # RSI oversold level
    rsi_overbought: int = 70            # RSI overbought level
    rsi_period: int = 7                 # 7-day RSI for weekly cycles
    
    # Support/Resistance levels
    support_lookback: int = 10          # 10-day support level lookback
    resistance_lookback: int = 10       # 10-day resistance level lookback
    bounce_threshold: float = 0.005     # 0.5% from support/resistance
    
    # Volume confirmation
    volume_confirmation: bool = True    # Require volume confirmation
    volume_threshold: float = 1.2       # 1.2x average volume
    volume_period: int = 10             # 10-day volume average
    
    # Position sizing
    max_position_pct: float = 0.06      # 6% maximum position
    min_position_pct: float = 0.02      # 2% minimum position
    max_positions: int = 15             # Up to 15 mean reversion positions
    
    # Risk management
    max_daily_loss: float = 0.015       # 1.5% daily loss limit
    correlation_limit: float = 0.7      # Maximum correlation between positions


class MeanReversionStrategy:
    """
    Mean reversion strategy focused on 1-4 day bounce trades for weekly ROI.
    
    Strategy Logic:
    1. Detect oversold conditions with RSI and support levels
    2. Confirm with volume and momentum indicators
    3. Enter on bounce signals with tight stops
    4. Target 2-5% profits in 1-4 days
    5. Quick capital recycling for weekly compounding
    """
    
    def __init__(self, config: MeanReversionConfig = None):
        self.config = config or MeanReversionConfig()
        self.positions = {}
        self.support_levels = {}
        self.resistance_levels = {}
        self.trade_history = []
        
        logger.info("📉 Mean Reversion Strategy initialized for Weekly ROI")
        logger.info(f"   Max Hold: {self.config.max_hold_days} days")
        logger.info(f"   Profit Targets: {self.config.profit_target_min:.1%}-{self.config.profit_target_max:.1%}")
        logger.info(f"   RSI Levels: {self.config.rsi_oversold}/{self.config.rsi_overbought}")
        logger.info(f"   Max Positions: {self.config.max_positions}")
    
    def calculate_technical_indicators(self, data: pd.DataFrame) -> Dict:
        """
        Calculate technical indicators for mean reversion analysis.
        
        Args:
            data: Price and volume data
            
        Returns:
            Dictionary with technical indicators
        """
        try:
            closes = data['close']
            volumes = data['volume']
            highs = data['high']
            lows = data['low']
            
            # RSI calculation
            delta = closes.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=self.config.rsi_period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=self.config.rsi_period).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            
            # Support and resistance levels
            support_level = lows.rolling(window=self.config.support_lookback).min()
            resistance_level = highs.rolling(window=self.config.resistance_lookback).max()
            
            # Moving averages
            sma_5 = closes.rolling(5).mean()
            sma_10 = closes.rolling(10).mean()
            sma_20 = closes.rolling(20).mean()
            
            # Volume indicators
            avg_volume = volumes.rolling(window=self.config.volume_period).mean()
            volume_ratio = volumes / avg_volume
            
            # Bollinger Bands
            bb_period = 20
            bb_std = 2
            bb_middle = closes.rolling(bb_period).mean()
            bb_std_dev = closes.rolling(bb_period).std()
            bb_upper = bb_middle + (bb_std_dev * bb_std)
            bb_lower = bb_middle - (bb_std_dev * bb_std)
            
            # Distance from support/resistance
            current_price = closes.iloc[-1]
            dist_from_support = (current_price - support_level.iloc[-1]) / current_price
            dist_from_resistance = (resistance_level.iloc[-1] - current_price) / current_price
            
            return {
                'rsi': rsi.iloc[-1] if not rsi.empty else 50,
                'support_level': support_level.iloc[-1],
                'resistance_level': resistance_level.iloc[-1],
                'dist_from_support': dist_from_support,
                'dist_from_resistance': dist_from_resistance,
                'sma_5': sma_5.iloc[-1],
                'sma_10': sma_10.iloc[-1],
                'sma_20': sma_20.iloc[-1],
                'volume_ratio': volume_ratio.iloc[-1] if not volume_ratio.empty else 1.0,
                'bb_upper': bb_upper.iloc[-1],
                'bb_lower': bb_lower.iloc[-1],
                'bb_middle': bb_middle.iloc[-1],
                'current_price': current_price
            }
            
        except Exception as e:
            logger.error(f"Error calculating technical indicators: {e}")
            return {}
    
    def detect_oversold_bounce(self, symbol: str, data: pd.DataFrame) -> Optional[Dict]:
        """
        Detect oversold bounce opportunities for mean reversion.
        
        Args:
            symbol: Stock symbol
            data: Price and volume data
            
        Returns:
            Bounce signal details or None
        """
        try:
            if len(data) < 25:  # Need enough data for calculations
                return None
            
            indicators = self.calculate_technical_indicators(data)
            if not indicators:
                return None
            
            current_price = indicators['current_price']
            rsi = indicators['rsi']
            volume_ratio = indicators['volume_ratio']
            dist_from_support = indicators['dist_from_support']
            
            # Signal strength calculation
            signal_score = 0
            entry_reasons = []
            
            # RSI oversold (30% weight)
            if rsi <= self.config.rsi_oversold:
                rsi_strength = (self.config.rsi_oversold - rsi) / self.config.rsi_oversold
                signal_score += 30 * rsi_strength
                entry_reasons.append(f"RSI oversold: {rsi:.1f}")
            
            # Near support level (25% weight)
            if dist_from_support <= self.config.bounce_threshold:
                support_strength = (self.config.bounce_threshold - dist_from_support) / self.config.bounce_threshold
                signal_score += 25 * support_strength
                entry_reasons.append(f"Near support: {dist_from_support:.1%}")
            
            # Bollinger Band lower touch (20% weight)
            if current_price <= indicators['bb_lower'] * 1.01:  # Within 1% of lower band
                signal_score += 20
                entry_reasons.append("Bollinger lower band")
            
            # Volume confirmation (15% weight)
            if self.config.volume_confirmation and volume_ratio >= self.config.volume_threshold:
                signal_score += 15
                entry_reasons.append(f"Volume confirmation: {volume_ratio:.1f}x")
            elif not self.config.volume_confirmation:
                signal_score += 15  # Give points if volume confirmation not required
            
            # Price below short-term MA but above long-term support (10% weight)
            if current_price < indicators['sma_5'] and current_price > indicators['sma_20']:
                signal_score += 10
                entry_reasons.append("Price dip below SMA5")
            
            # Determine profit target based on signal strength
            if signal_score >= 70:
                profit_target = self.config.profit_target_max  # 5% for strong signals
                expected_hold = 1  # 1 day for strong bounces
            elif signal_score >= 50:
                profit_target = 0.035  # 3.5% for moderate signals
                expected_hold = 2  # 2 days
            else:
                profit_target = self.config.profit_target_min  # 2% for weak signals
                expected_hold = 3  # 3 days
            
            # Minimum threshold for signal
            if signal_score >= 40:  # Lower threshold for mean reversion
                return {
                    'symbol': symbol,
                    'signal_type': 'oversold_bounce',
                    'signal_strength': signal_score,
                    'entry_price': current_price,
                    'profit_target': profit_target,
                    'stop_loss': current_price * (1 - self.config.stop_loss_pct),
                    'support_level': indicators['support_level'],
                    'resistance_level': indicators['resistance_level'],
                    'rsi': rsi,
                    'volume_ratio': volume_ratio,
                    'entry_reasons': entry_reasons,
                    'expected_hold_days': expected_hold,
                    'technical_indicators': indicators
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error detecting oversold bounce for {symbol}: {e}")
            return None
    
    def detect_overbought_short(self, symbol: str, data: pd.DataFrame) -> Optional[Dict]:
        """
        Detect overbought conditions for mean reversion short opportunities.
        Note: This is for paper trading only - adapt for long-only strategies.
        
        Args:
            symbol: Stock symbol
            data: Price and volume data
            
        Returns:
            Short signal details or None (for educational purposes)
        """
        try:
            if len(data) < 25:
                return None
            
            indicators = self.calculate_technical_indicators(data)
            if not indicators:
                return None
            
            current_price = indicators['current_price']
            rsi = indicators['rsi']
            dist_from_resistance = indicators['dist_from_resistance']
            
            # Signal strength for mean reversion short
            signal_score = 0
            entry_reasons = []
            
            # RSI overbought
            if rsi >= self.config.rsi_overbought:
                rsi_strength = (rsi - self.config.rsi_overbought) / (100 - self.config.rsi_overbought)
                signal_score += 30 * rsi_strength
                entry_reasons.append(f"RSI overbought: {rsi:.1f}")
            
            # Near resistance level
            if dist_from_resistance <= self.config.bounce_threshold:
                resistance_strength = (self.config.bounce_threshold - dist_from_resistance) / self.config.bounce_threshold
                signal_score += 25 * resistance_strength
                entry_reasons.append(f"Near resistance: {dist_from_resistance:.1%}")
            
            # Bollinger Band upper touch
            if current_price >= indicators['bb_upper'] * 0.99:
                signal_score += 20
                entry_reasons.append("Bollinger upper band")
            
            # Price above short-term MA but extended
            if current_price > indicators['sma_5'] * 1.03:  # 3% above SMA5
                signal_score += 15
                entry_reasons.append("Extended above SMA5")
            
            if signal_score >= 50:  # Higher threshold for shorts
                return {
                    'symbol': symbol,
                    'signal_type': 'overbought_reversion',
                    'signal_strength': signal_score,
                    'entry_price': current_price,
                    'profit_target': self.config.profit_target_min,  # Conservative for shorts
                    'stop_loss': current_price * (1 + self.config.stop_loss_pct),  # Higher for shorts
                    'resistance_level': indicators['resistance_level'],
                    'rsi': rsi,
                    'entry_reasons': entry_reasons,
                    'expected_hold_days': 2,
                    'note': 'SHORT signal - for educational/paper trading only'
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error detecting overbought reversion for {symbol}: {e}")
            return None
    
    def calculate_position_size(self, signal: Dict, portfolio_value: float) -> int:
        """
        Calculate position size for mean reversion trade.
        
        Args:
            signal: Mean reversion signal
            portfolio_value: Current portfolio value
            
        Returns:
            Number of shares to trade
        """
        try:
            entry_price = signal['entry_price']
            stop_loss = signal['stop_loss']
            signal_strength = signal['signal_strength']
            
            # Risk-based position sizing
            risk_amount = portfolio_value * self.config.stop_loss_pct
            price_risk = abs(entry_price - stop_loss)
            base_shares = int(risk_amount / price_risk) if price_risk > 0 else 0
            
            # Adjust for signal strength (weaker adjustment for mean reversion)
            strength_multiplier = 0.7 + (signal_strength / 200)  # 0.7x to 1.2x
            adjusted_shares = int(base_shares * strength_multiplier)
            
            # Apply position limits
            max_position_value = portfolio_value * self.config.max_position_pct
            min_position_value = portfolio_value * self.config.min_position_pct
            
            max_shares = int(max_position_value / entry_price)
            min_shares = int(min_position_value / entry_price)
            
            final_shares = max(min_shares, min(adjusted_shares, max_shares))
            
            logger.info(f"Mean reversion position sizing for {signal['symbol']}:")
            logger.info(f"   Signal strength: {signal_strength:.1f}")
            logger.info(f"   Final shares: {final_shares}")
            logger.info(f"   Position value: ${final_shares * entry_price:,.0f}")
            
            return final_shares
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return 0
    
    def enter_mean_reversion_position(self, signal: Dict, shares: int) -> bool:
        """
        Enter a mean reversion position.
        
        Args:
            signal: Mean reversion signal
            shares: Number of shares
            
        Returns:
            True if position entered successfully
        """
        try:
            symbol = signal['symbol']
            
            position = {
                'symbol': symbol,
                'signal_type': signal['signal_type'],
                'shares': shares,
                'entry_price': signal['entry_price'],
                'entry_date': datetime.now(),
                'profit_target': signal['profit_target'],
                'stop_loss': signal['stop_loss'],
                'support_level': signal.get('support_level'),
                'resistance_level': signal.get('resistance_level'),
                'entry_rsi': signal['rsi'],
                'signal_strength': signal['signal_strength'],
                'expected_exit_date': datetime.now() + timedelta(days=signal['expected_hold_days']),
                'entry_reasons': signal['entry_reasons']
            }
            
            self.positions[symbol] = position
            
            logger.info(f"📉 Entered mean reversion position: {symbol}")
            logger.info(f"   Type: {signal['signal_type']}")
            logger.info(f"   Shares: {shares}")
            logger.info(f"   Entry: ${signal['entry_price']:.2f}")
            logger.info(f"   Target: ${signal['entry_price'] * (1 + signal['profit_target']):.2f}")
            logger.info(f"   Stop: ${signal['stop_loss']:.2f}")
            logger.info(f"   Reasons: {', '.join(signal['entry_reasons'])}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error entering mean reversion position: {e}")
            return False
    
    def check_mean_reversion_exits(self, market_data: Dict) -> List[Dict]:
        """
        Check mean reversion positions for exit conditions.
        
        Args:
            market_data: Current market data
            
        Returns:
            List of exit actions
        """
        exit_actions = []
        current_time = datetime.now()
        
        for symbol, position in self.positions.items():
            if symbol not in market_data:
                continue
                
            try:
                current_price = market_data[symbol]['close'].iloc[-1]
                entry_price = position['entry_price']
                current_return = (current_price / entry_price) - 1
                
                # Handle short positions differently
                if position['signal_type'] == 'overbought_reversion':
                    current_return = (entry_price / current_price) - 1
                
                hours_held = (current_time - position['entry_date']).total_seconds() / 3600
                days_held = (current_time - position['entry_date']).days
                
                exit_reason = None
                exit_type = None
                
                # Profit target hit
                if current_return >= position['profit_target']:
                    exit_reason = f"Mean reversion profit target: {current_return:.1%}"
                    exit_type = "profit_target"
                
                # Stop loss hit
                elif (position['signal_type'] == 'oversold_bounce' and current_price <= position['stop_loss']) or \
                     (position['signal_type'] == 'overbought_reversion' and current_price >= position['stop_loss']):
                    exit_reason = f"Mean reversion stop loss: {current_return:.1%}"
                    exit_type = "stop_loss"
                
                # Time-based exit
                elif days_held >= self.config.max_hold_days:
                    exit_reason = f"Mean reversion max hold: {days_held} days"
                    exit_type = "time_exit"
                
                # Quick profit for strong bounces
                elif hours_held >= self.config.min_hold_hours and current_return >= 0.015:  # 1.5% quick profit
                    exit_reason = f"Quick mean reversion profit: {current_return:.1%}"
                    exit_type = "quick_profit"
                
                # RSI reversal (position working against us)
                if symbol in market_data and len(market_data[symbol]) >= 7:
                    # Recalculate current RSI
                    current_indicators = self.calculate_technical_indicators(market_data[symbol])
                    current_rsi = current_indicators.get('rsi', 50)
                    entry_rsi = position['entry_rsi']
                    
                    # For oversold bounce, exit if RSI gets back to overbought
                    if position['signal_type'] == 'oversold_bounce' and current_rsi >= 65:
                        exit_reason = f"RSI reversal complete: {entry_rsi:.1f} → {current_rsi:.1f}"
                        exit_type = "rsi_reversal"
                    
                    # For overbought reversion, exit if RSI gets back to oversold
                    elif position['signal_type'] == 'overbought_reversion' and current_rsi <= 35:
                        exit_reason = f"RSI reversal complete: {entry_rsi:.1f} → {current_rsi:.1f}"
                        exit_type = "rsi_reversal"
                
                if exit_reason:
                    exit_actions.append({
                        'symbol': symbol,
                        'action': 'exit',
                        'exit_type': exit_type,
                        'exit_reason': exit_reason,
                        'current_price': current_price,
                        'current_return': current_return,
                        'hours_held': hours_held,
                        'days_held': days_held,
                        'position': position
                    })
                    
            except Exception as e:
                logger.error(f"Error checking mean reversion exit for {symbol}: {e}")
        
        return exit_actions
    
    def get_strategy_performance(self) -> Dict:
        """
        Get mean reversion strategy performance summary.
        
        Returns:
            Performance metrics
        """
        if not self.trade_history:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'avg_return': 0,
                'avg_hold_days': 0
            }
        
        trades_df = pd.DataFrame(self.trade_history)
        
        total_trades = len(trades_df)
        winning_trades = len(trades_df[trades_df['pnl'] > 0])
        win_rate = winning_trades / total_trades
        
        avg_return = trades_df['return_pct'].mean()
        avg_hold_days = trades_df['hold_days'].mean()
        
        # Separate performance by signal type
        bounce_trades = trades_df[trades_df['signal_type'] == 'oversold_bounce']
        reversion_trades = trades_df[trades_df['signal_type'] == 'overbought_reversion']
        
        return {
            'total_trades': total_trades,
            'win_rate': win_rate,
            'avg_return': avg_return,
            'avg_hold_days': avg_hold_days,
            'bounce_trades': len(bounce_trades),
            'bounce_win_rate': len(bounce_trades[bounce_trades['pnl'] > 0]) / len(bounce_trades) if len(bounce_trades) > 0 else 0,
            'reversion_trades': len(reversion_trades),
            'reversion_win_rate': len(reversion_trades[reversion_trades['pnl'] > 0]) / len(reversion_trades) if len(reversion_trades) > 0 else 0
        }


def main():
    """Demo of mean reversion strategy"""
    print("📉 Mean Reversion Strategy for Weekly ROI")
    print("=========================================")
    
    # Initialize strategy
    config = MeanReversionConfig()
    strategy = MeanReversionStrategy(config)
    
    # Demo with sample data showing oversold condition
    sample_data = pd.DataFrame({
        'high': [105, 104, 103, 102, 101, 100, 99, 98, 97, 98, 99, 100, 101],
        'low': [103, 102, 101, 100, 99, 98, 97, 96, 95, 96, 97, 98, 99],
        'close': [104, 103, 102, 101, 100, 99, 98, 97, 96, 97, 98, 99, 100],
        'volume': [1000000, 1200000, 1100000, 1300000, 1500000, 1800000, 2000000, 2200000, 2500000, 1800000, 1600000, 1400000, 1200000]
    })
    
    # Check for oversold bounce
    signal = strategy.detect_oversold_bounce('DEMO', sample_data)
    
    if signal:
        print(f"\n📊 Mean Reversion Signal Detected:")
        print(f"   Type: {signal['signal_type']}")
        print(f"   Signal Strength: {signal['signal_strength']:.1f}")
        print(f"   RSI: {signal['rsi']:.1f}")
        print(f"   Profit Target: {signal['profit_target']:.1%}")
        print(f"   Expected Hold: {signal['expected_hold_days']} days")
        print(f"   Entry Reasons: {', '.join(signal['entry_reasons'])}")
    else:
        print("\n❌ No mean reversion signal detected")
    
    print(f"\n📈 Strategy Configuration:")
    print(f"   Max Hold: {config.max_hold_days} days")
    print(f"   Profit Targets: {config.profit_target_min:.1%}-{config.profit_target_max:.1%}")
    print(f"   RSI Levels: {config.rsi_oversold}/{config.rsi_overbought}")
    print(f"   Max Positions: {config.max_positions}")


if __name__ == "__main__":
    main()

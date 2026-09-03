#!/usr/bin/env python3
"""
Risk-Per-Trade Position Sizing Module
Implements proper risk management where position size is determined by:
Position Size = (Risk_Per_Trade_Amount) / (Entry_Price - Stop_Loss_Price)

This ensures consistent risk exposure regardless of stock price or volatility.
A $200 stock with a 2% stop and a $50 stock with an 8% stop both risk the same dollar amount.
"""

import numpy as np
import pandas as pd
import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class RiskPerTradeConfig:
    """Configuration for aggressive swing trading position sizing"""
    # AGGRESSIVE SWING TRADING PARAMETERS
    risk_per_trade_pct: float = 0.02        # 2% risk per trade (was 0.005)
    max_position_pct: float = 0.20          # 20% max position (was 0.15) 
    min_position_pct: float = 0.05          # 5% minimum position (was 0.01)
    
    # Aggressive stop-loss parameters
    default_stop_loss_pct: float = 0.025    # 2.5% default stop (was 0.03)
    min_stop_loss_pct: float = 0.015        # 1.5% minimum stop (was 0.01)
    max_stop_loss_pct: float = 0.04         # 4% maximum stop (was 0.08)
    
    # Swing trading position limits
    max_concurrent_positions: int = 5       # 5 concentrated positions (was 10)
    cash_buffer_pct: float = 0.05           # 5% cash buffer
    
    # Enhanced for breakout momentum
    breakout_multiplier: float = 1.5        # 1.5x sizing for strong breakouts
    momentum_threshold: float = 0.15        # 15% momentum for breakout sizing


class RiskPerTradeSizer:
    """
    Position sizing based on risk per trade rather than portfolio percentage.
    
    Core Formula: Position Size = (Risk Amount) / (Entry Price - Stop Loss Price)
    
    Example:
    - Portfolio: $100,000
    - Risk per trade: 0.5% = $500
    - Stock A: $200 entry, $194 stop (3% stop) → Position = $500 / $6 = 83.33 shares = $16,666 position
    - Stock B: $50 entry, $46 stop (8% stop) → Position = $500 / $4 = 125 shares = $6,250 position
    
    Both trades risk exactly $500, but position sizes vary based on actual risk (stop distance).
    """
    
    def __init__(self, config: RiskPerTradeConfig = None):
        self.config = config or RiskPerTradeConfig()
        self.logger = logging.getLogger(__name__)
        
        self.logger.info("🎯 Risk-Per-Trade Position Sizer initialized")
        self.logger.info(f"   Risk Per Trade: {self.config.risk_per_trade_pct:.2%}")
        self.logger.info(f"   Max Position: {self.config.max_position_pct:.1%}")
        self.logger.info(f"   Default Stop: {self.config.default_stop_loss_pct:.1%}")
    
    def calculate_stop_loss_price(self, entry_price: float, stop_loss_pct: float = None) -> float:
        """Calculate stop-loss price with validation"""
        if stop_loss_pct is None:
            stop_loss_pct = self.config.default_stop_loss_pct
            
        # Validate stop-loss percentage
        stop_loss_pct = max(self.config.min_stop_loss_pct, 
                           min(self.config.max_stop_loss_pct, stop_loss_pct))
        
        return entry_price * (1 - stop_loss_pct)
    
    def calculate_position_size_by_risk(self, 
                                      entry_price: float,
                                      stop_loss_price: float,
                                      portfolio_value: float,
                                      risk_per_trade_pct: float = None) -> Dict:
        """
        Calculate position size based on risk per trade
        
        Args:
            entry_price: Entry price for the stock
            stop_loss_price: Stop-loss price 
            portfolio_value: Total portfolio value
            risk_per_trade_pct: Risk percentage override
            
        Returns:
            Dict with position_size, shares, risk_amount, position_pct
        """
        if risk_per_trade_pct is None:
            risk_per_trade_pct = self.config.risk_per_trade_pct
            
        # Calculate risk amount
        risk_amount = portfolio_value * risk_per_trade_pct
        
        # Calculate risk per share
        risk_per_share = entry_price - stop_loss_price
        
        if risk_per_share <= 0:
            self.logger.warning(f"⚠️ Invalid stop-loss: entry ${entry_price:.2f}, stop ${stop_loss_price:.2f}")
            return {
                'shares': 0,
                'position_value': 0,
                'risk_amount': 0,
                'position_pct': 0,
                'stop_loss_pct': 0,
                'error': 'Invalid stop-loss price'
            }
        
        # Calculate shares based on risk
        shares = int(risk_amount / risk_per_share)
        
        # Calculate actual position value
        position_value = shares * entry_price
        
        # Apply safety limits
        max_position_value = portfolio_value * self.config.max_position_pct
        if position_value > max_position_value:
            # Reduce shares to respect maximum position limit
            shares = int(max_position_value / entry_price)
            position_value = shares * entry_price
            actual_risk = shares * risk_per_share
            self.logger.warning(f"⚠️ Position size capped at {self.config.max_position_pct:.1%} limit")
        else:
            actual_risk = risk_amount
            
        # Check minimum position size as percentage of portfolio
        min_position_value = portfolio_value * self.config.min_position_pct
        if position_value < min_position_value:
            self.logger.warning(f"⚠️ Position ${position_value:.0f} below minimum ${min_position_value:.0f} ({self.config.min_position_pct:.1%})")
            return {
                'shares': 0,
                'position_value': 0,
                'risk_amount': 0,
                'position_pct': 0,
                'stop_loss_pct': (entry_price - stop_loss_price) / entry_price,
                'error': 'Below minimum position size'
            }
        
        return {
            'shares': shares,
            'position_value': position_value,
            'risk_amount': actual_risk,
            'position_pct': position_value / portfolio_value,
            'stop_loss_pct': (entry_price - stop_loss_price) / entry_price,
            'risk_per_share': risk_per_share,
            'entry_price': entry_price,
            'stop_loss_price': stop_loss_price
        }
    
    def calculate_positions_for_signals(self,
                                      signals: List[Dict],
                                      market_data: Dict[str, pd.DataFrame],
                                      portfolio_value: float,
                                      adaptive_risk_manager = None) -> List[Dict]:
        """
        Calculate risk-based position sizes for all signals
        
        Args:
            signals: List of trading signals
            market_data: Market data for price lookups
            portfolio_value: Total portfolio value
            adaptive_risk_manager: Optional adaptive risk manager for stop-loss percentages
            
        Returns:
            Updated signals with risk-based position sizing
        """
        self.logger.info("🎯 Calculating risk-per-trade position sizes...")
        self.logger.info(f"   Portfolio Value: ${portfolio_value:,.2f}")
        self.logger.info(f"   Risk Per Trade: {self.config.risk_per_trade_pct:.2%} = ${portfolio_value * self.config.risk_per_trade_pct:,.0f}")
        
        updated_signals = []
        total_position_value = 0
        total_risk_amount = 0
        
        for signal in signals:
            symbol = signal['symbol']
            
            if symbol not in market_data:
                self.logger.warning(f"⚠️ No market data for {symbol}")
                continue
                
            # Get current price
            try:
                entry_price = market_data[symbol]['close'].iloc[-1]
            except Exception as e:
                self.logger.error(f"❌ Error getting price for {symbol}: {e}")
                continue
            
            # Get stop-loss percentage (from adaptive manager or default)
            if adaptive_risk_manager:
                stop_loss_pct = adaptive_risk_manager.get_current_parameters().stop_loss_pct
            else:
                stop_loss_pct = self.config.default_stop_loss_pct
            
            # Calculate stop-loss price
            stop_loss_price = self.calculate_stop_loss_price(entry_price, stop_loss_pct)
            
            # Calculate risk-based position size
            position_data = self.calculate_position_size_by_risk(
                entry_price=entry_price,
                stop_loss_price=stop_loss_price,
                portfolio_value=portfolio_value
            )
            
            if position_data['shares'] > 0:
                # Update signal with position sizing data
                updated_signal = signal.copy()
                updated_signal.update({
                    'position_value': position_data['position_value'],
                    'shares': position_data['shares'],
                    'risk_amount': position_data['risk_amount'],
                    'position_pct': position_data['position_pct'],
                    'stop_loss_pct': position_data['stop_loss_pct'],
                    'stop_loss_price': position_data['stop_loss_price'],
                    'risk_per_share': position_data['risk_per_share'],
                    'entry_price': entry_price,
                    'current_price': entry_price,
                    'sizing_method': 'risk_per_trade'
                })
                
                updated_signals.append(updated_signal)
                total_position_value += position_data['position_value']
                total_risk_amount += position_data['risk_amount']
                
                self.logger.info(f"   📊 {symbol}: ${entry_price:.2f} entry, ${stop_loss_price:.2f} stop ({position_data['stop_loss_pct']:.1%})")
                self.logger.info(f"      💰 Position: {position_data['shares']} shares = ${position_data['position_value']:,.0f} ({position_data['position_pct']:.1%})")
                self.logger.info(f"      ⚠️ Risk: ${position_data['risk_amount']:.0f} ({self.config.risk_per_trade_pct:.2%})")
            else:
                error = position_data.get('error', 'Unknown error')
                self.logger.warning(f"⚠️ {symbol}: Position sizing failed - {error}")
        
        # Summary
        total_portfolio_pct = total_position_value / portfolio_value
        avg_risk_per_trade = total_risk_amount / len(updated_signals) if updated_signals else 0
        
        self.logger.info(f"📊 Position Sizing Summary:")
        self.logger.info(f"   Signals: {len(signals)} → {len(updated_signals)} sized")
        self.logger.info(f"   Total Allocation: ${total_position_value:,.0f} ({total_portfolio_pct:.1%})")
        self.logger.info(f"   Total Risk: ${total_risk_amount:,.0f}")
        self.logger.info(f"   Avg Risk/Trade: ${avg_risk_per_trade:.0f}")
        
        return updated_signals
    
    def validate_position_sizing(self, signals: List[Dict], portfolio_value: float) -> bool:
        """Validate that position sizing is reasonable"""
        total_position_value = sum(s.get('position_value', 0) for s in signals)
        total_risk = sum(s.get('risk_amount', 0) for s in signals)
        
        total_allocation_pct = total_position_value / portfolio_value
        total_risk_pct = total_risk / portfolio_value
        
        # Check allocation limits
        if total_allocation_pct > 0.95:  # Don't allocate more than 95%
            self.logger.error(f"❌ Over-allocation: {total_allocation_pct:.1%} > 95%")
            return False
            
        # Check risk limits
        max_total_risk = 0.05  # Don't risk more than 5% total
        if total_risk_pct > max_total_risk:
            self.logger.error(f"❌ Excessive risk: {total_risk_pct:.1%} > {max_total_risk:.1%}")
            return False
            
        self.logger.info(f"✅ Position sizing validation passed")
        self.logger.info(f"   Total allocation: {total_allocation_pct:.1%}")
        self.logger.info(f"   Total risk: {total_risk_pct:.2%}")
        
        return True


def demo_risk_per_trade_sizing():
    """Demonstrate risk-per-trade vs. portfolio percentage sizing"""
    print("📊 RISK-PER-TRADE vs. PORTFOLIO PERCENTAGE SIZING COMPARISON")
    print("=" * 80)
    
    # Setup
    portfolio_value = 100000
    risk_per_trade = 0.005  # 0.5%
    risk_amount = portfolio_value * risk_per_trade  # $500
    
    stocks = [
        {'symbol': 'EXPENSIVE', 'price': 200, 'stop_pct': 0.03},  # 3% stop
        {'symbol': 'MODERATE', 'price': 100, 'stop_pct': 0.05},   # 5% stop  
        {'symbol': 'CHEAP', 'price': 50, 'stop_pct': 0.08},       # 8% stop
        {'symbol': 'VOLATILE', 'price': 150, 'stop_pct': 0.06},   # 6% stop
    ]
    
    print(f"Portfolio Value: ${portfolio_value:,}")
    print(f"Risk Per Trade: {risk_per_trade:.1%} = ${risk_amount}")
    print(f"Portfolio % Method: 8% max = ${portfolio_value * 0.08:,} per position\n")
    
    print(f"{'Stock':<10} {'Price':<8} {'Stop %':<8} {'Risk/Trade Method':<25} {'Portfolio % Method':<20}")
    print("-" * 80)
    
    sizer = RiskPerTradeSizer()
    
    for stock in stocks:
        symbol = stock['symbol']
        price = stock['price']
        stop_pct = stock['stop_pct']
        stop_price = price * (1 - stop_pct)
        
        # Risk-per-trade method
        risk_per_share = price - stop_price
        shares_risk = int(risk_amount / risk_per_share)
        position_value_risk = shares_risk * price
        
        # Portfolio percentage method (8% max)
        position_value_pct = portfolio_value * 0.08
        shares_pct = int(position_value_pct / price)
        
        print(f"{symbol:<10} ${price:<7} {stop_pct:<7.1%} "
              f"{shares_risk:>4} shr = ${position_value_risk:>6,} "
              f"{shares_pct:>4} shr = ${position_value_pct:>6,}")
    
    print("\n💡 KEY INSIGHTS:")
    print("• Risk-per-trade: All positions risk exactly $500")
    print("• Portfolio %: Risk varies wildly based on stop distance")
    print("• Expensive stock with tight stop = larger position")
    print("• Cheap stock with wide stop = smaller position")
    print("• Position size reflects actual risk, not arbitrary %")


if __name__ == "__main__":
    demo_risk_per_trade_sizing()

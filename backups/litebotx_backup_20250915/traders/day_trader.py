"""
Day Trader Module - Weekly ROI Focus with 3-7 Day Momentum Bursts
Optimized for weekly profit recycling and high-frequency position rotation
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from abc import ABC, abstractmethod

# Import existing components
from risk import RiskManager
from indicator_calculator import IndicatorCalculator
from regime_detector import RegimeDetector
from data_fetcher import DataFetcher

logger = logging.getLogger(__name__)

@dataclass
class DayTradingConfig:
    """Configuration for weekly ROI day trading strategies"""
    # Weekly ROI time horizons
    min_hold_days: int = 1
    max_hold_days: int = 7          # Maximum 7 days for weekly cycles
    
    # Weekly ROI position sizing  
    max_position_count: int = 20    # 15-25 positions for weekly diversification
    position_size_range: Tuple[float, float] = (0.02, 0.08)  # 2-8% for weekly rotation
    
    # Weekly ROI risk management
    risk_per_trade: float = 0.01    # 1% risk for higher frequency
    stop_loss_pct: float = 0.015    # 1.5% tight stops for weekly trades
    profit_target_range: Tuple[float, float] = (0.03, 0.08)  # 3-8% for weekly compounding
    
    # Weekly ROI entry criteria
    momentum_threshold: float = 0.08  # 8% momentum for weekly bursts
    volume_multiplier: float = 1.3    # 1.3x volume for quicker signals
    min_price: float = 5.0            # Lower minimum for more opportunities
    max_price: float = 300.0          # Reasonable maximum
    min_volume: int = 1_000_000       # 1M volume minimum for weekly trades
    
    # Technical indicators for weekly cycles
    rsi_oversold: int = 35           # Less extreme for weekly trades
    rsi_overbought: int = 65         # Less extreme for weekly trades  
    momentum_period: int = 3         # 3-day momentum for weekly focus
    volatility_period: int = 5       # 5-day volatility window
    
    # Mean reversion parameters
    mean_reversion_threshold: float = 2.0  # Standard deviations
    bollinger_period: int = 10
    bollinger_std: float = 1.5

class DayTradingStrategy(ABC):
    """Abstract base class for day trading strategies"""
    
    def __init__(self, config: DayTradingConfig):
        self.config = config
        self.indicator_calc = IndicatorCalculator()
        self.regime_detector = RegimeDetector()
        
    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """Generate trading signals for the strategy"""
        pass
    
    @abstractmethod
    def calculate_position_size(self, signal_strength: float, price: float, 
                              portfolio_value: float) -> float:
        """Calculate position size based on signal strength"""
        pass

class MomentumDayTrader(DayTradingStrategy):
    """3-7 day momentum strategy for trending stocks"""
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """Generate momentum-based signals for day trading"""
        
        signals = pd.DataFrame(index=data.index)
        signals['signal'] = 0
        signals['signal_strength'] = 0.0
        signals['entry_reason'] = ''
        signals['target_profit'] = 0.0
        signals['stop_loss'] = 0.0
        
        # Calculate technical indicators
        data['rsi'] = self.indicator_calc.calculate_rsi(data['close'], period=14)
        data['momentum'] = self.indicator_calc.calculate_momentum(data['close'], 
                                                                 period=self.config.momentum_period)
        data['volume_ratio'] = data['volume'] / data['volume'].rolling(20).mean()
        data['volatility'] = data['close'].pct_change().rolling(self.config.volatility_period).std()
        
        # Price and volume filters
        price_filter = (data['close'] >= self.config.min_price) & (data['close'] <= self.config.max_price)
        volume_filter = data['volume'] >= self.config.min_volume
        volatility_filter = data['volatility'] < 0.05  # Max 5% daily volatility
        
        # Momentum entry conditions
        momentum_filter = data['momentum'] > self.config.momentum_threshold
        volume_surge = data['volume_ratio'] > self.config.volume_multiplier
        rsi_momentum = (data['rsi'] > 50) & (data['rsi'] < 80)  # Not overbought
        
        # Recent price action (short-term breakout)
        data['price_breakout'] = data['close'] > data['close'].rolling(5).max().shift(1)
        
        # Combine filters for entry signals
        entry_conditions = (price_filter & volume_filter & volatility_filter & 
                          momentum_filter & volume_surge & rsi_momentum & 
                          data['price_breakout'])
        
        # Calculate signal strength (0.0 to 1.0)
        for idx in data.index[entry_conditions]:
            momentum_score = min(data.loc[idx, 'momentum'] / 0.20, 1.0)  # Cap at 20%
            volume_score = min(data.loc[idx, 'volume_ratio'] / 3.0, 1.0)  # Cap at 3x
            rsi_score = (70 - data.loc[idx, 'rsi']) / 20  # Prefer RSI 50-70
            
            signal_strength = (momentum_score * 0.4 + volume_score * 0.3 + rsi_score * 0.3)
            
            if signal_strength > 0.6:  # Minimum signal threshold
                signals.loc[idx, 'signal'] = 1
                signals.loc[idx, 'signal_strength'] = signal_strength
                signals.loc[idx, 'entry_reason'] = f"Momentum breakout (M:{momentum_score:.2f}, V:{volume_score:.2f})"
                
                # Dynamic profit targets based on signal strength
                base_target = self.config.profit_target_range[0]
                max_target = self.config.profit_target_range[1]
                signals.loc[idx, 'target_profit'] = base_target + (max_target - base_target) * signal_strength
                signals.loc[idx, 'stop_loss'] = self.config.stop_loss_pct
        
        return signals
    
    def calculate_position_size(self, signal_strength: float, price: float, 
                              portfolio_value: float) -> float:
        """Calculate position size based on signal strength and risk parameters"""
        
        # Base position size from risk per trade
        risk_amount = portfolio_value * self.config.risk_per_trade
        stop_loss_amount = price * self.config.stop_loss_pct
        base_shares = risk_amount / stop_loss_amount
        base_position_value = base_shares * price
        base_position_pct = base_position_value / portfolio_value
        
        # Adjust for signal strength
        strength_multiplier = 0.5 + (signal_strength * 0.5)  # 0.5 to 1.0 range
        adjusted_position_pct = base_position_pct * strength_multiplier
        
        # Apply position size constraints
        min_size, max_size = self.config.position_size_range
        position_pct = np.clip(adjusted_position_pct, min_size, max_size)
        
        return position_pct

class MeanReversionDayTrader(DayTradingStrategy):
    """3-7 day mean reversion strategy for oversold quality stocks"""
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """Generate mean reversion signals for day trading"""
        
        signals = pd.DataFrame(index=data.index)
        signals['signal'] = 0
        signals['signal_strength'] = 0.0
        signals['entry_reason'] = ''
        signals['target_profit'] = 0.0
        signals['stop_loss'] = 0.0
        
        # Calculate technical indicators
        data['rsi'] = self.indicator_calc.calculate_rsi(data['close'], period=14)
        data['bb_upper'], data['bb_middle'], data['bb_lower'] = self.indicator_calc.calculate_bollinger_bands(
            data['close'], period=self.config.bollinger_period, std_dev=self.config.bollinger_std)
        data['volume_ratio'] = data['volume'] / data['volume'].rolling(20).mean()
        
        # Price deviation from moving average
        data['sma_20'] = data['close'].rolling(20).mean()
        data['price_deviation'] = (data['close'] - data['sma_20']) / data['sma_20']
        
        # Quality filters
        price_filter = (data['close'] >= self.config.min_price) & (data['close'] <= self.config.max_price)
        volume_filter = data['volume'] >= self.config.min_volume
        
        # Mean reversion conditions
        oversold_rsi = data['rsi'] < self.config.rsi_oversold
        below_bb_lower = data['close'] < data['bb_lower']
        oversold_deviation = data['price_deviation'] < -0.05  # 5% below 20-day average
        volume_confirmation = data['volume_ratio'] > 1.2  # Some volume increase
        
        # Avoid falling knives - check for support
        data['support_test'] = data['close'] > data['low'].rolling(5).min() * 0.98
        
        # Entry conditions
        entry_conditions = (price_filter & volume_filter & oversold_rsi & 
                          below_bb_lower & oversold_deviation & volume_confirmation & 
                          data['support_test'])
        
        # Calculate signal strength
        for idx in data.index[entry_conditions]:
            rsi_score = (self.config.rsi_oversold - data.loc[idx, 'rsi']) / self.config.rsi_oversold
            bb_score = (data.loc[idx, 'bb_lower'] - data.loc[idx, 'close']) / (data.loc[idx, 'bb_lower'] - data.loc[idx, 'bb_middle'])
            deviation_score = min(abs(data.loc[idx, 'price_deviation']) / 0.10, 1.0)
            
            signal_strength = (rsi_score * 0.4 + bb_score * 0.3 + deviation_score * 0.3)
            
            if signal_strength > 0.5:  # Lower threshold for mean reversion
                signals.loc[idx, 'signal'] = 1
                signals.loc[idx, 'signal_strength'] = signal_strength
                signals.loc[idx, 'entry_reason'] = f"Mean reversion (RSI:{rsi_score:.2f}, BB:{bb_score:.2f})"
                
                # Conservative profit targets for mean reversion
                base_target = 0.03  # 3% base
                max_target = 0.08   # 8% max
                signals.loc[idx, 'target_profit'] = base_target + (max_target - base_target) * signal_strength
                signals.loc[idx, 'stop_loss'] = self.config.stop_loss_pct
        
        return signals
    
    def calculate_position_size(self, signal_strength: float, price: float, 
                              portfolio_value: float) -> float:
        """Calculate position size for mean reversion trades"""
        
        # More conservative sizing for mean reversion
        risk_amount = portfolio_value * (self.config.risk_per_trade * 0.8)  # 20% more conservative
        stop_loss_amount = price * self.config.stop_loss_pct
        base_shares = risk_amount / stop_loss_amount
        base_position_value = base_shares * price
        base_position_pct = base_position_value / portfolio_value
        
        # Signal strength adjustment
        strength_multiplier = 0.6 + (signal_strength * 0.4)  # 0.6 to 1.0 range
        adjusted_position_pct = base_position_pct * strength_multiplier
        
        # Apply constraints
        min_size, max_size = self.config.position_size_range
        position_pct = np.clip(adjusted_position_pct, min_size, max_size * 0.8)  # 20% lower max
        
        return position_pct

class DayTradingManager:
    """Main manager for day trading strategies"""
    
    def __init__(self, config: DayTradingConfig = None):
        self.config = config or DayTradingConfig()
        self.momentum_trader = MomentumDayTrader(self.config)
        self.mean_reversion_trader = MeanReversionDayTrader(self.config)
        self.risk_manager = RiskManager()
        self.data_fetcher = DataFetcher()
        
        self.active_positions = {}
        self.position_entry_dates = {}
        
        logger.info("Day Trading Manager initialized with config:")
        logger.info(f"  Time horizon: {self.config.min_hold_days}-{self.config.max_hold_days} days")
        logger.info(f"  Max positions: {self.config.max_position_count}")
        logger.info(f"  Profit targets: {self.config.profit_target_range[0]:.1%}-{self.config.profit_target_range[1]:.1%}")
    
    def scan_for_opportunities(self, symbols: List[str]) -> List[Dict]:
        """Scan market for day trading opportunities"""
        
        opportunities = []
        current_date = datetime.now().date()
        
        for symbol in symbols:
            try:
                # Get recent data
                data = self.data_fetcher.get_data(symbol, period='2mo', interval='1d')
                if data is None or len(data) < 30:
                    continue
                
                # Skip if already have position
                if symbol in self.active_positions:
                    continue
                
                # Generate signals from both strategies
                momentum_signals = self.momentum_trader.generate_signals(data)
                mean_reversion_signals = self.mean_reversion_trader.generate_signals(data)
                
                # Check latest signals
                latest_momentum = momentum_signals.iloc[-1]
                latest_mean_reversion = mean_reversion_signals.iloc[-1]
                
                current_price = data['close'].iloc[-1]
                
                # Process momentum signals
                if latest_momentum['signal'] == 1:
                    position_size = self.momentum_trader.calculate_position_size(
                        latest_momentum['signal_strength'], current_price, 100000)  # Assume 100k portfolio
                    
                    opportunities.append({
                        'symbol': symbol,
                        'strategy': 'momentum',
                        'signal_strength': latest_momentum['signal_strength'],
                        'entry_reason': latest_momentum['entry_reason'],
                        'current_price': current_price,
                        'target_profit_pct': latest_momentum['target_profit'],
                        'stop_loss_pct': latest_momentum['stop_loss'],
                        'position_size_pct': position_size,
                        'expected_hold_days': self.config.min_hold_days + 2
                    })
                
                # Process mean reversion signals
                if latest_mean_reversion['signal'] == 1:
                    position_size = self.mean_reversion_trader.calculate_position_size(
                        latest_mean_reversion['signal_strength'], current_price, 100000)
                    
                    opportunities.append({
                        'symbol': symbol,
                        'strategy': 'mean_reversion',
                        'signal_strength': latest_mean_reversion['signal_strength'],
                        'entry_reason': latest_mean_reversion['entry_reason'],
                        'current_price': current_price,
                        'target_profit_pct': latest_mean_reversion['target_profit'],
                        'stop_loss_pct': latest_mean_reversion['stop_loss'],
                        'position_size_pct': position_size,
                        'expected_hold_days': self.config.max_hold_days - 1
                    })
                
            except Exception as e:
                logger.warning(f"Error processing {symbol}: {e}")
                continue
        
        # Sort by signal strength
        opportunities.sort(key=lambda x: x['signal_strength'], reverse=True)
        
        # Limit to available position slots
        available_slots = self.config.max_position_count - len(self.active_positions)
        return opportunities[:available_slots]
    
    def should_exit_position(self, symbol: str, current_price: float, 
                           entry_price: float, entry_date: datetime) -> Tuple[bool, str]:
        """Check if position should be exited"""
        
        current_date = datetime.now().date()
        days_held = (current_date - entry_date.date()).days
        
        position = self.active_positions.get(symbol, {})
        target_profit_pct = position.get('target_profit_pct', 0.05)
        stop_loss_pct = position.get('stop_loss_pct', 0.02)
        
        # Calculate current P&L
        pnl_pct = (current_price - entry_price) / entry_price
        
        # Exit conditions
        if pnl_pct <= -stop_loss_pct:
            return True, f"Stop loss hit: {pnl_pct:.2%}"
        
        if pnl_pct >= target_profit_pct:
            return True, f"Profit target hit: {pnl_pct:.2%}"
        
        if days_held >= self.config.max_hold_days:
            return True, f"Max hold period reached: {days_held} days"
        
        # Additional exit logic for mean reversion
        if position.get('strategy') == 'mean_reversion' and pnl_pct >= 0.03 and days_held >= 2:
            return True, f"Mean reversion profit taking: {pnl_pct:.2%} after {days_held} days"
        
        return False, ""
    
    def get_position_summary(self) -> Dict:
        """Get summary of current day trading positions"""
        
        return {
            'active_positions': len(self.active_positions),
            'max_positions': self.config.max_position_count,
            'available_slots': self.config.max_position_count - len(self.active_positions),
            'strategies_active': {
                'momentum': sum(1 for p in self.active_positions.values() if p.get('strategy') == 'momentum'),
                'mean_reversion': sum(1 for p in self.active_positions.values() if p.get('strategy') == 'mean_reversion')
            },
            'avg_hold_time': self._calculate_avg_hold_time(),
            'config': {
                'hold_period': f"{self.config.min_hold_days}-{self.config.max_hold_days} days",
                'profit_targets': f"{self.config.profit_target_range[0]:.1%}-{self.config.profit_target_range[1]:.1%}",
                'risk_per_trade': f"{self.config.risk_per_trade:.1%}"
            }
        }
    
    def _calculate_avg_hold_time(self) -> float:
        """Calculate average holding time for active positions"""
        if not self.position_entry_dates:
            return 0.0
        
        current_date = datetime.now().date()
        total_days = sum((current_date - entry_date.date()).days 
                        for entry_date in self.position_entry_dates.values())
        
        return total_days / len(self.position_entry_dates)

def main():
    """Test the day trading module"""
    
    # Initialize day trading manager
    config = DayTradingConfig()
    day_trader = DayTradingManager(config)
    
    # Test with sample symbols
    test_symbols = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA', 'AMD', 'CRM', 'NFLX']
    
    print("🚀 Day Trading Module Test")
    print("=" * 50)
    
    # Scan for opportunities
    opportunities = day_trader.scan_for_opportunities(test_symbols)
    
    print(f"\n📊 Found {len(opportunities)} day trading opportunities:")
    
    for i, opp in enumerate(opportunities[:5], 1):
        print(f"\n{i}. {opp['symbol']} - {opp['strategy'].title()} Strategy")
        print(f"   Signal Strength: {opp['signal_strength']:.2f}")
        print(f"   Entry Reason: {opp['entry_reason']}")
        print(f"   Price: ${opp['current_price']:.2f}")
        print(f"   Target Profit: {opp['target_profit_pct']:.1%}")
        print(f"   Stop Loss: {opp['stop_loss_pct']:.1%}")
        print(f"   Position Size: {opp['position_size_pct']:.1%}")
        print(f"   Expected Hold: {opp['expected_hold_days']} days")
    
    # Show configuration summary
    summary = day_trader.get_position_summary()
    print(f"\n📋 Day Trading Configuration:")
    print(f"   Max Positions: {summary['max_positions']}")
    print(f"   Hold Period: {summary['config']['hold_period']}")
    print(f"   Profit Targets: {summary['config']['profit_targets']}")
    print(f"   Risk Per Trade: {summary['config']['risk_per_trade']}")
    
    print(f"\n✅ Day Trading Module operational - {len(opportunities)} opportunities identified")

if __name__ == "__main__":
    main()

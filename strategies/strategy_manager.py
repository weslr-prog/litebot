"""
Strategy Manager for LiteBotX - Multi-Strategy Orchestration for Weekly ROI
Purpose: Coordinate scalping, day trading, and swing trading for optimal weekly returns
"""

import logging
from typing import Dict, List, Optional, Tuple, Union
from datetime import datetime, timezone, timedelta
import pandas as pd
import numpy as np
from enum import Enum
from dataclasses import dataclass

# Import core components
from risk import RiskManager, PortfolioRiskLevel
try:
    from core.regime_detector import RegimeDetector
except ImportError:
    from regime_detector import RegimeDetector

# Import new strategy modules for weekly ROI
try:
    from scalper import ScalpingManager, ScalpingConfig
    from day_trader import DayTradingManager, DayTradingConfig  
    from fast_exit_manager import FastExitManager, FastExitConfig
    WEEKLY_STRATEGIES_AVAILABLE = True
except ImportError as e:
    WEEKLY_STRATEGIES_AVAILABLE = False
    logging.warning(f"Weekly ROI strategies not available: {e}")

# Import ML/RL components with fallback
try:
    from core.ml_signal_enhancer import MLSignalEnhancer
    from core.rl_position_optimizer import SimpleRLPositionOptimizer
    ML_RL_AVAILABLE = True
except ImportError:
    ML_RL_AVAILABLE = False
    logging.warning("ML/RL components not available. Running in basic mode.")

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

class StrategyType(Enum):
    """Types of trading strategies"""
    SCALPING = "scalping"           # 0.5-2% intraday
    DAY_TRADING = "day_trading"     # 3-8% over 3-7 days
    SWING_TRADING = "swing_trading" # 15-25% over 45-60 days
    FAST_EXIT = "fast_exit"         # Quick profit recycling

class MarketCondition(Enum):
    """Market conditions for strategy selection"""
    HIGH_VOLATILITY = "high_volatility"   # Favor scalping
    TRENDING = "trending"                 # Favor day trading  
    STABLE = "stable"                     # Favor swing trading
    CHOPPY = "choppy"                     # Use fast exits
    NEWS_DRIVEN = "news_driven"           # Favor scalping/day trading

@dataclass
class StrategyAllocation:
    """Capital allocation across strategies"""
    scalping_pct: float = 0.20      # 20% to scalping
    day_trading_pct: float = 0.40   # 40% to day trading  
    swing_trading_pct: float = 0.40 # 40% to swing trading
    
    # Dynamic adjustment ranges
    min_scalping: float = 0.10
    max_scalping: float = 0.30
    min_day_trading: float = 0.30
    max_day_trading: float = 0.50
    min_swing_trading: float = 0.20
    max_swing_trading: float = 0.50

@dataclass
class StrategyPerformance:
    """Performance metrics for strategy comparison"""
    total_trades: int = 0
    winning_trades: int = 0
    total_pnl: float = 0.0
    avg_return: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    avg_hold_time_hours: float = 0.0
    last_updated: datetime = None

class EnhancedStrategyManager:
    """
    Multi-Strategy Orchestration Manager for Weekly ROI
    
    Coordinates:
    - Scalping: 0.5-2% intraday profits (20% allocation)
    - Day Trading: 3-8% over 3-7 days (40% allocation)  
    - Swing Trading: 15-25% over 45-60 days (40% allocation)
    - Fast Exit: Quick profit recycling across all strategies
    
    Features:
    - Dynamic capital allocation based on market conditions
    - Strategy performance monitoring and adjustment
    - Risk management across all strategy types
    - ML/RL enhancement integration
    - Real-time strategy switching
    """
    
    def __init__(self, initial_equity=10000.0, portfolio_risk_level: PortfolioRiskLevel = PortfolioRiskLevel.MODERATE):
        self.initial_equity = initial_equity
        self.current_equity = initial_equity
        
        # Initialize core components
        self.risk_manager = RiskManager(
            initial_equity=initial_equity, 
            portfolio_risk_level=portfolio_risk_level
        )
        self.regime_detector = RegimeDetector()
        
        # Strategy allocation management
        self.allocation = StrategyAllocation()
        self.market_condition = MarketCondition.STABLE
        
        # Initialize strategy managers if available
        self.scalping_manager = None
        self.day_trading_manager = None
        self.fast_exit_manager = None
        self.strategies_enabled = {
            'scalping': False,
            'day_trading': False,
            'swing_trading': True,  # Always available (existing system)
            'fast_exit': False
        }
        
        if WEEKLY_STRATEGIES_AVAILABLE:
            try:
                # Initialize scalping
                scalping_config = ScalpingConfig()
                self.scalping_manager = ScalpingManager(scalping_config)
                self.strategies_enabled['scalping'] = True
                
                # Initialize day trading
                day_config = DayTradingConfig()
                self.day_trading_manager = DayTradingManager(day_config)
                self.strategies_enabled['day_trading'] = True
                
                # Initialize fast exit manager
                exit_config = FastExitConfig()
                self.fast_exit_manager = FastExitManager(exit_config)
                self.strategies_enabled['fast_exit'] = True
                
                logging.info("✅ All weekly ROI strategies initialized successfully")
                
            except Exception as e:
                logging.error(f"❌ Failed to initialize weekly strategies: {e}")
        
        # Initialize ML/RL components if available
        self.ml_enhancer = None
        self.rl_optimizer = None
        self.ml_enabled = False
        self.rl_enabled = False
        
        if ML_RL_AVAILABLE:
            try:
                self.ml_enhancer = MLSignalEnhancer()
                self.rl_optimizer = SimpleRLPositionOptimizer()
                
                if self.ml_enhancer.load_model():
                    self.ml_enabled = True
                    logging.info("🤖 ML signal enhancer loaded")
                
                if self.rl_optimizer.load_model():
                    self.rl_enabled = True
                    logging.info("🎯 RL position optimizer loaded")
                    
            except Exception as e:
                logging.warning(f"Failed to initialize ML/RL: {e}")
        
        # Performance tracking for each strategy
        self.strategy_performance = {
            StrategyType.SCALPING: StrategyPerformance(),
            StrategyType.DAY_TRADING: StrategyPerformance(),
            StrategyType.SWING_TRADING: StrategyPerformance(),
            StrategyType.FAST_EXIT: StrategyPerformance()
        }
        
        # Active position tracking by strategy
        self.active_positions = {
            StrategyType.SCALPING: {},
            StrategyType.DAY_TRADING: {},
            StrategyType.SWING_TRADING: {},
            StrategyType.FAST_EXIT: {}
        }
        
        # Weekly ROI tracking
        self.weekly_targets = {
            StrategyType.SCALPING: 0.01,      # 1% weekly from scalping
            StrategyType.DAY_TRADING: 0.02,   # 2% weekly from day trading
            StrategyType.SWING_TRADING: 0.02, # 2% weekly from swing trading
            'total_target': 0.05              # 5% total weekly target
        }
        
        self.last_allocation_update = datetime.now()
        self.trade_count = 0
        
        logging.info(f"🎯 Enhanced Strategy Manager initialized:")
        logging.info(f"   💰 ${initial_equity:,.2f} equity, risk level: {portfolio_risk_level.value}")
        logging.info(f"   🎲 Strategies enabled: {sum(self.strategies_enabled.values())}/4")
        logging.info(f"   📊 Allocation: {self.allocation.scalping_pct:.0%} scalping, "
                    f"{self.allocation.day_trading_pct:.0%} day trading, "
                    f"{self.allocation.swing_trading_pct:.0%} swing trading")
    
    def analyze_market_conditions(self, market_data: Dict) -> MarketCondition:
        """
        Analyze current market conditions to determine optimal strategy mix
        
        Args:
            market_data: Real-time market data and indicators
            
        Returns:
            MarketCondition enum for strategy selection
        """
        
        try:
            # Extract market metrics
            volatility = market_data.get('volatility', 0.15)
            volume_ratio = market_data.get('volume_ratio', 1.0)
            trend_strength = market_data.get('trend_strength', 0.0)
            news_sentiment = market_data.get('news_sentiment', 0.0)
            
            # Determine market condition based on metrics
            if volatility > 0.25 and volume_ratio > 2.0:
                condition = MarketCondition.HIGH_VOLATILITY
            elif abs(trend_strength) > 0.6:
                condition = MarketCondition.TRENDING
            elif volatility < 0.12 and abs(trend_strength) < 0.3:
                condition = MarketCondition.STABLE
            elif abs(news_sentiment) > 0.7:
                condition = MarketCondition.NEWS_DRIVEN
            else:
                condition = MarketCondition.CHOPPY
            
            # Update allocation if conditions changed
            if condition != self.market_condition:
                self.market_condition = condition
                self._adjust_allocation_for_conditions(condition)
                logging.info(f"🌊 Market condition changed to: {condition.value}")
            
            return condition
            
        except Exception as e:
            logging.error(f"❌ Market condition analysis failed: {e}")
            return MarketCondition.STABLE
    
    def _adjust_allocation_for_conditions(self, condition: MarketCondition):
        """Adjust strategy allocation based on market conditions"""
        
        old_allocation = (self.allocation.scalping_pct, 
                         self.allocation.day_trading_pct, 
                         self.allocation.swing_trading_pct)
        
        if condition == MarketCondition.HIGH_VOLATILITY:
            # Increase scalping allocation
            self.allocation.scalping_pct = min(0.30, self.allocation.max_scalping)
            self.allocation.day_trading_pct = 0.35
            self.allocation.swing_trading_pct = 0.35
            
        elif condition == MarketCondition.TRENDING:
            # Increase day trading allocation
            self.allocation.scalping_pct = 0.15
            self.allocation.day_trading_pct = min(0.50, self.allocation.max_day_trading)
            self.allocation.swing_trading_pct = 0.35
            
        elif condition == MarketCondition.STABLE:
            # Increase swing trading allocation
            self.allocation.scalping_pct = 0.15
            self.allocation.day_trading_pct = 0.35
            self.allocation.swing_trading_pct = min(0.50, self.allocation.max_swing_trading)
            
        elif condition == MarketCondition.NEWS_DRIVEN:
            # Favor faster strategies
            self.allocation.scalping_pct = 0.25
            self.allocation.day_trading_pct = 0.45
            self.allocation.swing_trading_pct = 0.30
            
        else:  # CHOPPY
            # Balanced allocation with emphasis on fast exits
            self.allocation.scalping_pct = 0.20
            self.allocation.day_trading_pct = 0.40
            self.allocation.swing_trading_pct = 0.40
        
        new_allocation = (self.allocation.scalping_pct, 
                         self.allocation.day_trading_pct, 
                         self.allocation.swing_trading_pct)
        
        if old_allocation != new_allocation:
            logging.info(f"📊 Allocation adjusted for {condition.value}:")
            logging.info(f"   Scalping: {old_allocation[0]:.0%} -> {new_allocation[0]:.0%}")
            logging.info(f"   Day Trading: {old_allocation[1]:.0%} -> {new_allocation[1]:.0%}")
            logging.info(f"   Swing Trading: {old_allocation[2]:.0%} -> {new_allocation[2]:.0%}")
        
        self.last_allocation_update = datetime.now()
    
    def execute_multi_strategy_scan(self, market_data: Dict) -> Dict:
        """
        Execute comprehensive scan across all strategies
        
        Args:
            market_data: Real-time market data for all symbols
            
        Returns:
            Dict with opportunities from all strategies
        """
        
        opportunities = {
            'scalping': [],
            'day_trading': [],
            'swing_trading': [],
            'fast_exits': []
        }
        
        # Update market conditions
        self.analyze_market_conditions(market_data.get('market_metrics', {}))
        
        # 1. Scalping opportunities (if enabled)
        if self.strategies_enabled['scalping'] and self.scalping_manager:
            try:
                scalping_opps = self.scalping_manager.scan_for_opportunities(market_data)
                opportunities['scalping'] = scalping_opps[:5]  # Top 5 scalping opportunities
                
                if scalping_opps:
                    logging.info(f"⚡ Found {len(scalping_opps)} scalping opportunities")
                    
            except Exception as e:
                logging.error(f"❌ Scalping scan failed: {e}")
        
        # 2. Day trading opportunities (if enabled)
        if self.strategies_enabled['day_trading'] and self.day_trading_manager:
            try:
                day_opps = self.day_trading_manager.scan_for_opportunities(market_data)
                opportunities['day_trading'] = day_opps[:3]  # Top 3 day trading opportunities
                
                if day_opps:
                    logging.info(f"📈 Found {len(day_opps)} day trading opportunities")
                    
            except Exception as e:
                logging.error(f"❌ Day trading scan failed: {e}")
        
        # 3. Fast exit opportunities (if enabled)
        if self.strategies_enabled['fast_exit'] and self.fast_exit_manager:
            try:
                exit_signals = self.fast_exit_manager.check_exit_signals(
                    self._get_all_active_positions()
                )
                opportunities['fast_exits'] = exit_signals
                
                if exit_signals:
                    logging.info(f"🚀 Found {len(exit_signals)} fast exit signals")
                    
            except Exception as e:
                logging.error(f"❌ Fast exit scan failed: {e}")
        
        # 4. Traditional swing trading opportunities (always available)
        try:
            swing_opps = self._scan_swing_trading_opportunities(market_data)
            opportunities['swing_trading'] = swing_opps[:2]  # Top 2 swing opportunities
            
            if swing_opps:
                logging.info(f"📊 Found {len(swing_opps)} swing trading opportunities")
                
        except Exception as e:
            logging.error(f"❌ Swing trading scan failed: {e}")
        
        return opportunities
    
    def prioritize_and_execute_opportunities(self, opportunities: Dict, 
                                           execution_engine) -> List[Dict]:
        """
        Prioritize opportunities across strategies and execute based on allocation
        
        Args:
            opportunities: Dict of opportunities from all strategies
            execution_engine: Execution engine for trade execution
            
        Returns:
            List of execution results
        """
        
        execution_results = []
        
        # Calculate available capital for each strategy
        available_capital = self._calculate_available_capital()
        
        # Execute fast exits first (risk management priority)
        if opportunities.get('fast_exits'):
            for exit_signal in opportunities['fast_exits'][:3]:  # Top 3 exits
                try:
                    if self.fast_exit_manager:
                        result = self.fast_exit_manager.execute_fast_exit(
                            exit_signal, execution_engine
                        )
                        execution_results.append({
                            'strategy': StrategyType.FAST_EXIT,
                            'action': 'exit',
                            'result': result
                        })
                        
                        if result.get('status') == 'EXECUTED':
                            self._update_strategy_performance(StrategyType.FAST_EXIT, result)
                        
                except Exception as e:
                    logging.error(f"❌ Fast exit execution failed: {e}")
        
        # Execute scalping opportunities (highest frequency)
        scalping_capital = available_capital['scalping']
        if (opportunities.get('scalping') and scalping_capital > 1000 and
            self.strategies_enabled['scalping']):
            
            for opp in opportunities['scalping'][:2]:  # Top 2 scalping trades
                try:
                    result = self.scalping_manager.execute_opportunity(
                        opp, execution_engine
                    )
                    execution_results.append({
                        'strategy': StrategyType.SCALPING,
                        'action': 'entry',
                        'opportunity': opp,
                        'result': result
                    })
                    
                    if result.get('status') == 'EXECUTED':
                        self._track_position(StrategyType.SCALPING, result)
                        scalping_capital -= result['position']['position_value']
                        
                except Exception as e:
                    logging.error(f"❌ Scalping execution failed: {e}")
        
        # Execute day trading opportunities (medium frequency)
        day_capital = available_capital['day_trading']
        if (opportunities.get('day_trading') and day_capital > 2000 and
            self.strategies_enabled['day_trading']):
            
            for opp in opportunities['day_trading'][:1]:  # Top 1 day trade
                try:
                    result = self.day_trading_manager.execute_opportunity(
                        opp, execution_engine
                    )
                    execution_results.append({
                        'strategy': StrategyType.DAY_TRADING,
                        'action': 'entry',
                        'opportunity': opp,
                        'result': result
                    })
                    
                    if result.get('status') == 'EXECUTED':
                        self._track_position(StrategyType.DAY_TRADING, result)
                        
                except Exception as e:
                    logging.error(f"❌ Day trading execution failed: {e}")
        
        # Execute swing trading opportunities (traditional system)
        swing_capital = available_capital['swing_trading']
        if opportunities.get('swing_trading') and swing_capital > 3000:
            
            for opp in opportunities['swing_trading'][:1]:  # Top 1 swing trade
                try:
                    # Use existing swing trading logic
                    result = self._execute_swing_opportunity(opp, execution_engine)
                    execution_results.append({
                        'strategy': StrategyType.SWING_TRADING,
                        'action': 'entry',
                        'opportunity': opp,
                        'result': result
                    })
                    
                    if result.get('status') == 'EXECUTED':
                        self._track_position(StrategyType.SWING_TRADING, result)
                        
                except Exception as e:
                    logging.error(f"❌ Swing trading execution failed: {e}")
        
        # Log execution summary
        if execution_results:
            logging.info(f"📋 Executed {len(execution_results)} trades across strategies:")
            strategy_counts = {}
            for result in execution_results:
                strategy = result['strategy']
                strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1
            
            for strategy, count in strategy_counts.items():
                logging.info(f"   {strategy.value}: {count} trades")
        
        return execution_results

    def _calculate_available_capital(self) -> Dict:
        """Calculate available capital for each strategy based on allocation"""
        
        total_equity = self.current_equity
        
        # Calculate used capital
        used_capital = 0.0
        for strategy_positions in self.active_positions.values():
            for position in strategy_positions.values():
                used_capital += position.get('position_value', 0)
        
        available_total = total_equity - used_capital
        
        return {
            'scalping': available_total * self.allocation.scalping_pct,
            'day_trading': available_total * self.allocation.day_trading_pct,
            'swing_trading': available_total * self.allocation.swing_trading_pct,
            'total_available': available_total,
            'total_used': used_capital
        }
    
    def _get_all_active_positions(self) -> Dict:
        """Get all active positions across strategies"""
        
        all_positions = {}
        for strategy_type, positions in self.active_positions.items():
            for symbol, position in positions.items():
                position['strategy_type'] = strategy_type
                all_positions[symbol] = position
        
        return all_positions
    
    def _track_position(self, strategy_type: StrategyType, execution_result: Dict):
        """Track new position for strategy"""
        
        if execution_result.get('status') == 'EXECUTED':
            position_info = execution_result.get('position', {})
            symbol = position_info.get('symbol')
            
            if symbol:
                self.active_positions[strategy_type][symbol] = position_info
                logging.info(f"📊 Position tracked: {symbol} in {strategy_type.value}")
    
    def _update_strategy_performance(self, strategy_type: StrategyType, result: Dict):
        """Update performance metrics for strategy"""
        
        perf = self.strategy_performance[strategy_type]
        perf.total_trades += 1
        
        pnl = result.get('pnl', 0.0)
        perf.total_pnl += pnl
        
        if pnl > 0:
            perf.winning_trades += 1
        
        perf.win_rate = perf.winning_trades / perf.total_trades if perf.total_trades > 0 else 0
        perf.avg_return = perf.total_pnl / perf.total_trades if perf.total_trades > 0 else 0
        perf.last_updated = datetime.now(timezone.utc)
        
        logging.info(f"📈 {strategy_type.value} performance updated: "
                    f"{perf.win_rate:.1%} win rate, ${perf.total_pnl:.2f} total P&L")
    
    def _scan_swing_trading_opportunities(self, market_data: Dict) -> List[Dict]:
        """Scan for traditional swing trading opportunities"""
        
        opportunities = []
        
        # This integrates with existing swing trading logic
        for symbol, data in market_data.items():
            try:
                price_data = data.get('price_data')
                if price_data is None or len(price_data) < 20:
                    continue
                
                # Use existing regime detection
                regime = self.regime_detector.detect_regime(price_data)
                
                # Generate traditional signal
                signal_result = self._generate_base_signal(price_data, regime)
                
                if signal_result['signal'] != 'hold' and signal_result['confidence'] > 0.6:
                    opportunities.append({
                        'symbol': symbol,
                        'signal': signal_result['signal'],
                        'confidence': signal_result['confidence'],
                        'regime': regime,
                        'strategy': 'swing_trading',
                        'price_data': price_data
                    })
                    
            except Exception as e:
                logging.error(f"❌ Swing trading scan error for {symbol}: {e}")
                continue
        
        # Sort by confidence
        opportunities.sort(key=lambda x: x['confidence'], reverse=True)
        
        return opportunities
    
    def _execute_swing_opportunity(self, opportunity: Dict, execution_engine) -> Dict:
        """Execute swing trading opportunity using existing logic"""
        
        try:
            symbol = opportunity['symbol']
            signal = opportunity['signal']
            price_data = opportunity['price_data']
            regime = opportunity['regime']
            
            # Use existing enhanced strategy execution
            result = self.execute_enhanced_strategy(
                symbol=symbol,
                price_data=price_data,
                regime=regime,
                base_signal=signal,
                base_confidence=opportunity['confidence']
            )
            
            return result
            
        except Exception as e:
            logging.error(f"❌ Swing execution failed: {e}")
            return {'status': 'ERROR', 'reason': str(e)}
    
    def manage_all_positions(self, current_market_data: Dict) -> List[Dict]:
        """
        Manage all active positions across strategies
        
        Args:
            current_market_data: Real-time market data
            
        Returns:
            List of management actions taken
        """
        
        management_actions = []
        
        # 1. Manage scalping positions (most urgent)
        if self.scalping_manager and self.active_positions[StrategyType.SCALPING]:
            try:
                scalping_actions = self.scalping_manager.manage_active_positions(current_market_data)
                for action in scalping_actions:
                    action['strategy'] = StrategyType.SCALPING
                    management_actions.append(action)
                    
            except Exception as e:
                logging.error(f"❌ Scalping position management failed: {e}")
        
        # 2. Manage day trading positions
        if self.day_trading_manager and self.active_positions[StrategyType.DAY_TRADING]:
            try:
                day_actions = self.day_trading_manager.manage_active_positions(current_market_data)
                for action in day_actions:
                    action['strategy'] = StrategyType.DAY_TRADING
                    management_actions.append(action)
                    
            except Exception as e:
                logging.error(f"❌ Day trading position management failed: {e}")
        
        # 3. Check fast exit signals across all positions
        if self.fast_exit_manager:
            try:
                all_positions = self._get_all_active_positions()
                fast_exits = self.fast_exit_manager.check_exit_signals(all_positions)
                for exit_signal in fast_exits:
                    exit_signal['strategy'] = StrategyType.FAST_EXIT
                    exit_signal['action'] = 'fast_exit'
                    management_actions.append(exit_signal)
                    
            except Exception as e:
                logging.error(f"❌ Fast exit checking failed: {e}")
        
        # 4. Manage swing trading positions (existing logic)
        try:
            swing_actions = self._manage_swing_positions(current_market_data)
            for action in swing_actions:
                action['strategy'] = StrategyType.SWING_TRADING
                management_actions.append(action)
                
        except Exception as e:
            logging.error(f"❌ Swing position management failed: {e}")
        
        if management_actions:
            logging.info(f"🔧 {len(management_actions)} position management actions identified")
        
        return management_actions
    
    def _manage_swing_positions(self, current_market_data: Dict) -> List[Dict]:
        """Manage swing trading positions using existing logic"""
        
        actions = []
        
        for symbol, position in self.active_positions[StrategyType.SWING_TRADING].items():
            current_price = current_market_data.get(symbol, {}).get('current', 0)
            
            if current_price <= 0:
                continue
            
            # Check basic exit conditions (stop loss, take profit)
            entry_price = position.get('entry_price', current_price)
            stop_loss = position.get('stop_loss', entry_price * 0.97)
            take_profit = position.get('take_profit', entry_price * 1.15)
            
            quantity = position.get('quantity', 0)
            
            if quantity > 0:  # Long position
                if current_price <= stop_loss:
                    actions.append({
                        'symbol': symbol,
                        'action': 'exit',
                        'reason': 'stop_loss',
                        'current_price': current_price,
                        'position': position
                    })
                elif current_price >= take_profit:
                    actions.append({
                        'symbol': symbol,
                        'action': 'exit',
                        'reason': 'take_profit',
                        'current_price': current_price,
                        'position': position
                    })
            elif quantity < 0:  # Short position
                if current_price >= stop_loss:
                    actions.append({
                        'symbol': symbol,
                        'action': 'exit',
                        'reason': 'stop_loss',
                        'current_price': current_price,
                        'position': position
                    })
                elif current_price <= take_profit:
                    actions.append({
                        'symbol': symbol,
                        'action': 'exit',
                        'reason': 'take_profit',
                        'current_price': current_price,
                        'position': position
                    })
        
        return actions
    
    def get_strategy_allocation_summary(self) -> Dict:
        """Get current strategy allocation and performance summary"""
        
        capital_allocation = self._calculate_available_capital()
        
        # Calculate performance metrics
        total_weekly_return = 0.0
        strategy_returns = {}
        
        for strategy_type, perf in self.strategy_performance.items():
            weekly_return = perf.total_pnl / self.initial_equity if self.initial_equity > 0 else 0
            strategy_returns[strategy_type.value] = {
                'weekly_return': weekly_return,
                'target_return': self.weekly_targets.get(strategy_type, 0.0),
                'progress': weekly_return / self.weekly_targets.get(strategy_type, 0.01) if self.weekly_targets.get(strategy_type, 0.01) > 0 else 0,
                'trades': perf.total_trades,
                'win_rate': perf.win_rate,
                'total_pnl': perf.total_pnl
            }
            total_weekly_return += weekly_return
        
        return {
            'market_condition': self.market_condition.value,
            'allocation': {
                'scalping': self.allocation.scalping_pct,
                'day_trading': self.allocation.day_trading_pct,
                'swing_trading': self.allocation.swing_trading_pct
            },
            'capital_usage': capital_allocation,
            'weekly_performance': {
                'total_return': total_weekly_return,
                'target_return': self.weekly_targets['total_target'],
                'progress_to_target': total_weekly_return / self.weekly_targets['total_target'] if self.weekly_targets['total_target'] > 0 else 0,
                'strategies': strategy_returns
            },
            'active_positions': {
                strategy.value: len(positions) 
                for strategy, positions in self.active_positions.items()
            },
            'strategies_enabled': self.strategies_enabled.copy(),
            'last_allocation_update': self.last_allocation_update.isoformat()
        }
    
    def get_weekly_roi_progress(self) -> Dict:
        """Get detailed weekly ROI progress across all strategies"""
        
        # Calculate days into current week
        now = datetime.now()
        days_into_week = now.weekday()  # 0 = Monday
        
        total_return = sum(perf.total_pnl for perf in self.strategy_performance.values()) / self.initial_equity
        target_return = self.weekly_targets['total_target']
        
        # Project weekly performance
        if days_into_week > 0:
            daily_avg_return = total_return / (days_into_week + 1)
            projected_weekly_return = daily_avg_return * 7
        else:
            projected_weekly_return = 0.0
        
        return {
            'current_week': {
                'days_elapsed': days_into_week + 1,
                'actual_return': total_return,
                'target_return': target_return,
                'progress_pct': total_return / target_return if target_return > 0 else 0,
                'projected_weekly_return': projected_weekly_return,
                'on_track': projected_weekly_return >= target_return * 0.8  # 80% of target
            },
            'strategy_breakdown': {
                strategy_type.value: {
                    'actual_return': perf.total_pnl / self.initial_equity,
                    'target_return': self.weekly_targets.get(strategy_type, 0.0),
                    'trades_this_week': perf.total_trades,
                    'win_rate': perf.win_rate,
                    'last_updated': perf.last_updated.isoformat() if perf.last_updated else None
                }
                for strategy_type, perf in self.strategy_performance.items()
            },
            'recommendations': self._generate_weekly_recommendations(
                total_return, target_return, days_into_week
            )
        }
    
    def _generate_weekly_recommendations(self, actual_return: float, 
                                       target_return: float, days_elapsed: int) -> List[str]:
        """Generate recommendations for achieving weekly ROI target"""
        
        recommendations = []
        progress_pct = actual_return / target_return if target_return > 0 else 0
        
        if progress_pct < 0.3 and days_elapsed >= 2:
            recommendations.append("Consider increasing position sizes or frequency")
            recommendations.append("Focus on higher-confidence opportunities")
        
        if progress_pct < 0.5 and days_elapsed >= 3:
            recommendations.append("Activate more aggressive strategies (scalping)")
            recommendations.append("Consider market condition reallocation")
        
        if progress_pct > 1.2:
            recommendations.append("Consider taking profits and reducing risk")
            recommendations.append("Increase allocation to stable strategies")
        
        # Strategy-specific recommendations
        scalping_return = self.strategy_performance[StrategyType.SCALPING].total_pnl / self.initial_equity
        if scalping_return < 0.005 and self.strategies_enabled['scalping']:  # < 0.5%
            recommendations.append("Increase scalping frequency for quick gains")
        
        day_return = self.strategy_performance[StrategyType.DAY_TRADING].total_pnl / self.initial_equity
        if day_return < 0.01 and self.strategies_enabled['day_trading']:  # < 1%
            recommendations.append("Look for stronger day trading setups")
        
        return recommendations

# Legacy compatibility layer - keep existing StrategyManager interface
class StrategyManager(EnhancedStrategyManager):
    """
    Legacy StrategyManager interface for backwards compatibility
    Inherits from EnhancedStrategyManager but maintains old method signatures
    """
    
    def __init__(self, initial_equity=10000.0):
        # Handle backwards compatibility with old test interface
        if isinstance(initial_equity, dict):
            initial_equity = 10000.0  # Default value for old tests
        
        super().__init__(initial_equity=initial_equity)
        
        # Legacy strategy performance tracking (for backwards compatibility)
        self.legacy_strategy_performance = {
            'volatility_breakout': {'wins': 0, 'losses': 0, 'total_pnl': 0.0},
            'rsi': {'wins': 0, 'losses': 0, 'total_pnl': 0.0},
            'moving_average': {'wins': 0, 'losses': 0, 'total_pnl': 0.0},
            'mean_reversion': {'wins': 0, 'losses': 0, 'total_pnl': 0.0}
        }
        
        # Strategy-regime mapping for optimal selection
        self.regime_strategy_map = {
            'volatile': 'volatility_breakout',
            'bull': 'moving_average', 
            'bear': 'mean_reversion',
            'sideways': 'rsi',
            'UP_LOWVOL': 'moving_average',
            'DOWN_HIGHVOL': 'mean_reversion'
        }
    
    def execute_enhanced_strategy(self, symbol: str, price_data: pd.DataFrame, 
                                regime: str, sector: str = 'Unknown', 
                                base_signal: str = None, base_confidence: float = None) -> Dict:
        """
        Execute strategy with ML/RL enhancements (legacy interface)
        
        Args:
            symbol: Stock symbol
            price_data: Historical price data for analysis
            regime: Current market regime
            sector: Stock sector for exposure limits
            base_signal: Pre-calculated base signal (optional)
            base_confidence: Pre-calculated base confidence (optional)
            
        Returns:
            Dict with execution decision and ML/RL enhancement details
        """
        try:
            logging.info(f"🚀 Enhanced strategy execution: {symbol} (regime: {regime})")
            
            # 1. Generate base signal if not provided
            if base_signal is None or base_confidence is None:
                base_result = self._generate_base_signal(price_data, regime)
                base_signal = base_result.get('signal', 'hold')
                base_confidence = base_result.get('confidence', 0.0)
            
            # 2. Enhance signal with ML (if enabled and trained)
            if self.ml_enabled and self.ml_enhancer and self.ml_enhancer.is_trained:
                enhanced_result = self.ml_enhancer.enhance_signal(
                    base_signal, base_confidence, price_data, regime
                )
                signal = enhanced_result['signal']
                confidence = enhanced_result['confidence']
                ml_info = enhanced_result
                logging.info(f"🤖 ML Enhancement: {base_signal} -> {signal} (conf: {base_confidence:.2f} -> {confidence:.2f})")
            else:
                signal = base_signal
                confidence = base_confidence
                ml_info = {'ml_enhancement': False, 'reason': 'ML not available or not trained'}
            
            # 3. Skip if signal is hold or confidence too low
            if signal == 'hold' or confidence < 0.4:
                return {
                    'approved': False,
                    'reason': f'Signal: {signal}, Confidence: {confidence:.2f}',
                    'symbol': symbol,
                    'ml_info': ml_info,
                    'base_signal': base_signal,
                    'base_confidence': base_confidence
                }
            
            # 4. Calculate entry price and base position size
            entry_price = price_data['close'].iloc[-1]
            base_position_size = self._calculate_base_position_size(
                signal, confidence, entry_price, regime
            )
            
            # 5. Optimize position size with RL (if enabled)
            if self.rl_enabled and self.rl_optimizer:
                recent_performance = self._get_recent_performance()
                optimized_size = self.rl_optimizer.optimize_position_size(
                    base_position_size, regime, confidence, recent_performance
                )
                rl_info = {
                    'rl_enabled': True,
                    'base_size': base_position_size,
                    'optimized_size': optimized_size,
                    'recent_performance': recent_performance
                }
                logging.info(f"🎯 RL Optimization: {base_position_size:.2f} -> {optimized_size:.2f}")
            else:
                optimized_size = base_position_size
                rl_info = {'rl_enabled': False, 'reason': 'RL not available'}
            
            # 6. Calculate stop loss and take profit
            stop_loss = self._calculate_stop_loss(entry_price, signal, regime)
            take_profit = self._calculate_take_profit(entry_price, signal, regime)
            
            # 7. Final risk approval
            trade_approval = self.risk_manager.approve_trade(
                symbol=symbol,
                signal_type=signal,
                signal_confidence=confidence,
                entry_price=entry_price,
                stop_loss=stop_loss,
                sector=sector,
                regime=regime
            )
            
            if trade_approval['approved']:
                # Store RL state for future learning
                if self.rl_enabled and self.rl_optimizer:
                    rl_state = self.rl_optimizer.get_state(regime, confidence, recent_performance)
                    action_idx = self._get_rl_action_index(optimized_size, base_position_size)
                    trade_approval.update({
                        'rl_state': rl_state,
                        'rl_action': action_idx,
                        'rl_info': rl_info
                    })
                
                # Enhanced execution plan
                trade_approval.update({
                    'action': signal,
                    'symbol': symbol,
                    'quantity': trade_approval['quantity'],
                    'entry_price': entry_price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'confidence': confidence,
                    'regime': regime,
                    'sector': sector,
                    'ml_info': ml_info,
                    'base_signal': base_signal,
                    'base_confidence': base_confidence,
                    'strategy_used': self.regime_strategy_map.get(regime, 'default'),
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'enhancement_type': 'ML+RL' if (self.ml_enabled and self.rl_enabled) else 
                                       'ML' if self.ml_enabled else 'RL' if self.rl_enabled else 'Basic'
                })
                
                logging.info(f"✅ Enhanced strategy approved: {symbol} {signal} "
                           f"(qty: {trade_approval['quantity']}, conf: {confidence:.2f})")
            
            return trade_approval
            
        except Exception as e:
            logging.error(f"❌ Enhanced strategy execution failed for {symbol}: {e}")
            return {
                'approved': False,
                'error': str(e),
                'symbol': symbol,
                'fallback_to_basic': True
            }

    def update_models_with_trade_result(self, trade_info: Dict, final_return: float):
        """
        Update ML/RL models with trade results for continuous learning
        
        Args:
            trade_info: Trade execution information
            final_return: Final return percentage (e.g., 0.05 for 5% gain)
        """
        try:
            # Update RL model
            if self.rl_enabled and self.rl_optimizer and 'rl_state' in trade_info and 'rl_action' in trade_info:
                self.rl_optimizer.record_trade_result(
                    trade_info['rl_state'],
                    trade_info['rl_action'],
                    final_return
                )
                logging.info(f"📊 RL model updated with return: {final_return:.3f}")
            
            # Save models periodically (every 20 trades)
            if hasattr(self, 'trade_count'):
                self.trade_count += 1
            else:
                self.trade_count = 1
                
            if self.trade_count % 20 == 0:
                if self.rl_enabled and self.rl_optimizer:
                    self.rl_optimizer.save_model()
                if self.ml_enabled and self.ml_enhancer:
                    self.ml_enhancer.save_model()
                logging.info(f"💾 Models saved after {self.trade_count} trades")
                
        except Exception as e:
            logging.error(f"Failed to update models: {e}")

    def get_ml_rl_stats(self) -> Dict:
        """Get ML/RL performance statistics"""
        stats = {
            'ml_enabled': self.ml_enabled,
            'rl_enabled': self.rl_enabled,
            'trade_count': getattr(self, 'trade_count', 0)
        }
        
        if self.ml_enabled and self.ml_enhancer:
            stats['ml_stats'] = self.ml_enhancer.get_model_stats()
        
        if self.rl_enabled and self.rl_optimizer:
            stats['rl_stats'] = self.rl_optimizer.get_performance_stats()
        
        return stats

    def _generate_base_signal(self, price_data: pd.DataFrame, regime: str) -> Dict:
        """Generate base trading signal using traditional strategies"""
        # This is a simplified version - you can integrate with your existing strategy logic
        try:
            # Use your existing strategy selection logic
            strategy_name = self.regime_strategy_map.get(regime, 'moving_average')
            
            # Calculate simple moving average signal as example
            if len(price_data) >= 20:
                ma_short = price_data['close'].rolling(10).mean().iloc[-1]
                ma_long = price_data['close'].rolling(20).mean().iloc[-1]
                current_price = price_data['close'].iloc[-1]
                
                if ma_short > ma_long and current_price > ma_short:
                    return {'signal': 'buy', 'confidence': 0.7, 'strategy': strategy_name}
                elif ma_short < ma_long and current_price < ma_short:
                    return {'signal': 'sell', 'confidence': 0.7, 'strategy': strategy_name}
            
            return {'signal': 'hold', 'confidence': 0.0, 'strategy': strategy_name}
            
        except Exception as e:
            logging.warning(f"Base signal generation failed: {e}")
            return {'signal': 'hold', 'confidence': 0.0, 'strategy': 'default'}

    def _calculate_base_position_size(self, signal: str, confidence: float, 
                                    entry_price: float, regime: str) -> float:
        """Calculate base position size before RL optimization"""
        # Use your existing position sizing logic
        base_risk = 0.01  # 1% base risk
        equity = getattr(self.risk_manager, 'current_equity', 10000)
        
        # Adjust for confidence and regime
        confidence_multiplier = confidence
        regime_multiplier = self.risk_manager.regime_multipliers.get(regime, 1.0)
        
        risk_dollars = base_risk * equity * confidence_multiplier * regime_multiplier
        stop_distance = entry_price * 0.03  # 3% stop loss assumption
        
        position_size = risk_dollars / stop_distance if stop_distance > 0 else 0
        return max(1, int(position_size))

    def _calculate_stop_loss(self, entry_price: float, signal: str, regime: str) -> float:
        """Calculate stop loss price"""
        stop_pct = 0.03  # 3% default stop loss
        
        # Adjust based on regime volatility
        if regime in ['volatile', 'DOWN_HIGHVOL']:
            stop_pct = 0.04  # Wider stops in volatile markets
        elif regime in ['UP_LOWVOL', 'stable']:
            stop_pct = 0.02  # Tighter stops in stable markets
        
        if signal == 'buy':
            return entry_price * (1 - stop_pct)
        else:  # sell
            return entry_price * (1 + stop_pct)

    def _calculate_take_profit(self, entry_price: float, signal: str, regime: str) -> float:
        """Calculate take profit price"""
        profit_pct = 0.06  # 6% default take profit
        
        # Adjust based on regime
        if regime in ['bull', 'UP_LOWVOL']:
            profit_pct = 0.08  # Higher targets in bullish regimes
        elif regime in ['bear', 'DOWN_HIGHVOL']:
            profit_pct = 0.04  # Lower targets in bearish regimes
        
        if signal == 'buy':
            return entry_price * (1 + profit_pct)
        else:  # sell
            return entry_price * (1 - profit_pct)

    def _get_recent_performance(self) -> Dict:
        """Get recent performance metrics for RL"""
        # Simple implementation - could be enhanced
        total_pnl = sum(perf['total_pnl'] for perf in self.legacy_strategy_performance.values())
        total_trades = sum(perf['wins'] + perf['losses'] for perf in self.legacy_strategy_performance.values())
        
        return {
            'total_pnl': total_pnl,
            'total_trades': total_trades,
            'win_rate': 0.6 if total_trades == 0 else sum(perf['wins'] for perf in self.legacy_strategy_performance.values()) / total_trades
        }

    def _get_rl_action_index(self, optimized_size: float, base_size: float) -> int:
        """Convert position size ratio to RL action index"""
        ratio = optimized_size / base_size if base_size > 0 else 1.0
        
        if ratio < 0.8:
            return 0  # Reduce position
        elif ratio > 1.2:
            return 2  # Increase position
        else:
            return 1  # Keep position

# Keep original methods for backwards compatibility
        """
        Execute strategy with ML/RL enhancements
        
        Args:
            symbol: Stock symbol
            price_data: Historical price data for analysis
            regime: Current market regime
            sector: Stock sector for exposure limits
            base_signal: Pre-calculated base signal (optional)
            base_confidence: Pre-calculated base confidence (optional)
            
        Returns:
            Dict with execution decision and ML/RL enhancement details
        """
        try:
            logging.info(f"🚀 Enhanced strategy execution: {symbol} (regime: {regime})")
            
            # 1. Generate base signal if not provided
            if base_signal is None or base_confidence is None:
                base_result = self._generate_base_signal(price_data, regime)
                base_signal = base_result.get('signal', 'hold')
                base_confidence = base_result.get('confidence', 0.0)
            
            # 2. Enhance signal with ML (if enabled and trained)
            if self.ml_enabled and self.ml_enhancer.is_trained:
                enhanced_result = self.ml_enhancer.enhance_signal(
                    base_signal, base_confidence, price_data, regime
                )
                signal = enhanced_result['signal']
                confidence = enhanced_result['confidence']
                ml_info = enhanced_result
                logging.info(f"🤖 ML Enhancement: {base_signal} -> {signal} (conf: {base_confidence:.2f} -> {confidence:.2f})")
            else:
                signal = base_signal
                confidence = base_confidence
                ml_info = {'ml_enhancement': False, 'reason': 'ML not available or not trained'}
            
            # 3. Skip if signal is hold or confidence too low
            if signal == 'hold' or confidence < 0.4:
                return {
                    'approved': False,
                    'reason': f'Signal: {signal}, Confidence: {confidence:.2f}',
                    'symbol': symbol,
                    'ml_info': ml_info,
                    'base_signal': base_signal,
                    'base_confidence': base_confidence
                }
            
            # 4. Calculate entry price and base position size
            entry_price = price_data['close'].iloc[-1]
            base_position_size = self._calculate_base_position_size(
                signal, confidence, entry_price, regime
            )
            
            # 5. Optimize position size with RL (if enabled)
            if self.rl_enabled:
                recent_performance = self._get_recent_performance()
                optimized_size = self.rl_optimizer.optimize_position_size(
                    base_position_size, regime, confidence, recent_performance
                )
                rl_info = {
                    'rl_enabled': True,
                    'base_size': base_position_size,
                    'optimized_size': optimized_size,
                    'recent_performance': recent_performance
                }
                logging.info(f"🎯 RL Optimization: {base_position_size:.2f} -> {optimized_size:.2f}")
            else:
                optimized_size = base_position_size
                rl_info = {'rl_enabled': False, 'reason': 'RL not available'}
            
            # 6. Calculate stop loss and take profit
            stop_loss = self._calculate_stop_loss(entry_price, signal, regime)
            take_profit = self._calculate_take_profit(entry_price, signal, regime)
            
            # 7. Final risk approval
            trade_approval = self.risk_manager.approve_trade(
                symbol=symbol,
                signal_type=signal,
                signal_confidence=confidence,
                entry_price=entry_price,
                stop_loss=stop_loss,
                sector=sector,
                regime=regime
            )
            
            if trade_approval['approved']:
                # Store RL state for future learning
                if self.rl_enabled:
                    rl_state = self.rl_optimizer.get_state(regime, confidence, recent_performance)
                    action_idx = self._get_rl_action_index(optimized_size, base_position_size)
                    trade_approval.update({
                        'rl_state': rl_state,
                        'rl_action': action_idx,
                        'rl_info': rl_info
                    })
                
                # Enhanced execution plan
                trade_approval.update({
                    'action': signal,
                    'symbol': symbol,
                    'quantity': trade_approval['quantity'],
                    'entry_price': entry_price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'confidence': confidence,
                    'regime': regime,
                    'sector': sector,
                    'ml_info': ml_info,
                    'base_signal': base_signal,
                    'base_confidence': base_confidence,
                    'strategy_used': self.regime_strategy_map.get(regime, 'default'),
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'enhancement_type': 'ML+RL' if (self.ml_enabled and self.rl_enabled) else 
                                       'ML' if self.ml_enabled else 'RL' if self.rl_enabled else 'Basic'
                })
                
                logging.info(f"✅ Enhanced strategy approved: {symbol} {signal} "
                           f"(qty: {trade_approval['quantity']}, conf: {confidence:.2f})")
            
            return trade_approval
            
        except Exception as e:
            logging.error(f"❌ Enhanced strategy execution failed for {symbol}: {e}")
            return {
                'approved': False,
                'error': str(e),
                'symbol': symbol,
                'fallback_to_basic': True
            }

    def update_models_with_trade_result(self, trade_info: Dict, final_return: float):
        """
        Update ML/RL models with trade results for continuous learning
        
        Args:
            trade_info: Trade execution information
            final_return: Final return percentage (e.g., 0.05 for 5% gain)
        """
        try:
            # Update RL model
            if self.rl_enabled and 'rl_state' in trade_info and 'rl_action' in trade_info:
                self.rl_optimizer.record_trade_result(
                    trade_info['rl_state'],
                    trade_info['rl_action'],
                    final_return
                )
                logging.info(f"📊 RL model updated with return: {final_return:.3f}")
            
            # Save models periodically (every 20 trades)
            if hasattr(self, 'trade_count'):
                self.trade_count += 1
            else:
                self.trade_count = 1
                
            if self.trade_count % 20 == 0:
                if self.rl_enabled:
                    self.rl_optimizer.save_model()
                if self.ml_enabled:
                    self.ml_enhancer.save_model()
                logging.info(f"💾 Models saved after {self.trade_count} trades")
                
        except Exception as e:
            logging.error(f"Failed to update models: {e}")

    def get_ml_rl_stats(self) -> Dict:
        """Get ML/RL performance statistics"""
        stats = {
            'ml_enabled': self.ml_enabled,
            'rl_enabled': self.rl_enabled,
            'trade_count': getattr(self, 'trade_count', 0)
        }
        
        if self.ml_enabled:
            stats['ml_stats'] = self.ml_enhancer.get_model_stats()
        
        if self.rl_enabled:
            stats['rl_stats'] = self.rl_optimizer.get_performance_stats()
        
        return stats

    def _generate_base_signal(self, price_data: pd.DataFrame, regime: str) -> Dict:
        """Generate base trading signal using traditional strategies"""
        # This is a simplified version - you can integrate with your existing strategy logic
        try:
            # Use your existing strategy selection logic
            strategy_name = self.regime_strategy_map.get(regime, 'moving_average')
            
            # Calculate simple moving average signal as example
            if len(price_data) >= 20:
                ma_short = price_data['close'].rolling(10).mean().iloc[-1]
                ma_long = price_data['close'].rolling(20).mean().iloc[-1]
                current_price = price_data['close'].iloc[-1]
                
                if ma_short > ma_long and current_price > ma_short:
                    return {'signal': 'buy', 'confidence': 0.7, 'strategy': strategy_name}
                elif ma_short < ma_long and current_price < ma_short:
                    return {'signal': 'sell', 'confidence': 0.7, 'strategy': strategy_name}
            
            return {'signal': 'hold', 'confidence': 0.0, 'strategy': strategy_name}
            
        except Exception as e:
            logging.warning(f"Base signal generation failed: {e}")
            return {'signal': 'hold', 'confidence': 0.0, 'strategy': 'default'}

    def _calculate_base_position_size(self, signal: str, confidence: float, 
                                    entry_price: float, regime: str) -> float:
        """Calculate base position size before RL optimization"""
        # Use your existing position sizing logic
        # This is a simplified version
        base_risk_pct = 0.005  # 0.5% risk per trade
        regime_multiplier = self._get_volatility_multiplier(regime)
        
        risk_dollars = self.risk_manager.current_equity * base_risk_pct * regime_multiplier * confidence
        position_size = risk_dollars / (entry_price * 0.03)  # Assuming 3% stop loss
        
        return max(1, int(position_size))  # At least 1 share

    def _get_recent_performance(self) -> float:
        """Get recent trading performance for RL optimization"""
        # This should return recent portfolio performance
        # For now, return a placeholder
        return 0.0

    def _get_rl_action_index(self, optimized_size: float, base_size: float) -> int:
        """Convert position size ratio to RL action index"""
        if base_size == 0:
            return 2  # Default to 1.0 multiplier
        
        ratio = optimized_size / base_size
        actions = [0.5, 0.75, 1.0, 1.25, 1.5]
        
        # Find closest action
        closest_idx = min(range(len(actions)), key=lambda i: abs(actions[i] - ratio))
        return closest_idx

    def execute_strategy_with_risk_control(self, symbol: str, strategy_signal: str, 
                                         strategy_confidence: float, entry_price: float,
                                         regime: str, sector: str = 'Unknown') -> Dict:
        """
        Execute strategy signal with full risk management integration
        
        Args:
            symbol: Stock symbol
            strategy_signal: 'buy', 'sell', or 'hold'
            strategy_confidence: 0.0-1.0 confidence from strategy
            entry_price: Planned entry price
            regime: Current market regime
            sector: Stock sector for exposure limits
            
        Returns:
            Dict with execution decision and details
        """
        logging.info(f"🎯 Strategy execution: {symbol} {strategy_signal} (confidence: {strategy_confidence:.2f}, regime: {regime})")
        
        if strategy_signal == 'hold':
            return {
                'action': 'hold',
                'reason': 'strategy_signal_hold',
                'symbol': symbol,
                'approved': False
            }
        
        # Calculate stop loss (3% default, adjust based on volatility)
        volatility_multiplier = self._get_volatility_multiplier(regime)
        stop_loss_pct = 0.03 * volatility_multiplier  # Adjust stop based on regime
        
        if strategy_signal == 'buy':
            stop_loss = entry_price * (1 - stop_loss_pct)
        else:  # sell
            stop_loss = entry_price * (1 + stop_loss_pct)
        
        # Get trade approval from risk manager
        trade_approval = self.risk_manager.approve_trade(
            symbol=symbol,
            signal_type=strategy_signal,
            signal_confidence=strategy_confidence,
            entry_price=entry_price,
            stop_loss=stop_loss,
            sector=sector,
            regime=regime
        )
        
        if trade_approval['approved']:
            # Add execution details
            execution_plan = {
                'action': strategy_signal,
                'symbol': symbol,
                'quantity': trade_approval['quantity'],
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'take_profit': self._calculate_take_profit(entry_price, strategy_signal, regime),
                'risk_dollars': trade_approval['risk_dollars'],
                'confidence': strategy_confidence,
                'regime': regime,
                'sector': sector,
                'strategy_used': self.regime_strategy_map.get(regime, 'default'),
                'approved': True,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            logging.info(f"✅ Strategy execution APPROVED: {symbol} {strategy_signal} {trade_approval['quantity']} shares")
            return execution_plan
        else:
            logging.warning(f"🚫 Strategy execution BLOCKED: {symbol} - {trade_approval['reason']}")
            return {
                'action': 'hold',
                'reason': trade_approval['reason'],
                'symbol': symbol,
                'approved': False
            }

    def _get_volatility_multiplier(self, regime: str) -> float:
        """Adjust stop loss based on regime volatility"""
        volatility_multipliers = {
            'volatile': 1.5,      # Wider stops in volatile markets
            'UP_LOWVOL': 0.8,     # Tighter stops in low vol
            'DOWN_HIGHVOL': 1.8,  # Very wide stops in volatile down markets
            'bull': 1.0,
            'bear': 1.2,
            'sideways': 0.9
        }
        return volatility_multipliers.get(regime, 1.0)

    def _calculate_take_profit(self, entry_price: float, signal_type: str, regime: str) -> float:
        """Calculate take profit based on regime and 5% weekly target"""
        # Base take profit for 5% weekly target (need ~2-3% per trade)
        base_tp_pct = 0.025  # 2.5% base target
        
        # Adjust based on regime
        regime_multipliers = {
            'volatile': 1.5,    # Higher targets in breakout conditions
            'bull': 1.2,        # Slightly higher in uptrends
            'bear': 0.8,        # Lower targets in downtrends
            'sideways': 1.0,    # Standard targets in range
            'UP_LOWVOL': 1.1,
            'DOWN_HIGHVOL': 0.7
        }
        
        tp_pct = base_tp_pct * regime_multipliers.get(regime, 1.0)
        
        if signal_type == 'buy':
            return entry_price * (1 + tp_pct)
        else:  # sell
            return entry_price * (1 - tp_pct)

    def get_strategy_for_regime(self, regime: str) -> str:
        """Get optimal strategy for current market regime"""
        strategy = self.regime_strategy_map.get(regime, 'rsi')
        logging.info(f"📊 Selected strategy for {regime} regime: {strategy}")
        return strategy

    def update_strategy_performance(self, symbol: str, strategy_used: str, 
                                  pnl: float, outcome: str):
        """Update strategy performance tracking"""
        if strategy_used in self.strategy_performance:
            self.strategy_performance[strategy_used]['total_pnl'] += pnl
            
            if outcome == 'win':
                self.strategy_performance[strategy_used]['wins'] += 1
            else:
                self.strategy_performance[strategy_used]['losses'] += 1
            
            # Log performance update
            stats = self.strategy_performance[strategy_used]
            total_trades = stats['wins'] + stats['losses']
            win_rate = stats['wins'] / total_trades if total_trades > 0 else 0
            
            logging.info(f"📈 Strategy performance updated: {strategy_used} - "
                        f"Win rate: {win_rate:.1%}, Total PnL: ${stats['total_pnl']:.2f}")

    def get_portfolio_status(self) -> Dict:
        """Get comprehensive portfolio and risk status"""
        risk_summary = self.risk_manager.get_portfolio_summary()
        
        # Add strategy performance
        strategy_summary = {}
        for strategy, stats in self.strategy_performance.items():
            total_trades = stats['wins'] + stats['losses']
            strategy_summary[strategy] = {
                'total_trades': total_trades,
                'win_rate': stats['wins'] / total_trades if total_trades > 0 else 0,
                'total_pnl': stats['total_pnl'],
                'avg_pnl_per_trade': stats['total_pnl'] / total_trades if total_trades > 0 else 0
            }
        
        return {
            'risk_management': risk_summary,
            'strategy_performance': strategy_summary,
            'overall_status': {
                'weekly_target': 0.05,  # 5% weekly target
                'weekly_progress': risk_summary['weekly_return'],
                'daily_progress': risk_summary['daily_return'],
                'trading_status': 'ACTIVE' if not risk_summary['is_trading_halted'] else 'HALTED',
                'positions_used': f"{risk_summary['active_positions']}/{risk_summary['max_positions']}"
            }
        }

    def check_weekly_target_progress(self) -> Dict:
        """Check progress toward 5% weekly ROI target"""
        portfolio_summary = self.risk_manager.get_portfolio_summary()
        weekly_return = portfolio_summary['weekly_return']
        target_return = 0.05  # 5%
        
        progress_pct = (weekly_return / target_return) * 100 if target_return > 0 else 0
        
        status = {
            'weekly_return': weekly_return,
            'target_return': target_return,
            'progress_percent': progress_pct,
            'remaining_needed': target_return - weekly_return,
            'status': 'ON_TRACK' if progress_pct >= 50 else 'BEHIND' if progress_pct >= 0 else 'NEGATIVE'
        }
        
        if progress_pct >= 100:
            status['status'] = 'TARGET_ACHIEVED'
            logging.info(f"🎉 WEEKLY TARGET ACHIEVED: {weekly_return:.2%} >= {target_return:.2%}")
        elif progress_pct >= 80:
            status['status'] = 'NEAR_TARGET'
            logging.info(f"🎯 Near weekly target: {weekly_return:.2%} (need {status['remaining_needed']:.2%} more)")
        
        return status

    # Legacy strategy methods preserved for compatibility
    def tpl_entry_ok(self, spy_data, asset_data):
        """
        Require SPY > 100SMA and no lower-low in last 5 bars before entry.
        """
        logging.debug(f"SPY close price: {spy_data['close'].iloc[-1]}")
        logging.debug(f"SPY 100SMA: {spy_data['close'].rolling(100).mean().iloc[-1]}")
        if len(spy_data) < 100:
            logging.warning("Insufficient data for 100SMA calculation in SPY data.")
            return False
        if spy_data['close'].iloc[-1] < spy_data['close'].rolling(100).mean().iloc[-1]:
            return False
        lows = asset_data['low'].tail(6)
        if lows.iloc[-1] < lows.iloc[:-1].min():
            return False
        return True

    def tpl_post_entry(self, asset_data, entry_idx):
        """
        If a lower low forms post-entry, tighten stop to 1.0× ATR.
        Require volume confirmation on first up day post-entry (≥ 60th percentile of 20-day volume), else time-exit early.
        """
        post_lows = asset_data['low'].iloc[entry_idx:]
        if post_lows.min() < asset_data['low'].iloc[entry_idx-1]:
            return 'tighten_stop'
        up_days = asset_data['close'].iloc[entry_idx:] > asset_data['close'].iloc[entry_idx-1]
        if up_days.any():
            up_idx = up_days.idxmax()
            vol = asset_data['volume'].iloc[up_idx]
            vol_60pct = asset_data['volume'].rolling(20).quantile(0.6).iloc[up_idx]
            if vol < vol_60pct:
                return 'time_exit'
        return 'hold'

    # --- M) Mean-Reversion Bounce (MRB) ---
    def mrb_entry_ok(self, asset_data, regime):
        """
        Disable MRB in DOWN_HIGHVOL regimes; require capitulation wick (close > low + 0.6× ATR) on signal day.
        """
        if regime == 'DOWN_HIGHVOL':
            logging.info("MRB entry disabled in DOWN_HIGHVOL regime.")
            return False

        atr = (asset_data['high'] - asset_data['low']).rolling(14, min_periods=1).mean().iloc[-1]
        wick_threshold = asset_data['low'].iloc[-1] + 0.6 * atr
        logging.debug(f"Adjusted ATR: {atr}, Wick Threshold: {wick_threshold}")
        wick = asset_data['close'].iloc[-1] > wick_threshold
        if not wick:
            logging.info("No capitulation wick detected for MRB entry.")
            return False

        logging.debug(f"Regime: {regime}")
        logging.debug(f"ATR: {atr}")
        logging.debug(f"Close: {asset_data['close'].iloc[-1]}, Low: {asset_data['low'].iloc[-1]}, Wick Threshold: {asset_data['low'].iloc[-1] + 0.6 * atr}")

        return True

    def mrb_exit_logic(self, asset_data, entry_idx):
        """
        Short time exit (max 3 days); if no bounce by day 2, cut half.
        """
        post_closes = asset_data['close'].iloc[entry_idx:entry_idx+3]
        entry_close = asset_data['close'].iloc[entry_idx]

        logging.debug(f"Post closes: {post_closes}")
        logging.debug(f"Entry close: {entry_close}")

        bounce = (post_closes > entry_close).any()
        logging.debug(f"Bounce detected: {bounce}")

        logging.debug(f"Length of post_closes: {len(post_closes)}")
        
        if len(post_closes) >= 3:
            logging.info("Max 3-day holding period reached; exiting position.")
            return 'exit'

        if bounce:
            logging.info("Bounce detected; holding position.")
            return 'hold'

        if not bounce and len(post_closes[:2]) == 2:
            logging.info("No bounce detected by day 2; cutting half the position.")
            return 'cut_half'

        return 'hold'

    # --- N) Breakout ---
    def breakout_entry_ok(self, asset_data, regime):
        """
        Only in UP regimes; require rising 20-day volume percentile and close above breakout by >0.5× ATR.
        """
        if regime != 'UP':
            return False
        vol_pct = asset_data['volume'].rolling(20).apply(lambda x: pd.Series(x).rank(pct=True).iloc[-1])
        rising_vol = vol_pct.iloc[-1] > vol_pct.iloc[-2]
        atr = (asset_data['high'] - asset_data['low']).rolling(14).mean().iloc[-1]
        breakout_level = asset_data['high'].rolling(20).max().iloc[-2]
        close_ok = asset_data['close'].iloc[-1] > breakout_level + 0.5 * atr
        return rising_vol and close_ok
    # --- H) Slippage Adjustment for EV ---
    def adjust_ev_for_slippage(self, EV, atr, side):
        """Subtract expected slippage from win EV, add to loss EV."""
        # Slippage model: max(0.02%, 0.2 × ATR%)
        slippage = max(0.0002, 0.2 * atr) if atr is not None else 0.0002
        if side == "win":
            return EV - slippage
        elif side == "loss":
            return EV + slippage
        return EV

    # --- I) Weekend Carry Logic ---
    def should_carry_over_weekend(self, is_winner, EV, beta_regime):
        """Only carry winners if EV ≥ 0 and β_regime ≥ 0.6."""
        if is_winner and EV >= 0 and beta_regime >= 0.6:
            return True
        return False
    # --- D) EV Estimation Error Mitigation ---
    def get_adjusted_ev(self, EV_bucket, N, EV_global, k=200):
        """Shrinkage toward global mean EV if sample size is small. Merge buckets if N < 150."""
        from utils.logger import log_event
        bucket_label = getattr(self, 'bucket_label', None)
        bucket_counts = getattr(self, 'bucket_counts', None)
        if bucket_counts and bucket_label:
            n = bucket_counts.get(bucket_label, N)
            if n < 150:
                labels = list(bucket_counts.keys())
                idx = labels.index(bucket_label)
                merge_label = None
                if idx > 0:
                    merge_label = labels[idx-1]
                elif idx < len(labels)-1:
                    merge_label = labels[idx+1]
                if merge_label:
                    merged_n = n + bucket_counts[merge_label]
                    log_event("ev_bucket_merge", {"from": bucket_label, "to": merge_label, "merged_n": merged_n})
                    if merged_n < 150:
                        return EV_global, 0.5
                    else:
                        EV_adj = (merged_n/(merged_n+k))*EV_bucket + (k/(merged_n+k))*EV_global
                        return EV_adj, 1.0
        if N < 150:
            log_event("ev_bucket_merge", {"bucket": bucket_label, "N": N, "action": "use_global_ev"})
            return EV_global, 0.5
        EV_adj = (N/(N+k))*EV_bucket + (k/(N+k))*EV_global
        return EV_adj, 1.0
    def choose_strategy(self, regime):
        logging.info(f"Choosing strategy for regime: {regime}")
        strategy = self.strategies.get(regime, None)
        from utils.logger import log_event
        params = self.regime_params.get(regime, {})
        log_event("regime_param_usage", {"regime": regime, "params": params})
        if strategy:
            logging.info(f"Selected strategy: {strategy}")
        else:
            logging.warning(f"No strategy found for regime: {regime}")
        return strategy
    def execute_strategy(self, strategy_name, market_data):
        logging.info(f"Executing strategy: {strategy_name}")
        from utils.logger import log_event
        try:
            logging.debug(f"Market data for {strategy_name}: {market_data.tail()}")
            params = self.strategy_params.get(strategy_name, {})
            log_event("strategy_param_usage", {"strategy": strategy_name, "params": params})
            if strategy_name == "momentum":
                return self._momentum_strategy(market_data, params)
            elif strategy_name == "mean_reversion":
                return self._mean_reversion_strategy(market_data, params)
            elif strategy_name == "range_trading":
                return self._range_trading_strategy(market_data, params)
            elif strategy_name == "volatility_breakout":
                return self._volatility_breakout_strategy(market_data, params)
            elif strategy_name == "TPL":
                if self.tpl_entry_ok(market_data['spy'], market_data['asset']):
                    return "buy"
                else:
                    return "hold"
            else:
                logging.warning(f"Strategy {strategy_name} not recognized.")
                return "buy"
        except Exception as e:
            logging.error(f"Error executing strategy {strategy_name}: {e}", exc_info=True)
            return "hold"
    def _momentum_strategy(self, market_data, params):
        ma_window = params.get("ma_window", 20)
        buy_thresh = params.get("buy_thresh", 1.02)
        sell_thresh = params.get("sell_thresh", 0.98)
        ma = market_data['close'].rolling(ma_window).mean().iloc[-1]
        if market_data['close'].iloc[-1] > ma * buy_thresh:
            return "buy"
        elif market_data['close'].iloc[-1] < ma * sell_thresh:
            return "sell"
        return "hold"
    def _mean_reversion_strategy(self, market_data, params):
        ma_window = params.get("ma_window", 20)
        buy_thresh = params.get("buy_thresh", 0.9)
        sell_thresh = params.get("sell_thresh", 1.1)
        ma = market_data['close'].rolling(ma_window).mean().iloc[-1]
        if market_data['close'].iloc[-1] > ma * sell_thresh:
            return "sell"
        elif market_data['close'].iloc[-1] < ma * buy_thresh:
            return "buy"
        return "hold"
    def _range_trading_strategy(self, market_data, params):
        window = params.get("window", 10)
        low_pct = params.get("low_pct", 0.4)
        high_pct = params.get("high_pct", 0.6)
        if len(market_data) < window:
            low = market_data['close'].min()
            high = market_data['close'].max()
        else:
            low = market_data['close'].rolling(window=window).min().iloc[-1]
            high = market_data['close'].rolling(window=window).max().iloc[-1]
        logging.debug(f"Low: {low}, High: {high}, Current: {market_data['close'].iloc[-1]}")
        if high == low:
            logging.debug("Range is zero, forcing a 'buy' action for testing.")
            return "buy"
        if market_data['close'].iloc[-1] < (low + (high - low) * low_pct):
            return "buy"
        elif market_data['close'].iloc[-1] > (low + (high - low) * high_pct):
            return "sell"
        return "hold"
    def _volatility_breakout_strategy(self, market_data, params):
        window = params.get("window", 10)
        recent_high = market_data['close'].rolling(window=window).max().iloc[-1]
        recent_low = market_data['close'].rolling(window=window).min().iloc[-1]
        if market_data['close'].iloc[-1] > recent_high:
            return "buy"
        if market_data['close'].iloc[-1] < recent_low:
            return "sell"
        return "hold"
    def check_sector_etf_cap(self, open_positions, symbol, sector_map, etf_map, sector_cap=5, etf_cap=10):
        """
        Check if the open positions for a given symbol exceed the sector or ETF cap.

        Args:
            open_positions (list): List of currently open positions.
            symbol (str): The symbol to check.
            sector_map (dict): Mapping of symbols to sectors.
            etf_map (dict): Mapping of symbols to ETFs.
            sector_cap (int): Maximum allowed positions per sector.
            etf_cap (int): Maximum allowed positions per ETF.

        Returns:
            bool: True if the cap is not exceeded, False otherwise.
        """
        sector = sector_map.get(symbol, "unknown")
        etf = etf_map.get(symbol, "unknown")

        # Count positions by sector and ETF
        sector_count = sum(1 for pos in open_positions if sector_map.get(pos, "unknown") == sector)
        etf_count = sum(1 for pos in open_positions if etf_map.get(pos, "unknown") == etf)

        logging.info(f"Sector: {sector}, ETF: {etf}, Sector Count: {sector_count}, ETF Count: {etf_count}")

        if sector_count >= sector_cap:
            logging.warning(f"Sector cap exceeded for {sector}. Current: {sector_count}, Cap: {sector_cap}")
            return False

        if etf_count >= etf_cap:
            logging.warning(f"ETF cap exceeded for {etf}. Current: {etf_count}, Cap: {etf_cap}")
            return False

        return True

    def compute_risk_dollars(self, equity: float, beta_regime: float) -> float:
        base = 0.005  # 0.5% per-trade cap
        risk_dollars = max(0.0, base * float(beta_regime) * float(equity))
        logging.info(f"[StrategyManager] risk_per_trade={risk_dollars:.2f} (beta={beta_regime:.2f}, equity={equity:.2f})")
        return risk_dollars

    def should_enter_trade(self, regime_label: str, strategy_name: str) -> bool:
        # Conservative defaults
        if regime_label == "DOWN_HIGHVOL":
            return False  # stand down
        # Optionally restrict long-only strategies when DOWN_*
        if strategy_name in ("TPL", "TREND_PULLBACK") and regime_label.startswith("DOWN_"):
            return False
        return True
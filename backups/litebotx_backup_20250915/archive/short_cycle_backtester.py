#!/usr/bin/env python3
"""
Short-Cycle Backtesting Framework
=================================

Specialized backtesting for 1-2 day trading cycles with forced D+1 exits,
realistic transaction costs, and comprehensive validation.

Key Features:
- Forced D+1 exit simulation
- Transaction cost modeling (commission, spread, slippage)
- Short-cycle specific metrics
- Integration with short_cycle_trader.py
- Paper trading validation framework

Author: LiteBotX Team
Version: 1.0 (Sprint 0)
"""

import os
import sys
import json
import logging
import datetime as dt
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, asdict
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Import short-cycle components
try:
    from short_cycle_trader import (
        ShortCycleConfig, AISignal, ShortCyclePosition, PositionStatus,
        AISignalGenerator, AIStopLossManager, AIConfidencePositionSizer,
        AIPredictiveRiskManager, AIMarketRegimeDetector
    )
except ImportError as e:
    print(f"❌ Failed to import short-cycle components: {e}")
    sys.exit(1)


@dataclass
class BacktestConfig:
    """Configuration for short-cycle backtesting"""
    start_date: str = "2023-01-01"
    end_date: str = "2024-08-01"
    initial_capital: float = 1000.0
    
    # Transaction costs
    commission_per_trade: float = 0.0  # Commission-free assumption
    spread_bp: float = 5.0  # 5 basis points spread
    slippage_bp: float = 2.0  # 2 basis points slippage
    market_impact_threshold: float = 0.01  # 1% of daily volume threshold
    
    # Short-cycle specific
    force_d1_exit: bool = True  # Core feature: force D+1 exits
    weekend_gap_modeling: bool = True  # Model Friday-Monday gaps
    overnight_gap_std: float = 0.008  # 0.8% overnight gap volatility
    
    # Validation parameters
    min_trades_for_validation: int = 50
    max_drawdown_threshold: float = 0.15  # 15% max drawdown
    min_sharpe_threshold: float = 1.0  # Minimum Sharpe ratio
    
    # Paper trading
    enable_paper_trading: bool = False
    paper_trading_duration_weeks: int = 12  # 8-12 weeks as required


@dataclass
class TradeResult:
    """Individual trade result with detailed tracking"""
    symbol: str
    entry_date: dt.date
    exit_date: dt.date
    entry_price: float
    exit_price: float
    position_size_shares: int
    position_value: float
    
    # P&L breakdown
    gross_pnl: float
    commission_cost: float
    spread_cost: float
    slippage_cost: float
    net_pnl: float
    return_pct: float
    
    # Trade characteristics
    hold_days: int
    exit_reason: str
    ai_confidence: float
    ai_features: Dict[str, Any]
    
    # Risk metrics
    max_risk: float
    max_adverse_excursion: float
    max_favorable_excursion: float


@dataclass
class BacktestResults:
    """Comprehensive backtest results"""
    # Performance metrics
    total_return: float
    annual_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    
    # Trade statistics
    total_trades: int
    winning_trades: int
    losing_trades: int
    avg_win: float
    avg_loss: float
    avg_hold_days: float
    
    # Short-cycle specific metrics
    weekly_returns: List[float]
    avg_weekly_return: float
    weekly_sharpe: float
    capital_recycling_efficiency: float
    d1_exit_compliance: float
    
    # Cost analysis
    total_commission: float
    total_spread_cost: float
    total_slippage: float
    cost_as_pct_of_returns: float
    
    # Risk metrics
    var_95: float
    var_99: float
    maximum_consecutive_losses: int
    
    # Detailed results
    trades: List[TradeResult]
    equity_curve: pd.Series
    drawdown_curve: pd.Series
    weekly_performance: pd.DataFrame


class ShortCycleBacktester:
    """Specialized backtester for short-cycle trading strategies"""
    
    def __init__(self, config: BacktestConfig = None, trading_config: ShortCycleConfig = None):
        self.config = config or BacktestConfig()
        self.trading_config = trading_config or ShortCycleConfig()
        self.logger = self._setup_logging()
        
        # Initialize AI components for backtesting
        self.signal_generator = AISignalGenerator(self.trading_config)
        self.stop_manager = AIStopLossManager(self.trading_config)
        self.position_sizer = AIConfidencePositionSizer(self.trading_config)
        self.risk_manager = AIPredictiveRiskManager(self.trading_config)
        self.regime_detector = AIMarketRegimeDetector(self.trading_config)
        
        # State tracking
        self.current_capital = self.config.initial_capital
        self.positions: List[ShortCyclePosition] = []
        self.completed_trades: List[TradeResult] = []
        self.daily_equity = []
        self.trade_id_counter = 0
        
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for backtesting"""
        logger = logging.getLogger("ShortCycleBacktester")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        
        return logger
    
    def run_backtest(self, market_data: Dict[str, pd.DataFrame]) -> BacktestResults:
        """Run comprehensive short-cycle backtest"""
        self.logger.info("🚀 Starting short-cycle backtest")
        self.logger.info(f"📅 Period: {self.config.start_date} to {self.config.end_date}")
        self.logger.info(f"💰 Initial capital: ${self.config.initial_capital:,.0f}")
        
        try:
            # Validate market data
            market_data = self._validate_market_data(market_data)
            
            # Get trading dates
            trading_dates = self._get_trading_dates(market_data)
            
            # Main backtest loop
            for i, current_date in enumerate(trading_dates):
                self._process_trading_day(current_date, market_data, i)
            
            # Generate results
            results = self._generate_results()
            self._save_results(results)
            
            self.logger.info("✅ Backtest completed successfully")
            return results
            
        except Exception as e:
            self.logger.error(f"❌ Backtest failed: {e}")
            raise
    
    def _validate_market_data(self, market_data: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """Validate and prepare market data for backtesting"""
        validated_data = {}
        
        for symbol, data in market_data.items():
            if data.empty:
                continue
            
            # Ensure required columns
            required_cols = ['open', 'high', 'low', 'close', 'volume']
            if not all(col in data.columns for col in required_cols):
                self.logger.warning(f"⚠️ {symbol}: Missing required columns, skipping")
                continue
            
            # Filter date range
            data['date'] = pd.to_datetime(data.index)
            mask = (data['date'] >= self.config.start_date) & (data['date'] <= self.config.end_date)
            filtered_data = data[mask].copy()
            
            if len(filtered_data) < 50:  # Minimum data requirement
                self.logger.warning(f"⚠️ {symbol}: Insufficient data, skipping")
                continue
            
            validated_data[symbol] = filtered_data
        
        self.logger.info(f"📊 Validated data for {len(validated_data)} symbols")
        return validated_data
    
    def _get_trading_dates(self, market_data: Dict[str, pd.DataFrame]) -> List[dt.date]:
        """Get list of trading dates from market data"""
        if not market_data:
            return []
        
        # Use first symbol's dates as reference
        first_symbol_data = next(iter(market_data.values()))
        dates = pd.to_datetime(first_symbol_data.index).date
        
        # Filter to trading days (Monday-Thursday for new positions, Friday for exits only)
        trading_dates = []
        for date in dates:
            weekday = date.weekday()
            if weekday < 5:  # Monday=0 to Friday=4
                trading_dates.append(date)
        
        return sorted(trading_dates)
    
    def _process_trading_day(self, current_date: dt.date, market_data: Dict[str, pd.DataFrame], day_index: int):
        """Process a single trading day"""
        weekday = current_date.weekday()
        
        # Process exits first (including Friday exits)
        self._process_exits(current_date, market_data)
        
        # Only generate new positions Monday-Thursday
        if weekday < 4:  # Monday=0 to Thursday=3
            self._process_entries(current_date, market_data)
        elif weekday == 4:  # Friday
            self.logger.info(f"📅 {current_date}: Friday - exits only, no new positions")
        
        # Update daily equity
        self._update_daily_equity(current_date, market_data)
        
        # Log daily status
        if day_index % 20 == 0:  # Log every 20 days
            self._log_daily_status(current_date)
    
    def _process_exits(self, current_date: dt.date, market_data: Dict[str, pd.DataFrame]):
        """Process position exits with D+1 forced exit logic"""
        exits_processed = 0
        
        for position in self.positions[:]:  # Copy list to allow modification
            if position.status != PositionStatus.ENTERED:
                continue
            
            symbol_data = market_data.get(position.symbol)
            if symbol_data is None:
                continue
            
            # Get current price
            current_price = self._get_price_for_date(symbol_data, current_date, 'close')
            if current_price is None:
                continue
            
            # Check exit conditions
            should_exit, exit_reason = self._should_exit_position(position, current_date, current_price)
            
            if should_exit:
                self._exit_position(position, current_date, current_price, exit_reason, symbol_data)
                exits_processed += 1
        
        if exits_processed > 0:
            self.logger.info(f"🔄 {current_date}: Processed {exits_processed} exits")
    
    def _should_exit_position(self, position: ShortCyclePosition, current_date: dt.date, current_price: float) -> Tuple[bool, str]:
        """Determine if position should be exited and why"""
        # D+1 forced exit (core feature)
        if self.config.force_d1_exit and current_date >= position.exit_date:
            return True, "D+1_FORCED_EXIT"
        
        # Stop loss
        if current_price <= position.stop_price:
            return True, "STOP_LOSS"
        
        # Fast exit for capital recycling
        if self.stop_manager.should_fast_exit(position, current_price):
            return True, "FAST_EXIT"
        
        # Target price (if set)
        if position.target_price and current_price >= position.target_price:
            return True, "TARGET_HIT"
        
        return False, ""
    
    def _process_entries(self, current_date: dt.date, market_data: Dict[str, pd.DataFrame]):
        """Process new position entries"""
        try:
            # Check if we have capacity for new positions
            active_positions = len([p for p in self.positions if p.status == PositionStatus.ENTERED])
            if active_positions >= self.trading_config.max_positions_per_day:
                return
            
            # Get regime information
            regime_info = self.regime_detector.get_current_regime(market_data)
            
            # Generate signals
            universe = list(market_data.keys())
            signals = self.signal_generator.generate_signals(universe, market_data)
            
            if not signals:
                return
            
            # Risk assessment
            risk_assessment = self.risk_manager.assess_portfolio_risk(
                signals, self.positions, market_data
            )
            
            if not risk_assessment["approved"]:
                return
            
            # Execute approved signals
            entries_processed = 0
            for signal in signals:
                if signal.symbol in risk_assessment.get("vetoed_signals", []):
                    continue
                
                if entries_processed >= self.trading_config.max_positions_per_day - active_positions:
                    break
                
                success = self._enter_position(signal, current_date, market_data)
                if success:
                    entries_processed += 1
            
            if entries_processed > 0:
                self.logger.info(f"🎯 {current_date}: Entered {entries_processed} new positions")
                
        except Exception as e:
            self.logger.error(f"Error processing entries for {current_date}: {e}")
    
    def _enter_position(self, signal: AISignal, current_date: dt.date, market_data: Dict[str, pd.DataFrame]) -> bool:
        """Enter a new position"""
        try:
            symbol_data = market_data.get(signal.symbol)
            if symbol_data is None:
                return False
            
            # Get entry price (next day open for realistic simulation)
            entry_price = self._get_entry_price(symbol_data, current_date, signal)
            if entry_price is None:
                return False
            
            # Calculate stop price
            stop_price, _ = self.stop_manager.calculate_optimal_stop(signal, symbol_data)
            
            # Calculate position size
            shares, position_value = self.position_sizer.calculate_position_size(
                signal, stop_price, self.current_capital
            )
            
            if shares == 0 or position_value > self.current_capital * 0.5:  # Safety check
                return False
            
            # Calculate D+1 exit date
            exit_date = self._get_next_trading_day(current_date)
            
            # Create position
            position = ShortCyclePosition(
                symbol=signal.symbol,
                entry_date=current_date,
                exit_date=exit_date,
                entry_price=entry_price,
                position_size_shares=shares,
                position_size_dollars=position_value,
                stop_price=stop_price,
                target_price=signal.target_price,
                status=PositionStatus.ENTERED,
                ai_signal=signal,
                max_risk_dollars=self.trading_config.max_risk_per_trade_dollars
            )
            
            # Add transaction costs
            entry_costs = self._calculate_transaction_costs(position_value, "ENTRY")
            self.current_capital -= position_value + entry_costs
            
            self.positions.append(position)
            self.trade_id_counter += 1
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error entering position for {signal.symbol}: {e}")
            return False
    
    def _exit_position(self, position: ShortCyclePosition, exit_date: dt.date, exit_price: float, 
                      exit_reason: str, symbol_data: pd.DataFrame):
        """Exit a position and record trade result"""
        try:
            # Calculate gross P&L
            gross_pnl = (exit_price - position.entry_price) * position.position_size_shares
            
            # Calculate transaction costs
            exit_costs = self._calculate_transaction_costs(position.position_size_dollars, "EXIT")
            entry_costs = self._calculate_transaction_costs(position.position_size_dollars, "ENTRY")
            total_costs = entry_costs + exit_costs
            
            # Net P&L
            net_pnl = gross_pnl - total_costs
            return_pct = net_pnl / position.position_size_dollars
            
            # Update capital
            position_proceeds = position.position_size_shares * exit_price
            self.current_capital += position_proceeds - exit_costs
            
            # Create trade result
            trade_result = TradeResult(
                symbol=position.symbol,
                entry_date=position.entry_date,
                exit_date=exit_date,
                entry_price=position.entry_price,
                exit_price=exit_price,
                position_size_shares=position.position_size_shares,
                position_value=position.position_size_dollars,
                gross_pnl=gross_pnl,
                commission_cost=0.0,  # Assuming commission-free
                spread_cost=total_costs * 0.7,  # Approximate split
                slippage_cost=total_costs * 0.3,
                net_pnl=net_pnl,
                return_pct=return_pct,
                hold_days=(exit_date - position.entry_date).days,
                exit_reason=exit_reason,
                ai_confidence=position.ai_signal.confidence,
                ai_features=position.ai_signal.features_used,
                max_risk=position.max_risk_dollars,
                max_adverse_excursion=self._calculate_mae(position, symbol_data),
                max_favorable_excursion=self._calculate_mfe(position, symbol_data)
            )
            
            # Update position status
            position.status = PositionStatus.EXITED
            position.exit_price = exit_price
            position.exit_reason = exit_reason
            position.realized_pnl = net_pnl
            
            self.completed_trades.append(trade_result)
            
        except Exception as e:
            self.logger.error(f"Error exiting position {position.symbol}: {e}")
    
    def _calculate_transaction_costs(self, position_value: float, side: str) -> float:
        """Calculate realistic transaction costs"""
        # Spread cost (half spread on each side)
        spread_cost = position_value * (self.config.spread_bp / 10000) * 0.5
        
        # Slippage cost
        slippage_cost = position_value * (self.config.slippage_bp / 10000)
        
        # Commission (typically zero for modern brokers)
        commission = self.config.commission_per_trade
        
        return spread_cost + slippage_cost + commission
    
    def _calculate_mae(self, position: ShortCyclePosition, symbol_data: pd.DataFrame) -> float:
        """Calculate Maximum Adverse Excursion"""
        try:
            # Get price data during position hold
            mask = (symbol_data.index >= pd.Timestamp(position.entry_date)) & \
                   (symbol_data.index <= pd.Timestamp(position.exit_date))
            hold_data = symbol_data[mask]
            
            if hold_data.empty:
                return 0.0
            
            # Find lowest price during hold
            lowest_price = hold_data['low'].min()
            mae = (position.entry_price - lowest_price) * position.position_size_shares
            
            return max(mae, 0.0)
            
        except Exception:
            return 0.0
    
    def _calculate_mfe(self, position: ShortCyclePosition, symbol_data: pd.DataFrame) -> float:
        """Calculate Maximum Favorable Excursion"""
        try:
            # Get price data during position hold
            mask = (symbol_data.index >= pd.Timestamp(position.entry_date)) & \
                   (symbol_data.index <= pd.Timestamp(position.exit_date))
            hold_data = symbol_data[mask]
            
            if hold_data.empty:
                return 0.0
            
            # Find highest price during hold
            highest_price = hold_data['high'].max()
            mfe = (highest_price - position.entry_price) * position.position_size_shares
            
            return max(mfe, 0.0)
            
        except Exception:
            return 0.0
    
    def _get_entry_price(self, symbol_data: pd.DataFrame, signal_date: dt.date, signal: AISignal) -> Optional[float]:
        """Get realistic entry price (next day open)"""
        try:
            # Find next trading day
            next_day = self._get_next_trading_day(signal_date)
            entry_price = self._get_price_for_date(symbol_data, next_day, 'open')
            
            # Apply overnight gap modeling if enabled
            if self.config.weekend_gap_modeling and signal_date.weekday() == 4:  # Friday signal
                gap_factor = np.random.normal(1.0, self.config.overnight_gap_std)
                entry_price *= gap_factor
            
            return entry_price
            
        except Exception:
            return None
    
    def _get_price_for_date(self, symbol_data: pd.DataFrame, date: dt.date, price_type: str) -> Optional[float]:
        """Get price for specific date and type"""
        try:
            date_str = date.strftime('%Y-%m-%d')
            matching_rows = symbol_data[symbol_data.index.strftime('%Y-%m-%d') == date_str]
            
            if matching_rows.empty:
                return None
            
            return float(matching_rows[price_type].iloc[0])
            
        except Exception:
            return None
    
    def _get_next_trading_day(self, current_date: dt.date) -> dt.date:
        """Get next trading day (handles weekends)"""
        next_day = current_date + dt.timedelta(days=1)
        
        # Skip weekends
        if next_day.weekday() == 5:  # Saturday
            next_day += dt.timedelta(days=2)
        elif next_day.weekday() == 6:  # Sunday
            next_day += dt.timedelta(days=1)
        
        return next_day
    
    def _update_daily_equity(self, current_date: dt.date, market_data: Dict[str, pd.DataFrame]):
        """Update daily equity curve"""
        # Calculate current position values
        position_value = 0.0
        for position in self.positions:
            if position.status != PositionStatus.ENTERED:
                continue
            
            symbol_data = market_data.get(position.symbol)
            if symbol_data is None:
                continue
            
            current_price = self._get_price_for_date(symbol_data, current_date, 'close')
            if current_price:
                position_value += position.position_size_shares * current_price
        
        total_equity = self.current_capital + position_value
        self.daily_equity.append({
            'date': current_date,
            'equity': total_equity,
            'cash': self.current_capital,
            'positions_value': position_value
        })
    
    def _log_daily_status(self, current_date: dt.date):
        """Log daily status for monitoring"""
        active_positions = len([p for p in self.positions if p.status == PositionStatus.ENTERED])
        current_equity = self.daily_equity[-1]['equity'] if self.daily_equity else self.config.initial_capital
        
        self.logger.info(f"📊 {current_date}: Equity ${current_equity:,.0f}, "
                        f"Active positions: {active_positions}, "
                        f"Completed trades: {len(self.completed_trades)}")
    
    def _generate_results(self) -> BacktestResults:
        """Generate comprehensive backtest results"""
        if not self.completed_trades:
            self.logger.warning("⚠️ No completed trades found")
            return self._empty_results()
        
        # Basic performance metrics
        total_return = (self.daily_equity[-1]['equity'] / self.config.initial_capital - 1) if self.daily_equity else 0
        
        # Trade statistics
        winning_trades = [t for t in self.completed_trades if t.net_pnl > 0]
        losing_trades = [t for t in self.completed_trades if t.net_pnl <= 0]
        
        win_rate = len(winning_trades) / len(self.completed_trades) if self.completed_trades else 0
        avg_win = np.mean([t.net_pnl for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t.net_pnl for t in losing_trades]) if losing_trades else 0
        profit_factor = abs(sum(t.net_pnl for t in winning_trades) / sum(t.net_pnl for t in losing_trades)) if losing_trades else float('inf')
        
        # Create equity curve
        equity_df = pd.DataFrame(self.daily_equity)
        if not equity_df.empty:
            equity_df.set_index('date', inplace=True)
            equity_curve = equity_df['equity']
            
            # Calculate drawdown
            peak = equity_curve.expanding().max()
            drawdown = (equity_curve - peak) / peak
            max_drawdown = abs(drawdown.min())
            
            # Calculate Sharpe ratio (assuming daily data)
            returns = equity_curve.pct_change().dropna()
            sharpe_ratio = returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0
        else:
            equity_curve = pd.Series()
            drawdown = pd.Series()
            max_drawdown = 0
            sharpe_ratio = 0
        
        # Weekly performance analysis
        weekly_returns = self._calculate_weekly_returns(equity_df) if not equity_df.empty else []
        avg_weekly_return = np.mean(weekly_returns) if weekly_returns else 0
        weekly_sharpe = (np.mean(weekly_returns) / np.std(weekly_returns) * np.sqrt(52)) if len(weekly_returns) > 1 and np.std(weekly_returns) > 0 else 0
        
        # Short-cycle specific metrics
        avg_hold_days = np.mean([t.hold_days for t in self.completed_trades]) if self.completed_trades else 0
        d1_exits = len([t for t in self.completed_trades if t.exit_reason == "D+1_FORCED_EXIT"])
        d1_exit_compliance = d1_exits / len(self.completed_trades) if self.completed_trades else 0
        
        # Calculate capital recycling efficiency (trades per week)
        trading_weeks = len(weekly_returns) if weekly_returns else 1
        capital_recycling_efficiency = len(self.completed_trades) / trading_weeks
        
        # Cost analysis
        total_costs = sum(t.commission_cost + t.spread_cost + t.slippage_cost for t in self.completed_trades)
        total_gross_pnl = sum(t.gross_pnl for t in self.completed_trades)
        cost_ratio = abs(total_costs / total_gross_pnl) if total_gross_pnl != 0 else 0
        
        # Risk metrics
        returns_list = [t.return_pct for t in self.completed_trades] if self.completed_trades else [0]
        var_95 = np.percentile(returns_list, 5) if returns_list else 0
        var_99 = np.percentile(returns_list, 1) if returns_list else 0
        
        # Calculate annual return
        if equity_df.empty:
            annual_return = 0
        else:
            days = (equity_df.index[-1] - equity_df.index[0]).days
            annual_return = (1 + total_return) ** (365 / days) - 1 if days > 0 else 0
        
        return BacktestResults(
            total_return=total_return,
            annual_return=annual_return,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            win_rate=win_rate,
            profit_factor=profit_factor,
            total_trades=len(self.completed_trades),
            winning_trades=len(winning_trades),
            losing_trades=len(losing_trades),
            avg_win=avg_win,
            avg_loss=avg_loss,
            avg_hold_days=avg_hold_days,
            weekly_returns=weekly_returns,
            avg_weekly_return=avg_weekly_return,
            weekly_sharpe=weekly_sharpe,
            capital_recycling_efficiency=capital_recycling_efficiency,
            d1_exit_compliance=d1_exit_compliance,
            total_commission=sum(t.commission_cost for t in self.completed_trades),
            total_spread_cost=sum(t.spread_cost for t in self.completed_trades),
            total_slippage=sum(t.slippage_cost for t in self.completed_trades),
            cost_as_pct_of_returns=cost_ratio,
            var_95=var_95,
            var_99=var_99,
            maximum_consecutive_losses=self._calculate_max_consecutive_losses(),
            trades=self.completed_trades,
            equity_curve=equity_curve,
            drawdown_curve=drawdown * -1 if not drawdown.empty else pd.Series(),
            weekly_performance=pd.DataFrame({'weekly_return': weekly_returns}) if weekly_returns else pd.DataFrame()
        )
    
    def _empty_results(self) -> BacktestResults:
        """Return empty results structure"""
        return BacktestResults(
            total_return=0, annual_return=0, sharpe_ratio=0, max_drawdown=0,
            win_rate=0, profit_factor=0, total_trades=0, winning_trades=0,
            losing_trades=0, avg_win=0, avg_loss=0, avg_hold_days=0,
            weekly_returns=[], avg_weekly_return=0, weekly_sharpe=0,
            capital_recycling_efficiency=0, d1_exit_compliance=0,
            total_commission=0, total_spread_cost=0, total_slippage=0,
            cost_as_pct_of_returns=0, var_95=0, var_99=0,
            maximum_consecutive_losses=0, trades=[], equity_curve=pd.Series(),
            drawdown_curve=pd.Series(), weekly_performance=pd.DataFrame()
        )
    
    def _calculate_weekly_returns(self, equity_df: pd.DataFrame) -> List[float]:
        """Calculate weekly returns from daily equity"""
        if equity_df.empty:
            return []
        
        # Resample to weekly
        weekly_equity = equity_df['equity'].resample('W').last()
        weekly_returns = weekly_equity.pct_change().dropna().tolist()
        
        return weekly_returns
    
    def _calculate_max_consecutive_losses(self) -> int:
        """Calculate maximum consecutive losing trades"""
        if not self.completed_trades:
            return 0
        
        max_consecutive = 0
        current_consecutive = 0
        
        for trade in self.completed_trades:
            if trade.net_pnl <= 0:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0
        
        return max_consecutive
    
    def _save_results(self, results: BacktestResults):
        """Save backtest results to files"""
        try:
            # Create results directory
            results_dir = Path("backtest_results")
            results_dir.mkdir(exist_ok=True)
            
            timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Save summary
            summary = {
                "backtest_config": asdict(self.config),
                "trading_config": asdict(self.trading_config),
                "performance_summary": {
                    "total_return": f"{results.total_return:.1%}",
                    "annual_return": f"{results.annual_return:.1%}",
                    "sharpe_ratio": f"{results.sharpe_ratio:.2f}",
                    "max_drawdown": f"{results.max_drawdown:.1%}",
                    "win_rate": f"{results.win_rate:.1%}",
                    "profit_factor": f"{results.profit_factor:.2f}",
                    "total_trades": results.total_trades,
                    "avg_weekly_return": f"{results.avg_weekly_return:.2%}",
                    "weekly_sharpe": f"{results.weekly_sharpe:.2f}",
                    "d1_exit_compliance": f"{results.d1_exit_compliance:.1%}",
                    "capital_recycling_efficiency": f"{results.capital_recycling_efficiency:.1f} trades/week"
                }
            }
            
            with open(results_dir / f"backtest_summary_{timestamp}.json", "w") as f:
                json.dump(summary, f, indent=2)
            
            # Save detailed trades
            if results.trades:
                trades_df = pd.DataFrame([asdict(trade) for trade in results.trades])
                trades_df.to_csv(results_dir / f"backtest_trades_{timestamp}.csv", index=False)
            
            # Save equity curve
            if not results.equity_curve.empty:
                results.equity_curve.to_csv(results_dir / f"equity_curve_{timestamp}.csv")
            
            self.logger.info(f"📁 Results saved to {results_dir}/backtest_*_{timestamp}.*")
            
        except Exception as e:
            self.logger.error(f"Failed to save results: {e}")
    
    def print_results_summary(self, results: BacktestResults):
        """Print formatted results summary"""
        print("\n" + "="*60)
        print("📊 SHORT-CYCLE BACKTEST RESULTS")
        print("="*60)
        
        print(f"\n🎯 PERFORMANCE METRICS:")
        print(f"  Total Return:        {results.total_return:.1%}")
        print(f"  Annual Return:       {results.annual_return:.1%}")
        print(f"  Sharpe Ratio:        {results.sharpe_ratio:.2f}")
        print(f"  Max Drawdown:        {results.max_drawdown:.1%}")
        
        print(f"\n📈 TRADING STATISTICS:")
        print(f"  Total Trades:        {results.total_trades}")
        print(f"  Win Rate:            {results.win_rate:.1%}")
        print(f"  Profit Factor:       {results.profit_factor:.2f}")
        print(f"  Avg Hold Days:       {results.avg_hold_days:.1f}")
        print(f"  Avg Win:             ${results.avg_win:.2f}")
        print(f"  Avg Loss:            ${results.avg_loss:.2f}")
        
        print(f"\n🔄 SHORT-CYCLE METRICS:")
        print(f"  Avg Weekly Return:   {results.avg_weekly_return:.2%}")
        print(f"  Weekly Sharpe:       {results.weekly_sharpe:.2f}")
        print(f"  Capital Recycling:   {results.capital_recycling_efficiency:.1f} trades/week")
        print(f"  D+1 Exit Compliance: {results.d1_exit_compliance:.1%}")
        
        print(f"\n💰 COST ANALYSIS:")
        print(f"  Total Spread Cost:   ${results.total_spread_cost:.2f}")
        print(f"  Total Slippage:      ${results.total_slippage:.2f}")
        print(f"  Cost vs Returns:     {results.cost_as_pct_of_returns:.1%}")
        
        print(f"\n⚠️  RISK METRICS:")
        print(f"  VaR 95%:             {results.var_95:.1%}")
        print(f"  VaR 99%:             {results.var_99:.1%}")
        print(f"  Max Consecutive Losses: {results.maximum_consecutive_losses}")
        
        # Validation status
        print(f"\n✅ VALIDATION STATUS:")
        validation_passed = self._validate_results(results)
        print(f"  Overall Validation:  {'✅ PASSED' if validation_passed else '❌ FAILED'}")
        
        print("="*60)
    
    def _validate_results(self, results: BacktestResults) -> bool:
        """Validate backtest results against criteria"""
        validations = []
        
        # Minimum trades
        min_trades_ok = results.total_trades >= self.config.min_trades_for_validation
        validations.append(min_trades_ok)
        print(f"  Min Trades ({self.config.min_trades_for_validation}):    {'✅' if min_trades_ok else '❌'} ({results.total_trades})")
        
        # Max drawdown
        max_dd_ok = results.max_drawdown <= self.config.max_drawdown_threshold
        validations.append(max_dd_ok)
        print(f"  Max Drawdown (<{self.config.max_drawdown_threshold:.0%}): {'✅' if max_dd_ok else '❌'} ({results.max_drawdown:.1%})")
        
        # Sharpe ratio
        sharpe_ok = results.sharpe_ratio >= self.config.min_sharpe_threshold
        validations.append(sharpe_ok)
        print(f"  Sharpe Ratio (>{self.config.min_sharpe_threshold:.1f}):   {'✅' if sharpe_ok else '❌'} ({results.sharpe_ratio:.2f})")
        
        # D+1 exit compliance
        d1_compliance_ok = results.d1_exit_compliance >= 0.8  # 80% compliance
        validations.append(d1_compliance_ok)
        print(f"  D+1 Compliance (>80%): {'✅' if d1_compliance_ok else '❌'} ({results.d1_exit_compliance:.1%})")
        
        return all(validations)


# Testing and validation functions
def create_sample_data() -> Dict[str, pd.DataFrame]:
    """Create sample market data for testing"""
    symbols = ["AAPL", "MSFT", "GOOGL", "SPY"]
    market_data = {}
    
    # Generate 2 years of sample data
    dates = pd.date_range("2023-01-01", "2024-08-01", freq="D")
    trading_dates = [d for d in dates if d.weekday() < 5]  # Remove weekends
    
    for symbol in symbols:
        np.random.seed(42 + hash(symbol) % 100)  # Reproducible but different for each symbol
        
        # Generate price series with some momentum and volatility
        price = 100.0
        prices = []
        volumes = []
        
        for i, date in enumerate(trading_dates):
            # Add some momentum and mean reversion
            momentum = np.random.normal(0.0002, 0.02)  # Small daily drift with volatility
            if i > 5:
                # Add momentum component
                recent_trend = np.mean([prices[j] / prices[j-1] - 1 for j in range(max(0, i-5), i)])
                momentum += recent_trend * 0.3
            
            price *= (1 + momentum)
            
            # Create OHLC data
            daily_range = price * 0.02  # 2% daily range
            high = price + np.random.uniform(0, daily_range)
            low = price - np.random.uniform(0, daily_range)
            open_price = price + np.random.uniform(-daily_range/2, daily_range/2)
            close_price = price
            
            prices.append(close_price)
            volumes.append(np.random.uniform(1_000_000, 5_000_000))
        
        # Create DataFrame
        df = pd.DataFrame({
            'open': [100 * (p/100 + np.random.normal(0, 0.005)) for p in prices],
            'high': [100 * (p/100 + abs(np.random.normal(0, 0.01))) for p in prices],
            'low': [100 * (p/100 - abs(np.random.normal(0, 0.01))) for p in prices],
            'close': prices,
            'volume': volumes
        }, index=trading_dates)
        
        market_data[symbol] = df
    
    return market_data


def test_short_cycle_backtester():
    """Test the short-cycle backtesting framework"""
    print("🧪 Testing Short-Cycle Backtesting Framework")
    
    try:
        # Create test configuration
        backtest_config = BacktestConfig(
            start_date="2023-01-01",
            end_date="2024-01-01",
            initial_capital=1000.0,
            force_d1_exit=True
        )
        
        trading_config = ShortCycleConfig(
            portfolio_value=1000.0,
            max_positions_per_day=2
        )
        
        # Create sample data
        print("📊 Generating sample market data...")
        market_data = create_sample_data()
        
        # Run backtest
        print("🚀 Running backtest...")
        backtester = ShortCycleBacktester(backtest_config, trading_config)
        results = backtester.run_backtest(market_data)
        
        # Print results
        backtester.print_results_summary(results)
        
        print("✅ Short-cycle backtesting framework test complete")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("🚀 LiteBotX Short-Cycle Backtesting Framework")
    print("=" * 60)
    
    # Run test
    if test_short_cycle_backtester():
        print("\n🎯 Backtesting framework ready for Sprint 1 integration")
    else:
        print("\n❌ Fix issues before proceeding")

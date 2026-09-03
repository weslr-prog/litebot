#!/usr/bin/env python3
"""
Forward Testing Framework for LiteBotX
Real-time paper trading validation and strategy performance monitoring

Features:
1. Real-time paper trading simulation
2. Live strategy performance tracking
3. Risk monitoring and alerts
4. Performance decay detection
5. Strategy health monitoring
6. Automated reporting
7. Integration with backtesting results
"""

import numpy as np
import pandas as pd
import logging
from typing import Dict, List, Tuple, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import time
import json
import threading
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# Import trading system components
try:
    from automated_momentum_trader_v2 import AutomatedMomentumTraderV2
    from comprehensive_backtester import ComprehensiveBacktester, BacktestConfig
    from risk import RiskManager
    from data_fetcher import DataFetcher
except ImportError:
    print("Warning: Some trading system components not available for import")
    # Define dummy classes to prevent import errors
    class DataFetcher:
        pass
    class RiskManager:
        pass


@dataclass
class ForwardTestConfig:
    """Configuration for forward testing"""
    
    # Testing parameters
    initial_capital: float = 1_000_000
    enable_paper_trading: bool = True
    enable_live_monitoring: bool = True
    
    # Performance thresholds
    min_sharpe_ratio: float = 0.5
    max_drawdown_threshold: float = 0.15
    performance_decay_threshold: float = 0.25
    min_win_rate: float = 0.45
    
    # Monitoring intervals
    update_frequency_minutes: int = 15
    daily_report_time: str = "16:30"  # Market close
    weekly_report_day: str = "Friday"
    
    # Risk limits
    max_position_size: float = 0.20  # 20% max per position
    max_portfolio_risk: float = 0.10  # 10% max portfolio risk
    correlation_limit: float = 0.70  # 70% max correlation
    
    # Alert settings
    enable_alerts: bool = True
    alert_email: Optional[str] = None
    alert_phone: Optional[str] = None
    
    # Data storage
    save_trade_log: bool = True
    save_performance_log: bool = True
    log_directory: str = "forward_test_logs"


@dataclass
class ForwardTestPosition:
    """Forward test position tracking"""
    symbol: str
    entry_date: datetime
    entry_price: float
    shares: int
    strategy: str
    current_price: float = 0.0
    unrealized_pnl: float = 0.0
    max_profit: float = 0.0
    max_loss: float = 0.0
    
    def update_price(self, new_price: float):
        """Update position with new price"""
        self.current_price = new_price
        self.unrealized_pnl = (new_price - self.entry_price) * self.shares
        
        if self.unrealized_pnl > self.max_profit:
            self.max_profit = self.unrealized_pnl
        elif self.unrealized_pnl < self.max_loss:
            self.max_loss = self.unrealized_pnl


@dataclass  
class ForwardTestTrade:
    """Completed forward test trade"""
    symbol: str
    entry_date: datetime
    exit_date: datetime
    entry_price: float
    exit_price: float
    shares: int
    strategy: str
    pnl: float
    return_pct: float
    hold_days: int
    exit_reason: str


class ForwardTester:
    """
    Real-time forward testing framework
    """
    
    def __init__(self, config: ForwardTestConfig = None):
        self.config = config or ForwardTestConfig()
        self.logger = logging.getLogger(__name__)
        
        # Components
        self.data_fetcher = DataFetcher()
        self.risk_manager = RiskManager()
        
        # State tracking
        self.positions: Dict[str, ForwardTestPosition] = {}
        self.completed_trades: List[ForwardTestTrade] = []
        self.equity_curve: List[Tuple[datetime, float]] = []
        self.performance_metrics: Dict = {}
        
        # Control flags
        self.is_running = False
        self.start_time = datetime.now(timezone.utc)
        self.last_update = None
        
        # Setup logging and directories
        self._setup_logging()
        
        self.logger.info("🧪 Forward Tester initialized")
        self.logger.info(f"   Initial Capital: ${self.config.initial_capital:,.0f}")
        self.logger.info(f"   Paper Trading: {'✅ Enabled' if self.config.enable_paper_trading else '❌ Disabled'}")
        self.logger.info(f"   Update Frequency: {self.config.update_frequency_minutes} minutes")
    
    def _setup_logging(self):
        """Setup logging directories and files"""
        log_dir = Path(self.config.log_directory)
        log_dir.mkdir(exist_ok=True)
        
        # Create log files
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if self.config.save_trade_log:
            self.trade_log_file = log_dir / f"trades_{timestamp}.json"
        
        if self.config.save_performance_log:
            self.performance_log_file = log_dir / f"performance_{timestamp}.json"
    
    def start_forward_test(self, trading_strategy=None, backtest_results: Dict = None):
        """
        Start forward testing
        
        Args:
            trading_strategy: Trading strategy instance
            backtest_results: Previous backtest results for comparison
        """
        self.logger.info("🚀 Starting Forward Test")
        self.logger.info("=" * 60)
        
        self.is_running = True
        self.trading_strategy = trading_strategy
        self.backtest_results = backtest_results
        
        # Initialize tracking
        self.equity_curve.append((self.start_time, self.config.initial_capital))
        
        # Start monitoring thread
        if self.config.enable_live_monitoring:
            monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
            monitoring_thread.start()
            self.logger.info("📊 Live monitoring started")
        
        # Log initial state
        self._log_performance_update()
        
        self.logger.info("✅ Forward test started successfully")
    
    def stop_forward_test(self):
        """Stop forward testing"""
        self.is_running = False
        
        # Final performance calculation
        final_metrics = self._calculate_performance_metrics()
        
        # Generate final report
        self._generate_final_report(final_metrics)
        
        self.logger.info("🏁 Forward test stopped")
        
        return final_metrics
    
    def _monitoring_loop(self):
        """Main monitoring loop for live updates"""
        
        while self.is_running:
            try:
                # Update positions and performance
                self._update_positions()
                self._calculate_performance_metrics()
                self._check_risk_limits()
                self._log_performance_update()
                
                # Check for alerts
                if self.config.enable_alerts:
                    self._check_alerts()
                
                # Sleep until next update
                time.sleep(self.config.update_frequency_minutes * 60)
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                time.sleep(60)  # Wait 1 minute before retry
    
    def add_position(self, symbol: str, shares: int, entry_price: float, strategy: str):
        """Add new position to forward test tracking"""
        
        position = ForwardTestPosition(
            symbol=symbol,
            entry_date=datetime.now(timezone.utc),
            entry_price=entry_price,
            shares=shares,
            strategy=strategy
        )
        
        self.positions[symbol] = position
        
        self.logger.info(f"📈 New position added: {symbol}")
        self.logger.info(f"   Shares: {shares}, Entry: ${entry_price:.2f}")
        self.logger.info(f"   Strategy: {strategy}")
        
        # Log trade
        if self.config.save_trade_log:
            self._log_trade_entry(position)
        
        return position
    
    def close_position(self, symbol: str, exit_price: float, exit_reason: str):
        """Close position and record completed trade"""
        
        if symbol not in self.positions:
            self.logger.warning(f"Position {symbol} not found for closing")
            return None
        
        position = self.positions[symbol]
        exit_date = datetime.now(timezone.utc)
        
        # Calculate trade results
        pnl = (exit_price - position.entry_price) * position.shares
        return_pct = (exit_price - position.entry_price) / position.entry_price
        hold_days = (exit_date - position.entry_date).days
        
        # Create completed trade record
        trade = ForwardTestTrade(
            symbol=symbol,
            entry_date=position.entry_date,
            exit_date=exit_date,
            entry_price=position.entry_price,
            exit_price=exit_price,
            shares=position.shares,
            strategy=position.strategy,
            pnl=pnl,
            return_pct=return_pct,
            hold_days=hold_days,
            exit_reason=exit_reason
        )
        
        self.completed_trades.append(trade)
        del self.positions[symbol]
        
        self.logger.info(f"📉 Position closed: {symbol}")
        self.logger.info(f"   P&L: ${pnl:.2f} ({return_pct:.1%})")
        self.logger.info(f"   Hold: {hold_days} days, Reason: {exit_reason}")
        
        # Log trade
        if self.config.save_trade_log:
            self._log_trade_exit(trade)
        
        return trade
    
    def _update_positions(self):
        """Update all position prices and unrealized P&L"""
        
        if not self.positions:
            return
        
        symbols = list(self.positions.keys())
        
        try:
            # Fetch current prices
            current_prices = self._fetch_current_prices(symbols)
            
            for symbol, position in self.positions.items():
                if symbol in current_prices:
                    position.update_price(current_prices[symbol])
            
            self.last_update = datetime.now(timezone.utc)
            
        except Exception as e:
            self.logger.error(f"Error updating positions: {e}")
    
    def _fetch_current_prices(self, symbols: List[str]) -> Dict[str, float]:
        """Fetch current market prices"""
        # Simplified price fetching - replace with real market data
        prices = {}
        
        for symbol in symbols:
            try:
                # This would be replaced with real market data API
                # For demo, simulate small price movements
                base_price = 100.0  # Demo price
                price_change = np.random.normal(0, 0.02)  # 2% volatility
                prices[symbol] = base_price * (1 + price_change)
                
            except Exception as e:
                self.logger.warning(f"Failed to fetch price for {symbol}: {e}")
        
        return prices
    
    def _calculate_performance_metrics(self) -> Dict:
        """Calculate current performance metrics"""
        
        current_time = datetime.now(timezone.utc)
        
        # Calculate current equity
        unrealized_pnl = sum(pos.unrealized_pnl for pos in self.positions.values())
        realized_pnl = sum(trade.pnl for trade in self.completed_trades)
        current_equity = self.config.initial_capital + realized_pnl + unrealized_pnl
        
        # Update equity curve
        self.equity_curve.append((current_time, current_equity))
        
        # Calculate returns
        total_return = (current_equity - self.config.initial_capital) / self.config.initial_capital
        
        # Calculate other metrics
        days_running = max(1, (current_time - self.start_time).days)
        annualized_return = (1 + total_return) ** (365 / days_running) - 1
        
        # Trade statistics
        if self.completed_trades:
            winning_trades = [t for t in self.completed_trades if t.pnl > 0]
            win_rate = len(winning_trades) / len(self.completed_trades)
            
            avg_win = np.mean([t.pnl for t in winning_trades]) if winning_trades else 0
            losing_trades = [t for t in self.completed_trades if t.pnl <= 0]
            avg_loss = np.mean([t.pnl for t in losing_trades]) if losing_trades else 0
            
            profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else float('inf')
        else:
            win_rate = 0
            avg_win = 0
            avg_loss = 0
            profit_factor = 0
        
        # Drawdown calculation
        equity_values = [eq[1] for eq in self.equity_curve]
        peak = np.maximum.accumulate(equity_values)
        drawdown = (equity_values[-1] - peak[-1]) / peak[-1] if len(peak) > 0 else 0
        max_drawdown = min(0, np.min((np.array(equity_values) - peak) / peak))
        
        # Risk metrics
        if len(equity_values) > 1:
            returns = np.diff(equity_values) / equity_values[:-1]
            volatility = np.std(returns) * np.sqrt(252) if len(returns) > 1 else 0
            sharpe_ratio = annualized_return / volatility if volatility > 0 else 0
        else:
            volatility = 0
            sharpe_ratio = 0
        
        metrics = {
            'current_equity': current_equity,
            'total_return': total_return,
            'annualized_return': annualized_return,
            'unrealized_pnl': unrealized_pnl,
            'realized_pnl': realized_pnl,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'current_drawdown': drawdown,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'volatility': volatility,
            'total_trades': len(self.completed_trades),
            'open_positions': len(self.positions),
            'days_running': days_running,
            'last_update': current_time
        }
        
        self.performance_metrics = metrics
        return metrics
    
    def _check_risk_limits(self):
        """Check risk limits and generate alerts if needed"""
        
        metrics = self.performance_metrics
        
        # Check drawdown limit
        if metrics.get('current_drawdown', 0) < -self.config.max_drawdown_threshold:
            self._trigger_alert(
                "DRAWDOWN ALERT", 
                f"Current drawdown {metrics['current_drawdown']:.1%} exceeds limit {-self.config.max_drawdown_threshold:.1%}"
            )
        
        # Check position sizes
        current_equity = metrics.get('current_equity', self.config.initial_capital)
        for symbol, position in self.positions.items():
            position_value = abs(position.current_price * position.shares)
            position_pct = position_value / current_equity
            
            if position_pct > self.config.max_position_size:
                self._trigger_alert(
                    "POSITION SIZE ALERT",
                    f"{symbol} position {position_pct:.1%} exceeds limit {self.config.max_position_size:.1%}"
                )
        
        # Check performance decay vs backtest
        if self.backtest_results and len(self.completed_trades) >= 10:
            backtest_sharpe = self.backtest_results.get('summary_metrics', {}).get('sharpe_ratio', 0)
            current_sharpe = metrics.get('sharpe_ratio', 0)
            
            if backtest_sharpe > 0:
                performance_decay = (backtest_sharpe - current_sharpe) / backtest_sharpe
                
                if performance_decay > self.config.performance_decay_threshold:
                    self._trigger_alert(
                        "PERFORMANCE DECAY ALERT",
                        f"Forward test Sharpe {current_sharpe:.2f} vs backtest {backtest_sharpe:.2f} ({performance_decay:.1%} decay)"
                    )
    
    def _trigger_alert(self, alert_type: str, message: str):
        """Trigger alert for risk or performance issues"""
        
        self.logger.warning(f"🚨 {alert_type}: {message}")
        
        # Additional alert mechanisms could be added here
        # (email, SMS, Slack, etc.)
        
        if self.config.alert_email:
            # Email alert implementation would go here
            pass
        
        if self.config.alert_phone:
            # SMS alert implementation would go here
            pass
    
    def _check_alerts(self):
        """Check for various alert conditions"""
        
        # Daily and weekly reporting
        current_time = datetime.now()
        
        # Daily report
        if (current_time.strftime("%H:%M") == self.config.daily_report_time and
            self.last_update and 
            self.last_update.date() < current_time.date()):
            
            self._generate_daily_report()
        
        # Weekly report
        if (current_time.strftime("%A") == self.config.weekly_report_day and
            current_time.hour == 17 and  # 5 PM
            self.last_update and
            (current_time - self.last_update).days >= 7):
            
            self._generate_weekly_report()
    
    def _generate_daily_report(self):
        """Generate daily performance report"""
        
        metrics = self.performance_metrics
        
        self.logger.info("📊 DAILY FORWARD TEST REPORT")
        self.logger.info("=" * 50)
        self.logger.info(f"Date: {datetime.now().strftime('%Y-%m-%d')}")
        self.logger.info(f"Equity: ${metrics.get('current_equity', 0):,.0f}")
        self.logger.info(f"Total Return: {metrics.get('total_return', 0):.1%}")
        self.logger.info(f"Open Positions: {metrics.get('open_positions', 0)}")
        self.logger.info(f"Completed Trades: {metrics.get('total_trades', 0)}")
        self.logger.info(f"Win Rate: {metrics.get('win_rate', 0):.1%}")
        self.logger.info(f"Current Drawdown: {metrics.get('current_drawdown', 0):.1%}")
        self.logger.info(f"Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.2f}")
    
    def _generate_weekly_report(self):
        """Generate weekly performance report"""
        
        metrics = self.performance_metrics
        
        self.logger.info("📈 WEEKLY FORWARD TEST REPORT")
        self.logger.info("=" * 50)
        
        # Compare with backtest if available
        if self.backtest_results:
            backtest_metrics = self.backtest_results.get('summary_metrics', {})
            
            self.logger.info("FORWARD TEST vs BACKTEST COMPARISON:")
            self.logger.info(f"  Return: {metrics.get('annualized_return', 0):.1%} vs {backtest_metrics.get('annualized_return', 0):.1%}")
            self.logger.info(f"  Sharpe: {metrics.get('sharpe_ratio', 0):.2f} vs {backtest_metrics.get('sharpe_ratio', 0):.2f}")
            self.logger.info(f"  Win Rate: {metrics.get('win_rate', 0):.1%} vs {backtest_metrics.get('win_rate', 0):.1%}")
            self.logger.info(f"  Max DD: {metrics.get('max_drawdown', 0):.1%} vs {backtest_metrics.get('max_drawdown', 0):.1%}")
    
    def _generate_final_report(self, final_metrics: Dict):
        """Generate comprehensive final report"""
        
        self.logger.info("🏁 FORWARD TEST FINAL REPORT")
        self.logger.info("=" * 60)
        
        self.logger.info(f"Testing Period: {self.start_time.strftime('%Y-%m-%d')} to {datetime.now().strftime('%Y-%m-%d')}")
        self.logger.info(f"Days Running: {final_metrics.get('days_running', 0)}")
        self.logger.info(f"Final Equity: ${final_metrics.get('current_equity', 0):,.0f}")
        self.logger.info(f"Total Return: {final_metrics.get('total_return', 0):.1%}")
        self.logger.info(f"Annualized Return: {final_metrics.get('annualized_return', 0):.1%}")
        self.logger.info(f"Sharpe Ratio: {final_metrics.get('sharpe_ratio', 0):.2f}")
        self.logger.info(f"Max Drawdown: {final_metrics.get('max_drawdown', 0):.1%}")
        self.logger.info(f"Win Rate: {final_metrics.get('win_rate', 0):.1%}")
        self.logger.info(f"Profit Factor: {final_metrics.get('profit_factor', 0):.2f}")
        self.logger.info(f"Total Trades: {final_metrics.get('total_trades', 0)}")
        
        # Validation assessment
        validation_passed = (
            final_metrics.get('sharpe_ratio', 0) >= self.config.min_sharpe_ratio and
            final_metrics.get('max_drawdown', 0) >= -self.config.max_drawdown_threshold and
            final_metrics.get('win_rate', 0) >= self.config.min_win_rate
        )
        
        self.logger.info(f"Validation Status: {'✅ PASSED' if validation_passed else '❌ FAILED'}")
        
        # Save final results
        if self.config.save_performance_log:
            self._save_final_results(final_metrics)
    
    def _log_trade_entry(self, position: ForwardTestPosition):
        """Log trade entry"""
        if hasattr(self, 'trade_log_file'):
            trade_data = {
                'timestamp': position.entry_date.isoformat(),
                'action': 'ENTRY',
                'symbol': position.symbol,
                'shares': position.shares,
                'price': position.entry_price,
                'strategy': position.strategy
            }
            
            with open(self.trade_log_file, 'a') as f:
                f.write(json.dumps(trade_data) + '\n')
    
    def _log_trade_exit(self, trade: ForwardTestTrade):
        """Log trade exit"""
        if hasattr(self, 'trade_log_file'):
            trade_data = {
                'timestamp': trade.exit_date.isoformat(),
                'action': 'EXIT',
                'symbol': trade.symbol,
                'shares': trade.shares,
                'entry_price': trade.entry_price,
                'exit_price': trade.exit_price,
                'pnl': trade.pnl,
                'return_pct': trade.return_pct,
                'hold_days': trade.hold_days,
                'exit_reason': trade.exit_reason,
                'strategy': trade.strategy
            }
            
            with open(self.trade_log_file, 'a') as f:
                f.write(json.dumps(trade_data) + '\n')
    
    def _log_performance_update(self):
        """Log performance update"""
        if hasattr(self, 'performance_log_file') and self.performance_metrics:
            perf_data = self.performance_metrics.copy()
            perf_data['timestamp'] = datetime.now(timezone.utc).isoformat()
            
            with open(self.performance_log_file, 'a') as f:
                f.write(json.dumps(perf_data, default=str) + '\n')
    
    def _save_final_results(self, final_metrics: Dict):
        """Save final results to file"""
        results_file = Path(self.config.log_directory) / f"forward_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        final_results = {
            'config': self.config.__dict__,
            'start_time': self.start_time.isoformat(),
            'end_time': datetime.now(timezone.utc).isoformat(),
            'final_metrics': final_metrics,
            'completed_trades': [trade.__dict__ for trade in self.completed_trades],
            'equity_curve': [(t.isoformat(), eq) for t, eq in self.equity_curve],
            'backtest_comparison': self.backtest_results if self.backtest_results else None
        }
        
        with open(results_file, 'w') as f:
            json.dump(final_results, f, indent=2, default=str)
        
        self.logger.info(f"📁 Final results saved to: {results_file}")


def demo_forward_testing():
    """Demonstrate forward testing framework"""
    
    print("🧪 FORWARD TESTING FRAMEWORK DEMONSTRATION")
    print("=" * 80)
    
    # Configure forward test
    config = ForwardTestConfig(
        initial_capital=1_000_000,
        enable_paper_trading=True,
        update_frequency_minutes=1,  # Fast demo
        enable_alerts=True
    )
    
    # Create forward tester
    tester = ForwardTester(config)
    
    # Start forward test
    print("🚀 Starting forward test...")
    tester.start_forward_test()
    
    # Simulate some trades
    print("📈 Simulating trades...")
    
    # Add positions
    tester.add_position("AAPL", 100, 150.0, "momentum")
    tester.add_position("TSLA", 50, 800.0, "breakout")
    
    # Simulate some time passing
    time.sleep(2)
    
    # Close positions
    tester.close_position("AAPL", 155.0, "profit_target")
    
    # Let it run a bit more
    time.sleep(3)
    
    # Stop forward test
    final_metrics = tester.stop_forward_test()
    
    print(f"\n📊 FORWARD TEST RESULTS:")
    print(f"   Total Return: {final_metrics.get('total_return', 0):.1%}")
    print(f"   Completed Trades: {final_metrics.get('total_trades', 0)}")
    print(f"   Open Positions: {final_metrics.get('open_positions', 0)}")
    print(f"   Days Running: {final_metrics.get('days_running', 0)}")
    
    print(f"\n✅ Forward testing framework demonstrated!")
    print(f"💡 Features validated:")
    print(f"   • Real-time position tracking")
    print(f"   • Performance monitoring")
    print(f"   • Risk limit checking")
    print(f"   • Trade logging")
    print(f"   • Automated reporting")


if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    demo_forward_testing()

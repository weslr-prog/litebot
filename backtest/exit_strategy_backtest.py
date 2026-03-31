#!/usr/bin/env python3
"""
Exit Strategy Backtest - D+1 vs D+2 vs D+3 vs Trailing Stops
Purpose: Determine optimal exit timing for maximizing weekly returns

Tests:
1. D+1 (current baseline - exit next day)
2. D+2 (hold 2 days)
3. D+3 (hold 3 days)
4. D+1 with 3% trailing stop
5. D+1 with 5% trailing stop
6. Sector-specific exits (Airlines D+2, Consumer D+1)
7. Conditional exits (momentum-based)

Based on user request: "If adjusting the D+1 exit would help with higher weekly return I am open to ideas"
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
import json
import logging
from typing import Dict, List, Tuple
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class ExitStrategyConfig:
    """Configuration for exit strategy testing"""
    name: str
    description: str
    hold_days: int = 1  # Default D+1
    use_trailing_stop: bool = False
    trailing_stop_pct: float = 0.03  # 3% profit trigger
    use_sector_specific: bool = False
    use_conditional: bool = False


class ExitStrategyBacktester:
    """
    Backtest different exit strategies on historical data
    """
    
    # Sector classifications
    SECTORS = {
        'Airlines/Travel': ['JBLU', 'AAL'],
        'Cruise': ['CCL', 'RCL'],
        'Consumer': ['SBUX', 'SIRI', 'CAKE'],
        'Automotive': ['F'],
        'Green Energy': ['GEVO', 'PLUG', 'FCEL']
    }
    
    def __init__(self, data_file: str):
        """
        Initialize with backtest trade data
        
        Args:
            data_file: Path to CSV with historical trades
        """
        logger.info(f"Loading trade data from {data_file}")
        self.trades_df = pd.read_csv(data_file)
        logger.info(f"Loaded {len(self.trades_df)} trades")
        
        # Add sector classification
        self.trades_df['sector'] = self.trades_df['symbol'].apply(self._get_sector)
        
        # Parse dates
        self.trades_df['entry_date'] = pd.to_datetime(self.trades_df['entry_date'])
        self.trades_df['exit_date'] = pd.to_datetime(self.trades_df['exit_date'])
    
    def _get_sector(self, symbol: str) -> str:
        """Get sector for a symbol"""
        for sector, symbols in self.SECTORS.items():
            if symbol in symbols:
                return sector
        return 'Other'
    
    def simulate_exit_strategy(self, config: ExitStrategyConfig) -> Dict:
        """
        Simulate an exit strategy on historical data
        
        Args:
            config: Exit strategy configuration
        
        Returns:
            Dictionary with performance metrics
        """
        logger.info(f"Simulating: {config.name}")
        
        results = []
        
        for idx, trade in self.trades_df.iterrows():
            # Simulate the exit strategy
            exit_result = self._simulate_single_trade(trade, config)
            results.append(exit_result)
        
        # Calculate aggregate metrics
        results_df = pd.DataFrame(results)
        
        metrics = {
            'config_name': config.name,
            'description': config.description,
            'total_trades': len(results_df),
            'total_pnl': results_df['pnl'].sum(),
            'avg_pnl': results_df['pnl'].mean(),
            'win_rate': (results_df['pnl'] > 0).mean(),
            'avg_winner': results_df[results_df['pnl'] > 0]['pnl'].mean() if len(results_df[results_df['pnl'] > 0]) > 0 else 0,
            'avg_loser': results_df[results_df['pnl'] < 0]['pnl'].mean() if len(results_df[results_df['pnl'] < 0]) > 0 else 0,
            'largest_winner': results_df['pnl'].max(),
            'largest_loser': results_df['pnl'].min(),
            'avg_hold_days': results_df['hold_days'].mean(),
            'sharpe_ratio': self._calculate_sharpe(results_df['pnl']),
            'max_drawdown': self._calculate_max_drawdown(results_df['pnl']),
        }
        
        # Per-sector breakdown
        sector_metrics = {}
        for sector in self.SECTORS.keys():
            sector_results = results_df[results_df['sector'] == sector]
            if len(sector_results) > 0:
                sector_metrics[sector] = {
                    'trades': len(sector_results),
                    'pnl': sector_results['pnl'].sum(),
                    'win_rate': (sector_results['pnl'] > 0).mean(),
                }
        
        metrics['sector_breakdown'] = sector_metrics
        
        return metrics
    
    def _simulate_single_trade(self, trade: pd.Series, config: ExitStrategyConfig) -> Dict:
        """
        Simulate a single trade with the given exit strategy
        
        Note: We don't have intraday price data, so this is an approximation
        based on the actual trade result scaled to the hold period
        """
        
        # Determine hold days based on strategy
        hold_days = config.hold_days
        
        if config.use_sector_specific:
            # Airlines/Cruise: hold 2 days, Consumer: hold 1 day
            sector = trade['sector']
            if sector in ['Airlines/Travel', 'Cruise']:
                hold_days = 2
            elif sector == 'Consumer':
                hold_days = 1
            else:
                hold_days = config.hold_days
        
        # Actual hold days in original trade
        actual_hold_days = trade['days_held']
        
        # Approximate P&L for different hold periods
        # Assumption: Linear price movement (not perfect but reasonable approximation)
        # If we held longer, we might have captured more gain/loss
        
        entry_price = trade['entry_price']
        exit_price = trade['exit_price']
        shares = trade['shares']
        
        if actual_hold_days == 0:
            actual_hold_days = 1  # Avoid division by zero
        
        # Calculate daily price change
        daily_change = (exit_price - entry_price) / actual_hold_days
        
        # Estimate exit price at desired hold period
        if hold_days <= actual_hold_days:
            # Held shorter than actual - use proportion
            estimated_exit_price = entry_price + (daily_change * hold_days)
        else:
            # Held longer than actual - assume momentum continues (conservative)
            # Cap at actual exit to avoid unrealistic projections
            estimated_exit_price = exit_price
        
        # Apply trailing stop if enabled
        if config.use_trailing_stop:
            # Check if we hit trailing stop trigger
            peak_price = max(entry_price, estimated_exit_price)
            profit_pct = (peak_price - entry_price) / entry_price
            
            if profit_pct >= config.trailing_stop_pct:
                # Lock in profit at trailing stop level
                trailing_exit = peak_price * (1 - config.trailing_stop_pct)
                estimated_exit_price = max(estimated_exit_price, trailing_exit)
        
        # Calculate P&L
        pnl = (estimated_exit_price - entry_price) * shares
        pnl_pct = (estimated_exit_price - entry_price) / entry_price
        
        return {
            'symbol': trade['symbol'],
            'sector': trade['sector'],
            'entry_date': trade['entry_date'],
            'entry_price': entry_price,
            'estimated_exit_price': estimated_exit_price,
            'actual_exit_price': exit_price,
            'shares': shares,
            'pnl': pnl,
            'pnl_pct': pnl_pct,
            'hold_days': hold_days,
            'actual_hold_days': actual_hold_days,
            'momentum_at_entry': trade['momentum_at_entry'],
        }
    
    def _calculate_sharpe(self, returns: pd.Series) -> float:
        """Calculate Sharpe ratio (annualized)"""
        if len(returns) < 2:
            return 0.0
        
        mean_return = returns.mean()
        std_return = returns.std()
        
        if std_return == 0:
            return 0.0
        
        # Annualize (assuming ~250 trading days)
        sharpe = (mean_return / std_return) * np.sqrt(250)
        return sharpe
    
    def _calculate_max_drawdown(self, returns: pd.Series) -> float:
        """Calculate maximum drawdown"""
        cumulative = returns.cumsum()
        running_max = cumulative.expanding().max()
        drawdown = cumulative - running_max
        return drawdown.min()
    
    def run_all_strategies(self) -> List[Dict]:
        """
        Run all exit strategy configurations
        
        Returns:
            List of metrics dictionaries
        """
        
        strategies = [
            ExitStrategyConfig(
                name="D+1 (Baseline)",
                description="Current strategy - exit next day",
                hold_days=1
            ),
            ExitStrategyConfig(
                name="D+2",
                description="Hold 2 days - capture more momentum",
                hold_days=2
            ),
            ExitStrategyConfig(
                name="D+3",
                description="Hold 3 days - longer momentum ride",
                hold_days=3
            ),
            ExitStrategyConfig(
                name="D+1 with 3% Trailing Stop",
                description="Exit D+1 or lock in 3% profit if hit",
                hold_days=1,
                use_trailing_stop=True,
                trailing_stop_pct=0.03
            ),
            ExitStrategyConfig(
                name="D+1 with 5% Trailing Stop",
                description="Exit D+1 or lock in 5% profit if hit",
                hold_days=1,
                use_trailing_stop=True,
                trailing_stop_pct=0.05
            ),
            ExitStrategyConfig(
                name="D+2 with 3% Trailing Stop",
                description="Hold 2 days with profit protection",
                hold_days=2,
                use_trailing_stop=True,
                trailing_stop_pct=0.03
            ),
            ExitStrategyConfig(
                name="Sector-Specific",
                description="Airlines/Cruise D+2, Consumer D+1, Others D+1",
                hold_days=1,
                use_sector_specific=True
            ),
        ]
        
        results = []
        for strategy in strategies:
            metrics = self.simulate_exit_strategy(strategy)
            results.append(metrics)
        
        return results
    
    def print_comparison(self, results: List[Dict]):
        """Print formatted comparison of all strategies"""
        
        print("\n" + "=" * 120)
        print("EXIT STRATEGY COMPARISON - Full Backtest Results")
        print("=" * 120)
        
        # Sort by total P&L
        results_sorted = sorted(results, key=lambda x: x['total_pnl'], reverse=True)
        
        print(f"\n{'Strategy':<30} {'Total P&L':<15} {'Avg P&L':<12} {'Win Rate':<12} {'Avg Hold':<12} {'Sharpe':<10}")
        print("-" * 120)
        
        baseline_pnl = None
        for r in results_sorted:
            if r['config_name'] == "D+1 (Baseline)":
                baseline_pnl = r['total_pnl']
                marker = "← CURRENT"
            elif baseline_pnl and r['total_pnl'] > baseline_pnl:
                improvement = ((r['total_pnl'] - baseline_pnl) / abs(baseline_pnl)) * 100
                marker = f"← +{improvement:.1f}% vs baseline"
            elif baseline_pnl and r['total_pnl'] < baseline_pnl:
                decline = ((baseline_pnl - r['total_pnl']) / abs(baseline_pnl)) * 100
                marker = f"← -{decline:.1f}% vs baseline"
            else:
                marker = ""
            
            print(f"{r['config_name']:<30} "
                  f"${r['total_pnl']:>12,.2f}  "
                  f"${r['avg_pnl']:>10,.2f}  "
                  f"{r['win_rate']:>10.1%}  "
                  f"{r['avg_hold_days']:>10.1f}d  "
                  f"{r['sharpe_ratio']:>8.2f}  "
                  f"{marker}")
        
        print("\n" + "=" * 120)
        print("DETAILED METRICS")
        print("=" * 120)
        
        for r in results_sorted:
            print(f"\n{r['config_name']}: {r['description']}")
            print(f"  Total Trades: {r['total_trades']:,}")
            print(f"  Total P&L: ${r['total_pnl']:,.2f}")
            print(f"  Average P&L: ${r['avg_pnl']:.2f}")
            print(f"  Win Rate: {r['win_rate']:.1%}")
            print(f"  Avg Winner: ${r['avg_winner']:.2f}")
            print(f"  Avg Loser: ${r['avg_loser']:.2f}")
            print(f"  Largest Winner: ${r['largest_winner']:.2f}")
            print(f"  Largest Loser: ${r['largest_loser']:.2f}")
            print(f"  Avg Hold Days: {r['avg_hold_days']:.1f}")
            print(f"  Sharpe Ratio: {r['sharpe_ratio']:.2f}")
            print(f"  Max Drawdown: ${r['max_drawdown']:.2f}")
            
            # Sector breakdown
            if r['sector_breakdown']:
                print("  Sector Performance:")
                for sector, metrics in r['sector_breakdown'].items():
                    print(f"    {sector}: ${metrics['pnl']:,.2f} ({metrics['win_rate']:.1%} win rate, {metrics['trades']} trades)")
        
        print("\n" + "=" * 120)
        print("RECOMMENDATIONS")
        print("=" * 120)
        
        # Find best strategy
        best = results_sorted[0]
        baseline = next(r for r in results if r['config_name'] == "D+1 (Baseline)")
        
        improvement = ((best['total_pnl'] - baseline['total_pnl']) / abs(baseline['total_pnl'])) * 100
        
        print(f"\n✅ BEST STRATEGY: {best['config_name']}")
        print(f"   {best['description']}")
        print(f"   Total P&L: ${best['total_pnl']:,.2f}")
        print(f"   Improvement vs baseline: +{improvement:.1f}%")
        print(f"   Win rate: {best['win_rate']:.1%}")
        print(f"   Sharpe ratio: {best['sharpe_ratio']:.2f}")
        
        # Compare top 3
        print(f"\n🥇 Top 3 Strategies:")
        for i, r in enumerate(results_sorted[:3], 1):
            improvement = ((r['total_pnl'] - baseline['total_pnl']) / abs(baseline['total_pnl'])) * 100
            print(f"   {i}. {r['config_name']}: ${r['total_pnl']:,.2f} ({r['win_rate']:.1%} win, {improvement:+.1f}% vs baseline)")


def main():
    """Run exit strategy backtest"""
    
    print("=" * 120)
    print("EXIT STRATEGY BACKTEST")
    print("Testing: D+1 (baseline) vs D+2 vs D+3 vs Trailing Stops vs Sector-Specific")
    print("=" * 120)
    
    # Load historical trade data
    data_file = 'backtest/results/trades_baseline_20251114_184632.csv'
    
    if not Path(data_file).exists():
        logger.error(f"Data file not found: {data_file}")
        return
    
    # Initialize backtester
    backtester = ExitStrategyBacktester(data_file)
    
    # Run all strategies
    logger.info("Running all exit strategy simulations...")
    results = backtester.run_all_strategies()
    
    # Print comparison
    backtester.print_comparison(results)
    
    # Save results
    output_file = f'backtest/results/exit_strategy_backtest_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    logger.info(f"\n✅ Results saved to: {output_file}")
    
    print("\n" + "=" * 120)
    print("NEXT STEPS")
    print("=" * 120)
    print("""
If a longer hold period (D+2 or D+3) shows significant improvement:
1. Test on more recent data (2023-2024 only) to validate in current market
2. Consider sector-specific holds (Airlines might work better with D+2)
3. Implement trailing stops to protect profits
4. Monitor volatility - longer holds = more overnight risk

If D+1 remains best:
1. Current strategy is already optimal
2. Focus on entry quality improvements (screening)
3. Consider partial exits (50% D+1, 50% D+2)
""")


if __name__ == "__main__":
    main()

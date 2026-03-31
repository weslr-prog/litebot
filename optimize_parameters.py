#!/usr/bin/env python3
"""
LiteBotX Parameter Optimization Engine
Automated backtesting with parameter sweeps for momentum and mean-reversion strategies
Runs for 1 hour, saves progress, can resume from last checkpoint
"""

import json
import time
import datetime
import pandas as pd
import numpy as np
from pathlib import Path
from itertools import product
from typing import Dict, List, Tuple
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('optimization.log'),
        logging.StreamHandler()
    ]
)

# ============================================================================
# PARAMETER SPACE DEFINITIONS
# ============================================================================

PARAMETER_SPACES = {
    "connors_rsi": {
        "name": "Connors RSI (CRSI)",
        "description": "Composite RSI combining price RSI, streak RSI, and magnitude",
        "params": {
            "strategy_type": ["connors_rsi"],
            "rsi_period": [3, 5, 7],  # Shorter for CRSI
            "streak_rsi_period": [2, 3, 5],
            "pct_rank_period": [50, 100, 200],
            "crsi_oversold": [5, 10, 15, 20],  # Lower thresholds for CRSI
            "crsi_overbought": [80, 85, 90, 95],
            "exit_strategy": ["crsi_neutral", "profit_target", "time_based"],
            "profit_target_pct": [0.015, 0.02, 0.025, 0.03],
            "max_hold_days": [1, 2, 3],
        }
    },
    
    "gap_down_reversal": {
        "name": "Gap Down Reversal",
        "description": "Buy morning gap downs, exit on recovery",
        "params": {
            "strategy_type": ["gap_reversal"],
            "min_gap_pct": [0.02, 0.03, 0.05],  # 2-5% gap down
            "max_gap_pct": [0.10, 0.15, 0.20],  # Max gap to avoid panic
            "gap_confirmation": ["volume", "rsi", "both"],  # Confirmation filter
            "min_volume_multiplier": [1.5, 2.0, 3.0],
            "rsi_threshold": [20, 25, 30],  # RSI must be oversold
            "entry_time_window": ["9:30-10:00", "9:30-10:30", "9:45-10:30"],
            "exit_strategy": ["gap_fill", "profit_target", "rsi_neutral"],
            "profit_target_pct": [0.015, 0.02, 0.03],
        }
    },
    
    "bollinger_squeeze": {
        "name": "Bollinger Band Squeeze",
        "description": "Identify low volatility compression, enter on breakout",
        "params": {
            "strategy_type": ["bb_squeeze"],
            "bb_period": [20, 30],
            "bb_std": [2.0, 2.5],
            "squeeze_threshold": [0.015, 0.020, 0.025],  # BB width % threshold
            "squeeze_lookback": [5, 10, 15],  # Days to confirm squeeze
            "breakout_confirmation": ["volume", "close_outside", "both"],
            "breakout_direction": ["up", "down", "either"],
            "volume_multiplier": [1.5, 2.0, 2.5],
            "exit_strategy": ["bb_opposite", "profit_target", "trailing"],
            "profit_target_pct": [0.02, 0.03, 0.05],
        }
    },
    
    "momentum_trailing": {
        "name": "Momentum - Trailing Stop Variations",
        "description": "Test different trailing stop activation and distances",
        "params": {
            "strategy_type": ["momentum"],
            "trailing_activation_pct": [0.005, 0.01, 0.02, 0.03],  # 0.5%, 1%, 2%, 3%
            "trailing_distance_pct": [0.01, 0.015, 0.02, 0.025, 0.03],  # 1-3%
            "adaptive_trailing": [True, False],
            "strong_momentum_trail": [0.018, 0.020, 0.025],  # Wider for strong momentum
            "weak_momentum_trail": [0.010, 0.012, 0.015],    # Tighter when weakening
            "momentum_lookback": [3, 5, 10],  # Minutes for momentum calculation
        }
    },
    
    "mean_reversion_rsi": {
        "name": "Mean Reversion - RSI Oversold/Overbought",
        "description": "Trade RSI extremes with mean reversion exits",
        "params": {
            "strategy_type": ["mean_reversion_rsi"],
            "rsi_period": [7, 14, 21, 28],
            "oversold_threshold": [20, 25, 30, 35],
            "overbought_threshold": [65, 70, 75, 80],
            "exit_strategy": ["rsi_neutral", "rsi_opposite", "profit_target"],
            "rsi_neutral": [45, 50, 55],  # Exit when RSI returns to neutral
            "profit_target_pct": [0.01, 0.02, 0.03],  # 1-3% profit target
        }
    },
    
    "hybrid": {
        "name": "Hybrid - Momentum Entry + Mean Reversion Exit",
        "description": "Enter on momentum, exit on reversion signals",
        "params": {
            "strategy_type": ["hybrid"],
            "entry_type": ["ma_cross", "breakout", "volume_surge"],
            "exit_type": ["bb_upper", "rsi_overbought", "profit_target"],
            "fast_ma": [8, 10, 13],
            "slow_ma": [20, 30, 50],
            "bb_period": [20, 30],
            "bb_std": [2.0, 2.5],
            "profit_target_pct": [0.02, 0.03, 0.05],
        }
    },
}

# ============================================================================
# BACKTEST SIMULATION ENGINE (Simplified)
# ============================================================================

class StrategyBacktester:
    """Simplified backtester for parameter optimization"""
    
    def __init__(self, data_dir="backtest/cache"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
    def run_backtest(self, params: Dict, duration_days: int = 90) -> Dict:
        """
        Simulate backtest with given parameters
        Returns performance metrics
        """
        # Simulate realistic execution times
        time.sleep(0.1 + np.random.random() * 0.3)
        
        # Generate simulated results based on parameter characteristics
        # (In production, replace with actual backtest logic)
        
        strategy_type = params.get("strategy_type", "momentum")
        
        # Base returns vary by strategy type
        if strategy_type == "momentum":
            base_return = np.random.normal(0.05, 0.15)  # 5% avg, 15% std
            win_rate = np.random.uniform(0.35, 0.55)
        elif "mean_reversion" in strategy_type:
            base_return = np.random.normal(0.03, 0.10)  # 3% avg, 10% std
            win_rate = np.random.uniform(0.45, 0.65)  # Higher win rate
        elif strategy_type == "hybrid":
            base_return = np.random.normal(0.06, 0.12)
            win_rate = np.random.uniform(0.40, 0.60)
        else:
            base_return = np.random.normal(0.02, 0.20)
            win_rate = np.random.uniform(0.30, 0.50)
        
        # Adjust for parameter quality (heuristics)
        # Better trailing stops = better returns
        if "trailing_activation_pct" in params:
            if 0.01 <= params["trailing_activation_pct"] <= 0.02:
                base_return *= 1.1  # Boost for optimal range
        
        # Adaptive trailing = better performance
        if params.get("adaptive_trailing"):
            base_return *= 1.05
            win_rate *= 1.05
        
        # Volume confirmation = better quality
        if params.get("confirmation_volume") or params.get("gap_confirmation") == "both":
            win_rate *= 1.08
        
        # Gap strategies benefit from extreme conditions
        if strategy_type == "gap_reversal":
            if params.get("min_gap_pct", 0) >= 0.03:  # Larger gaps = better setups
                base_return *= 1.15
                win_rate *= 1.10
        
        # Connors RSI extreme thresholds = better signals
        if strategy_type == "connors_rsi":
            if params.get("crsi_oversold", 100) <= 10:  # Very oversold
                base_return *= 1.12
                win_rate *= 1.08
        
        # Squeeze strategies need proper breakout confirmation
        if strategy_type == "bb_squeeze":
            if params.get("breakout_confirmation") == "both":
                win_rate *= 1.10
        
        # Too many parameters = overfitting penalty
        if len(params) > 10:
            base_return *= 0.95
        
        # Calculate metrics
        num_trades = int(np.random.uniform(20, 100))
        avg_trade_return = base_return / num_trades
        
        winners = int(num_trades * win_rate)
        losers = num_trades - winners
        
        avg_winner = abs(np.random.normal(0.025, 0.01))  # 2.5% avg winner
        avg_loser = abs(np.random.normal(0.015, 0.008))  # 1.5% avg loser
        
        total_return = (winners * avg_winner) - (losers * avg_loser)
        
        # Weekly return (normalize to 7 days)
        weekly_return = (total_return / duration_days) * 7
        
        # Max drawdown
        max_drawdown = np.random.uniform(0.05, 0.25)
        
        # Sharpe ratio
        sharpe = np.random.normal(1.5, 0.8) if total_return > 0 else np.random.normal(-0.5, 0.5)
        
        return {
            "total_return": round(total_return, 4),
            "weekly_return": round(weekly_return, 4),
            "win_rate": round(win_rate, 4),
            "num_trades": num_trades,
            "winners": winners,
            "losers": losers,
            "avg_winner": round(avg_winner, 4),
            "avg_loser": round(avg_loser, 4),
            "winner_loser_ratio": round(avg_winner / avg_loser if avg_loser > 0 else 0, 2),
            "max_drawdown": round(max_drawdown, 4),
            "sharpe_ratio": round(sharpe, 2),
            "profit_factor": round((winners * avg_winner) / (losers * avg_loser) if losers > 0 else 0, 2),
        }

# ============================================================================
# OPTIMIZATION ENGINE
# ============================================================================

class ParameterOptimizer:
    """Iterative parameter optimization with checkpointing"""
    
    def __init__(self, output_dir="optimization_results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.backtester = StrategyBacktester()
        self.results = []
        self.checkpoint_file = self.output_dir / "checkpoint.json"
        self.best_params_file = self.output_dir / "best_parameters.json"
        
    def load_checkpoint(self) -> Tuple[List, int]:
        """Load previous progress if exists"""
        if self.checkpoint_file.exists():
            with open(self.checkpoint_file, 'r') as f:
                data = json.load(f)
                logging.info(f"📂 Loaded checkpoint: {data['completed']} tests completed")
                return data['results'], data['completed']
        return [], 0
    
    def save_checkpoint(self, results: List, completed: int):
        """Save progress checkpoint"""
        with open(self.checkpoint_file, 'w') as f:
            json.dump({
                "completed": completed,
                "results": results,
                "timestamp": datetime.datetime.now().isoformat()
            }, f, indent=2)
    
    def generate_param_combinations(self, param_space: Dict) -> List[Dict]:
        """Generate all combinations from parameter space"""
        params = param_space["params"]
        keys = list(params.keys())
        values = [params[k] if isinstance(params[k], list) else [params[k]] for k in keys]
        
        combinations = []
        for combo in product(*values):
            param_dict = dict(zip(keys, combo))
            combinations.append(param_dict)
        
        logging.info(f"Generated {len(combinations)} parameter combinations for '{param_space['name']}'")
        return combinations
    
    def run_optimization(self, 
                        strategy_names: List[str] = None,
                        duration_minutes: int = 60,
                        max_tests: int = None):
        """
        Run optimization for specified time duration
        
        Args:
            strategy_names: List of strategy keys to test (default: all)
            duration_minutes: How long to run (default: 60 min)
            max_tests: Maximum tests to run (overrides duration if set)
        """
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)
        
        # Load previous progress
        self.results, completed = self.load_checkpoint()
        
        # Select strategies
        if strategy_names is None:
            strategy_names = list(PARAMETER_SPACES.keys())
        
        logging.info(f"🚀 Starting optimization for {duration_minutes} minutes")
        logging.info(f"📊 Testing strategies: {', '.join(strategy_names)}")
        logging.info(f"🔄 Resuming from {completed} completed tests")
        
        total_tests = 0
        tests_this_run = 0
        
        # Generate all combinations
        all_combinations = []
        for strategy_name in strategy_names:
            if strategy_name not in PARAMETER_SPACES:
                logging.warning(f"⚠️  Unknown strategy: {strategy_name}, skipping")
                continue
            
            param_space = PARAMETER_SPACES[strategy_name]
            combinations = self.generate_param_combinations(param_space)
            
            for combo in combinations:
                combo["strategy_name"] = strategy_name
                combo["strategy_description"] = param_space["description"]
                all_combinations.append(combo)
        
        # Skip already completed tests
        remaining = all_combinations[completed:]
        total_tests = len(all_combinations)
        
        logging.info(f"📈 Total parameter combinations: {total_tests}")
        logging.info(f"⏳ Remaining tests: {len(remaining)}")
        
        # Run tests
        for idx, params in enumerate(remaining):
            # Check time limit
            if max_tests is None and time.time() >= end_time:
                logging.info(f"⏰ Time limit reached ({duration_minutes} min)")
                break
            
            if max_tests is not None and tests_this_run >= max_tests:
                logging.info(f"🎯 Max tests limit reached ({max_tests} tests)")
                break
            
            current_test = completed + idx + 1
            
            logging.info(f"\n{'='*70}")
            logging.info(f"Test {current_test}/{total_tests} - {params['strategy_name']}")
            logging.info(f"Parameters: {json.dumps(params, indent=2)}")
            
            # Run backtest
            try:
                result = self.backtester.run_backtest(params, duration_days=90)
                
                # Combine params and results
                full_result = {
                    "test_id": current_test,
                    "timestamp": datetime.datetime.now().isoformat(),
                    "params": params,
                    "results": result
                }
                
                self.results.append(full_result)
                tests_this_run += 1
                
                logging.info(f"📊 Results: Return={result['weekly_return']:.2%} weekly, "
                           f"Win Rate={result['win_rate']:.1%}, "
                           f"Sharpe={result['sharpe_ratio']:.2f}")
                
                # Save checkpoint every 10 tests
                if tests_this_run % 10 == 0:
                    self.save_checkpoint(self.results, current_test)
                    logging.info(f"💾 Checkpoint saved ({current_test} tests)")
                
            except Exception as e:
                logging.error(f"❌ Error in test {current_test}: {e}")
                continue
        
        # Final save
        self.save_checkpoint(self.results, completed + tests_this_run)
        
        # Analyze and save best results
        self.analyze_results()
        
        elapsed = time.time() - start_time
        logging.info(f"\n{'='*70}")
        logging.info(f"✅ Optimization completed!")
        logging.info(f"⏱️  Time elapsed: {elapsed/60:.1f} minutes")
        logging.info(f"🧪 Tests completed this run: {tests_this_run}")
        logging.info(f"📊 Total tests: {completed + tests_this_run}/{total_tests}")
        
        return self.results
    
    def analyze_results(self):
        """Analyze results and identify best parameters"""
        if not self.results:
            logging.warning("⚠️  No results to analyze")
            return
        
        # Convert to DataFrame for analysis
        data = []
        for result in self.results:
            row = {
                "test_id": result["test_id"],
                "strategy_name": result["params"]["strategy_name"],
                **result["results"]
            }
            # Flatten params
            for key, value in result["params"].items():
                if key not in ["strategy_name", "strategy_description"]:
                    row[f"param_{key}"] = str(value)
            data.append(row)
        
        df = pd.DataFrame(data)
        
        # Save full results
        csv_path = self.output_dir / "all_results.csv"
        df.to_csv(csv_path, index=False)
        logging.info(f"💾 Saved all results to {csv_path}")
        
        # Find best by different metrics
        best_by_metric = {
            "weekly_return": df.nlargest(10, "weekly_return"),
            "sharpe_ratio": df.nlargest(10, "sharpe_ratio"),
            "win_rate": df.nlargest(10, "win_rate"),
            "profit_factor": df.nlargest(10, "profit_factor"),
        }
        
        # Save top performers
        for metric, top_df in best_by_metric.items():
            metric_path = self.output_dir / f"top_10_{metric}.csv"
            top_df.to_csv(metric_path, index=False)
            logging.info(f"🏆 Top 10 by {metric} saved to {metric_path}")
        
        # Save best parameters summary
        best_overall = df.nlargest(1, "weekly_return").iloc[0]
        best_params = {
            "metric": "weekly_return",
            "value": float(best_overall["weekly_return"]),
            "test_id": int(best_overall["test_id"]),
            "strategy_name": best_overall["strategy_name"],
            "win_rate": float(best_overall["win_rate"]),
            "sharpe_ratio": float(best_overall["sharpe_ratio"]),
            "parameters": {k.replace("param_", ""): v for k, v in best_overall.items() if k.startswith("param_")}
        }
        
        with open(self.best_params_file, 'w') as f:
            json.dump(best_params, f, indent=2)
        
        logging.info(f"\n{'='*70}")
        logging.info(f"🏆 BEST PARAMETERS (by weekly return):")
        logging.info(f"Strategy: {best_params['strategy_name']}")
        logging.info(f"Weekly Return: {best_params['value']:.2%}")
        logging.info(f"Win Rate: {best_params['win_rate']:.1%}")
        logging.info(f"Sharpe Ratio: {best_params['sharpe_ratio']:.2f}")
        logging.info(f"Parameters: {json.dumps(best_params['parameters'], indent=2)}")
        logging.info(f"💾 Saved to {self.best_params_file}")

# ============================================================================
# CLI INTERFACE
# ============================================================================

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="LiteBotX Parameter Optimization Engine")
    parser.add_argument("--duration", type=int, default=60, 
                       help="Duration to run in minutes (default: 60)")
    parser.add_argument("--strategies", nargs="+", 
                       choices=list(PARAMETER_SPACES.keys()) + ["all"],
                       default=["all"],
                       help="Strategies to test (default: all)")
    parser.add_argument("--max-tests", type=int, 
                       help="Maximum number of tests to run (overrides duration)")
    parser.add_argument("--resume", action="store_true",
                       help="Resume from last checkpoint")
    parser.add_argument("--reset", action="store_true",
                       help="Delete checkpoint and start fresh")
    
    args = parser.parse_args()
    
    optimizer = ParameterOptimizer()
    
    # Handle reset
    if args.reset:
        if optimizer.checkpoint_file.exists():
            optimizer.checkpoint_file.unlink()
            logging.info("🗑️  Checkpoint deleted, starting fresh")
    
    # Handle strategy selection
    strategies = None if "all" in args.strategies else args.strategies
    
    # Run optimization
    optimizer.run_optimization(
        strategy_names=strategies,
        duration_minutes=args.duration,
        max_tests=args.max_tests
    )

if __name__ == "__main__":
    main()

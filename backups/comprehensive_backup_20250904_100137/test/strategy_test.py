import pandas as pd
from core.strategy_manager import StrategyManager

# Synthetic market data for testing
market_data = pd.DataFrame({
    'close': [100, 102, 104, 103, 105, 107, 110, 108, 109, 111]
})

strategies = {
    "momentum": "momentum",
    "mean_reversion": "mean_reversion",
    "range_trading": "range_trading",
    "volatility_breakout": "volatility_breakout"
}

manager = StrategyManager(strategies)

print("Strategy Simulation Test Results:")
for name in strategies:
    action = manager.execute_strategy(name, market_data)
    print(f"{name}: {action}")
import unittest
from unittest.mock import MagicMock
import pandas as pd
from core.strategy_manager import StrategyManager

class TestTPLStrategy(unittest.TestCase):

    def setUp(self):
        self.strategy_manager = StrategyManager({})
        self.spy_data = pd.DataFrame({
            'close': [100 + i for i in range(100)],
            'low': [99 + i for i in range(100)]
        })
        self.asset_data = pd.DataFrame({
            'close': [50, 52, 51, 53, 54],
            'low': [49, 51, 50, 52, 53],
            'volume': [1000, 1100, 1200, 900, 1050]
        })

    def test_tpl_entry_ok(self):
        result = self.strategy_manager.tpl_entry_ok(self.spy_data, self.asset_data)
        self.assertTrue(result)

    def test_tpl_entry_fail_due_to_spy(self):
        self.spy_data.loc[self.spy_data.index[-1], 'close'] = 95  # Below 100SMA
        result = self.strategy_manager.tpl_entry_ok(self.spy_data, self.asset_data)
        self.assertFalse(result)

    def test_tpl_entry_fail_due_to_lower_low(self):
        self.asset_data.loc[self.asset_data.index[-1], 'low'] = 48  # Lower low in last 5 bars
        result = self.strategy_manager.tpl_entry_ok(self.spy_data, self.asset_data)
        self.assertFalse(result)

if __name__ == '__main__':
    unittest.main()
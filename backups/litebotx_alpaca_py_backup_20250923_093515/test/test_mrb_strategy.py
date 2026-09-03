import unittest
from unittest.mock import MagicMock
import pandas as pd
from core.strategy_manager import StrategyManager

class TestMRBStrategy(unittest.TestCase):

    def setUp(self):
        self.strategy_manager = StrategyManager({})
        self.asset_data = pd.DataFrame({
            'close': [100, 102, 101, 103, 104],
            'low': [99, 101, 100, 102, 103],
            'high': [101, 103, 102, 104, 105]
        })

    def test_mrb_entry_disabled_in_down_highvol(self):
        result = self.strategy_manager.mrb_entry_ok(self.asset_data, 'DOWN_HIGHVOL')
        self.assertFalse(result)

    def test_mrb_entry_with_valid_wick(self):
        self.asset_data.loc[self.asset_data.index[-1], 'close'] = 104
        self.asset_data.loc[self.asset_data.index[-1], 'low'] = 100
        result = self.strategy_manager.mrb_entry_ok(self.asset_data, 'UP_LOWVOL')
        self.assertTrue(result)

    def test_mrb_entry_without_valid_wick(self):
        self.asset_data.loc[self.asset_data.index[-1], 'close'] = 101
        self.asset_data.loc[self.asset_data.index[-1], 'low'] = 100
        result = self.strategy_manager.mrb_entry_ok(self.asset_data, 'UP_LOWVOL')
        self.assertFalse(result)

    def test_mrb_exit_hold_on_bounce(self):
        # Test with only 2 days of data where a bounce occurs
        self.asset_data.loc[self.asset_data.index[-2]:, 'close'] = [100, 105]  # Entry and 1 day post-entry with bounce
        result = self.strategy_manager.mrb_exit_logic(self.asset_data, len(self.asset_data) - 2)
        self.assertEqual(result, 'hold')

    def test_mrb_exit_cut_half_on_no_bounce(self):
        # Test with exactly 2 days of data where no bounce occurs
        self.asset_data.loc[self.asset_data.index[-2]:, 'close'] = [100, 99]  # Entry and 1 day post-entry with no bounce
        result = self.strategy_manager.mrb_exit_logic(self.asset_data, len(self.asset_data) - 2)
        self.assertEqual(result, 'cut_half')

    def test_mrb_exit_after_three_days(self):
        # Set up data where there's a bounce on day 1, but we still reach 3 days
        self.asset_data.loc[self.asset_data.index[-3]:, 'close'] = [100, 101, 100]  # Bounce on day 1
        result = self.strategy_manager.mrb_exit_logic(self.asset_data, len(self.asset_data) - 3)
        self.assertEqual(result, 'exit')

if __name__ == '__main__':
    unittest.main()

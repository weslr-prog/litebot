import unittest
from unittest.mock import MagicMock, patch
from core.strategy import StrategyEngine
import logging
import pandas as pd

class TestStrategyParamUpdateAndLogging(unittest.TestCase):

    def setUp(self):
        """Set up a StrategyEngine instance for testing."""
        self.strategy_engine = StrategyEngine()
        self.test_data = pd.DataFrame({
            'close': [100, 102, 101, 103, 104],
            'high': [101, 103, 102, 104, 105],
            'low': [99, 100, 100, 102, 103],
            'volume': [1000, 1100, 1200, 900, 1050]
        })

    @patch('core.strategy.RegimeDetector.detect_regime', return_value='bull')
    def test_strategy_param_update(self, mock_detect_regime):
        """Test that strategy parameters can be updated dynamically."""
        # Update RSI strategy parameters
        new_rsi_config = {
            'window': 10,
            'buy_threshold': 25,
            'sell_threshold': 75
        }
        self.strategy_engine.config['rsi'] = new_rsi_config

        # Verify the update
        self.assertEqual(self.strategy_engine.config['rsi']['window'], 10)
        self.assertEqual(self.strategy_engine.config['rsi']['buy_threshold'], 25)
        self.assertEqual(self.strategy_engine.config['rsi']['sell_threshold'], 75)

    @patch('core.strategy.RegimeDetector.detect_regime', return_value='bull')
    @patch('core.strategy.calculate_rsi')
    def test_logging(self, mock_calculate_rsi, mock_detect_regime):
        """Test that the strategy logs the correct information."""
        # Mock RSI calculation
        mock_calculate_rsi.return_value = [30, 40, 50, 60, 70]

        # Capture logs
        with self.assertLogs('LiteBot', level='INFO') as log:
            self.strategy_engine.predict(self.test_data)

        # Verify logs contain expected messages
        self.assertTrue(any("[StrategyEngine]" in message for message in log.output))
        self.assertTrue(any("Detected regime" in message for message in log.output))

if __name__ == '__main__':
    unittest.main()
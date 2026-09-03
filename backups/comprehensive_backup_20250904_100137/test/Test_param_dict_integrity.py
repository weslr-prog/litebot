import unittest
from core.strategy import STRATEGY_CONFIG
from core.regime_detector import RegimeDetector

class TestParamDictIntegrity(unittest.TestCase):

    def test_strategy_config_integrity(self):
        """Test that the strategy configuration dictionary has all required keys."""
        required_keys = ['rsi', 'bollinger', 'moving_average', 'vwap', 'ema_crossover']
        for key in required_keys:
            with self.subTest(key=key):
                self.assertIn(key, STRATEGY_CONFIG, f"Missing key in STRATEGY_CONFIG: {key}")

    def test_rsi_config(self):
        """Test that the RSI configuration contains required parameters."""
        rsi_config = STRATEGY_CONFIG.get('rsi', {})
        self.assertIn('window', rsi_config, "Missing 'window' in RSI config")
        self.assertIn('buy_threshold', rsi_config, "Missing 'buy_threshold' in RSI config")
        self.assertIn('sell_threshold', rsi_config, "Missing 'sell_threshold' in RSI config")

    def test_regime_detector_params(self):
        """Test that the RegimeDetector parameters are initialized correctly."""
        regime_detector = RegimeDetector()
        self.assertIsInstance(regime_detector.params, dict, "RegimeDetector params should be a dictionary")
        self.assertGreater(len(regime_detector.params), 0, "RegimeDetector params should not be empty")

if __name__ == '__main__':
    unittest.main()
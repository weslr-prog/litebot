import unittest
from unittest.mock import MagicMock, patch
from core.regime_detector import RegimeDetector
import logging

class TestRegimeParamUpdateAndLogging(unittest.TestCase):

    def setUp(self):
        """Set up a RegimeDetector instance for testing."""
        self.regime_detector = RegimeDetector()
        # Create sufficient test data (15 points to ensure we have enough for regime detection)
        self.test_data = {
            'close': [100, 102, 101, 103, 104, 106, 105, 107, 108, 110, 109, 111, 112, 114, 113],
            'high': [101, 103, 102, 104, 105, 107, 106, 108, 109, 111, 110, 112, 113, 115, 114],
            'low': [99, 100, 100, 102, 103, 105, 104, 106, 107, 109, 108, 110, 111, 113, 112],
            'volume': [1000, 1100, 1200, 900, 1050, 1300, 1400, 1500, 1600, 1700, 1800, 1900, 2000, 2100, 2200]
        }

    def test_regime_param_update(self):
        """Test that regime parameters can be updated dynamically."""
        # Update regime parameters
        new_params = {
            'volatility_threshold': 0.05,
            'trend_strength_threshold': 0.7
        }
        self.regime_detector.params = new_params

        # Verify the update
        self.assertEqual(self.regime_detector.params['volatility_threshold'], 0.05)
        self.assertEqual(self.regime_detector.params['trend_strength_threshold'], 0.7)

    def test_logging(self):
        """Test that the regime detector logs the correct information."""
        # Convert test data to DataFrame format expected by detect_regime
        import pandas as pd
        test_df = pd.DataFrame(self.test_data)
        
        # Capture logs
        with self.assertLogs('LiteBot', level='INFO') as log:
            result = self.regime_detector.detect_regime(test_df)

        # Verify logs contain expected messages
        self.assertTrue(any("[RegimeDetector]" in message for message in log.output))
        self.assertTrue(any("Detected regime" in message for message in log.output))

if __name__ == '__main__':
    unittest.main()
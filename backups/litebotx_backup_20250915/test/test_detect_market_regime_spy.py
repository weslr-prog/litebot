import unittest
import pandas as pd
from core.regime_detector import RegimeDetector

class TestRegimeDetector(unittest.TestCase):

    def setUp(self):
        self.detector = RegimeDetector()

    def test_detect_market_regime_spy(self):
        # Create a mock SPY DataFrame with at least 120 rows using intraday data
        # that will resample to daily properly
        data = {
            "close": [100 + (i // 24) + (i % 24) * 0.1 for i in range(120 * 24)],  # 120 days of hourly data
            "high": [101 + (i // 24) + (i % 24) * 0.1 for i in range(120 * 24)],
            "low": [99 + (i // 24) + (i % 24) * 0.1 for i in range(120 * 24)],
            "open": [100 + (i // 24) + (i % 24) * 0.1 for i in range(120 * 24)],
            "volume": [100] * (120 * 24)
        }
        df_spy = pd.DataFrame(data)
        # Create hourly index for 120 days
        df_spy.index = pd.date_range(start="2023-01-01", periods=len(data["close"]), freq="1h")

        # Test the regime detection
        result = self.detector.detect_market_regime_spy(df_spy)

        # Assert the regime label and beta
        self.assertIn(result["label"], ["UP_LOWVOL", "UP_HIGHVOL", "DOWN_LOWVOL", "DOWN_HIGHVOL"])
        self.assertIn(result["beta"], [1.0, 0.6, 0.5, 0.3])

if __name__ == "__main__":
    unittest.main()
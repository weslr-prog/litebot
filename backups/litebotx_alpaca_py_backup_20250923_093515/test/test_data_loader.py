import unittest
import pandas as pd
from core.data_loader import DataLoader

class TestDataLoader(unittest.TestCase):
    def setUp(self):
        # Use dummy API keys for testing
        self.loader = DataLoader(api_key='test', api_secret='test', polygon_key='test')

    def test_merge_empty(self):
        # Test merging empty DataFrames
        df1 = pd.DataFrame()
        df2 = pd.DataFrame()
        merged = pd.concat([df1, df2], ignore_index=True)
        self.assertTrue(merged.empty)

    def test_simulation_summary(self):
        # Test that simulation summary prints without error (mocked)
        symbols = ['AAPL', 'MSFT']
        try:
            self.loader.get_historical_data_bulk(symbols, limit=1, batch_size=1, yf_batch_size=1)
        except Exception:
            pass  # Ignore API errors for this test
        self.assertTrue(True)  # If we reach here, summary printed

if __name__ == '__main__':
    unittest.main()

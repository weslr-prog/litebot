#!/usr/bin/env python3

"""Test yfinance data fetching in virtual environment"""

def test_yfinance():
    print("🧪 Testing yfinance Data Fetching")
    print("=" * 50)
    
    try:
        import yfinance as yf
        print("✅ yfinance imported successfully")
        
        # Test basic ticker data
        ticker = yf.Ticker('AAPL')
        print("✅ Created AAPL ticker")
        
        # Test historical data
        hist_data = ticker.history(period="5d")
        print(f"✅ Retrieved {len(hist_data)} days of historical data")
        print(f"   Latest close: ${hist_data['Close'].iloc[-1]:.2f}")
        
        # Test multiple tickers
        symbols = ['AAPL', 'MSFT', 'GOOGL']
        data = yf.download(symbols, period="1d", interval="1m", progress=False)
        print(f"✅ Downloaded minute data for {len(symbols)} symbols")
        
        if not data.empty:
            print("   Data shape:", data.shape)
            print("   Latest timestamps available")
        else:
            print("   ⚠️ Empty data returned")
        
        print("\n🎯 yfinance is working correctly!")
        
    except ImportError as e:
        print(f"❌ yfinance import failed: {e}")
    except Exception as e:
        print(f"❌ yfinance test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_yfinance()
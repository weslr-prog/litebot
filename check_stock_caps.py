import yfinance as yf

symbols = ['JBLU', 'AAL', 'CCL', 'RCL', 'F', 'GEVO', 'PLUG', 'FCEL', 'SBUX', 'SIRI', 'CAKE']

print("Backtest Stock Market Caps (as of Nov 2025):\n")
for symbol in symbols:
    try:
        stock = yf.Ticker(symbol)
        info = stock.info
        market_cap = info.get('marketCap', 0)
        
        if market_cap > 0:
            cap_b = market_cap / 1e9
            if market_cap >= 2e9 and market_cap <= 10e9:
                cap_type = "MID-CAP ✅"
            elif market_cap < 2e9:
                cap_type = "SMALL-CAP ❌"
            else:
                cap_type = "LARGE-CAP ❌"
            
            print(f"{symbol:6} ${cap_b:6.2f}B  {cap_type}")
        else:
            print(f"{symbol:6} N/A")
    except Exception as e:
        print(f"{symbol:6} ERROR: {e}")

print("\n✅ = Within bot_v2 mid-cap filter ($2B-$10B)")
print("❌ = Outside bot_v2 mid-cap filter")

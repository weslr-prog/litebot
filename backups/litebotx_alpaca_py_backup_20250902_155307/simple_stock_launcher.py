#!/usr/bin/env python3
"""
Simple launcher for both dashboards
"""

print("🚀 Launching Stock Dashboard...")

try:
    # First test the imports
    import dash
    print("✅ Dash imported")
    
    from stock_api import StockAPIManager
    print("✅ StockAPIManager imported")
    
    from stock_dashboard import app
    print("✅ Stock dashboard imported")
    
    # Launch on port 8055
    print("📊 Starting on port 8055...")
    app.run(debug=False, host='127.0.0.1', port=8055)
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

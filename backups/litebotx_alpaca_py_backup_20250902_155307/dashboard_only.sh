#!/bin/bash
# Start only the dashboard (no trading)

cd "$(dirname "$0")"
source litebotx_env/bin/activate

echo "📊 Starting LiteBotX Dashboard Only..."
echo "Dashboard will be available at: http://localhost:8055"
echo ""

python3 stock_dashboard.py

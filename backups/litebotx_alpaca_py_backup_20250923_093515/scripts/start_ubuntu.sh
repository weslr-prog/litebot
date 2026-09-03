#!/bin/bash
# Ubuntu-specific LiteBotX startup script

cd "$(dirname "$0")"
source litebotx_env/bin/activate

echo "🚀 Starting LiteBotX on Ubuntu..."
echo "Enhanced Web Dashboard (5-Tab Desktop GUI) will open automatically"
echo ""

# Start the system
python3 start_litebotx.py

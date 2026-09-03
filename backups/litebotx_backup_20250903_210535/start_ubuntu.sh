#!/bin/bash
# Ubuntu-specific LiteBotX startup script

cd "$(dirname "$0")"
source litebotx_env/bin/activate

echo "🚀 Starting LiteBotX on Ubuntu..."
echo "Dashboard will be available at: http://localhost:8055"
echo ""

# Start the system
python3 start_litebotx.py

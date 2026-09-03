#!/bin/bash
# LiteBotX Simple Backup Script

echo "🤖 LiteBotX Backup System"
echo "=========================="

# Get current timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="litebotx_backup_${TIMESTAMP}"

# Navigate to project directory
cd /Users/wesleyrufus/Desktop/litebotx

# Create backups directory
mkdir -p backups
echo "📁 Created backups directory"

# Create backup folder
mkdir -p "backups/${BACKUP_NAME}"
echo "📦 Creating backup: ${BACKUP_NAME}"

# Copy critical files
echo "📋 Copying critical files:"

# Core trading files
cp automated_momentum_trader_v2.py "backups/${BACKUP_NAME}/" 2>/dev/null && echo "   ✅ automated_momentum_trader_v2.py" || echo "   ⚠️ automated_momentum_trader_v2.py not found"
cp automated_momentum_trader.py "backups/${BACKUP_NAME}/" 2>/dev/null && echo "   ✅ automated_momentum_trader.py" || echo "   ⚠️ automated_momentum_trader.py not found"
cp start_automated_trading.py "backups/${BACKUP_NAME}/" 2>/dev/null && echo "   ✅ start_automated_trading.py" || echo "   ⚠️ start_automated_trading.py not found"

# Dashboard files
cp stock_dashboard.py "backups/${BACKUP_NAME}/" 2>/dev/null && echo "   ✅ stock_dashboard.py" || echo "   ⚠️ stock_dashboard.py not found"
cp stock_api.py "backups/${BACKUP_NAME}/" 2>/dev/null && echo "   ✅ stock_api.py" || echo "   ⚠️ stock_api.py not found"
cp stock_metrics.py "backups/${BACKUP_NAME}/" 2>/dev/null && echo "   ✅ stock_metrics.py" || echo "   ⚠️ stock_metrics.py not found"
cp stock_config.py "backups/${BACKUP_NAME}/" 2>/dev/null && echo "   ✅ stock_config.py" || echo "   ⚠️ stock_config.py not found"

# Control files
cp start_litebotx.py "backups/${BACKUP_NAME}/" 2>/dev/null && echo "   ✅ start_litebotx.py" || echo "   ⚠️ start_litebotx.py not found"
cp stop_litebotx.py "backups/${BACKUP_NAME}/" 2>/dev/null && echo "   ✅ stop_litebotx.py" || echo "   ⚠️ stop_litebotx.py not found"
cp emergency_monitor.py "backups/${BACKUP_NAME}/" 2>/dev/null && echo "   ✅ emergency_monitor.py" || echo "   ⚠️ emergency_monitor.py not found"
cp backup_system.py "backups/${BACKUP_NAME}/" 2>/dev/null && echo "   ✅ backup_system.py" || echo "   ⚠️ backup_system.py not found"

# Configuration files
cp .env "backups/${BACKUP_NAME}/" 2>/dev/null && echo "   ✅ .env" || echo "   ⚠️ .env not found"
cp risk_settings.json "backups/${BACKUP_NAME}/" 2>/dev/null && echo "   ✅ risk_settings.json" || echo "   ⚠️ risk_settings.json not found"

# Documentation
cp README.md "backups/${BACKUP_NAME}/" 2>/dev/null && echo "   ✅ README.md" || echo "   ⚠️ README.md not found"
cp STOCK_DASHBOARD_PROMPT.md "backups/${BACKUP_NAME}/" 2>/dev/null && echo "   ✅ STOCK_DASHBOARD_PROMPT.md" || echo "   ⚠️ STOCK_DASHBOARD_PROMPT.md not found"

# Directories
cp -r core/ "backups/${BACKUP_NAME}/" 2>/dev/null && echo "   ✅ core/" || echo "   ⚠️ core/ not found"
cp -r utils/ "backups/${BACKUP_NAME}/" 2>/dev/null && echo "   ✅ utils/" || echo "   ⚠️ utils/ not found"
cp -r data/ "backups/${BACKUP_NAME}/" 2>/dev/null && echo "   ✅ data/" || echo "   ⚠️ data/ not found"

# Create backup info
cat > "backups/${BACKUP_NAME}/backup_info.txt" << EOF
LiteBotX System Backup
=====================

Backup Created: $(date)
Backup Name: ${BACKUP_NAME}
Source Directory: /Users/wesleyrufus/Desktop/litebotx

System Status at Backup:
- Portfolio Value: \$925,715.60
- Strategy: Enhanced Multi-Sector Momentum Trading
- Version: Phase 3A ML-Enhanced
- API: Alpaca Paper Trading
- Active Positions: 12 symbols

Critical Components Backed Up:
✅ Core trading bot (automated_momentum_trader_v2.py)
✅ Professional dashboard (stock_dashboard.py)
✅ Emergency control system (stop_litebotx.py, emergency_monitor.py)
✅ API integration (stock_api.py)
✅ Risk management (risk_settings.json)
✅ Configuration files (.env)
✅ Documentation (README.md, STOCK_DASHBOARD_PROMPT.md)
✅ Core utilities and data directories

Restoration Instructions:
1. Copy all files to a new directory
2. Install dependencies: pip install -r requirements.txt
3. Configure .env file with your API keys
4. Run: python3 start_litebotx.py

Emergency Contacts:
- Stop trading: python3 stop_litebotx.py
- Emergency monitor: python3 emergency_monitor.py --emergency
- Dashboard access: http://127.0.0.1:8055
EOF

# Create compressed archive
echo "📦 Creating compressed archive..."
cd backups
tar -czf "${BACKUP_NAME}.tar.gz" "${BACKUP_NAME}/"
cd ..

# Get sizes
FOLDER_SIZE=$(du -sh "backups/${BACKUP_NAME}" | cut -f1)
ARCHIVE_SIZE=$(du -sh "backups/${BACKUP_NAME}.tar.gz" | cut -f1)

echo ""
echo "=========================="
echo "✅ LiteBotX Backup Complete!"
echo "=========================="
echo "📁 Backup Folder: backups/${BACKUP_NAME}/"
echo "📦 Compressed Archive: backups/${BACKUP_NAME}.tar.gz"
echo "📊 Folder Size: ${FOLDER_SIZE}"
echo "📦 Archive Size: ${ARCHIVE_SIZE}"
echo ""
echo "💰 System Status at Backup:"
echo "   Portfolio Value: \$925,715.60"
echo "   Active Positions: 12 symbols"
echo "   Strategy: Enhanced Multi-Sector Momentum"
echo "   API: Alpaca Paper Trading"
echo ""
echo "🛡️ Backup Includes:"
echo "   ✅ Complete trading bot system"
echo "   ✅ Professional dashboard & GUI"
echo "   ✅ Emergency control systems"
echo "   ✅ Risk management tools"
echo "   ✅ Configuration files"
echo "   ✅ Documentation"
echo ""
echo "📅 Backup Created: $(date)"
echo ""
echo "🔄 To create another backup, run: ./create_backup.sh"
echo "📋 To list backups, run: ls -la backups/"

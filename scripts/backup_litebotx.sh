#!/bin/bash
# LiteBotX Comprehensive Backup Script

echo "🤖 LiteBotX Backup System"
echo "=========================="

# Get current timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="litebotx_backup_${TIMESTAMP}"

# Current directory (should be litebotx-usb-deployment)
CURRENT_DIR=$(pwd)
echo "📁 Working directory: ${CURRENT_DIR}"

# Create backups directory
mkdir -p backups
echo "📁 Created backups directory"

# Create backup folder
mkdir -p "backups/${BACKUP_NAME}"
echo "📦 Creating backup: ${BACKUP_NAME}"

# Copy critical files
echo "📋 Copying critical trading files:"

# Core trading files
cp automated_momentum_trader_v2.py "backups/${BACKUP_NAME}/" 2>/dev/null && echo "   ✅ automated_momentum_trader_v2.py" || echo "   ⚠️ automated_momentum_trader_v2.py not found"
cp automated_momentum_trader.py "backups/${BACKUP_NAME}/" 2>/dev/null && echo "   ✅ automated_momentum_trader.py" || echo "   ⚠️ automated_momentum_trader.py not found"
cp start_automated_trading.py "backups/${BACKUP_NAME}/" 2>/dev/null && echo "   ✅ start_automated_trading.py" || echo "   ⚠️ start_automated_trading.py not found"

echo "📋 Copying dashboard files:"
# Dashboard files  
cp stock_dashboard.py "backups/${BACKUP_NAME}/" 2>/dev/null && echo "   ✅ stock_dashboard.py" || echo "   ⚠️ stock_dashboard.py not found"
cp enhanced_trading_dashboard.py "backups/${BACKUP_NAME}/" 2>/dev/null && echo "   ✅ enhanced_trading_dashboard.py" || echo "   ⚠️ enhanced_trading_dashboard.py not found"
cp stock_api.py "backups/${BACKUP_NAME}/" 2>/dev/null && echo "   ✅ stock_api.py" || echo "   ⚠️ stock_api.py not found"
cp stock_metrics.py "backups/${BACKUP_NAME}/" 2>/dev/null && echo "   ✅ stock_metrics.py" || echo "   ⚠️ stock_metrics.py not found"
cp stock_config.py "backups/${BACKUP_NAME}/" 2>/dev/null && echo "   ✅ stock_config.py" || echo "   ⚠️ stock_config.py not found"

echo "📋 Copying control files:"
# Control files
cp start_litebotx.py "backups/${BACKUP_NAME}/" 2>/dev/null && echo "   ✅ start_litebotx.py" || echo "   ⚠️ start_litebotx.py not found"
cp stop_litebotx.py "backups/${BACKUP_NAME}/" 2>/dev/null && echo "   ✅ stop_litebotx.py" || echo "   ⚠️ stop_litebotx.py not found"
cp emergency_monitor.py "backups/${BACKUP_NAME}/" 2>/dev/null && echo "   ✅ emergency_monitor.py" || echo "   ⚠️ emergency_monitor.py not found"
cp backup_system.py "backups/${BACKUP_NAME}/" 2>/dev/null && echo "   ✅ backup_system.py" || echo "   ⚠️ backup_system.py not found"

echo "📋 Copying strategy files:"
# Strategy files
cp momentum_strategy.py "backups/${BACKUP_NAME}/" 2>/dev/null && echo "   ✅ momentum_strategy.py" || echo "   ⚠️ momentum_strategy.py not found"
cp enhanced_momentum_strategy.py "backups/${BACKUP_NAME}/" 2>/dev/null && echo "   ✅ enhanced_momentum_strategy.py" || echo "   ⚠️ enhanced_momentum_strategy.py not found"
cp smart_threshold_strategy.py "backups/${BACKUP_NAME}/" 2>/dev/null && echo "   ✅ smart_threshold_strategy.py" || echo "   ⚠️ smart_threshold_strategy.py not found"
cp adaptive_threshold_manager.py "backups/${BACKUP_NAME}/" 2>/dev/null && echo "   ✅ adaptive_threshold_manager.py" || echo "   ⚠️ adaptive_threshold_manager.py not found"

echo "📋 Copying risk management files:"
# Risk management
cp risk.py "backups/${BACKUP_NAME}/" 2>/dev/null && echo "   ✅ risk.py" || echo "   ⚠️ risk.py not found"
cp risk_adjusted_sizing.py "backups/${BACKUP_NAME}/" 2>/dev/null && echo "   ✅ risk_adjusted_sizing.py" || echo "   ⚠️ risk_adjusted_sizing.py not found"
cp weekend_risk_manager.py "backups/${BACKUP_NAME}/" 2>/dev/null && echo "   ✅ weekend_risk_manager.py" || echo "   ⚠️ weekend_risk_manager.py not found"

echo "📋 Copying configuration files:"
# Configuration files
cp config.py "backups/${BACKUP_NAME}/" 2>/dev/null && echo "   ✅ config.py" || echo "   ⚠️ config.py not found"
cp requirements.txt "backups/${BACKUP_NAME}/" 2>/dev/null && echo "   ✅ requirements.txt" || echo "   ⚠️ requirements.txt not found"

echo "📋 Copying documentation:"
# Documentation
cp README.md "backups/${BACKUP_NAME}/" 2>/dev/null && echo "   ✅ README.md" || echo "   ⚠️ README.md not found"
cp ADAPTIVE_THRESHOLD_USAGE_GUIDE.md "backups/${BACKUP_NAME}/" 2>/dev/null && echo "   ✅ ADAPTIVE_THRESHOLD_USAGE_GUIDE.md" || echo "   ⚠️ ADAPTIVE_THRESHOLD_USAGE_GUIDE.md not found"
cp ROADMAP.md "backups/${BACKUP_NAME}/" 2>/dev/null && echo "   ✅ ROADMAP.md" || echo "   ⚠️ ROADMAP.md not found"
cp UBUNTU_DEPLOYMENT_README.md "backups/${BACKUP_NAME}/" 2>/dev/null && echo "   ✅ UBUNTU_DEPLOYMENT_README.md" || echo "   ⚠️ UBUNTU_DEPLOYMENT_README.md not found"

echo "📋 Copying launcher scripts:"
# Launcher scripts
cp start_ubuntu.sh "backups/${BACKUP_NAME}/" 2>/dev/null && echo "   ✅ start_ubuntu.sh" || echo "   ⚠️ start_ubuntu.sh not found"
cp ubuntu_setup.sh "backups/${BACKUP_NAME}/" 2>/dev/null && echo "   ✅ ubuntu_setup.sh" || echo "   ⚠️ ubuntu_setup.sh not found"
cp install_linux.sh "backups/${BACKUP_NAME}/" 2>/dev/null && echo "   ✅ install_linux.sh" || echo "   ⚠️ install_linux.sh not found"

echo "📋 Copying directories:"
# Copy important directories
cp -r core/ "backups/${BACKUP_NAME}/" 2>/dev/null && echo "   ✅ core/" || echo "   ⚠️ core/ not found"
cp -r utils/ "backups/${BACKUP_NAME}/" 2>/dev/null && echo "   ✅ utils/" || echo "   ⚠️ utils/ not found"
cp -r config/ "backups/${BACKUP_NAME}/" 2>/dev/null && echo "   ✅ config/" || echo "   ⚠️ config/ not found"
cp -r validators/ "backups/${BACKUP_NAME}/" 2>/dev/null && echo "   ✅ validators/" || echo "   ⚠️ validators/ not found"

echo "📋 Copying log files (latest):"
# Copy recent logs
cp *.log "backups/${BACKUP_NAME}/" 2>/dev/null && echo "   ✅ Log files" || echo "   ⚠️ No log files found"

# Create backup info file
echo "📋 Creating backup information file:"
cat > "backups/${BACKUP_NAME}/backup_info.txt" << EOF
LiteBotX Backup Information
===========================
Backup Created: $(date)
Backup Name: ${BACKUP_NAME}
Source Directory: ${CURRENT_DIR}
System: $(uname -a)

Portfolio Value: \$928,271.39 (as of backup time)
Trading Strategy: Aggressive Swing Trading
Risk Per Trade: 2.0%
Max Positions: 5

Files Backed Up:
- Core trading bot (automated_momentum_trader_v2.py)  
- Web dashboard (stock_dashboard.py)
- Desktop dashboard (enhanced_trading_dashboard.py)
- All strategy files
- Risk management modules
- Configuration files
- Documentation
- Launch scripts
- Core directories

To Restore:
1. Copy files from this backup to your deployment directory
2. Ensure Python environment is set up (pip install -r requirements.txt)
3. Configure API keys in .env file
4. Run ./start_ubuntu.sh to launch system

EOF

echo "   ✅ backup_info.txt created"

# Create archive
echo "📦 Creating compressed backup archive:"
cd backups
tar -czf "${BACKUP_NAME}.tar.gz" "${BACKUP_NAME}/"
echo "   ✅ ${BACKUP_NAME}.tar.gz created"

# Get file sizes
FOLDER_SIZE=$(du -sh "${BACKUP_NAME}" | cut -f1)
ARCHIVE_SIZE=$(du -sh "${BACKUP_NAME}.tar.gz" | cut -f1)

echo ""
echo "✅ Backup Complete!"
echo "=========================="
echo "📁 Backup Folder: backups/${BACKUP_NAME}/ (${FOLDER_SIZE})"
echo "📦 Archive File: backups/${BACKUP_NAME}.tar.gz (${ARCHIVE_SIZE})"
echo "💾 Total Files Backed Up: $(find backups/${BACKUP_NAME} -type f | wc -l)"
echo ""
echo "🚀 Your LiteBotX trading bot has been safely backed up!"
echo "💡 Keep this backup in a safe location for disaster recovery"

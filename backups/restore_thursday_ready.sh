#!/bin/bash
# 🚀 LiteBotX Thursday Ready Backup Restore Script
# Created: September 23, 2025
# Restores the Thursday autonomous trading system with all enhancements

echo "🚀 LiteBotX Thursday Ready System Restore"
echo "========================================"

BACKUP_FILE="litebotx_thursday_ready_backup_20250923_164105.tar.gz"
BACKUP_PATH="/home/wes/Desktop/litebotx-usb-deployment/backups/$BACKUP_FILE"

# Check if backup file exists
if [ ! -f "$BACKUP_PATH" ]; then
    echo "❌ Error: Backup file not found at $BACKUP_PATH"
    exit 1
fi

echo "📋 Backup file found: $BACKUP_FILE (118MB)"
echo "📅 Contains Thursday autonomous trading enhancements:"
echo "   • NoneType error fixes"
echo "   • Early watchlist refresh (5 PM ET)"
echo "   • Position diversification controls"
echo "   • Smart D+1 exit logic"

read -p "🤔 Do you want to restore this backup? This will replace current files. (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Restore cancelled."
    exit 0
fi

echo "🔄 Starting restore process..."

# Create backup of current state before restore
CURRENT_BACKUP="current_state_before_restore_$(date +%Y%m%d_%H%M%S).tar.gz"
echo "💾 Creating backup of current state: $CURRENT_BACKUP"
cd /home/wes/Desktop
tar -czf "litebotx-usb-deployment/backups/$CURRENT_BACKUP" \
    --exclude='litebotx-usb-deployment/backups' \
    --exclude='litebotx-usb-deployment/litebotx_env' \
    --exclude='litebotx-usb-deployment/__pycache__' \
    --exclude='litebotx-usb-deployment/*/__pycache__' \
    --exclude='litebotx-usb-deployment/logs/*.log' \
    --exclude='litebotx-usb-deployment/*.log' \
    --exclude='litebotx-usb-deployment/cache' \
    litebotx-usb-deployment/ 2>/dev/null

# Extract the backup
echo "📦 Extracting Thursday ready backup..."
cd /home/wes/Desktop
tar -xzf "$BACKUP_PATH"

echo "✅ Restore completed successfully!"
echo ""
echo "🎯 System Status: THURSDAY AUTONOMOUS TRADING READY"
echo "   • NoneType crashes prevented"
echo "   • Early watchlist refresh active (5 PM ET)" 
echo "   • Diversification controls enabled"
echo "   • Smart D+1 exits configured"
echo ""
echo "🚀 To start the bot:"
echo "   cd /home/wes/Desktop/litebotx-usb-deployment"
echo "   python3 start_litebotx.py"
echo ""
echo "📚 See THURSDAY_READY_BACKUP_README.md for full details"
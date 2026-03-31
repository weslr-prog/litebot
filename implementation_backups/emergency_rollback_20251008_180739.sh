#!/bin/bash
# Emergency Rollback Script
# Generated: 20251008_180739
# Restores system to pre-implementation state

echo "🔄 Starting emergency rollback..."
echo "Backup from: 20251008_180739"

BACKUP_DIR="/home/wes/Desktop/litebotx-usb-deployment/implementation_backups/pre_implementation_backup_20251008_180739"
BASE_DIR="/home/wes/Desktop/litebotx-usb-deployment"

if [ ! -d "$BACKUP_DIR" ]; then
    echo "❌ Backup directory not found: $BACKUP_DIR"
    exit 1
fi

echo "Restoring files..."
cp "$BACKUP_DIR/signal_generator.py" "$BASE_DIR/signal_generator.py"
echo "✅ Restored: signal_generator.py"
cp "$BACKUP_DIR/trade_executor.py" "$BASE_DIR/trade_executor.py"
echo "✅ Restored: trade_executor.py"
cp "$BACKUP_DIR/execution_engine.py" "$BASE_DIR/execution_engine.py"
echo "✅ Restored: execution_engine.py"
cp "$BACKUP_DIR/config.py" "$BASE_DIR/config.py"
echo "✅ Restored: config.py"
cp "$BACKUP_DIR/positions.json" "$BASE_DIR/positions.json"
echo "✅ Restored: positions.json"
cp "$BACKUP_DIR/strategic_improvements.py" "$BASE_DIR/strategic_improvements.py"
echo "✅ Restored: strategic_improvements.py"
cp "$BACKUP_DIR/traders/short_cycle_trader.py" "$BASE_DIR/traders/short_cycle_trader.py"
echo "✅ Restored: traders/short_cycle_trader.py"

echo "🔄 Rollback completed!"
echo "⚠️  Please restart the trading system to ensure changes take effect"
echo "📝 Check logs for any issues during rollback"

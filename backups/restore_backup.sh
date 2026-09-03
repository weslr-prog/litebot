#!/bin/bash
# LiteBotX Restoration Script
# Use this script to restore from backup

echo "🤖 LiteBotX Restoration Script"
echo "============================="

if [ $# -eq 0 ]; then
    echo "Usage: $0 <backup_folder_path>"
    echo "Example: $0 /path/to/backups/litebotx_alpaca_py_backup_20250902_155307"
    exit 1
fi

BACKUP_PATH="$1"
RESTORE_DIR="./litebotx_restored_$(date +%Y%m%d_%H%M%S)"

echo "📦 Backup source: $BACKUP_PATH"
echo "📁 Restore target: $RESTORE_DIR"

# Check if backup exists
if [ ! -d "$BACKUP_PATH" ]; then
    echo "❌ Backup folder not found: $BACKUP_PATH"
    exit 1
fi

# Create restoration directory
mkdir -p "$RESTORE_DIR"
echo "✅ Created restoration directory"

# Copy all files
echo "📋 Copying files from backup..."
cp -r "$BACKUP_PATH"/* "$RESTORE_DIR"/
echo "✅ Files copied successfully"

# Navigate to restored directory
cd "$RESTORE_DIR"

# Create virtual environment
echo "🐍 Creating virtual environment..."
python3 -m venv litebotx_env
echo "✅ Virtual environment created"

# Activate and install packages
echo "📦 Installing packages..."
source litebotx_env/bin/activate
pip install --upgrade pip

# Install from requirements if it exists
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    echo "✅ Installed packages from requirements.txt"
fi

# Install key packages for alpaca-py setup
pip install alpaca-py>=0.42.1
pip install yfinance>=0.2.65
pip install "websockets>=15.0"
echo "✅ Installed core packages"

# Create .env from template if needed
if [ -f ".env.template" ] && [ ! -f ".env" ]; then
    cp .env.template .env
    echo "✅ Created .env from template"
    echo "⚠️  IMPORTANT: Edit .env file with your API keys!"
fi

echo ""
echo "🎉 RESTORATION COMPLETED!"
echo "========================="
echo "📁 System restored to: $(pwd)"
echo "🔧 Virtual environment: $(pwd)/litebotx_env"
echo ""
echo "📋 Next steps:"
echo "1. Edit .env file with your API keys"
echo "2. Activate environment: source litebotx_env/bin/activate"
echo "3. Test the system: python start_litebotx.py"
echo ""
echo "📚 See backup_info.txt for detailed instructions"

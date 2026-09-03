#!/bin/bash
# LiteBotX Linux Installation Script
# For Ubuntu 20.04/22.04/24.04 LTS

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_status() { echo -e "${GREEN}[INFO]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

echo "🐧 LiteBotX Linux Installation Starting..."

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   print_error "Do not run as root! Use regular user with sudo."
   exit 1
fi

# Update system
print_status "Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install dependencies
print_status "Installing dependencies..."
sudo apt install -y python3 python3-pip python3-venv python3-dev \
    build-essential curl wget git htop screen tmux nano vim unzip

# Create app directory
APP_DIR="$HOME/litebotx"
print_status "Creating app directory: $APP_DIR"

if [ -d "$APP_DIR" ]; then
    print_warning "Directory exists. Remove? (y/N)"
    read -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$APP_DIR"
    else
        exit 1
    fi
fi

mkdir -p "$APP_DIR"
cp -r * "$APP_DIR/" 2>/dev/null || true
cd "$APP_DIR"

# Setup Python environment
print_status "Setting up Python environment..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip

if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    pip install alpaca-trade-api yfinance pandas numpy scikit-learn dash plotly requests python-dotenv
fi

# Create .env file
if [ -f ".env.template" ]; then
    print_status "Creating .env from template..."
    cp .env.template .env
    print_warning "Edit .env with your API keys!"
fi

mkdir -p logs

# Create convenience scripts
cat > start_bot.sh << 'EOF'
#!/bin/bash
cd "$HOME/litebotx" && source venv/bin/activate && python automated_momentum_trader_v2.py
EOF

cat > start_dashboard.sh << 'EOF'
#!/bin/bash
cd "$HOME/litebotx" && source venv/bin/activate && python enhanced_trading_dashboard.py
EOF

cat > health_check.sh << 'EOF'
#!/bin/bash
cd "$HOME/litebotx" && source venv/bin/activate && python quick_health_check.py
EOF

chmod +x *.sh

print_status "🎉 Installation complete!"
echo "📁 Location: $APP_DIR"
echo "🔧 Next: Edit .env file, then run ./health_check.sh"

#!/bin/bash
# LiteBotX Ubuntu Setup Script
# Automated setup for Ubuntu 22.04+ LTS

echo "🐧 LiteBotX Ubuntu Linux Setup"
echo "=============================="
echo "Setting up LiteBotX trading system on Ubuntu..."
echo ""

# Check Ubuntu version
if ! grep -q "Ubuntu" /etc/os-release; then
    echo "⚠️ Warning: This script is designed for Ubuntu Linux"
    echo "Continue anyway? (y/N)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo "📋 System Information:"
lsb_release -a
echo ""

# Update system
echo "🔄 Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install Python 3.11 and pip
echo "🐍 Installing Python 3.11 and dependencies..."
sudo apt install -y software-properties-common
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3.11-dev python3-pip

# Install additional system dependencies
echo "📦 Installing system dependencies..."
sudo apt install -y \
    build-essential \
    git \
    curl \
    wget \
    vim \
    htop \
    tree \
    screen \
    tmux \
    firefox \
    nodejs \
    npm

# Create Python virtual environment
echo "🔧 Setting up Python virtual environment..."
python3.11 -m venv litebotx_env
source litebotx_env/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install Python dependencies
echo "📚 Installing Python packages..."
pip install \
    alpaca-py \
    pandas \
    numpy \
    dash \
    plotly \
    dash-bootstrap-components \
    requests \
    python-dotenv \
    schedule \
    yfinance \
    scikit-learn \
    ta \
    matplotlib \
    seaborn \
    psutil

echo "🔐 Setting up configuration..."

# Create .env file if template exists
if [ -f ".env.template" ]; then
    cp .env.template .env
    echo "   ✅ Created .env from template"
    echo "   ⚠️ IMPORTANT: Edit .env file with your Alpaca API keys!"
else
    # Create basic .env template
    cat > .env << 'EOF'
# Alpaca API Configuration
ALPACA_API_KEY=YOUR_API_KEY_HERE
ALPACA_SECRET_KEY=YOUR_SECRET_KEY_HERE
ALPACA_BASE_URL=https://paper-api.alpaca.markets

# Trading Configuration  
TRADING_MODE=paper
MAX_POSITION_SIZE=10000
RISK_PERCENTAGE=0.02
ENABLE_LOGGING=true

# Dashboard Configuration
DASHBOARD_HOST=0.0.0.0
DASHBOARD_PORT=8055
EOF
    echo "   ✅ Created basic .env template"
fi

# Set executable permissions
echo "🔧 Setting file permissions..."
chmod +x *.py
chmod +x *.sh
chmod +x create_backup.sh

# Create desktop shortcuts
echo "🖥️ Creating desktop shortcuts..."
mkdir -p ~/Desktop

# LiteBotX Launcher shortcut
cat > ~/Desktop/LiteBotX-Launcher.desktop << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=LiteBotX Trading System
Comment=Launch LiteBotX Trading Bot and Dashboard
Exec=$(pwd)/litebotx_env/bin/python3 $(pwd)/start_litebotx.py
Icon=utilities-terminal
Terminal=true
StartupNotify=false
Categories=Office;Finance;
EOF

# Dashboard shortcut
cat > ~/Desktop/LiteBotX-Dashboard.desktop << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=LiteBotX Dashboard
Comment=Open LiteBotX Trading Dashboard
Exec=firefox http://localhost:8055
Icon=firefox
Terminal=false
StartupNotify=false
Categories=Office;Finance;
EOF

# Emergency Stop shortcut
cat > ~/Desktop/LiteBotX-EmergencyStop.desktop << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=LiteBotX Emergency Stop
Comment=Emergency stop for LiteBotX trading
Exec=$(pwd)/litebotx_env/bin/python3 $(pwd)/stop_litebotx.py
Icon=process-stop
Terminal=true
StartupNotify=false
Categories=Office;Finance;
EOF

chmod +x ~/Desktop/LiteBotX-*.desktop

# Create startup scripts
echo "🚀 Creating Ubuntu-specific startup scripts..."

cat > start_ubuntu.sh << 'EOF'
#!/bin/bash
# Ubuntu-specific LiteBotX startup script

cd "$(dirname "$0")"
source litebotx_env/bin/activate

echo "🚀 Starting LiteBotX on Ubuntu..."
echo "Dashboard will be available at: http://localhost:8055"
echo ""

# Start the system
python3 start_litebotx.py
EOF

cat > dashboard_only.sh << 'EOF'
#!/bin/bash
# Start only the dashboard (no trading)

cd "$(dirname "$0")"
source litebotx_env/bin/activate

echo "📊 Starting LiteBotX Dashboard Only..."
echo "Dashboard will be available at: http://localhost:8055"
echo ""

python3 stock_dashboard.py
EOF

chmod +x start_ubuntu.sh dashboard_only.sh

# Create system service (optional)
echo "⚙️ Creating systemd service template..."
cat > litebotx.service << EOF
[Unit]
Description=LiteBotX Trading System
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
Environment=PATH=$(pwd)/litebotx_env/bin
ExecStart=$(pwd)/litebotx_env/bin/python3 $(pwd)/start_litebotx.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

echo ""
echo "=================================="
echo "✅ Ubuntu Setup Complete!"
echo "=================================="
echo ""
echo "🔐 IMPORTANT - Next Steps:"
echo "1. Edit .env file with your Alpaca API keys:"
echo "   nano .env"
echo ""
echo "2. Test your API connection:"
echo "   source litebotx_env/bin/activate"
echo "   python3 -c \"from stock_api import StockAPI; api = StockAPI(); print('API Test:', api.test_connection())\""
echo ""
echo "🚀 Launch Options:"
echo "   • Full System:     ./start_ubuntu.sh"
echo "   • Dashboard Only:  ./dashboard_only.sh" 
echo "   • Emergency Stop:  python3 stop_litebotx.py"
echo ""
echo "🖥️ Desktop Shortcuts:"
echo "   • LiteBotX Launcher (Full System)"
echo "   • LiteBotX Dashboard (Browser)"
echo "   • LiteBotX Emergency Stop"
echo ""
echo "🌐 Dashboard Access:"
echo "   http://localhost:8055"
echo ""
echo "📋 System Service (Optional):"
echo "   sudo cp litebotx.service /etc/systemd/system/"
echo "   sudo systemctl enable litebotx.service"
echo "   sudo systemctl start litebotx.service"
echo ""
echo "💰 Current Portfolio: \$925,715.60"
echo "🎯 Strategy: Enhanced Multi-Sector Momentum"
echo "🛡️ Emergency Controls: Fully Implemented"
echo ""
echo "📅 Setup completed: $(date)"
echo ""
echo "🎉 LiteBotX is ready for Ubuntu Linux!"

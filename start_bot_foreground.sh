#!/bin/bash
################################################################################
# Start LiteBotX V2 in FOREGROUND (visible terminal output)
# Press Ctrl+C to stop
################################################################################

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo ""
echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                                                              ║${NC}"
echo -e "${BLUE}║             LiteBotX V2 - Foreground Mode                    ║${NC}"
echo -e "${BLUE}║                                                              ║${NC}"
echo -e "${BLUE}║  Strategy: D+1 Mean Reversion RSI                            ║${NC}"
echo -e "${BLUE}║  Mode: Paper Trading                                         ║${NC}"
echo -e "${BLUE}║  Output: Terminal (visible)                                  ║${NC}"
echo -e "${BLUE}║                                                              ║${NC}"
echo -e "${BLUE}║  🛡️  Anti-Churning Safeguards Active:                        ║${NC}"
echo -e "${BLUE}║     • No duplicate entries (5 min window)                   ║${NC}"
echo -e "${BLUE}║     • 30 min minimum hold time                              ║${NC}"
echo -e "${BLUE}║     • 60 min re-entry cooldown                              ║${NC}"
echo -e "${BLUE}║                                                              ║${NC}"
echo -e "${BLUE}║  Press Ctrl+C to stop                                        ║${NC}"
echo -e "${BLUE}║                                                              ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Change to project directory
cd "$(dirname "$0")"

# Check if virtual environment exists
if [ ! -d "litebotx_env" ]; then
    echo -e "${RED}❌ ERROR: Virtual environment not found${NC}"
    echo -e "${YELLOW}   Run: python3 -m venv litebotx_env${NC}"
    echo -e "${YELLOW}   Then: source litebotx_env/bin/activate && pip install -r requirements.txt${NC}"
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo -e "${RED}❌ ERROR: .env file not found${NC}"
    echo -e "${YELLOW}   Copy .env.template to .env and add your Alpaca keys${NC}"
    exit 1
fi

# Load environment variables
echo -e "${BLUE}🔑 Loading environment variables...${NC}"
export $(grep -v '^#' .env | xargs)

# Check required environment variables
if [ -z "$APCA_API_KEY_ID" ] || [ -z "$APCA_API_SECRET_KEY" ]; then
    echo -e "${RED}❌ ERROR: Alpaca API credentials not found in .env${NC}"
    echo -e "${YELLOW}   Add APCA_API_KEY_ID and APCA_API_SECRET_KEY to .env file${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Environment loaded${NC}"
echo ""

# Kill any existing bot processes
echo -e "${BLUE}🔍 Checking for existing bot processes...${NC}"
if pgrep -f "bot_v2.launcher" > /dev/null; then
    echo -e "${YELLOW}⚠️  Found existing bot process, stopping it...${NC}"
    pkill -f "bot_v2.launcher"
    sleep 2
    echo -e "${GREEN}✅ Previous bot stopped${NC}"
else
    echo -e "${GREEN}✅ No existing bot found${NC}"
fi
echo ""

# Start bot
echo -e "${GREEN}🚀 Starting LiteBotX V2...${NC}"
echo -e "${YELLOW}   Logs also saved to: logs/sprint1_alpaca.log${NC}"
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

# Run in foreground using virtual environment Python
# Tee output to both terminal and log file
litebotx_env/bin/python3 -m bot_v2.launcher 2>&1 | tee -a logs/sprint1_alpaca.log

# If we get here, bot was stopped
echo ""
echo -e "${YELLOW}Bot stopped${NC}"

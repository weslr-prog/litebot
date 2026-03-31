#!/bin/bash
################################################################################
# bot_v2 Clean Runtime Launcher
# Launches the rebuilt modular runtime entrypoint.
################################################################################

set -e  # Exit on error

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                                                              ║${NC}"
echo -e "${BLUE}║              bot_v2 CLEAN RUNTIME - Paper Trading            ║${NC}"
echo -e "${BLUE}║                                                              ║${NC}"
echo -e "${BLUE}║  Runtime: Modular launcher facade over current bot_v2        ║${NC}"
echo -e "${BLUE}║  Focus: Preserve behavior with cleaner startup surface       ║${NC}"
echo -e "${BLUE}║  Validation: Focused regression tests before launch          ║${NC}"
echo -e "${BLUE}║                                                              ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if we're in the right directory
if [ ! -f "bot_v2/main.py" ]; then
    echo -e "${RED}❌ ERROR: Must run from litebotx-usb-deployment directory${NC}"
    echo -e "${YELLOW}   Try: cd /home/wes/Desktop/litebotx-usb-deployment${NC}"
    exit 1
fi

# Check Python environment
echo -e "${BLUE}🔍 Checking Python environment...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ ERROR: Python 3 not found${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Python found: $(python3 --version)${NC}"

# Check required files
echo ""
echo -e "${BLUE}🔍 Checking bot_v2 components...${NC}"

required_files=(
    "bot_v2/main.py"
    "bot_v2/launcher.py"
    "bot_v2/runtime/cli.py"
    "data_loader.py"
    ".env"
)

for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}✅ $file${NC}"
    else
        echo -e "${RED}❌ MISSING: $file${NC}"
        exit 1
    fi
done

# Check Alpaca credentials
echo ""
echo -e "${BLUE}🔍 Checking Alpaca credentials...${NC}"
if [ -z "$APCA_API_KEY_ID" ] || [ -z "$APCA_API_SECRET_KEY" ]; then
    echo -e "${YELLOW}⚠️  WARNING: Alpaca credentials not exported in shell${NC}"
    echo -e "${YELLOW}   Runtime will attempt to load them from .env${NC}"
else
    echo -e "${GREEN}✅ Alpaca credentials set in environment${NC}"
fi

# Show configuration
echo ""
echo -e "${BLUE}📊 Configuration Summary${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}Entry Surface:${NC}  python3 -m bot_v2.main"
echo -e "${GREEN}Default Mode:${NC}   launcher"
echo -e "${GREEN}Broker Mode:${NC}    paper (unless overridden)"
echo -e "${GREEN}Validation:${NC}     config + risk + observability tests"
echo -e "${GREEN}Dry Run:${NC}        prints resolved startup summary"
echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"

# Run test before starting
echo ""
echo -e "${BLUE}🧪 Running focused regression tests...${NC}"
python3 -m pytest tests/bot_v2/test_config.py tests/bot_v2/test_risk_management.py tests/bot_v2/test_phase_a_observability.py tests/bot_v2/test_runtime_cli.py -q

if [ $? -ne 0 ]; then
    echo ""
    echo -e "${RED}❌ Regression tests FAILED${NC}"
    echo -e "${YELLOW}   Please check configuration and try again${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}✅ All tests passed!${NC}"
echo ""

# Countdown
echo -e "${YELLOW}Starting bot_v2 in:${NC}"
for i in 3 2 1; do
    echo -e "${YELLOW}   $i...${NC}"
    sleep 1
done

echo ""
echo -e "${GREEN}🚀 LAUNCHING bot_v2 clean runtime...${NC}"
echo ""
echo -e "${BLUE}Dry Run:${NC} python3 -m bot_v2.main launcher --paper --dry-run"
python3 -m bot_v2.main launcher --paper --dry-run
echo ""
echo -e "${BLUE}Command:${NC} python3 -m bot_v2.main launcher --paper"
echo ""
python3 -m bot_v2.main launcher --paper

# Instructions
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}Next Steps:${NC}"
echo -e "  1. Use ${GREEN}python3 -m bot_v2.main launcher --paper --dry-run${NC} for startup verification"
echo -e "  2. Use ${GREEN}python3 -m bot_v2.main daily-engine${NC} for one-shot daily cycles"
echo -e "  3. Use ${GREEN}python3 -m bot_v2.main continuous-engine${NC} for legacy continuous engine mode"
echo -e "  4. Review ${GREEN}bot_v2/data/daily_stats.json${NC} and ${GREEN}positions.json${NC} after each session"
echo -e "  5. Re-run focused tests after config or risk changes"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

exit 0

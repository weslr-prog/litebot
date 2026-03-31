#!/bin/bash
#
# Setup Cron Job for Daily Universe Refresh
# Installs a cron job to run daily_refresh.sh at 8:00 AM ET every weekday
#
# Usage: ./scripts/setup_daily_refresh_cron.sh
#

set -e

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}======================================================================${NC}"
echo -e "${BLUE}Daily Universe Refresh - Cron Setup${NC}"
echo -e "${BLUE}======================================================================${NC}"

# Get absolute path to script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
DAILY_REFRESH_SCRIPT="${SCRIPT_DIR}/daily_refresh.sh"

# Verify script exists
if [ ! -f "$DAILY_REFRESH_SCRIPT" ]; then
    echo -e "${YELLOW}ERROR: daily_refresh.sh not found at: ${DAILY_REFRESH_SCRIPT}${NC}"
    exit 1
fi

# Verify script is executable
if [ ! -x "$DAILY_REFRESH_SCRIPT" ]; then
    echo -e "${YELLOW}Making daily_refresh.sh executable...${NC}"
    chmod +x "$DAILY_REFRESH_SCRIPT"
fi

echo -e "${GREEN}Script found: ${DAILY_REFRESH_SCRIPT}${NC}"

# Cron job specification
# Run at 8:00 AM ET, Monday-Friday (1-5)
CRON_TIME="0 8 * * 1-5"
CRON_COMMAND="${DAILY_REFRESH_SCRIPT}"
CRON_JOB="${CRON_TIME} ${CRON_COMMAND}"

echo ""
echo -e "${BLUE}Cron Job Configuration:${NC}"
echo -e "  Schedule: ${YELLOW}Every weekday at 8:00 AM ET${NC}"
echo -e "  Command:  ${YELLOW}${CRON_COMMAND}${NC}"
echo -e "  Full Job: ${YELLOW}${CRON_JOB}${NC}"
echo ""

# Check if cron job already exists
EXISTING_CRON=$(crontab -l 2>/dev/null | grep -F "$DAILY_REFRESH_SCRIPT" || true)

if [ -n "$EXISTING_CRON" ]; then
    echo -e "${YELLOW}Existing cron job found:${NC}"
    echo "  $EXISTING_CRON"
    echo ""
    read -p "Remove existing cron job and install new one? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}Installation cancelled.${NC}"
        exit 0
    fi
    
    # Remove existing cron job
    (crontab -l 2>/dev/null | grep -v -F "$DAILY_REFRESH_SCRIPT") | crontab -
    echo -e "${GREEN}✓ Removed existing cron job${NC}"
fi

# Install new cron job
echo -e "${BLUE}Installing cron job...${NC}"
(crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -

# Verify installation
if crontab -l 2>/dev/null | grep -F "$DAILY_REFRESH_SCRIPT" > /dev/null; then
    echo -e "${GREEN}✓ Cron job installed successfully!${NC}"
    echo ""
    echo -e "${BLUE}Current crontab:${NC}"
    crontab -l | grep -F "$DAILY_REFRESH_SCRIPT"
    echo ""
    
    # Show next run times
    echo -e "${BLUE}Next scheduled runs (8:00 AM ET, weekdays only):${NC}"
    
    # Calculate next 5 weekday runs
    for i in {1..10}; do
        NEXT_DATE=$(date -d "+${i} days" '+%Y-%m-%d %A')
        DAY_OF_WEEK=$(date -d "+${i} days" '+%u')
        
        # Only show weekdays (1-5)
        if [ "$DAY_OF_WEEK" -le 5 ]; then
            echo "  📅 ${NEXT_DATE} at 08:00 AM ET"
        fi
    done | head -5
    
    echo ""
    echo -e "${GREEN}======================================================================${NC}"
    echo -e "${GREEN}Setup Complete!${NC}"
    echo -e "${GREEN}======================================================================${NC}"
    echo ""
    echo -e "${BLUE}Commands:${NC}"
    echo -e "  View cron jobs:   ${YELLOW}crontab -l${NC}"
    echo -e "  Remove cron job:  ${YELLOW}crontab -e${NC} (then delete the line)"
    echo -e "  Test manually:    ${YELLOW}${DAILY_REFRESH_SCRIPT}${NC}"
    echo -e "  View logs:        ${YELLOW}ls -lt ${PROJECT_DIR}/logs/universe_refresh_*.log${NC}"
    echo ""
else
    echo -e "${YELLOW}ERROR: Failed to install cron job${NC}"
    exit 1
fi

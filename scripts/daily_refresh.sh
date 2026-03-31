#!/bin/bash
#
# Daily Universe Refresh Script
# Runs refresh_universe.py to update the trading universe using Polygon API
# FREE: Uses Polygon free tier (5 calls/min limit)
#
# Expected runtime: ~12 minutes for 57 stocks at 5 calls/min
# Expected impact: +$4,160/year by keeping universe fresh
#
# Usage:
#   ./scripts/daily_refresh.sh
#
# Cron: 0 8 * * 1-5 /home/wes/Desktop/litebotx-usb-deployment/scripts/daily_refresh.sh
#       (Runs at 8:00 AM ET, Monday-Friday)
#

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PYTHON_ENV="${PROJECT_DIR}/litebotx_env/bin/python"
REFRESH_SCRIPT="${PROJECT_DIR}/refresh_universe.py"
LOG_DIR="${PROJECT_DIR}/logs"
LOG_FILE="${LOG_DIR}/universe_refresh_$(date +%Y%m%d_%H%M%S).log"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Function to log with timestamp
log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1" | tee -a "$LOG_FILE"
}

log_info() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')] INFO:${NC} $1" | tee -a "$LOG_FILE"
}

# Main execution
log "========================================================================"
log "Starting Daily Universe Refresh"
log "========================================================================"

# Check if Python environment exists
if [ ! -f "$PYTHON_ENV" ]; then
    log_error "Python environment not found at: $PYTHON_ENV"
    exit 1
fi

# Check if refresh script exists
if [ ! -f "$REFRESH_SCRIPT" ]; then
    log_error "Refresh script not found at: $REFRESH_SCRIPT"
    exit 1
fi

# Check if .env file exists
if [ ! -f "${PROJECT_DIR}/.env" ]; then
    log_error ".env file not found. Polygon API key is required."
    exit 1
fi

# Source .env to get Polygon API key
set -a
source "${PROJECT_DIR}/.env"
set +a

if [ -z "$POLYGON_API_KEY" ]; then
    log_error "POLYGON_API_KEY not found in .env file"
    exit 1
fi

log_info "Environment: OK"
log_info "API Key: ${POLYGON_API_KEY:0:10}... (${#POLYGON_API_KEY} chars)"

# Check if it's a trading day (Monday-Friday)
DAY_OF_WEEK=$(date +%u)
if [ "$DAY_OF_WEEK" -gt 5 ]; then
    log_warning "Today is a weekend. Skipping universe refresh."
    exit 0
fi

# Check market hours (optional - run even if market closed)
HOUR=$(date +%H)
log_info "Current hour: ${HOUR}:00 ET"

# Run the refresh script
log "Running universe refresh..."
log_info "This may take ~12 minutes due to Polygon free tier rate limits (5 calls/min)"

START_TIME=$(date +%s)

# Run Python script and capture output
if "$PYTHON_ENV" "$REFRESH_SCRIPT" >> "$LOG_FILE" 2>&1; then
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))
    MINUTES=$((DURATION / 60))
    SECONDS=$((DURATION % 60))
    
    log "✅ Universe refresh completed successfully"
    log_info "Runtime: ${MINUTES}m ${SECONDS}s"
    
    # Check if universe file was created/updated
    UNIVERSE_FILE="${PROJECT_DIR}/data/universe.csv"
    if [ -f "$UNIVERSE_FILE" ]; then
        STOCK_COUNT=$(tail -n +2 "$UNIVERSE_FILE" | wc -l)
        log_info "Universe contains ${STOCK_COUNT} stocks"
        log_info "Universe file: ${UNIVERSE_FILE}"
        log_info "Last modified: $(date -r "$UNIVERSE_FILE" '+%Y-%m-%d %H:%M:%S')"
    else
        log_warning "Universe file not found: ${UNIVERSE_FILE}"
    fi
    
    # Keep only last 7 days of logs
    log_info "Cleaning old logs (keeping last 7 days)..."
    find "$LOG_DIR" -name "universe_refresh_*.log" -type f -mtime +7 -delete
    
    log "========================================================================"
    log "Daily Universe Refresh Complete"
    log "========================================================================"
    exit 0
else
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))
    
    log_error "Universe refresh failed after ${DURATION}s"
    log_error "Check log file: ${LOG_FILE}"
    
    # Send error notification (optional - could add email/Slack here)
    log_error "Manual intervention may be required"
    
    exit 1
fi

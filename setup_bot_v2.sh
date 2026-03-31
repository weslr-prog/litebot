#!/bin/bash
# Setup script for bot_v2 refactoring
# Run this to create the clean directory structure

set -e

echo "=================================="
echo "LiteBotX V2 Refactoring Setup"
echo "=================================="
echo ""

# Check we're in the right directory
if [ ! -f "traders/short_cycle_trader.py" ]; then
    echo "❌ Error: Must run from litebotx-usb-deployment directory"
    exit 1
fi

echo "✅ Current directory: $(pwd)"
echo ""

# Create main bot_v2 directory
echo "📁 Creating bot_v2/ directory structure..."
mkdir -p bot_v2

# Create subdirectories
mkdir -p bot_v2/config
mkdir -p bot_v2/models
mkdir -p bot_v2/signal_generation
mkdir -p bot_v2/risk_management
mkdir -p bot_v2/market_analysis
mkdir -p bot_v2/execution
mkdir -p bot_v2/data
mkdir -p bot_v2/portfolio
mkdir -p bot_v2/monitoring
mkdir -p bot_v2/utils
mkdir -p bot_v2/core

# Create test directories
mkdir -p tests/bot_v2/test_models
mkdir -p tests/bot_v2/test_signal_generation
mkdir -p tests/bot_v2/test_risk_management
mkdir -p tests/bot_v2/test_execution
mkdir -p tests/bot_v2/test_integration

# Create __init__.py files
echo "📝 Creating __init__.py files..."
find bot_v2 -type d -exec touch {}/__init__.py \;
find tests/bot_v2 -type d -exec touch {}/__init__.py \;

# Create main entry point
cat > bot_v2/main.py << 'MAIN_EOF'
#!/usr/bin/env python3
"""
LiteBotX V2 - Clean Modular Trading Bot
Entry point for the refactored trading system
"""

import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def main():
    """Main entry point for bot_v2"""
    print("=" * 80)
    print("LiteBotX V2 - Clean Modular Bot")
    print("=" * 80)
    print()
    print("⚠️  Bot V2 is under construction")
    print("    Use traders/short_cycle_trader.py for production trading")
    print()
    print("Status: Refactoring in progress...")
    print("  ✅ Directory structure created")
    print("  ⏳ Modules being extracted")
    print()
    return 0

if __name__ == "__main__":
    sys.exit(main())
MAIN_EOF

chmod +x bot_v2/main.py

# Create README
cat > bot_v2/README.md << 'README_EOF'
# LiteBotX V2 - Clean Modular Architecture

## ⚠️ Development Status
**This is a refactored version of the trading bot - NOT yet production ready**

Use `traders/short_cycle_trader.py` for actual trading.

## 🎯 Goals
1. **Modularity**: Each file <500 lines, focused single responsibility
2. **Testability**: Unit tests for all modules
3. **Maintainability**: Easy to understand and modify
4. **Functional Equivalence**: Same behavior as original bot

## 📁 Structure

```
bot_v2/
├── main.py                 # Entry point
├── config/                 # Configuration
│   ├── trading_config.py   # ShortCycleConfig
│   └── risk_config.py      # Risk parameters
├── models/                 # Data models
│   ├── signals.py          # AISignal
│   ├── positions.py        # ShortCyclePosition
│   └── enums.py            # TradingDay, PositionStatus
├── signal_generation/      # Signal generation
│   ├── signal_generator.py
│   ├── technical_analyzer.py
│   └── confidence_scorer.py
├── risk_management/        # Risk management
│   ├── stop_loss_manager.py
│   ├── position_sizer.py
│   └── portfolio_risk_manager.py
├── execution/              # Order execution
│   ├── order_manager.py
│   └── exit_manager.py
└── core/                   # Core trading logic
    ├── trading_engine.py
    ├── entry_handler.py
    └── exit_handler.py
```

## 🚀 Quick Start (Developers)

### Run V2 (when ready)
```bash
cd bot_v2
python3 main.py
```

### Run Tests
```bash
pytest tests/bot_v2/
```

### Compare with Original
```bash
python3 scripts/compare_bots.py
```

## 📋 Refactoring Progress

- [x] Directory structure created
- [ ] Data models extracted
- [ ] Config extracted
- [ ] Risk management modules extracted
- [ ] Signal generation refactored
- [ ] Main engine refactored
- [ ] Full test coverage
- [ ] Production validation

## 🔧 Development Guidelines

1. **Never modify `traders/short_cycle_trader.py`**
2. Copy code, don't move it
3. Test after each extraction
4. Keep functional equivalence
5. One module per file
6. Clear naming conventions
README_EOF

# Create example test file
cat > tests/bot_v2/test_models/test_signals.py << 'TEST_EOF'
"""
Unit tests for AISignal model
Example test structure for bot_v2
"""

import pytest
from datetime import datetime
import pytz

# TODO: Uncomment when models/signals.py is created
# from bot_v2.models.signals import AISignal


def test_example():
    """Example test - replace with actual AISignal tests"""
    # TODO: Implement tests for AISignal
    # signal = AISignal(
    #     symbol="AAPL",
    #     action="BUY",
    #     confidence=0.75,
    #     time_horizon_days=1.0,
    #     entry_price=150.0
    # )
    # assert signal.symbol == "AAPL"
    # assert signal.confidence == 0.75
    pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
TEST_EOF

# Create gitignore for bot_v2
cat > bot_v2/.gitignore << 'GIT_EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python

# Testing
.pytest_cache/
.coverage
htmlcov/

# IDE
.vscode/
.idea/
*.swp
*.swo

# Logs
*.log
GIT_EOF

echo ""
echo "=================================="
echo "✅ Setup Complete!"
echo "=================================="
echo ""
echo "Directory structure created:"
tree -L 2 bot_v2/ 2>/dev/null || find bot_v2 -type d | sed 's|[^/]*/| |g'
echo ""
echo "📋 Next Steps:"
echo ""
echo "1. Review the refactoring plan:"
echo "   cat REFACTORING_PLAN.md"
echo ""
echo "2. Start with Phase 1 (Data Models):"
echo "   - Extract AISignal to bot_v2/models/signals.py"
echo "   - Extract ShortCyclePosition to bot_v2/models/positions.py"
echo "   - Extract enums to bot_v2/models/enums.py"
echo ""
echo "3. Run tests:"
echo "   pytest tests/bot_v2/ -v"
echo ""
echo "4. Check example files:"
echo "   - bot_v2/main.py (entry point)"
echo "   - bot_v2/README.md (documentation)"
echo "   - tests/bot_v2/test_models/test_signals.py (example test)"
echo ""
echo "🎯 Weekend Goal: Extract models + config (Phases 1-2)"
echo ""

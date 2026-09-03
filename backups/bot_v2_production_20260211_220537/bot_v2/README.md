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

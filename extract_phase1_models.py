#!/usr/bin/env python3
"""
Phase 1 Extractor: Data Models
Extracts AISignal, ShortCyclePosition, and Enums from old bot to bot_v2
"""

import re
from pathlib import Path

# Read the original file
original_file = Path("traders/short_cycle_trader.py")
with open(original_file) as f:
    content = f.read()

print("=" * 80)
print("PHASE 1: Extracting Data Models")
print("=" * 80)
print()

# ============================================================================
# 1. Extract Enums (TradingDay, PositionStatus)
# ============================================================================
print("1️⃣ Extracting Enums...")

enums_content = '''"""
Data models: Enums
Extracted from traders/short_cycle_trader.py
"""

from enum import Enum


class TradingDay(Enum):
    """Trading day types for short-cycle system"""
    MONDAY = "monday"
    TUESDAY = "tuesday" 
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"  # No new positions, exit only
    WEEKEND = "weekend"  # No trading


class PositionStatus(Enum):
    """Position lifecycle states"""
    PENDING = "pending"
    ENTERED = "entered"
    EXIT_SCHEDULED = "exit_scheduled"
    EXITED = "exited"
    STOPPED_OUT = "stopped_out"
'''

enums_file = Path("bot_v2/models/enums.py")
with open(enums_file, "w") as f:
    f.write(enums_content)
print(f"   ✅ Created: {enums_file}")

# ============================================================================
# 2. Extract AISignal
# ============================================================================
print("2️⃣ Extracting AISignal...")

signals_content = '''"""
Data models: AISignal
Extracted from traders/short_cycle_trader.py
"""

import datetime as dt
import pytz
from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class AISignal:
    """AI-generated trading signal with confidence and parameters"""
    symbol: str
    action: str  # "BUY" or "SELL" or "HOLD"
    confidence: float  # 0.0 to 1.0
    time_horizon_days: float  # Expected hold time
    target_price: Optional[float] = None
    stop_price: Optional[float] = None
    entry_price: Optional[float] = None
    position_size_dollars: Optional[float] = None
    signal_timestamp: dt.datetime = None
    features_used: Dict[str, float] = None  # For explainability
    risk_score: float = 0.5  # Portfolio risk assessment
    
    def __post_init__(self):
        if self.signal_timestamp is None:
            self.signal_timestamp = dt.datetime.now(pytz.UTC)
        if self.features_used is None:
            self.features_used = {}
'''

signals_file = Path("bot_v2/models/signals.py")
with open(signals_file, "w") as f:
    f.write(signals_content)
print(f"   ✅ Created: {signals_file}")

# ============================================================================
# 3. Extract ShortCyclePosition (partial - simplified version)
# ============================================================================
print("3️⃣ Extracting ShortCyclePosition...")

# Extract the full ShortCyclePosition class
position_match = re.search(
    r'(@dataclass\nclass ShortCyclePosition:.*?)(?=\nclass |\n@dataclass\nclass |\Z)',
    content,
    re.DOTALL
)

if position_match:
    position_class = position_match.group(1)
    
    positions_content = f'''"""
Data models: ShortCyclePosition
Extracted from traders/short_cycle_trader.py
"""

import datetime as dt
import pytz
import pandas as pd
from typing import Optional
from dataclasses import dataclass

from bot_v2.models.enums import PositionStatus
from bot_v2.models.signals import AISignal


{position_class}
'''
    
    positions_file = Path("bot_v2/models/positions.py")
    with open(positions_file, "w") as f:
        f.write(positions_content)
    print(f"   ✅ Created: {positions_file}")
else:
    print("   ⚠️  Could not extract ShortCyclePosition automatically")
    print("      Manual extraction required")

# ============================================================================
# 4. Update __init__.py for models
# ============================================================================
print("4️⃣ Updating models/__init__.py...")

models_init = '''"""
Data models package
"""

from bot_v2.models.enums import TradingDay, PositionStatus
from bot_v2.models.signals import AISignal
from bot_v2.models.positions import ShortCyclePosition

__all__ = [
    "TradingDay",
    "PositionStatus",
    "AISignal",
    "ShortCyclePosition",
]
'''

models_init_file = Path("bot_v2/models/__init__.py")
with open(models_init_file, "w") as f:
    f.write(models_init)
print(f"   ✅ Updated: {models_init_file}")

# ============================================================================
# 5. Create test file
# ============================================================================
print("5️⃣ Creating test file...")

test_content = '''"""
Unit tests for data models
"""

import pytest
from datetime import datetime
import pytz

from bot_v2.models.enums import TradingDay, PositionStatus
from bot_v2.models.signals import AISignal


class TestEnums:
    """Test enum types"""
    
    def test_trading_day_enum(self):
        assert TradingDay.MONDAY.value == "monday"
        assert TradingDay.FRIDAY.value == "friday"
    
    def test_position_status_enum(self):
        assert PositionStatus.PENDING.value == "pending"
        assert PositionStatus.EXITED.value == "exited"


class TestAISignal:
    """Test AISignal model"""
    
    def test_signal_creation(self):
        signal = AISignal(
            symbol="AAPL",
            action="BUY",
            confidence=0.75,
            time_horizon_days=1.0,
            entry_price=150.0
        )
        
        assert signal.symbol == "AAPL"
        assert signal.action == "BUY"
        assert signal.confidence == 0.75
        assert signal.entry_price == 150.0
    
    def test_signal_defaults(self):
        signal = AISignal(
            symbol="MSFT",
            action="BUY",
            confidence=0.60,
            time_horizon_days=2.0
        )
        
        # Should auto-set timestamp
        assert signal.signal_timestamp is not None
        assert signal.features_used == {}
        assert signal.risk_score == 0.5
    
    def test_signal_with_features(self):
        signal = AISignal(
            symbol="TSLA",
            action="BUY",
            confidence=0.80,
            time_horizon_days=1.0,
            features_used={"rsi": 65.0, "volume_surge": 1.5}
        )
        
        assert signal.features_used["rsi"] == 65.0
        assert signal.features_used["volume_surge"] == 1.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
'''

test_file = Path("tests/bot_v2/test_models/test_models.py")
with open(test_file, "w") as f:
    f.write(test_content)
print(f"   ✅ Created: {test_file}")

# ============================================================================
# Summary
# ============================================================================
print()
print("=" * 80)
print("✅ PHASE 1 COMPLETE: Data Models Extracted")
print("=" * 80)
print()
print("Files created:")
print("  ✅ bot_v2/models/enums.py")
print("  ✅ bot_v2/models/signals.py")
print("  ✅ bot_v2/models/positions.py")
print("  ✅ bot_v2/models/__init__.py")
print("  ✅ tests/bot_v2/test_models/test_models.py")
print()
print("Next steps:")
print("  1. Run tests: pytest tests/bot_v2/test_models/ -v")
print("  2. Review extracted code for correctness")
print("  3. Move to Phase 2: Extract Config")
print()
print("To test imports:")
print("  python3 -c 'from bot_v2.models import AISignal, ShortCyclePosition; print(\"✅ Imports work!\")'")
print()

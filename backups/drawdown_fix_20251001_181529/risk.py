# Shim to preserve legacy imports like `from risk import RiskManager`
from core.risk import RiskManager

__all__ = ["RiskManager"]

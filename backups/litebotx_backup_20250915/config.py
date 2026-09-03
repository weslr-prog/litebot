# Shim to preserve legacy imports like `from config import Config`
# Re-exports from core.config
from core.config import Sprint1Config, Config, config

__all__ = ["Sprint1Config", "Config", "config"]

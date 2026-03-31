# Shim to preserve legacy imports like `from config import Config`
# Re-exports from core.config
from core.config import Sprint1Config, Config, config

__all__ = ["Sprint1Config", "Config", "config"]

# Intraday config for legacy imports
ENABLE_INTRADAY_ANALYSIS = config.enable_intraday_analysis
MAX_INTRADAY_ANALYSES_PER_DAY = config.max_intraday_analyses_per_day

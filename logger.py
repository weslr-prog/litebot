import logging
import os
from logging.handlers import RotatingFileHandler


def setup_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    log_path = os.environ.get("LITEBOTX_LOG_PATH", "logs/sprint1_alpaca.log")

    logger.setLevel(logging.INFO)
    
    # Prevent propagation to avoid duplicate logs
    logger.propagate = False

    # Ensure logs dir
    os.makedirs(os.path.dirname(log_path), exist_ok=True)

    # File handler (rotating) - logs everything
    fh = RotatingFileHandler(log_path, maxBytes=2_000_000, backupCount=3)
    fh.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    fh.setFormatter(fmt)

    # Console handler - DISABLED for general logs (Dec 29, 2025)
    # When bot runs with nohup and stdout redirected to log file,
    # console handler causes duplicate messages (both file + console go to same file)
    # Only add console handler if running interactively (not redirected)
    # ch = logging.StreamHandler()
    # ch.setLevel(logging.INFO)
    # ch.setFormatter(fmt)
    
    # Error/Warning console handler - ALWAYS ENABLED for visibility
    # Show errors and warnings on stdout for immediate attention
    # even when general logging is redirected to file
    error_console = logging.StreamHandler()
    error_console.setLevel(logging.WARNING)  # WARNING and above (WARNING, ERROR, CRITICAL)
    error_fmt = logging.Formatter("%(levelname)s - %(name)s - %(message)s")
    error_console.setFormatter(error_fmt)

    logger.addHandler(fh)
    logger.addHandler(error_console)  # Show errors/warnings on console
    # logger.addHandler(ch)  # Disabled - causes duplicates with nohup

    logger.info(f"Logger initialized; writing to {log_path}")
    return logger

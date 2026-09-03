import logging
import os
from logging.handlers import RotatingFileHandler

LOG_PATH = os.environ.get("LITEBOTX_LOG_PATH", "logs/sprint1_alpaca.log")


def setup_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    # Ensure logs dir
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

    # File handler (rotating)
    fh = RotatingFileHandler(LOG_PATH, maxBytes=2_000_000, backupCount=3)
    fh.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    fh.setFormatter(fmt)

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)

    logger.addHandler(fh)
    logger.addHandler(ch)

    logger.info(f"Logger initialized; writing to {LOG_PATH}")
    return logger

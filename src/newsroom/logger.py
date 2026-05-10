import logging
from pathlib import Path

LOG_DIR = Path.home() / ".local" / "share" / "newsroom" / "logs"
LOG_FILE = LOG_DIR / "newsroom.log"


def setup_logger(name: str = "newsroom", level: int = logging.INFO) -> logging.Logger:
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:
        handler = logging.FileHandler(LOG_FILE)
        handler.setLevel(level)
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
        logger.addHandler(handler)

    return logger


logger = setup_logger()

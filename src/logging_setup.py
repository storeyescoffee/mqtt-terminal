from __future__ import annotations

import logging
import sys


class ColoredFormatter(logging.Formatter):
    """Colored log formatter"""

    COLORS = {
        "DEBUG": "\033[0;36m",  # Cyan
        "INFO": "\033[0;34m",  # Blue
        "SUCCESS": "\033[0;32m",  # Green
        "WARNING": "\033[1;33m",  # Yellow
        "ERROR": "\033[0;31m",  # Red
        "CRITICAL": "\033[1;31m",  # Bold Red
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        log_color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname_colored = f"{log_color}{record.levelname}{self.RESET}"
        return super().format(record)


def setup_logger(log_file: str, level: int = logging.INFO) -> logging.Logger:
    # Add SUCCESS level
    if not hasattr(logging, "SUCCESS"):
        logging.SUCCESS = 25  # type: ignore[attr-defined]
        logging.addLevelName(logging.SUCCESS, "SUCCESS")  # type: ignore[arg-type]

        def success(self: logging.Logger, message, *args, **kwargs):
            if self.isEnabledFor(logging.SUCCESS):  # type: ignore[attr-defined]
                self._log(logging.SUCCESS, message, args, **kwargs)  # type: ignore[attr-defined]

        logging.Logger.success = success  # type: ignore[assignment]

    logger = logging.getLogger("mqtt_terminal")
    logger.setLevel(level)
    logger.propagate = False

    # Avoid duplicate handlers if main() called twice
    if logger.handlers:
        return logger

    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_formatter = ColoredFormatter(
        fmt="[%(asctime)s] [%(levelname_colored)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(console_formatter)

    # File handler without colors
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        fmt="[%(asctime)s] [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    return logger


#!/usr/bin/env python3
"""A logger that can send a given message to the console, to a file, or
both — chosen per call, not fixed for the whole logger."""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_FORMAT = "%(asctime)s %(levelname)s %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
DEFAULT_LOG_DIR = Path(__file__).parent / "log"


class Logger:
    def __init__(self, name, log_file=None, level=logging.INFO):
        formatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)

        self._console_logger = logging.getLogger(f"{name}.console")
        self._console_logger.setLevel(level)
        self._console_logger.propagate = False
        if not self._console_logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(formatter)
            self._console_logger.addHandler(handler)

        if log_file is None:
            DEFAULT_LOG_DIR.mkdir(exist_ok=True)
            log_file = DEFAULT_LOG_DIR / f"{name}.log"

        self._file_logger = logging.getLogger(f"{name}.file")
        self._file_logger.setLevel(level)
        self._file_logger.propagate = False
        if not self._file_logger.handlers:
            handler = RotatingFileHandler(log_file, maxBytes=1_000_000, backupCount=5)
            handler.setFormatter(formatter)
            self._file_logger.addHandler(handler)

    def log(self, message, level=logging.INFO, console=True, file=True):
        if console:
            self._console_logger.log(level, message)
        if file:
            self._file_logger.log(level, message)

    def debug(self, message, console=True, file=True):
        self.log(message, logging.DEBUG, console, file)

    def info(self, message, console=True, file=True):
        self.log(message, logging.INFO, console, file)

    def warning(self, message, console=True, file=True):
        self.log(message, logging.WARNING, console, file)

    def error(self, message, console=True, file=True):
        self.log(message, logging.ERROR, console, file)


if __name__ == "__main__":
    logger = Logger("test")
    logger.info("Sent to both console and file.")
    logger.info("Console only.", file=False)
    logger.info("File only.", console=False)

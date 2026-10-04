#!/usr/bin/env python3
"""Launch and later stop a command line process, on macOS, with its
output captured to a log file.

Launches by running the command directly (not through an indirect
launcher like `open`), so the process handle always corresponds to the
actual running process — that's what makes stopping it reliable.
"""

import logging
import subprocess
import threading
import uuid
from datetime import datetime
from pathlib import Path

LOG_DIR = Path(__file__).parent / "log_processes"


def _create_logger():
    """A simple logger that writes to a uniquely named file."""
    LOG_DIR.mkdir(exist_ok=True)
    log_file = LOG_DIR / f"{datetime.now():%Y-%m-%d %H-%M-%S} {uuid.uuid4().hex[:8]}.log"
    logger = logging.getLogger(str(log_file))
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s", "%Y-%m-%d %H:%M:%S")
    handler = logging.FileHandler(log_file)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


class Process:
    def __init__(self, name, command):
        self.name = name
        self._command = command
        self._process = None
        self._logger = _create_logger()
        self._stdout_thread = None
        self._stderr_thread = None

    def start(self):
        """Start the process."""
        if self.is_running():
            raise RuntimeError(f"Process '{self.name}' is already running.")
        self._logger.info(f"Starting: {self._command}")
        self._process = subprocess.Popen(self._command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self._stdout_thread = threading.Thread(target=self._read_stdout, daemon=True)
        self._stderr_thread = threading.Thread(target=self._read_stderr, daemon=True)
        self._stdout_thread.start()
        self._stderr_thread.start()

    def is_running(self):
        """Check if the process is currently running."""
        return self._process is not None and self._process.poll() is None

    def stop(self, timeout=5):
        """Stop the process."""
        if not self.is_running():
            raise RuntimeError(f"Process '{self.name}' is not running.")
        self._logger.info(f"Stopping: {self._command}")
        self._process.terminate()
        try:
            self._process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            self._process.kill()
            self._process.wait()
        if self._stdout_thread:
            self._stdout_thread.join(timeout=timeout)
        if self._stderr_thread:
            self._stderr_thread.join(timeout=timeout)
        self._logger.info(f"Stopped: {self._command}")

    def _read_stdout(self):
        """Read stdout from the process."""
        for line in self._process.stdout:
            self._logger.info(line.rstrip())

    def _read_stderr(self):
        """Read stderr from the process."""
        for line in self._process.stderr:
            self._logger.error(line.rstrip())

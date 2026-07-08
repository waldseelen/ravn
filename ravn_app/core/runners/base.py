"""
RAVN - Base process runner abstractions.
"""

from __future__ import annotations

import logging
import os
import subprocess
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


def get_hidden_subprocess_kwargs() -> Dict[str, Any]:
    """Return Windows-specific subprocess kwargs that suppress child console windows and enforce UTF-8."""
    kwargs: Dict[str, Any] = {"encoding": "utf-8", "errors": "replace"}
    if os.name != "nt":
        return kwargs
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    if creationflags:
        kwargs["creationflags"] = creationflags

    startupinfo_factory = getattr(subprocess, "STARTUPINFO", None)
    if startupinfo_factory is not None:
        startupinfo = startupinfo_factory()
        startupinfo.dwFlags |= getattr(subprocess, "STARTF_USESHOWWINDOW", 0)
        try:
            startupinfo.wShowWindow = getattr(subprocess, "SW_HIDE", 0)
        except Exception:
            pass
        kwargs["startupinfo"] = startupinfo

    return kwargs


class RunnerStatus(Enum):
    """Process execution status."""

    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


@dataclass
class RunnerResult:
    """Result of a runner execution."""

    success: bool
    return_code: int
    stdout: str = ""
    stderr: str = ""
    error_message: str = ""
    duration_seconds: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseRunner(ABC):
    """Abstract base class for process runners."""

    def __init__(self, executable_path: str):
        self.executable_path = executable_path
        self.current_process: Optional[subprocess.Popen] = None
        self.status = RunnerStatus.IDLE
        self._lock = threading.Lock()

    @abstractmethod
    def _build_command(self, *args, **kwargs) -> List[str]:
        """Build the command to execute."""

    def _find_executable(self, name: str) -> Optional[str]:
        """Find executable in PATH or local directory."""
        from shutil import which

        if os.path.isabs(name) and os.path.exists(name):
            return name

        import sys

        script_dir = Path(sys.argv[0]).parent
        local_exe = script_dir / (f"{name}.exe" if os.name == "nt" else name)
        if local_exe.exists():
            return str(local_exe)

        return which(name)

    def is_available(self) -> bool:
        """Check if the executable is available."""
        return self._find_executable(self.executable_path) is not None

    def cancel(self) -> bool:
        """Cancel the current running process."""
        with self._lock:
            if self.current_process and self.status == RunnerStatus.RUNNING:
                try:
                    self.current_process.terminate()
                    self.current_process.wait(timeout=5)
                    self.status = RunnerStatus.CANCELLED
                    logger.info("%s: Process cancelled", self.__class__.__name__)
                    return True
                except Exception as exc:
                    logger.error("Failed to cancel process: %s", exc)
                    try:
                        self.current_process.kill()
                    except Exception:
                        pass
        return False

    def _run_process(
        self,
        command: List[str],
        timeout: Optional[int] = None,
        progress_callback: Optional[Callable[[int, str], None]] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> RunnerResult:
        """Execute a process with the given command."""
        import time

        _ = progress_callback
        start_time = time.time()

        with self._lock:
            self.status = RunnerStatus.RUNNING

        try:
            process_env = os.environ.copy()
            if env:
                process_env.update(env)

            logger.debug("Running command: %s", " ".join(command))

            self.current_process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                env=process_env,
                **get_hidden_subprocess_kwargs(),
            )

            stdout, stderr = self.current_process.communicate(timeout=timeout)
            duration = time.time() - start_time

            with self._lock:
                if self.current_process.returncode == 0:
                    self.status = RunnerStatus.COMPLETED
                    return RunnerResult(
                        success=True,
                        return_code=0,
                        stdout=stdout,
                        stderr=stderr,
                        duration_seconds=duration,
                    )

                self.status = RunnerStatus.FAILED
                error_msg = self._parse_error(stderr)
                return RunnerResult(
                    success=False,
                    return_code=self.current_process.returncode,
                    stdout=stdout,
                    stderr=stderr,
                    error_message=error_msg,
                    duration_seconds=duration,
                )

        except subprocess.TimeoutExpired:
            with self._lock:
                self.status = RunnerStatus.TIMEOUT
            if self.current_process:
                self.current_process.kill()
                self.current_process.wait()
            return RunnerResult(
                success=False,
                return_code=-1,
                error_message="Process timed out",
                duration_seconds=time.time() - start_time,
            )

        except Exception as exc:
            with self._lock:
                self.status = RunnerStatus.FAILED
            logger.exception("Process execution error: %s", exc)
            return RunnerResult(
                success=False,
                return_code=-1,
                error_message=str(exc),
                duration_seconds=time.time() - start_time,
            )

        finally:
            with self._lock:
                self.current_process = None

    @abstractmethod
    def _parse_error(self, stderr: str) -> str:
        """Parse stderr to extract human-readable error message."""

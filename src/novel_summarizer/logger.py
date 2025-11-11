from __future__ import annotations

import sys
from pathlib import Path
from types import TracebackType
from typing import IO, Any, TextIO


class WithFileLogger:
    """Context manager that tees stdout to a file while still printing to the console."""

    def __init__(
        self,
        log_path: Path | str | None,
        *,
        mode: str = "w",
        encoding: str = "utf-8",
    ):
        self._path = Path(log_path) if log_path is not None else None
        self._mode = mode
        self._encoding = encoding
        self._file: IO[str] | None = None
        self._stdout: TextIO | None = None

    def __enter__(self) -> WithFileLogger:
        if self._path is not None:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._file = self._path.open(self._mode, encoding=self._encoding)
        self._stdout = sys.stdout
        sys.stdout = self  # type: ignore[assignment]
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.flush()

        if self._stdout is not None:
            sys.stdout = self._stdout
            self._stdout = None

        if self._file is not None:
            self._file.close()
            self._file = None

    def write(self, data: str) -> int:
        if self._stdout is None:
            raise RuntimeError("WithFileLogger is not active")

        written = len(data)
        if self._file is not None:
            written = self._file.write(data)
        self._stdout.write(data)
        self.flush()
        return written

    def flush(self) -> None:
        if self._file is not None:
            self._file.flush()
        if self._stdout is not None:
            self._stdout.flush()

    def __getattr__(self, name: str) -> Any:
        if self._stdout is None:
            raise AttributeError(name)
        return getattr(self._stdout, name)

    def log(self, *parts: object, sep: str = " ", end: str = "\n") -> None:
        """Print-like helper that writes to stdout and the optional log file."""
        text = sep.join(str(part) for part in parts) + end
        self.write(text)

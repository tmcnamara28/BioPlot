"""BioWorker — QRunnable base class and concrete workers for all async ops."""
from __future__ import annotations

from typing import Any, Callable, Optional

from PySide6.QtCore import QObject, QRunnable, Signal, Slot


class WorkerSignals(QObject):
    """Signals emitted by any BioWorker."""
    started = Signal()
    finished = Signal()
    progress = Signal(int)          # 0–100
    result = Signal(object)         # any Python object
    error = Signal(str)             # error message string


class BioWorker(QRunnable):
    """Base worker that runs a callable in QThreadPool.

    Subclass and override ``run()`` for domain-specific work, or use
    ``FunctionWorker`` for one-off callables.
    """

    def __init__(self) -> None:
        super().__init__()
        self.signals = WorkerSignals()
        self.setAutoDelete(True)
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    @property
    def is_cancelled(self) -> bool:
        return self._cancelled

    @Slot()
    def run(self) -> None:  # pragma: no cover
        raise NotImplementedError


class FunctionWorker(BioWorker):
    """Run an arbitrary callable in a thread pool worker."""

    def __init__(
        self,
        fn: Callable[..., Any],
        *args: Any,
        progress_callback: Optional[Callable[[int], None]] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__()
        self._fn = fn
        self._args = args
        self._kwargs = kwargs
        self._progress_callback = progress_callback

    @Slot()
    def run(self) -> None:
        self.signals.started.emit()
        try:
            if self._progress_callback is not None:
                self._kwargs["progress_callback"] = self.signals.progress.emit
            result = self._fn(*self._args, **self._kwargs)
            if not self._cancelled:
                self.signals.result.emit(result)
        except Exception as exc:  # noqa: BLE001
            self.signals.error.emit(str(exc))
        finally:
            self.signals.finished.emit()


class LoadWorker(BioWorker):
    """Load a CSV/TSV file into a pandas DataFrame with chunked progress."""

    def __init__(self, path: str, sep: str = ",") -> None:
        super().__init__()
        self._path = path
        self._sep = sep

    @Slot()
    def run(self) -> None:
        import pandas as pd

        self.signals.started.emit()
        try:
            self.signals.progress.emit(10)
            df = pd.read_csv(self._path, sep=self._sep, index_col=0)
            self.signals.progress.emit(90)
            if not self._cancelled:
                self.signals.result.emit(df)
        except Exception as exc:  # noqa: BLE001
            self.signals.error.emit(str(exc))
        finally:
            self.signals.progress.emit(100)
            self.signals.finished.emit()


class AnalysisWorker(BioWorker):
    """Run DEG / PCA analysis in a worker thread."""

    def __init__(
        self,
        fn: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super().__init__()
        self._fn = fn
        self._args = args
        self._kwargs = kwargs

    @Slot()
    def run(self) -> None:
        self.signals.started.emit()
        try:
            result = self._fn(*self._args, **self._kwargs)
            if not self._cancelled:
                self.signals.result.emit(result)
        except Exception as exc:  # noqa: BLE001
            self.signals.error.emit(str(exc))
        finally:
            self.signals.finished.emit()


class RenderWorker(BioWorker):
    """Build a matplotlib Figure off the main thread.

    Only ``canvas.draw()`` should be called on the main thread after
    receiving the result signal.
    """

    def __init__(
        self,
        fn: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super().__init__()
        self._fn = fn
        self._args = args
        self._kwargs = kwargs

    @Slot()
    def run(self) -> None:
        self.signals.started.emit()
        try:
            fig = self._fn(*self._args, **self._kwargs)
            if not self._cancelled:
                self.signals.result.emit(fig)
        except Exception as exc:  # noqa: BLE001
            self.signals.error.emit(str(exc))
        finally:
            self.signals.finished.emit()

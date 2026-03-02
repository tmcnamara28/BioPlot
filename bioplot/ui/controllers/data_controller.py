"""DataController — wires DataManager signals to DataNavigator UI."""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QMessageBox

from bioplot.core import DataManager
from bioplot.ui.panels.data_navigator import DataNavigator


class DataController(QObject):
    """Connects DataManager events to navigator UI and handles errors."""

    def __init__(
        self,
        data_manager: DataManager,
        navigator: DataNavigator,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._dm = data_manager
        self._nav = navigator

        # Connect error signals
        self._dm.load_error.connect(self._on_load_error)
        self._dm.load_progress.connect(self._on_load_progress)

    def _on_load_error(self, dataset_id: str, message: str) -> None:
        # Remove placeholder dataset
        self._dm.remove_dataset(dataset_id)
        QMessageBox.critical(
            None, "Load Error",
            f"Failed to load dataset:\n{message}"
        )

    def _on_load_progress(self, dataset_id: str, pct: int) -> None:
        # Could update a per-item progress indicator in the tree
        # For now just refresh labels at 100%
        if pct >= 100:
            self._nav.refresh()

"""DataNavigator — left panel: dataset tree + plot library icons."""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QGroupBox, QInputDialog, QLabel, QMenu, QMessageBox,
    QSizePolicy, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)

from bioplot.constants import PLOT_TYPES
from bioplot.core import DataManager


class DataNavigator(QWidget):
    """Left panel showing loaded datasets and plot type library."""

    plot_type_selected = Signal(str)   # plot_type id
    dataset_activated = Signal(str)    # dataset_id

    def __init__(self, data_manager: DataManager, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._dm = data_manager
        self._build_ui()
        self._connect_signals()

    # ── Build UI ──────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        # Dataset section
        ds_group = QGroupBox("Data Navigator")
        ds_layout = QVBoxLayout(ds_group)
        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(["Name", "Info"])
        self._tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(self._show_context_menu)
        self._tree.itemDoubleClicked.connect(self._on_item_activated)
        ds_layout.addWidget(self._tree)
        layout.addWidget(ds_group)

        # Plot library section
        plot_group = QGroupBox("Plot Library")
        plot_layout = QVBoxLayout(plot_group)
        self._plot_tree = QTreeWidget()
        self._plot_tree.setHeaderHidden(True)
        self._plot_tree.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        for pid, pname in PLOT_TYPES.items():
            item = QTreeWidgetItem([pname])
            item.setData(0, Qt.ItemDataRole.UserRole, pid)
            self._plot_tree.addTopLevelItem(item)
        self._plot_tree.itemDoubleClicked.connect(self._on_plot_selected)
        plot_layout.addWidget(self._plot_tree)
        layout.addWidget(plot_group)

    def _connect_signals(self) -> None:
        self._dm.dataset_added.connect(self.refresh)
        self._dm.dataset_removed.connect(self.refresh)
        self._dm.dataset_renamed.connect(self.refresh)
        self._dm.dataset_updated.connect(self.refresh)

    # ── Refresh ───────────────────────────────────────────────────────────────

    def refresh(self, _=None) -> None:
        self._tree.clear()
        for ds in self._dm.datasets:
            item = QTreeWidgetItem([ds.name, ds.summary()])
            item.setData(0, Qt.ItemDataRole.UserRole, ds.dataset_id)
            self._tree.addTopLevelItem(item)
        self._tree.resizeColumnToContents(0)

    # ── Signals ───────────────────────────────────────────────────────────────

    def _on_plot_selected(self, item: QTreeWidgetItem, _col: int) -> None:
        pid = item.data(0, Qt.ItemDataRole.UserRole)
        if pid:
            self.plot_type_selected.emit(pid)

    def _on_item_activated(self, item: QTreeWidgetItem, _col: int) -> None:
        did = item.data(0, Qt.ItemDataRole.UserRole)
        if did:
            self.dataset_activated.emit(did)

    # ── Context menu ──────────────────────────────────────────────────────────

    def _show_context_menu(self, pos) -> None:
        item = self._tree.itemAt(pos)
        if item is None:
            return
        did = item.data(0, Qt.ItemDataRole.UserRole)
        if did is None:
            return

        menu = QMenu(self)
        rename_act = menu.addAction("Rename…")
        dup_act = menu.addAction("Duplicate")
        menu.addSeparator()
        delete_act = menu.addAction("Remove")

        action = menu.exec(self._tree.mapToGlobal(pos))
        if action == rename_act:
            self._rename_dataset(did)
        elif action == dup_act:
            self._dm.duplicate_dataset(did)
        elif action == delete_act:
            self._remove_dataset(did)

    def _rename_dataset(self, dataset_id: str) -> None:
        ds = self._dm.get_dataset(dataset_id)
        if ds is None:
            return
        name, ok = QInputDialog.getText(self, "Rename", "New name:", text=ds.name)
        if ok and name:
            self._dm.rename_dataset(dataset_id, name)

    def _remove_dataset(self, dataset_id: str) -> None:
        resp = QMessageBox.question(
            self, "Remove", "Remove this dataset?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if resp == QMessageBox.StandardButton.Yes:
            self._dm.remove_dataset(dataset_id)

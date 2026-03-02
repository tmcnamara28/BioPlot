"""ImportDialog — wizard for loading CSV/TSV/H5AD files."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox,
    QFileDialog, QFormLayout, QGroupBox, QHBoxLayout,
    QLabel, QLineEdit, QMessageBox, QPushButton,
    QSpinBox, QVBoxLayout, QWidget,
)

from bioplot.core import DataManager


class ImportDialog(QDialog):
    """File import wizard: select file, configure options, load."""

    def __init__(self, data_manager: DataManager, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._dm = data_manager
        self.setWindowTitle("Import Data")
        self.setMinimumWidth(480)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        # File selection
        file_group = QGroupBox("File")
        file_layout = QHBoxLayout(file_group)
        self._path_edit = QLineEdit()
        self._path_edit.setPlaceholderText("Path to CSV, TSV, or H5AD file…")
        browse_btn = QPushButton("Browse…")
        browse_btn.clicked.connect(self._browse)
        file_layout.addWidget(self._path_edit)
        file_layout.addWidget(browse_btn)
        layout.addWidget(file_group)

        # Options
        opts_group = QGroupBox("Options")
        form = QFormLayout(opts_group)

        self._sep_combo = QComboBox()
        self._sep_combo.addItems(["Comma (CSV)", "Tab (TSV)", "Semicolon"])
        form.addRow("Delimiter:", self._sep_combo)

        self._index_col = QSpinBox()
        self._index_col.setRange(0, 10)
        self._index_col.setValue(0)
        form.addRow("Index column:", self._index_col)

        self._header_check = QCheckBox("First row is header")
        self._header_check.setChecked(True)
        form.addRow("", self._header_check)

        self._transpose_check = QCheckBox("Transpose (genes as columns → rows)")
        form.addRow("", self._transpose_check)

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("Auto-detected from filename")
        form.addRow("Dataset name:", self._name_edit)

        layout.addWidget(opts_group)

        # Status label
        self._status = QLabel("")
        self._status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._status)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        self._ok_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        self._ok_btn.setText("Import")
        layout.addWidget(buttons)

        # Auto-detect delimiter on path change
        self._path_edit.textChanged.connect(self._auto_detect)

    def _browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Expression File", "",
            "Expression Files (*.csv *.tsv *.txt *.h5ad);;All Files (*)"
        )
        if path:
            self._path_edit.setText(path)

    def _auto_detect(self, path: str) -> None:
        p = Path(path)
        if p.suffix.lower() in (".tsv", ".txt"):
            self._sep_combo.setCurrentIndex(1)
        elif p.suffix.lower() == ".csv":
            self._sep_combo.setCurrentIndex(0)
        if not self._name_edit.text():
            self._name_edit.setPlaceholderText(p.stem)

    def _accept(self) -> None:
        path = self._path_edit.text().strip()
        if not path:
            QMessageBox.warning(self, "No File", "Please select a file to import.")
            return
        if not Path(path).exists():
            QMessageBox.warning(self, "Not Found", f"File not found:\n{path}")
            return

        self._status.setText("Loading…")
        dataset_id = self._dm.load_file_async(path)

        # Set custom name if provided
        name = self._name_edit.text().strip()
        if name:
            ds = self._dm.get_dataset(dataset_id)
            if ds:
                ds.name = name
                self._dm.dataset_renamed.emit(dataset_id)

        self._status.setText("Import started in background.")
        self.accept()

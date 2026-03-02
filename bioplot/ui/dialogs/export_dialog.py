"""ExportDialog — choose format, DPI, and dimensions for figure export."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox,
    QDoubleSpinBox, QFileDialog, QFormLayout, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QPushButton, QSpinBox,
    QVBoxLayout, QWidget,
)

from bioplot.constants import DPI_PRESETS, FIGURE_SIZE_PRESETS


class ExportDialog(QDialog):
    """Export settings dialog.

    Attributes (read after exec):
        export_path: chosen file path
        export_format: "pdf" | "svg" | "png" | "eps"
        dpi: int
        width_mm: float
        height_mm: float
        transparent: bool
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Export Figure")
        self.setMinimumWidth(420)

        self.export_path: Optional[str] = None
        self.export_format: str = "pdf"
        self.dpi: int = 300
        self.width_mm: float = 89.0
        self.height_mm: float = 89.0
        self.transparent: bool = False

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Destination
        dest_group = QGroupBox("Destination")
        dest_layout = QHBoxLayout(dest_group)
        self._path_edit = QLineEdit()
        self._path_edit.setPlaceholderText("Output file path…")
        browse_btn = QPushButton("Browse…")
        browse_btn.clicked.connect(self._browse)
        dest_layout.addWidget(self._path_edit)
        dest_layout.addWidget(browse_btn)
        layout.addWidget(dest_group)

        # Format & DPI
        fmt_group = QGroupBox("Format")
        fmt_form = QFormLayout(fmt_group)

        self._format_combo = QComboBox()
        self._format_combo.addItems(["PDF", "SVG", "PNG", "EPS", "TIFF"])
        fmt_form.addRow("Format:", self._format_combo)

        self._dpi_preset = QComboBox()
        self._dpi_preset.addItems(list(DPI_PRESETS.keys()))
        self._dpi_preset.setCurrentText("Print (300 dpi)")
        self._dpi_preset.currentIndexChanged.connect(self._on_dpi_preset)
        fmt_form.addRow("DPI preset:", self._dpi_preset)

        self._dpi_spin = QSpinBox()
        self._dpi_spin.setRange(72, 1200)
        self._dpi_spin.setValue(300)
        fmt_form.addRow("DPI:", self._dpi_spin)

        layout.addWidget(fmt_group)

        # Size
        size_group = QGroupBox("Size")
        size_form = QFormLayout(size_group)

        self._size_preset = QComboBox()
        self._size_preset.addItem("(current figure size)")
        self._size_preset.addItems(list(FIGURE_SIZE_PRESETS.keys()))
        self._size_preset.currentIndexChanged.connect(self._on_size_preset)
        size_form.addRow("Size preset:", self._size_preset)

        self._width_spin = QDoubleSpinBox()
        self._width_spin.setRange(10, 600)
        self._width_spin.setSuffix(" mm")
        self._width_spin.setValue(89)
        size_form.addRow("Width:", self._width_spin)

        self._height_spin = QDoubleSpinBox()
        self._height_spin.setRange(10, 600)
        self._height_spin.setSuffix(" mm")
        self._height_spin.setValue(89)
        size_form.addRow("Height:", self._height_spin)

        self._transparent_check = QCheckBox("Transparent background")
        size_form.addRow("", self._transparent_check)

        layout.addWidget(size_group)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        export_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        export_btn.setText("Export")
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # Auto-select format from extension
        self._format_combo.currentIndexChanged.connect(self._on_format_changed)

    def _browse(self) -> None:
        fmt = self._format_combo.currentText().lower()
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Figure", "",
            f"{fmt.upper()} Files (*.{fmt});;All Files (*)"
        )
        if path:
            self._path_edit.setText(path)

    def _on_format_changed(self) -> None:
        fmt = self._format_combo.currentText().lower()
        path = self._path_edit.text()
        if path:
            new_path = str(Path(path).with_suffix(f".{fmt}"))
            self._path_edit.setText(new_path)

    def _on_dpi_preset(self) -> None:
        label = self._dpi_preset.currentText()
        dpi = DPI_PRESETS.get(label)
        if dpi:
            self._dpi_spin.setValue(dpi)

    def _on_size_preset(self) -> None:
        label = self._size_preset.currentText()
        preset = FIGURE_SIZE_PRESETS.get(label)
        if preset:
            self._width_spin.setValue(preset[0])
            self._height_spin.setValue(preset[1])

    def _accept(self) -> None:
        from PySide6.QtWidgets import QMessageBox
        path = self._path_edit.text().strip()
        if not path:
            QMessageBox.warning(self, "No Path", "Please choose an output file path.")
            return
        self.export_path = path
        self.export_format = self._format_combo.currentText().lower()
        self.dpi = self._dpi_spin.value()
        self.width_mm = self._width_spin.value()
        self.height_mm = self._height_spin.value()
        self.transparent = self._transparent_check.isChecked()
        self.accept()

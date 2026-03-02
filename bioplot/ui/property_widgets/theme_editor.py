"""Theme editor — preset selector, save preset."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox, QFormLayout, QHBoxLayout, QInputDialog,
    QMessageBox, QPushButton, QVBoxLayout, QWidget,
)

from bioplot.core import PresetManager


class ThemeEditor(QWidget):
    """Preset selection and save UI."""

    changed = Signal()
    preset_applied = Signal(str)    # preset name

    def __init__(self, preset_manager: PresetManager, parent=None) -> None:
        super().__init__(parent)
        self._pm = preset_manager
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        form = QFormLayout()
        self._preset_combo = QComboBox()
        self._refresh_presets()
        form.addRow("Journal preset:", self._preset_combo)
        layout.addLayout(form)

        btn_row = QHBoxLayout()
        self._apply_btn = QPushButton("Apply Preset")
        self._save_btn = QPushButton("Save as Preset…")
        self._delete_btn = QPushButton("Delete")
        btn_row.addWidget(self._apply_btn)
        btn_row.addWidget(self._save_btn)
        btn_row.addWidget(self._delete_btn)
        layout.addLayout(btn_row)
        layout.addStretch()

        self._apply_btn.clicked.connect(self._apply_preset)
        self._save_btn.clicked.connect(self._save_preset)
        self._delete_btn.clicked.connect(self._delete_preset)

    def _refresh_presets(self) -> None:
        self._preset_combo.clear()
        self._preset_combo.addItem("(none)")
        self._preset_combo.addItems(self._pm.preset_names)

    def _apply_preset(self) -> None:
        name = self._preset_combo.currentText()
        if name and name != "(none)":
            self.preset_applied.emit(name)

    def _save_preset(self) -> None:
        name, ok = QInputDialog.getText(self, "Save Preset", "Preset name:")
        if ok and name:
            self.changed.emit()   # trigger collect → then caller saves

    def _delete_preset(self) -> None:
        name = self._preset_combo.currentText()
        if not name or name == "(none)":
            return
        if not self._pm.is_user_preset(name):
            QMessageBox.warning(self, "Cannot Delete", "Built-in presets cannot be deleted.")
            return
        resp = QMessageBox.question(
            self, "Delete Preset", f"Delete preset '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if resp == QMessageBox.StandardButton.Yes:
            self._pm.delete_user_preset(name)
            self._refresh_presets()

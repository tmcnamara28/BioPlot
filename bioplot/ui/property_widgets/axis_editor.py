"""Axis editor — limits, scale, labels, grid."""
from __future__ import annotations

from typing import Optional, Tuple

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout,
    QGroupBox, QLabel, QLineEdit, QScrollArea, QTabWidget,
    QVBoxLayout, QWidget,
)

from bioplot.models import AxisConfig


class _SingleAxisEditor(QWidget):
    changed = Signal()

    def __init__(self, label_prefix: str, parent=None) -> None:
        super().__init__(parent)
        self._prefix = label_prefix
        self._build_ui()

    def _build_ui(self) -> None:
        form = QFormLayout(self)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)

        self._label = QLineEdit()
        self._label.setPlaceholderText(f"{self._prefix} axis label")
        form.addRow("Label:", self._label)

        self._scale = QComboBox()
        self._scale.addItems(["linear", "log", "symlog", "logit"])
        form.addRow("Scale:", self._scale)

        self._limit_min = QDoubleSpinBox()
        self._limit_min.setRange(-1e9, 1e9)
        self._limit_min.setSpecialValueText("Auto")
        self._limit_min.setValue(self._limit_min.minimum())
        form.addRow("Min:", self._limit_min)

        self._limit_max = QDoubleSpinBox()
        self._limit_max.setRange(-1e9, 1e9)
        self._limit_max.setSpecialValueText("Auto")
        self._limit_max.setValue(self._limit_max.minimum())
        form.addRow("Max:", self._limit_max)

        self._grid = QCheckBox("Show grid")
        form.addRow("", self._grid)

        self._tick_size = QDoubleSpinBox()
        self._tick_size.setRange(4, 24)
        self._tick_size.setValue(8)
        form.addRow("Tick size:", self._tick_size)

        self._tick_rotation = QDoubleSpinBox()
        self._tick_rotation.setRange(0, 90)
        self._tick_rotation.setValue(0)
        form.addRow("Tick rotation:", self._tick_rotation)

        for w in (self._label, self._scale, self._limit_min, self._limit_max,
                  self._grid, self._tick_size, self._tick_rotation):
            try:
                w.editingFinished.connect(self.changed)
            except AttributeError:
                pass
            try:
                w.currentIndexChanged.connect(self.changed)
            except AttributeError:
                pass
            try:
                w.stateChanged.connect(self.changed)
            except AttributeError:
                pass
            try:
                w.valueChanged.connect(self.changed)
            except AttributeError:
                pass

    def load(self, cfg: AxisConfig) -> None:
        self._label.setText(cfg.label)
        self._scale.setCurrentText(cfg.scale)
        if cfg.limits:
            self._limit_min.setValue(cfg.limits[0])
            self._limit_max.setValue(cfg.limits[1])
        self._grid.setChecked(cfg.show_grid)
        self._tick_size.setValue(cfg.tick_size)
        self._tick_rotation.setValue(cfg.tick_rotation)

    def get_values(self) -> AxisConfig:
        min_v = self._limit_min.value()
        max_v = self._limit_max.value()
        limits = None
        if min_v > self._limit_min.minimum() and max_v > self._limit_max.minimum():
            limits = (min_v, max_v)

        return AxisConfig(
            label=self._label.text(),
            scale=self._scale.currentText(),
            limits=limits,
            show_grid=self._grid.isChecked(),
            tick_size=self._tick_size.value(),
            tick_rotation=self._tick_rotation.value(),
        )


class AxisEditor(QWidget):
    """Two-tab widget for X and Y axis configuration."""

    changed = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        self._x_editor = _SingleAxisEditor("X")
        self._y_editor = _SingleAxisEditor("Y")
        tabs.addTab(self._x_editor, "X Axis")
        tabs.addTab(self._y_editor, "Y Axis")
        layout.addWidget(tabs)
        layout.addStretch()

        self._x_editor.changed.connect(self.changed)
        self._y_editor.changed.connect(self.changed)

    def load(self, x_cfg: AxisConfig, y_cfg: AxisConfig) -> None:
        self._x_editor.load(x_cfg)
        self._y_editor.load(y_cfg)

    def get_values(self) -> Tuple[AxisConfig, AxisConfig]:
        return self._x_editor.get_values(), self._y_editor.get_values()

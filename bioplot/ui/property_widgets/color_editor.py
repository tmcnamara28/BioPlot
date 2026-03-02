"""Color editor — color pickers, palette selector."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QColorDialog, QComboBox, QDoubleSpinBox,
    QFormLayout, QHBoxLayout, QPushButton, QVBoxLayout, QWidget,
)

from bioplot.constants import SEABORN_PALETTES
from bioplot.models import ColorConfig


class ColorButton(QPushButton):
    """Button that shows a color swatch and opens QColorDialog on click."""
    color_changed = Signal(str)   # hex string

    def __init__(self, color: str = "#ffffff", parent=None) -> None:
        super().__init__(parent)
        self._color = color
        self._update_swatch()
        self.clicked.connect(self._pick_color)

    def _update_swatch(self) -> None:
        self.setStyleSheet(
            f"background-color: {self._color}; border: 1px solid #888; min-width: 60px;"
        )
        self.setText(self._color)

    def _pick_color(self) -> None:
        col = QColorDialog.getColor(QColor(self._color), self, "Pick Color")
        if col.isValid():
            self._color = col.name()
            self._update_swatch()
            self.color_changed.emit(self._color)

    @property
    def color(self) -> str:
        return self._color

    @color.setter
    def color(self, value: str) -> None:
        self._color = value
        self._update_swatch()


class ColorEditor(QWidget):
    """Color configuration panel."""

    changed = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        form = QFormLayout(self)

        self._up_btn = ColorButton("#d62728")
        self._down_btn = ColorButton("#1f77b4")
        self._ns_btn = ColorButton("#aec7e8")
        self._bg_btn = ColorButton("#ffffff")

        self._palette = QComboBox()
        self._palette.addItems(SEABORN_PALETTES)

        self._colormap = QComboBox()
        import matplotlib.pyplot as plt
        cmaps = sorted(plt.colormaps())
        self._colormap.addItems(cmaps)
        self._colormap.setCurrentText("viridis")

        self._alpha = QDoubleSpinBox()
        self._alpha.setRange(0.0, 1.0)
        self._alpha.setSingleStep(0.05)
        self._alpha.setValue(0.8)

        form.addRow("Up-regulated:", self._up_btn)
        form.addRow("Down-regulated:", self._down_btn)
        form.addRow("Non-significant:", self._ns_btn)
        form.addRow("Background:", self._bg_btn)
        form.addRow("Palette:", self._palette)
        form.addRow("Colormap:", self._colormap)
        form.addRow("Alpha:", self._alpha)

        for w in (self._up_btn, self._down_btn, self._ns_btn, self._bg_btn):
            w.color_changed.connect(self.changed)
        self._palette.currentIndexChanged.connect(self.changed)
        self._colormap.currentIndexChanged.connect(self.changed)
        self._alpha.valueChanged.connect(self.changed)

    def load(self, cfg: ColorConfig) -> None:
        self._up_btn.color = cfg.up_color
        self._down_btn.color = cfg.down_color
        self._ns_btn.color = cfg.ns_color
        self._bg_btn.color = cfg.background
        self._palette.setCurrentText(cfg.palette)
        self._colormap.setCurrentText(cfg.colormap)
        self._alpha.setValue(cfg.alpha)

    def get_values(self) -> ColorConfig:
        return ColorConfig(
            up_color=self._up_btn.color,
            down_color=self._down_btn.color,
            ns_color=self._ns_btn.color,
            background=self._bg_btn.color,
            palette=self._palette.currentText(),
            colormap=self._colormap.currentText(),
            alpha=self._alpha.value(),
        )

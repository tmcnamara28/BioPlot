"""Marker editor — point size, alpha, shape."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox, QDoubleSpinBox, QFormLayout, QWidget,
)

from bioplot.models import MarkerConfig

MARKER_SHAPES = ["o", "s", "^", "v", "D", "+", "x", "*", "p", "h"]
MARKER_SHAPE_LABELS = {
    "o": "Circle", "s": "Square", "^": "Triangle Up", "v": "Triangle Down",
    "D": "Diamond", "+": "Plus", "x": "Cross", "*": "Star", "p": "Pentagon",
    "h": "Hexagon",
}


class MarkerEditor(QWidget):
    """Marker style configuration panel."""

    changed = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        form = QFormLayout(self)

        self._shape = QComboBox()
        for sym in MARKER_SHAPES:
            self._shape.addItem(MARKER_SHAPE_LABELS.get(sym, sym), sym)

        self._size = QDoubleSpinBox()
        self._size.setRange(1, 500)
        self._size.setValue(20)
        self._size.setSuffix(" pt²")

        self._alpha = QDoubleSpinBox()
        self._alpha.setRange(0.0, 1.0)
        self._alpha.setSingleStep(0.05)
        self._alpha.setValue(0.7)

        self._edge_width = QDoubleSpinBox()
        self._edge_width.setRange(0, 5)
        self._edge_width.setSingleStep(0.25)
        self._edge_width.setValue(0.5)

        self._jitter = QDoubleSpinBox()
        self._jitter.setRange(0, 5)
        self._jitter.setSingleStep(0.1)
        self._jitter.setValue(0)

        form.addRow("Shape:", self._shape)
        form.addRow("Size:", self._size)
        form.addRow("Alpha:", self._alpha)
        form.addRow("Edge width:", self._edge_width)
        form.addRow("Jitter:", self._jitter)

        self._shape.currentIndexChanged.connect(self.changed)
        for w in (self._size, self._alpha, self._edge_width, self._jitter):
            w.valueChanged.connect(self.changed)

    def load(self, cfg: MarkerConfig) -> None:
        idx = MARKER_SHAPES.index(cfg.shape) if cfg.shape in MARKER_SHAPES else 0
        self._shape.setCurrentIndex(idx)
        self._size.setValue(cfg.size)
        self._alpha.setValue(cfg.alpha)
        self._edge_width.setValue(cfg.edge_width)
        self._jitter.setValue(cfg.jitter)

    def get_values(self) -> MarkerConfig:
        return MarkerConfig(
            shape=self._shape.currentData() or "o",
            size=self._size.value(),
            alpha=self._alpha.value(),
            edge_color="none",
            edge_width=self._edge_width.value(),
            jitter=self._jitter.value(),
        )

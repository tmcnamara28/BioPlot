"""Font editor — family, sizes, weight."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout, QWidget,
)

from bioplot.models import FontConfig


def _available_font_families() -> list[str]:
    try:
        import matplotlib.font_manager as fm
        fonts = sorted({f.name for f in fm.fontManager.ttflist})
        return fonts if fonts else ["Arial", "Helvetica", "Times New Roman"]
    except Exception:
        return ["Arial", "Helvetica", "Times New Roman", "DejaVu Sans"]


class FontEditor(QWidget):
    """Font configuration panel."""

    changed = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        form = QFormLayout(self)

        self._family = QComboBox()
        self._family.setEditable(True)
        self._family.addItems(_available_font_families())
        self._family.setCurrentText("Arial")

        def _spin(lo=4, hi=36, val=10):
            s = QDoubleSpinBox()
            s.setRange(lo, hi)
            s.setSingleStep(0.5)
            s.setValue(val)
            return s

        self._title_size = _spin(val=12)
        self._axis_label_size = _spin(val=10)
        self._tick_label_size = _spin(val=8)
        self._legend_size = _spin(val=9)
        self._annotation_size = _spin(val=8)
        self._bold_title = QCheckBox("Bold title")

        form.addRow("Family:", self._family)
        form.addRow("Title size:", self._title_size)
        form.addRow("Axis label:", self._axis_label_size)
        form.addRow("Tick label:", self._tick_label_size)
        form.addRow("Legend:", self._legend_size)
        form.addRow("Annotation:", self._annotation_size)
        form.addRow("", self._bold_title)

        for w in (self._family, self._title_size, self._axis_label_size,
                  self._tick_label_size, self._legend_size, self._annotation_size):
            try:
                w.currentIndexChanged.connect(self.changed)
            except AttributeError:
                pass
            try:
                w.valueChanged.connect(self.changed)
            except AttributeError:
                pass
        self._bold_title.stateChanged.connect(self.changed)

    def load(self, cfg: FontConfig) -> None:
        self._family.setCurrentText(cfg.family)
        self._title_size.setValue(cfg.title_size)
        self._axis_label_size.setValue(cfg.axis_label_size)
        self._tick_label_size.setValue(cfg.tick_label_size)
        self._legend_size.setValue(cfg.legend_size)
        self._annotation_size.setValue(cfg.annotation_size)
        self._bold_title.setChecked(cfg.bold_title)

    def get_values(self) -> FontConfig:
        return FontConfig(
            family=self._family.currentText(),
            title_size=self._title_size.value(),
            axis_label_size=self._axis_label_size.value(),
            tick_label_size=self._tick_label_size.value(),
            legend_size=self._legend_size.value(),
            annotation_size=self._annotation_size.value(),
            bold_title=self._bold_title.isChecked(),
        )

"""Statistics editor — p-value thresholds, label count, annotation style."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout, QSpinBox, QWidget,
)

from bioplot.models import StatConfig


class StatsEditor(QWidget):
    """Statistical parameter configuration panel."""

    changed = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        form = QFormLayout(self)

        self._pvalue_type = QComboBox()
        self._pvalue_type.addItems(["padj", "pvalue"])

        self._pvalue_threshold = QDoubleSpinBox()
        self._pvalue_threshold.setRange(0.0001, 1.0)
        self._pvalue_threshold.setDecimals(4)
        self._pvalue_threshold.setSingleStep(0.01)
        self._pvalue_threshold.setValue(0.05)

        self._fc_threshold = QDoubleSpinBox()
        self._fc_threshold.setRange(0, 10)
        self._fc_threshold.setSingleStep(0.25)
        self._fc_threshold.setValue(1.0)

        self._label_top_n = QSpinBox()
        self._label_top_n.setRange(0, 100)
        self._label_top_n.setValue(10)

        self._annotation_style = QComboBox()
        self._annotation_style.addItems(["gene", "dot", "none"])

        self._show_threshold_lines = QCheckBox("Show threshold lines")
        self._show_threshold_lines.setChecked(True)

        self._correction = QComboBox()
        self._correction.addItems([
            "fdr_bh", "bonferroni", "holm", "fdr_by", "none"
        ])

        form.addRow("p-value column:", self._pvalue_type)
        form.addRow("p-value threshold:", self._pvalue_threshold)
        form.addRow("log₂FC threshold:", self._fc_threshold)
        form.addRow("Label top N genes:", self._label_top_n)
        form.addRow("Annotation style:", self._annotation_style)
        form.addRow("", self._show_threshold_lines)
        form.addRow("Correction method:", self._correction)

        for w in (self._pvalue_type, self._pvalue_threshold, self._fc_threshold,
                  self._label_top_n, self._annotation_style, self._correction):
            try:
                w.currentIndexChanged.connect(self.changed)
            except AttributeError:
                pass
            try:
                w.valueChanged.connect(self.changed)
            except AttributeError:
                pass
        self._show_threshold_lines.stateChanged.connect(self.changed)

    def load(self, cfg: StatConfig) -> None:
        self._pvalue_type.setCurrentText(cfg.pvalue_type)
        self._pvalue_threshold.setValue(cfg.pvalue_threshold)
        self._fc_threshold.setValue(cfg.fc_threshold)
        self._label_top_n.setValue(cfg.label_top_n)
        self._annotation_style.setCurrentText(cfg.annotation_style)
        self._show_threshold_lines.setChecked(cfg.show_threshold_lines)
        self._correction.setCurrentText(cfg.correction_method)

    def get_values(self) -> StatConfig:
        return StatConfig(
            pvalue_type=self._pvalue_type.currentText(),
            pvalue_threshold=self._pvalue_threshold.value(),
            fc_threshold=self._fc_threshold.value(),
            label_top_n=self._label_top_n.value(),
            annotation_style=self._annotation_style.currentText(),
            show_threshold_lines=self._show_threshold_lines.isChecked(),
            correction_method=self._correction.currentText(),
        )

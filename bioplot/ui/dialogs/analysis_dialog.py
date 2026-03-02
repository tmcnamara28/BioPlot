"""AnalysisDialog — DEG settings and contrast selection."""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox,
    QDoubleSpinBox, QFormLayout, QGroupBox, QLabel,
    QListWidget, QListWidgetItem, QMessageBox, QProgressBar,
    QSpinBox, QVBoxLayout, QWidget,
)

from bioplot.core import DataManager
from bioplot.core.worker import AnalysisWorker
from bioplot.models.dataset import DEGResult, PCAResult
from PySide6.QtCore import QThreadPool


class AnalysisDialog(QDialog):
    """Dialog for configuring and running DEG or PCA analysis."""

    def __init__(
        self,
        data_manager: DataManager,
        parent: Optional[QWidget] = None,
        mode: str = "deg",   # "deg" | "pca"
    ) -> None:
        super().__init__(parent)
        self._dm = data_manager
        self._mode = mode
        self.setWindowTitle("PCA Analysis" if mode == "pca" else "Differential Expression")
        self.setMinimumWidth(440)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Dataset selection
        ds_group = QGroupBox("Dataset")
        ds_form = QFormLayout(ds_group)
        self._ds_combo = QComboBox()
        for ds in self._dm.datasets:
            self._ds_combo.addItem(ds.name, ds.dataset_id)
        ds_form.addRow("Dataset:", self._ds_combo)
        layout.addWidget(ds_group)

        if self._mode == "deg":
            self._build_deg_ui(layout)
        else:
            self._build_pca_ui(layout)

        # Progress
        self._progress = QProgressBar()
        self._progress.hide()
        layout.addWidget(self._progress)

        self._status = QLabel("")
        layout.addWidget(self._status)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self._run_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        self._run_btn.setText("Run")
        buttons.accepted.connect(self._run)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _build_deg_ui(self, layout) -> None:
        deg_group = QGroupBox("DEG Settings")
        form = QFormLayout(deg_group)

        self._contrast_a = _SampleListWidget()
        self._contrast_b = _SampleListWidget()

        form.addRow("Group A samples:", self._contrast_a)
        form.addRow("Group B samples:", self._contrast_b)

        self._method = QComboBox()
        self._method.addItems(["ttest", "wilcoxon"])
        form.addRow("Test method:", self._method)

        self._correction = QComboBox()
        self._correction.addItems(["fdr_bh", "bonferroni", "holm", "fdr_by"])
        form.addRow("Correction:", self._correction)

        self._log_transform = QCheckBox("Log-normalize before test")
        self._log_transform.setChecked(True)
        form.addRow("", self._log_transform)

        self._contrast_name = QLineEdit("GroupA_vs_GroupB")
        form.addRow("Contrast name:", self._contrast_name)

        layout.addWidget(deg_group)

        # Populate sample lists when dataset changes
        self._ds_combo.currentIndexChanged.connect(self._populate_samples)
        self._populate_samples()

    def _build_pca_ui(self, layout) -> None:
        pca_group = QGroupBox("PCA Settings")
        form = QFormLayout(pca_group)

        self._n_components = QSpinBox()
        self._n_components.setRange(2, 50)
        self._n_components.setValue(10)
        form.addRow("# Components:", self._n_components)

        self._scale = QCheckBox("Scale (z-score) genes")
        self._scale.setChecked(True)
        form.addRow("", self._scale)

        self._log_pca = QCheckBox("Log-normalize before PCA")
        self._log_pca.setChecked(True)
        form.addRow("", self._log_pca)

        layout.addWidget(pca_group)

    def _populate_samples(self) -> None:
        did = self._ds_combo.currentData()
        ds = self._dm.get_dataset(did) if did else None
        samples = ds.sample_names if ds else []
        if hasattr(self, "_contrast_a"):
            self._contrast_a.set_items(samples)
        if hasattr(self, "_contrast_b"):
            self._contrast_b.set_items(samples)

    def _run(self) -> None:
        did = self._ds_combo.currentData()
        ds = self._dm.get_dataset(did)
        if ds is None or ds.counts is None:
            QMessageBox.warning(self, "No Data", "Please load a dataset with count data first.")
            return

        self._run_btn.setEnabled(False)
        self._progress.show()
        self._progress.setRange(0, 0)

        if self._mode == "deg":
            self._run_deg(ds)
        else:
            self._run_pca(ds)

    def _run_deg(self, ds) -> None:
        from bioplot.core.analysis_engine import run_deg

        group_a = self._contrast_a.selected_items()
        group_b = self._contrast_b.selected_items()

        if not group_a or not group_b:
            QMessageBox.warning(self, "Selection", "Select at least one sample per group.")
            self._run_btn.setEnabled(True)
            self._progress.hide()
            return

        contrast_name = self._contrast_name.text() or "Group_A_vs_B"

        worker = AnalysisWorker(
            run_deg, ds.counts, group_a, group_b,
            method=self._method.currentText(),
            correction=self._correction.currentText(),
            log_transform=self._log_transform.isChecked(),
        )
        worker.signals.progress.connect(self._on_progress)
        worker.signals.result.connect(
            lambda tbl: self._on_deg_done(ds.dataset_id, contrast_name, tbl)
        )
        worker.signals.error.connect(self._on_error)
        QThreadPool.globalInstance().start(worker)

    def _run_pca(self, ds) -> None:
        from bioplot.core.analysis_engine import run_pca

        n_comp = self._n_components.value()
        worker = AnalysisWorker(
            run_pca, ds.counts,
            n_components=n_comp,
            log_transform=self._log_pca.isChecked(),
            scale=self._scale.isChecked(),
        )
        worker.signals.progress.connect(self._on_progress)
        worker.signals.result.connect(
            lambda res: self._on_pca_done(ds.dataset_id, res)
        )
        worker.signals.error.connect(self._on_error)
        QThreadPool.globalInstance().start(worker)

    def _on_progress(self, pct: int) -> None:
        self._progress.setRange(0, 100)
        self._progress.setValue(pct)

    def _on_deg_done(self, dataset_id, contrast_name, table) -> None:
        ds = self._dm.get_dataset(dataset_id)
        if ds:
            result = DEGResult(
                contrast_name=contrast_name,
                gene_col="gene",
                log2fc_col="log2FC",
                pvalue_col="pvalue",
                padj_col="padj",
                table=table,
            )
            ds.deg_results[contrast_name] = result
            self._dm.dataset_updated.emit(dataset_id)
        self._status.setText(f"DEG complete: {contrast_name}")
        self._progress.hide()
        self.accept()

    def _on_pca_done(self, dataset_id, res) -> None:
        coords, evr, loadings = res
        ds = self._dm.get_dataset(dataset_id)
        if ds:
            result = PCAResult(
                coords=coords,
                explained_variance_ratio=evr,
                loadings=loadings,
                sample_names=ds.sample_names,
                gene_names=ds.gene_names,
                n_components=coords.shape[1],
            )
            ds.pca_results["default"] = result
            self._dm.dataset_updated.emit(dataset_id)
        self._status.setText("PCA complete")
        self._progress.hide()
        self.accept()

    def _on_error(self, msg: str) -> None:
        QMessageBox.critical(self, "Analysis Error", msg)
        self._run_btn.setEnabled(True)
        self._progress.hide()


class _SampleListWidget(QListWidget):
    """Multi-select list for sample groups."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.setMaximumHeight(120)

    def set_items(self, items: list[str]) -> None:
        self.clear()
        for item in items:
            self.addItem(item)

    def selected_items(self) -> list[str]:
        return [i.text() for i in self.selectedItems()]



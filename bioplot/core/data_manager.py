"""DataManager — observable registry of BioDataset objects with Qt signals."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd
from PySide6.QtCore import QObject, QThreadPool, Signal

from bioplot.models.dataset import BioDataset
from bioplot.core.worker import LoadWorker


class DataManager(QObject):
    """Central registry for all loaded datasets.

    Emits Qt signals so the UI can react without polling.
    """

    dataset_added = Signal(str)       # dataset_id
    dataset_removed = Signal(str)     # dataset_id
    dataset_renamed = Signal(str)     # dataset_id
    dataset_updated = Signal(str)     # dataset_id (e.g. after analysis)
    load_progress = Signal(str, int)  # dataset_id, 0-100
    load_error = Signal(str, str)     # dataset_id, message

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._datasets: dict[str, BioDataset] = {}
        self._pool = QThreadPool.globalInstance()

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def add_dataset(self, dataset: BioDataset) -> None:
        self._datasets[dataset.dataset_id] = dataset
        self.dataset_added.emit(dataset.dataset_id)

    def remove_dataset(self, dataset_id: str) -> None:
        if dataset_id in self._datasets:
            del self._datasets[dataset_id]
            self.dataset_removed.emit(dataset_id)

    def get_dataset(self, dataset_id: str) -> Optional[BioDataset]:
        return self._datasets.get(dataset_id)

    def rename_dataset(self, dataset_id: str, new_name: str) -> None:
        ds = self._datasets.get(dataset_id)
        if ds:
            ds.name = new_name
            self.dataset_renamed.emit(dataset_id)

    def duplicate_dataset(self, dataset_id: str) -> Optional[str]:
        ds = self._datasets.get(dataset_id)
        if ds is None:
            return None
        import copy, uuid
        new_ds = copy.deepcopy(ds)
        new_ds.dataset_id = str(uuid.uuid4())
        new_ds.name = f"{ds.name} (copy)"
        self.add_dataset(new_ds)
        return new_ds.dataset_id

    @property
    def datasets(self) -> list[BioDataset]:
        return list(self._datasets.values())

    @property
    def dataset_ids(self) -> list[str]:
        return list(self._datasets.keys())

    # ── Async loading ─────────────────────────────────────────────────────────

    def load_file_async(self, path: str | Path) -> str:
        """Start async file load; returns a provisional dataset_id."""
        import uuid
        path = Path(path)
        dataset_id = str(uuid.uuid4())

        # Create a placeholder dataset immediately
        ds = BioDataset(
            name=path.stem,
            source_path=path,
            dataset_id=dataset_id,
            file_format=path.suffix.lstrip(".").lower(),
        )
        self._datasets[dataset_id] = ds
        self.dataset_added.emit(dataset_id)

        sep = "\t" if path.suffix.lower() in (".tsv", ".txt") else ","

        if path.suffix.lower() == ".h5ad":
            self._load_h5ad_async(ds)
        else:
            worker = LoadWorker(str(path), sep=sep)
            worker.signals.progress.connect(
                lambda p: self.load_progress.emit(dataset_id, p)
            )
            worker.signals.result.connect(
                lambda df: self._on_csv_loaded(dataset_id, df)
            )
            worker.signals.error.connect(
                lambda msg: self.load_error.emit(dataset_id, msg)
            )
            self._pool.start(worker)

        return dataset_id

    def _on_csv_loaded(self, dataset_id: str, df: pd.DataFrame) -> None:
        ds = self._datasets.get(dataset_id)
        if ds is None:
            return
        ds.counts = df
        self.dataset_updated.emit(dataset_id)

    def _load_h5ad_async(self, ds: BioDataset) -> None:
        from bioplot.core.worker import FunctionWorker

        def _load(path: Path) -> object:
            try:
                import anndata as ad  # type: ignore
                return ad.read_h5ad(str(path), backed="r")
            except ImportError as e:
                raise RuntimeError(
                    "scanpy/anndata not installed. Install with: pip install scanpy anndata"
                ) from e

        worker = FunctionWorker(_load, ds.source_path)
        worker.signals.result.connect(
            lambda adata: self._on_h5ad_loaded(ds.dataset_id, adata)
        )
        worker.signals.error.connect(
            lambda msg: self.load_error.emit(ds.dataset_id, msg)
        )
        self._pool.start(worker)

    def _on_h5ad_loaded(self, dataset_id: str, adata: object) -> None:
        ds = self._datasets.get(dataset_id)
        if ds is None:
            return
        ds.h5ad_path = ds.source_path
        # Store adata reference in extras for plot engine
        ds.description = f"AnnData: {adata}"  # type: ignore[union-attr]
        self.dataset_updated.emit(dataset_id)

    # ── Serialization support ─────────────────────────────────────────────────

    def to_dict(self) -> dict:
        """Minimal snapshot for session saving (paths only, not raw data)."""
        return {
            ds.dataset_id: {
                "name": ds.name,
                "source_path": str(ds.source_path),
                "file_format": ds.file_format,
                "description": ds.description,
            }
            for ds in self._datasets.values()
        }

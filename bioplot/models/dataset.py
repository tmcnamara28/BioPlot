"""BioDataset and result dataclasses."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd


@dataclass
class DEGResult:
    """Differential expression result for one contrast."""
    contrast_name: str
    gene_col: str
    log2fc_col: str
    pvalue_col: str
    padj_col: str
    table: pd.DataFrame   # full DEG table with all stats

    @property
    def n_up(self) -> int:
        mask = (self.table[self.padj_col] < 0.05) & (self.table[self.log2fc_col] > 1)
        return int(mask.sum())

    @property
    def n_down(self) -> int:
        mask = (self.table[self.padj_col] < 0.05) & (self.table[self.log2fc_col] < -1)
        return int(mask.sum())


@dataclass
class PCAResult:
    """PCA decomposition result."""
    coords: np.ndarray          # (n_samples, n_components)
    explained_variance_ratio: np.ndarray
    loadings: np.ndarray        # (n_genes, n_components)
    sample_names: list[str]
    gene_names: list[str]
    n_components: int = 10


@dataclass
class BioDataset:
    """Observable dataset holding raw counts, metadata, and analysis results."""
    name: str
    source_path: Path
    dataset_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Raw expression: rows=genes, cols=samples (or cells for scRNA-seq)
    counts: Optional[pd.DataFrame] = None

    # Optional normalised matrix
    normalized: Optional[pd.DataFrame] = None

    # Sample/cell metadata
    metadata: Optional[pd.DataFrame] = None

    # Gene annotation / rowData
    gene_info: Optional[pd.DataFrame] = None

    # Cached analysis results keyed by contrast or parameter string
    deg_results: dict[str, DEGResult] = field(default_factory=dict)
    pca_results: dict[str, PCAResult] = field(default_factory=dict)

    # File format detected at import
    file_format: str = "csv"   # csv | tsv | h5ad

    # For h5ad, hold path only (backed mode); counts is None
    h5ad_path: Optional[Path] = None

    # Human-readable description
    description: str = ""

    # ── Convenience properties ────────────────────────────────────────────────

    @property
    def n_genes(self) -> int:
        if self.counts is not None:
            return len(self.counts)
        return 0

    @property
    def n_samples(self) -> int:
        if self.counts is not None:
            return len(self.counts.columns)
        return 0

    @property
    def sample_names(self) -> list[str]:
        if self.counts is not None:
            return list(self.counts.columns)
        return []

    @property
    def gene_names(self) -> list[str]:
        if self.counts is not None:
            return list(self.counts.index)
        return []

    def summary(self) -> str:
        parts = [f"{self.n_genes} genes × {self.n_samples} samples"]
        if self.deg_results:
            parts.append(f"{len(self.deg_results)} DEG contrast(s)")
        if self.pca_results:
            parts.append("PCA computed")
        return ", ".join(parts)

"""Unit tests for DataManager (no Qt event loop required for CRUD tests)."""
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from bioplot.models.dataset import BioDataset


# Minimal DataManager tests that don't require a running Qt app
# We mock the Qt signals so no QApplication is needed.

def _make_dataset(name="TestDS") -> BioDataset:
    ds = BioDataset(
        name=name,
        source_path=Path("/tmp/test.csv"),
        dataset_id=str(uuid.uuid4()),
    )
    counts = pd.DataFrame(
        {"Sample1": [10, 20, 30], "Sample2": [15, 25, 35]},
        index=["GeneA", "GeneB", "GeneC"],
    )
    ds.counts = counts
    return ds


class TestBioDataset:
    def test_properties(self):
        ds = _make_dataset()
        assert ds.n_genes == 3
        assert ds.n_samples == 2
        assert "Sample1" in ds.sample_names
        assert "GeneA" in ds.gene_names

    def test_summary(self):
        ds = _make_dataset()
        s = ds.summary()
        assert "3 genes" in s
        assert "2 samples" in s

    def test_no_counts(self):
        ds = BioDataset(name="empty", source_path=Path("/tmp/x.csv"))
        assert ds.n_genes == 0
        assert ds.n_samples == 0
        assert ds.sample_names == []

    def test_unique_ids(self):
        ids = {_make_dataset().dataset_id for _ in range(100)}
        assert len(ids) == 100

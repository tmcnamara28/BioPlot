"""Unit tests for PlotEngine and all plot renderers (headless)."""
import matplotlib
matplotlib.use("Agg")

import numpy as np
import pandas as pd
import pytest

from bioplot.core.plot_engine import PlotEngine
from bioplot.models.dataset import BioDataset, DEGResult, PCAResult
from bioplot.models.plot_config import PlotConfig
from pathlib import Path


@pytest.fixture
def deg_dataset() -> BioDataset:
    """Dataset with pre-computed DEG table (like sample_DEG.csv)."""
    ds = BioDataset(name="DEG", source_path=Path("/tmp/deg.csv"))
    table = pd.DataFrame({
        "log2FC": np.concatenate([
            np.random.default_rng(0).normal(3, 0.5, 20),    # up
            np.random.default_rng(1).normal(-3, 0.5, 20),   # down
            np.random.default_rng(2).normal(0, 0.3, 60),    # ns
        ]),
        "pvalue": np.concatenate([
            np.full(20, 1e-6), np.full(20, 1e-6), np.full(60, 0.5)
        ]),
        "padj": np.concatenate([
            np.full(20, 1e-5), np.full(20, 1e-5), np.full(60, 0.8)
        ]),
        "neg_log10_padj": np.concatenate([
            np.full(20, 5.0), np.full(20, 5.0), np.full(60, 0.1)
        ]),
        "mean_A": np.random.default_rng(3).exponential(100, 100),
        "mean_B": np.random.default_rng(4).exponential(100, 100),
    }, index=[f"Gene{i:03d}" for i in range(100)])

    result = DEGResult(
        contrast_name="KO_vs_WT",
        gene_col="gene", log2fc_col="log2FC",
        pvalue_col="pvalue", padj_col="padj",
        table=table,
    )
    ds.deg_results["KO_vs_WT"] = result
    return ds


@pytest.fixture
def counts_dataset() -> BioDataset:
    rng = np.random.default_rng(42)
    ds = BioDataset(name="Counts", source_path=Path("/tmp/counts.csv"))
    ds.counts = pd.DataFrame(
        rng.negative_binomial(20, 0.5, (50, 8)),
        index=[f"Gene{i:03d}" for i in range(50)],
        columns=[f"S{i}" for i in range(8)],
    ).astype(float)
    return ds


@pytest.fixture
def pca_dataset(counts_dataset) -> BioDataset:
    from bioplot.core.analysis_engine import run_pca
    coords, evr, loadings = run_pca(counts_dataset.counts, n_components=5)
    counts_dataset.pca_results["default"] = PCAResult(
        coords=coords, explained_variance_ratio=evr, loadings=loadings,
        sample_names=counts_dataset.sample_names,
        gene_names=counts_dataset.gene_names,
        n_components=5,
    )
    return counts_dataset


class TestVolcanoPlot:
    def test_renders_with_data(self, deg_dataset):
        config = PlotConfig(plot_type="volcano")
        fig = PlotEngine.render(config, deg_dataset)
        assert len(fig.axes) >= 1

    def test_renders_placeholder(self):
        config = PlotConfig(plot_type="volcano")
        fig = PlotEngine.render(config, None)
        assert len(fig.axes) >= 1

    def test_axes_count(self, deg_dataset):
        config = PlotConfig(plot_type="volcano")
        fig = PlotEngine.render(config, deg_dataset)
        # Main axis + optional legend axes
        assert len(fig.axes) >= 1


class TestMAPlot:
    def test_renders_with_data(self, deg_dataset):
        config = PlotConfig(plot_type="ma")
        fig = PlotEngine.render(config, deg_dataset)
        assert len(fig.axes) >= 1


class TestScatterPlot:
    def test_renders_with_data(self, counts_dataset):
        config = PlotConfig(plot_type="scatter")
        config.extras["x_col"] = "Gene000"
        config.extras["y_col"] = "Gene001"
        fig = PlotEngine.render(config, counts_dataset)
        assert len(fig.axes) >= 1

    def test_placeholder_without_data(self):
        config = PlotConfig(plot_type="scatter")
        fig = PlotEngine.render(config, None)
        assert len(fig.axes) >= 1


class TestPCAPlot:
    def test_renders_with_pca_data(self, pca_dataset):
        config = PlotConfig(plot_type="pca")
        fig = PlotEngine.render(config, pca_dataset)
        assert len(fig.axes) >= 1

    def test_placeholder_without_pca(self, counts_dataset):
        config = PlotConfig(plot_type="pca")
        fig = PlotEngine.render(config, counts_dataset)
        # Should render placeholder since no PCA result
        assert len(fig.axes) >= 1


class TestViolinPlot:
    def test_renders(self, counts_dataset):
        config = PlotConfig(plot_type="violin")
        config.extras["genes"] = ["Gene000", "Gene001", "Gene002"]
        fig = PlotEngine.render(config, counts_dataset)
        assert len(fig.axes) >= 1


class TestBarPlot:
    def test_renders(self, counts_dataset):
        config = PlotConfig(plot_type="barplot")
        config.extras["genes"] = ["Gene000", "Gene001", "Gene002"]
        fig = PlotEngine.render(config, counts_dataset)
        assert len(fig.axes) >= 1


class TestHeatmapPlot:
    def test_renders(self, counts_dataset):
        config = PlotConfig(plot_type="heatmap")
        config.extras["top_n_genes"] = 10
        fig = PlotEngine.render(config, counts_dataset)
        assert fig is not None


class TestPlotEngineRegistry:
    def test_unknown_type_raises(self):
        config = PlotConfig(plot_type="totally_unknown_xyz")
        with pytest.raises(ValueError, match="Unknown plot type"):
            PlotEngine.render(config, None)

    def test_available_types(self):
        types = PlotEngine.available_plot_types()
        for expected in ["volcano", "ma", "heatmap", "pca", "violin", "scatter", "barplot"]:
            assert expected in types

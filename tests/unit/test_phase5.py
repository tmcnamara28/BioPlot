"""Phase 5 unit tests — headless, no Qt required."""
import matplotlib
matplotlib.use("Agg")

import numpy as np
import pandas as pd
import pytest
from pathlib import Path

from bioplot.core.plot_engine import PlotEngine
from bioplot.models.dataset import BioDataset, DEGResult
from bioplot.models.plot_config import PlotConfig, AnnotationItem
from bioplot.constants import COLORBLIND_MATRICES


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def counts_ds():
    rng = np.random.default_rng(0)
    ds = BioDataset(name="Counts", source_path=Path("/tmp/c.csv"))
    ds.counts = pd.DataFrame(
        rng.negative_binomial(20, 0.5, (30, 6)).astype(float),
        index=[f"G{i}" for i in range(30)],
        columns=[f"S{i}" for i in range(6)],
    )
    ds.metadata = pd.DataFrame(
        {"group": ["A", "A", "A", "B", "B", "B"]},
        index=[f"S{i}" for i in range(6)],
    )
    return ds


@pytest.fixture
def deg_ds():
    rng = np.random.default_rng(1)
    ds = BioDataset(name="DEG", source_path=Path("/tmp/d.csv"))
    n = 80
    table = pd.DataFrame({
        "log2FC": np.concatenate([rng.normal(3, .5, 20), rng.normal(-3, .5, 20), rng.normal(0, .3, 40)]),
        "pvalue": np.concatenate([np.full(40, 1e-6), rng.uniform(.1, 1, 40)]),
        "padj":   np.concatenate([np.full(40, 1e-5), rng.uniform(.1, 1, 40)]),
        "neg_log10_padj": np.concatenate([np.full(40, 5.0), rng.uniform(0, 1, 40)]),
        "mean_A": rng.exponential(50, n),
        "mean_B": rng.exponential(50, n),
    }, index=[f"Gene{i:03d}" for i in range(n)])
    ds.deg_results["contrast"] = DEGResult(
        contrast_name="contrast", gene_col="gene",
        log2fc_col="log2FC", pvalue_col="pvalue", padj_col="padj",
        table=table,
    )
    ds.counts = table
    return ds


# ── DotPlot ───────────────────────────────────────────────────────────────────

class TestDotPlot:
    def test_renders_with_data(self, counts_ds):
        config = PlotConfig(plot_type="dotplot")
        config.extras["genes"] = [f"G{i}" for i in range(5)]
        fig = PlotEngine.render(config, counts_ds)
        assert fig is not None
        assert len(fig.axes) >= 1

    def test_placeholder_without_metadata(self):
        ds = BioDataset(name="X", source_path=Path("/tmp/x.csv"))
        ds.counts = pd.DataFrame({"S1": [1.0]}, index=["G1"])
        # No metadata → placeholder
        config = PlotConfig(plot_type="dotplot")
        fig = PlotEngine.render(config, ds)
        assert fig is not None

    def test_placeholder_without_data(self):
        config = PlotConfig(plot_type="dotplot")
        fig = PlotEngine.render(config, None)
        assert fig is not None


# ── Heatmap k-means ───────────────────────────────────────────────────────────

class TestHeatmapKmeans:
    def test_kmeans_renders(self, counts_ds):
        config = PlotConfig(plot_type="heatmap")
        config.extras["cluster_method"] = "kmeans"
        config.extras["n_clusters_row"] = 2
        config.extras["n_clusters_col"] = 2
        config.extras["top_n_genes"] = 20
        fig = PlotEngine.render(config, counts_ds)
        assert fig is not None

    def test_no_cluster_renders(self, counts_ds):
        config = PlotConfig(plot_type="heatmap")
        config.extras["cluster_method"] = "none"
        fig = PlotEngine.render(config, counts_ds)
        assert fig is not None

    def test_hierarchical_still_works(self, counts_ds):
        config = PlotConfig(plot_type="heatmap")
        config.extras["cluster_method"] = "hierarchical"
        config.extras["top_n_genes"] = 10
        fig = PlotEngine.render(config, counts_ds)
        assert fig is not None


# ── Annotations ───────────────────────────────────────────────────────────────

class TestAnnotations:
    def test_text_annotation_applied(self, deg_ds):
        config = PlotConfig(plot_type="volcano")
        config.annotations.append(
            AnnotationItem(kind="text", x=0.5, y=0.5, text="Label", coords="axes")
        )
        fig = PlotEngine.render(config, deg_ds)
        # Text should be on the axes
        texts = [t.get_text() for ax in fig.axes for t in ax.texts]
        assert any("Label" in t for t in texts)

    def test_arrow_annotation(self, deg_ds):
        config = PlotConfig(plot_type="volcano")
        config.annotations.append(
            AnnotationItem(kind="arrow", x=0.0, y=0.0, x2=1.0, y2=2.0,
                           text="Arrow", coords="data")
        )
        fig = PlotEngine.render(config, deg_ds)
        assert fig is not None

    def test_annotation_round_trip(self):
        config = PlotConfig()
        config.annotations.append(
            AnnotationItem(kind="text", x=1.0, y=2.0, text="TP53",
                           font_size=8.0, color="red", coords="data")
        )
        restored = PlotConfig.from_json(config.to_json())
        assert len(restored.annotations) == 1
        a = restored.annotations[0]
        assert a.text == "TP53"
        assert a.color == "red"
        assert a.kind == "text"

    def test_multiple_annotations(self, deg_ds):
        config = PlotConfig(plot_type="scatter")
        for i in range(5):
            config.annotations.append(
                AnnotationItem(kind="text", x=float(i), y=float(i),
                               text=f"Ann{i}", coords="axes")
            )
        fig = PlotEngine.render(config, deg_ds)
        texts = [t.get_text() for ax in fig.axes for t in ax.texts]
        assert sum("Ann" in t for t in texts) == 5


# ── Colorblindness matrices ───────────────────────────────────────────────────

class TestColorblindMatrices:
    def test_all_modes_present(self):
        for mode in ("deuteranopia", "protanopia", "tritanopia"):
            assert mode in COLORBLIND_MATRICES

    def test_matrix_shapes(self):
        for mode, mat in COLORBLIND_MATRICES.items():
            arr = np.array(mat)
            assert arr.shape == (3, 3), f"{mode} matrix must be 3×3"

    def test_simulation_preserves_shape(self):
        """Pixel transformation does not change image dimensions."""
        rng = np.random.default_rng(0)
        h, w = 100, 150
        rgba = rng.integers(0, 255, (h, w, 4), dtype=np.uint8)
        rgba[..., 3] = 255

        mat = np.array(COLORBLIND_MATRICES["deuteranopia"], dtype=np.float32)
        rgb = rgba[..., :3].astype(np.float32) / 255.0
        simulated = np.clip(rgb @ mat.T, 0, 1)
        result = rgba.copy()
        result[..., :3] = (simulated * 255).astype(np.uint8)

        assert result.shape == rgba.shape
        assert result.dtype == np.uint8

    def test_white_stays_white(self):
        """Pure white is perceptually white under all simulations."""
        white = np.ones((1, 1, 3), dtype=np.float32)
        for mode, mat in COLORBLIND_MATRICES.items():
            arr = np.array(mat, dtype=np.float32)
            out = np.clip(white @ arr.T, 0, 1)
            assert np.allclose(out, 1.0, atol=0.05), f"{mode}: white not preserved"

    def test_black_stays_black(self):
        black = np.zeros((1, 1, 3), dtype=np.float32)
        for mode, mat in COLORBLIND_MATRICES.items():
            arr = np.array(mat, dtype=np.float32)
            out = np.clip(black @ arr.T, 0, 1)
            assert np.allclose(out, 0.0, atol=0.05), f"{mode}: black not preserved"


# ── PlotEngine dotplot registration ──────────────────────────────────────────

class TestPlotEnginePhase5:
    def test_dotplot_registered(self):
        assert "dotplot" in PlotEngine.available_plot_types()

    def test_umap_registered(self):
        assert "umap" in PlotEngine.available_plot_types()

    def test_umap_placeholder_without_scanpy(self, monkeypatch):
        """UMAPPlot returns a placeholder when scanpy is missing."""
        import sys
        monkeypatch.setitem(sys.modules, "scanpy", None)
        config = PlotConfig(plot_type="umap")
        fig = PlotEngine.render(config, None)
        assert fig is not None

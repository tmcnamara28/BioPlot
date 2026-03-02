"""Integration tests: full pipeline CSV → DEG → plot → export."""
import matplotlib
matplotlib.use("Agg")

import os
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from bioplot.assets.sample_data import SAMPLE_DEG_PATH
from bioplot.core.analysis_engine import run_deg, run_pca
from bioplot.core.export_engine import ExportEngine
from bioplot.core.plot_engine import PlotEngine
from bioplot.core.preset_manager import PresetManager
from bioplot.core.session_manager import SessionManager
from bioplot.models.dataset import BioDataset, DEGResult
from bioplot.models.plot_config import PlotConfig


@pytest.fixture
def sample_deg_dataset() -> BioDataset:
    """Load the bundled sample DEG CSV."""
    ds = BioDataset(name="SampleDEG", source_path=SAMPLE_DEG_PATH)
    df = pd.read_csv(SAMPLE_DEG_PATH, index_col=0)
    ds.counts = df
    # Treat the DEG table itself as the result
    result = DEGResult(
        contrast_name="sample",
        gene_col="gene",
        log2fc_col="log2FC",
        pvalue_col="pvalue",
        padj_col="padj",
        table=df,
    )
    ds.deg_results["sample"] = result
    return ds


class TestVolcanoPipeline:
    def test_volcano_from_sample_data(self, sample_deg_dataset, tmp_path):
        config = PlotConfig(plot_type="volcano")
        config.stat.pvalue_threshold = 0.05
        config.stat.fc_threshold = 1.0

        fig = PlotEngine.render(config, sample_deg_dataset)
        assert fig is not None
        assert len(fig.axes) >= 1

        pdf_path = tmp_path / "volcano.pdf"
        result = ExportEngine.export_pdf(fig, pdf_path, dpi=72)
        assert result.exists()
        with open(result, "rb") as f:
            assert f.read(4) == b"%PDF"

    def test_svg_valid_xml(self, sample_deg_dataset, tmp_path):
        config = PlotConfig(plot_type="volcano")
        fig = PlotEngine.render(config, sample_deg_dataset)
        svg_path = tmp_path / "volcano.svg"
        ExportEngine.export_svg(fig, svg_path)
        content = svg_path.read_text()
        assert "<?xml" in content or "<svg" in content


class TestDEGPipeline:
    def test_full_deg_computation(self):
        rng = np.random.default_rng(7)
        n_genes = 200
        # Group B has 2x expression for first 20 genes
        counts_a = rng.negative_binomial(30, 0.5, (n_genes, 5)).astype(float)
        counts_b = rng.negative_binomial(30, 0.5, (n_genes, 5)).astype(float)
        counts_b[:20] *= 4  # inflate first 20

        df = pd.DataFrame(
            np.hstack([counts_a, counts_b]),
            index=[f"G{i}" for i in range(n_genes)],
            columns=[f"A{i}" for i in range(5)] + [f"B{i}" for i in range(5)],
        )

        result = run_deg(df, [f"A{i}" for i in range(5)], [f"B{i}" for i in range(5)])

        sig = result[result["padj"] < 0.05]
        # Most of the 20 inflated genes should be detected
        assert len(sig) >= 5

        # p-value distribution sanity: null genes should have mostly large p-values
        null_genes = result.iloc[50:]
        assert null_genes["pvalue"].median() > 0.1


class TestSessionPipeline:
    def test_save_load_session(self, tmp_path):
        """PlotConfig save/load produces identical configs."""
        from unittest.mock import MagicMock

        configs = [
            PlotConfig(plot_type="volcano"),
            PlotConfig(plot_type="pca"),
        ]
        configs[0].x_axis.label = "log₂FC"
        configs[0].stat.pvalue_threshold = 0.01
        configs[1].figure.width_mm = 120.0

        # Mock DataManager
        dm = MagicMock()
        dm.to_dict.return_value = {}

        session_path = tmp_path / "test.biop"
        SessionManager.save(session_path, dm, configs)

        assert session_path.exists()

        state, loaded_configs = SessionManager.load(session_path)
        assert len(loaded_configs) == 2
        assert loaded_configs[0].plot_type == "volcano"
        assert loaded_configs[0].x_axis.label == "log₂FC"
        assert loaded_configs[0].stat.pvalue_threshold == 0.01
        assert loaded_configs[1].figure.width_mm == 120.0


class TestPresetPipeline:
    def test_nature_preset_applied(self):
        pm = PresetManager()
        config = PlotConfig()
        nature = pm.apply_preset(config, "nature")
        assert nature.font.axis_label_size < config.font.axis_label_size

    def test_preset_does_not_mutate_original(self):
        pm = PresetManager()
        config = PlotConfig()
        original_size = config.font.axis_label_size
        pm.apply_preset(config, "nature")
        assert config.font.axis_label_size == original_size

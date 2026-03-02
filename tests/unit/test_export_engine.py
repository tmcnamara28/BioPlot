"""Unit tests for ExportEngine."""
import tempfile
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pytest

from bioplot.core.export_engine import ExportEngine, mm_to_inches


class TestMmToInches:
    def test_known_value(self):
        assert abs(mm_to_inches(25.4) - 1.0) < 1e-9

    def test_89mm(self):
        assert abs(mm_to_inches(89.0) - 3.504) < 0.01


class TestExportEngine:
    @pytest.fixture
    def simple_fig(self):
        fig, ax = plt.subplots(figsize=(4, 3))
        ax.plot([1, 2, 3], [4, 5, 6])
        yield fig
        plt.close(fig)

    def test_export_png(self, simple_fig, tmp_path):
        path = tmp_path / "test.png"
        result = ExportEngine.export_png(simple_fig, path, dpi=72)
        assert result.exists()
        assert result.suffix == ".png"
        assert result.stat().st_size > 0

    def test_export_pdf(self, simple_fig, tmp_path):
        path = tmp_path / "test.pdf"
        result = ExportEngine.export_pdf(simple_fig, path, dpi=72)
        assert result.exists()
        # PDF magic bytes
        with open(result, "rb") as f:
            header = f.read(4)
        assert header == b"%PDF"

    def test_export_svg(self, simple_fig, tmp_path):
        path = tmp_path / "test.svg"
        result = ExportEngine.export_svg(simple_fig, path)
        assert result.exists()
        content = result.read_text()
        assert "<svg" in content

    def test_export_with_size_override(self, simple_fig, tmp_path):
        path = tmp_path / "test.png"
        ExportEngine.export(simple_fig, path, fmt="png", width_mm=89, height_mm=89, dpi=72)
        assert path.exists()

    def test_unsupported_format(self, simple_fig, tmp_path):
        with pytest.raises(ValueError, match="Unsupported format"):
            ExportEngine.export(simple_fig, tmp_path / "test.xyz", fmt="xyz")

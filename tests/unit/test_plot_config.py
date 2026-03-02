"""Unit tests for PlotConfig serialization and sub-configs."""
import json
import pytest

from bioplot.models.plot_config import (
    PlotConfig, AxisConfig, ColorConfig, FontConfig,
    StatConfig, MarkerConfig, FigureConfig, AnnotationItem,
)


class TestAxisConfig:
    def test_defaults(self):
        cfg = AxisConfig()
        assert cfg.scale == "linear"
        assert cfg.show_grid is False
        assert cfg.limits is None

    def test_custom(self):
        cfg = AxisConfig(label="log₂FC", scale="log", limits=(-5.0, 5.0))
        assert cfg.label == "log₂FC"
        assert cfg.limits == (-5.0, 5.0)


class TestPlotConfigSerialization:
    def test_round_trip_json(self):
        config = PlotConfig(plot_type="volcano")
        config.x_axis.label = "log₂FC"
        config.y_axis.label = "-log₁₀ p"
        config.stat.pvalue_threshold = 0.01
        config.stat.fc_threshold = 1.5
        config.figure.width_mm = 120.0

        json_str = config.to_json()
        data = json.loads(json_str)
        assert data["plot_type"] == "volcano"
        assert data["figure"]["width_mm"] == 120.0

        restored = PlotConfig.from_json(json_str)
        assert restored.plot_type == "volcano"
        assert restored.x_axis.label == "log₂FC"
        assert restored.stat.pvalue_threshold == 0.01
        assert restored.stat.fc_threshold == 1.5
        assert restored.figure.width_mm == 120.0

    def test_clone_is_independent(self):
        config = PlotConfig()
        clone = config.clone()
        clone.x_axis.label = "mutated"
        assert config.x_axis.label == ""

    def test_all_plot_types_round_trip(self):
        for pt in ["volcano", "ma", "heatmap", "pca", "violin", "scatter", "barplot", "umap"]:
            config = PlotConfig(plot_type=pt)
            restored = PlotConfig.from_json(config.to_json())
            assert restored.plot_type == pt

    def test_annotations_serialization(self):
        config = PlotConfig()
        config.annotations.append(
            AnnotationItem(kind="text", x=1.0, y=2.0, text="TP53", font_size=8.0)
        )
        restored = PlotConfig.from_json(config.to_json())
        assert len(restored.annotations) == 1
        assert restored.annotations[0].text == "TP53"

    def test_extras_round_trip(self):
        config = PlotConfig()
        config.extras["contrast"] = "KO_vs_WT"
        config.extras["rcparams"] = {"axes.linewidth": 0.5}
        restored = PlotConfig.from_json(config.to_json())
        assert restored.extras["contrast"] == "KO_vs_WT"
        assert restored.extras["rcparams"]["axes.linewidth"] == 0.5

    def test_get_rcparams(self):
        config = PlotConfig()
        config.font.family = "Helvetica"
        config.font.title_size = 9.0
        rcp = config.get_rcparams()
        assert rcp["font.family"] == "Helvetica"
        assert rcp["axes.titlesize"] == 9.0


class TestColorConfig:
    def test_defaults(self):
        cfg = ColorConfig()
        assert cfg.up_color == "#d62728"
        assert cfg.alpha == 0.8


class TestStatConfig:
    def test_defaults(self):
        cfg = StatConfig()
        assert cfg.pvalue_threshold == 0.05
        assert cfg.fc_threshold == 1.0
        assert cfg.label_top_n == 10

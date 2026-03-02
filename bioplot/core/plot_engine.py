"""PlotEngine — dispatches PlotConfig + BioDataset → matplotlib Figure."""
from __future__ import annotations

from typing import TYPE_CHECKING

import matplotlib
import matplotlib.pyplot as plt

if TYPE_CHECKING:
    from matplotlib.figure import Figure
    from bioplot.models.dataset import BioDataset
    from bioplot.models.plot_config import PlotConfig


class PlotEngine:
    """Stateless dispatcher: config + data → Figure.

    All rendering runs inside ``matplotlib.rc_context`` so rcParams from
    presets don't leak between calls (thread-safe).
    """

    _REGISTRY: dict[str, str] = {
        "volcano": "bioplot.plots.volcano.VolcanoPlot",
        "ma": "bioplot.plots.ma_plot.MAPlot",
        "heatmap": "bioplot.plots.heatmap.HeatmapPlot",
        "pca": "bioplot.plots.pca.PCAPlot",
        "violin": "bioplot.plots.violin.ViolinPlot",
        "scatter": "bioplot.plots.scatter.ScatterPlot",
        "barplot": "bioplot.plots.barplot.BarPlot",
        "umap": "bioplot.plots.umap.UMAPPlot",
    }

    @classmethod
    def render(cls, config: "PlotConfig", dataset: "BioDataset | None" = None) -> "Figure":
        """Render a figure for *config* using optional *dataset*.

        Applies config rcParams inside an rc_context to avoid global state.
        """
        plot_cls = cls._load_plot_class(config.plot_type)
        rcparams = config.get_rcparams()

        with matplotlib.rc_context(rcparams):
            fig = plot_cls().render(config, dataset)

        return fig

    @classmethod
    def _load_plot_class(cls, plot_type: str):
        dotted = cls._REGISTRY.get(plot_type)
        if dotted is None:
            raise ValueError(
                f"Unknown plot type '{plot_type}'. "
                f"Available: {list(cls._REGISTRY)}"
            )
        module_path, class_name = dotted.rsplit(".", 1)
        import importlib
        module = importlib.import_module(module_path)
        return getattr(module, class_name)

    @classmethod
    def register(cls, plot_type: str, dotted_class_path: str) -> None:
        """Register a custom plot type at runtime."""
        cls._REGISTRY[plot_type] = dotted_class_path

    @classmethod
    def available_plot_types(cls) -> list[str]:
        return list(cls._REGISTRY.keys())

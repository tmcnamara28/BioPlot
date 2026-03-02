"""PlotEngine — dispatches PlotConfig + BioDataset → matplotlib Figure."""
from __future__ import annotations

from typing import TYPE_CHECKING

import matplotlib

if TYPE_CHECKING:
    from matplotlib.figure import Figure
    from bioplot.models.dataset import BioDataset
    from bioplot.models.plot_config import PlotConfig, AnnotationItem


class PlotEngine:
    """Stateless dispatcher: config + data → Figure.

    All rendering runs inside ``matplotlib.rc_context`` so rcParams from
    presets don't leak between calls (thread-safe).
    Annotations stored in ``config.annotations`` are applied after the
    plot-type-specific render, so every plot type supports them for free.
    """

    _REGISTRY: dict[str, str] = {
        "volcano":  "bioplot.plots.volcano.VolcanoPlot",
        "ma":       "bioplot.plots.ma_plot.MAPlot",
        "heatmap":  "bioplot.plots.heatmap.HeatmapPlot",
        "pca":      "bioplot.plots.pca.PCAPlot",
        "violin":   "bioplot.plots.violin.ViolinPlot",
        "scatter":  "bioplot.plots.scatter.ScatterPlot",
        "barplot":  "bioplot.plots.barplot.BarPlot",
        "umap":     "bioplot.plots.umap.UMAPPlot",
        "dotplot":  "bioplot.plots.dot_plot.DotPlot",
    }

    @classmethod
    def render(
        cls,
        config: "PlotConfig",
        dataset: "BioDataset | None" = None,
    ) -> "Figure":
        """Render a figure for *config* using optional *dataset*.

        Steps:
        1. Load the registered plot class.
        2. Build rcParams from config and apply inside rc_context.
        3. Call plot_cls().render(config, dataset).
        4. Overlay any AnnotationItems from config.annotations.
        """
        plot_cls = cls._load_plot_class(config.plot_type)
        rcparams = config.get_rcparams()

        with matplotlib.rc_context(rcparams):
            fig = plot_cls().render(config, dataset)
            if config.annotations:
                cls._apply_annotations(fig, config.annotations)

        return fig

    # ── Annotation overlay ────────────────────────────────────────────────────

    @classmethod
    def _apply_annotations(cls, fig: "Figure", annotations: "list[AnnotationItem]") -> None:
        """Draw all AnnotationItems onto the first axes of *fig*."""
        if not fig.axes:
            return
        ax = fig.axes[0]

        for ann in annotations:
            transform = (
                ax.transData if ann.coords == "data"
                else ax.transAxes if ann.coords == "axes"
                else fig.transFigure
            )
            if ann.kind == "text":
                ax.text(
                    ann.x, ann.y, ann.text,
                    fontsize=ann.font_size,
                    color=ann.color,
                    transform=transform,
                    ha="center", va="center",
                    bbox=dict(boxstyle="round,pad=0.2", fc="white", alpha=0.7, lw=0),
                )
            elif ann.kind == "arrow":
                ax.annotate(
                    ann.text,
                    xy=(ann.x2, ann.y2),
                    xytext=(ann.x, ann.y),
                    xycoords=("data" if ann.coords == "data" else "axes fraction"),
                    textcoords=("data" if ann.coords == "data" else "axes fraction"),
                    fontsize=ann.font_size,
                    color=ann.color,
                    arrowprops=dict(
                        arrowstyle=ann.arrow_style,
                        color=ann.color,
                        lw=1.0,
                    ),
                )
            elif ann.kind == "line":
                ax.plot(
                    [ann.x, ann.x2], [ann.y, ann.y2],
                    color=ann.color, lw=1.0, transform=transform,
                )

    # ── Registry helpers ──────────────────────────────────────────────────────

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

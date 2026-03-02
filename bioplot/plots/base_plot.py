"""Abstract base class for all BioPlot plot types."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

import matplotlib.pyplot as plt

if TYPE_CHECKING:
    from matplotlib.figure import Figure
    from bioplot.models.dataset import BioDataset
    from bioplot.models.plot_config import PlotConfig


class BasePlot(ABC):
    """Contract: render(config, dataset) -> Figure.

    All subclasses must be stateless; PlotEngine may call render() from
    worker threads. Only canvas.draw() must happen on the main thread.
    """

    @abstractmethod
    def render(
        self,
        config: "PlotConfig",
        dataset: "BioDataset | None" = None,
    ) -> "Figure":
        """Build and return a matplotlib Figure.

        Parameters
        ----------
        config:
            Full plot configuration (axes, colors, fonts, stats, …).
        dataset:
            Source data. May be None for placeholder/empty renders.
        """

    # ── Shared helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _make_figure(config: "PlotConfig") -> "Figure":
        """Create a Figure with dimensions and DPI from *config*."""
        from bioplot.core.export_engine import mm_to_inches
        w = mm_to_inches(config.figure.width_mm)
        h = mm_to_inches(config.figure.height_mm)
        fig = plt.figure(figsize=(w, h), dpi=config.figure.dpi)
        return fig

    @staticmethod
    def _apply_axis_config(ax, x_cfg, y_cfg) -> None:
        """Apply AxisConfig to a matplotlib Axes object."""
        if x_cfg.label:
            ax.set_xlabel(x_cfg.label)
        if y_cfg.label:
            ax.set_ylabel(y_cfg.label)

        if x_cfg.limits:
            ax.set_xlim(x_cfg.limits)
        if y_cfg.limits:
            ax.set_ylim(y_cfg.limits)

        ax.set_xscale(x_cfg.scale)
        ax.set_yscale(y_cfg.scale)

        show_grid = x_cfg.show_grid or y_cfg.show_grid
        ax.grid(show_grid)
        if show_grid:
            ax.set_axisbelow(True)
            for line in ax.get_xgridlines() + ax.get_ygridlines():
                line.set_alpha(x_cfg.grid_alpha)

        ax.tick_params(
            axis="x",
            labelsize=x_cfg.tick_size,
            rotation=x_cfg.tick_rotation,
        )
        ax.tick_params(
            axis="y",
            labelsize=y_cfg.tick_size,
            rotation=y_cfg.tick_rotation,
        )

    @staticmethod
    def _placeholder_figure(config: "PlotConfig", message: str) -> "Figure":
        """Return an empty figure with a centred message."""
        from bioplot.core.export_engine import mm_to_inches
        w = mm_to_inches(config.figure.width_mm)
        h = mm_to_inches(config.figure.height_mm)
        fig, ax = plt.subplots(figsize=(w, h), dpi=config.figure.dpi)
        ax.text(0.5, 0.5, message, ha="center", va="center", transform=ax.transAxes,
                fontsize=11, color="gray")
        ax.set_axis_off()
        return fig

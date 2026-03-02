"""Generic scatter plot."""
from __future__ import annotations

from typing import TYPE_CHECKING

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from bioplot.plots.base_plot import BasePlot

if TYPE_CHECKING:
    from matplotlib.figure import Figure
    from bioplot.models.dataset import BioDataset
    from bioplot.models.plot_config import PlotConfig


class ScatterPlot(BasePlot):
    """Generic two-column scatter plot."""

    def render(
        self,
        config: "PlotConfig",
        dataset: "BioDataset | None" = None,
    ) -> "Figure":
        x_col = config.extras.get("x_col")
        y_col = config.extras.get("y_col")
        color_col = config.extras.get("color_col")

        data = self._get_data(dataset)
        if data is None:
            return self._placeholder_figure(config, "Load tabular data for scatter plot")

        # Auto-pick first two numeric columns if not specified
        numeric_cols = data.select_dtypes(include=[np.number]).columns.tolist()
        if not x_col or x_col not in data.columns:
            x_col = numeric_cols[0] if len(numeric_cols) >= 1 else None
        if not y_col or y_col not in data.columns:
            y_col = numeric_cols[1] if len(numeric_cols) >= 2 else None

        if x_col is None or y_col is None:
            return self._placeholder_figure(config, "Need at least 2 numeric columns")

        fig = self._make_figure(config)
        ax = fig.add_subplot(111)

        x = data[x_col].values
        y = data[y_col].values
        mk = config.marker

        scatter_kw = dict(
            s=mk.size, alpha=mk.alpha,
            edgecolors=mk.edge_color, linewidths=mk.edge_width,
        )

        if color_col and color_col in data.columns:
            cvals = data[color_col].values
            sc = ax.scatter(x, y, c=cvals, cmap=config.color.colormap, **scatter_kw)
            fig.colorbar(sc, ax=ax, label=color_col)
        else:
            ax.scatter(x, y, c=config.color.up_color, **scatter_kw)

        # Optional regression line
        if config.extras.get("show_regression", False):
            m, b = np.polyfit(x, y, 1)
            xr = np.linspace(x.min(), x.max(), 100)
            ax.plot(xr, m * xr + b, color="red", lw=1, ls="--")
            r = np.corrcoef(x, y)[0, 1]
            ax.text(0.05, 0.95, f"r = {r:.3f}", transform=ax.transAxes,
                    fontsize=config.font.annotation_size, va="top")

        self._apply_axis_config(ax, config.x_axis, config.y_axis)
        if not config.x_axis.label:
            ax.set_xlabel(x_col)
        if not config.y_axis.label:
            ax.set_ylabel(y_col)

        if config.figure.title:
            ax.set_title(config.figure.title, fontsize=config.font.title_size)

        if config.figure.tight_layout:
            fig.tight_layout()

        return fig

    @staticmethod
    def _get_data(dataset) -> pd.DataFrame | None:
        if dataset is None:
            return None
        if dataset.counts is not None:
            return dataset.counts.T  # samples as rows
        return None

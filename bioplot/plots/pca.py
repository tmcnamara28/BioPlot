"""PCA scatter plot."""
from __future__ import annotations

from typing import TYPE_CHECKING

import matplotlib.pyplot as plt
import numpy as np

from bioplot.plots.base_plot import BasePlot

if TYPE_CHECKING:
    from matplotlib.figure import Figure
    from bioplot.models.dataset import BioDataset
    from bioplot.models.plot_config import PlotConfig


class PCAPlot(BasePlot):
    """PCA scatter plot renderer."""

    def render(
        self,
        config: "PlotConfig",
        dataset: "BioDataset | None" = None,
    ) -> "Figure":
        pca_result = self._get_pca(config, dataset)
        if pca_result is None:
            return self._placeholder_figure(config, "Run PCA analysis first")

        coords, evr, sample_names = pca_result
        pc_x = config.extras.get("pc_x", 0)
        pc_y = config.extras.get("pc_y", 1)

        fig = self._make_figure(config)
        ax = fig.add_subplot(111)

        # Optional grouping
        groups = config.extras.get("groups")  # list matching sample_names
        mk = config.marker

        if groups:
            import pandas as pd
            unique_groups = list(dict.fromkeys(groups))
            cmap = plt.get_cmap(config.color.palette)
            colors = [cmap(i / max(1, len(unique_groups) - 1)) for i in range(len(unique_groups))]
            for g, col in zip(unique_groups, colors):
                mask = np.array(groups) == g
                ax.scatter(
                    coords[mask, pc_x], coords[mask, pc_y],
                    c=[col], label=g, s=mk.size, alpha=mk.alpha,
                    edgecolors=mk.edge_color, linewidths=mk.edge_width,
                )
        else:
            ax.scatter(
                coords[:, pc_x], coords[:, pc_y],
                c=config.color.up_color, s=mk.size, alpha=mk.alpha,
                edgecolors=mk.edge_color, linewidths=mk.edge_width,
            )

        # Sample labels
        if config.extras.get("show_labels", False):
            for i, name in enumerate(sample_names):
                ax.annotate(name, (coords[i, pc_x], coords[i, pc_y]),
                            fontsize=config.font.annotation_size,
                            xytext=(3, 3), textcoords="offset points")

        pct_x = evr[pc_x] * 100 if pc_x < len(evr) else 0
        pct_y = evr[pc_y] * 100 if pc_y < len(evr) else 0

        xlabel = config.x_axis.label or f"PC{pc_x + 1} ({pct_x:.1f}%)"
        ylabel = config.y_axis.label or f"PC{pc_y + 1} ({pct_y:.1f}%)"
        ax.set_xlabel(xlabel, fontsize=config.font.axis_label_size)
        ax.set_ylabel(ylabel, fontsize=config.font.axis_label_size)

        self._apply_axis_config(ax, config.x_axis, config.y_axis)

        if config.figure.title:
            ax.set_title(config.figure.title, fontsize=config.font.title_size)

        if config.figure.show_legend and groups:
            ax.legend(fontsize=config.font.legend_size, framealpha=0.8)

        if config.figure.tight_layout:
            fig.tight_layout()

        return fig

    @staticmethod
    def _get_pca(config, dataset):
        if dataset is None:
            return None
        key = config.extras.get("pca_key", "default")
        if key in dataset.pca_results:
            r = dataset.pca_results[key]
            return r.coords, r.explained_variance_ratio, r.sample_names
        # Try any cached result
        if dataset.pca_results:
            r = next(iter(dataset.pca_results.values()))
            return r.coords, r.explained_variance_ratio, r.sample_names
        return None

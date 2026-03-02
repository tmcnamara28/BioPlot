"""MA plot: log2FC (M) vs average expression (A)."""
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


class MAPlot(BasePlot):
    """MA (Bland-Altman / log-ratio vs mean) plot."""

    def render(
        self,
        config: "PlotConfig",
        dataset: "BioDataset | None" = None,
    ) -> "Figure":
        table = self._get_table(config, dataset)
        if table is None:
            return self._placeholder_figure(config, "Load DEG data to render MA plot")

        sc = config.stat
        cc = config.color
        mk = config.marker

        # Compute A (mean expression) and M (log2FC)
        if "mean_A" in table.columns and "mean_B" in table.columns:
            A = (table["mean_A"].values + table["mean_B"].values) / 2
        elif "baseMean" in table.columns:
            A = np.log2(table["baseMean"].values + 1)
        else:
            A = np.arange(len(table), dtype=float)

        M = table["log2FC"].values
        pval = table[sc.pvalue_type].values if sc.pvalue_type in table.columns \
            else table.get("padj", table.get("pvalue", pd.Series(np.ones(len(table))))).values

        sig = pval < sc.pvalue_threshold

        fig = self._make_figure(config)
        ax = fig.add_subplot(111)

        scatter_kw = dict(s=mk.size, alpha=mk.alpha, edgecolors=mk.edge_color,
                          linewidths=mk.edge_width)

        ax.scatter(A[~sig], M[~sig], c=cc.ns_color, label=f"NS (n={(~sig).sum()})",
                   zorder=1, **scatter_kw)
        ax.scatter(A[sig], M[sig],
                   c=[cc.up_color if m > 0 else cc.down_color for m in M[sig]],
                   label=f"Sig. (n={sig.sum()})", zorder=2, **scatter_kw)

        ax.axhline(0, color="black", lw=0.8)
        if sc.show_threshold_lines:
            ax.axhline(sc.fc_threshold, color="gray", lw=0.8, ls="--")
            ax.axhline(-sc.fc_threshold, color="gray", lw=0.8, ls="--")

        self._apply_axis_config(ax, config.x_axis, config.y_axis)
        if not config.x_axis.label:
            ax.set_xlabel("Average Expression (log2)")
        if not config.y_axis.label:
            ax.set_ylabel("log2 Fold Change")

        if config.figure.title:
            ax.set_title(config.figure.title, fontsize=config.font.title_size)

        if config.figure.show_legend:
            ax.legend(fontsize=config.font.legend_size, framealpha=0.8)

        if config.figure.tight_layout:
            fig.tight_layout()

        return fig

    @staticmethod
    def _get_table(config, dataset) -> pd.DataFrame | None:
        if dataset is None:
            return None
        contrast = config.extras.get("contrast")
        if contrast and contrast in dataset.deg_results:
            return dataset.deg_results[contrast].table
        if dataset.deg_results:
            return next(iter(dataset.deg_results.values())).table
        if dataset.counts is not None and "log2FC" in dataset.counts.columns:
            return dataset.counts
        return None

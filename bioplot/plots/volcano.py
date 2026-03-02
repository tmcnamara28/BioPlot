"""Volcano plot: -log10(padj) vs log2FC."""
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


class VolcanoPlot(BasePlot):
    """Volcano plot renderer."""

    def render(
        self,
        config: "PlotConfig",
        dataset: "BioDataset | None" = None,
    ) -> "Figure":
        deg_table = self._get_deg_table(config, dataset)
        if deg_table is None:
            return self._placeholder_figure(config, "Load DEG data to render volcano plot")

        fig = self._make_figure(config)
        ax = fig.add_subplot(111)

        sc = config.stat
        cc = config.color
        mk = config.marker

        x = deg_table["log2FC"].values
        y = deg_table["neg_log10_padj"].values if "neg_log10_padj" in deg_table.columns \
            else -np.log10(deg_table[sc.pvalue_type].values + 1e-300)

        # Classify points
        up_mask = (deg_table[sc.pvalue_type].values < sc.pvalue_threshold) & (x > sc.fc_threshold)
        dn_mask = (deg_table[sc.pvalue_type].values < sc.pvalue_threshold) & (x < -sc.fc_threshold)
        ns_mask = ~(up_mask | dn_mask)

        scatter_kwargs = dict(
            s=mk.size, alpha=mk.alpha, edgecolors=mk.edge_color,
            linewidths=mk.edge_width,
        )

        ax.scatter(x[ns_mask], y[ns_mask], c=cc.ns_color, zorder=1,
                   label=f"NS (n={ns_mask.sum()})", **scatter_kwargs)
        ax.scatter(x[up_mask], y[up_mask], c=cc.up_color, zorder=2,
                   label=f"Up (n={up_mask.sum()})", **scatter_kwargs)
        ax.scatter(x[dn_mask], y[dn_mask], c=cc.down_color, zorder=2,
                   label=f"Down (n={dn_mask.sum()})", **scatter_kwargs)

        # Threshold lines
        if sc.show_threshold_lines:
            ax.axhline(-np.log10(sc.pvalue_threshold), color="gray", lw=0.8, ls="--", zorder=0)
            ax.axvline(sc.fc_threshold, color="gray", lw=0.8, ls="--", zorder=0)
            ax.axvline(-sc.fc_threshold, color="gray", lw=0.8, ls="--", zorder=0)

        # Gene labels
        if sc.label_top_n > 0 and sc.annotation_style == "gene":
            self._label_top_genes(ax, deg_table, x, y, sc.label_top_n, config)

        # Axes
        self._apply_axis_config(ax, config.x_axis, config.y_axis)
        if not config.x_axis.label:
            ax.set_xlabel("log2 Fold Change")
        if not config.y_axis.label:
            ax.set_ylabel("-log10(padj)")

        if config.figure.title:
            ax.set_title(config.figure.title, fontsize=config.font.title_size,
                         fontweight="bold" if config.font.bold_title else "normal")

        if config.figure.show_legend:
            ax.legend(loc=config.figure.legend_position, fontsize=config.font.legend_size,
                      framealpha=0.8)

        if config.figure.tight_layout:
            fig.tight_layout()

        return fig

    @staticmethod
    def _get_deg_table(config, dataset) -> pd.DataFrame | None:
        if dataset is None:
            return None
        contrast = config.extras.get("contrast")
        if contrast and contrast in dataset.deg_results:
            return dataset.deg_results[contrast].table
        if dataset.deg_results:
            return next(iter(dataset.deg_results.values())).table
        # Fallback: treat counts as a pre-computed DEG table
        if dataset.counts is not None:
            needed = {"log2FC", "pvalue", "padj"}
            if needed.issubset(set(dataset.counts.columns)):
                return dataset.counts
        return None

    @staticmethod
    def _label_top_genes(ax, table, x, y, top_n, config) -> None:
        try:
            from adjustText import adjust_text
            has_adjust = True
        except ImportError:
            has_adjust = False

        # Pick top_n by abs(log2FC) * -log10(padj)
        score = np.abs(x) * y
        idx = np.argsort(score)[-top_n:][::-1]
        gene_names = list(table.index)

        texts = []
        for i in idx:
            if i < len(gene_names):
                t = ax.text(x[i], y[i], gene_names[i],
                            fontsize=config.font.annotation_size, ha="center")
                texts.append(t)

        if has_adjust and texts:
            adjust_text(texts, ax=ax,
                        arrowprops={"arrowstyle": "-", "color": "gray", "lw": 0.5})

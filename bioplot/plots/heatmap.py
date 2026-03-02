"""Heatmap plot using seaborn clustermap."""
from __future__ import annotations

from typing import TYPE_CHECKING

import matplotlib.pyplot as plt
import numpy as np

from bioplot.plots.base_plot import BasePlot

if TYPE_CHECKING:
    from matplotlib.figure import Figure
    from bioplot.models.dataset import BioDataset
    from bioplot.models.plot_config import PlotConfig


class HeatmapPlot(BasePlot):
    """Clustered heatmap using seaborn.clustermap."""

    def render(
        self,
        config: "PlotConfig",
        dataset: "BioDataset | None" = None,
    ) -> "Figure":
        import seaborn as sns

        data = self._get_matrix(config, dataset)
        if data is None:
            return self._placeholder_figure(config, "Load expression data for heatmap")

        from bioplot.core.export_engine import mm_to_inches
        w = mm_to_inches(config.figure.width_mm)
        h = mm_to_inches(config.figure.height_mm)

        method = config.extras.get("cluster_method", "average")
        metric = config.extras.get("cluster_metric", "euclidean")
        col_cluster = config.extras.get("col_cluster", True)
        row_cluster = config.extras.get("row_cluster", True)
        z_score = config.extras.get("z_score", 0)  # 0=row, 1=col, None=off
        if z_score not in (0, 1):
            z_score = None

        top_n = config.extras.get("top_n_genes", 50)
        if top_n and len(data) > top_n:
            var = data.var(axis=1)
            data = data.loc[var.nlargest(top_n).index]

        cg = sns.clustermap(
            data,
            method=method,
            metric=metric,
            col_cluster=col_cluster,
            row_cluster=row_cluster,
            z_score=z_score,
            cmap=config.color.colormap,
            figsize=(w, h),
            xticklabels=True,
            yticklabels=True,
            dendrogram_ratio=(0.15, 0.1),
        )

        # Apply font sizes
        cg.ax_heatmap.tick_params(
            axis="x", labelsize=config.font.tick_label_size,
            rotation=config.x_axis.tick_rotation or 45,
        )
        cg.ax_heatmap.tick_params(
            axis="y", labelsize=config.font.tick_label_size, rotation=0,
        )

        if config.figure.title:
            cg.fig.suptitle(config.figure.title, fontsize=config.font.title_size,
                            fontweight="bold" if config.font.bold_title else "normal",
                            y=1.02)

        return cg.fig

    @staticmethod
    def _get_matrix(config, dataset):
        if dataset is None:
            return None

        normalized = config.extras.get("use_normalized", True)
        if normalized and dataset.normalized is not None:
            return dataset.normalized
        if dataset.counts is not None:
            # Log-transform for display
            import pandas as pd
            counts = dataset.counts.select_dtypes(include=[np.number])
            return np.log1p(counts)
        return None

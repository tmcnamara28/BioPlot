"""Heatmap plot — seaborn clustermap with hierarchical or k-means ordering."""
from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from bioplot.plots.base_plot import BasePlot

if TYPE_CHECKING:
    from matplotlib.figure import Figure
    from bioplot.models.dataset import BioDataset
    from bioplot.models.plot_config import PlotConfig


class HeatmapPlot(BasePlot):
    """Clustered heatmap.

    ``extras`` keys
    ---------------
    cluster_method : str
        ``"hierarchical"`` (default), ``"kmeans"``, or ``"none"``.
    n_clusters_row / n_clusters_col : int
        Number of k-means clusters (only used when method == "kmeans").
    cluster_metric : str
        Distance metric for hierarchical clustering (default ``"euclidean"``).
    col_cluster : bool
    row_cluster : bool
    z_score : int or None
        0 = row-wise z-score, 1 = column-wise, None = off.
    top_n_genes : int
        Subset to top-N most variable genes before plotting.
    use_normalized : bool
        Use ``dataset.normalized`` if available.
    """

    def render(
        self,
        config: "PlotConfig",
        dataset: "BioDataset | None" = None,
    ) -> "Figure":
        data = self._get_matrix(config, dataset)
        if data is None:
            return self._placeholder_figure(config, "Load expression data for heatmap")

        from bioplot.core.export_engine import mm_to_inches
        w = mm_to_inches(config.figure.width_mm)
        h = mm_to_inches(config.figure.height_mm)

        top_n = config.extras.get("top_n_genes", 50)
        if top_n and len(data) > top_n:
            var = data.var(axis=1)
            data = data.loc[var.nlargest(top_n).index]

        method = config.extras.get("cluster_method", "hierarchical")

        if method == "kmeans":
            return self._render_kmeans(data, config, w, h)
        elif method == "none":
            return self._render_no_cluster(data, config, w, h)
        else:
            return self._render_hierarchical(data, config, w, h)

    # ── Hierarchical ──────────────────────────────────────────────────────────

    @staticmethod
    def _render_hierarchical(data, config, w, h) -> "Figure":
        import seaborn as sns

        z_score = config.extras.get("z_score", 0)
        if z_score not in (0, 1):
            z_score = None

        cg = sns.clustermap(
            data,
            method=config.extras.get("cluster_metric", "average"),
            metric=config.extras.get("cluster_metric", "euclidean"),
            col_cluster=config.extras.get("col_cluster", True),
            row_cluster=config.extras.get("row_cluster", True),
            z_score=z_score,
            cmap=config.color.colormap,
            figsize=(w, h),
            xticklabels=True,
            yticklabels=True,
            dendrogram_ratio=(0.15, 0.1),
        )
        cg.ax_heatmap.tick_params(
            axis="x", labelsize=config.font.tick_label_size,
            rotation=config.x_axis.tick_rotation or 45,
        )
        cg.ax_heatmap.tick_params(
            axis="y", labelsize=config.font.tick_label_size, rotation=0,
        )
        if config.figure.title:
            cg.fig.suptitle(
                config.figure.title, fontsize=config.font.title_size,
                fontweight="bold" if config.font.bold_title else "normal",
                y=1.02,
            )
        return cg.fig

    # ── K-means ───────────────────────────────────────────────────────────────

    @staticmethod
    def _render_kmeans(data, config, w, h) -> "Figure":
        from sklearn.cluster import KMeans
        import matplotlib.pyplot as plt
        from matplotlib.figure import Figure as MplFigure

        k_row = config.extras.get("n_clusters_row", 3)
        k_col = config.extras.get("n_clusters_col", 3)

        X = data.values

        # Row clustering
        km_row = KMeans(n_clusters=min(k_row, len(data)), random_state=42, n_init="auto")
        row_labels = km_row.fit_predict(X)
        row_order = np.argsort(row_labels)

        # Column clustering
        km_col = KMeans(n_clusters=min(k_col, data.shape[1]), random_state=42, n_init="auto")
        col_labels = km_col.fit_predict(X.T)
        col_order = np.argsort(col_labels)

        ordered = data.iloc[row_order, :].iloc[:, col_order]

        fig = MplFigure(figsize=(w, h), dpi=config.figure.dpi)
        ax = fig.add_subplot(111)

        im = ax.imshow(ordered.values, aspect="auto", cmap=config.color.colormap,
                       interpolation="nearest")
        fig.colorbar(im, ax=ax, shrink=0.8, label="Expression")

        ax.set_xticks(range(len(ordered.columns)))
        ax.set_xticklabels(ordered.columns, rotation=45, ha="right",
                           fontsize=config.font.tick_label_size)
        ax.set_yticks(range(len(ordered.index)))
        ax.set_yticklabels(ordered.index, fontsize=config.font.tick_label_size)

        # Draw cluster boundaries
        row_boundaries = np.where(np.diff(row_labels[row_order]))[0] + 0.5
        for b in row_boundaries:
            ax.axhline(b, color="white", lw=1.5)

        col_boundaries = np.where(np.diff(col_labels[col_order]))[0] + 0.5
        for b in col_boundaries:
            ax.axvline(b, color="white", lw=1.5)

        if config.figure.title:
            ax.set_title(config.figure.title, fontsize=config.font.title_size,
                         fontweight="bold" if config.font.bold_title else "normal")

        if config.figure.tight_layout:
            fig.tight_layout()
        return fig

    # ── No clustering ─────────────────────────────────────────────────────────

    @staticmethod
    def _render_no_cluster(data, config, w, h) -> "Figure":
        from matplotlib.figure import Figure as MplFigure

        fig = MplFigure(figsize=(w, h), dpi=config.figure.dpi)
        ax = fig.add_subplot(111)

        im = ax.imshow(data.values, aspect="auto", cmap=config.color.colormap,
                       interpolation="nearest")
        fig.colorbar(im, ax=ax, shrink=0.8, label="Expression")

        ax.set_xticks(range(len(data.columns)))
        ax.set_xticklabels(data.columns, rotation=45, ha="right",
                           fontsize=config.font.tick_label_size)
        ax.set_yticks(range(len(data.index)))
        ax.set_yticklabels(data.index, fontsize=config.font.tick_label_size)

        if config.figure.title:
            ax.set_title(config.figure.title, fontsize=config.font.title_size)

        if config.figure.tight_layout:
            fig.tight_layout()
        return fig

    # ── Data helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _get_matrix(config, dataset):
        if dataset is None:
            return None
        if config.extras.get("use_normalized", True) and dataset.normalized is not None:
            return dataset.normalized
        if dataset.counts is not None:
            counts = dataset.counts.select_dtypes(include=[np.number])
            return np.log1p(counts)
        return None

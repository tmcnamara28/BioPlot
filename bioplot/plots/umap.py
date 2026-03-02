"""UMAP plot — scanpy-backed (Phase 5)."""
from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from bioplot.plots.base_plot import BasePlot

if TYPE_CHECKING:
    from matplotlib.figure import Figure
    from bioplot.models.dataset import BioDataset
    from bioplot.models.plot_config import PlotConfig


class UMAPPlot(BasePlot):
    """UMAP scatter plot.

    Requires scanpy + anndata.  Falls back to a manual scatter if UMAP
    coordinates are pre-computed and stored in ``dataset.pca_results``
    (using the same coords array with key ``"umap"``).
    """

    def render(
        self,
        config: "PlotConfig",
        dataset: "BioDataset | None" = None,
    ) -> "Figure":
        try:
            import scanpy as sc  # type: ignore  # noqa: F401
        except ImportError:
            return self._placeholder_figure(
                config,
                "UMAP requires scanpy.\nInstall: pip install scanpy anndata",
            )

        adata = self._get_adata(config, dataset)
        if adata is None:
            return self._placeholder_figure(
                config, "Load an H5AD file to render a UMAP plot"
            )

        # Compute UMAP if not yet present
        if "X_umap" not in adata.obsm:
            adata = self._run_umap_pipeline(adata, config)

        return self._draw(adata, config)

    # ── Drawing ───────────────────────────────────────────────────────────────

    @staticmethod
    def _draw(adata, config) -> "Figure":
        from bioplot.core.export_engine import mm_to_inches
        from matplotlib.figure import Figure as MplFigure

        w = mm_to_inches(config.figure.width_mm)
        h = mm_to_inches(config.figure.height_mm)

        color_key = config.extras.get("color_key")
        coords = adata.obsm["X_umap"]

        fig = MplFigure(figsize=(w, h), dpi=config.figure.dpi)
        ax = fig.add_subplot(111)

        if color_key and color_key in adata.obs.columns:
            categories = adata.obs[color_key]
            unique = categories.unique()
            import matplotlib.pyplot as plt
            cmap = plt.get_cmap(config.color.palette)
            palette = {g: cmap(i / max(1, len(unique) - 1))
                       for i, g in enumerate(unique)}
            for group in unique:
                mask = categories == group
                ax.scatter(
                    coords[mask, 0], coords[mask, 1],
                    c=[palette[group]], label=str(group),
                    s=config.marker.size, alpha=config.marker.alpha,
                    edgecolors=config.marker.edge_color,
                    linewidths=config.marker.edge_width,
                    rasterized=True,
                )
            if config.figure.show_legend:
                ax.legend(
                    fontsize=config.font.legend_size,
                    markerscale=1.5,
                    framealpha=0.8,
                    loc=config.figure.legend_position,
                )
        else:
            ax.scatter(
                coords[:, 0], coords[:, 1],
                c=config.color.up_color,
                s=config.marker.size, alpha=config.marker.alpha,
                rasterized=True,
            )

        xlabel = config.x_axis.label or "UMAP 1"
        ylabel = config.y_axis.label or "UMAP 2"
        ax.set_xlabel(xlabel, fontsize=config.font.axis_label_size)
        ax.set_ylabel(ylabel, fontsize=config.font.axis_label_size)

        title = config.figure.title or (color_key or "UMAP")
        ax.set_title(title, fontsize=config.font.title_size,
                     fontweight="bold" if config.font.bold_title else "normal")

        ax.set_aspect("equal", adjustable="datalim")
        ax.tick_params(labelsize=config.font.tick_label_size)

        if config.figure.tight_layout:
            fig.tight_layout()

        return fig

    # ── Pipeline ──────────────────────────────────────────────────────────────

    @staticmethod
    def _run_umap_pipeline(adata, config):
        import scanpy as sc  # type: ignore

        n_pcs = config.extras.get("n_pcs", 50)
        n_neighbors = config.extras.get("n_neighbors", 15)
        min_dist = config.extras.get("min_dist", 0.5)

        if "X_pca" not in adata.obsm:
            sc.pp.normalize_total(adata, target_sum=1e4)
            sc.pp.log1p(adata)
            sc.pp.highly_variable_genes(adata, n_top_genes=2000)
            sc.pp.scale(adata, max_value=10)
            sc.tl.pca(adata, svd_solver="arpack", n_comps=min(n_pcs, adata.n_obs - 1))

        sc.pp.neighbors(adata, n_neighbors=n_neighbors, n_pcs=n_pcs)
        sc.tl.umap(adata, min_dist=min_dist)
        return adata

    # ── Data access ───────────────────────────────────────────────────────────

    @staticmethod
    def _get_adata(config, dataset):
        if dataset is None:
            return None
        # Inline reference from extras (e.g. already-loaded AnnData)
        adata_ref = config.extras.get("adata")
        if adata_ref is not None:
            return adata_ref
        if dataset.h5ad_path and dataset.h5ad_path.exists():
            try:
                import anndata as ad  # type: ignore
                # Load fully (not backed) so we can run preprocessing
                return ad.read_h5ad(str(dataset.h5ad_path))
            except Exception:
                pass
        return None

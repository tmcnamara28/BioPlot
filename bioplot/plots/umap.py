"""UMAP plot (Phase 5, requires scanpy/anndata)."""
from __future__ import annotations

from typing import TYPE_CHECKING

import matplotlib.pyplot as plt
import numpy as np

from bioplot.plots.base_plot import BasePlot

if TYPE_CHECKING:
    from matplotlib.figure import Figure
    from bioplot.models.dataset import BioDataset
    from bioplot.models.plot_config import PlotConfig


class UMAPPlot(BasePlot):
    """UMAP scatter plot (requires scanpy + anndata installed)."""

    def render(
        self,
        config: "PlotConfig",
        dataset: "BioDataset | None" = None,
    ) -> "Figure":
        try:
            import scanpy as sc  # type: ignore
        except ImportError:
            return self._placeholder_figure(
                config, "UMAP requires scanpy.\nInstall: pip install scanpy anndata"
            )

        adata = self._get_adata(config, dataset)
        if adata is None:
            return self._placeholder_figure(config, "Load H5AD file for UMAP plot")

        color_key = config.extras.get("color_key", "leiden")
        from bioplot.core.export_engine import mm_to_inches
        w = mm_to_inches(config.figure.width_mm)
        h = mm_to_inches(config.figure.height_mm)

        # Use scanpy's built-in UMAP plot but capture the figure
        import matplotlib
        old_backend = matplotlib.get_backend()
        matplotlib.use("Agg")

        try:
            sc.pl.umap(
                adata,
                color=color_key,
                show=False,
                title=config.figure.title or color_key,
                palette=config.color.palette,
                size=config.marker.size,
                alpha=config.marker.alpha,
                legend_fontsize=config.font.legend_size,
            )
            fig = plt.gcf()
            fig.set_size_inches(w, h)
        finally:
            matplotlib.use(old_backend)

        return fig

    @staticmethod
    def _get_adata(config, dataset):
        if dataset is None:
            return None
        adata_ref = config.extras.get("adata")
        if adata_ref is not None:
            return adata_ref
        # Try to load from h5ad_path
        if dataset.h5ad_path and dataset.h5ad_path.exists():
            try:
                import anndata as ad  # type: ignore
                return ad.read_h5ad(str(dataset.h5ad_path), backed="r")
            except Exception:
                pass
        return None

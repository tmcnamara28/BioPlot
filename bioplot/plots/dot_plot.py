"""Dot plot — gene expression fraction + mean per group (scRNA-seq style)."""
from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from bioplot.plots.base_plot import BasePlot

if TYPE_CHECKING:
    from matplotlib.figure import Figure
    from bioplot.models.dataset import BioDataset
    from bioplot.models.plot_config import PlotConfig


class DotPlot(BasePlot):
    """Dot plot: dot size = fraction expressing, colour = mean expression.

    Works with both bulk (BioDataset.counts + metadata group column) and
    AnnData (via scanpy, if installed).
    """

    def render(
        self,
        config: "PlotConfig",
        dataset: "BioDataset | None" = None,
    ) -> "Figure":
        # Try scanpy path first for H5AD datasets
        if dataset is not None and dataset.h5ad_path is not None:
            return self._render_scanpy(config, dataset)
        return self._render_manual(config, dataset)

    # ── scanpy-backed render ──────────────────────────────────────────────────

    def _render_scanpy(self, config, dataset) -> "Figure":
        try:
            import scanpy as sc  # type: ignore
        except ImportError:
            return self._placeholder_figure(
                config, "Dot plot on H5AD requires scanpy.\npip install scanpy"
            )

        adata = self._load_adata(dataset)
        if adata is None:
            return self._placeholder_figure(config, "Could not load H5AD data")

        genes = config.extras.get("genes") or list(adata.var_names[:20])
        groupby = config.extras.get("groupby", "leiden")

        from bioplot.core.export_engine import mm_to_inches
        w = mm_to_inches(config.figure.width_mm)
        h = mm_to_inches(config.figure.height_mm)

        import matplotlib
        old = matplotlib.get_backend()
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        try:
            ax = sc.pl.dotplot(
                adata,
                var_names=genes,
                groupby=groupby,
                show=False,
                cmap=config.color.colormap,
                return_fig=True,
            )
            fig = ax.fig
            fig.set_size_inches(w, h)
        finally:
            matplotlib.use(old)
            plt.close("all")

        return fig

    # ── manual render (bulk / no scanpy) ─────────────────────────────────────

    def _render_manual(self, config, dataset) -> "Figure":
        result = self._compute_stats(config, dataset)
        if result is None:
            return self._placeholder_figure(
                config,
                "Dot plot needs expression data with a\n"
                "'group' column in sample metadata.\n\n"
                "Genes to show: set extras['genes']."
            )

        mean_expr, frac_expr, genes, groups = result
        fig = self._make_figure(config)
        ax = fig.add_subplot(111)

        import matplotlib.pyplot as plt
        from matplotlib.colors import Normalize
        from matplotlib.cm import ScalarMappable

        cmap = plt.get_cmap(config.color.colormap)
        norm = Normalize(vmin=float(mean_expr.values.min()), vmax=float(mean_expr.values.max()))

        max_size = config.marker.size * 4

        for gi, group in enumerate(groups):
            for fi, gene in enumerate(genes):
                mean = mean_expr.loc[group, gene]
                frac = frac_expr.loc[group, gene]
                color = cmap(norm(mean))
                size = frac * max_size
                ax.scatter(fi, gi, s=size, c=[color],
                           alpha=config.marker.alpha,
                           edgecolors="grey", linewidths=0.3)

        ax.set_xticks(range(len(genes)))
        ax.set_xticklabels(genes, rotation=45, ha="right",
                           fontsize=config.font.tick_label_size)
        ax.set_yticks(range(len(groups)))
        ax.set_yticklabels(groups, fontsize=config.font.tick_label_size)

        # Colorbar
        sm = ScalarMappable(cmap=cmap, norm=norm)
        sm.set_array([])
        cbar = fig.colorbar(sm, ax=ax, shrink=0.6, pad=0.02)
        cbar.set_label("Mean expression", fontsize=config.font.axis_label_size)

        # Size legend
        for frac_val, label in [(0.25, "25%"), (0.5, "50%"), (1.0, "100%")]:
            ax.scatter([], [], s=frac_val * max_size, c="grey",
                       alpha=0.7, label=label)
        ax.legend(
            title="Fraction\nexpressing",
            loc="upper left",
            bbox_to_anchor=(1.15, 1),
            fontsize=config.font.legend_size,
            title_fontsize=config.font.legend_size,
        )

        if not config.x_axis.label:
            ax.set_xlabel("Gene", fontsize=config.font.axis_label_size)
        if not config.y_axis.label:
            ax.set_ylabel("Group", fontsize=config.font.axis_label_size)

        if config.figure.title:
            ax.set_title(config.figure.title, fontsize=config.font.title_size,
                         fontweight="bold" if config.font.bold_title else "normal")

        self._apply_axis_config(ax, config.x_axis, config.y_axis)
        if config.figure.tight_layout:
            fig.tight_layout()

        return fig

    @staticmethod
    def _compute_stats(config, dataset):
        if dataset is None or dataset.counts is None:
            return None
        if dataset.metadata is None or "group" not in dataset.metadata.columns:
            return None

        genes = config.extras.get("genes") or list(dataset.counts.index[:20])
        available = [g for g in genes if g in dataset.counts.index]
        if not available:
            return None

        expr = dataset.counts.loc[available]  # genes × samples
        meta = dataset.metadata

        groups = sorted(meta["group"].unique())
        mean_rows, frac_rows = {}, {}

        for group in groups:
            samples = meta[meta["group"] == group].index.tolist()
            samples = [s for s in samples if s in expr.columns]
            if not samples:
                continue
            sub = expr[samples]
            mean_rows[group] = sub.mean(axis=1)
            frac_rows[group] = (sub > 0).mean(axis=1)

        if not mean_rows:
            return None

        mean_df = pd.DataFrame(mean_rows).T  # groups × genes
        frac_df = pd.DataFrame(frac_rows).T
        mean_df.columns = available
        frac_df.columns = available

        return mean_df, frac_df, available, list(mean_df.index)

    @staticmethod
    def _load_adata(dataset):
        if dataset is None:
            return None
        if dataset.h5ad_path and dataset.h5ad_path.exists():
            try:
                import anndata as ad  # type: ignore
                return ad.read_h5ad(str(dataset.h5ad_path))
            except Exception:
                pass
        return None

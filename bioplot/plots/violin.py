"""Violin plot for gene expression across groups."""
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


class ViolinPlot(BasePlot):
    """Violin plot renderer (seaborn-backed)."""

    def render(
        self,
        config: "PlotConfig",
        dataset: "BioDataset | None" = None,
    ) -> "Figure":
        import seaborn as sns

        plot_data = self._get_tidy(config, dataset)
        if plot_data is None:
            return self._placeholder_figure(config, "Load expression data for violin plot")

        fig = self._make_figure(config)
        ax = fig.add_subplot(111)

        genes = config.extras.get("genes")
        x_col = "gene" if (genes and len(genes) > 1) else "sample"
        hue_col = config.extras.get("hue_col")

        violinplot_kwargs: dict = dict(
            data=plot_data,
            x=x_col,
            y="expression",
            inner=config.extras.get("inner", "box"),
            cut=config.extras.get("cut", 0),
            ax=ax,
        )
        if hue_col:
            violinplot_kwargs["hue"] = hue_col
            violinplot_kwargs["palette"] = config.color.palette
        else:
            violinplot_kwargs["hue"] = x_col
            violinplot_kwargs["palette"] = config.color.palette
            violinplot_kwargs["legend"] = False
        sns.violinplot(**violinplot_kwargs)

        # Overlay strip/jitter
        if config.marker.jitter > 0:
            sns.stripplot(
                data=plot_data,
                x=x_col,
                y="expression",
                hue=hue_col,
                dodge=hue_col is not None,
                size=config.marker.size / 10,
                alpha=config.marker.alpha * 0.6,
                color="black",
                jitter=config.marker.jitter,
                ax=ax,
            )

        self._apply_axis_config(ax, config.x_axis, config.y_axis)
        if not config.y_axis.label:
            ax.set_ylabel("Expression")

        if config.figure.title:
            ax.set_title(config.figure.title, fontsize=config.font.title_size)

        if config.figure.tight_layout:
            fig.tight_layout()

        return fig

    @staticmethod
    def _get_tidy(config, dataset) -> pd.DataFrame | None:
        if dataset is None or dataset.counts is None:
            return None

        genes = config.extras.get("genes")
        counts = dataset.counts

        if genes:
            available = [g for g in genes if g in counts.index]
            if not available:
                return None
            subset = counts.loc[available]
        else:
            subset = counts.head(10)  # default first 10 genes

        # Melt to tidy format: gene, sample, expression
        df = subset.reset_index().melt(
            id_vars=subset.index.name or "index",
            var_name="sample",
            value_name="expression",
        ).rename(columns={subset.index.name or "index": "gene"})

        # Attach group metadata if present
        if dataset.metadata is not None and "group" in dataset.metadata.columns:
            df = df.merge(
                dataset.metadata[["group"]].reset_index(),
                left_on="sample",
                right_on=dataset.metadata.index.name or "index",
                how="left",
            )

        return df

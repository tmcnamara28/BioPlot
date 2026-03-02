"""Bar plot for gene expression or summary statistics."""
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


class BarPlot(BasePlot):
    """Bar plot (seaborn-backed) with error bars."""

    def render(
        self,
        config: "PlotConfig",
        dataset: "BioDataset | None" = None,
    ) -> "Figure":
        import seaborn as sns

        plot_data = self._get_tidy(config, dataset)
        if plot_data is None:
            return self._placeholder_figure(config, "Load expression data for bar plot")

        fig = self._make_figure(config)
        ax = fig.add_subplot(111)

        x_col = config.extras.get("x_col", "gene")
        hue_col = config.extras.get("hue_col")
        orient = config.extras.get("orient", "v")
        estimator = config.extras.get("estimator", "mean")
        ci = config.extras.get("ci", 95)

        x_var = x_col if orient == "v" else "expression"
        y_var = "expression" if orient == "v" else x_col
        effective_hue = hue_col if hue_col else x_var
        barplot_kwargs: dict = dict(
            data=plot_data,
            x=x_var,
            y=y_var,
            hue=effective_hue,
            palette=config.color.palette,
            errorbar=("ci", ci) if isinstance(ci, int) else ("sd", 1),
            capsize=0.1,
            ax=ax,
        )
        if not hue_col:
            barplot_kwargs["legend"] = False
        sns.barplot(**barplot_kwargs)

        self._apply_axis_config(ax, config.x_axis, config.y_axis)
        if not config.y_axis.label:
            ax.set_ylabel("Expression")

        if config.figure.title:
            ax.set_title(config.figure.title, fontsize=config.font.title_size)

        ax.tick_params(axis="x", rotation=config.x_axis.tick_rotation or 45)

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
            subset = counts.head(10)

        df = subset.reset_index().melt(
            id_vars=subset.index.name or "index",
            var_name="sample",
            value_name="expression",
        ).rename(columns={subset.index.name or "index": "gene"})

        if dataset.metadata is not None and "group" in dataset.metadata.columns:
            df = df.merge(
                dataset.metadata[["group"]].reset_index(),
                left_on="sample",
                right_on=dataset.metadata.index.name or "index",
                how="left",
            )

        return df

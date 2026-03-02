"""PlotConfig — central serializable dataclass for all plot settings."""
from __future__ import annotations

from typing import Any, Literal, Optional
from pydantic import BaseModel, Field


# ── Sub-configs ────────────────────────────────────────────────────────────────

class AxisConfig(BaseModel):
    label: str = ""
    limits: Optional[tuple[float, float]] = None
    scale: Literal["linear", "log", "symlog", "logit"] = "linear"
    show_grid: bool = False
    grid_alpha: float = 0.3
    tick_size: float = 8.0
    tick_rotation: float = 0.0
    show_minor_ticks: bool = False

    model_config = {"frozen": False}


class ColorConfig(BaseModel):
    up_color: str = "#d62728"
    down_color: str = "#1f77b4"
    ns_color: str = "#aec7e8"
    palette: str = "tab10"
    colormap: str = "viridis"
    background: str = "white"
    alpha: float = 0.8

    model_config = {"frozen": False}


class FontConfig(BaseModel):
    family: str = "Arial"
    title_size: float = 12.0
    axis_label_size: float = 10.0
    tick_label_size: float = 8.0
    legend_size: float = 9.0
    annotation_size: float = 8.0
    bold_title: bool = False

    model_config = {"frozen": False}


class StatConfig(BaseModel):
    pvalue_threshold: float = 0.05
    fc_threshold: float = 1.0          # log2 fold-change
    pvalue_type: Literal["pvalue", "padj"] = "padj"
    label_top_n: int = 10
    show_threshold_lines: bool = True
    annotation_style: Literal["gene", "dot", "none"] = "gene"
    correction_method: str = "fdr_bh"  # statsmodels MTP method

    model_config = {"frozen": False}


class MarkerConfig(BaseModel):
    size: float = 20.0
    alpha: float = 0.7
    shape: str = "o"
    edge_color: str = "none"
    edge_width: float = 0.5
    jitter: float = 0.0

    model_config = {"frozen": False}


class FigureConfig(BaseModel):
    width_mm: float = 89.0
    height_mm: float = 89.0
    dpi: int = 300
    title: str = ""
    show_legend: bool = True
    legend_position: str = "best"
    tight_layout: bool = True

    model_config = {"frozen": False}


class AnnotationItem(BaseModel):
    kind: Literal["text", "arrow", "line", "rect"] = "text"
    x: float = 0.0
    y: float = 0.0
    x2: float = 0.0    # for arrow/line end
    y2: float = 0.0
    text: str = ""
    font_size: float = 9.0
    color: str = "black"
    arrow_style: str = "->"
    coords: Literal["data", "axes", "figure"] = "data"

    model_config = {"frozen": False}


# ── Master config ──────────────────────────────────────────────────────────────

class PlotConfig(BaseModel):
    """Single serializable object fully describing one plot.

    Serializes to/from JSON for .biop session files and preset system.
    """
    plot_type: str = "scatter"
    dataset_id: Optional[str] = None

    x_axis: AxisConfig = Field(default_factory=AxisConfig)
    y_axis: AxisConfig = Field(default_factory=AxisConfig)
    color: ColorConfig = Field(default_factory=ColorConfig)
    font: FontConfig = Field(default_factory=FontConfig)
    stat: StatConfig = Field(default_factory=StatConfig)
    marker: MarkerConfig = Field(default_factory=MarkerConfig)
    figure: FigureConfig = Field(default_factory=FigureConfig)

    annotations: list[AnnotationItem] = Field(default_factory=list)

    # Plot-type-specific options and matplotlib rcParams from presets
    extras: dict[str, Any] = Field(default_factory=dict)

    model_config = {"frozen": False}

    # ── Serialization helpers ──────────────────────────────────────────────────

    def to_json(self, indent: int = 2) -> str:
        return self.model_dump_json(indent=indent)

    @classmethod
    def from_json(cls, json_str: str) -> "PlotConfig":
        return cls.model_validate_json(json_str)

    def clone(self) -> "PlotConfig":
        return PlotConfig.model_validate(self.model_dump())

    # ── rcParams extraction ────────────────────────────────────────────────────

    def get_rcparams(self) -> dict[str, Any]:
        """Return matplotlib rcParams built from this config."""
        return {
            "font.family": self.font.family,
            "font.size": self.font.axis_label_size,
            "axes.titlesize": self.font.title_size,
            "axes.labelsize": self.font.axis_label_size,
            "xtick.labelsize": self.font.tick_label_size,
            "ytick.labelsize": self.font.tick_label_size,
            "legend.fontsize": self.font.legend_size,
            "figure.dpi": self.figure.dpi,
            "axes.facecolor": self.color.background,
            "axes.grid": self.color_or_grid(),
            "grid.alpha": self.x_axis.grid_alpha,
            **self.extras.get("rcparams", {}),
        }

    def color_or_grid(self) -> bool:
        return self.x_axis.show_grid or self.y_axis.show_grid

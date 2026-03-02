"""App-wide constants: color palettes, DPI presets, paths."""
from __future__ import annotations

import os
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────
APP_SUPPORT_DIR = Path(
    os.environ.get("BIOPLOT_SUPPORT_DIR")
    or Path.home() / "Library" / "Application Support" / "BioPlot"
)
USER_PRESETS_DIR = APP_SUPPORT_DIR / "presets" / "custom"
SESSION_DIR = APP_SUPPORT_DIR / "sessions"

ASSETS_DIR = Path(__file__).parent / "assets"
BUILTIN_PRESETS_DIR = Path(__file__).parent / "presets"
SAMPLE_DATA_DIR = ASSETS_DIR / "sample_data"

# ── DPI Presets ────────────────────────────────────────────────────────────────
DPI_PRESETS: dict[str, int] = {
    "Screen (96 dpi)": 96,
    "Print (300 dpi)": 300,
    "High-res (600 dpi)": 600,
}

# ── Figure size presets (mm) ──────────────────────────────────────────────────
FIGURE_SIZE_PRESETS: dict[str, tuple[float, float]] = {
    "Single column (89mm)": (89, 67),
    "1.5 column (120mm)": (120, 90),
    "Double column (183mm)": (183, 120),
    "Square": (89, 89),
    "Wide (183×100mm)": (183, 100),
}

# ── Color schemes ─────────────────────────────────────────────────────────────
VOLCANO_COLORS = {
    "up": "#d62728",
    "down": "#1f77b4",
    "ns": "#aec7e8",
}

SEABORN_PALETTES = [
    "deep", "muted", "bright", "pastel", "dark", "colorblind",
    "Set1", "Set2", "Set3", "tab10", "tab20",
]

COLORBLIND_PALETTES = ["colorblind", "cividis", "viridis", "plasma"]

# ── Font defaults ─────────────────────────────────────────────────────────────
DEFAULT_FONT_FAMILY = "Arial"
DEFAULT_FONT_SIZE = 10

# ── Plot type identifiers ─────────────────────────────────────────────────────
PLOT_TYPES = {
    "volcano": "Volcano Plot",
    "ma": "MA Plot",
    "heatmap": "Heatmap",
    "pca": "PCA Plot",
    "violin": "Violin Plot",
    "scatter": "Scatter Plot",
    "barplot": "Bar Plot",
    "umap": "UMAP",
}

# ── Statistical thresholds ────────────────────────────────────────────────────
DEFAULT_PVALUE_THRESHOLD = 0.05
DEFAULT_FC_THRESHOLD = 1.0  # log2 fold-change

# ── Live preview debounce (ms) ────────────────────────────────────────────────
DEBOUNCE_MS = 250

# ── Memory warning threshold ──────────────────────────────────────────────────
MEMORY_WARNING_PERCENT = 80

# ── Session file extension ────────────────────────────────────────────────────
SESSION_EXTENSION = ".biop"

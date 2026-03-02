"""PlotPickerDialog — grid gallery of plot type thumbnails."""
from __future__ import annotations

from typing import Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QGridLayout,
    QGroupBox, QLabel, QPushButton, QScrollArea,
    QSizePolicy, QVBoxLayout, QWidget,
)

from bioplot.constants import PLOT_TYPES


def _make_thumbnail(plot_type: str, size_inch: float = 1.8) -> plt.Figure:
    """Generate a small placeholder thumbnail for a given plot type."""
    import numpy as np

    fig, ax = plt.subplots(figsize=(size_inch, size_inch), dpi=72)
    ax.set_axis_off()
    fig.patch.set_facecolor("#fafafa")

    rng = np.random.default_rng(42)

    if plot_type == "volcano":
        x = rng.normal(0, 2, 200)
        y = rng.exponential(2, 200)
        colors = ["#d62728" if xi > 1 else "#1f77b4" if xi < -1 else "#aec7e8" for xi in x]
        ax.scatter(x, y, c=colors, s=4, alpha=0.6)
    elif plot_type == "ma":
        x = rng.uniform(2, 15, 200)
        y = rng.normal(0, 2, 200)
        ax.scatter(x, y, c="#1f77b4", s=4, alpha=0.6)
        ax.axhline(0, color="black", lw=0.5)
    elif plot_type == "heatmap":
        data = rng.standard_normal((8, 6))
        ax.imshow(data, aspect="auto", cmap="viridis")
    elif plot_type == "pca":
        x = rng.normal(0, 1, 50)
        y = rng.normal(0, 0.5, 50)
        ax.scatter(x[:25], y[:25], c="#d62728", s=8)
        ax.scatter(x[25:], y[25:], c="#1f77b4", s=8)
    elif plot_type == "violin":
        from matplotlib.patches import FancyBboxPatch
        for i, col in enumerate(["#1f77b4", "#ff7f0e", "#2ca02c"]):
            d = rng.normal(i, 0.3, 30)
            parts = ax.violinplot([d], positions=[i], widths=0.6)
            for pc in parts["bodies"]:
                pc.set_facecolor(col)
                pc.set_alpha(0.7)
    elif plot_type == "scatter":
        x = rng.uniform(0, 10, 80)
        y = x * 0.8 + rng.normal(0, 1, 80)
        ax.scatter(x, y, c="#2ca02c", s=6, alpha=0.7)
    elif plot_type == "barplot":
        ax.bar(range(5), rng.uniform(1, 5, 5),
               color=["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"])
    elif plot_type == "umap":
        for i, col in enumerate(["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"]):
            cx, cy = rng.uniform(-3, 3, 2)
            x = rng.normal(cx, 0.4, 30)
            y = rng.normal(cy, 0.4, 30)
            ax.scatter(x, y, c=col, s=4, alpha=0.8)
    else:
        ax.text(0.5, 0.5, plot_type, ha="center", va="center",
                transform=ax.transAxes, fontsize=8)

    fig.tight_layout(pad=0.2)
    return fig


class _PlotCard(QWidget):
    """Clickable thumbnail card for one plot type."""

    def __init__(self, plot_type: str, plot_name: str, parent=None) -> None:
        super().__init__(parent)
        self.plot_type = plot_type
        self._selected = False
        self.setFixedSize(140, 160)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._build_ui(plot_name)

    def _build_ui(self, plot_name: str) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        fig = _make_thumbnail(self.plot_type)
        canvas = FigureCanvasQTAgg(fig)
        canvas.setFixedSize(120, 110)
        canvas.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        label = QLabel(plot_name)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setWordWrap(True)

        layout.addWidget(canvas, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(label)

        self._update_border()

    def _update_border(self) -> None:
        color = "#0078d7" if self._selected else "#cccccc"
        self.setStyleSheet(
            f"QWidget {{ border: 2px solid {color}; border-radius: 4px; background: white; }}"
        )

    def set_selected(self, selected: bool) -> None:
        self._selected = selected
        self._update_border()

    def mousePressEvent(self, event) -> None:
        self.set_selected(True)
        super().mousePressEvent(event)


class PlotPickerDialog(QDialog):
    """Modal gallery for selecting a plot type."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Choose Plot Type")
        self.setMinimumSize(600, 480)
        self.selected_plot_type: Optional[str] = None
        self._cards: list[_PlotCard] = []
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        grid = QGridLayout(container)
        grid.setSpacing(8)

        for i, (pid, pname) in enumerate(PLOT_TYPES.items()):
            card = _PlotCard(pid, pname)
            card.mousePressEvent = lambda ev, c=card: self._select_card(c)
            grid.addWidget(card, i // 4, i % 4)
            self._cards.append(card)

        scroll.setWidget(container)
        layout.addWidget(scroll)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _select_card(self, card: _PlotCard) -> None:
        for c in self._cards:
            c.set_selected(False)
        card.set_selected(True)
        self.selected_plot_type = card.plot_type

    def _accept(self) -> None:
        if self.selected_plot_type is None:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(self, "Select Plot", "Please select a plot type.")
            return
        self.accept()

"""FigureCanvas — center panel: embedded Matplotlib canvas + toolbar."""
from __future__ import annotations

from typing import Optional

import matplotlib
matplotlib.use("qtagg")

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLabel, QProgressBar, QSizePolicy, QVBoxLayout, QWidget,
)


class FigureCanvas(QWidget):
    """Embeds a Matplotlib FigureCanvasQTAgg with zoom/pan toolbar.

    Key public methods:
        set_figure(fig)  — swap in a new Figure (call only from main thread)
        show_progress()  — show animated progress overlay
        hide_progress()  — remove progress overlay
        reset_zoom()     — home navigation
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Create default blank figure
        self._figure = Figure(figsize=(6, 5), dpi=100)
        self._figure.patch.set_facecolor("#f5f5f5")
        ax = self._figure.add_subplot(111)
        ax.set_axis_off()
        ax.text(0.5, 0.5, "Import data and select a plot type\nto begin",
                ha="center", va="center", transform=ax.transAxes,
                fontsize=12, color="#888888")

        self._canvas = FigureCanvasQTAgg(self._figure)
        self._canvas.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        self._toolbar = NavigationToolbar2QT(self._canvas, self)

        # Progress overlay
        self._progress = QProgressBar()
        self._progress.setRange(0, 0)   # indeterminate
        self._progress.setMaximumHeight(4)
        self._progress.setTextVisible(False)
        self._progress.hide()

        self._status = QLabel("")
        self._status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status.hide()

        layout.addWidget(self._toolbar)
        layout.addWidget(self._progress)
        layout.addWidget(self._canvas, stretch=1)
        layout.addWidget(self._status)

    # ── Public API ────────────────────────────────────────────────────────────

    def set_figure(self, fig: Figure) -> None:
        """Replace the current figure. Must be called on the main thread."""
        # Detach old figure
        plt.close(self._figure)

        self._figure = fig
        self._canvas.figure = fig
        fig.canvas = self._canvas

        self._canvas.draw()
        self.hide_progress()

    def show_progress(self, message: str = "Rendering…") -> None:
        self._progress.show()
        self._status.setText(message)
        self._status.show()

    def hide_progress(self) -> None:
        self._progress.hide()
        self._status.hide()

    def reset_zoom(self) -> None:
        self._toolbar.home()

    def set_progress_value(self, value: int) -> None:
        if value >= 0:
            self._progress.setRange(0, 100)
            self._progress.setValue(value)
        else:
            self._progress.setRange(0, 0)

    @property
    def current_figure(self) -> Figure:
        return self._figure

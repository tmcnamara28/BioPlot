"""FigureCanvas — embedded Matplotlib canvas + toolbar + colorblind simulation."""
from __future__ import annotations

from typing import Optional

import matplotlib
matplotlib.use("qtagg")

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure

import numpy as np
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QInputDialog, QLabel, QProgressBar, QPushButton,
    QSizePolicy, QVBoxLayout, QWidget,
)

from bioplot.constants import COLORBLIND_MATRICES


class FigureCanvas(QWidget):
    """Embeds FigureCanvasQTAgg with zoom/pan toolbar.

    Phase 5 additions
    -----------------
    set_colorblind_mode(mode)  — "deuteranopia" | "protanopia" | "tritanopia" | None
    enter_annotation_mode()    — next click on canvas prompts for a text annotation
    annotation_requested(x, y, text) — emitted when user places an annotation

    Public API (unchanged from Phase 1–4)
    --------------------------------------
    set_figure(fig)     — swap in a new Figure (main thread only)
    show_progress(msg)  — animated progress bar
    hide_progress()     — hide progress bar
    reset_zoom()        — home navigation
    current_figure      — property
    """

    annotation_requested = Signal(float, float, str)  # data-space x, y, text

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._colorblind_mode: Optional[str] = None
        self._annotation_mode: bool = False
        self._sim_overlay: Optional[QLabel] = None
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Default blank figure
        self._figure = Figure(figsize=(6, 5), dpi=100)
        self._figure.patch.set_facecolor("#f5f5f5")
        ax = self._figure.add_subplot(111)
        ax.set_axis_off()
        ax.text(0.5, 0.5, "Import data and select a plot type\nto begin",
                ha="center", va="center", transform=ax.transAxes,
                fontsize=12, color="#888888")

        self._mpl_canvas = FigureCanvasQTAgg(self._figure)
        self._mpl_canvas.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self._mpl_canvas.mpl_connect("button_press_event", self._on_canvas_click)

        self._toolbar = NavigationToolbar2QT(self._mpl_canvas, self)

        self._progress = QProgressBar()
        self._progress.setRange(0, 0)
        self._progress.setMaximumHeight(4)
        self._progress.setTextVisible(False)
        self._progress.hide()

        self._status = QLabel("")
        self._status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status.hide()

        # Colorblind simulation overlay (QLabel with pixmap, stacked on canvas)
        self._sim_overlay = QLabel(self._mpl_canvas)
        self._sim_overlay.setScaledContents(True)
        self._sim_overlay.hide()

        layout.addWidget(self._toolbar)
        layout.addWidget(self._progress)
        layout.addWidget(self._mpl_canvas, stretch=1)
        layout.addWidget(self._status)

    # ── Figure swap ───────────────────────────────────────────────────────────

    def set_figure(self, fig: Figure) -> None:
        """Replace the current figure. Must be called on the main thread."""
        import matplotlib.pyplot as plt
        plt.close(self._figure)

        self._figure = fig
        self._mpl_canvas.figure = fig
        fig.canvas = self._mpl_canvas
        self._mpl_canvas.draw()
        self.hide_progress()

        if self._colorblind_mode:
            self._update_simulation()

    # ── Progress overlay ──────────────────────────────────────────────────────

    def show_progress(self, message: str = "Rendering…") -> None:
        self._progress.show()
        self._status.setText(message)
        self._status.show()

    def hide_progress(self) -> None:
        self._progress.hide()
        self._status.hide()

    def set_progress_value(self, value: int) -> None:
        if value >= 0:
            self._progress.setRange(0, 100)
            self._progress.setValue(value)
        else:
            self._progress.setRange(0, 0)

    def reset_zoom(self) -> None:
        self._toolbar.home()

    @property
    def current_figure(self) -> Figure:
        return self._figure

    # ── Colorblindness simulation ─────────────────────────────────────────────

    def set_colorblind_mode(self, mode: Optional[str]) -> None:
        """Set colorblindness simulation mode.

        Parameters
        ----------
        mode : "deuteranopia" | "protanopia" | "tritanopia" | None
        """
        self._colorblind_mode = mode
        if mode is None:
            self._sim_overlay.hide()
        else:
            self._update_simulation()

    def _update_simulation(self) -> None:
        matrix = COLORBLIND_MATRICES.get(self._colorblind_mode)
        if matrix is None:
            return

        # Grab canvas pixels as RGBA
        self._mpl_canvas.draw()
        buf = self._mpl_canvas.buffer_rgba()
        w = self._mpl_canvas.width()
        h = self._mpl_canvas.height()

        rgba = np.frombuffer(buf, dtype=np.uint8).reshape(h, w, 4).copy()
        rgb = rgba[..., :3].astype(np.float32) / 255.0

        mat = np.array(matrix, dtype=np.float32)
        simulated = np.clip(rgb @ mat.T, 0, 1)
        rgba[..., :3] = (simulated * 255).astype(np.uint8)

        qimg = QImage(rgba.tobytes(), w, h, QImage.Format.Format_RGBA8888)
        pixmap = QPixmap.fromImage(qimg)

        self._sim_overlay.setPixmap(pixmap)
        self._sim_overlay.setGeometry(self._mpl_canvas.geometry())
        self._sim_overlay.raise_()
        self._sim_overlay.show()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._colorblind_mode and self._sim_overlay.isVisible():
            self._sim_overlay.setGeometry(self._mpl_canvas.geometry())

    # ── Annotation mode ───────────────────────────────────────────────────────

    def enter_annotation_mode(self) -> None:
        """Next canvas click will prompt for annotation text."""
        self._annotation_mode = True
        self.setCursor(Qt.CursorShape.CrossCursor)

    def _on_canvas_click(self, event) -> None:
        if not self._annotation_mode:
            return
        if event.inaxes is None:
            return

        self._annotation_mode = False
        self.setCursor(Qt.CursorShape.ArrowCursor)

        text, ok = QInputDialog.getText(
            self, "Add Annotation", "Annotation text:"
        )
        if ok and text:
            self.annotation_requested.emit(event.xdata, event.ydata, text)

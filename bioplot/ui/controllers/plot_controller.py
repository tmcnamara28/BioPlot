"""PlotController — debounced live preview + undo/redo stack."""
from __future__ import annotations

import copy
from collections import deque
from typing import Optional

from PySide6.QtCore import QObject, QThreadPool, QTimer

from bioplot.core import DataManager, PlotEngine
from bioplot.core.worker import RenderWorker
from bioplot.models import PlotConfig
from bioplot.ui.panels.figure_canvas import FigureCanvas
from bioplot.ui.panels.property_panel import PropertyPanel


class PlotController(QObject):
    """Owns the 250ms debounce timer for live preview.

    Workflow:
      property widget changes → PropertyPanel.config_changed → _on_config_changed
      → restart debounce timer → timer fires → RenderWorker → canvas.set_figure()
    """

    UNDO_LIMIT = 50

    def __init__(
        self,
        canvas: FigureCanvas,
        property_panel: PropertyPanel,
        data_manager: DataManager,
        plot_configs: list[PlotConfig],
        debounce_ms: int = 250,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._canvas = canvas
        self._panel = property_panel
        self._dm = data_manager
        self._configs = plot_configs
        self._debounce_ms = debounce_ms

        self._active_index: int = 0
        self._undo_stack: deque[PlotConfig] = deque(maxlen=self.UNDO_LIMIT)
        self._redo_stack: deque[PlotConfig] = deque(maxlen=self.UNDO_LIMIT)
        self._current_worker: Optional[RenderWorker] = None

        # Debounce timer
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._do_render)

        # Wire property panel
        self._panel.config_changed.connect(self._on_config_changed)

        # Initial render
        self._panel.load_config(self.current_config)
        self._schedule_render()

    # ── Public API ────────────────────────────────────────────────────────────

    @property
    def current_config(self) -> PlotConfig:
        return self._configs[self._active_index]

    def set_plot_type(self, plot_type: str) -> None:
        self._push_undo()
        self.current_config.plot_type = plot_type
        self._panel.load_config(self.current_config)
        self._schedule_render()

    def config_changed(self) -> None:
        """External trigger to re-render with current config."""
        self._schedule_render()

    def undo(self) -> None:
        if not self._undo_stack:
            return
        self._redo_stack.append(copy.deepcopy(self.current_config))
        self._configs[self._active_index] = self._undo_stack.pop()
        self._panel.load_config(self.current_config)
        self._schedule_render()

    def redo(self) -> None:
        if not self._redo_stack:
            return
        self._undo_stack.append(copy.deepcopy(self.current_config))
        self._configs[self._active_index] = self._redo_stack.pop()
        self._panel.load_config(self.current_config)
        self._schedule_render()

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _on_config_changed(self, new_config: PlotConfig) -> None:
        self._push_undo()
        self._configs[self._active_index] = new_config
        self._schedule_render()

    def _push_undo(self) -> None:
        self._undo_stack.append(copy.deepcopy(self.current_config))
        self._redo_stack.clear()

    def _schedule_render(self) -> None:
        self._timer.start(self._debounce_ms)

    def _do_render(self) -> None:
        config = copy.deepcopy(self.current_config)

        # Get active dataset
        dataset = None
        if config.dataset_id:
            dataset = self._dm.get_dataset(config.dataset_id)
        elif self._dm.datasets:
            dataset = self._dm.datasets[-1]

        # Cancel any in-flight worker
        if self._current_worker is not None:
            self._current_worker.cancel()

        self._canvas.show_progress("Rendering…")

        worker = RenderWorker(PlotEngine.render, config, dataset)
        worker.signals.result.connect(self._canvas.set_figure)
        worker.signals.error.connect(self._on_render_error)
        self._current_worker = worker
        QThreadPool.globalInstance().start(worker)

    def _on_render_error(self, message: str) -> None:
        self._canvas.hide_progress()
        from matplotlib.figure import Figure
        from bioplot.core.export_engine import mm_to_inches
        cfg = self.current_config
        w = mm_to_inches(cfg.figure.width_mm)
        h = mm_to_inches(cfg.figure.height_mm)
        err_fig = Figure(figsize=(w, h))
        ax = err_fig.add_subplot(111)
        ax.text(0.5, 0.5, f"Render error:\n{message}",
                ha="center", va="center", transform=ax.transAxes,
                color="red", fontsize=9, wrap=True)
        ax.set_axis_off()
        self._canvas.set_figure(err_fig)

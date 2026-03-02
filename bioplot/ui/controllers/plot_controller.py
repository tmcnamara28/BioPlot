"""PlotController — debounced live preview, QUndoStack, multi-figure."""
from __future__ import annotations

import copy
from typing import Optional

from PySide6.QtCore import QObject, QThreadPool, QTimer
from PySide6.QtGui import QUndoCommand, QUndoStack

from bioplot.core import DataManager, PlotEngine
from bioplot.core.worker import RenderWorker
from bioplot.models import PlotConfig
from bioplot.models.plot_config import AnnotationItem
from bioplot.ui.panels.multi_figure_panel import MultiFigurePanel
from bioplot.ui.panels.property_panel import PropertyPanel


class PlotConfigCommand(QUndoCommand):
    """Reversible mutation of one PlotConfig."""

    def __init__(
        self,
        controller: "PlotController",
        old_config: PlotConfig,
        new_config: PlotConfig,
        description: str = "Edit plot",
    ) -> None:
        super().__init__(description)
        self._ctrl = controller
        self._old = old_config
        self._new = new_config

    def undo(self) -> None:
        self._ctrl._apply_config(self._old)

    def redo(self) -> None:
        self._ctrl._apply_config(self._new)


class PlotController(QObject):
    """Owns the 250ms debounce timer for live preview.

    Multi-figure: one ``QUndoStack`` per figure tab, stored in
    ``self._undo_stacks``.  Active stack switches with the active tab.

    Workflow
    --------
    property widget change → PropertyPanel.config_changed →
    _on_config_changed → push QUndoCommand → restart debounce →
    timer fires → RenderWorker → canvas.set_figure()
    """

    def __init__(
        self,
        figure_panel: MultiFigurePanel,
        property_panel: PropertyPanel,
        data_manager: DataManager,
        plot_configs: list[PlotConfig],
        debounce_ms: int = 250,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._panel_widget = figure_panel
        self._panel = property_panel
        self._dm = data_manager
        self._configs = plot_configs
        self._debounce_ms = debounce_ms

        self._active_index: int = 0
        # One QUndoStack per figure tab
        self._undo_stacks: list[QUndoStack] = [QUndoStack(self)]
        self._current_worker: Optional[RenderWorker] = None

        # Debounce timer
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._do_render)

        # Tab change syncs active config
        self._panel_widget.tab_changed.connect(self._on_tab_changed)
        self._panel_widget.tab_closed.connect(self._on_tab_closed)

        # Annotation from canvas
        self._panel_widget.current_canvas.annotation_requested.connect(
            self._on_annotation_requested
        )

        # Property panel changes
        self._panel.config_changed.connect(self._on_config_changed)

        # Initial render
        self._panel.load_config(self.current_config)
        self._schedule_render()

    # ── Public API ────────────────────────────────────────────────────────────

    @property
    def current_config(self) -> PlotConfig:
        return self._configs[self._active_index]

    @property
    def active_undo_stack(self) -> QUndoStack:
        return self._undo_stacks[self._active_index]

    def set_plot_type(self, plot_type: str) -> None:
        old = copy.deepcopy(self.current_config)
        self.current_config.plot_type = plot_type
        self._push(old, copy.deepcopy(self.current_config), "Change plot type")
        self._panel.load_config(self.current_config)
        self._schedule_render()

    def config_changed(self) -> None:
        self._schedule_render()

    def add_figure(self) -> None:
        """Add a new figure tab with a fresh PlotConfig."""
        self._configs.append(PlotConfig())
        self._undo_stacks.append(QUndoStack(self))
        canvas = self._panel_widget.add_figure(f"Figure {len(self._configs)}")
        canvas.annotation_requested.connect(self._on_annotation_requested)

    def undo(self) -> None:
        self.active_undo_stack.undo()

    def redo(self) -> None:
        self.active_undo_stack.redo()

    # ── Apply config (called by QUndoCommand) ─────────────────────────────────

    def _apply_config(self, config: PlotConfig) -> None:
        self._configs[self._active_index] = config
        self._panel.load_config(config)
        self._schedule_render()

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _on_config_changed(self, new_config: PlotConfig) -> None:
        old = copy.deepcopy(self.current_config)
        self._configs[self._active_index] = new_config
        self._push(old, copy.deepcopy(new_config), "Edit properties")
        self._schedule_render()

    def _on_tab_changed(self, index: int) -> None:
        if index < 0 or index >= len(self._configs):
            return
        self._active_index = index
        self._panel.load_config(self.current_config)
        self._schedule_render()

    def _on_tab_closed(self, index: int) -> None:
        if index < len(self._configs):
            self._configs.pop(index)
            self._undo_stacks.pop(index)
        self._active_index = min(self._active_index, len(self._configs) - 1)

    def _on_annotation_requested(self, x: float, y: float, text: str) -> None:
        old = copy.deepcopy(self.current_config)
        self.current_config.annotations.append(
            AnnotationItem(kind="text", x=x, y=y, text=text)
        )
        self._push(old, copy.deepcopy(self.current_config), f"Add annotation: {text}")
        self._schedule_render()

    # ── Undo/redo helpers ─────────────────────────────────────────────────────

    def _push(self, old: PlotConfig, new: PlotConfig, description: str) -> None:
        cmd = PlotConfigCommand(self, old, new, description)
        # Push without triggering redo() (it was just executed directly)
        self.active_undo_stack.push(cmd)

    # ── Render pipeline ───────────────────────────────────────────────────────

    def _schedule_render(self) -> None:
        self._timer.start(self._debounce_ms)

    def _do_render(self) -> None:
        config = copy.deepcopy(self.current_config)

        dataset = None
        if config.dataset_id:
            dataset = self._dm.get_dataset(config.dataset_id)
        elif self._dm.datasets:
            dataset = self._dm.datasets[-1]

        if self._current_worker is not None:
            self._current_worker.cancel()

        canvas = self._panel_widget.current_canvas
        canvas.show_progress("Rendering…")

        worker = RenderWorker(PlotEngine.render, config, dataset)
        worker.signals.result.connect(canvas.set_figure)
        worker.signals.error.connect(self._on_render_error)
        self._current_worker = worker
        QThreadPool.globalInstance().start(worker)

    def _on_render_error(self, message: str) -> None:
        canvas = self._panel_widget.current_canvas
        canvas.hide_progress()
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
        canvas.set_figure(err_fig)

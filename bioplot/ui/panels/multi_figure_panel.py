"""MultiFigurePanel — QTabWidget holding one FigureCanvas per figure."""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout, QPushButton, QSizePolicy,
    QTabWidget, QVBoxLayout, QWidget,
)

from bioplot.ui.panels.figure_canvas import FigureCanvas


class MultiFigurePanel(QWidget):
    """Center panel: a tabbed collection of FigureCanvas widgets.

    Signals
    -------
    tab_changed(int)
        Emitted when the active tab (figure) changes.
    tab_closed(int)
        Emitted when a tab is closed; int is the removed index.
    """

    tab_changed = Signal(int)
    tab_closed = Signal(int)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._canvases: list[FigureCanvas] = []
        self._build_ui()
        # Start with one blank figure
        self.add_figure("Figure 1")

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Tab bar + "+" button row
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        self._tabs = QTabWidget()
        self._tabs.setTabsClosable(True)
        self._tabs.setMovable(True)
        self._tabs.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._tabs.tabCloseRequested.connect(self._close_tab)
        self._tabs.currentChanged.connect(self.tab_changed)

        self._add_btn = QPushButton("+")
        self._add_btn.setFixedSize(26, 26)
        self._add_btn.setToolTip("New figure tab")
        self._add_btn.clicked.connect(self._new_tab)

        layout.addWidget(self._tabs)

        # Place "+" button in the tab bar corner
        self._tabs.setCornerWidget(self._add_btn)

    # ── Public API ────────────────────────────────────────────────────────────

    def add_figure(self, title: str = "") -> FigureCanvas:
        """Add a new figure tab and return its FigureCanvas."""
        canvas = FigureCanvas()
        self._canvases.append(canvas)
        idx = self._tabs.addTab(canvas, title or f"Figure {len(self._canvases)}")
        self._tabs.setCurrentIndex(idx)
        return canvas

    def remove_figure(self, index: int) -> None:
        if len(self._canvases) <= 1:
            return  # always keep at least one
        self._tabs.removeTab(index)
        self._canvases.pop(index)
        self.tab_closed.emit(index)

    def rename_current(self, title: str) -> None:
        self._tabs.setTabText(self._tabs.currentIndex(), title)

    @property
    def current_canvas(self) -> FigureCanvas:
        return self._canvases[self._tabs.currentIndex()]

    @property
    def current_index(self) -> int:
        return self._tabs.currentIndex()

    @property
    def count(self) -> int:
        return self._tabs.count()

    def canvas_at(self, index: int) -> FigureCanvas:
        return self._canvases[index]

    def set_colorblind_mode(self, mode: Optional[str]) -> None:
        """Propagate colorblindness simulation to all canvases."""
        for canvas in self._canvases:
            canvas.set_colorblind_mode(mode)

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _new_tab(self) -> None:
        self.add_figure()

    def _close_tab(self, index: int) -> None:
        self.remove_figure(index)

    def reset_zoom(self) -> None:
        self.current_canvas.reset_zoom()

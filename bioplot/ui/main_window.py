"""MainWindow — 3-panel QSplitter layout with menu bar."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QSettings, QTimer
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QMainWindow, QMessageBox,
    QSplitter, QStatusBar, QToolBar, QLabel,
)

from bioplot.constants import DEBOUNCE_MS, SESSION_EXTENSION
from bioplot.core import DataManager, PlotEngine, PresetManager, SessionManager
from bioplot.models import PlotConfig
from bioplot.ui.panels.data_navigator import DataNavigator
from bioplot.ui.panels.figure_canvas import FigureCanvas
from bioplot.ui.panels.property_panel import PropertyPanel
from bioplot.ui.controllers.data_controller import DataController
from bioplot.ui.controllers.plot_controller import PlotController
from bioplot.ui.controllers.export_controller import ExportController


class MainWindow(QMainWindow):
    """Primary application window: 3-panel layout (nav | canvas | props)."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("BioPlot")
        self.resize(1400, 900)

        # Core services
        self._data_manager = DataManager(self)
        self._preset_manager = PresetManager()
        self._plot_configs: list[PlotConfig] = [PlotConfig()]

        # Build UI
        self._build_panels()
        self._build_menu()
        self._build_status_bar()

        # Controllers wire signals
        self._data_ctrl = DataController(
            self._data_manager, self._navigator, self
        )
        self._plot_ctrl = PlotController(
            self._canvas, self._property_panel,
            self._data_manager, self._plot_configs,
            debounce_ms=DEBOUNCE_MS, parent=self,
        )
        self._export_ctrl = ExportController(self._canvas, self)

        # Restore geometry
        self._restore_settings()

        # Memory monitor (every 5 s)
        self._mem_timer = QTimer(self)
        self._mem_timer.timeout.connect(self._check_memory)
        self._mem_timer.start(5000)

    # ── Panel construction ────────────────────────────────────────────────────

    def _build_panels(self) -> None:
        self._splitter = QSplitter(Qt.Orientation.Horizontal)

        self._navigator = DataNavigator(self._data_manager, self)
        self._canvas = FigureCanvas(self)
        self._property_panel = PropertyPanel(self._preset_manager, self)

        self._splitter.addWidget(self._navigator)
        self._splitter.addWidget(self._canvas)
        self._splitter.addWidget(self._property_panel)

        # Proportional sizes: 18% | 56% | 26%
        self._splitter.setStretchFactor(0, 2)
        self._splitter.setStretchFactor(1, 6)
        self._splitter.setStretchFactor(2, 3)

        self.setCentralWidget(self._splitter)

    # ── Menu bar ──────────────────────────────────────────────────────────────

    def _build_menu(self) -> None:
        mb = self.menuBar()

        # File
        file_menu = mb.addMenu("&File")
        self._add_action(file_menu, "&New Session", self._new_session, QKeySequence.StandardKey.New)
        self._add_action(file_menu, "&Open Session…", self._open_session, QKeySequence.StandardKey.Open)
        self._add_action(file_menu, "&Save Session", self._save_session, QKeySequence.StandardKey.Save)
        self._add_action(file_menu, "Save Session &As…", self._save_session_as,
                         QKeySequence.StandardKey.SaveAs)
        file_menu.addSeparator()
        self._add_action(file_menu, "&Import Data…", self._import_data,
                         QKeySequence("Ctrl+I"))
        file_menu.addSeparator()
        self._add_action(file_menu, "&Quit", QApplication.quit, QKeySequence.StandardKey.Quit)

        # Edit
        edit_menu = mb.addMenu("&Edit")
        self._add_action(edit_menu, "&Undo", self._undo, QKeySequence.StandardKey.Undo)
        self._add_action(edit_menu, "&Redo", self._redo, QKeySequence.StandardKey.Redo)

        # View
        view_menu = mb.addMenu("&View")
        self._add_action(view_menu, "&Plot Library…", self._show_plot_picker,
                         QKeySequence("Ctrl+L"))
        self._add_action(view_menu, "&Reset Zoom", self._canvas.reset_zoom,
                         QKeySequence("Ctrl+0"))

        # Analysis
        analysis_menu = mb.addMenu("&Analysis")
        self._add_action(analysis_menu, "&Differential Expression…", self._run_deg,
                         QKeySequence("Ctrl+D"))
        self._add_action(analysis_menu, "&PCA…", self._run_pca, QKeySequence("Ctrl+P"))

        # Export
        export_menu = mb.addMenu("E&xport")
        self._add_action(export_menu, "Export &Figure…", self._export_figure,
                         QKeySequence("Ctrl+E"))

    @staticmethod
    def _add_action(menu, label, slot, shortcut=None) -> QAction:
        action = QAction(label)
        if shortcut:
            action.setShortcut(shortcut)
        action.triggered.connect(slot)
        menu.addAction(action)
        return action

    # ── Status bar ────────────────────────────────────────────────────────────

    def _build_status_bar(self) -> None:
        sb = QStatusBar()
        self._status_label = QLabel("Ready")
        self._mem_label = QLabel("")
        sb.addWidget(self._status_label)
        sb.addPermanentWidget(self._mem_label)
        self.setStatusBar(sb)

    def set_status(self, message: str) -> None:
        self._status_label.setText(message)

    # ── Memory monitor ────────────────────────────────────────────────────────

    def _check_memory(self) -> None:
        try:
            import psutil
            pct = psutil.virtual_memory().percent
            self._mem_label.setText(f"RAM: {pct:.0f}%")
            if pct >= 80:
                self._mem_label.setStyleSheet("color: red;")
                self.set_status("Warning: high memory usage")
            else:
                self._mem_label.setStyleSheet("")
        except ImportError:
            self._mem_timer.stop()

    # ── Menu actions ──────────────────────────────────────────────────────────

    def _new_session(self) -> None:
        if not self._confirm_discard():
            return
        self._data_manager._datasets.clear()
        self._navigator.refresh()
        self._plot_configs.clear()
        self._plot_configs.append(PlotConfig())
        self._plot_ctrl.config_changed()
        self._current_session_path: Optional[Path] = None

    def _open_session(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Session", "",
            f"BioPlot Session (*{SESSION_EXTENSION});;All Files (*)"
        )
        if not path:
            return
        try:
            state, configs = SessionManager.load(path)
            self._plot_configs.clear()
            self._plot_configs.extend(configs)
            self._plot_ctrl.config_changed()
            self._current_session_path = Path(path)
            self.set_status(f"Opened {path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open session:\n{e}")

    def _save_session(self) -> None:
        if not hasattr(self, "_current_session_path") or self._current_session_path is None:
            self._save_session_as()
        else:
            self._do_save(self._current_session_path)

    def _save_session_as(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Session As", "",
            f"BioPlot Session (*{SESSION_EXTENSION});;All Files (*)"
        )
        if path:
            self._current_session_path = Path(path)
            self._do_save(self._current_session_path)

    def _do_save(self, path: Path) -> None:
        try:
            saved = SessionManager.save(
                path, self._data_manager, self._plot_configs
            )
            self.set_status(f"Saved: {saved}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save session:\n{e}")

    def _import_data(self) -> None:
        from bioplot.ui.dialogs.import_dialog import ImportDialog
        dlg = ImportDialog(self._data_manager, self)
        dlg.exec()

    def _show_plot_picker(self) -> None:
        from bioplot.ui.dialogs.plot_picker import PlotPickerDialog
        dlg = PlotPickerDialog(self)
        if dlg.exec():
            plot_type = dlg.selected_plot_type
            if plot_type:
                self._plot_ctrl.set_plot_type(plot_type)

    def _run_deg(self) -> None:
        from bioplot.ui.dialogs.analysis_dialog import AnalysisDialog
        dlg = AnalysisDialog(self._data_manager, self)
        dlg.exec()

    def _run_pca(self) -> None:
        from bioplot.ui.dialogs.analysis_dialog import AnalysisDialog
        dlg = AnalysisDialog(self._data_manager, self, mode="pca")
        dlg.exec()

    def _export_figure(self) -> None:
        self._export_ctrl.show_export_dialog()

    def _undo(self) -> None:
        self._plot_ctrl.undo()

    def _redo(self) -> None:
        self._plot_ctrl.redo()

    def _confirm_discard(self) -> bool:
        resp = QMessageBox.question(
            self, "Unsaved Changes",
            "Discard current session?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        return resp == QMessageBox.StandardButton.Yes

    # ── Geometry persistence ──────────────────────────────────────────────────

    def _restore_settings(self) -> None:
        settings = QSettings("BioPlot", "BioPlot")
        geom = settings.value("geometry")
        if geom:
            self.restoreGeometry(geom)
        state = settings.value("windowState")
        if state:
            self.restoreState(state)
        splitter_state = settings.value("splitterState")
        if splitter_state:
            self._splitter.restoreState(splitter_state)

    def closeEvent(self, event) -> None:
        settings = QSettings("BioPlot", "BioPlot")
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())
        settings.setValue("splitterState", self._splitter.saveState())
        super().closeEvent(event)

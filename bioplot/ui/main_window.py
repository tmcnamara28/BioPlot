"""MainWindow — 3-panel QSplitter layout with menu bar (Phase 5)."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QSettings, QTimer
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QLabel, QMainWindow,
    QMessageBox, QSplitter, QStatusBar,
)

from bioplot.constants import COLORBLIND_MATRICES, DEBOUNCE_MS, SESSION_EXTENSION
from bioplot.core import DataManager, PlotEngine, PresetManager, SessionManager
from bioplot.models import PlotConfig
from bioplot.ui.panels.data_navigator import DataNavigator
from bioplot.ui.panels.multi_figure_panel import MultiFigurePanel
from bioplot.ui.panels.property_panel import PropertyPanel
from bioplot.ui.controllers.data_controller import DataController
from bioplot.ui.controllers.plot_controller import PlotController
from bioplot.ui.controllers.export_controller import ExportController


class MainWindow(QMainWindow):
    """Primary application window: nav | multi-figure tabs | property panel."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("BioPlot")
        self.resize(1400, 900)

        self._data_manager = DataManager(self)
        self._preset_manager = PresetManager()
        self._plot_configs: list[PlotConfig] = [PlotConfig()]
        self._colorblind_mode: Optional[str] = None
        self._current_session_path: Optional[Path] = None

        self._build_panels()
        self._build_menu()
        self._build_status_bar()

        self._data_ctrl = DataController(self._data_manager, self._navigator, self)
        self._plot_ctrl = PlotController(
            self._figure_panel, self._property_panel,
            self._data_manager, self._plot_configs,
            debounce_ms=DEBOUNCE_MS, parent=self,
        )
        self._export_ctrl = ExportController(self._figure_panel, self)

        self._restore_settings()

        self._mem_timer = QTimer(self)
        self._mem_timer.timeout.connect(self._check_memory)
        self._mem_timer.start(5000)

    # ── Panel construction ────────────────────────────────────────────────────

    def _build_panels(self) -> None:
        self._splitter = QSplitter(Qt.Orientation.Horizontal)

        self._navigator = DataNavigator(self._data_manager, self)
        self._figure_panel = MultiFigurePanel(self)
        self._property_panel = PropertyPanel(self._preset_manager, self)

        self._splitter.addWidget(self._navigator)
        self._splitter.addWidget(self._figure_panel)
        self._splitter.addWidget(self._property_panel)

        self._splitter.setStretchFactor(0, 2)
        self._splitter.setStretchFactor(1, 6)
        self._splitter.setStretchFactor(2, 3)

        self.setCentralWidget(self._splitter)

    # ── Menu bar ──────────────────────────────────────────────────────────────

    def _build_menu(self) -> None:
        mb = self.menuBar()

        # File
        file_menu = mb.addMenu("&File")
        self._add_action(file_menu, "&New Session",        self._new_session,    QKeySequence.StandardKey.New)
        self._add_action(file_menu, "&Open Session…",      self._open_session,   QKeySequence.StandardKey.Open)
        self._add_action(file_menu, "&Save Session",       self._save_session,   QKeySequence.StandardKey.Save)
        self._add_action(file_menu, "Save Session &As…",   self._save_session_as, QKeySequence.StandardKey.SaveAs)
        file_menu.addSeparator()
        self._add_action(file_menu, "&Import Data…",       self._import_data,    QKeySequence("Ctrl+I"))
        file_menu.addSeparator()
        self._add_action(file_menu, "&Quit", QApplication.quit, QKeySequence.StandardKey.Quit)

        # Edit
        edit_menu = mb.addMenu("&Edit")
        self._add_action(edit_menu, "&Undo", self._undo, QKeySequence.StandardKey.Undo)
        self._add_action(edit_menu, "&Redo", self._redo, QKeySequence.StandardKey.Redo)
        edit_menu.addSeparator()
        self._add_action(edit_menu, "Add &Annotation", self._add_annotation, QKeySequence("Ctrl+T"))

        # View
        view_menu = mb.addMenu("&View")
        self._add_action(view_menu, "&Plot Library…",  self._show_plot_picker, QKeySequence("Ctrl+L"))
        self._add_action(view_menu, "&New Figure Tab", self._new_figure_tab,   QKeySequence("Ctrl+Shift+N"))
        self._add_action(view_menu, "&Reset Zoom",     self._reset_zoom,       QKeySequence("Ctrl+0"))
        view_menu.addSeparator()

        # Colorblindness submenu
        cb_menu = view_menu.addMenu("Colorblindness Simulation")
        self._cb_actions: dict[Optional[str], QAction] = {}
        for mode in [None, "deuteranopia", "protanopia", "tritanopia"]:
            label = "Off" if mode is None else mode.capitalize()
            act = QAction(label, self, checkable=True)
            act.triggered.connect(lambda checked, m=mode: self._set_colorblind(m))
            cb_menu.addAction(act)
            self._cb_actions[mode] = act
        self._cb_actions[None].setChecked(True)

        # Analysis
        analysis_menu = mb.addMenu("&Analysis")
        self._add_action(analysis_menu, "&Differential Expression…", self._run_deg, QKeySequence("Ctrl+D"))
        self._add_action(analysis_menu, "&PCA…",                     self._run_pca, QKeySequence("Ctrl+P"))

        # Export
        export_menu = mb.addMenu("E&xport")
        self._add_action(export_menu, "Export &Figure…", self._export_figure, QKeySequence("Ctrl+E"))

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
        self._cb_label = QLabel("")
        self._cb_label.setStyleSheet("color: #0078d7;")
        sb.addWidget(self._status_label)
        sb.addPermanentWidget(self._cb_label)
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
        self._current_session_path = None

    def _open_session(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Session", "",
            f"BioPlot Session (*{SESSION_EXTENSION});;All Files (*)",
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
        if self._current_session_path is None:
            self._save_session_as()
        else:
            self._do_save(self._current_session_path)

    def _save_session_as(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Session As", "",
            f"BioPlot Session (*{SESSION_EXTENSION});;All Files (*)",
        )
        if path:
            self._current_session_path = Path(path)
            self._do_save(self._current_session_path)

    def _do_save(self, path: Path) -> None:
        try:
            saved = SessionManager.save(path, self._data_manager, self._plot_configs)
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

    def _new_figure_tab(self) -> None:
        self._plot_ctrl.add_figure()

    def _reset_zoom(self) -> None:
        self._figure_panel.reset_zoom()

    def _add_annotation(self) -> None:
        self._figure_panel.current_canvas.enter_annotation_mode()
        self.set_status("Click on the figure to place an annotation…")

    def _set_colorblind(self, mode: Optional[str]) -> None:
        self._colorblind_mode = mode
        # Update checkmarks
        for m, act in self._cb_actions.items():
            act.setChecked(m == mode)
        self._figure_panel.set_colorblind_mode(mode)
        label = "" if mode is None else f"Simulating: {mode.capitalize()}"
        self._cb_label.setText(label)
        self.set_status(label or "Colorblindness simulation off")

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
            self, "Unsaved Changes", "Discard current session?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        return resp == QMessageBox.StandardButton.Yes

    # ── Geometry persistence ──────────────────────────────────────────────────

    def _restore_settings(self) -> None:
        s = QSettings("BioPlot", "BioPlot")
        if geom := s.value("geometry"):
            self.restoreGeometry(geom)
        if state := s.value("windowState"):
            self.restoreState(state)
        if sp := s.value("splitterState"):
            self._splitter.restoreState(sp)

    def closeEvent(self, event) -> None:
        s = QSettings("BioPlot", "BioPlot")
        s.setValue("geometry", self.saveGeometry())
        s.setValue("windowState", self.saveState())
        s.setValue("splitterState", self._splitter.saveState())
        super().closeEvent(event)

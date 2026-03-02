"""ExportController — handles figure export from the canvas."""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QMessageBox

from bioplot.core import ExportEngine


class ExportController(QObject):
    """Bridges ExportDialog → ExportEngine → filesystem."""

    def __init__(
        self,
        figure_panel,   # MultiFigurePanel
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._figure_panel = figure_panel

    def show_export_dialog(self) -> None:
        from bioplot.ui.dialogs.export_dialog import ExportDialog
        dlg = ExportDialog(self.parent())
        if dlg.exec():
            self._do_export(dlg)

    def _do_export(self, dlg) -> None:
        fig = self._figure_panel.current_canvas.current_figure
        try:
            path = ExportEngine.export(
                fig,
                dlg.export_path,
                fmt=dlg.export_format,
                dpi=dlg.dpi,
                width_mm=dlg.width_mm,
                height_mm=dlg.height_mm,
                transparent=dlg.transparent,
                metadata={"Title": "BioPlot Figure", "Creator": "BioPlot"},
            )
            QMessageBox.information(
                self.parent(), "Export Complete",
                f"Figure saved to:\n{path}"
            )
        except Exception as e:
            QMessageBox.critical(
                self.parent(), "Export Error",
                f"Failed to export figure:\n{e}"
            )

"""PropertyPanel — right panel: tabbed customization widgets."""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QTabWidget, QVBoxLayout, QWidget

from bioplot.core import PresetManager
from bioplot.models import PlotConfig
from bioplot.ui.property_widgets.axis_editor import AxisEditor
from bioplot.ui.property_widgets.color_editor import ColorEditor
from bioplot.ui.property_widgets.font_editor import FontEditor
from bioplot.ui.property_widgets.stats_editor import StatsEditor
from bioplot.ui.property_widgets.marker_editor import MarkerEditor
from bioplot.ui.property_widgets.theme_editor import ThemeEditor


class PropertyPanel(QWidget):
    """Tabbed right panel exposing all PlotConfig sub-configs.

    Emits ``config_changed(PlotConfig)`` whenever any sub-editor changes.
    """

    config_changed = Signal(object)   # PlotConfig

    def __init__(
        self,
        preset_manager: PresetManager,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._preset_manager = preset_manager
        self._config: PlotConfig = PlotConfig()
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        self._tabs = QTabWidget()

        self._axis_editor = AxisEditor()
        self._color_editor = ColorEditor()
        self._font_editor = FontEditor()
        self._stats_editor = StatsEditor()
        self._marker_editor = MarkerEditor()
        self._theme_editor = ThemeEditor(self._preset_manager)

        self._tabs.addTab(self._axis_editor, "Axes")
        self._tabs.addTab(self._color_editor, "Colors")
        self._tabs.addTab(self._font_editor, "Fonts")
        self._tabs.addTab(self._stats_editor, "Statistics")
        self._tabs.addTab(self._marker_editor, "Markers")
        self._tabs.addTab(self._theme_editor, "Theme")

        layout.addWidget(self._tabs)

        # Wire each editor's change signal
        for editor in (
            self._axis_editor, self._color_editor, self._font_editor,
            self._stats_editor, self._marker_editor, self._theme_editor,
        ):
            editor.changed.connect(self._on_editor_changed)

        self._theme_editor.preset_applied.connect(self._on_preset_applied)

    # ── Public API ────────────────────────────────────────────────────────────

    def load_config(self, config: PlotConfig) -> None:
        """Push *config* into all editors (block signals to prevent feedback loop)."""
        self._config = config
        for editor, subcfg in [
            (self._axis_editor, None),
            (self._color_editor, config.color),
            (self._font_editor, config.font),
            (self._stats_editor, config.stat),
            (self._marker_editor, config.marker),
            (self._theme_editor, None),
        ]:
            if subcfg is not None and hasattr(editor, "load"):
                editor.load(subcfg)

        self._axis_editor.load(config.x_axis, config.y_axis)

    def current_config(self) -> PlotConfig:
        return self._config

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _on_editor_changed(self) -> None:
        """Collect all sub-editor values into _config, emit config_changed."""
        x, y = self._axis_editor.get_values()
        self._config.x_axis = x
        self._config.y_axis = y
        self._config.color = self._color_editor.get_values()
        self._config.font = self._font_editor.get_values()
        self._config.stat = self._stats_editor.get_values()
        self._config.marker = self._marker_editor.get_values()
        self.config_changed.emit(self._config)

    def _on_preset_applied(self, preset_name: str) -> None:
        new_config = self._preset_manager.apply_preset(self._config, preset_name)
        self.load_config(new_config)
        self.config_changed.emit(new_config)

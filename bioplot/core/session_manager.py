"""SessionManager — save/load .biop session files (JSON)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bioplot.constants import SESSION_EXTENSION
from bioplot.models.plot_config import PlotConfig

if TYPE_CHECKING:
    from bioplot.core.data_manager import DataManager


class SessionState:
    """In-memory representation of a full session."""

    def __init__(self) -> None:
        self.datasets: dict[str, dict] = {}          # from DataManager.to_dict()
        self.plot_configs: list[dict] = []            # list of PlotConfig.model_dump()
        self.active_config_index: int = 0
        self.window_geometry: dict = {}

    def to_dict(self) -> dict:
        return {
            "version": "1",
            "datasets": self.datasets,
            "plot_configs": self.plot_configs,
            "active_config_index": self.active_config_index,
            "window_geometry": self.window_geometry,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SessionState":
        state = cls()
        state.datasets = data.get("datasets", {})
        state.plot_configs = data.get("plot_configs", [])
        state.active_config_index = data.get("active_config_index", 0)
        state.window_geometry = data.get("window_geometry", {})
        return state


class SessionManager:
    """Serialize and deserialize full application state."""

    @staticmethod
    def save(
        path: str | Path,
        data_manager: "DataManager",
        plot_configs: list[PlotConfig],
        active_index: int = 0,
        window_geometry: dict | None = None,
    ) -> Path:
        path = Path(path)
        if path.suffix != SESSION_EXTENSION:
            path = path.with_suffix(SESSION_EXTENSION)

        state = SessionState()
        state.datasets = data_manager.to_dict()
        state.plot_configs = [c.model_dump() for c in plot_configs]
        state.active_config_index = active_index
        state.window_geometry = window_geometry or {}

        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(state.to_dict(), f, indent=2)
        return path.resolve()

    @staticmethod
    def load(path: str | Path) -> tuple[SessionState, list[PlotConfig]]:
        path = Path(path)
        with path.open(encoding="utf-8") as f:
            data = json.load(f)

        state = SessionState.from_dict(data)
        configs = [PlotConfig.model_validate(c) for c in state.plot_configs]
        return state, configs

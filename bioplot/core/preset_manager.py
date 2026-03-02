"""PresetManager — load, apply, and save journal style presets."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from bioplot.constants import BUILTIN_PRESETS_DIR, USER_PRESETS_DIR
from bioplot.models.plot_config import PlotConfig


def _deep_merge(base: dict, overlay: dict) -> dict:
    """Recursively merge *overlay* into *base* (returns new dict)."""
    result = dict(base)
    for key, val in overlay.items():
        if key in result and isinstance(result[key], dict) and isinstance(val, dict):
            result[key] = _deep_merge(result[key], val)
        else:
            result[key] = val
    return result


class PresetManager:
    """Manage built-in and user-defined journal presets."""

    def __init__(self) -> None:
        self._builtin: dict[str, dict] = {}
        self._user: dict[str, dict] = {}
        self._load_builtins()
        self._load_user_presets()

    # ── Loading ───────────────────────────────────────────────────────────────

    def _load_builtins(self) -> None:
        if not BUILTIN_PRESETS_DIR.exists():
            return
        for p in BUILTIN_PRESETS_DIR.glob("*.json"):
            with p.open() as f:
                self._builtin[p.stem] = json.load(f)

    def _load_user_presets(self) -> None:
        if not USER_PRESETS_DIR.exists():
            return
        for p in USER_PRESETS_DIR.glob("*.json"):
            with p.open() as f:
                self._user[p.stem] = json.load(f)

    # ── Public API ────────────────────────────────────────────────────────────

    @property
    def preset_names(self) -> list[str]:
        return sorted(self._builtin) + sorted(self._user)

    def get_preset(self, name: str) -> dict | None:
        return self._user.get(name) or self._builtin.get(name)

    def apply_preset(self, config: PlotConfig, name: str) -> PlotConfig:
        """Deep-merge preset *name* over *config* and return new PlotConfig."""
        preset = self.get_preset(name)
        if preset is None:
            raise KeyError(f"Preset not found: {name!r}")
        base = config.model_dump()
        merged = _deep_merge(base, preset)
        return PlotConfig.model_validate(merged)

    def save_user_preset(self, name: str, config: PlotConfig) -> None:
        """Save current config as a user preset."""
        USER_PRESETS_DIR.mkdir(parents=True, exist_ok=True)
        data = config.model_dump()
        path = USER_PRESETS_DIR / f"{name}.json"
        with path.open("w") as f:
            json.dump(data, f, indent=2)
        self._user[name] = data

    def delete_user_preset(self, name: str) -> None:
        path = USER_PRESETS_DIR / f"{name}.json"
        path.unlink(missing_ok=True)
        self._user.pop(name, None)

    def is_user_preset(self, name: str) -> bool:
        return name in self._user

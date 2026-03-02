"""Unit tests for PresetManager."""
import json
import tempfile
from pathlib import Path

import pytest

from bioplot.models.plot_config import PlotConfig


class TestPresetMerge:
    """Test deep merge logic without file I/O."""

    def test_deep_merge_basic(self):
        from bioplot.core.preset_manager import _deep_merge
        base = {"a": 1, "b": {"c": 2, "d": 3}}
        overlay = {"b": {"c": 99}}
        result = _deep_merge(base, overlay)
        assert result["a"] == 1
        assert result["b"]["c"] == 99
        assert result["b"]["d"] == 3

    def test_deep_merge_adds_keys(self):
        from bioplot.core.preset_manager import _deep_merge
        base = {"a": 1}
        overlay = {"b": 2}
        result = _deep_merge(base, overlay)
        assert result["a"] == 1
        assert result["b"] == 2

    def test_deep_merge_non_dict_override(self):
        from bioplot.core.preset_manager import _deep_merge
        base = {"a": {"x": 1}}
        overlay = {"a": "string"}
        result = _deep_merge(base, overlay)
        assert result["a"] == "string"


class TestPresetManager:
    def test_builtin_presets_loaded(self):
        from bioplot.core.preset_manager import PresetManager
        pm = PresetManager()
        names = pm.preset_names
        assert "nature" in names
        assert "cell" in names
        assert "science" in names

    def test_apply_nature_preset(self):
        from bioplot.core.preset_manager import PresetManager
        pm = PresetManager()
        config = PlotConfig()
        new_config = pm.apply_preset(config, "nature")
        # Nature preset uses 7pt axis labels
        assert new_config.font.axis_label_size == 7.0
        assert new_config.figure.width_mm == 89.0

    def test_unknown_preset_raises(self):
        from bioplot.core.preset_manager import PresetManager
        pm = PresetManager()
        with pytest.raises(KeyError):
            pm.apply_preset(PlotConfig(), "nonexistent_preset_xyz")

    def test_user_preset_save_load_delete(self, tmp_path, monkeypatch):
        import bioplot.constants as const
        monkeypatch.setattr(const, "USER_PRESETS_DIR", tmp_path)
        from bioplot.core.preset_manager import PresetManager
        pm = PresetManager()

        config = PlotConfig()
        config.font.family = "Courier"
        pm.save_user_preset("mypreset", config)

        assert "mypreset" in pm.preset_names
        loaded = pm.apply_preset(PlotConfig(), "mypreset")
        assert loaded.font.family == "Courier"

        pm.delete_user_preset("mypreset")
        assert "mypreset" not in pm.preset_names

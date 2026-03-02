"""PyInstaller runtime hook.

Sets environment variables needed by matplotlib and Qt inside the frozen bundle.
"""
import os
import sys

# Point matplotlib to a writable config dir inside the bundle's Application Support
home = os.path.expanduser("~")
mpl_dir = os.path.join(home, "Library", "Application Support", "BioPlot", ".matplotlib")
os.makedirs(mpl_dir, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", mpl_dir)

# Qt plugin path inside frozen app
if getattr(sys, "frozen", False):
    bundle_dir = sys._MEIPASS  # type: ignore[attr-defined]
    qt_plugin_path = os.path.join(bundle_dir, "PySide6", "Qt", "plugins")
    if os.path.isdir(qt_plugin_path):
        os.environ["QT_PLUGIN_PATH"] = qt_plugin_path

    # Prevent Qt from looking for system plugins on macOS
    os.environ.setdefault("QT_MAC_WANTS_LAYER", "1")

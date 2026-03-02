# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for BioPlot.app

Build with:
    pyinstaller packaging/app.spec

Test on clean macOS 12 VM before distribution.
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(SPECPATH).parent
BIOPLOT_PKG = str(PROJECT_ROOT / "bioplot")

block_cipher = None

# ── Collect all hidden imports (numpy/scipy/sklearn have C extensions) ────────
hidden_imports = [
    # Scientific stack
    "numpy", "numpy.core._multiarray_umath",
    "scipy", "scipy.stats", "scipy.linalg",
    "scipy.special", "scipy.sparse",
    "statsmodels", "statsmodels.stats.multitest",
    "sklearn", "sklearn.decomposition", "sklearn.preprocessing",
    "pandas", "pandas.plotting",
    "matplotlib", "matplotlib.backends.backend_qtagg",
    "matplotlib.backends.backend_pdf",
    "matplotlib.backends.backend_svg",
    "seaborn",
    "pydantic", "pydantic.v1",
    "psutil",
    # PySide6
    "PySide6", "PySide6.QtCore", "PySide6.QtGui", "PySide6.QtWidgets",
    # Optional Phase 5
    # "scanpy", "anndata", "umap",
]

# ── Analysis ──────────────────────────────────────────────────────────────────
a = Analysis(
    [str(PROJECT_ROOT / "main.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=[
        (str(PROJECT_ROOT / "bioplot" / "presets"), "bioplot/presets"),
        (str(PROJECT_ROOT / "bioplot" / "assets"), "bioplot/assets"),
    ],
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[str(PROJECT_ROOT / "packaging" / "runtime_hook.py")],
    excludes=[
        "tkinter", "_tkinter",
        "PyQt5", "PyQt6",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# ── PYZ ───────────────────────────────────────────────────────────────────────
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# ── EXE ───────────────────────────────────────────────────────────────────────
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="BioPlot",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,   # Universal if both slices built
    codesign_identity=None,
    entitlements_file=str(PROJECT_ROOT / "packaging" / "entitlements.plist"),
)

# ── COLLECT ───────────────────────────────────────────────────────────────────
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="BioPlot",
)

# ── BUNDLE (.app) ─────────────────────────────────────────────────────────────
app = BUNDLE(
    coll,
    name="BioPlot.app",
    icon=str(PROJECT_ROOT / "packaging" / "BioPlot.icns"),
    bundle_identifier="app.bioplot.BioPlot",
    version="0.1.0",
    info_plist={
        "NSPrincipalClass": "NSApplication",
        "NSAppleScriptEnabled": False,
        "NSHighResolutionCapable": True,
        "LSMinimumSystemVersion": "12.0",
        "CFBundleDocumentTypes": [
            {
                "CFBundleTypeName": "BioPlot Session",
                "CFBundleTypeExtensions": ["biop"],
                "CFBundleTypeRole": "Editor",
            }
        ],
        "UTExportedTypeDeclarations": [
            {
                "UTTypeIdentifier": "app.bioplot.session",
                "UTTypeDescription": "BioPlot Session",
                "UTTypeConformsTo": ["public.json"],
                "UTTypeTagSpecification": {
                    "public.filename-extension": ["biop"],
                },
            }
        ],
    },
)

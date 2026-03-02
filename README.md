# BioPlot

Native macOS GUI for publication-quality RNA-seq visualization — no coding required.

![Platform](https://img.shields.io/badge/platform-macOS-lightgrey)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-LGPL--3.0-green)
![Tests](https://img.shields.io/badge/tests-58%20passed-brightgreen)

---

## Overview

BioPlot fills the gap between web-based explorers (Vitessce, cellxgene) and command-line pipelines (Scanpy, DESeq2). It is a Prism-inspired three-panel desktop app that wraps the full Python bioinformatics stack — Matplotlib, Seaborn, pandas, scipy, statsmodels, scikit-learn — behind a point-and-click interface.

**Bulk RNA-seq MVP (Phases 1–4) is fully implemented.** scRNA-seq / AnnData / UMAP support ships in Phase 5.

---

## Features

### Plot types
| Plot | Description |
|---|---|
| Volcano | log₂FC vs −log₁₀(padj), threshold lines, top-gene labels |
| MA | log-ratio vs mean expression (Bland-Altman style) |
| Heatmap | seaborn clustermap with hierarchical clustering |
| PCA | Sample scatter with % variance labels, group colouring |
| Violin | Per-gene expression distributions across groups |
| Bar | Mean ± CI bar plots |
| Scatter | Generic two-column scatter with optional regression line |
| UMAP | *(Phase 5)* scanpy-backed, requires `anndata` + `scanpy` |

### Analysis
- **DEG**: Student's t-test or Mann-Whitney U, Benjamini-Hochberg / Bonferroni / Holm correction
- **PCA**: sklearn, optional z-score scaling, configurable components
- **Normalization**: CPM, log1p

### Property panel (live preview)
- **Axes** — limits, scale (linear / log / symlog), labels, grid, tick size
- **Colors** — per-category color pickers, seaborn palette selector, colormap
- **Fonts** — family (populated from matplotlib font manager), sizes for title / axes / ticks / legend
- **Statistics** — p-value column, thresholds, top-N gene labels, annotation style
- **Markers** — size, alpha, shape, jitter
- **Theme / Preset** — journal presets with one click; save custom presets

### Journal presets
| Preset | Width | Font | DPI |
|---|---|---|---|
| `nature` | 89 mm | Arial 7 pt | 300 |
| `cell` | 85 mm | Arial 8 pt | 300 |
| `science` | 55 mm | Helvetica 7 pt | 600 |

### Export
PDF · SVG · PNG · EPS · TIFF — configurable DPI and physical dimensions in mm.

### Session files
Full app state serializes to `.biop` (JSON) for reproducible figure sessions.

---

## Installation

```bash
git clone https://github.com/tmcnamara28/BioPlot.git
cd BioPlot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

**Requirements:** macOS 12+, Python 3.10+

---

## Usage

1. **Import data** — `File › Import Data…` or `⌘I`. Accepts CSV / TSV (genes × samples) or H5AD *(Phase 5)*.
2. **Choose a plot** — double-click a type in the Plot Library panel, or `View › Plot Library… (⌘L)`.
3. **Run analysis** — `Analysis › Differential Expression… (⌘D)` or `PCA… (⌘P)`.
4. **Customise** — adjust axes, colors, fonts, statistics and markers in the right panel; preview updates in 250 ms.
5. **Apply a preset** — Theme tab → select journal → Apply Preset.
6. **Export** — `Export › Export Figure… (⌘E)`. Choose format, DPI, and size in mm.
7. **Save session** — `File › Save Session (⌘S)` writes a `.biop` file.

---

## Project structure

```
BioPlot/
├── main.py
├── requirements.txt
├── bioplot/
│   ├── constants.py
│   ├── core/               # Stateless engines + Qt workers
│   │   ├── analysis_engine.py
│   │   ├── data_manager.py
│   │   ├── export_engine.py
│   │   ├── plot_engine.py
│   │   ├── preset_manager.py
│   │   ├── session_manager.py
│   │   └── worker.py
│   ├── models/             # Pydantic v2 dataclasses (no Qt)
│   │   ├── dataset.py
│   │   └── plot_config.py
│   ├── plots/              # BasePlot subclasses
│   ├── presets/            # nature.json, cell.json, science.json
│   ├── assets/sample_data/ # Bundled example DEG CSV
│   └── ui/                 # PySide6 only
│       ├── main_window.py
│       ├── panels/
│       ├── property_widgets/
│       ├── dialogs/
│       └── controllers/
├── tests/
│   ├── unit/               # No Qt, no disk I/O
│   └── integration/        # CSV → DEG → plot → export
└── packaging/
    ├── app.spec            # PyInstaller
    ├── runtime_hook.py
    └── entitlements.plist
```

---

## Architecture

```
UI (PySide6)  ──signals──▶  Controllers  ──call──▶  Core / Models
                                │                   (no Qt imports)
                          QThreadPool
                     LoadWorker · AnalysisWorker · RenderWorker
```

- **Strict layer separation** — `core/` and `models/` have zero Qt imports and are fully headless-testable.
- **Live preview** — property change → `PlotConfig` mutation → 250 ms debounce timer → `RenderWorker` → `canvas.set_figure()` on main thread.
- **Thread safety** — figures are constructed with `matplotlib.figure.Figure()` directly (not `plt.subplots`) so they are safe to build off the main thread.
- **PlotConfig** — single pydantic v2 dataclass serialising the entire plot state to JSON for `.biop` session files and preset deep-merge.

---

## Running tests

```bash
pytest tests/                      # all 58 tests
pytest tests/unit/                 # pure unit tests (no Qt)
pytest tests/integration/          # full pipeline tests
pytest -W error                    # warnings as errors
```

---

## Roadmap

| Phase | Status |
|---|---|
| 1 · Core infrastructure + models | ✅ |
| 2 · Canvas + first plots (volcano, MA, scatter) | ✅ |
| 3 · Full plot library + property panel | ✅ |
| 4 · Presets, export, session management | ✅ |
| 5 · scRNA-seq: H5AD, UMAP, dot plot, adjustText | 🔜 |
| 6 · PyInstaller `.app` + DMG + notarisation | 🔜 |

---

## Dependencies

| Package | Purpose |
|---|---|
| PySide6 | Qt6 GUI framework (LGPL) |
| matplotlib | Figure rendering and export |
| seaborn | Heatmap clustermap, violin/bar plots |
| pandas / numpy | Data handling |
| scipy | Statistical tests |
| statsmodels | Multiple-testing correction |
| scikit-learn | PCA |
| pydantic v2 | PlotConfig serialisation |
| adjustText | Gene label collision avoidance *(Phase 5)* |
| psutil | Memory monitor |

---

## License

LGPL-3.0 — see [LICENSE](LICENSE).

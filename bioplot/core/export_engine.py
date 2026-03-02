"""ExportEngine — save matplotlib Figures to PDF, SVG, or PNG."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from matplotlib.figure import Figure


def mm_to_inches(mm: float) -> float:
    return mm / 25.4


class ExportEngine:
    """Stateless figure export helpers."""

    @staticmethod
    def export(
        fig: "Figure",
        path: str | Path,
        fmt: str | None = None,
        dpi: int = 300,
        width_mm: float | None = None,
        height_mm: float | None = None,
        transparent: bool = False,
        metadata: dict | None = None,
    ) -> Path:
        """Export *fig* to *path*.

        Parameters
        ----------
        fig:
            matplotlib Figure to save.
        path:
            Destination file path. Extension determines format unless *fmt*
            is provided explicitly.
        fmt:
            One of ``"pdf"``, ``"svg"``, ``"png"``, ``"eps"``.
        dpi:
            Resolution for raster formats.
        width_mm, height_mm:
            Override figure size in millimetres.
        transparent:
            Transparent background.
        metadata:
            PDF/SVG metadata dict (title, author, …).

        Returns
        -------
        Resolved output path.
        """
        path = Path(path)
        fmt = fmt or path.suffix.lstrip(".").lower()
        if fmt not in ("pdf", "svg", "png", "eps", "tiff"):
            raise ValueError(f"Unsupported format: {fmt!r}")

        if width_mm is not None and height_mm is not None:
            fig.set_size_inches(mm_to_inches(width_mm), mm_to_inches(height_mm))

        save_kwargs: dict = {
            "dpi": dpi,
            "bbox_inches": "tight",
            "transparent": transparent,
            "format": fmt,
        }
        if metadata and fmt in ("pdf", "svg"):
            save_kwargs["metadata"] = metadata

        path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, **save_kwargs)
        return path.resolve()

    @staticmethod
    def export_pdf(
        fig: "Figure",
        path: str | Path,
        **kwargs,
    ) -> Path:
        return ExportEngine.export(fig, path, fmt="pdf", **kwargs)

    @staticmethod
    def export_svg(
        fig: "Figure",
        path: str | Path,
        **kwargs,
    ) -> Path:
        return ExportEngine.export(fig, path, fmt="svg", **kwargs)

    @staticmethod
    def export_png(
        fig: "Figure",
        path: str | Path,
        **kwargs,
    ) -> Path:
        return ExportEngine.export(fig, path, fmt="png", **kwargs)

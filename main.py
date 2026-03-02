"""BioPlot — Native macOS GUI for RNA-seq Visualization."""
import sys
import os

# Set matplotlib backend before any Qt imports
os.environ.setdefault("MPLBACKEND", "qtagg")

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from bioplot.ui.main_window import MainWindow


def main() -> None:
    # Enable high-DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("BioPlot")
    app.setApplicationVersion("0.1.0")
    app.setOrganizationName("BioPlot")
    app.setOrganizationDomain("bioplot.app")

    # macOS style
    app.setStyle("macos")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

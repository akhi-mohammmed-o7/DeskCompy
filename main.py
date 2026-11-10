"""DeskCompy — a desk lantern that listens to rhythm, never to words.

Run from this folder:

    python main.py

No console window:

    launch.bat

Package later (after ``pip install pyinstaller``):

    pyinstaller --noconfirm lumen_moth.spec

The executable looks for an ``assets`` folder beside it first, so images can
be swapped without rebuilding.
"""

from __future__ import annotations

import logging
import sys

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from paths import APP_NAME, VERSION
from ui_engine import CompanionWindow


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def main() -> int:
    _configure_logging()
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(VERSION)
    app.setOrganizationName("DeskCompy")
    app.setQuitOnLastWindowClosed(True)

    window = CompanionWindow()
    app.aboutToQuit.connect(window.shutdown)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

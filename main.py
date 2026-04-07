#!/usr/bin/env python3
"""Dispatch — slide remote → OSC bridge."""

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from app.config import AppConfig
from app.main_window import MainWindow
from app.theme import get_stylesheet

_ASSETS = Path(__file__).parent / "assets"


def main() -> None:
    # High-DPI support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Dispatch")
    app.setOrganizationName("Dispatch")
    app.setApplicationDisplayName("Dispatch")

    # Force dark appearance so the native title bar matches the dark theme
    app.styleHints().setColorScheme(Qt.ColorScheme.Dark)
    icon = QIcon()
    iconset = _ASSETS / "Dispatch.iconset"
    for name in ("icon_16x16.png", "icon_32x32.png", "icon_128x128.png",
                 "icon_256x256.png", "icon_512x512.png"):
        p = iconset / name
        if p.exists():
            icon.addFile(str(p))
    if icon.isNull():
        fallback = _ASSETS / "icon.png"
        if fallback.exists():
            icon = QIcon(str(fallback))
    app.setWindowIcon(icon)

    config = AppConfig.load_default()
    app.setStyleSheet(get_stylesheet(config.settings.theme))
    window = MainWindow(config)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

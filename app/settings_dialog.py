"""Settings dialog for advanced/global app options."""

import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
)

from .config import AppSettings


class SettingsDialog(QDialog):
    def __init__(self, settings: AppSettings, parent=None) -> None:
        super().__init__(parent)
        self._settings = settings
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.setMinimumWidth(420)
        self._build_ui()
        self._populate(settings)

    # ── Public ───────────────────────────────────────────────────────────────

    def get_settings(self) -> AppSettings:
        return AppSettings(
            long_press_threshold_ms=self._threshold_spin.value(),
            theme="light" if self._radio_light.isChecked() else "dark",
        )

    # ── Private ───────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 20)
        root.setSpacing(20)

        # ── Appearance section ────────────────────────────────────────────────
        root.addWidget(self._section_label("APPEARANCE"))

        theme_row = QHBoxLayout()
        theme_row.setSpacing(20)
        self._radio_dark = QRadioButton("Dark")
        self._radio_light = QRadioButton("Light")
        self._theme_group = QButtonGroup(self)
        self._theme_group.addButton(self._radio_dark)
        self._theme_group.addButton(self._radio_light)
        theme_row.addWidget(self._radio_dark)
        theme_row.addWidget(self._radio_light)
        theme_row.addStretch()
        root.addLayout(theme_row)

        divider = QFrame()
        divider.setObjectName("divider")
        root.addWidget(divider)

        # ── Input section ────────────────────────────────────────────────────
        root.addWidget(self._section_label("INPUT"))

        # Long press threshold
        root.addWidget(QLabel("Long Press Threshold"))

        threshold_row = QHBoxLayout()
        threshold_row.setSpacing(12)

        self._threshold_slider = QSlider(Qt.Horizontal)
        self._threshold_slider.setRange(100, 2000)
        self._threshold_slider.setSingleStep(50)
        self._threshold_slider.setPageStep(100)
        self._threshold_slider.setTickInterval(250)
        threshold_row.addWidget(self._threshold_slider, 1)

        self._threshold_spin = QSpinBox()
        self._threshold_spin.setRange(100, 2000)
        self._threshold_spin.setSuffix(" ms")
        self._threshold_spin.setFixedWidth(90)
        threshold_row.addWidget(self._threshold_spin)

        root.addLayout(threshold_row)

        # Keep slider and spinbox in sync
        self._threshold_slider.valueChanged.connect(self._threshold_spin.setValue)
        self._threshold_spin.valueChanged.connect(self._threshold_slider.setValue)

        hint = QLabel(
            "How long a key must be held before a Long Press action fires. "
            "Short press triggers on release if the key was released before "
            "this threshold."
        )
        hint.setObjectName("hintLabel")
        hint.setWordWrap(True)
        root.addWidget(hint)

        # ── Platform note ────────────────────────────────────────────────────
        if sys.platform.startswith("linux"):
            note_frame = QFrame()
            note_frame.setObjectName("dialogPanel")
            note_layout = QVBoxLayout(note_frame)
            note_layout.setContentsMargins(14, 12, 14, 12)
            note_lbl = QLabel(
                "⚠  On Wayland, global key capture may be limited.  "
                "Running under XWayland or X11 is recommended for full "
                "remote support."
            )
            note_lbl.setObjectName("warningLabel")
            note_lbl.setWordWrap(True)
            note_layout.addWidget(note_lbl)
            root.addWidget(note_frame)
        elif sys.platform == "darwin":
            note_frame = QFrame()
            note_frame.setObjectName("dialogPanel")
            note_layout = QVBoxLayout(note_frame)
            note_layout.setContentsMargins(14, 12, 14, 12)
            note_lbl = QLabel(
                "Dispatch requires two macOS permissions for global key capture:\n\n"
                "  •  System Settings → Privacy & Security → Accessibility\n"
                "  •  System Settings → Privacy & Security → Input Monitoring\n\n"
                "Enable Dispatch in both, then restart the app.\n\n"
                "Note: some remote buttons (such as the Spotlight highlight button) "
                "send hardware signals rather than keyboard events and cannot be "
                "captured by any keyboard listener."
            )
            note_lbl.setObjectName("warningLabel")
            note_lbl.setWordWrap(True)
            note_layout.addWidget(note_lbl)
            root.addWidget(note_frame)

        root.addStretch()

        # ── Buttons ───────────────────────────────────────────────────────────
        divider = QFrame()
        divider.setObjectName("divider")
        root.addWidget(divider)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("cancelButton")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        save_btn = QPushButton("Save")
        save_btn.setObjectName("primaryButton")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self.accept)
        btn_row.addWidget(save_btn)

        root.addLayout(btn_row)

    def _populate(self, settings: AppSettings) -> None:
        self._threshold_spin.setValue(settings.long_press_threshold_ms)
        self._threshold_slider.setValue(settings.long_press_threshold_ms)
        if settings.theme == "light":
            self._radio_light.setChecked(True)
        else:
            self._radio_dark.setChecked(True)

    @staticmethod
    def _section_label(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("dialogSectionLabel")
        return lbl

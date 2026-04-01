# Catppuccin Mocha (dark) and Latte (light) themes

DARK_COLORS = {
    "base": "#1e1e2e",
    "mantle": "#181825",
    "crust": "#11111b",
    "surface0": "#313244",
    "surface1": "#45475a",
    "surface2": "#585b70",
    "overlay0": "#6c7086",
    "overlay1": "#7f849c",
    "text": "#cdd6f4",
    "subtext0": "#a6adc8",
    "subtext1": "#bac2de",
    "lavender": "#b4befe",
    "blue": "#89b4fa",
    "sapphire": "#74c7ec",
    "green": "#a6e3a1",
    "yellow": "#f9e2af",
    "peach": "#fab387",
    "red": "#f38ba8",
    "mauve": "#cba6f7",
    "teal": "#94e2d5",
}

LIGHT_COLORS = {
    "base": "#eff1f5",
    "mantle": "#e6e9ef",
    "crust": "#dce0e8",
    "surface0": "#ccd0da",
    "surface1": "#bcc0cc",
    "surface2": "#acb0be",
    "overlay0": "#9ca0b0",
    "overlay1": "#8c8fa1",
    "text": "#4c4f69",
    "subtext0": "#6c6f85",
    "subtext1": "#5c5f77",
    "lavender": "#7287fd",
    "blue": "#1e66f5",
    "sapphire": "#209fb5",
    "green": "#40a02b",
    "yellow": "#df8e1d",
    "peach": "#fe640b",
    "red": "#d20f39",
    "mauve": "#8839ef",
    "teal": "#179299",
}

# Keep a reference to current colors for any module that imports COLORS directly
COLORS = DARK_COLORS


def get_stylesheet(theme: str = "dark") -> str:
    C = LIGHT_COLORS if theme == "light" else DARK_COLORS
    return f"""
/* ─── Base ─────────────────────────────────────── */
QMainWindow, QDialog {{
    background-color: {C["base"]};
    color: {C["text"]};
}}

QWidget {{
    background-color: transparent;
    color: {C["text"]};
    font-family: "SF Pro Display", "Inter", "Segoe UI", "Helvetica Neue", Arial, sans-serif;
    font-size: 13px;
    selection-background-color: {C["lavender"]};
    selection-color: {C["base"]};
}}

/* ─── Scrollbars ────────────────────────────────── */
QScrollBar:vertical {{
    background: transparent;
    width: 6px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {C["surface1"]};
    border-radius: 3px;
    min-height: 20px;
}}
QScrollBar::handle:vertical:hover {{
    background: {C["surface2"]};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
    background: none;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none;
}}

/* ─── QFrame sections ───────────────────────────── */
#headerFrame {{
    background-color: {C["mantle"]};
    border-bottom: 1px solid {C["surface0"]};
}}

#sectionFrame {{
    background-color: {C["mantle"]};
    border-bottom: 1px solid {C["surface0"]};
}}

#mappingsSectionOuter {{
    background-color: {C["base"]};
}}

#statusBarFrame {{
    background-color: {C["mantle"]};
    border-top: 1px solid {C["surface0"]};
}}

#colHeader {{
    background-color: transparent;
}}

#mappingsContainer {{
    background-color: transparent;
}}

/* ─── Mapping rows ──────────────────────────────── */
#mappingRow {{
    background-color: {C["surface0"]};
    border: 1px solid {C["surface1"]};
    border-radius: 8px;
}}
#mappingRow:hover {{
    background-color: {C["surface1"]};
    border: 1px solid {C["surface2"]};
}}

/* ─── Labels ────────────────────────────────────── */
#headerIcon {{
    color: {C["lavender"]};
    font-size: 22px;
}}
#headerTitle {{
    color: {C["text"]};
    font-size: 17px;
    font-weight: 600;
}}
#sectionLabel {{
    color: {C["overlay1"]};
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1px;
}}
#colHeaderLabel {{
    color: {C["overlay0"]};
    font-size: 11px;
    font-weight: 600;
}}
#mappingName {{
    color: {C["text"]};
    font-weight: 500;
}}
#mappingKey {{
    color: {C["subtext0"]};
    font-family: "SF Mono", "JetBrains Mono", "Fira Code", "Consolas", monospace;
    font-size: 12px;
}}
#mappingOsc {{
    color: {C["blue"]};
    font-family: "SF Mono", "JetBrains Mono", "Fira Code", "Consolas", monospace;
    font-size: 12px;
}}
#fieldLabel {{
    color: {C["subtext0"]};
    font-size: 12px;
}}
#statusText {{
    color: {C["subtext0"]};
    font-size: 12px;
}}
#listenerStatus {{
    color: {C["subtext0"]};
    font-size: 12px;
}}
#lastAction {{
    color: {C["subtext0"]};
    font-size: 12px;
    font-family: "SF Mono", "JetBrains Mono", "Fira Code", "Consolas", monospace;
}}
#dialogSectionLabel {{
    color: {C["overlay1"]};
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1px;
}}
#hintLabel {{
    color: {C["overlay0"]};
    font-size: 11px;
}}
#captureLabel {{
    color: {C["yellow"]};
    font-size: 12px;
    font-style: italic;
}}
#keyDisplayLabel {{
    color: {C["teal"]};
    font-family: "SF Mono", "JetBrains Mono", "Fira Code", "Consolas", monospace;
    font-size: 13px;
    font-weight: 600;
}}
#warningLabel {{
    color: {C["yellow"]};
    font-size: 12px;
}}
#errorLabel {{
    color: {C["red"]};
    font-size: 12px;
}}

/* ─── Status dots ───────────────────────────────── */
#statusDotActive {{
    color: {C["green"]};
    font-size: 10px;
}}
#statusDotInactive {{
    color: {C["surface2"]};
    font-size: 10px;
}}
#listenerDotActive {{
    color: {C["green"]};
    font-size: 10px;
}}
#listenerDotInactive {{
    color: {C["red"]};
    font-size: 10px;
}}

/* ─── Type badges ───────────────────────────────── */
#badgeShort {{
    background-color: rgba(137, 180, 250, 0.15);
    color: {C["blue"]};
    border: 1px solid rgba(137, 180, 250, 0.3);
    border-radius: 4px;
    padding: 1px 4px;
    font-size: 10px;
    font-weight: 700;
}}
#badgeLong {{
    background-color: rgba(203, 166, 247, 0.15);
    color: {C["mauve"]};
    border: 1px solid rgba(203, 166, 247, 0.3);
    border-radius: 4px;
    padding: 1px 4px;
    font-size: 10px;
    font-weight: 700;
}}
#badgeAny {{
    background-color: rgba(148, 226, 213, 0.15);
    color: {C["teal"]};
    border: 1px solid rgba(148, 226, 213, 0.3);
    border-radius: 4px;
    padding: 1px 4px;
    font-size: 10px;
    font-weight: 700;
}}

/* ─── Enabled dot button ────────────────────────── */
#enabledDot {{
    background: transparent;
    border: none;
    font-size: 14px;
    padding: 0;
}}
#enabledDot[enabled_state="on"] {{
    color: {C["green"]};
}}
#enabledDot[enabled_state="off"] {{
    color: {C["surface2"]};
}}

/* ─── Buttons ───────────────────────────────────── */
QPushButton {{
    background-color: {C["surface0"]};
    color: {C["text"]};
    border: 1px solid {C["surface1"]};
    border-radius: 6px;
    padding: 6px 14px;
    font-size: 13px;
    font-weight: 500;
}}
QPushButton:hover {{
    background-color: {C["surface1"]};
    border-color: {C["surface2"]};
}}
QPushButton:pressed {{
    background-color: {C["surface2"]};
}}
QPushButton:disabled {{
    color: {C["overlay0"]};
    background-color: {C["surface0"]};
    border-color: {C["surface0"]};
}}

#headerButton {{
    background-color: transparent;
    color: {C["subtext0"]};
    border: 1px solid {C["surface1"]};
    border-radius: 6px;
    padding: 5px 12px;
    font-size: 12px;
}}
#headerButton:hover {{
    background-color: {C["surface0"]};
    color: {C["text"]};
}}

#addButton {{
    background-color: rgba(180, 190, 254, 0.15);
    color: {C["lavender"]};
    border: 1px solid rgba(180, 190, 254, 0.3);
    border-radius: 6px;
    padding: 5px 12px;
    font-size: 12px;
    font-weight: 600;
}}
#addButton:hover {{
    background-color: rgba(180, 190, 254, 0.25);
    border-color: {C["lavender"]};
}}

#rowButton {{
    background-color: transparent;
    color: {C["subtext0"]};
    border: 1px solid {C["surface1"]};
    border-radius: 5px;
    padding: 3px 8px;
    font-size: 12px;
}}
#rowButton:hover {{
    background-color: {C["surface1"]};
    color: {C["text"]};
}}

#deleteButton {{
    background-color: transparent;
    color: {C["surface2"]};
    border: 1px solid {C["surface1"]};
    border-radius: 5px;
    padding: 2px;
    font-size: 12px;
    font-weight: 700;
}}
#deleteButton:hover {{
    background-color: rgba(243, 139, 168, 0.15);
    color: {C["red"]};
    border-color: rgba(243, 139, 168, 0.4);
}}

#primaryButton {{
    background-color: {C["lavender"]};
    color: {C["base"]};
    border: none;
    border-radius: 6px;
    padding: 7px 20px;
    font-size: 13px;
    font-weight: 600;
}}
#primaryButton:hover {{
    background-color: {C["blue"]};
}}
#primaryButton:pressed {{
    background-color: {C["sapphire"]};
}}

#cancelButton {{
    background-color: transparent;
    color: {C["subtext0"]};
    border: 1px solid {C["surface1"]};
    border-radius: 6px;
    padding: 7px 20px;
    font-size: 13px;
}}
#cancelButton:hover {{
    background-color: {C["surface0"]};
    color: {C["text"]};
}}

#listenButton {{
    background-color: rgba(148, 226, 213, 0.15);
    color: {C["teal"]};
    border: 1px solid rgba(148, 226, 213, 0.3);
    border-radius: 6px;
    padding: 6px 14px;
    font-size: 12px;
    font-weight: 600;
}}
#listenButton:hover {{
    background-color: rgba(148, 226, 213, 0.25);
}}
#listenButton:disabled {{
    color: {C["overlay0"]};
    background-color: transparent;
    border-color: {C["surface1"]};
}}

#listeningActiveButton {{
    background-color: rgba(249, 226, 175, 0.15);
    color: {C["yellow"]};
    border: 1px solid rgba(249, 226, 175, 0.4);
    border-radius: 6px;
    padding: 6px 14px;
    font-size: 12px;
    font-weight: 600;
}}

/* ─── Inputs ────────────────────────────────────── */
QLineEdit {{
    background-color: {C["mantle"]};
    color: {C["text"]};
    border: 1px solid {C["surface1"]};
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 13px;
    selection-background-color: {C["lavender"]};
    selection-color: {C["base"]};
}}
QLineEdit:focus {{
    border-color: {C["lavender"]};
    background-color: {C["crust"]};
}}
QLineEdit:disabled {{
    color: {C["overlay0"]};
    background-color: {C["surface0"]};
}}
QLineEdit#inputField {{
    background-color: {C["mantle"]};
}}

QSpinBox {{
    background-color: {C["mantle"]};
    color: {C["text"]};
    border: 1px solid {C["surface1"]};
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 13px;
}}
QSpinBox:focus {{
    border-color: {C["lavender"]};
}}
QSpinBox::up-button, QSpinBox::down-button {{
    background-color: {C["surface0"]};
    border: none;
    width: 18px;
    border-radius: 3px;
}}
QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
    background-color: {C["surface1"]};
}}

/* ─── Radio buttons ─────────────────────────────── */
QRadioButton {{
    color: {C["text"]};
    font-size: 13px;
    spacing: 6px;
}}
QRadioButton::indicator {{
    width: 16px;
    height: 16px;
    border-radius: 8px;
    border: 2px solid {C["surface2"]};
    background-color: transparent;
}}
QRadioButton::indicator:checked {{
    border-color: {C["lavender"]};
    background-color: {C["lavender"]};
}}
QRadioButton::indicator:hover {{
    border-color: {C["subtext0"]};
}}

/* ─── Checkboxes ────────────────────────────────── */
QCheckBox {{
    color: {C["text"]};
    font-size: 13px;
    spacing: 8px;
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 2px solid {C["surface2"]};
    background-color: transparent;
}}
QCheckBox::indicator:checked {{
    border-color: {C["lavender"]};
    background-color: {C["lavender"]};
    image: url(none);
}}
QCheckBox::indicator:hover {{
    border-color: {C["subtext0"]};
}}

/* ─── Slider ────────────────────────────────────── */
QSlider::groove:horizontal {{
    background: {C["surface1"]};
    height: 4px;
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {C["lavender"]};
    width: 16px;
    height: 16px;
    margin: -6px 0;
    border-radius: 8px;
}}
QSlider::handle:horizontal:hover {{
    background: {C["blue"]};
}}
QSlider::sub-page:horizontal {{
    background: {C["lavender"]};
    border-radius: 2px;
}}

/* ─── Message boxes ─────────────────────────────── */
QMessageBox {{
    background-color: {C["base"]};
}}
QMessageBox QLabel {{
    color: {C["text"]};
}}

/* ─── Divider lines ─────────────────────────────── */
#divider {{
    background-color: {C["surface0"]};
    max-height: 1px;
    min-height: 1px;
}}

/* ─── Dialog panels ─────────────────────────────── */
#dialogPanel {{
    background-color: {C["mantle"]};
    border: 1px solid {C["surface0"]};
    border-radius: 8px;
}}
#keyDisplayPanel {{
    background-color: {C["surface0"]};
    border: 1px solid {C["surface1"]};
    border-radius: 6px;
}}

/* ─── Test (fire OSC) button ────────────────────── */
#testButton {{
    background-color: transparent;
    color: {C["teal"]};
    border: 1px solid rgba(148, 226, 213, 0.3);
    border-radius: 5px;
    padding: 2px;
    font-size: 12px;
}}
#testButton:hover {{
    background-color: rgba(148, 226, 213, 0.15);
    border-color: rgba(148, 226, 213, 0.6);
}}
#testButton:pressed {{
    background-color: rgba(148, 226, 213, 0.25);
}}

/* ─── Paused state button ───────────────────────── */
#pausedButton {{
    background-color: rgba(249, 226, 175, 0.15);
    color: {C["yellow"]};
    border: 1px solid rgba(249, 226, 175, 0.3);
    border-radius: 6px;
    padding: 5px 12px;
    font-size: 12px;
}}
#pausedButton:hover {{
    background-color: rgba(249, 226, 175, 0.25);
    border-color: {C["yellow"]};
}}

/* ─── OSC Log panel ─────────────────────────────── */
#logPanelFrame {{
    background-color: {C["crust"]};
    border-top: 1px solid {C["surface0"]};
}}
QPlainTextEdit#oscLogEdit {{
    background-color: {C["crust"]};
    color: {C["subtext0"]};
    border: none;
    font-family: "SF Mono", "JetBrains Mono", "Fira Code", "Consolas", monospace;
    font-size: 11px;
    selection-background-color: {C["lavender"]};
    selection-color: {C["base"]};
}}

/* ─── Tab widget ────────────────────────────────── */
QTabWidget::pane {{
    border: none;
    background-color: {C["base"]};
}}
QTabWidget::tab-bar {{
    left: 20px;
}}
QTabBar {{
    background-color: {C["mantle"]};
    border-bottom: 1px solid {C["surface0"]};
}}
QTabBar::tab {{
    background-color: transparent;
    color: {C["overlay1"]};
    border: none;
    border-bottom: 2px solid transparent;
    padding: 8px 18px;
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.5px;
}}
QTabBar::tab:selected {{
    color: {C["text"]};
    border-bottom: 2px solid {C["lavender"]};
}}
QTabBar::tab:hover:!selected {{
    color: {C["subtext1"]};
    border-bottom: 2px solid {C["surface2"]};
}}

/* ─── Notification banner ───────────────────────── */
#notificationBanner {{
    background-color: rgba(203, 166, 247, 0.12);
    border-bottom: 1px solid rgba(203, 166, 247, 0.25);
}}
#notificationBannerText {{
    color: {C["mauve"]};
    font-size: 12px;
}}

/* ─── Permission warning banner ─────────────────── */
#permissionBannerFrame {{
    background-color: rgba(249, 226, 175, 0.10);
    border-bottom: 1px solid rgba(249, 226, 175, 0.25);
}}
#permissionBannerText {{
    color: {C["yellow"]};
    font-size: 12px;
}}

/* ─── Template-locked fields ────────────────────── */
QLineEdit[templateLocked="true"] {{
    color: {C["overlay1"]};
    background-color: {C["surface0"]};
    border-color: {C["surface0"]};
}}

/* ─── Template combo ────────────────────────────── */
QComboBox#templateCombo {{
    background-color: {C["mantle"]};
    color: {C["text"]};
    border: 1px solid {C["surface1"]};
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 13px;
}}
QComboBox#templateCombo:focus {{
    border-color: {C["lavender"]};
}}
QComboBox#templateCombo::drop-down {{
    border: none;
    width: 24px;
}}
QComboBox#templateCombo::down-arrow {{
    width: 10px;
    height: 10px;
}}
QComboBox QAbstractItemView {{
    background-color: {C["mantle"]};
    color: {C["text"]};
    border: 1px solid {C["surface1"]};
    selection-background-color: {C["surface1"]};
    selection-color: {C["text"]};
    outline: none;
}}

/* ─── Template args label ───────────────────────── */
#templateArgs {{
    color: {C["subtext0"]};
    font-family: "SF Mono", "JetBrains Mono", "Fira Code", "Consolas", monospace;
    font-size: 12px;
}}

/* ─── Empty state label ─────────────────────────── */
#emptyStateLabel {{
    color: {C["overlay0"]};
    font-size: 13px;
    padding: 40px 0;
}}

/* ─── Save-as-template button ───────────────────── */
#saveTemplateButton {{
    background-color: rgba(166, 227, 161, 0.10);
    color: {C["green"]};
    border: 1px solid rgba(166, 227, 161, 0.25);
    border-radius: 6px;
    padding: 5px 12px;
    font-size: 12px;
    font-weight: 500;
}}
#saveTemplateButton:hover {{
    background-color: rgba(166, 227, 161, 0.20);
    border-color: rgba(166, 227, 161, 0.45);
}}

/* ─── Profile bar ───────────────────────────────── */
#profileBarFrame {{
    background-color: {C["mantle"]};
    border-bottom: 1px solid {C["surface0"]};
}}

QComboBox#profileCombo {{
    background-color: {C["surface0"]};
    color: {C["text"]};
    border: 1px solid {C["surface1"]};
    border-radius: 6px;
    padding: 4px 8px;
    font-size: 13px;
    font-weight: 500;
}}
QComboBox#profileCombo:focus {{
    border-color: {C["lavender"]};
}}
QComboBox#profileCombo::drop-down {{
    border: none;
    width: 22px;
}}
QComboBox#profileCombo::down-arrow {{
    width: 10px;
    height: 10px;
}}

#iconButton {{
    background-color: transparent;
    color: {C["subtext0"]};
    border: 1px solid {C["surface1"]};
    border-radius: 5px;
    padding: 2px;
    font-size: 14px;
}}
#iconButton:hover {{
    background-color: {C["surface1"]};
    color: {C["text"]};
}}

/* ─── Toggle badge ──────────────────────────────── */
#badgeToggle {{
    background-color: rgba(250, 179, 135, 0.15);
    color: {C["peach"]};
    border: 1px solid rgba(250, 179, 135, 0.3);
    border-radius: 4px;
    padding: 1px 4px;
    font-size: 10px;
    font-weight: 700;
}}

/* ─── Destination rows ──────────────────────────── */
#destinationRow {{
    background-color: transparent;
}}
#destinationName {{
    color: {C["text"]};
    font-weight: 500;
    font-size: 13px;
}}
#destinationAddr {{
    color: {C["subtext0"]};
    font-family: "SF Mono", "JetBrains Mono", "Fira Code", "Consolas", monospace;
    font-size: 12px;
}}

/* ─── Test outline button (template dialog) ─────── */
#testOutlineButton {{
    background-color: transparent;
    color: {C["teal"]};
    border: 1px solid rgba(148, 226, 213, 0.4);
    border-radius: 6px;
    padding: 6px 14px;
    font-size: 12px;
    font-weight: 500;
}}
#testOutlineButton:hover {{
    background-color: rgba(148, 226, 213, 0.12);
    border-color: rgba(148, 226, 213, 0.65);
}}
"""

# Legacy alias so any code that imports STYLESHEET still works
STYLESHEET = get_stylesheet("dark")

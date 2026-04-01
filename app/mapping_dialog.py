"""Dialog for creating or editing a single key → OSC mapping."""

from typing import Callable, List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .config import Mapping, OSCDestination, Template
from .key_utils import key_display
from .osc_sender import OSCSender


class MappingDialog(QDialog):
    """
    Modal dialog to create or edit a Mapping.

    Key-capture is delegated back to the main window so the global listener
    can intercept the next keystroke.  The dialog emits signals to request
    capture and to cancel it.

    Pass a live ``templates`` list, an ``OSCSender``, and a ``destinations``
    list to enable template selection, test OSC, and per-destination routing.
    """

    key_capture_requested = Signal(object)   # delivers a Python callable
    key_capture_cancelled = Signal()
    template_added = Signal(object)          # emits the new Template

    def __init__(
        self,
        mapping: Mapping,
        templates: List[Template],
        osc: OSCSender,
        destinations: List[OSCDestination],
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._mapping = mapping
        self._templates = templates
        self._osc = osc
        self._destinations = destinations
        self._listening = False
        self._dest_checkboxes: List[tuple[str, QCheckBox]] = []  # (dest_id, checkbox)

        self.setWindowTitle("Edit Mapping" if mapping.key_str else "New Mapping")
        self.setModal(True)
        self.setMinimumWidth(480)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Minimum)

        self._build_ui()
        self._populate(mapping)

    # ── Public ───────────────────────────────────────────────────────────────

    def get_mapping(self) -> Mapping:
        """Return the mapping with current dialog values applied."""
        m = self._mapping.copy()
        m.name = self._name_edit.text().strip() or "Unnamed"
        m.press_type = self._get_press_type()
        m.osc_address = self._osc_addr_edit.text().strip()
        m.osc_args = self._osc_args_edit.text().strip()
        m.enabled = self._enabled_cb.isChecked()
        m.template_id = self._current_template_id()
        m.toggle_mode = self._toggle_cb.isChecked()
        m.osc_address_b = self._osc_addr_b_edit.text().strip()
        m.osc_args_b = self._osc_args_b_edit.text().strip()
        m.destination_ids = self._get_checked_destination_ids()
        return m

    # ── Signal handlers (called by main window via signal) ────────────────────

    def on_key_captured(self, key_str: str) -> None:
        """Called when the global listener has captured a key."""
        self._mapping.key_str = key_str
        self._update_key_display(key_str)
        self._set_listening(False)

    # ── Private ───────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 20)
        root.setSpacing(20)

        # ── Name ─────────────────────────────────────────────────────────────
        root.addWidget(self._section_label("NAME"))
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("e.g. Forward Long Press")
        root.addWidget(self._name_edit)

        # ── Key binding ──────────────────────────────────────────────────────
        root.addWidget(self._section_label("KEY BINDING"))

        key_row = QHBoxLayout()
        key_row.setSpacing(10)

        key_panel = QFrame()
        key_panel.setObjectName("keyDisplayPanel")
        key_panel_layout = QHBoxLayout(key_panel)
        key_panel_layout.setContentsMargins(12, 8, 12, 8)
        self._key_display_lbl = QLabel("Not set")
        self._key_display_lbl.setObjectName("keyDisplayLabel")
        self._capture_status_lbl = QLabel("")
        self._capture_status_lbl.setObjectName("captureLabel")
        key_panel_layout.addWidget(self._key_display_lbl)
        key_panel_layout.addStretch()
        key_panel_layout.addWidget(self._capture_status_lbl)

        key_row.addWidget(key_panel, 1)

        self._listen_btn = QPushButton("Listen")
        self._listen_btn.setObjectName("listenButton")
        self._listen_btn.setFixedWidth(80)
        self._listen_btn.setToolTip(
            "Click then press a key on your remote to capture it"
        )
        self._listen_btn.clicked.connect(self._toggle_listen)
        key_row.addWidget(self._listen_btn)

        root.addLayout(key_row)

        hint = QLabel(
            "Click Listen, then press any key on your remote. "
            "Hold for long press detection. "
            "Note: some remote buttons (e.g. the Spotlight highlight button) "
            "send hardware signals rather than keyboard events and cannot be captured."
        )
        hint.setObjectName("hintLabel")
        hint.setWordWrap(True)
        root.addWidget(hint)

        # ── Press type ───────────────────────────────────────────────────────
        root.addWidget(self._section_label("PRESS TYPE"))

        radio_row = QHBoxLayout()
        radio_row.setSpacing(20)

        self._radio_short = QRadioButton("Short press")
        self._radio_long = QRadioButton("Long press")
        self._radio_any = QRadioButton("Any (both)")

        self._press_type_group = QButtonGroup(self)
        self._press_type_group.addButton(self._radio_short)
        self._press_type_group.addButton(self._radio_long)
        self._press_type_group.addButton(self._radio_any)

        radio_row.addWidget(self._radio_short)
        radio_row.addWidget(self._radio_long)
        radio_row.addWidget(self._radio_any)
        radio_row.addStretch()
        root.addLayout(radio_row)

        # ── OSC command A ─────────────────────────────────────────────────────
        root.addWidget(self._section_label("OSC COMMAND"))

        # Template dropdown row
        tmpl_row = QHBoxLayout()
        tmpl_row.setSpacing(8)

        self._template_combo = QComboBox()
        self._template_combo.setObjectName("templateCombo")
        self._template_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._rebuild_combo()
        self._template_combo.currentIndexChanged.connect(self._on_template_changed)
        tmpl_row.addWidget(self._template_combo, 1)

        self._detach_btn = QPushButton("Detach")
        self._detach_btn.setObjectName("rowButton")
        self._detach_btn.setToolTip("Unlink from template and edit the command manually")
        self._detach_btn.setFixedWidth(68)
        self._detach_btn.clicked.connect(self._detach_template)
        self._detach_btn.setVisible(False)
        tmpl_row.addWidget(self._detach_btn)

        root.addLayout(tmpl_row)

        self._osc_addr_edit = QLineEdit()
        self._osc_addr_edit.setPlaceholderText("/atem/cut")
        root.addWidget(self._osc_addr_edit)

        osc_args_lbl = QLabel("OSC ARGUMENTS  (optional)")
        osc_args_lbl.setObjectName("dialogSectionLabel")
        root.addWidget(osc_args_lbl)

        self._osc_args_edit = QLineEdit()
        self._osc_args_edit.setPlaceholderText('e.g.  1   or   2.5   or   "text"')
        root.addWidget(self._osc_args_edit)

        args_hint = QLabel(
            "Space-separated values. Integers and floats are detected automatically."
        )
        args_hint.setObjectName("hintLabel")
        root.addWidget(args_hint)

        self._save_tmpl_btn = QPushButton("Save as template…")
        self._save_tmpl_btn.setObjectName("saveTemplateButton")
        self._save_tmpl_btn.setToolTip("Save this OSC command as a reusable template")
        self._save_tmpl_btn.clicked.connect(self._save_as_template)
        root.addWidget(self._save_tmpl_btn)

        # ── Toggle mode ───────────────────────────────────────────────────────
        divider1 = QFrame()
        divider1.setObjectName("divider")
        root.addWidget(divider1)

        self._toggle_cb = QCheckBox("Toggle mode — alternate between two commands on each press")
        self._toggle_cb.toggled.connect(self._on_toggle_mode_changed)
        root.addWidget(self._toggle_cb)

        self._toggle_section = QWidget()
        toggle_layout = QVBoxLayout(self._toggle_section)
        toggle_layout.setContentsMargins(0, 0, 0, 0)
        toggle_layout.setSpacing(8)

        toggle_layout.addWidget(self._section_label("OSC COMMAND B  (second press)"))

        self._osc_addr_b_edit = QLineEdit()
        self._osc_addr_b_edit.setPlaceholderText("/atem/cut")
        toggle_layout.addWidget(self._osc_addr_b_edit)

        osc_args_b_lbl = QLabel("OSC ARGUMENTS B  (optional)")
        osc_args_b_lbl.setObjectName("dialogSectionLabel")
        toggle_layout.addWidget(osc_args_b_lbl)

        self._osc_args_b_edit = QLineEdit()
        self._osc_args_b_edit.setPlaceholderText('e.g.  0   or   "off"')
        toggle_layout.addWidget(self._osc_args_b_edit)

        toggle_hint = QLabel(
            "First press fires Command A, second press fires Command B, and so on."
        )
        toggle_hint.setObjectName("hintLabel")
        toggle_layout.addWidget(toggle_hint)

        self._toggle_section.setVisible(False)
        root.addWidget(self._toggle_section)

        # ── Destinations ──────────────────────────────────────────────────────
        if self._destinations:
            divider2 = QFrame()
            divider2.setObjectName("divider")
            root.addWidget(divider2)

            root.addWidget(self._section_label("DESTINATIONS"))

            dest_hint = QLabel(
                "Leave all unchecked to fire to all enabled destinations."
            )
            dest_hint.setObjectName("hintLabel")
            root.addWidget(dest_hint)

            for dest in self._destinations:
                cb = QCheckBox(f"{dest.name}  {dest.host}:{dest.port}")
                self._dest_checkboxes.append((dest.id, cb))
                root.addWidget(cb)

        # ── Enabled toggle ────────────────────────────────────────────────────
        divider3 = QFrame()
        divider3.setObjectName("divider")
        root.addWidget(divider3)

        self._enabled_cb = QCheckBox("Mapping enabled")
        root.addWidget(self._enabled_cb)

        # ── Validation error ──────────────────────────────────────────────────
        self._error_lbl = QLabel("")
        self._error_lbl.setObjectName("errorLabel")
        self._error_lbl.setWordWrap(True)
        self._error_lbl.setVisible(False)
        root.addWidget(self._error_lbl)

        # ── Buttons ───────────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("cancelButton")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        save_btn = QPushButton("Save")
        save_btn.setObjectName("primaryButton")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self._save)
        btn_row.addWidget(save_btn)

        root.addLayout(btn_row)

    def _on_toggle_mode_changed(self, checked: bool) -> None:
        self._toggle_section.setVisible(checked)
        self.adjustSize()

    def _get_checked_destination_ids(self) -> List[str]:
        checked = [did for did, cb in self._dest_checkboxes if cb.isChecked()]
        # If all are checked (or all unchecked), return [] to mean "fire to all"
        if len(checked) == len(self._dest_checkboxes):
            return []
        return checked

    def _rebuild_combo(self) -> None:
        """Repopulate the template combo box from the current templates list."""
        self._template_combo.blockSignals(True)
        self._template_combo.clear()
        for t in self._templates:
            self._template_combo.addItem(t.label, userData=t.id)
        self._template_combo.addItem("Custom command", userData=None)
        self._template_combo.blockSignals(False)

    def _populate(self, mapping: Mapping) -> None:
        self._name_edit.setText(mapping.name)
        self._update_key_display(mapping.key_str)
        {
            "short": self._radio_short,
            "long": self._radio_long,
            "any": self._radio_any,
        }.get(mapping.press_type, self._radio_short).setChecked(True)

        if mapping.template_id:
            idx = self._combo_index_for_id(mapping.template_id)
            if idx >= 0:
                self._template_combo.setCurrentIndex(idx)
                self._apply_template_at(idx)
                # continue to populate remaining fields below
        else:
            self._template_combo.setCurrentIndex(self._combo_index_for_id(None))
            self._osc_addr_edit.setText(mapping.osc_address)
            self._osc_args_edit.setText(mapping.osc_args)
            self._set_template_locked(False)

        self._enabled_cb.setChecked(mapping.enabled)

        # Toggle mode
        self._toggle_cb.setChecked(mapping.toggle_mode)
        self._osc_addr_b_edit.setText(mapping.osc_address_b)
        self._osc_args_b_edit.setText(mapping.osc_args_b)
        self._toggle_section.setVisible(mapping.toggle_mode)

        # Destinations
        for dest_id, cb in self._dest_checkboxes:
            cb.setChecked(dest_id in mapping.destination_ids)

    def _combo_index_for_id(self, template_id: Optional[str]) -> int:
        for i in range(self._template_combo.count()):
            if self._template_combo.itemData(i) == template_id:
                return i
        return self._template_combo.count() - 1  # fallback to "Custom command"

    def _current_template_id(self) -> Optional[str]:
        return self._template_combo.currentData()

    def _on_template_changed(self, index: int) -> None:
        template_id = self._template_combo.itemData(index)
        if template_id is None:
            self._set_template_locked(False)
        else:
            self._apply_template_at(index)

    def _apply_template_at(self, index: int) -> None:
        template_id = self._template_combo.itemData(index)
        template = next((t for t in self._templates if t.id == template_id), None)
        if not template:
            return
        self._osc_addr_edit.setText(template.address)
        self._osc_args_edit.setText(template.args)
        self._set_template_locked(True)

    def _set_template_locked(self, locked: bool) -> None:
        self._osc_addr_edit.setReadOnly(locked)
        self._osc_args_edit.setReadOnly(locked)
        self._osc_addr_edit.setProperty("templateLocked", locked)
        self._osc_args_edit.setProperty("templateLocked", locked)
        self._osc_addr_edit.style().unpolish(self._osc_addr_edit)
        self._osc_addr_edit.style().polish(self._osc_addr_edit)
        self._osc_args_edit.style().unpolish(self._osc_args_edit)
        self._osc_args_edit.style().polish(self._osc_args_edit)
        self._detach_btn.setVisible(locked)
        self._save_tmpl_btn.setVisible(not locked)

    def _detach_template(self) -> None:
        """Switch to custom mode, keeping the current field values."""
        self._template_combo.blockSignals(True)
        self._template_combo.setCurrentIndex(self._combo_index_for_id(None))
        self._template_combo.blockSignals(False)
        self._set_template_locked(False)

    def _save_as_template(self) -> None:
        from .config import Template
        from .template_dialog import TemplateDialog

        addr = self._osc_addr_edit.text().strip()
        args = self._osc_args_edit.text().strip()
        new_tmpl = Template.new()
        new_tmpl.address = addr
        new_tmpl.args = args

        dialog = TemplateDialog(new_tmpl, self._osc, self)
        if dialog.exec():
            created = dialog.get_template()
            self._templates.append(created)
            self._rebuild_combo()
            idx = self._combo_index_for_id(created.id)
            self._template_combo.blockSignals(True)
            self._template_combo.setCurrentIndex(idx)
            self._template_combo.blockSignals(False)
            self._apply_template_at(idx)
            self.template_added.emit(created)

    def _get_press_type(self) -> str:
        if self._radio_long.isChecked():
            return "long"
        if self._radio_any.isChecked():
            return "any"
        return "short"

    def _toggle_listen(self) -> None:
        if self._listening:
            self._set_listening(False)
            self.key_capture_cancelled.emit()
        else:
            self._set_listening(True)
            self.key_capture_requested.emit(self.on_key_captured)

    def _set_listening(self, active: bool) -> None:
        self._listening = active
        if active:
            self._listen_btn.setText("Cancel")
            self._listen_btn.setObjectName("listeningActiveButton")
            self._capture_status_lbl.setText("⬤ Waiting for key…")
        else:
            self._listen_btn.setText("Listen")
            self._listen_btn.setObjectName("listenButton")
            self._capture_status_lbl.setText("")
        self._listen_btn.style().unpolish(self._listen_btn)
        self._listen_btn.style().polish(self._listen_btn)

    def _update_key_display(self, key_str: str) -> None:
        self._key_display_lbl.setText(key_display(key_str))

    def _save(self) -> None:
        if self._listening:
            self._set_listening(False)
            self.key_capture_cancelled.emit()

        errors = []
        if not self._mapping.key_str:
            errors.append("A key binding is required — click Listen and press a key.")
        addr = self._osc_addr_edit.text().strip()
        if not addr:
            errors.append("An OSC address is required.")
        elif not addr.startswith("/"):
            errors.append('OSC address must start with "/".')

        if self._toggle_cb.isChecked():
            addr_b = self._osc_addr_b_edit.text().strip()
            if not addr_b:
                errors.append("OSC Command B address is required when toggle mode is enabled.")
            elif not addr_b.startswith("/"):
                errors.append('OSC Command B address must start with "/".')

        if errors:
            self._error_lbl.setText("  •  " + "\n  •  ".join(errors))
            self._error_lbl.setVisible(True)
            return

        self._error_lbl.setVisible(False)
        self.accept()

    def keyPressEvent(self, event) -> None:
        # While listening, block Qt from acting on Escape (closes dialog) and
        # Return/Enter (activates the Save button). pynput captures these via
        # its global X11/Quartz listener independently of Qt's event handling.
        if self._listening and event.key() in (
            Qt.Key.Key_Escape,
            Qt.Key.Key_Return,
            Qt.Key.Key_Enter,
        ):
            event.ignore()
            return
        super().keyPressEvent(event)

    def reject(self) -> None:
        if self._listening:
            self._set_listening(False)
            self.key_capture_cancelled.emit()
        super().reject()

    @staticmethod
    def _section_label(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("dialogSectionLabel")
        return lbl

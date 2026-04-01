"""Dialog for creating or editing an OSC destination."""

import re

from PySide6.QtGui import QIntValidator

# Allows IPv4, IPv6 (with brackets), and hostnames. Rejects control characters,
# whitespace, and shell-special characters that have no place in a host field.
_VALID_HOST_RE = re.compile(r'^[A-Za-z0-9._:\[\]-]+$')
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from .config import OSCDestination
from .osc_sender import OSCSender


class DestinationDialog(QDialog):
    def __init__(self, destination: OSCDestination, parent=None) -> None:
        super().__init__(parent)
        self._destination = destination
        self.setWindowTitle("Edit Destination" if destination.name else "New Destination")
        self.setModal(True)
        self.setMinimumWidth(380)
        self._build_ui()
        self._populate(destination)

    def get_destination(self) -> OSCDestination:
        d = self._destination.copy()
        d.name = self._name_edit.text().strip() or "Unnamed"
        host = self._host_edit.text().strip()
        d.host = host if host and _VALID_HOST_RE.match(host) else "127.0.0.1"
        try:
            d.port = int(self._port_edit.text())
        except ValueError:
            d.port = 3333
        d.enabled = self._enabled_cb.isChecked()
        return d

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 20)
        root.setSpacing(14)

        root.addWidget(self._section_label("NAME"))
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("e.g. Main Mixer")
        root.addWidget(self._name_edit)

        root.addWidget(self._section_label("HOST"))
        self._host_edit = QLineEdit()
        self._host_edit.setPlaceholderText("192.168.1.100")
        root.addWidget(self._host_edit)

        root.addWidget(self._section_label("PORT"))
        self._port_edit = QLineEdit()
        self._port_edit.setPlaceholderText("3333")
        self._port_edit.setValidator(QIntValidator(1, 65535))
        root.addWidget(self._port_edit)

        self._enabled_cb = QCheckBox("Destination enabled")
        root.addWidget(self._enabled_cb)

        test_btn = QPushButton("Send Test Message  (/dispatch/test 1)")
        test_btn.setObjectName("testOutlineButton")
        test_btn.clicked.connect(self._send_test)
        root.addWidget(test_btn)

        self._status_lbl = QLabel("")
        self._status_lbl.setObjectName("hintLabel")
        root.addWidget(self._status_lbl)

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

    def _populate(self, destination: OSCDestination) -> None:
        self._name_edit.setText(destination.name)
        self._host_edit.setText(destination.host)
        self._port_edit.setText(str(destination.port))
        self._enabled_cb.setChecked(destination.enabled)

    def _send_test(self) -> None:
        raw = self._host_edit.text().strip()
        host = raw if raw and _VALID_HOST_RE.match(raw) else "127.0.0.1"
        try:
            port = int(self._port_edit.text())
        except ValueError:
            port = 3333
        sender = OSCSender(host, port)
        ok, err = sender.send("/dispatch/test", "1")
        if ok:
            self._status_lbl.setText(f"✓ Sent to {host}:{port}")
        else:
            self._status_lbl.setText(f"✗ {err}")

    def _save(self) -> None:
        errors = []
        if not self._name_edit.text().strip():
            errors.append("Name is required.")
        host = self._host_edit.text().strip()
        if not host:
            errors.append("Host is required.")
        elif not _VALID_HOST_RE.match(host):
            errors.append("Host contains invalid characters.")
        if not self._port_edit.text().strip():
            errors.append("Port is required.")
        if errors:
            self._status_lbl.setObjectName("errorLabel")
            self._status_lbl.setText("  •  " + "\n  •  ".join(errors))
            self._status_lbl.style().unpolish(self._status_lbl)
            self._status_lbl.style().polish(self._status_lbl)
            return
        self.accept()

    @staticmethod
    def _section_label(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("dialogSectionLabel")
        return lbl

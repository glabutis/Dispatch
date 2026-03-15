"""Main application window."""

import json
import sys
import uuid
from datetime import datetime
from typing import Callable, Dict, List, Optional

from PySide6.QtCore import QObject, QTimer, Qt, Signal, Slot
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSystemTrayIcon,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .config import AppConfig, Mapping, OSCDestination, Profile, Template
from .destination_dialog import DestinationDialog
from .input_listener import InputListener
from .mapping_dialog import MappingDialog
from .mapping_row import MappingRow
from .osc_sender import OSCSender
from .profile_io import export_profile, import_profile
from .settings_dialog import SettingsDialog
from .templates_tab import TemplatesTab
from .theme import get_stylesheet


class _ListenerBridge(QObject):
    """
    Bridges pynput's background thread to Qt signals.

    pynput fires callbacks from its own thread; Qt signals posted from
    non-GUI threads are safely queued to the main thread.
    """
    action_received = Signal(str, str)   # key_str, press_type
    key_captured = Signal(str)           # key_str


class MainWindow(QMainWindow):
    def __init__(self, config: AppConfig) -> None:
        super().__init__()
        self.config = config
        self._rows: dict[str, MappingRow] = {}
        self._pending_captures: list[Callable[[str], None]] = []
        self._active = True  # master OSC enable flag
        self._banner_timer = QTimer(self)
        self._banner_timer.setSingleShot(True)
        self._banner_timer.timeout.connect(self._hide_banner)

        # Toggle state — aliased to config.toggle_states so saves are automatic
        self._toggle_states = config.toggle_states

        # One OSCSender per destination id
        self._osc_senders: dict[str, OSCSender] = {}
        for d in config.destinations:
            self._osc_senders[d.id] = OSCSender(d.host, d.port)

        # Keyboard listener
        self._listener = InputListener()
        self._listener.set_threshold(config.settings.long_press_threshold_ms)

        # Bridge (lives in the main thread; signals are queued automatically)
        self._bridge = _ListenerBridge()
        self._bridge.action_received.connect(self._on_action)
        self._bridge.key_captured.connect(self._on_key_captured)
        self._listener.set_action_callback(self._listener_action_cb)

        self._build_ui()
        self._start_listener()
        self._setup_tray()

    # ── Primary sender (first enabled destination) ────────────────────────────

    @property
    def _primary_sender(self) -> Optional[OSCSender]:
        for d in self.config.destinations:
            if d.enabled and d.id in self._osc_senders:
                return self._osc_senders[d.id]
        return None

    # ── Keyboard capture API (called by MappingDialog via signal) ─────────────

    def request_key_capture(self, callback: Callable[[str], None]) -> None:
        self._pending_captures.append(callback)
        self._listener.capture_next_key(
            lambda ks: self._bridge.key_captured.emit(ks)
        )

    def cancel_key_capture(self) -> None:
        self._listener.cancel_capture()
        self._pending_captures.clear()

    # ── Private: listener callbacks ──────────────────────────────────────────

    def _listener_action_cb(self, key_str: str, press_type: str) -> None:
        """Called from pynput thread — emit signal to cross into main thread."""
        self._bridge.action_received.emit(key_str, press_type)

    @Slot(str, str)
    def _on_action(self, key_str: str, press_type: str) -> None:
        """Runs in main thread. Looks up matching mappings and fires OSC."""
        if not self._active:
            return
        for mapping in self.config.active_profile.mappings:
            if not mapping.enabled:
                continue
            if mapping.key_str != key_str:
                continue
            if mapping.press_type not in (press_type, "any"):
                continue
            if mapping.toggle_mode:
                state = self._toggle_states.get(mapping.id, False)
                if state:
                    address, args = mapping.osc_address_b, mapping.osc_args_b
                else:
                    address, args = mapping.osc_address, mapping.osc_args
                self._toggle_states[mapping.id] = not state
                self.config.save()
            else:
                address, args = mapping.osc_address, mapping.osc_args
            self._fire_osc(mapping, address, args)

    def _fire_osc(self, mapping: Mapping, address: str, args: str) -> None:
        """Send OSC to the appropriate destinations for this mapping."""
        if mapping.destination_ids:
            senders = [
                (did, self._osc_senders[did])
                for did in mapping.destination_ids
                if did in self._osc_senders
            ]
        else:
            senders = [
                (d.id, self._osc_senders[d.id])
                for d in self.config.destinations
                if d.enabled and d.id in self._osc_senders
            ]
        for _did, sender in senders:
            ok, err = sender.send(address, args)
            self._append_log(ok, address, args)
            if ok:
                self._set_status(f"✓ [{mapping.name}]  {address}", "success")
            else:
                self._set_status(f"✗ [{mapping.name}]  {err}", "error")

    @Slot(str)
    def _on_key_captured(self, key_str: str) -> None:
        """Runs in main thread. Delivers captured key to the waiting dialog."""
        if self._pending_captures:
            cb = self._pending_captures.pop(0)
            cb(key_str)

    # ── UI construction ──────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        self.setWindowTitle("Dispatch")
        self.setMinimumSize(720, 520)
        self.resize(900, 660)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self._make_header())
        layout.addWidget(self._make_profile_bar())
        layout.addWidget(self._make_destinations_section())
        layout.addWidget(self._make_notification_banner())
        layout.addWidget(self._make_tabs(), 1)
        self._log_panel = self._make_log_panel()
        layout.addWidget(self._log_panel)
        layout.addWidget(self._make_status_bar())

    # ── Header ────────────────────────────────────────────────────────────────

    def _make_header(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("headerFrame")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(20, 12, 20, 12)
        layout.setSpacing(10)

        icon = QLabel("◎")
        icon.setObjectName("headerIcon")
        layout.addWidget(icon)

        title = QLabel("Dispatch")
        title.setObjectName("headerTitle")
        layout.addWidget(title)

        layout.addStretch()

        self._pause_btn = QPushButton("⏸  Pause")
        self._pause_btn.setObjectName("headerButton")
        self._pause_btn.setToolTip("Pause all OSC output without stopping the listener")
        self._pause_btn.clicked.connect(self._toggle_active)
        layout.addWidget(self._pause_btn)

        self._log_btn = QPushButton("Log ▾")
        self._log_btn.setObjectName("headerButton")
        self._log_btn.setToolTip("Show / hide OSC message log")
        self._log_btn.clicked.connect(self._toggle_log)
        layout.addWidget(self._log_btn)

        settings_btn = QPushButton("⚙  Settings")
        settings_btn.setObjectName("headerButton")
        settings_btn.clicked.connect(self._open_settings)
        layout.addWidget(settings_btn)

        return frame

    # ── Profile bar ───────────────────────────────────────────────────────────

    def _make_profile_bar(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("profileBarFrame")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(20, 10, 20, 10)
        layout.setSpacing(8)

        profile_lbl = QLabel("PROFILE")
        profile_lbl.setObjectName("sectionLabel")
        layout.addWidget(profile_lbl)

        self._profile_combo = QComboBox()
        self._profile_combo.setObjectName("profileCombo")
        self._profile_combo.setMinimumWidth(160)
        self._rebuild_profile_combo()
        self._profile_combo.currentIndexChanged.connect(self._on_profile_changed)
        layout.addWidget(self._profile_combo)

        add_profile_btn = QPushButton("+")
        add_profile_btn.setObjectName("iconButton")
        add_profile_btn.setFixedSize(28, 28)
        add_profile_btn.setToolTip("Add new profile")
        add_profile_btn.clicked.connect(self._add_profile)
        layout.addWidget(add_profile_btn)

        edit_profile_btn = QPushButton("✎")
        edit_profile_btn.setObjectName("iconButton")
        edit_profile_btn.setFixedSize(28, 28)
        edit_profile_btn.setToolTip("Rename or delete current profile")
        edit_profile_btn.clicked.connect(self._edit_profile)
        layout.addWidget(edit_profile_btn)

        layout.addStretch()

        export_btn = QPushButton("Export…")
        export_btn.setObjectName("rowButton")
        export_btn.setToolTip("Export current profile to a JSON file")
        export_btn.clicked.connect(self._export_profile)
        layout.addWidget(export_btn)

        import_btn = QPushButton("Import…")
        import_btn.setObjectName("rowButton")
        import_btn.setToolTip("Import a profile from a JSON file")
        import_btn.clicked.connect(self._import_profile)
        layout.addWidget(import_btn)

        return frame

    def _rebuild_profile_combo(self) -> None:
        self._profile_combo.blockSignals(True)
        self._profile_combo.clear()
        for p in self.config.profiles:
            self._profile_combo.addItem(p.name, userData=p.id)
        # Select the active profile
        active_id = self.config.active_profile_id
        for i in range(self._profile_combo.count()):
            if self._profile_combo.itemData(i) == active_id:
                self._profile_combo.setCurrentIndex(i)
                break
        self._profile_combo.blockSignals(False)

    def _on_profile_changed(self, index: int) -> None:
        profile_id = self._profile_combo.itemData(index)
        if not profile_id or profile_id == self.config.active_profile_id:
            return
        self.config.active_profile_id = profile_id
        self._toggle_states.clear()
        self._reload_mappings()
        self.config.save()

    def _add_profile(self) -> None:
        name, ok = QInputDialog.getText(self, "New Profile", "Profile name:")
        if not ok or not name.strip():
            return
        profile = Profile.new(name.strip())
        self.config.profiles.append(profile)
        self.config.active_profile_id = profile.id
        self._rebuild_profile_combo()
        self._toggle_states.clear()
        self._reload_mappings()
        self.config.save()

    def _edit_profile(self) -> None:
        profile = self.config.active_profile
        options = ["Rename", "Delete"]
        action, ok = QInputDialog.getItem(
            self, "Edit Profile", f'Profile: "{profile.name}"', options, 0, False
        )
        if not ok:
            return
        if action == "Rename":
            name, ok2 = QInputDialog.getText(
                self, "Rename Profile", "New name:", text=profile.name
            )
            if ok2 and name.strip():
                profile.name = name.strip()
                self._rebuild_profile_combo()
                self.config.save()
        elif action == "Delete":
            if len(self.config.profiles) <= 1:
                QMessageBox.warning(
                    self,
                    "Cannot Delete",
                    "You must have at least one profile.",
                )
                return
            count = len(profile.mappings)
            noun = "mapping" if count == 1 else "mappings"
            msg = f'Delete profile "{profile.name}"?'
            if count:
                msg += f"\n\nThis will also delete {count} {noun}."
            reply = QMessageBox.question(
                self, "Delete Profile", msg, QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return
            self.config.profiles = [p for p in self.config.profiles if p.id != profile.id]
            self.config.active_profile_id = self.config.profiles[0].id
            self._rebuild_profile_combo()
            self._toggle_states.clear()
            self._reload_mappings()
            self.config.save()

    def _reload_mappings(self) -> None:
        """Remove all row widgets and repopulate from the active profile."""
        for row in list(self._rows.values()):
            self._rows_layout.removeWidget(row)
            row.deleteLater()
        self._rows.clear()
        for m in self.config.active_profile.mappings:
            self._insert_row(m)

    # ── Destinations section ──────────────────────────────────────────────────

    def _make_destinations_section(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("sectionFrame")
        outer = QVBoxLayout(frame)
        outer.setContentsMargins(20, 14, 20, 14)
        outer.setSpacing(8)

        # Header row
        header_row = QHBoxLayout()
        section_lbl = QLabel("OSC DESTINATIONS")
        section_lbl.setObjectName("sectionLabel")
        header_row.addWidget(section_lbl)
        header_row.addStretch()
        add_dest_btn = QPushButton("+ Add")
        add_dest_btn.setObjectName("rowButton")
        add_dest_btn.setToolTip("Add a new OSC destination")
        add_dest_btn.clicked.connect(self._add_destination)
        header_row.addWidget(add_dest_btn)
        outer.addLayout(header_row)

        # Container for destination rows
        self._dest_rows_widget = QWidget()
        self._dest_rows_layout = QVBoxLayout(self._dest_rows_widget)
        self._dest_rows_layout.setContentsMargins(0, 0, 0, 0)
        self._dest_rows_layout.setSpacing(4)
        outer.addWidget(self._dest_rows_widget)

        self._dest_row_widgets: dict[str, QFrame] = {}
        for d in self.config.destinations:
            self._insert_dest_row(d)

        return frame

    def _insert_dest_row(self, dest: OSCDestination) -> None:
        row = QFrame()
        row.setObjectName("destinationRow")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(10)

        # Enabled dot
        dot = QPushButton("●")
        dot.setObjectName("enabledDot")
        dot.setFixedSize(22, 22)
        dot.setCheckable(True)
        dot.setChecked(dest.enabled)
        dot.setProperty("enabled_state", "on" if dest.enabled else "off")
        dot.style().unpolish(dot)
        dot.style().polish(dot)
        dot.clicked.connect(lambda checked, did=dest.id: self._toggle_destination(did, checked))
        layout.addWidget(dot)

        name_lbl = QLabel(dest.name)
        name_lbl.setObjectName("destinationName")
        name_lbl.setMinimumWidth(100)
        layout.addWidget(name_lbl)

        addr_lbl = QLabel(f"{dest.host}:{dest.port}")
        addr_lbl.setObjectName("destinationAddr")
        layout.addWidget(addr_lbl, 1)

        edit_btn = QPushButton("Edit")
        edit_btn.setObjectName("rowButton")
        edit_btn.setFixedWidth(48)
        edit_btn.clicked.connect(lambda _, did=dest.id: self._edit_destination(did))
        layout.addWidget(edit_btn)

        del_btn = QPushButton("✕")
        del_btn.setObjectName("deleteButton")
        del_btn.setFixedSize(28, 28)
        del_btn.setToolTip("Delete destination")
        del_btn.clicked.connect(lambda _, did=dest.id: self._delete_destination(did))
        layout.addWidget(del_btn)

        self._dest_rows_layout.addWidget(row)
        self._dest_row_widgets[dest.id] = row

    def _rebuild_dest_rows(self) -> None:
        for w in list(self._dest_row_widgets.values()):
            self._dest_rows_layout.removeWidget(w)
            w.deleteLater()
        self._dest_row_widgets.clear()
        for d in self.config.destinations:
            self._insert_dest_row(d)

    def _add_destination(self) -> None:
        dest = OSCDestination.new()
        dialog = DestinationDialog(dest, self)
        if dialog.exec():
            new_dest = dialog.get_destination()
            self.config.destinations.append(new_dest)
            self._osc_senders[new_dest.id] = OSCSender(new_dest.host, new_dest.port)
            self._insert_dest_row(new_dest)
            self._update_templates_osc()
            self.config.save()

    def _edit_destination(self, dest_id: str) -> None:
        dest = next((d for d in self.config.destinations if d.id == dest_id), None)
        if not dest:
            return
        dialog = DestinationDialog(dest.copy(), self)
        if dialog.exec():
            updated = dialog.get_destination()
            for i, d in enumerate(self.config.destinations):
                if d.id == dest_id:
                    self.config.destinations[i] = updated
                    break
            if dest_id in self._osc_senders:
                self._osc_senders[dest_id].update(updated.host, updated.port)
            else:
                self._osc_senders[dest_id] = OSCSender(updated.host, updated.port)
            self._rebuild_dest_rows()
            self._update_templates_osc()
            self.config.save()

    def _delete_destination(self, dest_id: str) -> None:
        dest = next((d for d in self.config.destinations if d.id == dest_id), None)
        if not dest:
            return

        # Find mappings across all profiles that reference this destination
        affected_mappings = [
            m
            for p in self.config.profiles
            for m in p.mappings
            if dest_id in m.destination_ids
        ]

        msg = f'Delete destination "{dest.name}" ({dest.host}:{dest.port})?'
        if affected_mappings:
            noun = "mapping" if len(affected_mappings) == 1 else "mappings"
            msg += (
                f"\n\n{len(affected_mappings)} {noun} target this destination specifically. "
                "They will revert to firing to all enabled destinations."
            )

        reply = QMessageBox.question(
            self, "Delete Destination", msg, QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        # Clear refs in all profiles
        for m in affected_mappings:
            m.destination_ids = [did for did in m.destination_ids if did != dest_id]

        self.config.destinations = [d for d in self.config.destinations if d.id != dest_id]
        if dest_id in self._osc_senders:
            del self._osc_senders[dest_id]

        if dest_id in self._dest_row_widgets:
            w = self._dest_row_widgets.pop(dest_id)
            self._dest_rows_layout.removeWidget(w)
            w.deleteLater()

        self._update_templates_osc()
        self.config.save()

    def _toggle_destination(self, dest_id: str, enabled: bool) -> None:
        for d in self.config.destinations:
            if d.id == dest_id:
                d.enabled = enabled
                break
        self._update_templates_osc()
        self.config.save()

    def _update_templates_osc(self) -> None:
        """Update the OSCSender reference in the templates tab."""
        if hasattr(self, "_templates_tab"):
            self._templates_tab.update_osc(self._primary_sender)

    # ── Notification banner ───────────────────────────────────────────────────

    def _make_notification_banner(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("notificationBanner")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(20, 8, 20, 8)

        self._banner_lbl = QLabel("")
        self._banner_lbl.setObjectName("notificationBannerText")
        self._banner_lbl.setWordWrap(True)
        layout.addWidget(self._banner_lbl, 1)

        close_btn = QPushButton("✕")
        close_btn.setObjectName("deleteButton")
        close_btn.setFixedSize(20, 20)
        close_btn.clicked.connect(self._hide_banner)
        layout.addWidget(close_btn)

        frame.setVisible(False)
        self._banner_frame = frame
        return frame

    def _show_banner(self, message: str) -> None:
        self._banner_lbl.setText(message)
        self._banner_frame.setVisible(True)
        self._banner_timer.start(5000)

    def _hide_banner(self) -> None:
        self._banner_frame.setVisible(False)
        self._banner_timer.stop()

    # ── Tabs ──────────────────────────────────────────────────────────────────

    def _make_tabs(self) -> QTabWidget:
        self._tabs = QTabWidget()
        self._tabs.setObjectName("mainTabs")
        self._tabs.addTab(self._make_mappings_section(), "Mappings")

        self._templates_tab = TemplatesTab(self.config, self._primary_sender, self)
        self._templates_tab.template_updated.connect(self._on_template_updated)
        self._templates_tab.template_deleted.connect(self._on_template_deleted)
        self._tabs.addTab(self._templates_tab, "Templates")

        return self._tabs

    # ── Mappings section ──────────────────────────────────────────────────────

    def _make_mappings_section(self) -> QWidget:
        outer = QWidget()
        outer.setObjectName("mappingsSectionOuter")
        layout = QVBoxLayout(outer)
        layout.setContentsMargins(20, 14, 20, 10)
        layout.setSpacing(8)

        # Header row
        header_row = QHBoxLayout()
        section_lbl = QLabel("KEY MAPPINGS")
        section_lbl.setObjectName("sectionLabel")
        header_row.addWidget(section_lbl)
        header_row.addStretch()
        add_btn = QPushButton("+ Add Mapping")
        add_btn.setObjectName("addButton")
        add_btn.clicked.connect(self._add_mapping)
        header_row.addWidget(add_btn)
        layout.addLayout(header_row)

        # Column headers
        col_frame = QFrame()
        col_frame.setObjectName("colHeader")
        col_layout = QHBoxLayout(col_frame)
        col_layout.setContentsMargins(46, 2, 12, 2)
        col_layout.setSpacing(12)
        for text, min_w, stretch in [
            ("Name", 130, 0),
            ("Key", 90, 0),
            ("Type", 52, 0),
            ("OSC Address", 0, 1),
            ("", 28 + 12 + 56 + 12 + 56 + 28, 0),
        ]:
            lbl = QLabel(text)
            lbl.setObjectName("colHeaderLabel")
            if min_w:
                lbl.setMinimumWidth(min_w)
                lbl.setMaximumWidth(min_w)
            if stretch:
                col_layout.addWidget(lbl, stretch)
            else:
                col_layout.addWidget(lbl)
        layout.addWidget(col_frame)

        # Scrollable list
        scroll = QScrollArea()
        scroll.setObjectName("mappingsScroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.NoFrame)

        self._rows_container = QWidget()
        self._rows_container.setObjectName("mappingsContainer")
        self._rows_layout = QVBoxLayout(self._rows_container)
        self._rows_layout.setContentsMargins(0, 0, 0, 0)
        self._rows_layout.setSpacing(4)
        self._rows_layout.addStretch()

        scroll.setWidget(self._rows_container)
        layout.addWidget(scroll, 1)

        # Populate with active profile's mappings
        for m in self.config.active_profile.mappings:
            self._insert_row(m)

        return outer

    # ── OSC Log panel ─────────────────────────────────────────────────────────

    def _make_log_panel(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("logPanelFrame")
        frame.setFixedHeight(150)
        frame.setVisible(False)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 8, 20, 8)
        layout.setSpacing(0)

        self._log_edit = QPlainTextEdit()
        self._log_edit.setObjectName("oscLogEdit")
        self._log_edit.setReadOnly(True)
        self._log_edit.setMaximumBlockCount(200)
        self._log_edit.setPlaceholderText("OSC messages will appear here…")
        layout.addWidget(self._log_edit)

        return frame

    # ── Status bar ────────────────────────────────────────────────────────────

    def _make_status_bar(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("statusBarFrame")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(20, 8, 20, 8)
        layout.setSpacing(8)

        self._listener_dot = QLabel("●")
        self._listener_dot.setObjectName("listenerDotActive")
        layout.addWidget(self._listener_dot)

        self._listener_lbl = QLabel("Listening for input")
        self._listener_lbl.setObjectName("listenerStatus")
        layout.addWidget(self._listener_lbl)

        layout.addStretch()

        self._last_action_lbl = QLabel("")
        self._last_action_lbl.setObjectName("lastAction")
        layout.addWidget(self._last_action_lbl)

        return frame

    # ── Mapping CRUD ──────────────────────────────────────────────────────────

    def _insert_row(self, mapping: Mapping) -> None:
        row = MappingRow(mapping)
        row.edit_requested.connect(self._edit_mapping)
        row.delete_requested.connect(self._delete_mapping)
        row.toggle_requested.connect(self._toggle_mapping)
        row.duplicate_requested.connect(self._duplicate_mapping)
        row.test_requested.connect(self._test_mapping)
        insert_at = self._rows_layout.count() - 1
        self._rows_layout.insertWidget(insert_at, row)
        self._rows[mapping.id] = row

    def _open_mapping_dialog(self, mapping: Mapping) -> MappingDialog:
        osc = self._primary_sender or OSCSender()
        dialog = MappingDialog(mapping, self.config.templates, osc, self.config.destinations, self)
        dialog.key_capture_requested.connect(self.request_key_capture)
        dialog.key_capture_cancelled.connect(self.cancel_key_capture)
        dialog.template_added.connect(self._on_template_added_from_dialog)
        return dialog

    def _add_mapping(self) -> None:
        mapping = Mapping.new()
        dialog = self._open_mapping_dialog(mapping)
        if dialog.exec():
            updated = dialog.get_mapping()
            self.config.active_profile.mappings.append(updated)
            self._insert_row(updated)
            self.config.save()

    def _edit_mapping(self, mapping_id: str) -> None:
        mappings = self.config.active_profile.mappings
        mapping = next((m for m in mappings if m.id == mapping_id), None)
        if not mapping:
            return
        dialog = self._open_mapping_dialog(mapping.copy())
        if dialog.exec():
            updated = dialog.get_mapping()
            for i, m in enumerate(mappings):
                if m.id == mapping_id:
                    mappings[i] = updated
                    break
            if mapping_id in self._rows:
                self._rows[mapping_id].update_mapping(updated)
            self.config.save()

    def _delete_mapping(self, mapping_id: str) -> None:
        reply = QMessageBox.question(
            self,
            "Delete Mapping",
            "Delete this mapping?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        profile = self.config.active_profile
        profile.mappings = [m for m in profile.mappings if m.id != mapping_id]
        self._toggle_states.pop(mapping_id, None)
        if mapping_id in self._rows:
            row = self._rows.pop(mapping_id)
            self._rows_layout.removeWidget(row)
            row.deleteLater()
        self.config.save()

    def _toggle_mapping(self, mapping_id: str, enabled: bool) -> None:
        for m in self.config.active_profile.mappings:
            if m.id == mapping_id:
                m.enabled = enabled
                break
        self.config.save()

    def _duplicate_mapping(self, mapping_id: str) -> None:
        mappings = self.config.active_profile.mappings
        mapping = next((m for m in mappings if m.id == mapping_id), None)
        if not mapping:
            return
        dup = mapping.copy()
        dup.id = str(uuid.uuid4())
        dup.name = f"Copy of {mapping.name}"

        orig_idx = next(i for i, m in enumerate(mappings) if m.id == mapping_id)
        mappings.insert(orig_idx + 1, dup)

        row = MappingRow(dup)
        row.edit_requested.connect(self._edit_mapping)
        row.delete_requested.connect(self._delete_mapping)
        row.toggle_requested.connect(self._toggle_mapping)
        row.duplicate_requested.connect(self._duplicate_mapping)
        row.test_requested.connect(self._test_mapping)
        orig_row = self._rows.get(mapping_id)
        if orig_row:
            insert_at = self._rows_layout.indexOf(orig_row) + 1
        else:
            insert_at = self._rows_layout.count() - 1
        self._rows_layout.insertWidget(insert_at, row)
        self._rows[dup.id] = row
        self.config.save()

    def _test_mapping(self, mapping_id: str) -> None:
        mapping = next(
            (m for m in self.config.active_profile.mappings if m.id == mapping_id), None
        )
        if not mapping:
            return
        # Always fire address A; never advance toggle state
        self._fire_osc(mapping, mapping.osc_address, mapping.osc_args)
        self._set_status(f"✓ Test [{mapping.name}]  {mapping.osc_address}", "success")

    # ── Template propagation ──────────────────────────────────────────────────

    def _on_template_added_from_dialog(self, template: Template) -> None:
        self._templates_tab.add_template(template)
        self.config.save()

    def _on_template_updated(self, template_id: str) -> None:
        template = next((t for t in self.config.templates if t.id == template_id), None)
        if not template:
            return
        total_affected = 0
        for profile in self.config.profiles:
            affected = [m for m in profile.mappings if m.template_id == template_id]
            for m in affected:
                m.osc_address = template.address
                m.osc_args = template.args
            total_affected += len(affected)
            if profile.id == self.config.active_profile_id:
                for m in affected:
                    if m.id in self._rows:
                        self._rows[m.id].update_mapping(m)
        self.config.save()
        if total_affected:
            noun = "mapping" if total_affected == 1 else "mappings"
            self._show_banner(
                f'Template "{template.label}" updated — {total_affected} {noun} updated.'
            )

    def _on_template_deleted(self, template_id: str, label: str) -> None:
        total_affected = 0
        for profile in self.config.profiles:
            affected = [m for m in profile.mappings if m.template_id == template_id]
            for m in affected:
                m.template_id = None
            total_affected += len(affected)
        self.config.save()
        if total_affected:
            noun = "mapping" if total_affected == 1 else "mappings"
            self._show_banner(
                f'Template "{label}" deleted — {total_affected} {noun} reverted to custom commands.'
            )

    # ── Export / Import ───────────────────────────────────────────────────────

    def _export_profile(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Profile",
            f"{self.config.active_profile.name}.json",
            "JSON Files (*.json)",
        )
        if not path:
            return
        try:
            data = export_profile(self.config.active_profile, self.config.templates)
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
            self._show_banner(f"Profile exported to {path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", str(e))

    def _import_profile(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Profile", "", "JSON Files (*.json)"
        )
        if not path:
            return
        try:
            with open(path) as f:
                data = json.load(f)
            profile, new_templates = import_profile(data, self.config.templates)
        except Exception as e:
            QMessageBox.critical(self, "Import Failed", str(e))
            return

        self.config.profiles.append(profile)
        for t in new_templates:
            self.config.templates.append(t)
            self._templates_tab.add_template(t)

        self.config.active_profile_id = profile.id
        self._rebuild_profile_combo()
        self._toggle_states.clear()
        self._reload_mappings()
        self.config.save()
        self._show_banner(
            f'Profile "{profile.name}" imported'
            + (f" with {len(new_templates)} new template(s)." if new_templates else ".")
        )

    # ── Master toggle ─────────────────────────────────────────────────────────

    def _toggle_active(self) -> None:
        self._active = not self._active
        if self._active:
            self._pause_btn.setText("⏸  Pause")
            self._pause_btn.setObjectName("headerButton")
        else:
            self._pause_btn.setText("▶  Resume")
            self._pause_btn.setObjectName("pausedButton")
        self._pause_btn.style().unpolish(self._pause_btn)
        self._pause_btn.style().polish(self._pause_btn)

    # ── OSC Log ───────────────────────────────────────────────────────────────

    def _toggle_log(self) -> None:
        visible = not self._log_panel.isVisible()
        self._log_panel.setVisible(visible)
        self._log_btn.setText("Log ▴" if visible else "Log ▾")

    def _append_log(self, ok: bool, address: str, args_str: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        symbol = "✓" if ok else "✗"
        line = f"{ts}  {symbol}  {address}"
        if args_str.strip():
            line += f"  {args_str.strip()}"
        self._log_edit.appendPlainText(line)

    # ── System tray ───────────────────────────────────────────────────────────

    def _setup_tray(self) -> None:
        self._tray = QSystemTrayIcon(self)
        self._tray.setIcon(QApplication.instance().windowIcon())
        self._tray.setToolTip("Dispatch")

        menu = QMenu(self)
        show_action = QAction("Show / Hide", self)
        show_action.triggered.connect(self._toggle_visibility)
        menu.addAction(show_action)
        menu.addSeparator()
        quit_action = QAction("Quit Dispatch", self)
        quit_action.triggered.connect(self._quit_app)
        menu.addAction(quit_action)

        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._on_tray_activated)
        self._tray.show()

    def _toggle_visibility(self) -> None:
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.raise_()
            self.activateWindow()

    def _on_tray_activated(self, reason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._toggle_visibility()

    def _quit_app(self) -> None:
        self._tray.hide()
        self._listener.stop()
        self.config.save()
        QApplication.quit()

    # ── Settings ──────────────────────────────────────────────────────────────

    def _open_settings(self) -> None:
        dialog = SettingsDialog(self.config.settings, self)
        if dialog.exec():
            updated = dialog.get_settings()
            theme_changed = updated.theme != self.config.settings.theme
            self.config.settings = updated
            self._listener.set_threshold(updated.long_press_threshold_ms)
            self.config.save()
            if theme_changed:
                QApplication.instance().setStyleSheet(get_stylesheet(updated.theme))

    # ── Listener start ────────────────────────────────────────────────────────

    def _start_listener(self) -> None:
        try:
            self._listener.start()
        except Exception as exc:
            self._listener_dot.setObjectName("listenerDotInactive")
            self._listener_lbl.setText(f"Listener error: {exc}")
            if sys.platform == "darwin":
                QMessageBox.warning(
                    self,
                    "Accessibility Permission Required",
                    "Dispatch needs Accessibility access to capture global key events.\n\n"
                    "Open System Settings → Privacy & Security → Accessibility\n"
                    "and enable Dispatch.",
                )

    # ── Status helper ─────────────────────────────────────────────────────────

    def _set_status(self, message: str, level: str = "normal") -> None:
        colors = {
            "success": "#a6e3a1",
            "error": "#f38ba8",
            "normal": "#a6adc8",
        }
        color = colors.get(level, colors["normal"])
        self._last_action_lbl.setText(message)
        self._last_action_lbl.setStyleSheet(f"color: {color};")
        QTimer.singleShot(4000, lambda: self._last_action_lbl.setText(""))

    # ── Window lifecycle ──────────────────────────────────────────────────────

    def closeEvent(self, event) -> None:
        if QSystemTrayIcon.isSystemTrayAvailable() and self._tray.isVisible():
            self.hide()
            event.ignore()
            return
        self._listener.stop()
        self.config.save()
        super().closeEvent(event)

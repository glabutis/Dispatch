"""
macOS CGEventTap-based keyboard listener.

Uses kCGEventTapOptionDefault so the callback runs *before* the OS dispatches
the event.  When a key matches an active Dispatch mapping the callback returns
None (consuming the event); everything else is returned unchanged so Spotlight,
Mission Control, and other system shortcuts keep working normally.

Threading model mirrors InputListener: all callbacks fire from the run-loop
thread; callers (MainWindow) marshal to the Qt main thread via Qt signals.
"""

import sys
import threading
import time
from typing import Callable, Optional, Set

assert sys.platform == "darwin", "CGEventListener is macOS-only"

import ctypes
import ctypes.util

# ---------------------------------------------------------------------------
# Low-level CoreGraphics bindings via ctypes
# (pyobjc wraps CGEventTapCreate but its callback bridging is unreliable;
#  we wire the tap through ctypes for a predictable ABI.)
# ---------------------------------------------------------------------------

_cg_path = (
    ctypes.util.find_library("CoreGraphics")
    or "/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics"
)
_cf_path = (
    ctypes.util.find_library("CoreFoundation")
    or "/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation"
)

_CG = ctypes.cdll.LoadLibrary(_cg_path)
_CF = ctypes.cdll.LoadLibrary(_cf_path)

# CGEventTapCreate
_TAP_CALLBACK = ctypes.CFUNCTYPE(
    ctypes.c_void_p,   # return: CGEventRef (or NULL to consume)
    ctypes.c_void_p,   # proxy
    ctypes.c_uint32,   # type
    ctypes.c_void_p,   # event
    ctypes.c_void_p,   # userInfo
)

_CG.CGEventTapCreate.restype = ctypes.c_void_p
_CG.CGEventTapCreate.argtypes = [
    ctypes.c_uint32,   # tap location
    ctypes.c_uint32,   # place
    ctypes.c_uint32,   # options
    ctypes.c_uint64,   # eventsOfInterest (mask)
    _TAP_CALLBACK,
    ctypes.c_void_p,   # userInfo
]

_CG.CGEventTapEnable.restype = None
_CG.CGEventTapEnable.argtypes = [ctypes.c_void_p, ctypes.c_bool]

_CG.CGEventGetIntegerValueField.restype = ctypes.c_int64
_CG.CGEventGetIntegerValueField.argtypes = [ctypes.c_void_p, ctypes.c_int32]

_CG.CGEventGetFlags.restype = ctypes.c_uint64
_CG.CGEventGetFlags.argtypes = [ctypes.c_void_p]

_CF.CFMachPortCreateRunLoopSource.restype = ctypes.c_void_p
_CF.CFMachPortCreateRunLoopSource.argtypes = [
    ctypes.c_void_p, ctypes.c_void_p, ctypes.c_long
]

_CF.CFRunLoopGetCurrent.restype = ctypes.c_void_p
_CF.CFRunLoopGetCurrent.argtypes = []

_CF.CFRunLoopAddSource.restype = None
_CF.CFRunLoopAddSource.argtypes = [
    ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p
]

_CF.CFRunLoopRun.restype = None
_CF.CFRunLoopRun.argtypes = []

_CF.CFRunLoopStop.restype = None
_CF.CFRunLoopStop.argtypes = [ctypes.c_void_p]

_CF.CFRelease.restype = None
_CF.CFRelease.argtypes = [ctypes.c_void_p]

# kCFRunLoopCommonModes as a CFStringRef
_CF.CFStringCreateWithCString.restype = ctypes.c_void_p
_CF.CFStringCreateWithCString.argtypes = [
    ctypes.c_void_p, ctypes.c_char_p, ctypes.c_uint32
]
_kCFStringEncodingUTF8 = 0x08000100
_COMMON_MODES = _CF.CFStringCreateWithCString(
    None, b"kCFRunLoopCommonModes", _kCFStringEncodingUTF8
)

# CGEventTap constants
_kCGSessionEventTap   = 1
_kCGHeadInsertEventTap = 0
_kCGEventTapOptionDefault = 0   # intercept (can suppress)

_kCGEventKeyDown = 10
_kCGEventKeyUp   = 11

_kCGKeyboardEventKeycode = 9    # CGEventField

# CGEvent modifier flag masks
_FLAG_CMD   = 0x000100000
_FLAG_CTRL  = 0x000040000
_FLAG_ALT   = 0x000080000
_FLAG_SHIFT = 0x000020000
_MOD_MASK   = _FLAG_CMD | _FLAG_CTRL | _FLAG_ALT | _FLAG_SHIFT

# ---------------------------------------------------------------------------
# Virtual-key → key_str tables  (ANSI layout; layout-independent for specials)
# ---------------------------------------------------------------------------

# Special / function keys — same key_str as pynput uses
_VK_SPECIAL: dict[int, str] = {
    36:  "Key.enter",
    48:  "Key.tab",
    49:  "Key.space",
    51:  "Key.backspace",
    53:  "Key.esc",
    96:  "Key.f5",
    97:  "Key.f6",
    98:  "Key.f7",
    99:  "Key.f3",
    100: "Key.f8",
    101: "Key.f9",
    103: "Key.f11",
    109: "Key.f10",
    111: "Key.f12",
    113: "Key.f13",
    114: "Key.insert",
    115: "Key.home",
    116: "Key.page_up",
    117: "Key.delete",
    119: "Key.end",
    120: "Key.f2",
    121: "Key.page_down",
    122: "Key.f1",
    123: "Key.left",
    124: "Key.right",
    125: "Key.down",
    126: "Key.up",
}

# Character keys: vk → (unshifted, shifted)
_VK_CHAR: dict[int, tuple[str, str]] = {
    0:  ("a", "A"),  1:  ("s", "S"),  2:  ("d", "D"),  3:  ("f", "F"),
    4:  ("h", "H"),  5:  ("g", "G"),  6:  ("z", "Z"),  7:  ("x", "X"),
    8:  ("c", "C"),  9:  ("v", "V"), 11:  ("b", "B"), 12:  ("q", "Q"),
    13: ("w", "W"), 14:  ("e", "E"), 15:  ("r", "R"), 16:  ("y", "Y"),
    17: ("t", "T"), 18:  ("1", "!"), 19:  ("2", "@"), 20:  ("3", "#"),
    21: ("4", "$"), 22:  ("6", "^"), 23:  ("5", "%"), 24:  ("=", "+"),
    25: ("9", "("), 26:  ("7", "&"), 27:  ("-", "_"), 28:  ("8", "*"),
    29: ("0", ")"), 30:  ("]", "}"), 31:  ("o", "O"), 32:  ("u", "U"),
    33: ("[", "{"), 34:  ("i", "I"), 35:  ("p", "P"), 37:  ("l", "L"),
    38: ("j", "J"), 39:  ("'", '"'), 40:  ("k", "K"), 41:  (";", ":"),
    42: ("\\", "|"), 43: (",", "<"), 44:  ("/", "?"), 45:  ("n", "N"),
    46: ("m", "M"), 47:  (".", ">"), 50:  ("`", "~"),
}

_SETTLE_S = 0.15  # key-capture settle window (matches InputListener)


def _make_key_str(vk: int, flags: int) -> str:
    """Convert a CGEvent virtual keycode + modifier flags to a key_str."""
    # Determine which modifiers are active
    active = flags & _MOD_MASK
    has_shift = bool(active & _FLAG_SHIFT)
    other_mods = active & ~_FLAG_SHIFT  # cmd / ctrl / alt

    # Build modifier prefix for non-shift modifiers
    parts: list[str] = []
    if active & _FLAG_CMD:
        parts.append("cmd")
    if active & _FLAG_CTRL:
        parts.append("ctrl")
    if active & _FLAG_ALT:
        parts.append("alt")

    if vk in _VK_SPECIAL:
        # For special keys, include shift in the prefix too
        if has_shift:
            parts.insert(
                next((i for i, p in enumerate(parts) if p not in ("cmd", "ctrl", "alt")), len(parts)),
                "shift",
            )
            # Simpler: append shift at the right spot
            # Actually rebuild with shift included:
            parts2: list[str] = []
            if active & _FLAG_CMD:
                parts2.append("cmd")
            if active & _FLAG_CTRL:
                parts2.append("ctrl")
            if active & _FLAG_ALT:
                parts2.append("alt")
            if has_shift:
                parts2.append("shift")
            parts = parts2
        prefix = "+".join(parts) + "+" if parts else ""
        return prefix + _VK_SPECIAL[vk]

    if vk in _VK_CHAR:
        # Shift is absorbed into the character (matches pynput behaviour)
        char = _VK_CHAR[vk][1 if has_shift else 0]
        prefix = "+".join(parts) + "+" if parts else ""
        return prefix + char

    # Unknown key — fall back to vk number
    prefix = "+".join(parts) + "+" if parts else ""
    return f"{prefix}vk:{vk}"


# ---------------------------------------------------------------------------
# CGEventListener
# ---------------------------------------------------------------------------

class CGEventListener:
    """
    macOS CGEventTap listener that intercepts only keys Dispatch has mapped.

    Drop-in replacement for InputListener on macOS.  Extra public method:
        set_mapped_keys(keys)  — call whenever the active mapping set changes.
    """

    def __init__(self) -> None:
        self._threshold: float = 0.5
        self._action_cb: Optional[Callable] = None
        self._lock = threading.Lock()
        self._pressed: dict = {}
        self._mapped_keys: Set[str] = set()
        self._capture_cb: Optional[Callable] = None
        self._capture_timer: Optional[threading.Timer] = None
        self._capture_last_key: Optional[str] = None

        self._tap_port: Optional[ctypes.c_void_p] = None
        self._run_loop: Optional[ctypes.c_void_p] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._error: Optional[str] = None

        # Keep a reference so the ctypes callback isn't garbage-collected
        self._c_callback: Optional[_TAP_CALLBACK] = None

    # ── Public API (matches InputListener) ───────────────────────────────────

    def set_threshold(self, ms: int) -> None:
        self._threshold = max(100, ms) / 1000.0

    def set_action_callback(self, cb: Callable[[str, str], None]) -> None:
        self._action_cb = cb

    def set_mapped_keys(self, keys: Set[str]) -> None:
        """Update which key_strs Dispatch should intercept and consume."""
        with self._lock:
            self._mapped_keys = set(keys)

    def capture_next_key(self, cb: Callable[[str], None]) -> None:
        with self._lock:
            if self._capture_timer:
                self._capture_timer.cancel()
                self._capture_timer = None
            self._capture_cb = cb
            self._capture_last_key = None

    def cancel_capture(self) -> None:
        with self._lock:
            self._capture_cb = None
            self._capture_last_key = None
            if self._capture_timer:
                self._capture_timer.cancel()
                self._capture_timer = None

    def start(self) -> None:
        if self._running:
            return
        self._thread = threading.Thread(
            target=self._run_loop_thread, daemon=True, name="CGEventTap"
        )
        self._thread.start()
        # Give the thread a moment to set _running or _error
        self._thread.join(timeout=0.5)
        if self._error:
            raise RuntimeError(self._error)

    def stop(self) -> None:
        self._running = False
        if self._tap_port:
            _CG.CGEventTapEnable(self._tap_port, False)
        if self._run_loop:
            _CF.CFRunLoopStop(self._run_loop)

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def last_error(self) -> Optional[str]:
        return self._error

    # ── Run-loop thread ───────────────────────────────────────────────────────

    def _run_loop_thread(self) -> None:
        # Build the event mask for key-down and key-up
        event_mask = (1 << _kCGEventKeyDown) | (1 << _kCGEventKeyUp)

        # Wrap our Python method as a C function pointer (kept alive via self)
        self._c_callback = _TAP_CALLBACK(self._tap_callback)

        tap = _CG.CGEventTapCreate(
            _kCGSessionEventTap,
            _kCGHeadInsertEventTap,
            _kCGEventTapOptionDefault,
            event_mask,
            self._c_callback,
            None,
        )

        if not tap:
            self._error = (
                "CGEventTap creation failed — "
                "grant Input Monitoring permission in System Settings and restart."
            )
            return

        self._tap_port = tap
        source = _CF.CFMachPortCreateRunLoopSource(None, tap, 0)
        rl = _CF.CFRunLoopGetCurrent()
        self._run_loop = rl
        _CF.CFRunLoopAddSource(rl, source, _COMMON_MODES)
        _CG.CGEventTapEnable(tap, True)
        self._running = True
        self._error = None
        _CF.CFRunLoopRun()   # blocks until stop() calls CFRunLoopStop
        self._running = False

    # ── CGEvent callback (runs on the run-loop thread) ────────────────────────

    def _tap_callback(
        self,
        proxy: ctypes.c_void_p,
        event_type: int,
        event: ctypes.c_void_p,
        refcon: ctypes.c_void_p,
    ) -> Optional[ctypes.c_void_p]:
        if event_type not in (_kCGEventKeyDown, _kCGEventKeyUp):
            return event

        vk    = int(_CG.CGEventGetIntegerValueField(event, _kCGKeyboardEventKeycode))
        flags = int(_CG.CGEventGetFlags(event))
        key_str = _make_key_str(vk, flags)
        is_down = event_type == _kCGEventKeyDown

        with self._lock:
            in_capture = self._capture_cb is not None
            is_mapped  = key_str in self._mapped_keys

        if in_capture:
            if is_down:
                self._handle_capture(key_str)
            return None  # consume all keys while capturing

        if not is_mapped:
            return event  # pass through — Spotlight / system handles it

        # Mapped key: consume and track press/release
        if is_down:
            self._handle_press(key_str)
        else:
            self._handle_release(key_str)
        return None  # consumed — OS never sees it

    # ── Capture mode ──────────────────────────────────────────────────────────

    def _handle_capture(self, key_str: str) -> None:
        with self._lock:
            to_cancel = self._capture_timer
            self._capture_last_key = key_str
            cb = self._capture_cb

            def _deliver(candidate: str = key_str) -> None:
                with self._lock:
                    if self._capture_last_key != candidate:
                        return  # a later key replaced this one
                    self._capture_cb = None
                    self._capture_timer = None
                    self._capture_last_key = None
                try:
                    cb(candidate)
                except Exception:
                    pass

            timer = threading.Timer(_SETTLE_S, _deliver)
            self._capture_timer = timer

        if to_cancel:
            to_cancel.cancel()
        timer.start()

    # ── Short / long press state machine ─────────────────────────────────────

    def _handle_press(self, key_str: str) -> None:
        with self._lock:
            if key_str in self._pressed:
                return  # debounce key-repeat
            timer = threading.Timer(self._threshold, self._fire_long, args=[key_str])
            self._pressed[key_str] = {
                "time": time.monotonic(),
                "long_fired": False,
                "timer": timer,
            }
        timer.start()

    def _handle_release(self, key_str: str) -> None:
        with self._lock:
            info = self._pressed.pop(key_str, None)
        if info is None:
            return
        info["timer"].cancel()
        if not info["long_fired"]:
            self._dispatch(key_str, "short")

    def _fire_long(self, key_str: str) -> None:
        with self._lock:
            if key_str not in self._pressed:
                return
            if self._pressed[key_str]["long_fired"]:
                return
            self._pressed[key_str]["long_fired"] = True
        self._dispatch(key_str, "long")

    def _dispatch(self, key_str: str, press_type: str) -> None:
        if self._action_cb:
            try:
                self._action_cb(key_str, press_type)
            except Exception:
                pass

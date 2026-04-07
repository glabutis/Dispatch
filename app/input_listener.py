"""
Global keyboard listener with short/long press detection.

Threading model:
- pynput runs its listener in a background thread.
- Key action callbacks are invoked from that background thread.
- Callers (e.g. MainWindow) are responsible for marshalling to the Qt main
  thread via Qt signals.
"""

import sys
import threading
import time
from typing import Callable, Optional

from pynput import keyboard

from .key_utils import key_to_str

# How long (seconds) to wait after the first captured key before delivering it.
# Presentation remotes (e.g. Logitech Spotlight) sometimes fire a spurious
# "forward" event immediately before the intended "back" or "spotlight" button.
# Waiting a short window and delivering the *last* key seen avoids this.
_CAPTURE_SETTLE_S = 0.15


class InputListener:
    """
    Listens globally for keyboard events and fires callbacks for short/long
    press detection.

    Typical usage::

        listener = InputListener()
        listener.set_threshold(500)
        listener.set_action_callback(lambda key, ptype: print(key, ptype))
        listener.start()
    """

    def __init__(self) -> None:
        self._threshold: float = 0.5        # seconds
        self._action_cb: Optional[Callable] = None
        self._listener: Optional[keyboard.Listener] = None
        self._lock = threading.Lock()
        self._pressed: dict = {}            # key_str -> {time, long_fired, timer}
        self._capture_cb: Optional[Callable] = None
        self._capture_timer: Optional[threading.Timer] = None
        self._capture_last_key: Optional[str] = None
        self._running = False
        self._error: Optional[str] = None

    # ── Public API ───────────────────────────────────────────────────────────

    def set_threshold(self, ms: int) -> None:
        """Set the long-press threshold in milliseconds."""
        self._threshold = max(100, ms) / 1000.0

    def set_mapped_keys(self, keys) -> None:
        """No-op on non-macOS; pynput cannot intercept system shortcuts."""

    def set_action_callback(self, cb: Callable[[str, str], None]) -> None:
        """
        Set callback invoked when a key action is detected.

        ``cb(key_str, press_type)`` where *press_type* is ``"short"`` or
        ``"long"``.  Called from the pynput listener thread.
        """
        self._action_cb = cb

    def start(self) -> None:
        """Start the keyboard listener."""
        if self._running:
            return
        try:
            self._listener = keyboard.Listener(
                on_press=self._on_press,
                on_release=self._on_release,
            )
            self._listener.start()
            self._running = True
            self._error = None
        except Exception as exc:
            self._running = False
            self._error = str(exc)
            raise

    def stop(self) -> None:
        """Stop the keyboard listener and cancel all pending timers."""
        self._running = False
        if self._listener:
            self._listener.stop()
            self._listener = None
        with self._lock:
            for info in self._pressed.values():
                info.get("timer", _NullTimer()).cancel()
            self._pressed.clear()

    def capture_next_key(self, cb: Callable[[str], None]) -> None:
        """
        Arm capture mode: deliver the last key pressed within a short settle
        window to *cb(key_str)*.  Normal action processing is bypassed.

        The settle delay (_CAPTURE_SETTLE_S) lets remotes that emit a spurious
        key before the intended button (e.g. Logitech Spotlight) be handled
        correctly — only the final key in the burst is delivered.
        """
        with self._lock:
            if self._capture_timer:
                self._capture_timer.cancel()
                self._capture_timer = None
            self._capture_cb = cb
            self._capture_last_key = None

    def cancel_capture(self) -> None:
        """Cancel any pending key-capture request."""
        with self._lock:
            self._capture_cb = None
            self._capture_last_key = None
            if self._capture_timer:
                self._capture_timer.cancel()
                self._capture_timer = None

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def last_error(self) -> Optional[str]:
        return self._error

    # ── Internal ─────────────────────────────────────────────────────────────

    def _on_press(self, key) -> None:
        key_str = key_to_str(key)
        to_cancel = None
        to_start = None

        with self._lock:
            if self._capture_cb:
                # Settle-delay capture: each new key in the burst resets the
                # timer and updates the candidate.  After _CAPTURE_SETTLE_S of
                # silence the last candidate is delivered.
                to_cancel = self._capture_timer
                self._capture_last_key = key_str
                cb = self._capture_cb  # keep ref; cleared inside _deliver

                def _deliver(candidate=key_str):
                    with self._lock:
                        if self._capture_last_key != candidate:
                            return  # a newer key replaced this one
                        self._capture_cb = None
                        self._capture_timer = None
                        self._capture_last_key = None
                    try:
                        cb(candidate)
                    except Exception:
                        pass

                to_start = threading.Timer(_CAPTURE_SETTLE_S, _deliver)
                self._capture_timer = to_start

            elif key_str in self._pressed:
                return  # debounce key-repeat

            else:
                to_start = threading.Timer(self._threshold, self._fire_long, args=[key_str])
                self._pressed[key_str] = {
                    "time": time.monotonic(),
                    "long_fired": False,
                    "timer": to_start,
                }

        if to_cancel:
            to_cancel.cancel()
        if to_start:
            to_start.start()

    def _on_release(self, key) -> None:
        key_str = key_to_str(key)

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


class _NullTimer:
    """Stand-in timer with a no-op cancel() for safe cleanup."""
    def cancel(self):
        pass

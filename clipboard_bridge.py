"""
clipboard_bridge.py — Hostless data channel via clipboard

Architecture:
  Browser (Tampermonkey) → clipboard with prefix TX_EMB::
  Python (ClipboardBridge) → QTimer polls clipboard every 400ms
  → emits data_received(dict) signal identical to FlaskWorker

No server, no network, no port forwarding needed.
The clipboard is polled, data is extracted, clipboard restored to avoid pollution.
"""
import json
from PySide6.QtCore import QObject, Signal, QTimer
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QClipboard

MARKER = "TX_EMB::"          # Prefix that marks TX data in clipboard
POLL_MS = 400                 # Polling interval in milliseconds


class ClipboardBridge(QObject):
    """Polls the system clipboard and emits data_received when TX data found."""
    data_received = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._last_text = ""
        self._timer = QTimer(self)
        self._timer.setInterval(POLL_MS)
        self._timer.timeout.connect(self._poll_safe)  # Use safe wrapper
        self._clipboard = QApplication.clipboard()

    def start(self):
        self._timer.start()
        print("[ClipBoard] Clipboard bridge started — waiting for TX_EMB:: data")

    def stop(self):
        self._timer.stop()

    def _poll(self):
        try:
            text = self._clipboard.text(QClipboard.Clipboard).strip()
        except Exception:
            return

        if text == self._last_text:
            return                        # Nothing new
        self._last_text = text

        if not text.startswith(MARKER):
            return                        # Normal clipboard content — ignore

        payload_str = text[len(MARKER):]
        try:
            data = json.loads(payload_str)
        except json.JSONDecodeError:
            try:
                print(f"[ClipBoard] Bad JSON in clipboard: {payload_str[:80]}")
            except Exception:
                print("[ClipBoard] Bad JSON in clipboard (unprintable)")
            return

        if not isinstance(data, dict):
            return
        if 'test' in data:
            print("[ClipBoard] Ping received via clipboard")
            return

        # Safe print: avoid OSError on Windows console with bad chars in scraped data
        try:
            preview = str(data)[:120]
            print(f"[ClipBoard] Data received: {preview}...")
        except Exception:
            try:
                print("[ClipBoard] Data received (preview unavailable, keys: {})".format(list(data.keys())[:5]))
            except Exception:
                print("[ClipBoard] Data received (unprintable)")

        # Clear clipboard so we don't re-process on next poll
        self._clipboard.clear(QClipboard.Clipboard)
        self._last_text = ""
        self.data_received.emit(data)

    def _poll_safe(self):
        """Wrapper so any unexpected error in polling never crashes the bridge."""
        try:
            self._poll()
        except Exception as e:
            try:
                print(f"[ClipBoard] _poll error (suppressed): {e}")
            except Exception:
                pass

import sys
from PySide6.QtWidgets import QApplication
from server import FlaskWorker
from clipboard_bridge import ClipboardBridge
from gui import MiniApp
import logic
import security
import tai_xiu_game
import tx_network
import color_reader
import auto_workflow
import ui_components

from PySide6.QtNetwork import QLocalServer, QLocalSocket

def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # Main window manages app lifetime explicitly
    
    # Singleton Check
    server_name = "TX_Embroider_Unique_Server"
    socket = QLocalSocket()
    socket.connectToServer(server_name)
    
    if socket.waitForConnected(500):
        # Existing instance found: request it to show/reset.
        # Exit only when the old instance confirms handling the request.
        socket.write(b"RESET_AND_SHOW")
        socket.waitForBytesWritten(1000)
        acknowledged = socket.waitForReadyRead(1200)
        reply = socket.readAll().data().decode().strip() if acknowledged else ""
        socket.disconnectFromServer()
        if reply == "OK":
            sys.exit(0)
        # Stale/unresponsive old instance: clean socket name and continue launching.
        QLocalServer.removeServer(server_name)
    
    # Not running - Start Server
    server = QLocalServer()
    if not server.listen(server_name):
        QLocalServer.removeServer(server_name)
        server.listen(server_name)
    # Check License and Register if needed
    is_auth, msg, expiry = security.check_license()
    if not is_auth:
        from gui import LicenseDialog
        dialog = LicenseDialog(security.get_hwid(), security.get_pc_name(), msg)
        dialog.exec()
        sys.exit(0)

    # Force nickname selection on start of tool
    from tai_xiu_game import load_profile, save_profile, NameInputDialog
    profile = load_profile()
    if not profile.get("username"):
        dialog = NameInputDialog()
        if dialog.exec() == 1 or dialog.username: # Accepted is 1
            profile["username"] = dialog.username
            save_profile(profile)
        else:
            sys.exit(0) # Forced exit if cancelled

    # Create Main Window
    window = MiniApp()
    window.flash_status("READY", "#00ff41")
    
    # Connect Singleton Server to Window
    def handle_new_connection():
        new_socket = server.nextPendingConnection()
        if not new_socket:
            return
        try:
            if new_socket.waitForReadyRead(1000):
                data = new_socket.readAll().data().decode()
                if data == "RESET_AND_SHOW":
                    window.on_instance_requested()
            new_socket.write(b"OK")
            new_socket.waitForBytesWritten(500)
        except Exception:
            # Keep server alive even if request handler fails.
            pass
        new_socket.disconnectFromServer()
    
    server.newConnection.connect(handle_new_connection)
    
    # UPDATE CHECK
    new_v, up_url = security.check_updates("1.3.0") # Current Version
    if new_v:
        from PySide6.QtWidgets import QMessageBox
        reply = QMessageBox.question(window, "New Update", 
                                   f"Version {new_v} is available. Update now?",
                                   QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            window.flash_status(f"UPDATING...", "#00ffff")
            if security.start_update(up_url):
                sys.exit(0)
            else:
                window.flash_status("UPD FAIL", "#ff0000")
        else:
            window.flash_status(f"NEW:{new_v}", "#00ffff")
    
    # ── Channel 1: HTTP/WebSocket server (requires local host) ────────────────
    flask_thread = FlaskWorker()
    flask_thread.data_received.connect(window.update_data)
    window.flask_thread = flask_thread
    flask_thread.start()

    # ── Channel 2: Clipboard bridge (hostless — no server needed) ─────────────
    clip_bridge = ClipboardBridge()
    clip_bridge.data_received.connect(window.update_data)
    clip_bridge.start()

    window.show()
    sys.exit(app.exec())

def exception_hook(exctype, value, traceback):
    from datetime import datetime
    import traceback as tb
    try:
        with open("error.log", "a", encoding="utf-8", errors="replace") as f:
            f.write(f"\n[{datetime.now()}] CRASH REPORT:\n")
            tb.print_exception(exctype, value, traceback, file=f)
    except Exception:
        pass  # Never let the error logger itself crash
    sys.__excepthook__(exctype, value, traceback)

if __name__ == "__main__":
    sys.excepthook = exception_hook
    main()

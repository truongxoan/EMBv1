"""
server.py — Flask HTTP + WebSocket server
- /receive  : HTTP POST (legacy Tampermonkey V5.x)
- /info     : HTTP GET  (ping + app info)
- WS :5001  : WebSocket direct channel (Tampermonkey V5.6+)
  Client sends JSON → server emits data_received signal to Qt GUI
"""
from flask import Flask, request, jsonify
from PySide6.QtCore import QObject, Signal, QThread
import logging, json, threading, socket as _socket

# ── Suppress Flask/werkzeug console noise ────────────────────────────────────
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# ── Optional WebSocket support ────────────────────────────────────────────────
try:
    import websockets
    import asyncio
    HAS_WS = True
except ImportError:
    HAS_WS = False

APP_NAME    = "TX Embroider Tool"
APP_VERSION = "1.3.0"
WS_PORT     = 5001   # WebSocket listens on a separate port from Flask (5000)


# Global set to track active sockets
active_sockets = set()

class FlaskWorker(QThread):
    data_received = Signal(dict)

    def __init__(self):
        super().__init__()
        self.app = Flask(__name__)
        self.setup_routes()
        self.loop = None
        # Start WebSocket server in its own daemon thread
        if HAS_WS:
            ws_thread = threading.Thread(target=self._start_ws, daemon=True)
            ws_thread.start()

    # ── Flask routes ─────────────────────────────────────────────────────────
    def setup_routes(self):
        @self.app.route('/receive', methods=['POST'])
        def receive_data():
            try:
                data = request.json
                if isinstance(data, list):
                    for item in data:
                        if 'test' not in item:
                            self.data_received.emit(item)
                elif isinstance(data, dict):
                    if 'test' not in data:
                        self.data_received.emit(data)
                return jsonify({"status": "success"}), 200
            except Exception as e:
                return jsonify({"status": "error", "message": str(e)}), 500

        @self.app.route('/info', methods=['GET'])
        def app_info():
            return jsonify({"name": APP_NAME, "version": APP_VERSION}), 200

        @self.app.route('/ws_info', methods=['GET'])
        def ws_info():
            """Tell Tampermonkey where WebSocket is"""
            return jsonify({
                "name": APP_NAME,
                "version": APP_VERSION,
                "ws_port": WS_PORT if HAS_WS else None,
                "ws_url": f"ws://127.0.0.1:{WS_PORT}" if HAS_WS else None,
            }), 200

    # ── WebSocket server (asyncio in daemon thread) ───────────────────────────
    def _start_ws(self):
        """Run asyncio event loop with WebSocket server in a daemon thread."""
        try:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop.run_until_complete(self._ws_serve())
        except Exception as e:
            print(f"[WS] Server error: {e}")

    async def _ws_serve(self):
        async def handler(websocket):
            client = websocket.remote_address
            print(f"[WS] Client connected: {client}")
            active_sockets.add(websocket)
            try:
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        if isinstance(data, dict) and 'test' not in data:
                            # Emit to Qt main thread via signal
                            self.data_received.emit(data)
                            await websocket.send(json.dumps({"status": "ok"}))
                        elif isinstance(data, dict) and 'test' in data:
                            # Ping from script
                            await websocket.send(json.dumps({
                                "status": "pong",
                                "name": APP_NAME,
                                "version": APP_VERSION
                            }))
                    except json.JSONDecodeError:
                        await websocket.send(json.dumps({"status": "error", "msg": "invalid json"}))
            except Exception:
                pass
            finally:
                if websocket in active_sockets:
                    active_sockets.remove(websocket)
                print(f"[WS] Client disconnected: {client}")

        try:
            async with websockets.serve(handler, "127.0.0.1", WS_PORT):
                print(f"[WS] WebSocket server running on ws://127.0.0.1:{WS_PORT}")
                await asyncio.Future()  # run forever
        except OSError as e:
            print(f"[WS] Could not bind port {WS_PORT}: {e}")

    def send_to_ws_clients(self, msg_dict):
        """Send a message to all connected WebSocket clients from any thread."""
        if not HAS_WS or not self.loop:
            return
        
        async def send_all():
            if active_sockets:
                msg_str = json.dumps(msg_dict)
                for ws in list(active_sockets):
                    try:
                        await ws.send(msg_str)
                    except Exception as e:
                        print(f"[WS] Error sending: {e}")
                        
        asyncio.run_coroutine_threadsafe(send_all(), self.loop)

    def run(self):
        print(f"[HTTP] Flask server running on http://127.0.0.1:5000")
        self.app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)

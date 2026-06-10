import os
import json
import time
import websocket
from PyQt6.QtCore import QThread, pyqtSignal

# Read server URL from env var, fallback to localhost
WS_URL = os.environ.get("CAS_WS_URL", "ws://localhost:8000/ws/alerts")

class WebSocketWorker(QThread):
    new_alert_signal = pyqtSignal(dict)
    dismiss_alert_signal = pyqtSignal(int)
    connection_status_signal = pyqtSignal(bool)

    def __init__(self, url=None):
        super().__init__()
        self.url = url or WS_URL
        self.ws = None
        self._is_running = True

    def run(self):
        while self._is_running:
            try:
                self.ws = websocket.WebSocketApp(
                    self.url,
                    on_message=self.on_message,
                    on_error=self.on_error,
                    on_close=self.on_close
                )
                self.ws.on_open = self.on_open
                # run_forever works in a blocking way, adding ping to keep alive
                self.ws.run_forever(ping_interval=30, ping_timeout=10)
            except Exception as e:
                print(f"WS thread error: {e}")
            
            # Reconnect delay if disconnected and still running
            if self._is_running:
                time.sleep(5)

    def on_message(self, ws, message):
        try:
            data = json.loads(message)
            if data.get("action") == "dismiss":
                alert_id = data.get("id")
                if alert_id is not None:
                    self.dismiss_alert_signal.emit(int(alert_id))
            else:
                self.new_alert_signal.emit(data)
        except Exception as e:
            print(f"Error parsing message: {e}")

    def on_error(self, ws, error):
        print(f"WebSocket Error: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        print("WebSocket Closed")
        self.connection_status_signal.emit(False)

    def on_open(self, ws):
        print(f"WebSocket Connected to {self.url}")
        self.connection_status_signal.emit(True)

    def send_message(self, message_dict):
        if self.ws and self._is_running:
            try:
                self.ws.send(json.dumps(message_dict))
            except Exception as e:
                print(f"Send error: {e}")

    def stop(self):
        self._is_running = False
        if self.ws:
            self.ws.close()

import os
import sys
import json
import time
import logging
import websocket
from pathlib import Path
from dotenv import load_dotenv
from PyQt6.QtCore import QThread, pyqtSignal

# Load .env from the executable directory if frozen, else from script dir
if getattr(sys, 'frozen', False):
    base_dir = Path(sys.executable).parent
else:
    base_dir = Path(__file__).parent

load_dotenv(dotenv_path=base_dir / ".env")

logger = logging.getLogger(__name__)

# Read server URL from env var, fallback to localhost
WS_URL = os.environ.get("CAS_WS_URL", "ws://localhost:8000/ws/alerts")


class WebSocketWorker(QThread):
    new_alert_signal = pyqtSignal(dict)
    dismiss_alert_signal = pyqtSignal(int)
    connection_status_signal = pyqtSignal(bool)

    def __init__(self, url: str = None):
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
                    on_close=self.on_close,
                )
                self.ws.on_open = self.on_open
                # run_forever blocks; ping keeps the connection alive
                self.ws.run_forever(ping_interval=60, ping_timeout=30)
            except Exception:
                logger.exception("WebSocket thread encountered an unexpected error.")

            # Reconnect delay if still running
            if self._is_running:
                logger.info("Reconnecting in 5 seconds...")
                time.sleep(5)

    def on_message(self, ws, message: str):
        try:
            data = json.loads(message)
            if data.get("action") == "dismiss":
                alert_id = data.get("id")
                if alert_id is not None:
                    self.dismiss_alert_signal.emit(int(alert_id))
            else:
                self.new_alert_signal.emit(data)
        except (json.JSONDecodeError, ValueError, TypeError):
            logger.warning(f"Failed to parse incoming message: {message!r}")
        except Exception:
            logger.exception("Unexpected error handling incoming message.")

    def on_error(self, ws, error):
        logger.error(f"WebSocket error: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        logger.info(f"WebSocket closed (code={close_status_code}, msg={close_msg}).")
        self.connection_status_signal.emit(False)

    def on_open(self, ws):
        logger.info(f"WebSocket connected to {self.url}.")
        self.connection_status_signal.emit(True)

    def send_message(self, message_dict: dict):
        """Send a JSON message to the server. Called from the main (Qt) thread."""
        if self.ws and self._is_running:
            try:
                self.ws.send(json.dumps(message_dict))
            except Exception:
                logger.exception("Failed to send message to server.")

    def stop(self):
        self._is_running = False
        if self.ws:
            self.ws.close()

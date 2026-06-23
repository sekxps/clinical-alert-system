import sys
import logging
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtGui import QAction
from PyQt6.QtCore import pyqtSlot, QObject
from websocket_worker import WebSocketWorker
from toast_notification import ToastNotification

# ---------------------------------------------------------------------------
# Logging Setup (StreamHandler and FileHandler)
# ---------------------------------------------------------------------------
import os
import winreg
from pathlib import Path

if getattr(sys, 'frozen', False):
    base_dir = Path(sys.executable).parent
else:
    base_dir = Path(__file__).parent

log_file = os.path.join(base_dir, "cas_client.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_file, encoding='utf-8')
    ],
)
logger = logging.getLogger(__name__)


class CASDesktopApp(QObject):
    def __init__(self, app: QApplication):
        super().__init__()
        self.app = app
        # Keep app running even when all windows are closed
        self.app.setQuitOnLastWindowClosed(False)

        self.setup_tray_icon()

        # Keep strong references to active toasts to prevent GC
        self.active_toasts: list[ToastNotification] = []

        # Setup WebSocket worker thread
        self.ws_worker = WebSocketWorker()
        self.ws_worker.new_alert_signal.connect(self.on_new_alert)
        self.ws_worker.dismiss_alert_signal.connect(self.on_dismiss_alert)
        self.ws_worker.connection_status_signal.connect(self.on_connection_status)
        self.ws_worker.start()
        logger.info("CAS Desktop Client started.")

    def setup_tray_icon(self):
        self.tray = QSystemTrayIcon()
        icon = self.app.style().standardIcon(
            self.app.style().StandardPixmap.SP_MessageBoxCritical
        )
        self.tray.setIcon(icon)

        menu = QMenu()

        self.status_action = QAction("Status: Connecting...")
        self.status_action.setEnabled(False)
        menu.addAction(self.status_action)

        menu.addSeparator()

        self.startup_action = QAction("Run on Startup", checkable=True)
        self.startup_action.setChecked(self.is_run_on_startup())
        self.startup_action.triggered.connect(self.toggle_startup)
        menu.addAction(self.startup_action)

        menu.addSeparator()

        self.logs_action = QAction("View Logs")
        self.logs_action.triggered.connect(self.open_logs)
        menu.addAction(self.logs_action)

        menu.addSeparator()

        quit_action = QAction("Exit App")
        quit_action.triggered.connect(self.quit_app)
        menu.addAction(quit_action)

        self.tray.setContextMenu(menu)
        self.tray.show()
        self.tray.setToolTip("CAS Monitoring")

    def is_run_on_startup(self) -> bool:
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_READ)
            value, _ = winreg.QueryValueEx(key, "CASClient")
            winreg.CloseKey(key)
            return sys.executable in value
        except FileNotFoundError:
            return False

    @pyqtSlot(bool)
    def toggle_startup(self, enable: bool):
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_ALL_ACCESS)
            if enable:
                exe_path = f'"{sys.executable}"'
                if not getattr(sys, 'frozen', False):
                    exe_path = f'"{sys.executable}" "{os.path.abspath(__file__)}"'
                winreg.SetValueEx(key, "CASClient", 0, winreg.REG_SZ, exe_path)
                logger.info("Enabled run on startup.")
            else:
                try:
                    winreg.DeleteValue(key, "CASClient")
                    logger.info("Disabled run on startup.")
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
        except Exception as e:
            logger.error(f"Failed to modify startup registry key: {e}")

    def open_logs(self):
        import platform
        import subprocess
        if not os.path.exists(log_file):
            open(log_file, 'a').close()
            
        if platform.system() == 'Windows':
            os.startfile(log_file)
        else:
            subprocess.call(('open', log_file))

    @pyqtSlot(dict)
    def on_new_alert(self, alert_data: dict):
        """Create a toast notification for a new incoming alert."""
        alert_id = alert_data.get("id")

        # Deduplicate: do not show a second toast for the same alert ID
        if any(getattr(t, "alert_id", None) == alert_id for t in self.active_toasts):
            logger.debug(f"Duplicate alert id={alert_id} — skipping.")
            return

        toast = ToastNotification(alert_data)
        toast.acknowledge_signal.connect(self.send_acknowledge_to_server)
        self.active_toasts.append(toast)
        toast.show_toast()

        # Use a default-argument capture to avoid the lambda closure bug
        toast.destroyed.connect(
            lambda checked=False, t=toast: (
                self.active_toasts.remove(t) if t in self.active_toasts else None
            )
        )
        logger.info(f"Showing toast for alert id={alert_id}.")

    @pyqtSlot(int)
    def send_acknowledge_to_server(self, alert_id: int):
        payload = {"action": "acknowledge", "id": alert_id}
        self.ws_worker.send_message(payload)
        logger.info(f"Sent acknowledge for alert id={alert_id}.")

    @pyqtSlot(int)
    def on_dismiss_alert(self, alert_id: int):
        """Close any active toast matching the given alert ID."""
        for toast in list(self.active_toasts):
            if getattr(toast, "alert_id", None) == alert_id:
                toast.close()

    @pyqtSlot(bool)
    def on_connection_status(self, is_connected: bool):
        if is_connected:
            icon = self.app.style().standardIcon(
                self.app.style().StandardPixmap.SP_MessageBoxInformation
            )
            self.tray.setIcon(icon)
            self.status_action.setText("Status: Connected ✅")
            self.tray.setToolTip("CAS Monitoring — Connected")
            logger.info("WebSocket connection established.")
        else:
            icon = self.app.style().standardIcon(
                self.app.style().StandardPixmap.SP_MessageBoxCritical
            )
            self.tray.setIcon(icon)
            self.status_action.setText("Status: Disconnected / Retrying...")
            self.tray.setToolTip("CAS Monitoring — Disconnected")
            logger.warning("WebSocket disconnected — worker will attempt reconnection.")

    def quit_app(self):
        logger.info("Shutting down CAS Desktop Client...")
        self.ws_worker.stop()
        self.ws_worker.wait(3000)  # Give worker up to 3 s to close cleanly
        self.app.quit()


if __name__ == "__main__":
    app_instance = QApplication(sys.argv)
    client_app = CASDesktopApp(app_instance)
    sys.exit(app_instance.exec())

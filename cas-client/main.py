import sys
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QMessageBox
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import pyqtSlot, QObject
from websocket_worker import WebSocketWorker
from toast_notification import ToastNotification

class CASDesktopApp(QObject):
    def __init__(self, app):
        super().__init__()
        self.app = app
        # Keeps app running even if popup is closed
        self.app.setQuitOnLastWindowClosed(False)
        
        self.setup_tray_icon()
        
        # Keep track of active toasts to prevent premature python garbage collection
        self.active_toasts = []
        
        # Setup WebSocket Thread
        self.ws_worker = WebSocketWorker()
        self.ws_worker.new_alert_signal.connect(self.on_new_alert)
        self.ws_worker.dismiss_alert_signal.connect(self.on_dismiss_alert)
        self.ws_worker.connection_status_signal.connect(self.on_connection_status)
        self.ws_worker.start()

    def setup_tray_icon(self):
        self.tray = QSystemTrayIcon()
        # Fallback to a standard critical icon for the tray
        icon = self.app.style().standardIcon(self.app.style().StandardPixmap.SP_MessageBoxCritical)
        self.tray.setIcon(icon)
        
        # Menu
        menu = QMenu()
        
        self.status_action = QAction("Status: Connecting...")
        self.status_action.setEnabled(False)
        menu.addAction(self.status_action)
        
        menu.addSeparator()
        
        quit_action = QAction("Exit App")
        quit_action.triggered.connect(self.quit_app)
        menu.addAction(quit_action)
        
        self.tray.setContextMenu(menu)
        self.tray.show()
        self.tray.setToolTip("CAS Monitoring")

    @pyqtSlot(dict)
    def on_new_alert(self, alert_data):
        # Prevent duplicate toasts for the same ID
        alert_id = alert_data.get("id")
        for existing in self.active_toasts:
            if getattr(existing, 'alert_id', None) == alert_id:
                return # Already showing

        # Create and show toast popup
        toast = ToastNotification(alert_data)
        toast.acknowledge_signal.connect(self.send_acknowledge_to_server)
        self.active_toasts.append(toast)
        toast.show_toast()
        
        # Remove reference when closed
        toast.destroyed.connect(lambda: self.active_toasts.remove(toast) if toast in self.active_toasts else None)

    @pyqtSlot(int)
    def send_acknowledge_to_server(self, alert_id):
        payload = {"action": "acknowledge", "id": alert_id}
        self.ws_worker.send_message(payload)

    @pyqtSlot(int)
    def on_dismiss_alert(self, alert_id):
        # Close any active toast with this ID
        for toast in list(self.active_toasts):
            if getattr(toast, 'alert_id', None) == alert_id:
                toast.close()

    @pyqtSlot(bool)
    def on_connection_status(self, is_connected):
        if is_connected:
            self.status_action.setText("Status: Connected (OK)")
            self.tray.setToolTip("CAS Monitoring - Connected")
        else:
            self.status_action.setText("Status: Disconnected / Retrying")
            self.tray.setToolTip("CAS Monitoring - Disconnected")

    def quit_app(self):
        self.ws_worker.stop()
        self.ws_worker.wait()
        self.app.quit()

if __name__ == "__main__":
    app_instance = QApplication(sys.argv)
    client_app = CASDesktopApp(app_instance)
    sys.exit(app_instance.exec())

import sys
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
from PyQt6.QtCore import pyqtSignal, Qt, QTimer, QRect
from PyQt6.QtGui import QFont, QScreen

class ToastNotification(QWidget):
    acknowledge_signal = pyqtSignal(int)

    def __init__(self, alert_data):
        super().__init__()
        self.alert_id = alert_data.get("id")
        
        # Make frameless and stay on top
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool  # Doesn't show in taskbar
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.setup_ui(alert_data)

    def setup_ui(self, alert_data):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Container with background and styling
        container = QWidget()
        container.setObjectName("toastContainer")
        container_layout = QVBoxLayout(container)
        
        # Styling based on severity field from the alert data
        severity = alert_data.get('severity', 'warning')
        severity_color = {"critical": "#e74c3c", "warning": "#e67e22", "info": "#3498db"}.get(severity, "#e67e22")
        container.setStyleSheet(f"""
            #toastContainer {{
                background-color: #2c3e50;
                border: 2px solid {severity_color};
                border-radius: 10px;
            }}
            QLabel {{
                color: white;
            }}
        """)
        
        # Title
        alert_type = alert_data.get('type', 'Clinical Alert')
        title = QLabel(f"🔴 {alert_type}")
        title_font = QFont("Segoe UI", 12, QFont.Weight.Bold)
        title.setFont(title_font)
        
        dept = alert_data.get('department', 'ไม่ระบุ')
        name = alert_data.get('patient_name', 'ไม่ระบุ')
        hn = alert_data.get('patient_hn', 'ไม่ระบุ')
        time_str = "ไม่ระบุ"
        if alert_data.get('timestamp'):
            try:
                from datetime import datetime
                d = datetime.fromisoformat(alert_data['timestamp'])
                time_str = d.strftime("%Y-%m-%d ") + alert_data.get('vsttime', '')
            except:
                pass
                
        # Format HTML message matching LINE
        html_content = f"""
        <table border="0" cellpadding="2" cellspacing="0" width="100%">
            <tr><td><font color="#8c8c8c" size="3">🏥 แผนก:</font></td><td><font color="#ecf0f1" size="3"><b>{dept}</b></font></td></tr>
            <tr><td><font color="#8c8c8c" size="3">🧍 ผู้ป่วย:</font></td><td><font color="#ecf0f1" size="3"><b>{name} (HN: {hn})</b></font></td></tr>
            <tr><td colspan="2"><br><font color="#d35400" size="3"><b>⚠️ ข้อบ่งชี้ / อาการทางคลินิก:</b></font></td></tr>
            <tr><td colspan="2"><font color="#bdc3c7" size="3">• {alert_data.get('message', '').replace('|', '<br>• ')}</font></td></tr>
            <tr><td colspan="2"><br><font color="#8c8c8c" size="3">⏰ เวลาประเมินเมื่อ:</font> <font color="#ecf0f1" size="3"><b>{time_str}</b></font></td></tr>
        </table>
        """
        
        msg_label = QLabel(html_content)
        msg_label.setTextFormat(Qt.TextFormat.RichText)
        msg_label.setWordWrap(True)
        
        # Dismiss button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        dismiss_btn = QPushButton("รับทราบ (Acknowledge)")
        dismiss_btn.setStyleSheet("""
            QPushButton {
                background-color: #34495e;
                color: white;
                border: 1px solid #7f8c8d;
                border-radius: 5px;
                padding: 5px 15px;
                font-family: Segoe UI;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
        """)
        dismiss_btn.clicked.connect(self.on_acknowledge_clicked)
        btn_layout.addWidget(dismiss_btn)
        
        container_layout.addWidget(title)
        container_layout.addWidget(msg_label)
        container_layout.addLayout(btn_layout)
        
        main_layout.addWidget(container)
        self.resize(380, 240)

    def show_toast(self):
        # Calculate position (bottom right above taskbar roughly)
        screen = self.screen().availableGeometry()
        x = screen.width() - self.width() - 20
        y = screen.height() - self.height() - 20
        self.move(x, y)
        self.show()

    def on_acknowledge_clicked(self):
        if self.alert_id is not None:
            self.acknowledge_signal.emit(self.alert_id)
        self.close()

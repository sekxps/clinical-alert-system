# CAS Desktop Client

Windows desktop tray application for the Clinical Alert System. Receives real-time clinical alerts from `cas-ws-dispatcher` and displays them as toast notifications on clinical workstations.

## Features

- System tray icon with live connection status
- Frameless, always-on-top toast notifications with patient details
- Severity-coded border colour (critical = red, warning = orange, info = blue)
- Per-workstation **Acknowledge** button — marks alert as seen in the database
- Auto-reconnects to the dispatcher if the connection is lost

## Setup

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env    # set CAS_WS_URL to your dispatcher address
python main.py
```

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `CAS_WS_URL` | ✅ | Full WebSocket URL of the dispatcher, e.g. `ws://10.0.1.X:8000/ws/alerts` |

## Requirements

- Windows 10 / 11
- Python 3.9+
- `cas-ws-dispatcher` must be running and reachable

## Running at Startup (Windows)

To launch the client automatically when a user logs in, simply right-click the system tray icon and check **"Run on Startup"**. The app will automatically configure the Windows Registry.

## Building Executable (.exe)

For easier distribution to multiple client machines without needing to install Python, you can compile the client into a single executable file:

1. Activate your virtual environment
2. Install PyInstaller:
   ```bash
   pip install pyinstaller
   ```
3. Run the build command:
   ```bash
   pyinstaller --noconsole --onefile --name "ClinicalAlert" main.py
   ```
4. The generated `ClinicalAlert.exe` will be located in the `dist/` directory.
5. To deploy, simply copy the `.exe` file along with your `.env` file to the target machine.

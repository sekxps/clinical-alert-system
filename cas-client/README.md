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

To launch the client automatically when a user logs in, create a shortcut to `main.py` (or a compiled `.exe`) in:

```
%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
```

# Clinical Alert System (CAS)

Real-time Clinical Alert System for hospital workstations. Provides immediate, actionable alerts to clinical staff with synchronized notifications across all connected clients.

## Architecture

```
 ┌─────────────────┐     SQL (batch)      ┌──────────────┐
 │   HIS Database  │◄─────────────────────│  cas-server  │
 │  (HOSxP/etc.)   │                      │  (Engine)    │
 └─────────────────┘                      └──────┬───────┘
                                                 │ HTTP POST /ws/dispatch
 ┌─────────────────┐     SQL (read/ack)   ┌──────▼───────────────┐
 │   CAS Database  │◄─────────────────────│  cas-ws-dispatcher   │
 │  (alerts, etc.) │                      │  (FastAPI + WS)      │
 └─────────────────┘                      └──────┬───────────────┘
                                                 │ ws://  (broadcast)
                                      ┌──────────▼──────────┐
                                      │     cas-client       │
                                      │  (PyQt6 tray app)    │
                                      │  [workstation 1..N]  │
                                      └─────────────────────┘
```

### Components

| Component | Description |
|---|---|
| **`cas-server`** | Core engine — polls HIS DB, evaluates clinical alert rules, dispatches alerts via WebSocket. |
| **`cas-ws-dispatcher`** | FastAPI WebSocket hub — manages client connections, enriches alerts with HIS metadata, persists acknowledgements. |
| **`cas-client`** | Windows desktop tray application — displays toast notifications, allows per-workstation acknowledgement. |

## Features

- **Synchronized Acknowledgement** — alerts dismissed on one workstation are cleared across all connected clients in real-time.
- **4-State Change Detection** — never spams alerts; intelligently detects `NOT_TO_NOT`, `NOT_TO_HIGH`, `HIGH_TO_HIGH`, `HIGH_TO_NOT` transitions per visit.
- **Batch SQL Engine** — single query per criteria eliminates N+1 patterns; keeps HIS DB load minimal.
- **Modular Alert Rules** — new clinical alert types (Sepsis, Stroke, etc.) added by inserting a row into the `criteria` table — no code changes needed.
- **LINE Notifications** — optional Morpromt API integration for LINE group alerts.

## Prerequisites

- Python **3.9+**
- MySQL / MariaDB access to both HIS and CAS databases
- Windows workstations for `cas-client`

## Setup Order

> Run the services in this order: **Dispatcher → Server → Client(s)**

### 1. CAS WebSocket Dispatcher (`cas-ws-dispatcher`)

```bash
cd cas-ws-dispatcher
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env          # then edit .env with your DB credentials
uvicorn server:app --host 0.0.0.0 --port 8000
```

### 2. CAS Server (`cas-server`)

```bash
cd cas-server
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env          # then edit .env with your DB credentials
python sql\schema.sql           # initialise CAS DB tables (run once)
python sql\seed.sql             # load default alert criteria (run once)
python run_server.py
```

### 3. CAS Client (`cas-client`)

Install on each clinical workstation:

```bash
cd cas-client
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env          # set CAS_WS_URL=ws://<dispatcher_ip>:8000/ws/alerts
python main.py
```

## Environment Variables Reference

### `cas-server/.env`

| Variable | Required | Description |
|---|---|---|
| `HIS_HOST` | ✅ | HIS database hostname/IP |
| `HIS_PORT` | ✅ | HIS database port (default `3306`) |
| `HIS_USER` | ✅ | HIS DB user — **must be READ-ONLY** |
| `HIS_PASSWORD` | ✅ | HIS DB password |
| `HIS_DATABASE` | ✅ | HIS database name |
| `CAS_HOST` | ✅ | CAS database hostname/IP |
| `CAS_PORT` | ✅ | CAS database port (default `3306`) |
| `CAS_USER` | ✅ | CAS DB user (needs full CRUD on cas_db) |
| `CAS_PASSWORD` | ✅ | CAS DB password |
| `CAS_DATABASE` | ✅ | CAS database name (default `cas_db`) |
| `POLL_INTERVAL_SEC` | ➖ | Polling interval in seconds (default `10`) |
| `WS_DISPATCH_URL` | ➖ | Dispatcher WebSocket URL (default `ws://localhost:8000/ws/dispatch`) |
| `MORPROMT_CLIENT_KEY` | ➖ | LINE Morpromt client key (optional) |
| `MORPROMT_SECRET_KEY` | ➖ | LINE Morpromt secret key (optional) |

### `cas-ws-dispatcher/.env`

Same `HIS_*` and `CAS_*` variables as above (no Morpromt keys needed here).

### `cas-client/.env`

| Variable | Required | Description |
|---|---|---|
| `CAS_WS_URL` | ✅ | WebSocket URL e.g. `ws://10.0.1.X:8000/ws/alerts` |

## Security Notes

- The HIS database account **must** have `SELECT`-only privileges.
- **Never commit `.env` files** — they are excluded via `.gitignore`.
- For sensitive environments, consider running the dispatcher behind a reverse proxy (Nginx/Caddy) with TLS (`wss://`).

## Database Maintenance

Run `cas-server/sql/housekeeping.sql` periodically (e.g. monthly via Task Scheduler) to prune old records and reclaim disk space.
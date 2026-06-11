# CAS WebSocket Dispatcher

Central WebSocket hub for the Clinical Alert System. Manages real-time connections between `cas-server` and all `cas-client` desktop instances.

## Responsibilities

- Maintains a persistent WebSocket connection pool for all connected desktop clients (`/ws/alerts`)
- On new client connection, sends the full backlog of unseen/unresolved alerts
- Polls the CAS database every 5 seconds and broadcasts newly-created alerts
- Enriches each alert with HIS patient metadata (name, HN, department, visit time)
- Handles client `acknowledge` actions and marks alerts as `seen` in the database
- Exposes a `GET /health` endpoint for uptime monitoring

## Setup

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env    # fill in your CAS_* and HIS_* credentials
uvicorn server:app --host 0.0.0.0 --port 8000
```

## Environment Variables

See `.env.example` for the full list of required variables.

| Variable | Description |
|---|---|
| `CAS_HOST` / `CAS_USER` / `CAS_PASSWORD` / `CAS_DATABASE` | CAS database connection |
| `HIS_HOST` / `HIS_USER` / `HIS_PASSWORD` / `HIS_DATABASE` | HIS database connection (read-only) |

## Endpoints

| Endpoint | Type | Description |
|---|---|---|
| `GET /health` | REST | Health check — returns status + connected client count |
| `WS /ws/alerts` | WebSocket | Client connection endpoint |

## WebSocket Protocol

**Server → Client messages:**

```json
{
  "action": "alert",
  "id": 42,
  "visit_id": "VN001234",
  "type": "MI Risk Screen (EKG Required)",
  "message": "เจ็บหน้าอก | BMI > 25",
  "timestamp": "2026-06-11T10:30:00",
  "patient_name": "สมชาย ใจดี",
  "patient_hn": "HN123456",
  "department": "อายุรกรรม",
  "vsttime": "09:15:00"
}
```

**Client → Server messages:**

```json
{ "action": "acknowledge", "id": 42 }
```

# Clinical Alert System (CAS) 🏥

A production-grade, background polling engine for Hospital Information Systems (HIS) designed to evaluate and dispatch clinical alerts based on real-time patient data.

## Features
- **Exhaustive Scan with Batch SQL**: Eliminates N+1 database queries. Scans the entire patient ward using a single batch query per criteria, keeping HIS database load practically zero.
- **Smart 4-State Detection (`cc_change_log`)**: Never spams alerts. It intelligently detects transitions (`NOT_TO_NOT`, `NOT_TO_HIGH`, `HIGH_TO_HIGH`, `HIGH_TO_NOT`).
- **Resilient Connection Pooling**: Utilizes `DBUtils.PooledDB` to maintain stable backend connections.
- **Multi-threaded Engine**: Uses `ThreadPoolExecutor` to handle complex evaluation math for dozens of criteria independently without blocking.

## Setup Instructions

### 1. Database Initialization
Copy the SQL scripts found in `/sql` into your CAS database management tool:
1. Run `schema.sql` to initialize tables.
2. Run `seed.sql` to populate the initial "MI Risk Screen" rule.
(*Note: Make sure to read `housekeeping.sql` for tips on clearing old data over time*).

### 2. Environment Setup
Rename `.env.example` to `.env` and fill in your hospital's specific HIS and CAS database credentials, WebSocket dispatcher URL, and (optionally) Morpromt LINE API keys.
**Security Note:** The HIS DB account should be restricted strictly to **Read-Only (SELECT)** privileges.

### 3. Installation
Ensure you have the required packages:
```bash
pip install -r requirements.txt
```

### 4. Running the Engine
Simply launch the server:
```bash
python run_server.py
```
*(The server defaults to checking for updates every 10 seconds. You can tune `POLL_INTERVAL_SEC` in `.env`)*

## Extending (API / Line Notify)
To send notifications outwards to a specific Line Notify or GUI API frontend, insert your custom REST payload functions directly into the `fire_alert()` block within `alert.py`.

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---|---|---|
| Server exits immediately on start | Missing env vars | Check `.env` matches `.env.example` exactly |
| `No active criteria found` warning | `criteria` table empty | Run `sql/seed.sql` on the CAS database |
| HIS queries return 0 visits | Wrong date / DB connection | Verify `HIS_DATABASE` and run `python check_db.py` |
| LINE alerts not sent | Morpromt keys missing or wrong | Check `MORPROMT_CLIENT_KEY` / `MORPROMT_SECRET_KEY` in `.env` |
| High CPU / DB load | `POLL_INTERVAL_SEC` too low | Increase to `30` or `60` seconds |

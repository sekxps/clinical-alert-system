# Clinical Alert System (CAS)

Real-time Clinical Alert System for hospital workstations. This system is designed to provide immediate, actionable alerts to clinical staff, ensuring synchronized notifications across multiple clients.

## Architecture

This repository is structured as a monorepo containing three core components:

*   **`cas-server`**: The central backend engine. It connects to the HIS database, fetches real-time patient metadata, processes alert rules (Modular Clinical Alert Engine), and handles the core business logic.
*   **`cas-ws-dispatcher`**: The WebSocket dispatcher service responsible for managing real-time connections with clients. It broadcasts alerts and synchronizes state (such as cross-client "Acknowledge" dismissals).
*   **`cas-client`**: The desktop notification client application installed on hospital workstations. It displays formatted alerts (similar to LINE alerts) and allows users to interact with and acknowledge them.

## Features

*   **Synchronized Acknowledgement**: Alerts dismissed on one workstation are automatically cleared across all connected clients in real-time.
*   **Modular Alert Engine**: Extensible architecture designed to easily plug in new clinical alert types (e.g., MI EKG, Sepsis, Stroke) via `BaseAlertRule` class and modular notification handlers.
*   **Real-time Patient Metadata**: Detailed information fetched directly from the HIS database ensuring rich and actionable desktop notifications.
*   **Centralized Configuration**: Clean, production-ready codebase using a unified monorepo structure.

## Getting Started

### Prerequisites

Ensure you have Python 3.8+ installed. It's recommended to use virtual environments (`venv`) for each subsystem.

### 1. CAS WebSocket Dispatcher (`cas-ws-dispatcher`)

This service manages the real-time connections. Run this first.

```bash
cd cas-ws-dispatcher
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 8000
```

### 2. CAS Server (`cas-server`)

The core engine that polls the HIS database and triggers alerts.

```bash
cd cas-server
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
# Make sure to configure your .env file here based on .env.example
python run_server.py
```

### 3. CAS Client (`cas-client`)

The desktop client that receives notifications.

```bash
cd cas-client
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py
```
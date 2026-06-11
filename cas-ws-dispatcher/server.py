import sys
import logging
from contextlib import asynccontextmanager
import asyncio
import json
import aiomysql
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from database import setup_cas_pool, setup_his_pool, get_pool, get_his_pool

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Logging Configuration
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)


# ---------------------------------------------------------------------------
# Application Lifespan (replaces deprecated @app.on_event("startup"))
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: initialise DB pools and kick off the background polling task."""
    await setup_cas_pool()
    await setup_his_pool()
    task = asyncio.create_task(poll_database_for_alerts())
    logger.info("CAS WebSocket Dispatcher started.")
    yield
    task.cancel()
    logger.info("CAS WebSocket Dispatcher stopped.")


app = FastAPI(title="CAS WebSocket Dispatcher", lifespan=lifespan)


# ---------------------------------------------------------------------------
# Connection Manager
# ---------------------------------------------------------------------------
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(
            f"Client connected: {websocket.client}. "
            f"Total connections: {len(self.active_connections)}"
        )
        # Send backlog of unseen, unresolved alerts to the newly-connected client
        pool = get_pool()
        his_pool = get_his_pool()
        if pool:
            try:
                async with pool.acquire() as conn:
                    async with conn.cursor(aiomysql.DictCursor) as cur:
                        query = """
                            SELECT a.id, a.visit_id, c.name AS type,
                                   a.detail AS message, a.alerted_at AS timestamp
                            FROM alerts a
                            JOIN criteria c ON a.criteria_id = c.id
                            WHERE a.seen = 0 
                              AND a.resolved_at IS NULL
                              AND a.alerted_at >= NOW() - INTERVAL 24 HOUR
                            ORDER BY a.id ASC
                        """
                        await cur.execute(query)
                        alerts = await cur.fetchall()
                        for alert in alerts:
                            if alert.get("timestamp"):
                                alert["timestamp"] = alert["timestamp"].isoformat()
                            await attach_his_metadata(alert, his_pool)
                            alert["action"] = "alert"
                            await websocket.send_text(json.dumps(alert, default=str))
                logger.info(
                    f"Sent {len(alerts)} backlog alert(s) to new client {websocket.client}."
                )
            except Exception:
                logger.exception(f"Error sending backlog to client {websocket.client}.")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(
                f"Client disconnected: {websocket.client}. "
                f"Remaining connections: {len(self.active_connections)}"
            )

    async def broadcast(self, message: dict):
        """Broadcast a message to all connected clients, pruning dead connections."""
        dead: list[WebSocket] = []
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message, default=str))
            except Exception:
                logger.warning(
                    f"Failed to send to client {connection.client} — marking for removal."
                )
                dead.append(connection)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()


# ---------------------------------------------------------------------------
# HIS Metadata Enrichment
# ---------------------------------------------------------------------------
async def attach_his_metadata(alert: dict, his_pool) -> None:
    """Enrich an alert dict with patient metadata from the HIS database."""
    alert.setdefault("patient_name", "-")
    alert.setdefault("patient_hn", "-")
    alert.setdefault("department", "ไม่ระบุ")
    alert.setdefault("vsttime", "-")

    if not his_pool or "visit_id" not in alert:
        return

    try:
        async with his_pool.acquire() as h_conn:
            async with h_conn.cursor(aiomysql.DictCursor) as h_cur:
                q = """
                    SELECT CONCAT(PT.pname, PT.fname, ' ', PT.lname) AS patient_name,
                           VS.hn, OV.vsttime, SP.name AS department_name
                    FROM vn_stat VS
                    LEFT JOIN patient PT ON PT.hn = VS.hn
                    LEFT JOIN ovst OV ON OV.vn = VS.vn
                    LEFT JOIN spclty SP ON SP.spclty = VS.spclty
                    WHERE VS.vn = %s
                """
                await h_cur.execute(q, (alert["visit_id"],))
                res = await h_cur.fetchone()
                if res:
                    alert["patient_name"] = res.get("patient_name") or "-"
                    alert["patient_hn"] = res.get("hn") or "-"
                    alert["department"] = res.get("department_name") or "ไม่ระบุ"
                    alert["vsttime"] = str(res.get("vsttime")) if res.get("vsttime") else "-"
    except Exception:
        logger.exception(f"Error fetching HIS metadata for visit_id={alert.get('visit_id')}.")


# ---------------------------------------------------------------------------
# Background Database Polling
# ---------------------------------------------------------------------------
async def poll_database_for_alerts():
    """Poll the CAS database every 5 s and broadcast new alerts to all clients."""
    last_processed_id = 0
    poll_interval = 5

    while True:
        try:
            pool = get_pool()
            his_pool = get_his_pool()
            if pool:
                async with pool.acquire() as conn:
                    async with conn.cursor(aiomysql.DictCursor) as cur:
                        query = """
                            SELECT a.id, a.visit_id, c.name AS type,
                                   a.detail AS message, a.alerted_at AS timestamp
                            FROM alerts a
                            JOIN criteria c ON a.criteria_id = c.id
                            WHERE a.id > %s AND a.seen = 0
                            ORDER BY a.id ASC
                        """
                        await cur.execute(query, (last_processed_id,))
                        new_alerts = await cur.fetchall()

                        for alert in new_alerts:
                            if alert.get("timestamp"):
                                alert["timestamp"] = alert["timestamp"].isoformat()
                            await attach_his_metadata(alert, his_pool)
                            alert["action"] = "alert"

                            logger.info(
                                f"Broadcasting alert id={alert['id']} "
                                f"type={alert['type']} hn={alert['patient_hn']}"
                            )
                            await manager.broadcast(alert)
                            last_processed_id = max(last_processed_id, alert["id"])
        except asyncio.CancelledError:
            logger.info("Polling task cancelled — shutting down.")
            raise
        except Exception:
            logger.exception("Error during database polling — will retry next interval.")

        await asyncio.sleep(poll_interval)


# ---------------------------------------------------------------------------
# WebSocket Endpoint
# ---------------------------------------------------------------------------
@app.websocket("/ws/alerts")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                payload = json.loads(data)
                if payload.get("action") == "acknowledge":
                    alert_id = payload.get("id")
                    if alert_id is not None:
                        pool = get_pool()
                        if pool:
                            async with pool.acquire() as conn:
                                async with conn.cursor() as cur:
                                    await cur.execute(
                                        "UPDATE alerts SET seen = 1 WHERE id = %s",
                                        (int(alert_id),),
                                    )
                            logger.info(f"Alert id={alert_id} acknowledged.")
            except (json.JSONDecodeError, ValueError, TypeError):
                logger.warning(f"Received invalid payload from {websocket.client}: {data!r}")
            except Exception:
                logger.exception(f"Error handling message from {websocket.client}.")
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------
@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "connected_clients": len(manager.active_connections),
    }

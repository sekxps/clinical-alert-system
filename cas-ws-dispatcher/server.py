from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import asyncio
from typing import List
import json
import aiomysql
from datetime import datetime

app = FastAPI()

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        # Send history / backlog of unseen alerts to the newly connected client
        from database import get_pool, get_his_pool
        pool = get_pool()
        his_pool = get_his_pool()
        if pool:
            try:
                async with pool.acquire() as conn:
                    async with conn.cursor(aiomysql.DictCursor) as cur:
                        query = """
                            SELECT a.id, a.visit_id, c.name as type, 
                                   a.detail as message, a.alerted_at as timestamp 
                            FROM alerts a
                            JOIN criteria c ON a.criteria_id = c.id
                            WHERE a.seen = 0
                            ORDER BY a.id ASC
                        """
                        await cur.execute(query)
                        alerts = await cur.fetchall()
                        for alert in alerts:
                            if 'timestamp' in alert and alert['timestamp']:
                                alert['timestamp'] = alert['timestamp'].isoformat()
                            
                            await attach_his_metadata(alert, his_pool)
                            alert['action'] = 'alert'
                            await websocket.send_text(json.dumps(alert))
            except Exception as e:
                print(f"Error fetching backlog on connection: {e}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except Exception:
                pass

async def attach_his_metadata(alert: dict, his_pool):
    import aiomysql
    alert['patient_name'] = '-'
    alert['patient_hn'] = '-'
    alert['department'] = 'ไม่ระบุ'
    alert['vsttime'] = '-'
    
    if not his_pool or 'visit_id' not in alert:
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
                await h_cur.execute(q, (alert['visit_id'],))
                res = await h_cur.fetchone()
                if res:
                    alert['patient_name'] = res.get('patient_name') or '-'
                    alert['patient_hn'] = res.get('hn') or '-'
                    alert['department'] = res.get('department_name') or 'ไม่ระบุ'
                    alert['vsttime'] = str(res.get('vsttime')) if res.get('vsttime') else '-'
    except Exception as e:
        print(f"Error fetching HIS metadata: {e}")

manager = ConnectionManager()

@app.on_event("startup")
async def startup_event():
    from database import setup_cas_pool, setup_his_pool
    await setup_cas_pool()
    await setup_his_pool()
    asyncio.create_task(poll_database_for_alerts())

async def poll_database_for_alerts():
    """Polls the CAS database for new alerts to broadcast"""
    from database import get_pool, get_his_pool
    last_processed_id = 0
    poll_interval = 5  # Check every 5 seconds
    
    while True:
        try:
            pool = get_pool()
            his_pool = get_his_pool()
            if pool:
                async with pool.acquire() as conn:
                    async with conn.cursor(aiomysql.DictCursor) as cur:
                        query = """
                            SELECT a.id, a.visit_id, c.name as type, 
                                   a.detail as message, a.alerted_at as timestamp 
                            FROM alerts a
                            JOIN criteria c ON a.criteria_id = c.id
                            WHERE a.id > %s AND a.seen = 0
                            ORDER BY a.id ASC
                        """
                        await cur.execute(query, (last_processed_id,))
                        new_alerts = await cur.fetchall()
                        
                        for alert in new_alerts:
                            # Convert datetime back to ISO format string
                            if 'timestamp' in alert and alert['timestamp']:
                                alert['timestamp'] = alert['timestamp'].isoformat()
                                
                            await attach_his_metadata(alert, his_pool)
                            alert['action'] = 'alert'
                                
                            print(f"Broadcasting new alert: {alert['type']} for HN {alert['patient_hn']}")
                            await manager.broadcast(alert)
                            
                            # Update our pointer logic
                            last_processed_id = max(last_processed_id, alert['id'])
        except Exception as e:
            print(f"Error polling database: {e}")
            
        await asyncio.sleep(poll_interval)

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
                    if alert_id:
                        from database import get_pool
                        import aiomysql
                        pool = get_pool()
                        if pool:
                            async with pool.acquire() as conn:
                                async with conn.cursor() as cur:
                                    await cur.execute(
                                        "UPDATE alerts SET seen = 1, resolved_at = NOW() WHERE id = %s",
                                        (alert_id,)
                                    )
                        print(f"Acknowledged alert ID: {alert_id}")
                        # Removed dismiss broadcast so other machines keep their popups
            except Exception as e:
                print(f"Error handling client message: {e}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)

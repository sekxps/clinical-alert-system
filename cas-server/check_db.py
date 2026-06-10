import sys
from db import get_cas_conn

def check():
    with get_cas_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, visit_id, criteria_id, old_risk, new_risk, change_type, created_at FROM cc_change_log ORDER BY id DESC LIMIT 20")
            print("--- cc_change_log (last 20) ---")
            for row in cur.fetchall():
                print(row)
                
            cur.execute("SELECT id, visit_id, criteria_id, detail, alerted_at, resolved_at FROM alerts ORDER BY alerted_at DESC LIMIT 20")
            print("\n--- alerts (last 20 updated) ---")
            for row in cur.fetchall():
                print(row)
                
            cur.execute("SELECT id, name, query FROM criteria WHERE active = 1")
            print("\n--- active criteria ---")
            for row in cur.fetchall():
                print(row)
                
            cur.execute("SELECT NOW()")
            print("\n--- MySQL NOW() ---")
            print(cur.fetchall())
            
            import datetime
            print("\n--- Python datetime.now() ---")
            print(datetime.datetime.now())
            
            cur.execute("DESCRIBE alerts")
            print("\n--- DESCRIBE alerts ---")
            for row in cur.fetchall():
                print(row)

if __name__ == "__main__":
    check()

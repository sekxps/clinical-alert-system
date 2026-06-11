import asyncio
import os
from dotenv import load_dotenv
import aiomysql

# Load env vars
load_dotenv()

DB_CAS_HOST = os.getenv("DB_CAS_HOST", "localhost")
DB_CAS_USER = os.getenv("DB_CAS_USER", "cas_user")
DB_CAS_PASS = os.getenv("DB_CAS_PASS", "cas_password")
DB_CAS_NAME = os.getenv("DB_CAS_NAME", "cas")

async def test_cast():
    print("Connecting to CAS Database...")
    try:
        conn = await aiomysql.connect(
            host=DB_CAS_HOST,
            user=DB_CAS_USER,
            password=DB_CAS_PASS,
            db=DB_CAS_NAME,
            charset='utf8mb4'
        )
        async with conn.cursor() as cur:
            # Check if criteria exists, use criteria 1 as fallback
            await cur.execute("SELECT id FROM criteria LIMIT 1")
            res = await cur.fetchone()
            criteria_id = res[0] if res else 1

            query = """
                INSERT INTO alerts (visit_id, criteria_id, detail, seen)
                VALUES (%s, %s, %s, 0)
            """
            print(f"Injecting test alert (visit_id='0000000', criteria_id={criteria_id})...")
            await cur.execute(query, ("0000000", criteria_id, "นี่คือการทดสอบแจ้งเตือนจาก Script ทดสอบ (Test Cast)"))
            await conn.commit()
            print("✅ Test alert successfully injected into database!")
            print("💡 The dispatcher should pick it up within 5 seconds and broadcast it to all clients.")
        conn.close()
    except Exception as e:
        print(f"❌ Error injecting test alert: {e}")

if __name__ == "__main__":
    asyncio.run(test_cast())

import os
from pathlib import Path
import aiomysql
from dotenv import load_dotenv

# Load .env from the main CAS folder
env_path = Path(__file__).parent.parent / "cas" / ".env"
load_dotenv(dotenv_path=env_path)

pool = None
his_pool = None

async def setup_cas_pool():
    global pool
    pool = await aiomysql.create_pool(
        host=os.getenv("CAS_HOST", "localhost"),
        port=int(os.getenv("CAS_PORT", "3306")),
        user=os.getenv("CAS_USER", "root"),
        password=os.getenv("CAS_PASSWORD", ""),
        db=os.getenv("CAS_DATABASE", "cas_db"),
        autocommit=True,
    )
    print("Connected to CAS MySQL database")
    return pool

async def setup_his_pool():
    global his_pool
    his_pool = await aiomysql.create_pool(
        host=os.getenv("HIS_HOST", "localhost"),
        port=int(os.getenv("HIS_PORT", "3306")),
        user=os.getenv("HIS_USER", "cas_readonly"),
        password=os.getenv("HIS_PASSWORD", ""),
        db=os.getenv("HIS_DATABASE", "his_db"),
        autocommit=True,
    )
    print("Connected to HIS MySQL database")
    return his_pool

def get_pool():
    return pool

def get_his_pool():
    return his_pool

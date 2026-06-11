import os
import logging
from pathlib import Path
import aiomysql
from dotenv import load_dotenv

# Load .env from the cas-ws-dispatcher folder
load_dotenv(dotenv_path=Path(__file__).parent / ".env")

logger = logging.getLogger(__name__)

pool = None
his_pool = None


async def setup_cas_pool():
    """Create the async connection pool for the CAS database."""
    global pool
    try:
        pool = await aiomysql.create_pool(
            host=os.getenv("CAS_HOST", "localhost"),
            port=int(os.getenv("CAS_PORT", "3306")),
            user=os.getenv("CAS_USER", "cas_user"),
            password=os.getenv("CAS_PASSWORD", ""),
            db=os.getenv("CAS_DATABASE", "cas_db"),
            charset="utf8mb4",
            autocommit=True,
        )
        logger.info("Connected to CAS MySQL database.")
    except Exception:
        logger.exception("Failed to create CAS connection pool — check CAS_* env vars.")
        raise
    return pool


async def setup_his_pool():
    """Create the async connection pool for the HIS database."""
    global his_pool
    try:
        his_pool = await aiomysql.create_pool(
            host=os.getenv("HIS_HOST", "localhost"),
            port=int(os.getenv("HIS_PORT", "3306")),
            user=os.getenv("HIS_USER", "cas_readonly"),
            password=os.getenv("HIS_PASSWORD", ""),
            db=os.getenv("HIS_DATABASE", "his_db"),
            charset="utf8mb4",
            autocommit=True,
        )
        logger.info("Connected to HIS MySQL database.")
    except Exception:
        logger.exception("Failed to create HIS connection pool — check HIS_* env vars.")
        raise
    return his_pool


def get_pool():
    return pool


def get_his_pool():
    return his_pool

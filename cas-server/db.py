import logging
import pymysql
from pymysql.cursors import DictCursor
from dbutils.pooled_db import PooledDB
from contextlib import contextmanager
from config import HIS_DB, CAS_DB

logger = logging.getLogger(__name__)

# Production-grade Connection Pools
his_pool = PooledDB(
    creator=pymysql,
    maxconnections=20,
    mincached=2,
    blocking=True,
    cursorclass=DictCursor,
    **HIS_DB
)

cas_pool = PooledDB(
    creator=pymysql,
    maxconnections=20,
    mincached=2,
    blocking=True,
    cursorclass=DictCursor,
    **CAS_DB
)

@contextmanager
def get_his_conn():
    """Context manager for HIS database connection (via Thread-safe Pool)."""
    conn = his_pool.connection()
    try:
        yield conn
    finally:
        conn.close()

@contextmanager
def get_cas_conn():
    """Context manager for CAS database connection (via Thread-safe Pool)."""
    conn = cas_pool.connection()
    try:
        yield conn
    finally:
        conn.close()

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Project Paths
PROJECT_ROOT = Path(__file__).resolve().parent
LOG_DIR = PROJECT_ROOT / "logs"

# HIS (Hospital Information System) Database
HIS_DB = {
    "host": os.getenv("HIS_HOST", "localhost"),
    "port": int(os.getenv("HIS_PORT", "3306")),
    "user": os.getenv("HIS_USER", "cas_readonly"),
    "password": os.getenv("HIS_PASSWORD", ""),
    "database": os.getenv("HIS_DATABASE", "his_db"),
    "charset": "utf8mb4",
    "autocommit": True,
}

# CAS (Clinical Alert System) Database
CAS_DB = {
    "host": os.getenv("CAS_HOST", "localhost"),
    "port": int(os.getenv("CAS_PORT", "3306")),
    "user": os.getenv("CAS_USER", "root"),
    "password": os.getenv("CAS_PASSWORD", ""),
    "database": os.getenv("CAS_DATABASE", "cas_db"),
    "charset": "utf8mb4",
    "autocommit": True,
}

# Polling Settings
POLL_INTERVAL_SEC = int(os.getenv("POLL_INTERVAL_SEC", "10"))

# Morpromt LINE API
MORPROMT_CLIENT_KEY = os.getenv("MORPROMT_CLIENT_KEY", "")
MORPROMT_SECRET_KEY = os.getenv("MORPROMT_SECRET_KEY", "")

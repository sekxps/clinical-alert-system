import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from the same directory as this script
load_dotenv(dotenv_path=Path(__file__).parent / ".env")

logger = logging.getLogger(__name__)

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
    "user": os.getenv("CAS_USER", "cas_user"),
    "password": os.getenv("CAS_PASSWORD", ""),
    "database": os.getenv("CAS_DATABASE", "cas_db"),
    "charset": "utf8mb4",
    "autocommit": True,
}

# Polling Settings
POLL_INTERVAL_SEC = int(os.getenv("POLL_INTERVAL_SEC", "10"))

# WebSocket Dispatcher URL
WS_DISPATCH_URL = os.getenv("WS_DISPATCH_URL", "ws://localhost:8000/ws/dispatch")

# Morpromt LINE API
MORPROMT_CLIENT_KEY = os.getenv("MORPROMT_CLIENT_KEY", "")
MORPROMT_SECRET_KEY = os.getenv("MORPROMT_SECRET_KEY", "")


def validate_config() -> bool:
    """Validate that required environment variables are set. Returns True if all OK."""
    required_vars = [
        ("HIS_HOST", os.getenv("HIS_HOST")),
        ("HIS_USER", os.getenv("HIS_USER")),
        ("HIS_PASSWORD", os.getenv("HIS_PASSWORD")),
        ("HIS_DATABASE", os.getenv("HIS_DATABASE")),
        ("CAS_HOST", os.getenv("CAS_HOST")),
        ("CAS_USER", os.getenv("CAS_USER")),
        ("CAS_PASSWORD", os.getenv("CAS_PASSWORD")),
        ("CAS_DATABASE", os.getenv("CAS_DATABASE")),
    ]
    missing = [name for name, val in required_vars if not val]
    if missing:
        logger.critical(
            f"Missing required environment variables: {', '.join(missing)}. "
            "Please check your .env file (refer to .env.example for guidance)."
        )
        return False

    if not MORPROMT_CLIENT_KEY or not MORPROMT_SECRET_KEY:
        logger.warning(
            "MORPROMT_CLIENT_KEY / MORPROMT_SECRET_KEY not set — LINE alerts will be disabled."
        )

    return True

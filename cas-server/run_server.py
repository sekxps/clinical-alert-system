import sys
import time
import logging
import logging.handlers
from config import LOG_DIR, POLL_INTERVAL_SEC, validate_config
from engine import ClinicalAlertEngine

# Ensure Thai characters display correctly in Windows terminal
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ---------------------------------------------------------------------------
# Logging Setup
# ---------------------------------------------------------------------------
LOG_DIR.mkdir(parents=True, exist_ok=True)
log_file = LOG_DIR / "cas_server.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.handlers.TimedRotatingFileHandler(
            str(log_file),
            when="midnight",
            interval=1,
            backupCount=30,
            encoding="utf-8",
        ),
    ],
)
logger = logging.getLogger("CAS_Entry")


def main():
    logger.info("=" * 60)
    logger.info("  CLINICAL ALERT SYSTEM (CAS) — SERVER STARTING")
    logger.info(f"  Poll interval : every {POLL_INTERVAL_SEC} second(s)")
    logger.info("=" * 60)

    # Validate configuration before connecting to any database
    if not validate_config():
        logger.critical("Configuration validation failed — server will not start.")
        sys.exit(1)

    engine = ClinicalAlertEngine()

    cycle = 0
    while True:
        cycle += 1
        logger.info(f"--- Cycle {cycle} ---")
        try:
            engine.run_cycle()
        except KeyboardInterrupt:
            raise
        except Exception:
            logger.exception("Unexpected error in main loop — continuing after sleep.")

        logger.info(f"Sleeping for {POLL_INTERVAL_SEC}s...")
        time.sleep(POLL_INTERVAL_SEC)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("System stopped by user (Ctrl+C).")
        sys.exit(0)

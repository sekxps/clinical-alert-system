import logging
import hashlib
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from db import get_his_conn, get_cas_conn
from alert import fire_alert

logger = logging.getLogger(__name__)


def compute_hash(text) -> str:
    """Compute a SHA-256 hash of the given text for change detection."""
    if not text:
        return ""
    return hashlib.sha256(str(text).encode("utf-8")).hexdigest()


class ClinicalAlertEngine:
    def run_cycle(self):
        """Execute one polling cycle: fetch visits, evaluate all active criteria in parallel."""
        logger.info("Cycle started.")

        try:
            with get_his_conn() as his_conn, get_cas_conn() as cas_conn:
                visits = self._fetch_visits(his_conn)
                logger.info(f"Fetched {len(visits)} visit(s) from HIS.")

                criteria_list = self._fetch_criteria(cas_conn)
                if not criteria_list:
                    logger.warning("No active criteria found in CAS DB — skipping cycle.")
                    return

                known_cc_hashes = self._fetch_known_cc_hashes(cas_conn)

            # Evaluate each criterion in a separate thread
            errors = []
            with ThreadPoolExecutor(max_workers=min(10, len(criteria_list))) as executor:
                futures = {
                    executor.submit(
                        self._evaluate_criteria_multithreaded, visits, criteria, known_cc_hashes
                    ): criteria["name"]
                    for criteria in criteria_list
                }
                for future, name in futures.items():
                    try:
                        future.result()
                    except Exception:
                        logger.exception(f"Criteria thread failed for '{name}'.")
                        errors.append(name)

            if errors:
                logger.warning(f"{len(errors)} criteria thread(s) failed: {errors}")

            # Persist updated CC hashes for all visited patients
            with get_cas_conn() as cas_conn:
                for visit in visits:
                    v_id   = visit["visit_id"]
                    c_hash = compute_hash(visit["cc"])
                    if known_cc_hashes.get(v_id) != c_hash:
                        self._upsert_cc_hash(cas_conn, v_id, c_hash)

        except Exception:
            logger.exception("Unhandled error during polling cycle.")

    # -------------------------------------------------------------------------
    # HIS Data Fetching
    # -------------------------------------------------------------------------

    def _fetch_visits(self, his_conn) -> list:
        """Fetch today's visits that have a non-empty Chief Complaint from HIS."""
        sql = """
            SELECT VS.vn AS visit_id, OS.cc
            FROM vn_stat VS
            LEFT JOIN opdscreen OS ON OS.vn = VS.vn
            WHERE VS.vstdate = CURDATE()
              AND OS.cc IS NOT NULL
              AND OS.cc != ''
        """
        with his_conn.cursor() as cursor:
            cursor.execute(sql)
            return cursor.fetchall()

    # -------------------------------------------------------------------------
    # CAS Data Fetching
    # -------------------------------------------------------------------------

    def _fetch_criteria(self, cas_conn) -> list:
        """Fetch all active clinical alert criteria from the CAS database."""
        sql = """
            SELECT id, name, category, query, severity, cooldown_min
            FROM criteria
            WHERE active = 1
        """
        with cas_conn.cursor() as cursor:
            cursor.execute(sql)
            return cursor.fetchall()

    def _fetch_known_cc_hashes(self, cas_conn) -> dict:
        """
        Fetch CC hashes only for today's visits.
        Using a subquery avoids loading the entire (unbounded) table into memory.
        """
        sql = """
            SELECT visit_id, cc_hash
            FROM visit_cc_hashes
            WHERE updated_at >= CURDATE()
        """
        with cas_conn.cursor() as cursor:
            cursor.execute(sql)
            rows = cursor.fetchall()
            return {r["visit_id"]: r["cc_hash"] for r in rows}

    # -------------------------------------------------------------------------
    # Criteria Evaluation (runs in a worker thread)
    # -------------------------------------------------------------------------

    def _evaluate_criteria_multithreaded(self, visits: list, criteria: dict, known_cc_hashes: dict):
        """Worker thread: execute the criteria SQL and run the 4-state engine for each visit."""
        try:
            with get_his_conn() as his_conn, get_cas_conn() as cas_conn:
                raw_query = criteria["query"]

                # BATCH MODE: single SQL scans all today's patients at once
                if ":visit_id" not in raw_query:
                    with his_conn.cursor() as cursor:
                        cursor.execute(raw_query)
                        results = cursor.fetchall()

                    batch_results = {str(r["visit_id"]): r for r in results}

                    for visit in visits:
                        visit_id        = visit["visit_id"]
                        current_cc_hash = compute_hash(visit["cc"])
                        old_cc_hash     = known_cc_hashes.get(visit_id)

                        res = batch_results.get(visit_id)
                        if not res:
                            continue

                        self._process_single_result(
                            cas_conn, visit_id, criteria, res, old_cc_hash, current_cc_hash
                        )

                # SINGLE MODE: legacy per-visit query (N queries)
                else:
                    safe_query = raw_query.replace("%", "%%").replace(":visit_id", "%s")
                    for visit in visits:
                        visit_id        = visit["visit_id"]
                        current_cc_hash = compute_hash(visit["cc"])
                        old_cc_hash     = known_cc_hashes.get(visit_id)

                        with his_conn.cursor() as cursor:
                            cursor.execute(safe_query, (visit_id,))
                            res = cursor.fetchone()

                        if not res:
                            continue

                        self._process_single_result(
                            cas_conn, visit_id, criteria, res, old_cc_hash, current_cc_hash
                        )

        except Exception:
            logger.exception(f"Thread error evaluating criteria '{criteria['name']}'.")
            raise  # Re-raise so the future captures it

    # -------------------------------------------------------------------------
    # 4-State Alert Logic
    # -------------------------------------------------------------------------

    def _process_single_result(
        self, cas_conn, visit_id, criteria: dict, result: dict,
        old_cc_hash, new_cc_hash
    ):
        """
        Resolve the 4-state CC-change logic:
          NOT_TO_NOT   — no action
          NOT_TO_HIGH  — insert/update alert, fire notification
          HIGH_TO_HIGH — update alert silently (no re-notification)
          HIGH_TO_NOT  — resolve alert, fire cancellation notification
        """
        criteria_id = criteria["id"]

        new_risk        = int(result.get("is_alert", 0))
        detail          = result.get("detail")
        new_detail_hash = compute_hash(detail)

        existing = self._get_existing_alert(cas_conn, visit_id, criteria_id)
        old_risk = 1 if existing and existing["resolved_at"] is None else 0

        cc_changed     = old_cc_hash != new_cc_hash
        detail_changed = existing is None or existing.get("detail_hash") != new_detail_hash

        metadata = {k: v for k, v in result.items() if k not in ("visit_id", "is_alert", "detail")}

        # First-ever visit: no previous CC hash tracked
        if old_cc_hash is None:
            if new_risk == 1 and existing is None:
                self._insert_alert(cas_conn, visit_id, criteria, detail, new_detail_hash)
                self._fire_alert_wrapper(visit_id, criteria, detail, "NOT_TO_HIGH", metadata)
            return

        change_type = f"{'HIGH' if old_risk else 'NOT'}_TO_{'HIGH' if new_risk else 'NOT'}"

        if change_type == "NOT_TO_NOT":
            pass

        elif change_type == "NOT_TO_HIGH":
            self._log_cc_change(
                cas_conn, visit_id, criteria_id, old_cc_hash, new_cc_hash, old_risk, new_risk, change_type
            )
            if existing is None:
                self._insert_alert(cas_conn, visit_id, criteria, detail, new_detail_hash)
            else:
                self._update_alert(cas_conn, existing["id"], detail, new_detail_hash)
            self._fire_alert_wrapper(visit_id, criteria, detail, change_type, metadata)

        elif change_type == "HIGH_TO_HIGH":
            if cc_changed or detail_changed:
                self._log_cc_change(
                    cas_conn, visit_id, criteria_id, old_cc_hash, new_cc_hash, old_risk, new_risk, change_type
                )
                self._update_alert(cas_conn, existing["id"], detail, new_detail_hash)
                # ไม่ส่ง LINE ซ้ำสำหรับ HIGH_TO_HIGH — อัปเดต DB เก็บข้อมูลไว้เท่านั้น

        elif change_type == "HIGH_TO_NOT":
            self._log_cc_change(
                cas_conn, visit_id, criteria_id, old_cc_hash, new_cc_hash, old_risk, new_risk, change_type
            )
            self._resolve_alert(cas_conn, existing["id"])
            self._fire_alert_wrapper(
                visit_id, criteria,
                "Patient no longer meets criteria (data was deleted/resolved)",
                change_type, metadata,
            )

    # -------------------------------------------------------------------------
    # Database Operations
    # -------------------------------------------------------------------------

    def _get_existing_alert(self, cas_conn, visit_id, criteria_id):
        sql = """
            SELECT id, detail_hash, alerted_at, resolved_at
            FROM alerts
            WHERE visit_id = %s AND criteria_id = %s
        """
        with cas_conn.cursor() as cursor:
            cursor.execute(sql, (visit_id, criteria_id))
            return cursor.fetchone()

    def _insert_alert(self, cas_conn, visit_id, criteria: dict, detail, detail_hash):
        sql = """
            INSERT INTO alerts (visit_id, criteria_id, detail, detail_hash, severity)
            VALUES (%s, %s, %s, %s, %s)
        """
        with cas_conn.cursor() as cursor:
            cursor.execute(sql, (visit_id, criteria["id"], detail, detail_hash, criteria["severity"]))

    def _update_alert(self, cas_conn, alert_id, detail, detail_hash):
        sql = """
            UPDATE alerts
            SET detail = %s, detail_hash = %s, alerted_at = NOW(), resolved_at = NULL
            WHERE id = %s
        """
        with cas_conn.cursor() as cursor:
            cursor.execute(sql, (detail, detail_hash, alert_id))

    def _resolve_alert(self, cas_conn, alert_id):
        sql = "UPDATE alerts SET resolved_at = NOW() WHERE id = %s"
        with cas_conn.cursor() as cursor:
            cursor.execute(sql, (alert_id,))

    def _upsert_cc_hash(self, cas_conn, visit_id, cc_hash):
        sql = """
            INSERT INTO visit_cc_hashes (visit_id, cc_hash)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE
                cc_hash    = VALUES(cc_hash),
                updated_at = NOW()
        """
        with cas_conn.cursor() as cursor:
            cursor.execute(sql, (visit_id, cc_hash))

    def _log_cc_change(
        self, cas_conn, visit_id, criteria_id,
        old_cc_hash, new_cc_hash, old_risk, new_risk, change_type
    ):
        """Write an audit record for every CC risk-state transition."""
        sql = """
            INSERT INTO cc_change_log
                (visit_id, criteria_id, old_cc_hash, new_cc_hash, old_risk, new_risk, change_type)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        with cas_conn.cursor() as cursor:
            cursor.execute(
                sql, (visit_id, criteria_id, old_cc_hash, new_cc_hash, old_risk, new_risk, change_type)
            )

    # -------------------------------------------------------------------------
    # Alert Dispatch
    # -------------------------------------------------------------------------

    def _fire_alert_wrapper(
        self, visit_id, criteria: dict, detail, change_type: str, metadata: dict = None
    ):
        alert_data = {
            "visit_id":      visit_id,
            "criteria_name": criteria["name"],
            "category":      criteria["category"],
            "severity":      criteria["severity"],
            "detail":        detail,
            "timestamp":     datetime.now(),
            "change_type":   change_type,
            "metadata":      metadata or {},
        }
        fire_alert(alert_data)

-- ---------------------------------------------------------
-- Manual Data Retention / Housekeeping Script
-- ---------------------------------------------------------
-- Run this script periodically to clear out old logs and keep the database size small.
-- It keeps 90 days of operational logs and 1 year of alerts history.

-- 1. Delete old CC Change Transition logs (Retain last 90 days)
DELETE FROM cc_change_log
WHERE
    created_at < NOW() - INTERVAL 90 DAY;

-- 2. Delete old cached CC strings used for state comparisons (Retain last 90 days)
DELETE FROM visit_cc_hashes
WHERE
    updated_at < NOW() - INTERVAL 90 DAY;

-- 3. Delete old clinical alerts (Retain last 365 days / 1 year)
DELETE FROM alerts WHERE updated_at < NOW() - INTERVAL 365 DAY;

-- Optimize tables to free up physical disk space after massive deletes (Optional)
OPTIMIZE TABLE cc_change_log;

OPTIMIZE TABLE visit_cc_hashes;

OPTIMIZE TABLE alerts;
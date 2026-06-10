-- ---------------------------------------------------------
-- Reset Factory Default Script
-- ---------------------------------------------------------
-- WARNING:
-- Running these commands will purge all 100% of the program's tracking history.
-- When the program runs on the next cycle, it will act as if it has never scanned any patients.
-- (Warning: It may immediately re-trigger NEW alerts for patients already alerted today)

-- 1. Clear 4-state CC modification tracking logs
TRUNCATE TABLE cc_change_log;

-- 2. Clear known latest CC hashes memory for all patients
TRUNCATE TABLE visit_cc_hashes;

-- 3. Clear all active and resolved alerts
TRUNCATE TABLE alerts;

-- =========================================================
-- OPTIONAL (To wipe all screening criteria rules as well)
-- You typically do not run this. Only uncomment if you want
-- to re-import a completely fresh seed.sql file.
-- =========================================================
-- TRUNCATE TABLE criteria;
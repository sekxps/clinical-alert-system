-- ---------------------------------------------------------
-- Clinical Alert System (CAS) - Initial Database Setup
-- ---------------------------------------------------------

-- 1. Table: criteria (Stores alert criteria and rules)
CREATE TABLE IF NOT EXISTS criteria (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100),
    query TEXT NOT NULL,
    active BOOLEAN DEFAULT 1,
    severity ENUM('info', 'warning', 'critical') DEFAULT 'warning',
    cooldown_min INT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 2. Table: alerts (Stores current alert state of patients)
CREATE TABLE IF NOT EXISTS alerts (
    id INT PRIMARY KEY AUTO_INCREMENT,
    visit_id VARCHAR(50) NOT NULL,
    criteria_id INT NOT NULL,
    detail TEXT,
    detail_hash VARCHAR(64),
    severity ENUM('info', 'warning', 'critical'),
    alerted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    resolved_at DATETIME DEFAULT NULL,
    seen BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_visit_criteria (visit_id, criteria_id),
    INDEX idx_alerts_active (seen, resolved_at)
);

-- 3. Table: visit_cc_hashes (Stores latest CC hash per visit to detect symptom edits)
CREATE TABLE IF NOT EXISTS visit_cc_hashes (
    visit_id VARCHAR(50) PRIMARY KEY,
    cc_hash VARCHAR(64) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 4. Table: cc_change_log (Audit log for edits and 4-state transitions)
CREATE TABLE IF NOT EXISTS cc_change_log (
    id INT PRIMARY KEY AUTO_INCREMENT,
    visit_id VARCHAR(50),
    criteria_id INT,
    old_cc_hash VARCHAR(64),
    new_cc_hash VARCHAR(64),
    old_risk INT,
    new_risk INT,
    change_type VARCHAR(20),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_cc_log (visit_id, criteria_id)
);
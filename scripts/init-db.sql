-- Initialize database schema

CREATE TABLE IF NOT EXISTS incidents (
    id SERIAL PRIMARY KEY,
    incident_id VARCHAR(50) UNIQUE NOT NULL,
    service_name VARCHAR(100) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    severity VARCHAR(20) NOT NULL,
    root_cause TEXT,
    status VARCHAR(20) NOT NULL,
    confidence FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_incidents_service ON incidents(service_name);
CREATE INDEX idx_incidents_timestamp ON incidents(timestamp);
CREATE INDEX idx_incidents_status ON incidents(status);

CREATE TABLE IF NOT EXISTS remediations (
    id SERIAL PRIMARY KEY,
    incident_id VARCHAR(50) REFERENCES incidents(incident_id),
    fix_type VARCHAR(50) NOT NULL,
    code TEXT NOT NULL,
    status VARCHAR(20) NOT NULL,
    applied_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

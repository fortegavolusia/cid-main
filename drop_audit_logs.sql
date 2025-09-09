-- Drop unused audit_logs table from CIDS schema
-- We are using activity_log for all auditing purposes

DROP TABLE IF EXISTS cids.audit_logs CASCADE;

-- Also drop any related indexes if they exist separately
DROP INDEX IF EXISTS cids.idx_audit_logs_user_email;
DROP INDEX IF EXISTS cids.idx_audit_logs_action;
DROP INDEX IF EXISTS cids.idx_audit_logs_resource_type;
DROP INDEX IF EXISTS cids.idx_audit_logs_created_at;

-- Confirm the table is dropped
SELECT 'audit_logs table dropped successfully' AS status;
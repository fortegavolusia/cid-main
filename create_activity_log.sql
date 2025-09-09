-- Create activity_log table in CIDS schema for comprehensive auditing
-- This table will track all activities including logins, API calls, CRUD operations, etc.

CREATE TABLE IF NOT EXISTS cids.activity_log (
    activity_id SERIAL PRIMARY KEY,
    activity_type VARCHAR(100) NOT NULL, -- login, logout, create, update, delete, api_call, etc.
    entity_type VARCHAR(100),            -- app, user, role, permission, token, etc.
    entity_id VARCHAR(255),              -- ID of the entity being acted upon
    entity_name VARCHAR(255),            -- Human-readable name of the entity
    user_email VARCHAR(255),             -- Email of the user performing the action
    user_id VARCHAR(255),                -- User ID if available
    details JSONB DEFAULT '{}'::jsonb,   -- Additional details about the activity
    status VARCHAR(50) DEFAULT 'success', -- success, failure, pending
    error_message TEXT,                  -- Error details if status is failure
    ip_address INET,                     -- IP address of the request
    user_agent TEXT,                     -- User agent string
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    -- Additional fields for better tracking
    session_id VARCHAR(255),             -- Session identifier for tracking user sessions
    api_endpoint VARCHAR(500),           -- API endpoint called
    http_method VARCHAR(10),             -- GET, POST, PUT, DELETE, etc.
    response_time_ms INTEGER,            -- Response time in milliseconds
    request_id VARCHAR(255)              -- Unique request identifier for tracing
);

-- Create comprehensive indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_activity_log_activity_type ON cids.activity_log(activity_type);
CREATE INDEX IF NOT EXISTS idx_activity_log_entity_type ON cids.activity_log(entity_type);
CREATE INDEX IF NOT EXISTS idx_activity_log_entity_id ON cids.activity_log(entity_id);
CREATE INDEX IF NOT EXISTS idx_activity_log_user_email ON cids.activity_log(user_email);
CREATE INDEX IF NOT EXISTS idx_activity_log_created_at ON cids.activity_log(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_activity_log_status ON cids.activity_log(status);
CREATE INDEX IF NOT EXISTS idx_activity_log_session_id ON cids.activity_log(session_id);

-- Create a composite index for common queries
CREATE INDEX IF NOT EXISTS idx_activity_log_user_date ON cids.activity_log(user_email, created_at DESC);

-- Add comments for documentation
COMMENT ON TABLE cids.activity_log IS 'Comprehensive activity log for all CID operations including authentication, authorization, and CRUD operations';
COMMENT ON COLUMN cids.activity_log.activity_type IS 'Type of activity: login, logout, token_issued, token_refreshed, app_created, role_updated, permission_granted, etc.';
COMMENT ON COLUMN cids.activity_log.entity_type IS 'Type of entity being acted upon: app, user, role, permission, token, api_key, etc.';
COMMENT ON COLUMN cids.activity_log.details IS 'JSON object containing additional context-specific details about the activity';
COMMENT ON COLUMN cids.activity_log.status IS 'Status of the operation: success, failure, pending';
COMMENT ON COLUMN cids.activity_log.session_id IS 'Session ID to track all activities within a user session';
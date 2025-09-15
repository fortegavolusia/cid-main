-- Create table for revoked tokens (government security compliance)
-- This table stores all revoked access and refresh tokens

CREATE TABLE IF NOT EXISTS cids.revoked_tokens (
    token_id VARCHAR(255) PRIMARY KEY,
    token_type VARCHAR(50) NOT NULL DEFAULT 'access', -- 'access' or 'refresh'
    revoked_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    revoked_by VARCHAR(255), -- email of user who revoked it
    revoked_reason VARCHAR(100), -- 'logout', 'admin_revoked', 'rotation', 'security_breach'
    user_email VARCHAR(255),
    user_id VARCHAR(255),
    ip_address VARCHAR(45), -- Support IPv6
    expires_at TIMESTAMP WITH TIME ZONE, -- Original expiry time
    token_hash VARCHAR(64), -- SHA256 hash for refresh tokens
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for fast lookups
CREATE INDEX idx_revoked_tokens_token_id ON cids.revoked_tokens(token_id);
CREATE INDEX idx_revoked_tokens_token_hash ON cids.revoked_tokens(token_hash);
CREATE INDEX idx_revoked_tokens_user_email ON cids.revoked_tokens(user_email);
CREATE INDEX idx_revoked_tokens_expires_at ON cids.revoked_tokens(expires_at);
CREATE INDEX idx_revoked_tokens_revoked_at ON cids.revoked_tokens(revoked_at);

-- Create table for refresh token tracking (for rotation)
CREATE TABLE IF NOT EXISTS cids.refresh_tokens (
    token_hash VARCHAR(64) PRIMARY KEY, -- SHA256 of refresh token
    user_email VARCHAR(255) NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    issued_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    last_used_at TIMESTAMP WITH TIME ZONE,
    use_count INTEGER DEFAULT 0,
    parent_token_hash VARCHAR(64), -- Previous token in rotation chain
    client_ip VARCHAR(45),
    user_agent TEXT,
    device_fingerprint VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    rotation_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX idx_refresh_tokens_user_email ON cids.refresh_tokens(user_email);
CREATE INDEX idx_refresh_tokens_is_active ON cids.refresh_tokens(is_active);
CREATE INDEX idx_refresh_tokens_expires_at ON cids.refresh_tokens(expires_at);

-- Add comments for documentation
COMMENT ON TABLE cids.revoked_tokens IS 'Stores all revoked tokens for security compliance';
COMMENT ON TABLE cids.refresh_tokens IS 'Tracks refresh tokens for rotation and security monitoring';

-- Create cleanup function for expired revoked tokens (run periodically)
CREATE OR REPLACE FUNCTION cids.cleanup_expired_revoked_tokens()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM cids.revoked_tokens 
    WHERE expires_at < CURRENT_TIMESTAMP - INTERVAL '7 days';
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION cids.cleanup_expired_revoked_tokens() IS 'Removes revoked tokens that have been expired for more than 7 days';
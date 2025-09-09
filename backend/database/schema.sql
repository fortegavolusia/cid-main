-- CIDS Database Schema for Supabase/PostgreSQL
-- Version: 1.0.0

-- Create schema if not exists
CREATE SCHEMA IF NOT EXISTS cids;

-- Set search path
SET search_path TO cids, public;

-- =====================================================
-- REGISTERED APPS TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS registered_apps (
    client_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    redirect_uris JSONB DEFAULT '[]'::jsonb,
    owner_email VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    discovery_endpoint VARCHAR(500),
    allow_discovery BOOLEAN DEFAULT true,
    last_discovery_at TIMESTAMP WITH TIME ZONE,
    discovery_status VARCHAR(50),
    discovery_version VARCHAR(10)
);

-- Create indexes for registered_apps
CREATE INDEX idx_registered_apps_owner_email ON registered_apps(owner_email);
CREATE INDEX idx_registered_apps_is_active ON registered_apps(is_active);
CREATE INDEX idx_registered_apps_created_at ON registered_apps(created_at DESC);

-- =====================================================
-- API KEYS TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS api_keys (
    key_id VARCHAR(50) PRIMARY KEY,
    client_id VARCHAR(50) NOT NULL REFERENCES registered_apps(client_id) ON DELETE CASCADE,
    key_hash VARCHAR(255) NOT NULL, -- Store hashed API key
    name VARCHAR(255),
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE,
    last_used_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT true,
    created_by VARCHAR(255) NOT NULL
);

-- Create indexes for api_keys
CREATE INDEX idx_api_keys_client_id ON api_keys(client_id);
CREATE INDEX idx_api_keys_is_active ON api_keys(is_active);
CREATE INDEX idx_api_keys_expires_at ON api_keys(expires_at);

-- =====================================================
-- ROLES TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS roles (
    role_id SERIAL PRIMARY KEY,
    client_id VARCHAR(50) NOT NULL REFERENCES registered_apps(client_id) ON DELETE CASCADE,
    role_name VARCHAR(100) NOT NULL,
    description TEXT,
    ad_groups JSONB DEFAULT '[]'::jsonb, -- Array of AD group IDs
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(client_id, role_name)
);

-- Create indexes for roles
CREATE INDEX idx_roles_client_id ON roles(client_id);
CREATE INDEX idx_roles_role_name ON roles(role_name);

-- =====================================================
-- PERMISSIONS TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS permissions (
    permission_id SERIAL PRIMARY KEY,
    role_id INTEGER NOT NULL REFERENCES roles(role_id) ON DELETE CASCADE,
    resource VARCHAR(255) NOT NULL,
    action VARCHAR(100) NOT NULL,
    fields JSONB DEFAULT '[]'::jsonb, -- Array of allowed fields
    resource_filters JSONB DEFAULT '{}'::jsonb, -- RLS filters
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for permissions
CREATE INDEX idx_permissions_role_id ON permissions(role_id);
CREATE INDEX idx_permissions_resource ON permissions(resource);
CREATE INDEX idx_permissions_action ON permissions(action);

-- =====================================================
-- DISCOVERED PERMISSIONS TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS discovered_permissions (
    discovery_id SERIAL PRIMARY KEY,
    client_id VARCHAR(50) NOT NULL REFERENCES registered_apps(client_id) ON DELETE CASCADE,
    resource VARCHAR(255) NOT NULL,
    action VARCHAR(100) NOT NULL,
    available_fields JSONB DEFAULT '[]'::jsonb,
    discovered_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT true,
    UNIQUE(client_id, resource, action)
);

-- Create indexes for discovered_permissions
CREATE INDEX idx_discovered_permissions_client_id ON discovered_permissions(client_id);
CREATE INDEX idx_discovered_permissions_resource ON discovered_permissions(resource);

-- =====================================================
-- TOKEN TEMPLATES TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS token_templates (
    template_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    claims_structure JSONB NOT NULL,
    ad_groups JSONB DEFAULT '[]'::jsonb, -- AD groups this template applies to
    is_default BOOLEAN DEFAULT false,
    is_enabled BOOLEAN DEFAULT true,
    priority INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255) NOT NULL
);

-- Create indexes for token_templates
CREATE INDEX idx_token_templates_is_default ON token_templates(is_default);
CREATE INDEX idx_token_templates_is_enabled ON token_templates(is_enabled);
CREATE INDEX idx_token_templates_priority ON token_templates(priority DESC);

-- =====================================================
-- APP ROLE MAPPINGS TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS app_role_mappings (
    mapping_id SERIAL PRIMARY KEY,
    client_id VARCHAR(50) NOT NULL REFERENCES registered_apps(client_id) ON DELETE CASCADE,
    ad_group_name VARCHAR(255) NOT NULL,
    role_name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(client_id, ad_group_name)
);

-- Create indexes for app_role_mappings
CREATE INDEX idx_app_role_mappings_client_id ON app_role_mappings(client_id);
CREATE INDEX idx_app_role_mappings_ad_group_name ON app_role_mappings(ad_group_name);

-- =====================================================
-- TOKEN ACTIVITY TABLE (for logging)
-- =====================================================
CREATE TABLE IF NOT EXISTS token_activity (
    activity_id SERIAL PRIMARY KEY,
    token_id VARCHAR(100) NOT NULL,
    user_email VARCHAR(255) NOT NULL,
    user_name VARCHAR(255),
    client_id VARCHAR(50),
    action VARCHAR(50) NOT NULL, -- 'issued', 'refreshed', 'validated', 'revoked'
    ip_address INET,
    user_agent TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for token_activity
CREATE INDEX idx_token_activity_token_id ON token_activity(token_id);
CREATE INDEX idx_token_activity_user_email ON token_activity(user_email);
CREATE INDEX idx_token_activity_client_id ON token_activity(client_id);
CREATE INDEX idx_token_activity_action ON token_activity(action);
CREATE INDEX idx_token_activity_created_at ON token_activity(created_at DESC);

-- =====================================================
-- AUDIT LOG TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS audit_logs (
    log_id SERIAL PRIMARY KEY,
    user_email VARCHAR(255),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100),
    resource_id VARCHAR(255),
    changes JSONB DEFAULT '{}'::jsonb,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for audit_logs
CREATE INDEX idx_audit_logs_user_email ON audit_logs(user_email);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_resource_type ON audit_logs(resource_type);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at DESC);

-- =====================================================
-- FUNCTIONS FOR UPDATED_AT TRIGGERS
-- =====================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at columns
CREATE TRIGGER update_registered_apps_updated_at BEFORE UPDATE ON registered_apps
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_roles_updated_at BEFORE UPDATE ON roles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_permissions_updated_at BEFORE UPDATE ON permissions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_token_templates_updated_at BEFORE UPDATE ON token_templates
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_app_role_mappings_updated_at BEFORE UPDATE ON app_role_mappings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- =====================================================

-- Enable RLS on all tables
ALTER TABLE registered_apps ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE permissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE discovered_permissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE token_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE app_role_mappings ENABLE ROW LEVEL SECURITY;
ALTER TABLE token_activity ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

-- Create policies (these will need to be adjusted based on your auth strategy)
-- For now, we'll create permissive policies that can be tightened later

-- Service role can do everything
CREATE POLICY "Service role full access" ON registered_apps
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access" ON api_keys
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access" ON roles
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access" ON permissions
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access" ON discovered_permissions
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access" ON token_templates
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access" ON app_role_mappings
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access" ON token_activity
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access" ON audit_logs
    FOR ALL USING (auth.role() = 'service_role');

-- =====================================================
-- INITIAL DATA / COMMENTS
-- =====================================================

COMMENT ON TABLE registered_apps IS 'Stores registered applications that can use CID for authentication';
COMMENT ON TABLE api_keys IS 'Stores API keys for programmatic access to registered apps';
COMMENT ON TABLE roles IS 'Defines roles for each registered application';
COMMENT ON TABLE permissions IS 'Stores permissions and RLS filters for each role';
COMMENT ON TABLE discovered_permissions IS 'Stores permissions discovered from application endpoints';
COMMENT ON TABLE token_templates IS 'JWT token templates with claim structures';
COMMENT ON TABLE app_role_mappings IS 'Maps Azure AD groups to application roles';
COMMENT ON TABLE token_activity IS 'Logs all token-related activities';
COMMENT ON TABLE audit_logs IS 'General audit log for administrative actions';
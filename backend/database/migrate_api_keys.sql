-- Migration script for API Keys table
-- Adds missing fields to support full APIKeyMetadata structure
-- This script is idempotent and can be run multiple times safely

-- Set search path
SET search_path TO cids, public;

-- Add missing columns if they don't exist
DO $$
BEGIN
    -- Add usage_count if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_schema = 'cids' AND table_name = 'api_keys'
                   AND column_name = 'usage_count') THEN
        ALTER TABLE cids.api_keys ADD COLUMN usage_count INTEGER DEFAULT 0;
        RAISE NOTICE 'Added usage_count column to api_keys table';
    END IF;

    -- Add last_rotated_at if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_schema = 'cids' AND table_name = 'api_keys'
                   AND column_name = 'last_rotated_at') THEN
        ALTER TABLE cids.api_keys ADD COLUMN last_rotated_at TIMESTAMP WITH TIME ZONE;
        RAISE NOTICE 'Added last_rotated_at column to api_keys table';
    END IF;

    -- Add rotation_scheduled_at if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_schema = 'cids' AND table_name = 'api_keys'
                   AND column_name = 'rotation_scheduled_at') THEN
        ALTER TABLE cids.api_keys ADD COLUMN rotation_scheduled_at TIMESTAMP WITH TIME ZONE;
        RAISE NOTICE 'Added rotation_scheduled_at column to api_keys table';
    END IF;

    -- Add rotation_grace_end if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_schema = 'cids' AND table_name = 'api_keys'
                   AND column_name = 'rotation_grace_end') THEN
        ALTER TABLE cids.api_keys ADD COLUMN rotation_grace_end TIMESTAMP WITH TIME ZONE;
        RAISE NOTICE 'Added rotation_grace_end column to api_keys table';
    END IF;

    -- Add log_id if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_schema = 'cids' AND table_name = 'api_keys'
                   AND column_name = 'log_id') THEN
        ALTER TABLE cids.api_keys ADD COLUMN log_id VARCHAR(50);
        RAISE NOTICE 'Added log_id column to api_keys table';
    END IF;

    -- Add token_template_name if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_schema = 'cids' AND table_name = 'api_keys'
                   AND column_name = 'token_template_name') THEN
        ALTER TABLE cids.api_keys ADD COLUMN token_template_name VARCHAR(255);
        RAISE NOTICE 'Added token_template_name column to api_keys table';
    END IF;

    -- Add app_roles_overrides if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_schema = 'cids' AND table_name = 'api_keys'
                   AND column_name = 'app_roles_overrides') THEN
        ALTER TABLE cids.api_keys ADD COLUMN app_roles_overrides JSONB;
        RAISE NOTICE 'Added app_roles_overrides column to api_keys table';
    END IF;

    -- Add token_ttl_minutes if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_schema = 'cids' AND table_name = 'api_keys'
                   AND column_name = 'token_ttl_minutes') THEN
        ALTER TABLE cids.api_keys ADD COLUMN token_ttl_minutes INTEGER;
        RAISE NOTICE 'Added token_ttl_minutes column to api_keys table';
    END IF;

    -- Add default_audience if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_schema = 'cids' AND table_name = 'api_keys'
                   AND column_name = 'default_audience') THEN
        ALTER TABLE cids.api_keys ADD COLUMN default_audience VARCHAR(255);
        RAISE NOTICE 'Added default_audience column to api_keys table';
    END IF;

    -- Add allowed_audiences if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_schema = 'cids' AND table_name = 'api_keys'
                   AND column_name = 'allowed_audiences') THEN
        ALTER TABLE cids.api_keys ADD COLUMN allowed_audiences JSONB;
        RAISE NOTICE 'Added allowed_audiences column to api_keys table';
    END IF;

    -- Add updated_at if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_schema = 'cids' AND table_name = 'api_keys'
                   AND column_name = 'updated_at') THEN
        ALTER TABLE cids.api_keys ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;
        RAISE NOTICE 'Added updated_at column to api_keys table';
    END IF;

END $$;

-- Create missing indexes if they don't exist
DO $$
BEGIN
    -- Add index on key_hash for fast validation
    IF NOT EXISTS (SELECT 1 FROM pg_indexes
                   WHERE schemaname = 'cids' AND tablename = 'api_keys'
                   AND indexname = 'idx_api_keys_key_hash') THEN
        CREATE INDEX idx_api_keys_key_hash ON cids.api_keys(key_hash);
        RAISE NOTICE 'Created index idx_api_keys_key_hash';
    END IF;

    -- Add index on last_used_at
    IF NOT EXISTS (SELECT 1 FROM pg_indexes
                   WHERE schemaname = 'cids' AND tablename = 'api_keys'
                   AND indexname = 'idx_api_keys_last_used') THEN
        CREATE INDEX idx_api_keys_last_used ON cids.api_keys(last_used_at);
        RAISE NOTICE 'Created index idx_api_keys_last_used';
    END IF;

    -- Add index on rotation_grace_end
    IF NOT EXISTS (SELECT 1 FROM pg_indexes
                   WHERE schemaname = 'cids' AND tablename = 'api_keys'
                   AND indexname = 'idx_api_keys_rotation_grace') THEN
        CREATE INDEX idx_api_keys_rotation_grace ON cids.api_keys(rotation_grace_end);
        RAISE NOTICE 'Created index idx_api_keys_rotation_grace';
    END IF;

END $$;

-- Show current table structure
\d cids.api_keys

RAISE NOTICE 'API Keys table migration completed successfully';
// Admin panel related types
export interface TokenInfo {
  id: string;
  user: {
    name: string;
    email: string;
  };
  issued_at: string;
  expires_at: string;
  subject: string;
  issuer: string;
  audience: string;
  id_token_preview?: string;
  access_token_preview?: string;
  full_id_token?: string;
  full_access_token?: string;
  type?: 'Internal' | 'Azure';
  typeColor?: string;
  userName?: string;
  userEmail?: string;
  revoked?: boolean;
}

export interface TokenListResponse {
  total: number;
  tokens: TokenInfo[];
  admin_user: string;
}

export interface AppInfo {
  client_id: string;
  name: string;
  is_active: boolean;
  created_at: string;
  redirect_uris?: string[];
  description?: string;
  owner_email?: string;
  allow_discovery?: boolean;
  discovery_endpoint?: string | null;
  last_discovery_at?: string | null;
  last_discovery_run_at?: string | null;
  last_discovery_run_by?: string | null;
  discovery_run_count?: number;
  discovery_status?: 'success' | 'error' | 'timeout' | 'connection_error' | 'unknown' | null;
  latest_version?: number;
  latest_endpoints_count?: number;
  latest_permissions_count?: number;
  latest_sensitive_fields_count?: number;
  latest_discovery_timestamp?: string;
  latest_discovery_id?: string;
  has_api_key?: boolean;  // Added to track if app has active API keys
  role_count?: number;
  active_roles_count?: number;
}

export interface AppRegistrationResult {
  app: AppInfo;
  api_key?: string;
  api_key_metadata?: any;
}

export interface APIKey {
  key_id: string;
  key_prefix: string;
  name: string;
  permissions?: string[];
  expires_at: string;
  created_at: string;
  created_by: string;
  is_active: boolean;
  last_used_at?: string;
  usage_count: number;
  log_id?: string;
}

export interface APIKeyCreationResponse {
  api_key: string;
  metadata: APIKey;
}

export interface CreateAPIKeyRequest {
  name: string;
  permissions: string[];
  ttl_days?: number;
}

export interface TokenActivity {
  timestamp: string;
  action: string;
  performed_by: {
    email: string;
    name: string;
  };
  details: Record<string, any>;
}

export interface TokenActivityResponse {
  token_id: string;
  token_info: {
    user: {
      name: string;
      email: string;
    };
    issued_at: string;
    expires_at: string;
    source: string;
    revoked: boolean;
  };
  activities: TokenActivity[];
  activity_count: number;
}

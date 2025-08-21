// API related types
export interface ApiResponse<T = any> {
  data?: T;
  error?: string;
  message?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export interface Endpoint {
  method: string;
  path: string;
  desc: string;
  discovered?: boolean;
}

export interface AppEndpoints {
  endpoints: Endpoint[];
  version: string;
  updated_at: string;
  updated_by: string;
  has_discovered?: boolean;
}

export interface DiscoveryResponse {
  total_apps: number;
  apps: Record<string, AppEndpoints>;
}

export interface EffectiveIdentity {
  sub: string;
  email: string;
  name: string;
  groups: string[];
  roles: string[];
  permissions: Record<string, string[]>;
  tenant_id?: string;
  computed_permissions: {
    [resource: string]: string[];
  };
}

export interface ServerInfo {
  platform: string;
  python_version: string;
  timezone_name: string[];
  timezone_offset_seconds: number;
  dst_offset_seconds: number;
  is_dst: number;
}

export interface TimestampInfo {
  utc_now: string;
  local_now: string;
  utc_timestamp: number;
  local_timestamp: number;
  offset_hours: number;
}

export interface DebugResponse {
  server_info: ServerInfo;
  current_timestamps: TimestampInfo;
  sample_token?: any;
  timestamp_examples: {
    correct_utc_format: string;
    without_z: string;
    with_timezone: string;
  };
}

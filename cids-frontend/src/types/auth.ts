// Authentication related types
export interface User {
  sub: string;
  email: string;
  name: string;
  groups?: Array<{
    displayName: string;
    type?: string;
  }>;
  permissions?: Record<string, string[]>;
  token_issued?: string;
  token_expires?: string;
  raw_claims?: Record<string, any>;
}

export interface AuthState {
  isAuthenticated: boolean;
  user: User | null;
  token: string | null;
  loading: boolean;
  error: string | null;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  refresh_token?: string;
}

export interface TokenValidationResponse {
  valid: boolean;
  sub?: string;
  email?: string;
  name?: string;
  permissions?: string[];
  app_client_id?: string;
  auth_type?: 'jwt' | 'api_key';
  error?: string;
}

export interface SessionData {
  access_token?: string;
  internal_token?: string;
  azure_id_token?: string;
  azure_claims?: Record<string, any>;
  user?: User;
}

import apiService from './api';
import type {
  LoginResponse,
  TokenValidationResponse,
  User
} from '../types/auth';

class AuthService {
  // Initiate login flow
  async login(): Promise<void> {
    window.location.href = '/auth/login';
  }

  // Handle logout
  async logout(): Promise<void> {
    try {
      await apiService.get('/auth/logout');
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      apiService.clearAuthToken();
      window.location.href = '/';
    }
  }

  // Get session token
  async getSessionToken(): Promise<LoginResponse> {
    const origin = (import.meta as any).env?.VITE_API_ORIGIN || 'https://10.1.5.58:8000';
    const res = await fetch(`${origin}/auth/token/session`, {
      method: 'POST',
      credentials: 'include',
    });
    if (!res.ok) {
      throw new Error(`Session token error: ${res.status}`);
    }
    return res.json();
  }

  // Validate token
  async validateToken(token?: string): Promise<TokenValidationResponse> {
    const tokenToValidate = token || apiService.getAuthToken();
    if (!tokenToValidate) {
      throw new Error('No token provided');
    }

    return apiService.post<TokenValidationResponse>('/auth/validate', {
      token: tokenToValidate
    });
  }

  // Get current user info
  async getCurrentUser(): Promise<User> {
    return apiService.get<User>('/auth/whoami');
  }

  // Get my token information
  async getMyToken(): Promise<any> {
    return apiService.get('/auth/my-token');
  }

  // Refresh token
  async refreshToken(refreshToken: string): Promise<LoginResponse> {
    return apiService.post<LoginResponse>('/auth/token', {
      grant_type: 'refresh_token',
      refresh_token: refreshToken
    });
  }

  // OAuth token endpoint
  async getOAuthToken(grantType: string, refreshToken?: string): Promise<LoginResponse> {
    const formData = new FormData();
    formData.append('grant_type', grantType);
    if (refreshToken) {
      formData.append('refresh_token', refreshToken);
    }

    return apiService.post<LoginResponse>('/oauth/token', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
  }

  // Check if user is authenticated
  isAuthenticated(): boolean {
    const token = apiService.getAuthToken();
    return !!token;
  }

  // Get auth token
  getAuthToken(): string | null {
    return apiService.getAuthToken();
  }

  // Set auth token
  setAuthToken(token: string): void {
    apiService.setAuthToken(token);
  }

  // Clear auth token
  clearAuthToken(): void {
    apiService.clearAuthToken();
  }

  // Get effective identity
  async getEffectiveIdentity(tenantId?: string): Promise<any> {
    const headers = tenantId ? { 'X-Tenant-ID': tenantId } : {};
    return apiService.get('/iam/me', { headers });
  }

  // Revoke token
  async revokeToken(token: string, tokenTypeHint?: string): Promise<void> {
    return apiService.post('/auth/revoke', {
      token,
      token_type_hint: tokenTypeHint || 'refresh_token'
    });
  }
}

export const authService = new AuthService();
export default authService;

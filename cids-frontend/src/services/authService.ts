import apiService from './api';
import type {
  LoginResponse,
  TokenValidationResponse,
  User
} from '../types/auth';

class AuthService {
  private readonly AZURE_CLIENT_ID = '85d64713-e09e-4ddd-8677-90a2a3b7f668';
  private readonly AZURE_TENANT_ID = 'ed785c93-cfd5-4daf-a103-4de951a43b70';
  private readonly AZURE_REDIRECT_URI = 'https://10.1.5.58:3000/auth/callback';
  private readonly AZURE_SCOPE = 'openid profile email User.Read';

	  // Decode JWT to read expiry (client-side, no verification)
	  private parseJWT(token: string): any | null {
	    try {
	      const base64Url = token.split('.')[1];
	      const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
	      const jsonPayload = decodeURIComponent(
	        atob(base64)
	          .split('')
	          .map(c => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
	          .join('')
	      );
	      return JSON.parse(jsonPayload);
	    } catch {
	      return null;
	    }
	  }


  // Initiate login flow - Direct OAuth with Azure AD
  async login(): Promise<void> {
    const state = this.generateRandomString(32);
    localStorage.setItem('oauth_state', state);

    const authUrl = new URL(`https://login.microsoftonline.com/${this.AZURE_TENANT_ID}/oauth2/v2.0/authorize`);
    authUrl.searchParams.append('client_id', this.AZURE_CLIENT_ID);
    authUrl.searchParams.append('response_type', 'code');
    authUrl.searchParams.append('redirect_uri', this.AZURE_REDIRECT_URI);
    authUrl.searchParams.append('scope', this.AZURE_SCOPE);
    authUrl.searchParams.append('state', state);
    authUrl.searchParams.append('response_mode', 'query');

    window.location.href = authUrl.toString();
  }

  // Generate random string for state parameter
  private generateRandomString(length: number): string {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
    let result = '';
    for (let i = 0; i < length; i++) {
      result += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    return result;
  }

  // Exchange authorization code for token
  async exchangeCodeForToken(code: string): Promise<LoginResponse> {
    return apiService.post<LoginResponse>('/auth/token/exchange', {
      code,
      redirect_uri: this.AZURE_REDIRECT_URI
    });
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

	  // Get session token bundle (access + refresh + derived metadata)
	  async getSessionToken(): Promise<any> {
	    const accessToken = apiService.getAuthToken();
	    const refreshToken = localStorage.getItem('refresh_token');
	    if (!accessToken) {
	      throw new Error('No access token');
	    }
	    const payload = this.parseJWT(accessToken) || {};
	    return {
	      access_token: accessToken,
	      refresh_token: refreshToken,
	      exp: payload.exp,
	      iat: payload.iat,
	      sub: payload.sub,
	      email: payload.email,
	      name: payload.name,
	    };
	  }

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

import apiService from './api';
import type {
  LoginResponse,
  TokenValidationResponse,
  User
} from '../types/auth';

class AuthService {
  private readonly AZURE_CLIENT_ID = '0c4550df-c462-4272-9203-ee0ec72b532b';
  private readonly AZURE_TENANT_ID = 'ed785c93-cfd5-4daf-a103-4de951a43b70';
  private readonly AZURE_REDIRECT_URI = 'http://localhost:3000/auth/callback';
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


  // Initiate login flow - Direct OAuth with Azure AD with PKCE
  async login(): Promise<void> {
    const state = this.generateRandomString(32);
    const codeVerifier = this.generateCodeVerifier();
    const codeChallenge = await this.generateCodeChallenge(codeVerifier);
    
    // Store state and code verifier for later use
    localStorage.setItem('oauth_state', state);
    localStorage.setItem('code_verifier', codeVerifier);

    const authUrl = new URL(`https://login.microsoftonline.com/${this.AZURE_TENANT_ID}/oauth2/v2.0/authorize`);
    authUrl.searchParams.append('client_id', this.AZURE_CLIENT_ID);
    authUrl.searchParams.append('response_type', 'code');
    authUrl.searchParams.append('redirect_uri', this.AZURE_REDIRECT_URI);
    authUrl.searchParams.append('scope', this.AZURE_SCOPE);
    authUrl.searchParams.append('state', state);
    authUrl.searchParams.append('response_mode', 'query');
    authUrl.searchParams.append('code_challenge', codeChallenge);
    authUrl.searchParams.append('code_challenge_method', 'S256');

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

  // Generate code verifier for PKCE
  private generateCodeVerifier(): string {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~';
    let result = '';
    for (let i = 0; i < 128; i++) {
      result += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    return result;
  }

  // Generate code challenge from verifier
  private async generateCodeChallenge(verifier: string): Promise<string> {
    const encoder = new TextEncoder();
    const data = encoder.encode(verifier);
    const digest = await window.crypto.subtle.digest('SHA-256', data);
    const base64 = btoa(String.fromCharCode(...new Uint8Array(digest)));
    // Convert to URL-safe base64
    return base64.replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '');
  }

  // Exchange authorization code for token
  async exchangeCodeForToken(code: string): Promise<LoginResponse> {
    // Get the stored code_verifier
    const codeVerifier = localStorage.getItem('code_verifier');
    
    // For SPA, we need to exchange the code directly with Azure AD
    const tokenEndpoint = `https://login.microsoftonline.com/${this.AZURE_TENANT_ID}/oauth2/v2.0/token`;
    
    const params = new URLSearchParams();
    params.append('client_id', this.AZURE_CLIENT_ID);
    params.append('scope', this.AZURE_SCOPE);
    params.append('code', code);
    params.append('redirect_uri', this.AZURE_REDIRECT_URI);
    params.append('grant_type', 'authorization_code');
    
    if (codeVerifier) {
      params.append('code_verifier', codeVerifier);
      localStorage.removeItem('code_verifier');
    }
    
    try {
      // Exchange code with Azure AD directly
      const azureResponse = await fetch(tokenEndpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: params.toString()
      });
      
      if (!azureResponse.ok) {
        const error = await azureResponse.json();
        throw new Error(error.error_description || 'Failed to exchange code');
      }
      
      const azureTokens = await azureResponse.json();
      
      // Now send the Azure tokens to our backend to get CID tokens
      const payload = {
        azure_access_token: azureTokens.access_token,
        azure_id_token: azureTokens.id_token,
        redirect_uri: this.AZURE_REDIRECT_URI
      };
      
      return apiService.post<LoginResponse>('/auth/token/exchange', payload);
    } catch (error) {
      console.error('Token exchange error:', error);
      throw error;
    }
  }

  // Handle logout with enhanced security - revoke tokens
  async logout(): Promise<void> {
    try {
      // Get refresh token to send for revocation
      const refreshToken = localStorage.getItem('refresh_token');

      // Call logout endpoint with refresh token for complete revocation
      await apiService.post('/auth/logout', {
        refresh_token: refreshToken
      });

      console.log('Logout successful, tokens revoked');
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      // Clear all tokens from localStorage
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');

      // Clear token from API service
      apiService.clearAuthToken();

      // Redirect to login
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

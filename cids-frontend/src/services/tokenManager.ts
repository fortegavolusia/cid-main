import { authService } from './authService';

interface TokenData {
  access_token: string;
  refresh_token: string;
  expires_at: number; // Unix timestamp in ms
}

class TokenManager {
  private refreshTimer: NodeJS.Timeout | null = null;
  private tokenData: TokenData | null = null;
  private isRefreshing = false;
  private refreshPromise: Promise<void> | null = null;

  // Token expiry buffer (refresh 1 minute before expiry)
  private readonly REFRESH_BUFFER_MS = 60 * 1000; // 1 minute
  
  // Parse JWT to get expiry
  private parseJWT(token: string): any {
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

  // Initialize token manager with tokens
  initialize(accessToken: string, refreshToken?: string) {
    // Clear any existing timer
    this.clearRefreshTimer();

    // Parse token to get expiry
    const payload = this.parseJWT(accessToken);
    if (!payload || !payload.exp) {
      console.error('Invalid token format');
      return;
    }

    // Store token data
    this.tokenData = {
      access_token: accessToken,
      refresh_token: refreshToken || localStorage.getItem('refresh_token') || '',
      expires_at: payload.exp * 1000 // Convert to ms
    };

    // Store tokens
    localStorage.setItem('access_token', accessToken);
    if (refreshToken) {
      localStorage.setItem('refresh_token', refreshToken);
    }

    // Schedule refresh
    this.scheduleTokenRefresh();
  }

  // Schedule automatic token refresh
  private scheduleTokenRefresh() {
    if (!this.tokenData) return;

    const now = Date.now();
    const expiresAt = this.tokenData.expires_at;
    const refreshAt = expiresAt - this.REFRESH_BUFFER_MS;
    const timeUntilRefresh = refreshAt - now;

    // If token already expired or will expire soon, refresh immediately
    if (timeUntilRefresh <= 0) {
      this.refreshToken();
    } else {
      // Schedule refresh
      this.refreshTimer = setTimeout(() => {
        this.refreshToken();
      }, timeUntilRefresh);

      console.log(`Token refresh scheduled in ${Math.round(timeUntilRefresh / 1000)} seconds`);
    }
  }

  // Refresh the access token
  async refreshToken(): Promise<void> {
    // Prevent multiple simultaneous refresh attempts
    if (this.isRefreshing && this.refreshPromise) {
      return this.refreshPromise;
    }

    this.isRefreshing = true;
    this.refreshPromise = this.performRefresh();

    try {
      await this.refreshPromise;
    } finally {
      this.isRefreshing = false;
      this.refreshPromise = null;
    }
  }

  private async performRefresh(): Promise<void> {
    const refreshToken = localStorage.getItem('refresh_token');
    
    if (!refreshToken) {
      console.error('No refresh token available');
      this.handleTokenExpired();
      return;
    }

    try {
      console.log('Refreshing access token...');
      const response = await authService.refreshToken(refreshToken);
      
      if (response.access_token) {
        // Update tokens
        this.initialize(response.access_token, response.refresh_token);
        console.log('Token refreshed successfully');
      } else {
        throw new Error('No access token in refresh response');
      }
    } catch (error) {
      console.error('Token refresh failed:', error);
      this.handleTokenExpired();
    }
  }

  // Handle token expiration (no valid refresh token)
  private handleTokenExpired() {
    this.clearTokens();
    // Trigger inactivity warning or redirect
    window.dispatchEvent(new CustomEvent('token-expired'));
  }

  // Clear all tokens and timers
  clearTokens() {
    this.clearRefreshTimer();
    this.tokenData = null;
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
  }

  // Clear refresh timer
  private clearRefreshTimer() {
    if (this.refreshTimer) {
      clearTimeout(this.refreshTimer);
      this.refreshTimer = null;
    }
  }

  // Get current access token
  getAccessToken(): string | null {
    return localStorage.getItem('access_token');
  }

  // Check if token is valid (not expired)
  isTokenValid(): boolean {
    if (!this.tokenData) return false;
    return Date.now() < this.tokenData.expires_at;
  }

  // Get time until token expires (in ms)
  getTimeUntilExpiry(): number {
    if (!this.tokenData) return 0;
    return Math.max(0, this.tokenData.expires_at - Date.now());
  }

  // Ensure we have a valid token (refresh if needed)
  async ensureValidToken(): Promise<string | null> {
    if (this.isTokenValid()) {
      return this.getAccessToken();
    }

    // Try to refresh
    await this.refreshToken();
    return this.getAccessToken();
  }
}

export const tokenManager = new TokenManager();
export default tokenManager;
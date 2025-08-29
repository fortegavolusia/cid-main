import axios from 'axios';
import type { AxiosInstance, AxiosResponse, AxiosError, InternalAxiosRequestConfig } from 'axios';
import { tokenManager } from './tokenManager';

class ApiService {
  private api: AxiosInstance;
  private isRefreshing = false;
  private failedQueue: Array<{
    resolve: (value?: any) => void;
    reject: (reason?: any) => void;
  }> = [];

  constructor() {
    this.api = axios.create({
      baseURL: '/', // Vite proxy will handle routing to backend
      timeout: 10000,
      withCredentials: false, // No longer need cookies - using JWT tokens
    });

    // Request interceptor to add auth token
    this.api.interceptors.request.use(
      async (config) => {
        // Skip token for auth endpoints
        if (config.url?.includes('/auth/token') || 
            config.url?.includes('/auth/login') ||
            config.url?.includes('/auth/logout')) {
          return config;
        }

        // Ensure we have a valid token
        const token = await tokenManager.ensureValidToken();
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // Response interceptor for error handling and token refresh
    this.api.interceptors.response.use(
      (response) => response,
      async (error: AxiosError) => {
        const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

        // If 401 and not already retried
        if (error.response?.status === 401 && !originalRequest._retry) {
          // Only skip retry for login/logout/token endpoints; allow refresh for admin endpoints
          const path = originalRequest.url || '';
          if (/^\/?auth\/(login|logout|token)/.test(path)) {
            tokenManager.clearTokens();
            window.location.href = '/login';
            return Promise.reject(error);
          }

          originalRequest._retry = true;

          // If already refreshing, queue this request
          if (this.isRefreshing) {
            return new Promise((resolve, reject) => {
              this.failedQueue.push({ resolve, reject });
            }).then(token => {
              originalRequest.headers.Authorization = `Bearer ${token}`;
              return this.api(originalRequest);
            }).catch(err => {
              return Promise.reject(err);
            });
          }

          this.isRefreshing = true;

          try {
            // Try to refresh token
            await tokenManager.refreshToken();
            const newToken = tokenManager.getAccessToken();

            if (newToken) {
              // Process queued requests
              this.processQueue(null, newToken);

              // Retry original request
              originalRequest.headers.Authorization = `Bearer ${newToken}`;
              return this.api(originalRequest);
            } else {
              throw new Error('No token after refresh');
            }
          } catch (refreshError) {
            // Refresh failed, process queue with error
            this.processQueue(refreshError, null);
            
            // Clear tokens and redirect to login
            tokenManager.clearTokens();
            window.location.href = '/login';
            return Promise.reject(refreshError);
          } finally {
            this.isRefreshing = false;
          }
        }

        return Promise.reject(error);
      }
    );
  }

  private processQueue(error: any, token: string | null = null) {
    this.failedQueue.forEach(prom => {
      if (error) {
        prom.reject(error);
      } else {
        prom.resolve(token);
      }
    });
    
    this.failedQueue = [];
  }

  // Generic request method
  private async request<T>(
    method: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH',
    url: string,
    data?: any,
    config?: any
  ): Promise<T> {
    try {
      const response: AxiosResponse<T> = await this.api.request({
        method,
        url,
        data,
        ...config,
      });
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || error.message);
    }
  }

  // GET request
  async get<T>(url: string, config?: any): Promise<T> {
    return this.request<T>('GET', url, undefined, config);
  }

  // POST request
  async post<T>(url: string, data?: any, config?: any): Promise<T> {
    return this.request<T>('POST', url, data, config);
  }

  // PUT request
  async put<T>(url: string, data?: any, config?: any): Promise<T> {
    return this.request<T>('PUT', url, data, config);
  }

  // DELETE request
  async delete<T>(url: string, config?: any): Promise<T> {
    return this.request<T>('DELETE', url, undefined, config);
  }

  // PATCH request
  async patch<T>(url: string, data?: any, config?: any): Promise<T> {
    return this.request<T>('PATCH', url, data, config);
  }

  // Set auth token
  setAuthToken(token: string) {
    localStorage.setItem('access_token', token);
  }

  // Clear auth token
  clearAuthToken() {
    localStorage.removeItem('access_token');
  }

  // Get auth token
  getAuthToken(): string | null {
    return localStorage.getItem('access_token');
  }
}

export const apiService = new ApiService();
export default apiService;

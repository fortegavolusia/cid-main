import axios from 'axios';
import type { AxiosInstance, AxiosResponse } from 'axios';

class ApiService {
  private api: AxiosInstance;

  constructor() {
    this.api = axios.create({
      baseURL: '/', // Vite proxy will handle routing to backend
      timeout: 10000,
      withCredentials: false, // No longer need cookies - using JWT tokens
    });

    // Request interceptor to add auth token
    this.api.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem('access_token');
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // Response interceptor for error handling
    this.api.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          // Clear token and redirect to login
          localStorage.removeItem('access_token');
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }
    );
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

import apiService from './api';
import type {
  TokenListResponse,
  AppInfo,
  APIKey,
  APIKeyCreationResponse,
  CreateAPIKeyRequest,
  TokenActivityResponse,
  AppRegistrationResult,
  RotateSecretResult
} from '../types/admin';

class AdminService {
  // Logging Config
  async getLoggingConfig(): Promise<any> {
    return apiService.get('/auth/admin/logging/config');
  }

  async updateLoggingConfig(patch: any): Promise<any> {
    return apiService.put('/auth/admin/logging/config', patch);
  }

  // Logs Readers
  async getAppLogs(params?: { start?: string; end?: string; level?: string; logger_prefix?: string; q?: string; limit?: number }): Promise<{ items: any[]; count: number }>{
    const usp = new URLSearchParams();
    Object.entries(params || {}).forEach(([k, v]) => {
      if (v !== undefined && v !== null && String(v).length) usp.append(k, String(v));
    });
    return apiService.get(`/auth/admin/logs/app${usp.toString() ? `?${usp.toString()}` : ''}`);
  }

  async getAuditLogs(params?: { start?: string; end?: string; action?: string; user_email?: string; resource_id?: string; limit?: number }): Promise<{ items: any[]; count: number }>{
    const usp = new URLSearchParams();
    Object.entries(params || {}).forEach(([k, v]) => {
      if (v !== undefined && v !== null && String(v).length) usp.append(k, String(v));
    });
    return apiService.get(`/auth/admin/logs/audit${usp.toString() ? `?${usp.toString()}` : ''}`);
  }

  async getTokenActivityLogs(params?: { start?: string; end?: string; action?: string; user_email?: string; token_id?: string; limit?: number }): Promise<{ items: any[]; count: number }>{
    const usp = new URLSearchParams();
    Object.entries(params || {}).forEach(([k, v]) => {
      if (v !== undefined && v !== null && String(v).length) usp.append(k, String(v));
    });
    return apiService.get(`/auth/admin/logs/token-activity${usp.toString() ? `?${usp.toString()}` : ''}`);
  }

  async exportLogs(kind: 'app' | 'audit' | 'token-activity', format: 'ndjson' | 'csv' = 'ndjson', limit: number = 50000): Promise<Blob> {
    const path = kind === 'app' ? '/auth/admin/logs/app/export' : kind === 'audit' ? '/auth/admin/logs/audit/export' : '/auth/admin/logs/token-activity/export';
    const usp = new URLSearchParams({ format, limit: String(limit) });
    // Use axios to include Authorization header and get blob
    // @ts-ignore - allow custom config
    return apiService.get(path + `?${usp.toString()}`, { responseType: 'blob' });
  }

  // Token Management
  async getInternalTokens(): Promise<TokenListResponse> {
    return apiService.get<TokenListResponse>('/auth/admin/tokens');
  }

  async getAzureTokens(): Promise<TokenListResponse> {
    return apiService.get<TokenListResponse>('/auth/admin/azure-tokens');
  }

  async getTokenActivity(tokenId: string): Promise<TokenActivityResponse> {
    return apiService.get<TokenActivityResponse>(`/auth/admin/tokens/${tokenId}/activities`);
  }

  async getAzureTokenActivity(tokenId: string): Promise<TokenActivityResponse> {
    return apiService.get<TokenActivityResponse>(`/auth/admin/azure-tokens/${tokenId}/activities`);
  }

  async removeToken(tokenId: string): Promise<void> {
    return apiService.delete(`/auth/admin/tokens/${tokenId}`);
  }

  async removeAzureToken(tokenId: string): Promise<void> {
    return apiService.delete(`/auth/admin/azure-tokens/${tokenId}`);
  }

  // App Management
  async getApps(): Promise<AppInfo[]> {
    return apiService.get('/auth/admin/apps');
  }

  async getApp(clientId: string): Promise<AppInfo> {
    return apiService.get(`/auth/admin/apps/${clientId}`);
  }

  async createApp(appData: Partial<AppInfo>): Promise<AppRegistrationResult> {
    return apiService.post('/auth/admin/apps', appData);
  }

  async updateApp(clientId: string, appData: Partial<AppInfo>): Promise<AppInfo> {
    return apiService.put(`/auth/admin/apps/${clientId}`, appData);
  }

  async deleteApp(clientId: string): Promise<void> {
    return apiService.delete(`/auth/admin/apps/${clientId}`);
  }

  // API Key Management
  async getAppAPIKeys(clientId: string): Promise<{ api_keys: APIKey[] }> {
    return apiService.get(`/auth/admin/apps/${clientId}/api-keys`);
  }

  async createAPIKey(clientId: string, request: CreateAPIKeyRequest): Promise<APIKeyCreationResponse> {
    return apiService.post(`/auth/admin/apps/${clientId}/api-keys`, request);
  }

  async revokeAPIKey(clientId: string, keyId: string): Promise<void> {
    return apiService.delete(`/auth/admin/apps/${clientId}/api-keys/${keyId}`);
  }

  async rotateAppSecret(clientId: string): Promise<RotateSecretResult> {
    return apiService.post(`/auth/admin/apps/${clientId}/rotate-secret`);
  }

  async rotateAPIKey(
    clientId: string,
    keyId: string,
    gracePeriodHours: number = 24
  ): Promise<APIKeyCreationResponse> {
    return apiService.post(
      `/auth/admin/apps/${clientId}/api-keys/${keyId}/rotate`,
      null,
      { params: { grace_period_hours: gracePeriodHours } }
    );
  }

  // App Endpoints
  async getAppEndpoints(clientId: string): Promise<any> {
    return apiService.get(`/auth/admin/apps/${clientId}/endpoints`);
  }

  async getRoleMappings(clientId: string): Promise<{ app_name: string; client_id: string; mappings: Array<{ ad_group: string; app_role: string }> }>{
    return apiService.get(`/auth/admin/apps/${clientId}/role-mappings`);
  }

  async setRoleMappings(clientId: string, mappings: Record<string, string | string[]>): Promise<{ message: string; mappings: Record<string, string | string[]> }>{
    return apiService.post(`/auth/admin/apps/${clientId}/role-mappings`, { mappings });
  }

  // Permission Management
  async createRolePermissions(clientId: string, roleData: { role_name: string; permissions: string[]; description?: string; rls_filters?: any }): Promise<any> {
    return apiService.post(`/permissions/${clientId}/roles`, roleData);
  }

  async updateRolePermissions(clientId: string, roleName: string, permissionData: { permissions: string[]; description?: string; rls_filters?: any }): Promise<any> {
    return apiService.put(`/permissions/${clientId}/roles/${roleName}`, permissionData);
  }

  async deleteRolePermissions(clientId: string, roleName: string): Promise<any> {
    return apiService.delete(`/permissions/${clientId}/roles/${roleName}`);
  }

  async triggerDiscovery(clientId: string): Promise<any> {
    return apiService.post(`/discovery/endpoints/${clientId}`);
  }

  async updateAppEndpoints(clientId: string, endpoints: any): Promise<any> {
    return apiService.put(`/auth/admin/apps/${clientId}/endpoints`, endpoints);
  }

  // Permission Discovery
  async getAppPermissions(clientId: string): Promise<any> {
    return apiService.get(`/discovery/v2/permissions/${clientId}`);
  }

  async getAppPermissionTree(clientId: string): Promise<any> {
    return apiService.get(`/discovery/v2/permissions/${clientId}/tree`);
  }

  // Azure AD Groups
  async searchAzureGroups(search?: string, top: number = 20): Promise<{
    groups: Array<{
      id: string;
      displayName: string;
      description?: string;
    }>;
  }> {
    const params = new URLSearchParams();
    if (search) params.append('search', search);
    params.append('top', top.toString());

    return apiService.get(`/auth/admin/azure-groups?${params.toString()}`);
  }

  // Rotation Management
  async manualRotationCheck(): Promise<any> {
    return apiService.post('/auth/admin/rotation/check');
  }

  async getRotationPolicies(): Promise<any> {
    return apiService.get('/auth/admin/rotation/policies');
  }

  async setRotationPolicy(
    clientId: string,
    daysBeforeExpiry: number,
    gracePeriodHours: number,
    autoRotate: boolean,
    notifyWebhook?: string
  ): Promise<any> {
    return apiService.post(`/auth/admin/apps/${clientId}/rotation-policy`, {
      days_before_expiry: daysBeforeExpiry,
      grace_period_hours: gracePeriodHours,
      auto_rotate: autoRotate,
      notify_webhook: notifyWebhook
    });
  }

  // Debug endpoints
  async getDebugInfo(): Promise<any> {
    return apiService.get('/auth/debug/timestamps');
  }

  async getAdminCheck(): Promise<any> {
    return apiService.get('/auth/debug/admin-check');
  }

  async getStorageDebug(): Promise<any> {
    return apiService.get('/debug/storage');
  }

  // Token Template Management
  async getTokenTemplates(): Promise<any> {
    return apiService.get('/auth/admin/token-templates');
  }

  async getTokenTemplate(name: string): Promise<any> {
    return apiService.get(`/auth/admin/token-templates/${encodeURIComponent(name)}`);
  }

  async saveTokenTemplate(template: any): Promise<any> {
    return apiService.post('/auth/admin/token-templates', template);
  }

  async deleteTokenTemplate(name: string): Promise<any> {
    return apiService.delete(`/auth/admin/token-templates/${encodeURIComponent(name)}`);
  }

  async importTokenTemplates(templates: any[]): Promise<any> {
    return apiService.post('/auth/admin/token-templates/import', { templates });
  }
}

export const adminService = new AdminService();
export default adminService;

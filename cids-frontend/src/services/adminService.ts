import apiService from './api';
import type {
  TokenListResponse,
  AppInfo,
  APIKey,
  APIKeyCreationResponse,
  CreateAPIKeyRequest,
  TokenActivityResponse,
  AppRegistrationResult
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

  async getActivityStats(): Promise<{ items: Array<{ type: string; count: number }>; count: number }> {
    return apiService.get('/auth/admin/logs/activity-stats');
  }

  async getActivityLogCount(userEmail?: string): Promise<{ count: number }> {
    const params = userEmail ? `?user_email=${encodeURIComponent(userEmail)}` : '';
    return apiService.get(`/auth/admin/logs/activity-count${params}`);
  }

  async logAppUsage(appName: string, clientId: string): Promise<void> {
    try {
      await apiService.post('/auth/admin/log-app-usage', {
        app_name: appName,
        client_id: clientId,
        action: `flw.${appName.toLowerCase()}`
      });
    } catch (error) {
      console.error('Failed to log app usage:', error);
    }
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

  async getAppsStats(): Promise<{
    apps: { total: number; active: number; inactive: number };
    tokens: { active: number };
    api_keys: { total: number };
  }> {
    return apiService.get('/auth/admin/apps/stats');
  }

  async getDashboardStats(): Promise<any> {
    return apiService.get('/auth/admin/dashboard/stats');
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
    const res = await apiService.get(`/auth/admin/apps/${clientId}/api-keys`);
    // Backend returns a raw array; adapt to expected shape
    if (Array.isArray(res)) {
      return { api_keys: res as APIKey[] };
    }
    return res;
  }

  async createAPIKey(clientId: string, request: CreateAPIKeyRequest): Promise<APIKeyCreationResponse> {
    return apiService.post(`/auth/admin/apps/${clientId}/api-keys`, request);
  }

  async revokeAPIKey(clientId: string, keyId: string): Promise<void> {
    return apiService.delete(`/auth/admin/apps/${clientId}/api-keys/${keyId}`);
  }

  async checkActiveApiKey(clientId: string): Promise<{ has_active_key: boolean }> {
    return apiService.get(`/auth/admin/apps/${clientId}/has-active-api-key`);
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
  async createRolePermissions(clientId: string, roleData: { role_name: string; permissions: string[]; denied_permissions?: string[]; description?: string; rls_filters?: any; a2a_only?: boolean }): Promise<any> {
    return apiService.post(`/permissions/${clientId}/roles`, roleData);
  }

  async updateRolePermissions(clientId: string, roleName: string, permissionData: { permissions: string[]; denied_permissions?: string[]; description?: string; rls_filters?: any; a2a_only?: boolean }): Promise<any> {
    return apiService.put(`/permissions/${clientId}/roles/${roleName}`, permissionData);
  }

  async deleteRolePermissions(clientId: string, roleName: string): Promise<any> {
    return apiService.delete(`/permissions/${clientId}/roles/${roleName}`);
  }

  async triggerDiscovery(clientId: string, force: boolean = true): Promise<any> {
    console.log('🚀 [DISCOVERY] ===== INICIANDO PROCESO DE DISCOVERY =====');
    console.log('📋 [DISCOVERY] Client ID:', clientId);
    console.log('🔄 [DISCOVERY] Force discovery:', force);
    console.log('📝 [DISCOVERY] PASOS DEL PROCESO:');
    console.log('  1️⃣ Obtener endpoints de la aplicación');
    console.log('  2️⃣ Guardar discovered_permissions (base)');
    console.log('  3️⃣ Guardar endpoints en discovery_endpoints');
    console.log('  4️⃣ Guardar field_metadata con flags de sensibilidad');
    console.log('  5️⃣ Actualizar estado de activity_log');
    console.log('  6️⃣ RECLASIFICACIÓN: Generar permisos por categoría (pii, phi, financial, sensitive)');
    console.log('⏳ [DISCOVERY] Enviando petición al backend...');
    
    const result = await apiService.post(`/discovery/endpoints/${clientId}?force=${force}`);
    
    console.log('✅ [DISCOVERY] Respuesta recibida:', result);
    console.log('🎯 [DISCOVERY] RECLASIFICACIÓN COMPLETADA - Revisa discovered_permissions para ver categorías');
    console.log('🔍 [DISCOVERY] Verifica en la BD: SELECT resource, action, category FROM cids.discovered_permissions');
    
    return result;
  }

  // Enhanced Discovery Methods
  async batchDiscovery(clientIds: string[], force: boolean = true): Promise<any> {
    return apiService.post('/discovery/batch', { client_ids: clientIds, force });
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

  async getPermissionsByCategory(clientId: string): Promise<any> {
    return apiService.get(`/discovery/permissions/${clientId}/categories`);
  }

  // Roles (Admin)
  async getAppRoles(clientId: string): Promise<string[]> {
    const res: any = await apiService.get(`/permissions/${clientId}/roles`);
    const rolesObj = res?.roles || {};
    return Object.keys(rolesObj);
  }

  async getAppRolesWithMetadata(clientId: string): Promise<Record<string, { permissions: string[]; metadata: any }>> {
    const res: any = await apiService.get(`/permissions/${clientId}/roles`);
    return res?.roles || {};
  }

  // A2A Role Mappings (App-level defaults)
  async getA2ARoleMappings(callerId: string): Promise<Record<string, string[]>> {
    const res: any = await apiService.get(`/auth/admin/apps/${callerId}/a2a-role-mappings`);
    // Response shape: { [callerId]: { target_app_id: [roles] } }
    const mapping = res?.[callerId] || {};
    return mapping as Record<string, string[]>;
  }

  async putA2ARoleMappings(callerId: string, mappings: Record<string, string[]>): Promise<void> {
    await apiService.put(`/auth/admin/apps/${callerId}/a2a-role-mappings`, { mappings });
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

  async refreshCache(): Promise<{ status: string; message: string }> {
    return apiService.post('/auth/admin/refresh-cache');
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

  // A2A Token Minting (for testing from UI)
  async mintA2AToken(apiKey: string, body?: { template_name?: string; audience?: string }): Promise<{ access_token: string; token_type: string; expires_in: number; token_id?: string }>{
    return apiService.post('/auth/token/a2a', body || {}, {
      headers: { Authorization: `Bearer ${apiKey}` }
    });
  }

  // User Photo Management
  async getUserPhoto(email: string): Promise<{ has_photo: boolean; photo_path: string | null }> {
    return apiService.get(`/api/user/photo/${encodeURIComponent(email)}`);
  }

  // A2A Permission Management
  async getA2aPermissions(): Promise<any[]> {
    console.log('🚀 [AdminService] Fetching A2A permissions from backend...');
    try {
      const response = await apiService.get('/auth/admin/a2a-permissions');
      console.log('✅ [AdminService] A2A permissions fetched:', response);
      return response;
    } catch (error) {
      console.error('❌ [AdminService] Error fetching A2A permissions:', error);
      throw error;
    }
  }

  async createA2aPermission(data: any): Promise<any> {
    return apiService.post('/auth/admin/a2a-permissions', data);
  }

  async updateA2aPermission(id: string, data: any): Promise<any> {
    return apiService.put(`/auth/admin/a2a-permissions/${id}`, data);
  }

  async deleteA2aPermission(id: string): Promise<void> {
    return apiService.delete(`/auth/admin/a2a-permissions/${id}`);
  }

  async getRegisteredApps(): Promise<any[]> {
    try {
      const response = await apiService.get('/auth/admin/apps');
      return response || [];
    } catch (error) {
      console.error('Failed to get registered apps:', error);
      return [];
    }
  }
}

export const adminService = new AdminService();
export default adminService;

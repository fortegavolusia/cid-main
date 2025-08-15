# CIDS IAM Extensions Summary

## What's New

The CIDS authentication service has been extended with comprehensive IAM (Identity and Access Management) features that enable:

### 🔑 JWKS & Service Discovery
- `GET /.well-known/jwks.json` - Public keys for token validation
- `GET /.well-known/cids-config` - Service metadata and endpoints

### 🎯 App Endpoints Registry
- `PUT /apps/{app}/endpoints` - Define which endpoints each app handles
- Supports wildcards for flexible routing
- Prevents endpoint conflicts between apps

### 👥 Advanced Role Management
- `PUT /apps/{app}/roles` - Define app-specific roles with permissions
- `PUT /role-mappings` - Map Azure AD groups to app roles
- Tenant-aware mappings for multi-tenant scenarios

### 📋 Policy Documents
- `PUT /policy/{app}` - Define permissions, role matrices, and ABAC rules
- Versioned policies with audit trail
- Attribute-based access control (ABAC) support

### 🎫 Enhanced Tokens
- Shorter TTL (5-10 minutes) for access tokens
- httpOnly refresh tokens (7 days)
- Includes roles, permissions, and user attributes
- Version 2.0 token format with backward compatibility

### 🔍 Effective Identity
- `GET /iam/me` - Real-time permission computation
- Shows all roles and effective permissions across apps
- Includes user attributes and token metadata

### 📝 Comprehensive Audit Logging
- All IAM changes are logged
- Queryable audit trail
- Who changed what and when

## Quick Example

```bash
# 1. Register app endpoints
curl -X PUT https://cids.example.com/apps/app_123/endpoints \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"endpoints": [{"method": "GET", "path": "/api/users/*", "desc": "User APIs"}]}'

# 2. Define roles
curl -X PUT https://cids.example.com/apps/app_123/roles \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"roles": [{"name": "admin", "description": "Admin role", "permissions": ["users.*"]}]}'

# 3. Map AD groups to roles
curl -X PUT https://cids.example.com/role-mappings \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"mappings": [{"azure_group": "IT Admins", "app_client_id": "app_123", "role": "admin"}]}'

# 4. Check effective permissions
curl https://cids.example.com/iam/me \
  -H "Authorization: Bearer $USER_TOKEN"
```

## Files Added

- `jwks_handler.py` - JWKS generation and metadata
- `app_endpoints.py` - Endpoint registry management
- `roles_manager.py` - Role and mapping management
- `policy_manager.py` - Policy document handling
- `audit_logger.py` - Audit trail functionality
- `main_iam_updates.py` - Integration code for main.py
- `k8s/` - Kubernetes deployment manifests
- `IAM-GUIDE.md` - Comprehensive IAM documentation
- `DEPLOY-K8S.md` - Kubernetes deployment guide

## Deployment

### Docker
```bash
# Build and run
docker build -t cids-auth:v2 .
docker run -p 8000:8000 --env-file .env cids-auth:v2
```

### Kubernetes
```bash
# Deploy to K8s
kubectl apply -k k8s/
```

### GitHub Container Registry
```bash
# Push to GHCR
docker tag cids-auth:v2 ghcr.io/jnbaileyiv-cto/cids-2:v2.0.0
docker push ghcr.io/jnbaileyiv-cto/cids-2:v2.0.0
```

## Key Benefits

1. **Dynamic Permissions** - No need to redeploy when permissions change
2. **Fine-grained Access** - Role-based and attribute-based controls
3. **Multi-tenant Ready** - Tenant-aware role mappings
4. **Audit Compliance** - Full audit trail of all changes
5. **Standard Compliant** - JWKS and OAuth 2.0 compatible
6. **Flexible Routing** - Apps can claim their endpoints with wildcards

## Next Steps

1. Integrate the code from `main_iam_updates.py` into your `main.py`
2. Test the IAM features locally
3. Deploy to your Kubernetes cluster
4. Configure your apps to use the new IAM endpoints

See `IAM-GUIDE.md` for detailed usage examples and `DEPLOY-K8S.md` for deployment instructions.
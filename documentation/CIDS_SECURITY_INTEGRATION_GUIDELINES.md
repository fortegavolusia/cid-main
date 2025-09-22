# CIDS Security Integration Guidelines
## Comprehensive Security Requirements for Application Integration

Version: 2.0
Last Updated: September 2025
Classification: OFFICIAL

---

## Table of Contents
1. [Overview](#overview)
2. [Security Architecture](#security-architecture)
3. [Required Endpoints](#required-endpoints)
4. [Authentication Flow](#authentication-flow)
5. [API Key Management](#api-key-management)
6. [Discovery Protocol](#discovery-protocol)
7. [Permission Categories](#permission-categories)
8. [Token Security](#token-security)
9. [Service-to-Service Authentication](#service-to-service-authentication)
10. [Audit and Compliance](#audit-and-compliance)
11. [Implementation Checklist](#implementation-checklist)

---

## 1. Overview

The Centralized Identity Discovery Service (CIDS) provides enterprise-grade authentication, authorization, and row-level security (RLS) for all integrated applications. This document outlines mandatory security requirements for applications integrating with CIDS.

### Core Security Principles
- **Zero Trust Architecture**: Never trust, always verify
- **Principle of Least Privilege**: Grant minimum required permissions
- **Defense in Depth**: Multiple layers of security controls
- **Audit Everything**: Complete activity logging and monitoring

---

## 2. Security Architecture

### 2.1 Token-Based Security Model
```
┌─────────────┐     ┌──────────┐     ┌─────────────┐
│   Browser   │────▶│   CIDS   │◀────│ Application │
└─────────────┘     └──────────┘     └─────────────┘
      JWT              Validate          API Key
                      & Authorize
```

### 2.2 Security Layers
1. **Transport Security**: HTTPS/TLS 1.3 mandatory
2. **Authentication**: JWT tokens with RSA256 signatures
3. **Authorization**: Role-based permissions with field-level granularity
4. **Row-Level Security**: SQL WHERE clause filters per field
5. **API Key Authentication**: Service-to-service communication
6. **IP & Device Binding**: Token bound to originating IP/device
7. **Audit Logging**: All actions logged with UUID tracking

---

## 3. Required Endpoints

Your application MUST implement these endpoints:

### 3.1 SSO Callback Endpoint
```http
POST /auth/sso
Content-Type: application/json

{
  "access_token": "jwt_token_from_cids"
}

Response:
{
  "success": true,
  "session_id": "uuid",
  "redirect_url": "https://app.example.com/dashboard"
}
```

**Security Requirements:**
- Validate token with CIDS before creating session
- Include service API key in validation request
- Store minimal user data in session
- Implement session timeout (default: 24 hours)

### 3.2 Discovery Endpoint
```http
GET /discovery/endpoints
Authorization: Bearer {jwt_token}

Response:
{
  "service_name": "Application Name",
  "app_name": "Application Name",
  "app_id": "app_client_id",
  "version": "2.0",
  "last_updated": "2025-09-14T00:00:00Z",
  "endpoints": [...],
  "permissions_format": "structured"
}
```

**Security Requirements:**
- Require valid JWT for discovery
- Return consistent app_id matching registration
- Version MUST be "2.0" for field-level permissions
- Update last_updated on any endpoint change

### 3.3 Health Check Endpoint
```http
GET /health

Response:
{
  "status": "healthy",
  "service": "Application Name",
  "version": "1.0.0",
  "database": "healthy"
}
```

---

## 4. Authentication Flow

### 4.1 Initial Authentication
```python
# Step 1: User redirected to CIDS login
redirect_url = f"{CIDS_BASE_URL}/auth/login?app_id={APP_ID}&redirect_uri={CALLBACK_URL}"

# Step 2: After CIDS authentication, receive token at callback
async def sso_callback(token: str):
    # Step 3: Validate token with CIDS (include API key for proxy validation)
    headers = {
        "Authorization": f"Bearer {token}",
        "X-API-Key": SERVICE_API_KEY  # Required for IP validation bypass
    }

    response = await httpx.get(
        f"{CIDS_BASE_URL}/auth/validate",
        headers=headers
    )

    if response.json()["valid"]:
        # Create session
        create_user_session(response.json())
```

### 4.2 Token Validation for Each Request
```python
async def validate_request(token: str) -> dict:
    """Validate every API request"""
    headers = {
        "Authorization": f"Bearer {token}",
        "X-API-Key": SERVICE_API_KEY  # Always include for service proxy
    }

    response = await httpx.get(
        f"{CIDS_BASE_URL}/auth/validate",
        headers=headers
    )

    if not response.json()["valid"]:
        raise HTTPException(401, "Invalid token")

    return response.json()  # Contains user info and permissions
```

---

## 5. API Key Management

### 5.1 API Key Requirements
- **Generation**: Only through CIDS Admin UI or API
- **Format**: `cids_ak_{32_character_alphanumeric}`
- **Storage**: Store securely in environment variables
- **Rotation**: Every 90 days (automated reminders)
- **Revocation**: Immediate upon compromise

### 5.2 API Key Usage
```python
# Environment variable
CIDS_API_KEY = os.getenv("CIDS_API_KEY")

# Always include in CIDS requests
headers = {
    "Authorization": f"Bearer {user_token}",
    "X-API-Key": CIDS_API_KEY  # Service authentication
}
```

### 5.3 API Key Security Rules
1. **One Active Key**: Only one API key active per application
2. **Automatic Deactivation**: Creating new key deactivates old ones
3. **Usage Tracking**: Every use updates `last_used_at` and `usage_count`
4. **Activity Logging**: All API key operations logged to `activity_log`

---

## 6. Discovery Protocol

### 6.1 Required Discovery Endpoints
Applications MUST expose these endpoints:
```
GET /discovery/endpoints  # Public endpoint for CIDS discovery
GET /discovery/metadata   # Protected endpoint (optional, requires API key)
POST /discovery/refresh   # Trigger self-registration with CIDS (requires API key)
```

### 6.2 CRITICAL: Permission Generation from Endpoints
**IMPORTANT**: CIDS generates permissions automatically from the `resource` and `action` fields **within each endpoint**, NOT from a separate `permissions` array.

**Discovery Finding (September 2025)**: After extensive testing, we discovered that CIDS ignores any `permissions` array in the discovery response. Permissions are ONLY generated from the `resource` and `action` fields that must be present in each endpoint definition.

#### Correct Format (REQUIRED for permission generation):
```json
{
  "endpoints": [
    {
      "path": "/api/employees",
      "method": "GET",
      "resource": "employees",  // REQUIRED for permission generation
      "action": "read",         // REQUIRED for permission generation
      "description": "List employees",
      "response_fields": {...}
    }
  ]
}
```

#### Incorrect Format (permissions will NOT be generated):
```json
{
  "permissions": [...],  // This field is IGNORED by CIDS
  "endpoints": [
    {
      "path": "/api/employees",
      "method": "GET",  // Method alone is NOT enough
      "description": "List employees"
      // Missing resource and action = NO permissions generated
    }
  ]
}
```

### 6.3 Complete Discovery Response Format v2.0
**CRITICAL**: This is the EXACT format required for successful discovery:
```json
{
  "version": "2.0",
  "app_id": "app_c6d42c16fe8a4b9b",
  "app_name": "Application Name",
  "app_version": "1.0.0",
  "base_url": "http://service:port",
  "last_updated": "2025-01-14T10:00:00Z",
  "authentication": {
    "type": "api_key",
    "header": "X-API-Key",
    "description": "CIDS-issued API key required for all endpoints"
  },
  "field_categories": {
    "BASE": ["id", "status", "created_at", "updated_at"],
    "PII": ["name", "email", "phone", "address"],
    "SENSITIVE": ["ssn", "account_number", "routing_number"],
    "FINANCIAL": ["balance", "amount", "payment"]
  },
  "permissions": [
    {
      "resource": "data_base",
      "action": "read",
      "description": "Read BASE category fields",
      "category": "BASE"
    },
    {
      "resource": "data_pii",
      "action": "read",
      "description": "Read PII category fields",
      "category": "PII"
    },
    {
      "resource": "data_sensitive",
      "action": "read",
      "description": "Read SENSITIVE category fields",
      "category": "SENSITIVE"
    },
    {
      "resource": "data_financial",
      "action": "read",
      "description": "Read FINANCIAL category fields",
      "category": "FINANCIAL"
    }
  ],
  "endpoints": [
    {
      "path": "/api/resource/{id}",
      "method": "GET",
      "resource": "resource_name",    // REQUIRED - used for permission generation
      "action": "read",               // REQUIRED - used for permission generation
      "description": "Get resource by ID",
      "parameters": ["id"],
      "response_fields": {
        "id": {"type": "string", "category": "BASE"},
        "name": {"type": "string", "category": "PII"},
        "ssn": {"type": "string", "category": "SENSITIVE"},
        "balance": {"type": "number", "category": "FINANCIAL"}
      }
    }
  ]
}
```

### 6.2 Discovery Requirements
1. **Authentication**: JWT required for discovery
2. **Real-time**: Discovery must reflect current API state
3. **Field Metadata**: Every field must declare its sensitivity category
4. **Permission Format**: `resource.action.category`

---

## 7. Permission Categories

### 7.1 Standard Categories
| Category | Description | Example Fields | Permission Suffix |
|----------|-------------|----------------|-------------------|
| BASE | Public information | name, department | `.base` |
| PII | Personally Identifiable | email, phone | `.pii` |
| SENSITIVE | Highly restricted | SSN, medical | `.sensitive` |
| FINANCIAL | Financial data | salary, bank | `.financial` |
| WILDCARD | All categories | * | `.wildcard` |

### 7.2 Permission Naming Convention
```
Format: {resource}.{action}.{category}
Examples:
- employees.read.base
- employees.write.sensitive
- payments.delete.financial
- employees.read.wildcard (grants all read permissions)
```

### 7.3 Permission Enforcement
```python
def check_permission(user_permissions: dict, required: str) -> bool:
    """Check if user has required permission"""
    app_permissions = user_permissions.get(APP_ID, [])

    # Check exact permission
    if required in app_permissions:
        return True

    # Check wildcard
    resource, action, category = required.split('.')
    wildcard = f"{resource}.{action}.wildcard"
    return wildcard in app_permissions
```

---

## 8. Token Security

### 8.1 JWT Token Structure
```json
{
  "sub": "user_id",
  "email": "user@example.com",
  "name": "User Name",
  "groups": ["AD_Group_1", "AD_Group_2"],
  "permissions": {
    "app_client_id": [
      "employees.read.base",
      "employees.read.pii"
    ]
  },
  "rls_filters": {
    "app_client_id": {
      "employees": {
        "department": ["department = 'IT'", "department = 'HR'"]
      }
    }
  },
  "bound_ip": "192.168.1.100",
  "bound_device": "device_fingerprint_hash",
  "iat": 1234567890,
  "exp": 1234571490,
  "jti": "unique_token_id"
}
```

### 8.2 Token Security Features
1. **IP Binding**: Token bound to originating IP
2. **Device Binding**: Token bound to device fingerprint
3. **Short Lifetime**: 1 hour default, max 24 hours
4. **Refresh Tokens**: Separate refresh token for renewal
5. **Revocation**: Immediate revocation capability
6. **Audit Trail**: All token operations logged

### 8.3 Token Validation Rules
```python
def validate_token_security(token_claims: dict, request: Request) -> bool:
    """Comprehensive token security validation"""

    # 1. Check expiration
    if token_claims['exp'] < time.time():
        return False

    # 2. Check IP binding (unless service proxy)
    if not is_service_proxy and token_claims.get('bound_ip'):
        if token_claims['bound_ip'] != request.client.host:
            log_security_event("IP_MISMATCH", token_claims)
            return False

    # 3. Check device binding
    if token_claims.get('bound_device'):
        device_hash = hash_device(request.headers.get('User-Agent'))
        if token_claims['bound_device'] != device_hash:
            log_security_event("DEVICE_MISMATCH", token_claims)
            return False

    # 4. Check revocation
    if is_token_revoked(token_claims['jti']):
        return False

    return True
```

---

## 9. Service-to-Service Authentication

### 9.1 Proxy Validation Pattern
When your service validates user tokens on behalf of users:

```python
async def proxy_validate_token(user_token: str) -> dict:
    """Service validates user token with its API key"""
    headers = {
        "Authorization": f"Bearer {user_token}",
        "X-API-Key": SERVICE_API_KEY  # Service authentication
    }

    # CIDS will:
    # 1. Validate the user token
    # 2. Authenticate the service via API key
    # 3. Bypass IP validation (service proxy pattern)
    # 4. Log the proxy validation

    response = await httpx.get(
        f"{CIDS_BASE_URL}/auth/validate",
        headers=headers
    )

    return response.json()
```

### 9.2 Direct Service Authentication
For service-only operations:

```python
async def service_only_operation():
    """Service authenticates with API key only"""
    headers = {
        "Authorization": f"Bearer {SERVICE_API_KEY}"
    }

    # Service gets limited permissions
    response = await httpx.get(
        f"{CIDS_BASE_URL}/api/service-endpoint",
        headers=headers
    )
```

---

## 10. Audit and Compliance

### 10.1 Required Logging
Every application MUST log:

```python
@dataclass
class AuditLog:
    activity_id: str  # UUID from UUID service
    timestamp: datetime
    user_email: str
    user_id: str
    action: str  # login, logout, read, write, delete
    resource: str  # employees, payments, etc.
    resource_id: str
    success: bool
    ip_address: str
    user_agent: str
    details: dict  # Additional context
```

### 10.2 Activity Types to Log
- **Authentication**: login, logout, token_refresh
- **Authorization**: permission_granted, permission_denied
- **Data Access**: read, write, update, delete
- **Security Events**: ip_mismatch, device_mismatch, invalid_token
- **API Key Operations**: key_created, key_used, key_revoked

### 10.3 Log Retention
- **Activity Logs**: Minimum 90 days
- **Security Events**: Minimum 1 year
- **Audit Trail**: Immutable, append-only

---

## 11. Complete Implementation Checklist

### Phase 1: Application Registration ✅
- [ ] Register application in CIDS Admin UI
- [ ] Set application name and client_id
- [ ] Configure discovery endpoint URL: `http://service:port/discovery/endpoints`
- [ ] Generate and save API key
- [ ] Store API key securely in environment variables

### Phase 2: Discovery Endpoint Implementation 🔍
**CRITICAL - Most Common Errors:**
- [ ] Create `/discovery/endpoints` endpoint (PUBLIC, no auth required)
- [ ] Ensure response includes `version: "2.0"`
- [ ] **MUST** include `resource` and `action` in EACH endpoint
- [ ] Include `app_id` matching your client_id exactly
- [ ] Include `app_name` (not `service_name`)
- [ ] Include `last_updated` field in ISO format
- [ ] Categorize ALL fields as BASE, PII, SENSITIVE, or FINANCIAL
- [ ] Test endpoint is accessible: `curl http://localhost:port/discovery/endpoints`

### Phase 3: Permission Structure ⚠️
**CRITICAL - Permissions are generated from endpoints, NOT from a permissions array:**
```json
{
  "endpoints": [
    {
      "path": "/api/resource",
      "method": "GET",
      "resource": "resource_name",  // REQUIRED for permissions
      "action": "read",             // REQUIRED for permissions
      "description": "Description",
      "response_fields": {...}
    }
  ]
}
```

### Phase 4: Authentication Implementation 🔐
- [ ] Implement `/auth/callback` for OAuth flow (if using user auth)
- [ ] Add `X-API-Key` header to ALL requests to CIDS
- [ ] Implement token validation using CIDS `/auth/validate`
- [ ] Handle token refresh with `/auth/token` endpoint
- [ ] Store tokens securely (never in code or logs)

### Phase 5: API Key Validation 🔑
```python
# Validate API key with CIDS
headers = {"Authorization": f"Bearer {token}"}
if CIDS_API_KEY:
    headers["X-API-Key"] = CIDS_API_KEY  # Required for service-to-service

response = await client.get(
    f"{CIDS_BASE_URL}/auth/validate",
    headers=headers
)
```

### Phase 6: Field Categories Implementation 📊
- [ ] Define field categories in config:
```python
FIELD_CATEGORIES = {
    'BASE': ['id', 'status', 'created_at'],
    'PII': ['name', 'email', 'phone'],
    'SENSITIVE': ['ssn', 'account_number'],
    'FINANCIAL': ['balance', 'salary', 'payment']
}
```
- [ ] Apply categories to ALL response fields
- [ ] Document category requirements

### Phase 7: Database Schema in Supabase 💾
**IMPORTANT: Each service must have its own schema in the shared database**

#### Step 1: Create Service Schema
```sql
-- Example for Bank System
CREATE SCHEMA IF NOT EXISTS volusia_bank;

-- Example for HR System
CREATE SCHEMA IF NOT EXISTS hr_app;
```

#### Step 2: Create Required Tables
```sql
-- Switch to your schema
SET search_path TO volusia_bank;

-- Example tables for Bank System
CREATE TABLE IF NOT EXISTS accounts (
    account_id VARCHAR(50) PRIMARY KEY,
    employee_id VARCHAR(50) NOT NULL,
    account_number VARCHAR(255) NOT NULL, -- Encrypt in production
    routing_number VARCHAR(255) NOT NULL, -- Encrypt in production
    account_type VARCHAR(20) CHECK (account_type IN ('checking', 'savings')),
    balance DECIMAL(15, 2) DEFAULT 0.00,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
);

-- API Access Log for audit trail
CREATE TABLE IF NOT EXISTS api_access_log (
    access_id VARCHAR(50) PRIMARY KEY,
    api_key_id VARCHAR(50),
    endpoint VARCHAR(255) NOT NULL,
    employee_id VARCHAR(50),
    accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX idx_accounts_employee ON accounts(employee_id);
CREATE INDEX idx_api_log_key ON api_access_log(api_key_id);
```

#### Step 3: Grant Permissions
```sql
GRANT ALL PRIVILEGES ON SCHEMA volusia_bank TO postgres;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA volusia_bank TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA volusia_bank TO postgres;
```

#### Step 4: Execute Schema Creation
```bash
# Using Docker
docker exec -i supabase_db_mi-proyecto-supabase psql -U postgres -d postgres < create_schema.sql

# Or directly with psql
PGPASSWORD=postgres psql -h localhost -p 54322 -U postgres -d postgres < create_schema.sql
```

#### Checklist:
- [ ] Create application-specific schema (e.g., `volusia_bank`, `hr_app`)
- [ ] Create all necessary tables with proper data types
- [ ] Add CHECK constraints for data validation
- [ ] Create indexes for frequently queried columns
- [ ] Implement audit logging table
- [ ] Grant appropriate permissions
- [ ] Test database connectivity from application
- [ ] Verify schema isolation between services

### Phase 8: Docker Configuration 🐳
- [ ] Create Dockerfile with non-root user
- [ ] Configure docker-compose.yml with proper networks
- [ ] Set up health checks
- [ ] Configure environment variables
- [ ] Test container builds and runs

### Phase 9: Testing Discovery 🧪
- [ ] Run discovery from CIDS Admin UI
- [ ] Verify permissions are created (check database)
- [ ] Check for error messages in CIDS logs
- [ ] Validate field metadata is saved
- [ ] Test with API key authentication

### Phase 10: Security Hardening 🛡️
- [ ] Enable HTTPS in production
- [ ] Implement rate limiting
- [ ] Add request validation
- [ ] Enable CORS properly
- [ ] Implement timeout handling
- [ ] Add security headers

### Phase 11: Monitoring & Logging 📈
- [ ] Implement structured logging
- [ ] Log all API access
- [ ] Monitor error rates
- [ ] Set up alerts for failures
- [ ] Track API key usage

### Phase 12: Production Deployment ✈️
- [ ] Configure production environment variables
- [ ] Set up SSL certificates
- [ ] Configure load balancing
- [ ] Implement backup strategy
- [ ] Create runbook documentation

### Common Issues & Solutions 🔧

| Issue | Solution |
|-------|----------|
| "Discovery failed: 404 Not Found" | Ensure `/discovery/endpoints` is public and accessible |
| "0 permissions created" | Add `resource` and `action` to each endpoint |
| "Invalid API key" | Check API key is active in CIDS, include X-API-Key header |
| "Field metadata not saved" | Ensure fields have `category` attribute |
| "Discovery version 1" | Update response to include `version: "2.0"` |

### Validation Commands 🔍
```bash
# Test discovery endpoint
curl http://localhost:PORT/discovery/endpoints

# Check permissions in database
docker exec -i [db-container] psql -U postgres -c \
  "SELECT resource, action FROM cids.discovered_permissions WHERE client_id='YOUR_CLIENT_ID'"

# Check API key validity
curl -H "X-API-Key: YOUR_KEY" http://localhost:8001/auth/validate
```

### Real Example: Bank System Implementation ✅

**Service Details:**
- Name: Volusia Bank
- Client ID: app_c6d42c16fe8a4b9b
- Port: 8006
- Schema: volusia_bank

**Working Discovery Format:**
```json
{
  "version": "2.0",
  "app_id": "app_c6d42c16fe8a4b9b",
  "app_name": "Bank System",
  "endpoints": [
    {
      "path": "/accounts/{employee_id}/balance",
      "method": "GET",
      "resource": "accounts",     // ✅ REQUIRED
      "action": "read",           // ✅ REQUIRED
      "description": "Get account balance",
      "response_fields": {
        "balance": {"type": "number", "category": "FINANCIAL"},
        "account_type": {"type": "string", "category": "BASE"}
      }
    },
    {
      "path": "/payroll/process",
      "method": "POST",
      "resource": "payroll",      // ✅ REQUIRED
      "action": "write",          // ✅ REQUIRED
      "description": "Process payroll",
      "request_fields": {
        "ssn": {"type": "string", "category": "SENSITIVE"},
        "payment_amount": {"type": "number", "category": "FINANCIAL"}
      }
    }
  ]
}
```

**This generates these permissions in CIDS:**
- accounts.read
- payroll.write
- (Plus category-based permissions if configured)

---

## Example Implementation (Python/FastAPI)

```python
# config.py
import os
from typing import Optional

# CIDS Configuration
CIDS_BASE_URL = os.getenv("CIDS_BASE_URL", "http://localhost:8000")
CIDS_CLIENT_ID = os.getenv("CIDS_CLIENT_ID")  # Your app's client_id
CIDS_API_KEY = os.getenv("CIDS_API_KEY")  # Your service API key

# Security Configuration
REQUIRE_HTTPS = os.getenv("REQUIRE_HTTPS", "true").lower() == "true"
SESSION_TIMEOUT = int(os.getenv("SESSION_TIMEOUT", "86400"))  # 24 hours

# auth.py
from fastapi import Depends, HTTPException, Header
import httpx

async def validate_token(authorization: Optional[str] = Header(None)) -> dict:
    """Validate JWT token with CIDS"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Invalid authorization header")

    token = authorization.replace("Bearer ", "")

    async with httpx.AsyncClient() as client:
        headers = {
            "Authorization": f"Bearer {token}",
            "X-API-Key": CIDS_API_KEY  # Always include for proxy validation
        }

        response = await client.get(
            f"{CIDS_BASE_URL}/auth/validate",
            headers=headers,
            timeout=10.0
        )

        if response.status_code != 200:
            raise HTTPException(401, "Token validation failed")

        data = response.json()
        if not data.get("valid"):
            raise HTTPException(401, "Invalid token")

        return data  # Contains user info and permissions

def check_permission(user_data: dict, required_permission: str) -> bool:
    """Check if user has required permission"""
    permissions = user_data.get("permissions", {}).get(CIDS_CLIENT_ID, [])

    # Check exact permission
    if required_permission in permissions:
        return True

    # Check wildcard permission
    parts = required_permission.split(".")
    if len(parts) == 3:
        resource, action, _ = parts
        wildcard = f"{resource}.{action}.wildcard"
        if wildcard in permissions:
            return True

    return False

# main.py
from fastapi import FastAPI, Depends, HTTPException

app = FastAPI(title="CIDS-Compliant Application")

@app.post("/auth/sso")
async def sso_callback(request: dict):
    """Handle SSO callback from CIDS"""
    token = request.get("access_token")
    if not token:
        raise HTTPException(400, "Token required")

    # Validate token with CIDS
    user_data = await validate_token(f"Bearer {token}")

    # Create session
    session_id = create_session(user_data)

    return {
        "success": True,
        "session_id": session_id,
        "redirect_url": f"/dashboard?session={session_id}"
    }

@app.get("/api/employees")
async def list_employees(user_data: dict = Depends(validate_token)):
    """List employees with permission check"""

    # Check base permission
    if not check_permission(user_data, "employees.read.base"):
        raise HTTPException(403, "Insufficient permissions")

    # Build response based on permissions
    employees = get_employees_from_db()

    # Filter fields based on permissions
    filtered_employees = []
    for emp in employees:
        filtered_emp = {"id": emp["id"]}  # Always visible

        if check_permission(user_data, "employees.read.base"):
            filtered_emp["name"] = emp["name"]
            filtered_emp["department"] = emp["department"]

        if check_permission(user_data, "employees.read.pii"):
            filtered_emp["email"] = emp["email"]
            filtered_emp["phone"] = emp["phone"]

        if check_permission(user_data, "employees.read.sensitive"):
            filtered_emp["ssn"] = emp["ssn"]

        if check_permission(user_data, "employees.read.financial"):
            filtered_emp["salary"] = emp["salary"]

        filtered_employees.append(filtered_emp)

    # Apply RLS filters if present
    rls_filters = user_data.get("rls_filters", {}).get(CIDS_CLIENT_ID, {})
    if "employees" in rls_filters:
        filtered_employees = apply_rls_filters(filtered_employees, rls_filters["employees"])

    # Log access
    log_activity(
        user_email=user_data.get("email"),
        action="employees.read",
        resource_count=len(filtered_employees)
    )

    return filtered_employees

@app.get("/discovery/endpoints")
async def discovery(user_data: dict = Depends(validate_token)):
    """CIDS Discovery endpoint"""
    return {
        "service_name": "Employee Management System",
        "app_name": "Employee Management System",
        "app_id": CIDS_CLIENT_ID,
        "version": "2.0",
        "last_updated": "2025-09-14T00:00:00Z",
        "endpoints": [
            {
                "endpoint": "/api/employees",
                "method": "GET",
                "description": "List all employees",
                "permission_required": "employees.read",
                "response_fields": [
                    {
                        "field": "id",
                        "type": "integer",
                        "always_visible": True
                    },
                    {
                        "field": "name",
                        "type": "string",
                        "category": "BASE",
                        "permission": "employees.read.base"
                    },
                    {
                        "field": "email",
                        "type": "string",
                        "category": "PII",
                        "permission": "employees.read.pii"
                    },
                    {
                        "field": "ssn",
                        "type": "string",
                        "category": "SENSITIVE",
                        "permission": "employees.read.sensitive"
                    },
                    {
                        "field": "salary",
                        "type": "number",
                        "category": "FINANCIAL",
                        "permission": "employees.read.financial"
                    }
                ]
            }
        ],
        "permissions_format": "structured"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Employee Management System",
        "version": "1.0.0",
        "database": check_database_health()
    }
```

---

## Security Contacts

For security issues, vulnerabilities, or questions:
- **Security Team**: security@cids.gov
- **CIDS Support**: support@cids.gov
- **Emergency**: +1-XXX-XXX-XXXX (24/7)

---

## Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-01-01 | CIDS Team | Initial release |
| 2.0 | 2025-09-14 | Security Team | Added API key management, proxy validation, RLS |

---

**END OF DOCUMENT**
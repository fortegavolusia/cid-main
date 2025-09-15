# 🔴 CIDS Mandatory Application Specification
## STRICT REQUIREMENTS FOR ALL CIDS-INTEGRATED APPLICATIONS

> ⚠️ **THIS IS A MANDATORY SPECIFICATION**
> All applications MUST implement EVERY requirement listed here to be compatible with CIDS.
> Non-compliance will result in integration failure.

---

## Table of Contents
1. [Mandatory Endpoints](#1-mandatory-endpoints)
2. [Required Response Formats](#2-required-response-formats)
3. [Mandatory Security Implementation](#3-mandatory-security-implementation)
4. [Required Field Classifications](#4-required-field-classifications)
5. [Compliance Checklist](#5-compliance-checklist)
6. [Validation Rules](#6-validation-rules)

---

## 1. MANDATORY ENDPOINTS

Every CIDS-integrated application **MUST** implement these endpoints:

### 1.1 Discovery Endpoint (REQUIRED)
```
GET /discovery/endpoints
```

**MUST return exactly this structure:**

```json
{
  "app_id": "string",           // MUST match assigned client_id EXACTLY
  "app_name": "string",          // REQUIRED, not empty
  "version": "2.0",              // MUST be exactly "2.0" (string)
  "last_updated": "string",      // MUST be ISO 8601: YYYY-MM-DDTHH:MM:SSZ
  "endpoints": [],               // REQUIRED array (see structure below)
  "response_fields": {}          // REQUIRED object (see structure below)
}
```

### 1.2 Health Check Endpoint (REQUIRED)
```
GET /health
```

**MUST return:**
```json
{
  "status": "healthy",           // or "unhealthy"
  "timestamp": "2025-09-15T12:00:00Z",
  "cids_compatible": true,
  "version": "2.0"
}
```

### 1.3 Token Validation Endpoint (REQUIRED)
```
GET /auth/validate
Headers: Authorization: Bearer {token}
```

**MUST:**
- Return 200 if token is valid
- Return 401 if token is invalid/expired
- Return 403 if IP binding fails

### 1.4 User Context Endpoint (REQUIRED)
```
GET /api/user/context
Headers: Authorization: Bearer {token}
```

**MUST return:**
```json
{
  "email": "user@volusia.gov",
  "permissions": ["array of active permissions"],
  "roles": ["array of user roles"],
  "filters": {"object with RLS filters"}
}
```

---

## 2. REQUIRED RESPONSE FORMATS

### 2.1 Endpoint Structure (for discovery)

**EVERY endpoint in your application MUST be documented as:**

```json
{
  "path": "/api/resource",      // EXACT path as implemented
  "method": "GET|POST|PUT|DELETE|PATCH",
  "description": "string",       // Human-readable description
  "resource": "string",          // Resource name (singular)
  "action": "read|create|update|delete|list",
  "response_fields": []          // Array of field names returned
}
```

### 2.2 Field Definition Structure

**EVERY field MUST be defined as:**

```json
{
  "field_name": {
    "type": "string|number|boolean|date|object|array",
    "description": "string",     // REQUIRED
    "category": "base|pii|phi|financial|sensitive",  // REQUIRED
    "nullable": true|false,      // REQUIRED
    "searchable": true|false,    // REQUIRED for list endpoints
    "filterable": true|false,    // REQUIRED for RLS
    "max_length": number,         // REQUIRED for strings
    "format": "string"            // REQUIRED for dates/special formats
  }
}
```

### 2.3 Standard CRUD Endpoints

**For EVERY resource, you MUST implement:**

| Operation | Method | Path | Required |
|-----------|--------|------|----------|
| List | GET | `/api/{resources}` | YES |
| Get One | GET | `/api/{resources}/{id}` | YES |
| Create | POST | `/api/{resources}` | YES |
| Update | PUT | `/api/{resources}/{id}` | YES |
| Partial Update | PATCH | `/api/{resources}/{id}` | Optional |
| Delete | DELETE | `/api/{resources}/{id}` | YES |
| Search | POST | `/api/{resources}/search` | YES |
| Bulk Operations | POST | `/api/{resources}/bulk` | Optional |

### 2.4 Pagination (REQUIRED for all LIST endpoints)

**MUST accept:**
```
GET /api/resources?page=1&limit=20&sort=field&order=asc|desc
```

**MUST return:**
```json
{
  "data": [],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 100,
    "total_pages": 5,
    "has_next": true,
    "has_prev": false
  }
}
```

### 2.5 Error Response Format (REQUIRED)

**ALL errors MUST follow:**

```json
{
  "error": {
    "code": "ERROR_CODE",        // UPPERCASE_SNAKE_CASE
    "message": "Human readable message",
    "details": {},                // Optional additional details
    "timestamp": "2025-09-15T12:00:00Z",
    "request_id": "uuid"         // For tracking
  }
}
```

**Required HTTP Status Codes:**
- 200: Success
- 201: Created
- 400: Bad Request
- 401: Unauthorized
- 403: Forbidden (permission denied)
- 404: Not Found
- 422: Validation Error
- 500: Internal Server Error

---

## 3. MANDATORY SECURITY IMPLEMENTATION

### 3.1 Token Validation (REQUIRED)

**EVERY authenticated endpoint MUST:**

```python
# Pseudo-code - implement in your language
function validate_request(request):
    token = extract_bearer_token(request.headers)

    if not token:
        return 401, "No token provided"

    # Validate JWT signature
    payload = validate_jwt(token, cids_public_key)

    if not payload:
        return 401, "Invalid token"

    # Check expiration
    if payload.exp < now():
        return 401, "Token expired"

    # Validate IP binding
    if payload.bound_ip != request.client_ip:
        return 403, "IP mismatch"

    # Validate audience
    if payload.aud != YOUR_CLIENT_ID:
        return 401, "Invalid audience"

    return 200, payload
```

### 3.2 Permission Checking (REQUIRED)

**EVERY endpoint MUST check permissions:**

```python
# Required permission format: resource.action.field
required_permission = f"{resource}.{action}"

if required_permission not in user.permissions:
    return 403, "Permission denied"

# For field-level access
for field in requested_fields:
    field_permission = f"{resource}.{action}.{field}"
    if field_permission not in user.permissions:
        remove_field_from_response(field)
```

### 3.3 Rate Limiting (REQUIRED)

**MUST implement:**
- 100 requests per minute per user (authenticated)
- 20 requests per minute per IP (unauthenticated)
- Return 429 with Retry-After header when exceeded

### 3.4 Audit Logging (REQUIRED)

**MUST log:**
```json
{
  "timestamp": "2025-09-15T12:00:00Z",
  "user": "user@volusia.gov",
  "action": "resource.action",
  "resource_id": "id",
  "ip_address": "192.168.1.1",
  "success": true|false,
  "error": "error message if failed"
}
```

---

## 4. REQUIRED FIELD CLASSIFICATIONS

### 4.1 Category Definitions (STRICT)

**MUST classify EVERY field as exactly ONE of:**

| Category | Definition | Examples | Access Level |
|----------|------------|----------|--------------|
| `base` | Public, non-sensitive data | IDs, names of things, statuses | ALWAYS accessible |
| `pii` | Personally Identifiable Information | Names, emails, phones, addresses | Requires `*.read.pii` permission |
| `phi` | Protected Health Information | Medical records, diagnoses, prescriptions | Requires `*.read.phi` permission |
| `financial` | Financial/monetary data | Salaries, account numbers, balances | Requires `*.read.financial` permission |
| `sensitive` | Highly sensitive data | SSN, passwords, credit cards | Requires `*.read.sensitive` permission |

### 4.2 Auto-Classification Rules (MUST FOLLOW)

These fields MUST ALWAYS be classified as shown:

| Field Name Pattern | Required Category |
|--------------------|-------------------|
| `*_id`, `id`, `uuid` | `base` |
| `*_name` (for objects) | `base` |
| `*_name` (for persons) | `pii` |
| `email*`, `*_email` | `pii` |
| `phone*`, `*_phone` | `pii` |
| `address*`, `*_address` | `pii` |
| `ssn*`, `*_ssn`, `social_security*` | `sensitive` |
| `salary*`, `*_amount`, `price*`, `cost*` | `financial` |
| `balance*`, `account_number*` | `financial` |
| `diagnosis*`, `medication*`, `medical*` | `phi` |
| `password*`, `*_secret`, `*_token` | `sensitive` |
| `credit_card*`, `cvv*` | `sensitive` |

---

## 5. COMPLIANCE CHECKLIST

### Required Features Checklist

**Your application MUST have ALL of these:**

- [ ] **Discovery Endpoint** returning version "2.0"
- [ ] **Health Check Endpoint** at `/health`
- [ ] **Token Validation** on EVERY authenticated endpoint
- [ ] **Permission Checking** using format `resource.action.field`
- [ ] **Field Classification** for EVERY field (base/pii/phi/financial/sensitive)
- [ ] **CRUD Endpoints** for EVERY resource (List, Get, Create, Update, Delete)
- [ ] **Pagination** on ALL list endpoints
- [ ] **Standard Error Format** for ALL errors
- [ ] **Rate Limiting** implemented
- [ ] **Audit Logging** for ALL data access
- [ ] **IP Binding Validation** for tokens
- [ ] **HTTPS Only** in production
- [ ] **CORS Configuration** allowing CIDS origin
- [ ] **Timeout Handling** (30 second max)
- [ ] **Request ID** in all responses

### Security Checklist

**MUST implement:**

- [ ] JWT signature validation using CIDS public key
- [ ] Token expiration checking
- [ ] IP binding validation
- [ ] Device binding validation (if enabled)
- [ ] Audience validation (must match client_id)
- [ ] Permission format: `resource.action.field`
- [ ] Deny-by-default permission model
- [ ] Field filtering based on permissions
- [ ] RLS filter application from token
- [ ] SQL injection prevention
- [ ] XSS prevention
- [ ] CSRF protection
- [ ] Input validation on ALL endpoints
- [ ] Output encoding

### Data Handling Checklist

**MUST follow:**

- [ ] Never log sensitive fields (passwords, tokens, SSN)
- [ ] Encrypt sensitive data at rest
- [ ] Use TLS 1.2+ for all communications
- [ ] Mask PII in logs
- [ ] Implement data retention policies
- [ ] Support data export (GDPR)
- [ ] Support data deletion (GDPR)
- [ ] Handle timezone as UTC
- [ ] Use ISO 8601 for all dates

---

## 6. VALIDATION RULES

### 6.1 Discovery Validation

**Your discovery response will FAIL if:**

1. `app_id` doesn't match your assigned `client_id`
2. `version` is not exactly `"2.0"` (string)
3. `last_updated` is not valid ISO 8601
4. Any endpoint is missing required fields
5. Any field is missing `category` classification
6. Response takes longer than 5 seconds
7. Response is larger than 1MB

### 6.2 Runtime Validation

**Your application will FAIL integration if:**

1. Health check doesn't return within 2 seconds
2. Any endpoint doesn't validate tokens
3. Permissions aren't checked correctly
4. Fields aren't filtered based on permissions
5. Error responses don't follow standard format
6. Rate limiting isn't implemented
7. Audit logs aren't created

### 6.3 Testing Requirements

**MUST pass these tests:**

```bash
# 1. Discovery Test
curl https://yourapp/discovery/endpoints
# Must return valid JSON with version "2.0"

# 2. Health Test
curl https://yourapp/health
# Must return {"status": "healthy", "cids_compatible": true}

# 3. Auth Test - No Token
curl https://yourapp/api/resources
# Must return 401

# 4. Auth Test - Invalid Token
curl -H "Authorization: Bearer invalid" https://yourapp/api/resources
# Must return 401

# 5. Auth Test - Wrong IP
# Token bound to different IP
curl -H "Authorization: Bearer {valid_token}" https://yourapp/api/resources
# Must return 403

# 6. Permission Test
# Token without required permission
curl -H "Authorization: Bearer {limited_token}" https://yourapp/api/resources
# Must return 403

# 7. Field Filtering Test
# Token with limited field permissions
curl -H "Authorization: Bearer {limited_token}" https://yourapp/api/resources/1
# Must return object with only permitted fields
```

---

## IMPLEMENTATION TEMPLATE

### Minimal Compliant Application Structure

```
your-app/
├── api/
│   ├── discovery.py        # REQUIRED: Discovery endpoint
│   ├── health.py           # REQUIRED: Health check
│   ├── auth.py             # REQUIRED: Token validation
│   └── resources/          # Your resources
│       ├── __init__.py
│       └── employees.py    # Example resource
├── middleware/
│   ├── auth.py             # REQUIRED: Auth middleware
│   ├── permissions.py      # REQUIRED: Permission checking
│   ├── rate_limit.py       # REQUIRED: Rate limiting
│   └── audit.py            # REQUIRED: Audit logging
├── models/
│   └── field_definitions.py # REQUIRED: Field categories
├── config/
│   └── cids.py             # CIDS configuration
└── main.py                  # Application entry point
```

### Minimal Discovery Implementation

```python
# discovery.py - COPY THIS EXACTLY
from datetime import datetime

FIELD_CATEGORIES = {
    # Define ALL your fields here
    "id": "base",
    "email": "pii",
    "salary": "financial",
    "ssn": "sensitive"
}

def get_discovery():
    return {
        "app_id": os.getenv("CIDS_CLIENT_ID"),  # MUST match
        "app_name": "Your App Name",
        "version": "2.0",  # MUST be exactly "2.0"
        "last_updated": datetime.utcnow().isoformat() + "Z",
        "endpoints": generate_endpoints(),
        "response_fields": generate_field_definitions()
    }
```

---

## AUTOMATED VALIDATION ENDPOINT

CIDS provides an automated validation endpoint to check your implementation:

```bash
POST https://cids.volusia.gov/validate/application
{
  "app_url": "https://yourapp.volusia.gov",
  "client_id": "app_xxxxxxxxxxxxx"
}
```

Returns:
```json
{
  "valid": true|false,
  "errors": [],
  "warnings": [],
  "score": 100,  // Compliance score
  "details": {}  // Detailed test results
}
```

---

## NON-NEGOTIABLE RULES

1. **Version MUST be "2.0"** - No exceptions
2. **ALL fields MUST have categories** - No "uncategorized" allowed
3. **ALL endpoints MUST validate tokens** - No public data endpoints
4. **ALL responses MUST be JSON** - No HTML, XML, or plain text
5. **ALL dates MUST be ISO 8601 UTC** - No local times
6. **ALL IDs MUST be strings** - Even if they're numbers
7. **ALL errors MUST follow format** - No custom error structures

---

## CERTIFICATION

Once your application passes all requirements, you'll receive:

```json
{
  "certification": "CIDS_COMPLIANT_V2",
  "client_id": "app_xxxxxxxxxxxxx",
  "validated_at": "2025-09-15T12:00:00Z",
  "expires_at": "2026-09-15T12:00:00Z",
  "compliance_score": 100
}
```

---

**This specification is MANDATORY. Non-compliance will prevent integration.**

**Version**: 2.0
**Last Updated**: September 15, 2025
**Status**: ENFORCED
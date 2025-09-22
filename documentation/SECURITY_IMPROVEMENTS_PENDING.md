# 🔒 SECURITY IMPROVEMENTS - PENDING TASKS

> **Generated**: September 16, 2025
> **Status**: PENDING IMPLEMENTATION
> **Systems**: CIDS, HR System, Bank System
> **Priority Levels**: 🔴 CRITICAL | 🟠 HIGH | 🟡 MEDIUM | 🟢 LOW

---

## 📊 Executive Summary

This document outlines security vulnerabilities discovered during the security audit of the County Services microservices architecture. While CIDS (Centralized Identity Discovery Service) serves as the main authentication gateway and is reasonably secure, several improvements are needed across all systems.

### Current Security Status
- **CIDS**: ✅ Good (main gateway, token management, session timeout)
- **HR System**: ⚠️ Needs improvement (hardcoded credentials, session management fixed)
- **Bank System**: ⚠️ Needs review
- **UUID Service**: ⚠️ CORS too permissive
- **Services Portal**: ⚠️ CORS too permissive

---

## 🔴 CRITICAL PRIORITY (Implement within 24-48 hours)

### 1. Hardcoded API Key in HR System
**Location**: `/home/dpi/projects/hr_system/src/main.py:643`
```python
# CURRENT (VULNERABLE)
HR_API_KEY = "cids_ak_WoQFlNG8ckBg6ve9NuvB12XeABLs30qV"
```

**Impact**:
- API key exposed in source code
- Anyone with repository access can impersonate the service
- Cannot rotate key without code changes

**Solution**:
```python
# FIXED
import os
from dotenv import load_dotenv

load_dotenv()
HR_API_KEY = os.getenv('CIDS_API_KEY')
if not HR_API_KEY:
    raise ValueError("CIDS_API_KEY environment variable not set")
```

**Implementation**:
1. Add to `.env` file (never commit to git)
2. Add `.env.example` with placeholder
3. Update Docker Compose to pass environment variable
4. Test in all environments

---

## 🔴 CRITICAL - CORS Configuration Too Permissive

### Affected Services:
- **Services Portal**: `allow_origins=["*"]`
- **UUID Service**: `allow_origins=["*"]`
- **Ecosystem Monitor**: `allow_origins=["*"]`

**Current (VULNERABLE)**:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # DANGEROUS
    allow_credentials=True,      # VERY DANGEROUS with *
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Solution**:
```python
# Define allowed origins explicitly
ALLOWED_ORIGINS = [
    "http://localhost:3000",      # CID frontend dev
    "https://localhost:3000",     # CID frontend dev (HTTPS)
    "http://localhost:4000",      # Services Portal
    "https://cids.volusia.gov",   # Production CID
    "https://services.volusia.gov" # Production Services
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],  # Only needed methods
    allow_headers=["Authorization", "Content-Type"],  # Only needed headers
)
```

---

## 🟠 HIGH PRIORITY (Implement this week)

### 1. No Rate Limiting Implementation

**Affected**: ALL services (CIDS, HR, Bank, UUID, Services Portal)

**Impact**:
- Vulnerable to brute force attacks
- Vulnerable to DoS/DDoS
- No protection against API abuse
- Potential cost implications if cloud-based

**Solution using slowapi**:
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Initialize limiter
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100 per minute"],
    storage_uri="redis://localhost:6379"  # Use Redis for distributed systems
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Critical endpoints - STRICT limits
@app.post("/auth/token/exchange")
@limiter.limit("3 per minute")  # Only 3 login attempts per minute
async def login():
    ...

@app.post("/auth/sso")
@limiter.limit("5 per minute")
async def sso_login():
    ...

# Standard API endpoints
@app.get("/api/data")
@limiter.limit("30 per minute")
async def get_data():
    ...

# Admin endpoints - more lenient
@app.get("/api/admin/users")
@limiter.limit("60 per minute")
async def admin_users():
    ...
```

**Implementation Priority by Service**:
1. **CIDS** (CRITICAL): Protect authentication endpoints
2. **HR System**: Protect sensitive data endpoints
3. **Bank System**: Protect financial endpoints
4. **Others**: Standard rate limiting

---

### 2. Input Validation Missing

**Affected**: All services

**Current Issues**:
- No systematic input validation
- No protection against injection attacks
- No field length limits
- No type validation

**Solution with Pydantic**:
```python
from pydantic import BaseModel, EmailStr, validator, constr, conint
from typing import Optional
import re

class UserCreateRequest(BaseModel):
    # String with constraints
    username: constr(min_length=3, max_length=50, regex="^[a-zA-Z0-9_-]+$")
    email: EmailStr

    # Integer with constraints
    age: conint(ge=18, le=120)  # >= 18 and <= 120

    # Optional field with pattern
    phone: Optional[constr(regex="^\+?1?\d{9,15}$")] = None

    # Custom validation
    @validator('username')
    def username_not_reserved(cls, v):
        reserved = ['admin', 'root', 'system']
        if v.lower() in reserved:
            raise ValueError('Username is reserved')
        return v

    @validator('email')
    def email_valid_domain(cls, v):
        if not v.endswith('@volusia.gov'):
            raise ValueError('Must use official email domain')
        return v

# Token validation
class TokenRequest(BaseModel):
    token: constr(regex="^[A-Za-z0-9\-_\.]+$", max_length=2048)

    @validator('token')
    def token_format(cls, v):
        if not v.startswith(('ey', 'cids_ak_')):
            raise ValueError('Invalid token format')
        return v

# SQL injection prevention for search
class SearchRequest(BaseModel):
    query: constr(max_length=100)

    @validator('query')
    def no_sql_injection(cls, v):
        dangerous = ['DROP', 'DELETE', 'UPDATE', 'INSERT', '--', '/*', '*/', 'EXEC', 'UNION']
        if any(word in v.upper() for word in dangerous):
            raise ValueError('Invalid characters in search query')
        return v
```

---

## 🟡 MEDIUM PRIORITY (Implement this month)

### 1. Sensitive Information in Logs

**Current Issues**:
```python
# VULNERABLE - Logs expose sensitive data
logger.info(f"Login successful: email={email}, password={password}")
logger.info(f"Token generated: {token}")
logger.info(f"User SSN: {ssn}")
logger.info(f"Credit card: {credit_card}")
```

**Solution**:
```python
import hashlib
from typing import Any

class SafeLogger:
    @staticmethod
    def hash_sensitive(value: str, length: int = 8) -> str:
        """Hash sensitive information for logging"""
        return hashlib.sha256(value.encode()).hexdigest()[:length]

    @staticmethod
    def mask_email(email: str) -> str:
        """Mask email for logging"""
        parts = email.split('@')
        if len(parts) != 2:
            return "invalid_email"
        username = parts[0]
        domain = parts[1]
        if len(username) > 2:
            masked = f"{username[:2]}***@{domain}"
        else:
            masked = f"***@{domain}"
        return masked

    @staticmethod
    def mask_token(token: str) -> str:
        """Show only beginning of token"""
        if len(token) > 20:
            return f"{token[:10]}...{token[-5:]}"
        return "***"

    @staticmethod
    def mask_ssn(ssn: str) -> str:
        """Mask SSN completely or show last 4"""
        if len(ssn) >= 4:
            return f"***-**-{ssn[-4:]}"
        return "***"

    @staticmethod
    def mask_credit_card(cc: str) -> str:
        """Show only last 4 digits"""
        cc_clean = cc.replace(' ', '').replace('-', '')
        if len(cc_clean) >= 4:
            return f"****-****-****-{cc_clean[-4:]}"
        return "****"

# Usage
safe_logger = SafeLogger()

# Safe logging
logger.info(f"Login successful: user={safe_logger.mask_email(email)}")
logger.info(f"Token generated: {safe_logger.mask_token(token)}")
logger.info(f"User ID: {safe_logger.hash_sensitive(ssn)}")
logger.info(f"Payment processed: card={safe_logger.mask_credit_card(credit_card)}")
```

---

### 2. No Request Size Limits

**Impact**:
- DoS through memory exhaustion
- Large file uploads can crash server
- No protection against zip bombs

**Solution**:
```python
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

# Global middleware for all requests
@app.middleware("http")
async def limit_request_size(request: Request, call_next):
    # Limit body size to 10MB
    MAX_SIZE = 10 * 1024 * 1024  # 10MB

    content_length = request.headers.get("content-length")
    if content_length:
        if int(content_length) > MAX_SIZE:
            return JSONResponse(
                status_code=413,
                content={"error": "Request too large"}
            )

    # For streaming bodies
    body = await request.body()
    if len(body) > MAX_SIZE:
        return JSONResponse(
            status_code=413,
            content={"error": "Request too large"}
        )

    # Re-create request with body
    import io
    from starlette.datastructures import Headers
    from starlette.requests import Request as StarletteRequest

    async def receive():
        return {"type": "http.request", "body": body}

    request = StarletteRequest(request.scope, receive)
    return await call_next(request)

# For file uploads specifically
from fastapi import File, UploadFile

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB for files

    # Check file size
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max size: {MAX_FILE_SIZE} bytes"
        )

    # Reset file pointer
    await file.seek(0)

    # Process file
    return {"filename": file.filename, "size": len(contents)}
```

---

### 3. XSS Prevention Not Implemented

**Current Issue**: HTML content not sanitized

**Solution**:
```python
import html
from markupsafe import escape
import bleach

class XSSProtection:
    # Allowed HTML tags and attributes for rich content
    ALLOWED_TAGS = ['p', 'br', 'span', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                    'strong', 'em', 'u', 'ol', 'ul', 'li', 'a', 'img']
    ALLOWED_ATTRS = {
        'a': ['href', 'title'],
        'img': ['src', 'alt'],
        'div': ['class'],
        'span': ['class']
    }

    @staticmethod
    def escape_html(text: str) -> str:
        """Escape all HTML - use for untrusted input"""
        return html.escape(text)

    @staticmethod
    def clean_html(html_content: str) -> str:
        """Clean HTML but allow safe tags"""
        return bleach.clean(
            html_content,
            tags=XSSProtection.ALLOWED_TAGS,
            attributes=XSSProtection.ALLOWED_ATTRS,
            strip=True
        )

    @staticmethod
    def sanitize_json_response(data: dict) -> dict:
        """Recursively sanitize all strings in JSON response"""
        if isinstance(data, dict):
            return {k: XSSProtection.sanitize_json_response(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [XSSProtection.sanitize_json_response(item) for item in data]
        elif isinstance(data, str):
            return XSSProtection.escape_html(data)
        else:
            return data

# Usage
xss = XSSProtection()

@app.post("/comment")
async def create_comment(content: str):
    # Sanitize user input
    safe_content = xss.clean_html(content)

    # Save to database
    save_comment(safe_content)

    return {"content": safe_content}

@app.get("/user/{username}")
async def get_user(username: str):
    # Escape username to prevent XSS
    safe_username = xss.escape_html(username)

    return {
        "username": safe_username,
        "profile": get_user_profile(username)
    }
```

---

## 🟢 LOW PRIORITY (Nice to have)

### 1. Security Headers

**Add security headers to all responses**:
```python
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        return response

app.add_middleware(SecurityHeadersMiddleware)
```

### 2. API Versioning

**Implement versioning for API endpoints**:
```python
from fastapi import APIRouter

# Version 1 API
v1_router = APIRouter(prefix="/api/v1")

@v1_router.get("/users")
async def get_users_v1():
    return {"version": "1.0", "users": []}

# Version 2 API with breaking changes
v2_router = APIRouter(prefix="/api/v2")

@v2_router.get("/users")
async def get_users_v2():
    return {"version": "2.0", "data": {"users": []}}

app.include_router(v1_router)
app.include_router(v2_router)
```

---

## 📋 Implementation Checklist

### Phase 1: Critical (24-48 hours)
- [ ] Remove hardcoded API key from HR System
- [ ] Fix CORS configuration in all services
- [ ] Document all changes

### Phase 2: High Priority (1 week)
- [ ] Implement rate limiting in CIDS
- [ ] Implement rate limiting in HR System
- [ ] Implement rate limiting in Bank System
- [ ] Add input validation to all endpoints
- [ ] Test rate limiting under load

### Phase 3: Medium Priority (1 month)
- [ ] Sanitize all logging statements
- [ ] Implement request size limits
- [ ] Add XSS protection
- [ ] Security testing

### Phase 4: Ongoing
- [ ] Security headers
- [ ] API versioning
- [ ] Regular security audits
- [ ] Dependency updates
- [ ] Penetration testing

---

## 🔧 Testing Scripts

### Test Rate Limiting
```bash
#!/bin/bash
# test_rate_limiting.sh

echo "Testing rate limiting..."

# Test login endpoint (should allow 3, block 4th)
for i in {1..5}; do
    echo "Attempt $i:"
    curl -X POST http://localhost:8001/auth/token/exchange \
         -H "Content-Type: application/json" \
         -d '{"code":"test"}' \
         -w "\nStatus: %{http_code}\n"
    sleep 1
done
```

### Test CORS
```bash
#!/bin/bash
# test_cors.sh

echo "Testing CORS configuration..."

# Test from unauthorized origin (should fail)
curl -H "Origin: http://evil.com" \
     -H "Access-Control-Request-Method: POST" \
     -H "Access-Control-Request-Headers: X-Requested-With" \
     -X OPTIONS \
     http://localhost:8001/auth/token \
     -v 2>&1 | grep -i "access-control"
```

### Security Audit Script
```bash
#!/bin/bash
# security_audit.sh

echo "🔍 Running Security Audit..."

echo -e "\n1. Checking for hardcoded credentials..."
grep -r "api_key.*=.*\"" --include="*.py" . | grep -v ".env"
grep -r "password.*=.*\"" --include="*.py" . | grep -v ".env"

echo -e "\n2. Checking CORS configuration..."
grep -r "allow_origins.*\*" --include="*.py" .

echo -e "\n3. Checking for rate limiting..."
grep -r "RateLimit\|Limiter\|throttle" --include="*.py" .

echo -e "\n4. Checking for sensitive data in logs..."
grep -r "logger.*password\|logger.*token\|logger.*secret" --include="*.py" .

echo -e "\n5. Checking for SQL injection vulnerabilities..."
grep -r "execute.*%\|execute.*format\|execute.*\+" --include="*.py" .

echo -e "\n✅ Audit complete!"
```

---

## 📚 References

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
- [CWE/SANS Top 25](https://cwe.mitre.org/top25/)
- [FastAPI Security Best Practices](https://fastapi.tiangolo.com/tutorial/security/)
- [Python Security Guidelines](https://python.org/dev/security/)

---

## 📞 Contact

For questions or security concerns:
- **Security Team**: security@volusia.gov
- **DevOps Team**: devops@volusia.gov
- **Incident Response**: incident@volusia.gov

---

**Document Version**: 1.0
**Last Updated**: September 16, 2025
**Next Review**: October 16, 2025
**Classification**: INTERNAL - CONFIDENTIAL
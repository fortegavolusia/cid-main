# Centralized Authentication Service - Architecture Phases

## Overview
Evolution plan from current single-app Azure AD integration to a hybrid centralized authentication service for multiple internal applications.

## Phase 1: Extract & Centralize (Current App → Auth Service)

### 1. Move auth logic to dedicated endpoints
- `/auth/login` - initiates Azure OAuth flow
- `/auth/callback` - handles Azure callback
- `/auth/token` - issues internal JWT
- `/auth/validate` - validates internal tokens

### 2. Create internal JWT issuer
- Generate RSA keypair for signing
- Define minimal token structure
- Add token generation after Azure auth

### 3. Add token validation endpoint
- Public key endpoint for apps
- Token introspection endpoint

## Phase 2: Add Multi-App Support

### 4. Implement app registration
- Store app credentials (client_id/secret)
- Define app-specific permissions
- Create app management API

### 5. Add permission mapping
- Map Azure groups → app permissions
- Store in database (not in-memory)
- Cache with TTL

## Phase 3: Production Features

### 6. Add refresh tokens
- Implement refresh flow
- Session management
- Token revocation

### 7. Add monitoring/security
- Rate limiting per app
- Audit logging
- Token usage analytics

## Phase 4: Client Integration

### 8. Create client libraries
- Python SDK for FastAPI apps
- Middleware for automatic validation
- Helper decorators

## Architecture Patterns Considered

### 1. Auth Gateway Pattern (Recommended)
```
[Apps] → [Auth Gateway] → [Azure AD]
                ↓
         [Internal JWT]
```

### 2. Direct Azure Token Pass-Through
```
[Apps] → [Azure AD] (each validates tokens)
```

### 3. Hybrid Approach (Selected)
```
[Apps] → [Auth Service] → [Azure AD]
              ↓
    [Lightweight JWT with claims]
    + [Permission Service for details]
```

## Key Design Decisions

### Token Strategy
- Issue short-lived JWTs (15-30 min)
- Include minimal claims (user ID, basic roles)
- Use refresh tokens for session management
- Cache Azure group memberships

### Permission Model
```json
{
  "sub": "user-id",
  "apps": {
    "app1": ["read", "write"],
    "app2": ["admin"]
  },
  "exp": 1234567890
}
```

### Security Considerations
- Implement token rotation
- Use asymmetric keys (RS256)
- Separate auth service from apps
- Implement rate limiting
- Add request signing between services
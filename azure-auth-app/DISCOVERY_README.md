# Endpoint Discovery Feature

This document describes the endpoint discovery feature in CIDS, which allows the authentication service to automatically discover and pull API endpoints from registered applications.

## Overview

The endpoint discovery feature enables:
- Apps to expose their API endpoints through a discovery endpoint
- CIDS to periodically fetch and store these endpoints
- Admins to view discovered endpoints in the UI
- Endpoints to be used in role mapping configurations

## How It Works

### 1. App Registration

When registering an app, you can now specify:
- **Discovery Endpoint**: URL where your app exposes its endpoints (e.g., `https://myapp.com/discovery/endpoints`)
- **Allow Discovery**: Boolean flag to enable/disable discovery

### 2. Discovery Protocol

Apps should expose a discovery endpoint that returns JSON in this format:

```json
{
  "version": "1.0",
  "app_id": "app_xxxxx",
  "endpoints": [
    {
      "method": "GET",
      "path": "/api/users",
      "description": "List all users",
      "required_permissions": ["users.read"],
      "required_roles": ["admin"],
      "tags": ["api", "users"]
    }
  ],
  "last_updated": "2024-01-15T12:00:00Z"
}
```

### 3. Authentication

CIDS authenticates to app discovery endpoints using service tokens:
- Token type: `service`
- Audience: `discovery-api`
- Valid for 5 minutes
- Apps should validate the token using CIDS JWKS endpoint

### 4. Discovery Process

Discovery can be triggered:
- Manually via admin UI (click "Run Discovery" button)
- Via API: `POST /discovery/endpoints/{client_id}`
- Batch all apps: `POST /discovery/endpoints`

Rate limiting:
- Discovery is skipped if run within 5 minutes of last attempt
- Use `force=true` parameter to override

## Implementation Guide

### For App Developers

1. **Add Discovery Endpoint**

```python
@app.route('/discovery/endpoints')
def discovery_endpoints():
    # Validate CIDS service token
    auth_header = request.headers.get('Authorization')
    if not validate_cids_token(auth_header):
        return jsonify({"error": "Unauthorized"}), 401
    
    # Return endpoint metadata
    return jsonify({
        "version": "1.0",
        "app_id": CLIENT_ID,
        "endpoints": get_endpoint_metadata()
    })
```

2. **Token Validation**

```python
def validate_cids_token(auth_header):
    if not auth_header or not auth_header.startswith('Bearer '):
        return False
    
    token = auth_header.replace('Bearer ', '')
    
    # Get CIDS JWKS
    jwks_response = requests.get('https://cids.example.com/.well-known/jwks.json')
    jwks = jwks_response.json()
    
    # Validate token
    try:
        claims = jwt.decode(token, jwks['keys'], audience='discovery-api')
        return claims.get('token_type') == 'service'
    except:
        return False
```

### For CIDS Admins

1. **Enable Discovery for an App**
   - Go to App Registration Management
   - When registering, provide discovery endpoint URL
   - Check "Allow Endpoint Discovery"

2. **Run Discovery**
   - Find app in the list
   - Click "Run Discovery" button
   - View results in notification

3. **View Discovered Endpoints**
   - Click "View Endpoints" on any app
   - Discovered endpoints are marked with "(discovered)"

4. **Use in Role Mappings**
   - Go to Role Mappings interface
   - Discovered endpoints appear automatically
   - Map endpoints to roles as needed

## Security Considerations

1. **Always validate CIDS service tokens** in your discovery endpoint
2. **Use HTTPS** for discovery endpoints
3. **Don't expose sensitive endpoint information** in discovery
4. **Rate limit** discovery requests to prevent abuse
5. **Audit log** all discovery activities

## Testing

Use the provided test script:

```bash
# Start the Flask test app
python test_app.py

# Run discovery test
python test_discovery.py
```

This will:
1. Register a test app with discovery enabled
2. Trigger discovery
3. Show discovered endpoints

## API Reference

### Discovery Endpoints

#### Trigger Discovery for One App
```
POST /discovery/endpoints/{client_id}
Authorization: Bearer {admin_token}
Query params: force=true (optional)
```

#### Trigger Discovery for All Apps
```
POST /discovery/endpoints
Authorization: Bearer {admin_token}
Query params: force=true (optional)
```

#### Get Discovery Status
```
GET /discovery/status
Authorization: Bearer {admin_token}
Query params: client_id={client_id} (optional)
```

#### Get Endpoints (for service accounts)
```
GET /discovery/endpoints
Authorization: Bearer {service_token}
Query params: app_id={app_id} (optional)
```

## Troubleshooting

### Discovery Fails

1. **Check discovery endpoint URL** is correct and accessible
2. **Verify app allows discovery** flag is enabled
3. **Check discovery endpoint returns** valid JSON format
4. **Ensure CIDS can reach** the discovery endpoint (firewall/network)
5. **Check logs** for specific error messages

### No Endpoints Discovered

1. **Verify endpoint format** matches the schema
2. **Check for JSON syntax errors** in response
3. **Ensure endpoints array** is not empty
4. **Check discovery status** in admin UI

### Authentication Errors

1. **Implement token validation** in your discovery endpoint
2. **Accept service tokens** with audience `discovery-api`
3. **Use CIDS JWKS endpoint** to validate tokens
4. **Check token hasn't expired** (5-minute lifetime)
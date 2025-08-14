from fastapi import FastAPI, Request, Depends, HTTPException, Response
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import httpx
import secrets
import os
from typing import Optional, Dict
from datetime import datetime
import jwt
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Advanced Test App")
security = HTTPBearer()

# Configuration
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "https://localhost:8000")
CLIENT_ID = os.getenv("TEST_APP_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("TEST_APP_CLIENT_SECRET", "")
REDIRECT_URI = "http://localhost:8001/auth/callback"

# In-memory session storage (use Redis in production)
sessions: Dict[str, dict] = {}

# HTML template with better UI
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Advanced Test App</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #f0f2f5;
        }
        .header {
            background: #1a1a1a;
            color: white;
            padding: 1rem 2rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .container {
            max-width: 1200px;
            margin: 2rem auto;
            padding: 0 2rem;
        }
        .card {
            background: white;
            border-radius: 8px;
            padding: 2rem;
            margin-bottom: 2rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 2rem;
        }
        .button {
            display: inline-block;
            padding: 0.75rem 1.5rem;
            background: #0066cc;
            color: white;
            text-decoration: none;
            border-radius: 4px;
            border: none;
            cursor: pointer;
            font-size: 1rem;
            transition: background 0.2s;
        }
        .button:hover {
            background: #0052a3;
        }
        .button.secondary {
            background: #6c757d;
        }
        .button.success {
            background: #28a745;
        }
        .button.danger {
            background: #dc3545;
        }
        .api-endpoint {
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 4px;
            padding: 1rem;
            margin: 1rem 0;
        }
        .api-endpoint h4 {
            margin: 0 0 0.5rem 0;
            color: #495057;
        }
        .api-response {
            background: #e9ecef;
            border-radius: 4px;
            padding: 1rem;
            margin-top: 1rem;
            font-family: monospace;
            font-size: 0.875rem;
            white-space: pre-wrap;
            word-break: break-all;
        }
        .role-badge {
            display: inline-block;
            padding: 0.25rem 0.75rem;
            background: #e9ecef;
            border-radius: 1rem;
            font-size: 0.875rem;
            margin: 0.25rem;
        }
        .role-badge.admin {
            background: #f8d7da;
            color: #721c24;
        }
        .role-badge.user {
            background: #d1ecf1;
            color: #0c5460;
        }
        .status {
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 4px;
            font-size: 0.875rem;
            font-weight: 500;
        }
        .status.authenticated {
            background: #d4edda;
            color: #155724;
        }
        .status.unauthenticated {
            background: #f8d7da;
            color: #721c24;
        }
        pre {
            background: #f5f5f5;
            padding: 1rem;
            border-radius: 4px;
            overflow-x: auto;
        }
        .loading {
            display: none;
            color: #666;
            font-style: italic;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>Advanced Test Application</h1>
    </div>
    
    <div class="container">
        {% if not user %}
            <div class="card">
                <h2>Welcome to the Test Application</h2>
                <p>This application demonstrates integration with the centralized authentication service.</p>
                <p class="status unauthenticated">Status: Not Authenticated</p>
                <p style="margin-top: 2rem;">
                    <a href="/login" class="button">Login with Auth Service</a>
                </p>
                
                {% if not client_id %}
                    <div style="background: #fff3cd; padding: 1rem; border-radius: 4px; margin-top: 2rem;">
                        <strong>Configuration Required:</strong>
                        <ol>
                            <li>Register this app in the auth service admin panel</li>
                            <li>Add redirect URI: <code>{{ redirect_uri }}</code></li>
                            <li>Set environment variables:
                                <pre>TEST_APP_CLIENT_ID=your_client_id
TEST_APP_CLIENT_SECRET=your_client_secret</pre>
                            </li>
                        </ol>
                    </div>
                {% endif %}
            </div>
        {% else %}
            <div class="card">
                <h2>User Information</h2>
                <p class="status authenticated">Status: Authenticated</p>
                
                <div class="grid" style="margin-top: 2rem;">
                    <div>
                        <h3>Profile</h3>
                        <p><strong>Name:</strong> {{ user.name }}</p>
                        <p><strong>Email:</strong> {{ user.email }}</p>
                        <p><strong>Subject ID:</strong> <code>{{ user.sub }}</code></p>
                    </div>
                    <div>
                        <h3>Permissions</h3>
                        <p><strong>App Roles:</strong></p>
                        {% if user.app_roles %}
                            {% for role in user.app_roles %}
                                <span class="role-badge {{ role }}">{{ role }}</span>
                            {% endfor %}
                        {% else %}
                            <span class="role-badge">No roles assigned</span>
                        {% endif %}
                        
                        <p style="margin-top: 1rem;"><strong>AD Groups:</strong></p>
                        {% if user.groups %}
                            {% for group in user.groups %}
                                <span class="role-badge">{{ group }}</span>
                            {% endfor %}
                        {% else %}
                            <span>No groups</span>
                        {% endif %}
                    </div>
                </div>
                
                <p style="margin-top: 2rem;">
                    <a href="/logout" class="button danger">Logout</a>
                </p>
            </div>
            
            <div class="card">
                <h2>API Test Panel</h2>
                <p>Test different API endpoints with your current authentication:</p>
                
                <div class="api-endpoint">
                    <h4>Public Endpoint</h4>
                    <p>No authentication required</p>
                    <button class="button secondary" onclick="testApi('/api/public')">Test GET /api/public</button>
                    <div id="response-public" class="api-response loading">Loading...</div>
                </div>
                
                <div class="api-endpoint">
                    <h4>Authenticated Endpoint</h4>
                    <p>Requires valid token</p>
                    <button class="button success" onclick="testApi('/api/profile')">Test GET /api/profile</button>
                    <div id="response-profile" class="api-response loading">Loading...</div>
                </div>
                
                <div class="api-endpoint">
                    <h4>Admin Endpoint</h4>
                    <p>Requires 'admin' role</p>
                    <button class="button danger" onclick="testApi('/api/admin/users')">Test GET /api/admin/users</button>
                    <div id="response-admin" class="api-response loading">Loading...</div>
                </div>
                
                <div class="api-endpoint">
                    <h4>Editor Endpoint</h4>
                    <p>Requires 'editor' role</p>
                    <button class="button" onclick="testApi('/api/editor/content')">Test GET /api/editor/content</button>
                    <div id="response-editor" class="api-response loading">Loading...</div>
                </div>
            </div>
            
            <div class="card">
                <h2>Token Details</h2>
                <pre>{{ token_info }}</pre>
            </div>
        {% endif %}
        
        <div class="card">
            <h2>Configuration</h2>
            <p><strong>Auth Service:</strong> {{ auth_url }}</p>
            <p><strong>Client ID:</strong> <code>{{ client_id or 'Not set' }}</code></p>
            <p><strong>Redirect URI:</strong> <code>{{ redirect_uri }}</code></p>
        </div>
    </div>
    
    <script>
        async function testApi(endpoint) {
            const responseId = 'response-' + endpoint.split('/').pop();
            const responseDiv = document.getElementById(responseId);
            responseDiv.style.display = 'block';
            responseDiv.textContent = 'Loading...';
            
            try {
                const response = await fetch(endpoint, {
                    headers: {
                        'Authorization': 'Bearer {{ token }}'
                    }
                });
                
                const data = await response.json();
                responseDiv.textContent = `Status: ${response.status} ${response.statusText}\n\n${JSON.stringify(data, null, 2)}`;
                
                // Color code based on status
                if (response.ok) {
                    responseDiv.style.background = '#d4edda';
                    responseDiv.style.color = '#155724';
                } else {
                    responseDiv.style.background = '#f8d7da';
                    responseDiv.style.color = '#721c24';
                }
            } catch (error) {
                responseDiv.textContent = `Error: ${error.message}`;
                responseDiv.style.background = '#f8d7da';
                responseDiv.style.color = '#721c24';
            }
        }
    </script>
</body>
</html>
"""

def get_session(session_id: str) -> Optional[dict]:
    return sessions.get(session_id)

def create_session(data: dict) -> str:
    session_id = secrets.token_urlsafe(32)
    sessions[session_id] = data
    return session_id

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Validate token and return user info"""
    token = credentials.credentials
    
    # Validate token with auth service
    async with httpx.AsyncClient(verify=False) as client:
        response = await client.post(
            f"{AUTH_SERVICE_URL}/auth/validate",
            json={"token": token}
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("valid"):
                return data.get("claims", {})
    
    raise HTTPException(status_code=401, detail="Invalid token")

def require_role(role: str):
    """Dependency to require a specific role"""
    async def role_checker(user: dict = Depends(get_current_user)):
        if role not in user.get("app_roles", []):
            raise HTTPException(
                status_code=403, 
                detail=f"Forbidden. Required role: {role}"
            )
        return user
    return role_checker

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    # Check for session cookie
    session_id = request.cookies.get("session_id")
    session_data = get_session(session_id) if session_id else None
    
    user = session_data.get("user") if session_data else None
    token = session_data.get("access_token") if session_data else None
    
    # Decode token for display (without verification)
    token_info = "No token"
    if token:
        try:
            # Decode without verification just for display
            decoded = jwt.decode(token, options={"verify_signature": False})
            token_info = f"Token Claims:\n{json.dumps(decoded, indent=2)}\n\nRaw Token:\n{token[:50]}..."
        except:
            token_info = "Failed to decode token"
    
    html = HTML_TEMPLATE.replace("{{ user.name }}", user.get("name", "") if user else "")
    html = html.replace("{{ user.email }}", user.get("email", "") if user else "")
    html = html.replace("{{ user.sub }}", user.get("sub", "") if user else "")
    html = html.replace("{{ auth_url }}", AUTH_SERVICE_URL)
    html = html.replace("{{ client_id }}", CLIENT_ID)
    html = html.replace("{{ redirect_uri }}", REDIRECT_URI)
    html = html.replace("{{ token }}", token or "")
    html = html.replace("{{ token_info }}", token_info)
    
    # Handle user data
    if user:
        html = html.replace("{% if not user %}", "<!-- ")
        html = html.replace("{% else %}", " -->")
        html = html.replace("{% endif %}", "")
        
        # Handle roles
        if user.get("app_roles"):
            roles_html = ""
            for role in user["app_roles"]:
                roles_html += f'<span class="role-badge {role}">{role}</span>'
            html = html.replace("{% for role in user.app_roles %}", "")
            html = html.replace("{% endfor %}", "")
            html = html.replace('<span class="role-badge {{ role }}">{{ role }}</span>', roles_html)
        else:
            html = html.replace("{% if user.app_roles %}", "<!-- ")
            html = html.replace("{% for role in user.app_roles %}", "<!-- ")
            html = html.replace("{% endfor %}", " -->")
        
        # Handle groups  
        if user.get("groups"):
            groups_html = ""
            for group in user["groups"]:
                groups_html += f'<span class="role-badge">{group}</span>'
            html = html.replace("{% for group in user.groups %}", "")
            html = html.replace("{% endfor %}", "")
            html = html.replace('<span class="role-badge">{{ group }}</span>', groups_html)
        else:
            html = html.replace("{% if user.groups %}", "<!-- ")
            html = html.replace("{% for group in user.groups %}", "<!-- ")
            html = html.replace("{% endfor %}", " -->")
    else:
        html = html.replace("{% if not user %}", "")
        html = html.replace("{% else %}", "<!-- ")
        html = html.replace("{% endif %}", " -->")
    
    # Handle client_id check
    if not CLIENT_ID:
        html = html.replace("{% if not client_id %}", "")
        html = html.replace("{% endif %}", "")
    else:
        html = html.replace("{% if not client_id %}", "<!-- ")
        html = html.replace("{% endif %}", " -->")
    
    return html

@app.get("/login")
async def login():
    if not CLIENT_ID:
        return RedirectResponse(url="/?error=Not configured")
    
    state = secrets.token_urlsafe(32)
    session_id = create_session({"oauth_state": state})
    
    auth_url = f"{AUTH_SERVICE_URL}/auth/login?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&state={state}"
    
    response = RedirectResponse(url=auth_url)
    response.set_cookie(key="session_id", value=session_id, httponly=True)
    return response

@app.get("/auth/callback")
async def auth_callback(
    request: Request,
    state: str,
    access_token: Optional[str] = None,
    error: Optional[str] = None
):
    if error:
        return RedirectResponse(url=f"/?error={error}")
    
    # Get session
    session_id = request.cookies.get("session_id")
    session_data = get_session(session_id) if session_id else None
    
    if not session_data or session_data.get("oauth_state") != state:
        return RedirectResponse(url="/?error=Invalid state")
    
    if not access_token:
        return RedirectResponse(url="/?error=No token received")
    
    # Validate token
    async with httpx.AsyncClient(verify=False) as client:
        response = await client.post(
            f"{AUTH_SERVICE_URL}/auth/validate",
            json={"token": access_token}
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("valid"):
                # Update session
                session_data["user"] = data["claims"]
                session_data["access_token"] = access_token
                return RedirectResponse(url="/")
    
    return RedirectResponse(url="/?error=Invalid token")

@app.get("/logout")
async def logout(response: Response):
    response = RedirectResponse(url="/")
    response.delete_cookie(key="session_id")
    return response

# API Endpoints

@app.get("/api/public")
async def api_public():
    """Public endpoint - no auth required"""
    return {
        "message": "This is public data",
        "timestamp": datetime.utcnow().isoformat(),
        "data": ["Item 1", "Item 2", "Item 3"]
    }

@app.get("/api/profile")
async def api_profile(user: dict = Depends(get_current_user)):
    """Protected endpoint - requires authentication"""
    return {
        "message": "Your profile data",
        "user": user,
        "profile": {
            "joined": "2023-01-01",
            "last_login": datetime.utcnow().isoformat(),
            "preferences": {
                "theme": "dark",
                "notifications": True
            }
        }
    }

@app.get("/api/admin/users")
async def api_admin_users(user: dict = Depends(require_role("admin"))):
    """Admin endpoint - requires 'admin' role"""
    return {
        "message": "Admin user list",
        "current_user": user,
        "users": [
            {"id": 1, "name": "John Doe", "email": "john@example.com", "role": "admin"},
            {"id": 2, "name": "Jane Smith", "email": "jane@example.com", "role": "user"},
            {"id": 3, "name": "Bob Wilson", "email": "bob@example.com", "role": "editor"}
        ]
    }

@app.get("/api/editor/content")
async def api_editor_content(user: dict = Depends(require_role("editor"))):
    """Editor endpoint - requires 'editor' role"""
    return {
        "message": "Content management",
        "current_user": user,
        "content": [
            {"id": 1, "title": "Article 1", "status": "published"},
            {"id": 2, "title": "Article 2", "status": "draft"},
            {"id": 3, "title": "Article 3", "status": "review"}
        ]
    }

if __name__ == "__main__":
    import uvicorn
    import json
    
    print(f"""
Advanced Test App Configuration:
================================
Auth Service URL: {AUTH_SERVICE_URL}
Client ID: {CLIENT_ID or 'NOT SET - Please register this app'}
Client Secret: {'SET' if CLIENT_SECRET else 'NOT SET'}
Redirect URI: {REDIRECT_URI}

To use this app:
1. Register it with the auth service admin panel
2. Add the redirect URI: {REDIRECT_URI}
3. Set environment variables in .env file:
   TEST_APP_CLIENT_ID=your_client_id_here
   TEST_APP_CLIENT_SECRET=your_client_secret_here

4. Set up role mappings in the auth service for testing:
   - Map an AD group to 'admin' role
   - Map an AD group to 'editor' role

Starting server on http://localhost:8001
""")
    
    uvicorn.run(app, host="0.0.0.0", port=8001)
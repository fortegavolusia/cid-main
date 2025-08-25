#!/usr/bin/env python3
"""
CIDS-Compliant Test Application with Web UI
This version includes a web interface for testing API keys and viewing data
"""

from fastapi import FastAPI, Header, HTTPException, Depends, Request, Query, Form
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import httpx
import os
import json
import logging
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Application configuration
CIDS_CONFIG = {
    "cids_base_url": os.getenv("CIDS_BASE_URL", "http://localhost:8000"),
    "app_name": "CIDS Compliant Test App with UI",
    "app_version": "2.1.0",
    "discovery_enabled": True
}

# Create FastAPI app
app = FastAPI(
    title="CIDS Compliant Test Application with UI",
    description="A fully CIDS-compliant application with web interface for testing",
    version="2.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# Data Models (Same as before)
# ============================================================================

class Department(BaseModel):
    id: str
    name: str
    budget: float = Field(..., description="Department annual budget")
    manager_id: Optional[str] = None
    created_at: datetime
    
class User(BaseModel):
    id: str
    email: str = Field(..., description="User email address")
    name: str = Field(..., description="Full name")
    salary: Optional[float] = Field(None, description="Annual salary")
    ssn: Optional[str] = Field(None, description="Social Security Number")
    phone: Optional[str] = Field(None, description="Phone number")
    address: Optional[str] = Field(None, description="Home address")
    department: Optional[Department] = None
    medical_records: Optional[Dict[str, Any]] = Field(None, description="Medical history")
    performance_rating: Optional[float] = Field(None, description="Performance score")
    hire_date: Optional[datetime] = None
    is_active: bool = True
    roles: List[str] = []
    created_at: datetime
    updated_at: datetime

class Order(BaseModel):
    id: str
    user_id: str
    total_amount: float = Field(..., description="Order total in USD")
    items: List[Dict[str, Any]] = []
    status: str = Field(..., description="Order status")
    payment_method: Optional[str] = Field(None, description="Payment method used")
    credit_card_last4: Optional[str] = Field(None, description="Last 4 digits of card")
    shipping_address: Optional[str] = None
    created_at: datetime
    shipped_at: Optional[datetime] = None

class Report(BaseModel):
    id: str
    name: str
    type: str = Field(..., description="Report type")
    content: Dict[str, Any] = Field(..., description="Report data")
    confidential: bool = False
    financial_data: Optional[Dict[str, Any]] = None
    created_by: str
    created_at: datetime

# Sample data (same as before)
users_db: Dict[str, User] = {
    "user1": User(
        id="user1",
        email="john.doe@company.com",
        name="John Doe",
        salary=95000,
        ssn="123-45-6789",
        phone="555-0100",
        address="123 Main St, Anytown, USA",
        department=Department(
            id="dept1",
            name="Engineering",
            budget=1000000,
            manager_id="user3",
            created_at=datetime.now()
        ),
        medical_records={"blood_type": "A+", "allergies": ["peanuts"]},
        performance_rating=4.5,
        hire_date=datetime.now() - timedelta(days=730),
        is_active=True,
        roles=["developer", "team_lead"],
        created_at=datetime.now() - timedelta(days=730),
        updated_at=datetime.now()
    ),
    "user2": User(
        id="user2",
        email="jane.smith@company.com",
        name="Jane Smith",
        salary=105000,
        ssn="987-65-4321",
        phone="555-0101",
        address="456 Oak Ave, Somewhere, USA",
        department=Department(
            id="dept2",
            name="Finance",
            budget=500000,
            manager_id="user4",
            created_at=datetime.now()
        ),
        medical_records={"blood_type": "O-", "conditions": ["diabetes"]},
        performance_rating=4.8,
        hire_date=datetime.now() - timedelta(days=365),
        is_active=True,
        roles=["analyst"],
        created_at=datetime.now() - timedelta(days=365),
        updated_at=datetime.now()
    )
}

orders_db: Dict[str, Order] = {
    "order1": Order(
        id="order1",
        user_id="user1",
        total_amount=299.99,
        items=[{"product": "Laptop", "quantity": 1, "price": 299.99}],
        status="delivered",
        payment_method="credit_card",
        credit_card_last4="1234",
        shipping_address="123 Main St, Anytown, USA",
        created_at=datetime.now() - timedelta(days=30),
        shipped_at=datetime.now() - timedelta(days=28)
    )
}

reports_db: Dict[str, Report] = {
    "report1": Report(
        id="report1",
        name="Q4 Financial Report",
        type="financial",
        content={"revenue": 1000000, "expenses": 750000, "profit": 250000},
        confidential=True,
        financial_data={"accounts": ["ACC001", "ACC002"], "transactions": 1500},
        created_by="user2",
        created_at=datetime.now() - timedelta(days=5)
    )
}

# ============================================================================
# Web UI HTML Templates
# ============================================================================

def get_base_html(content: str, api_key: str = "") -> str:
    """Base HTML template"""
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CIDS Compliant Test App</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        .header {{
            background: white;
            border-radius: 12px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }}
        .header h1 {{
            color: #333;
            margin-bottom: 10px;
        }}
        .header p {{
            color: #666;
            font-size: 16px;
        }}
        .status {{
            display: inline-block;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            margin-left: 10px;
        }}
        .status.connected {{
            background: #d4edda;
            color: #155724;
        }}
        .status.disconnected {{
            background: #f8d7da;
            color: #721c24;
        }}
        .main-content {{
            display: grid;
            grid-template-columns: 300px 1fr;
            gap: 30px;
        }}
        .sidebar {{
            background: white;
            border-radius: 12px;
            padding: 20px;
            height: fit-content;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }}
        .sidebar h3 {{
            color: #333;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #667eea;
        }}
        .nav-link {{
            display: block;
            padding: 12px 15px;
            margin-bottom: 8px;
            color: #333;
            text-decoration: none;
            border-radius: 8px;
            transition: all 0.3s;
        }}
        .nav-link:hover {{
            background: #f8f9fa;
            color: #667eea;
            transform: translateX(5px);
        }}
        .nav-link.active {{
            background: #667eea;
            color: white;
        }}
        .content {{
            background: white;
            border-radius: 12px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }}
        .api-key-form {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 30px;
        }}
        .form-group {{
            margin-bottom: 20px;
        }}
        .form-group label {{
            display: block;
            margin-bottom: 8px;
            color: #333;
            font-weight: 600;
        }}
        .form-group input {{
            width: 100%;
            padding: 12px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 14px;
            transition: border-color 0.3s;
        }}
        .form-group input:focus {{
            outline: none;
            border-color: #667eea;
        }}
        .btn {{
            padding: 12px 24px;
            border: none;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
        }}
        .btn-primary {{
            background: #667eea;
            color: white;
        }}
        .btn-primary:hover {{
            background: #5a67d8;
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }}
        .btn-success {{
            background: #48bb78;
            color: white;
        }}
        .btn-danger {{
            background: #f56565;
            color: white;
            margin-left: 10px;
        }}
        .data-section {{
            margin-top: 30px;
        }}
        .data-section h3 {{
            color: #333;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #e0e0e0;
        }}
        .data-card {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 15px;
            border-left: 4px solid #667eea;
        }}
        .data-card h4 {{
            color: #333;
            margin-bottom: 10px;
        }}
        .data-field {{
            margin: 8px 0;
            display: flex;
            align-items: flex-start;
        }}
        .data-field strong {{
            display: inline-block;
            min-width: 150px;
            color: #666;
        }}
        .data-field span {{
            color: #333;
        }}
        .sensitive {{
            color: #f56565 !important;
            font-style: italic;
        }}
        .hidden {{
            color: #999;
            font-style: italic;
        }}
        .json-view {{
            background: #1e1e1e;
            color: #d4d4d4;
            padding: 20px;
            border-radius: 8px;
            overflow-x: auto;
            font-family: 'Courier New', monospace;
            font-size: 14px;
            line-height: 1.5;
        }}
        .alert {{
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
        }}
        .alert-success {{
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }}
        .alert-error {{
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }}
        .alert-info {{
            background: #d1ecf1;
            color: #0c5460;
            border: 1px solid #bee5eb;
        }}
        .endpoint-list {{
            display: grid;
            gap: 15px;
        }}
        .endpoint-card {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            border-left: 4px solid #28a745;
        }}
        .endpoint-card.protected {{
            border-left-color: #ffc107;
        }}
        .method-badge {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 600;
            margin-right: 10px;
        }}
        .method-get {{ background: #28a745; color: white; }}
        .method-post {{ background: #007bff; color: white; }}
        .method-put {{ background: #ffc107; color: #333; }}
        .method-delete {{ background: #dc3545; color: white; }}
        .tabs {{
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            border-bottom: 2px solid #e0e0e0;
        }}
        .tab {{
            padding: 12px 20px;
            background: none;
            border: none;
            color: #666;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
            border-bottom: 3px solid transparent;
            margin-bottom: -2px;
        }}
        .tab:hover {{
            color: #667eea;
        }}
        .tab.active {{
            color: #667eea;
            border-bottom-color: #667eea;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔐 CIDS Compliant Test Application
                <span class="status {'connected' if api_key else 'disconnected'}">
                    {'API Key Set' if api_key else 'No API Key'}
                </span>
            </h1>
            <p>Test your CIDS integration with full discovery support and field-level permissions</p>
        </div>
        
        <div class="main-content">
            <div class="sidebar">
                <h3>Navigation</h3>
                <a href="/" class="nav-link">🏠 Home</a>
                <a href="/ui/users" class="nav-link">👥 Users</a>
                <a href="/ui/orders" class="nav-link">📦 Orders</a>
                <a href="/ui/reports" class="nav-link">📊 Reports</a>
                <a href="/ui/discovery" class="nav-link">🔍 Discovery</a>
                <a href="/ui/test" class="nav-link">🧪 Test Endpoints</a>
            </div>
            
            <div class="content">
                {content}
            </div>
        </div>
    </div>
    
    <script>
        // Store API key in sessionStorage
        function saveApiKey() {{
            const apiKey = document.getElementById('api_key').value;
            if (apiKey) {{
                sessionStorage.setItem('cids_api_key', apiKey);
                window.location.reload();
            }}
        }}
        
        function clearApiKey() {{
            sessionStorage.removeItem('cids_api_key');
            window.location.reload();
        }}
        
        // Load API key on page load
        window.onload = function() {{
            const savedKey = sessionStorage.getItem('cids_api_key');
            if (savedKey) {{
                const input = document.getElementById('api_key');
                if (input) {{
                    input.value = savedKey;
                }}
            }}
        }}
        
        // Test API endpoint
        async function testEndpoint(endpoint, method = 'GET') {{
            const apiKey = sessionStorage.getItem('cids_api_key');
            const resultDiv = document.getElementById('test-result');
            
            if (!apiKey) {{
                resultDiv.innerHTML = '<div class="alert alert-error">Please set an API key first!</div>';
                return;
            }}
            
            try {{
                const response = await fetch(endpoint, {{
                    method: method,
                    headers: {{
                        'Authorization': 'Bearer ' + apiKey,
                        'Content-Type': 'application/json'
                    }}
                }});
                
                const data = await response.json();
                
                if (response.ok) {{
                    resultDiv.innerHTML = '<div class="alert alert-success">Success!</div>' +
                        '<div class="json-view">' + JSON.stringify(data, null, 2) + '</div>';
                }} else {{
                    resultDiv.innerHTML = '<div class="alert alert-error">Error: ' + response.status + '</div>' +
                        '<div class="json-view">' + JSON.stringify(data, null, 2) + '</div>';
                }}
            }} catch (error) {{
                resultDiv.innerHTML = '<div class="alert alert-error">Request failed: ' + error.message + '</div>';
            }}
        }}
    </script>
</body>
</html>
"""

# ============================================================================
# Web UI Routes
# ============================================================================

@app.get("/", response_class=HTMLResponse)
async def home_page(request: Request):
    """Home page with API key setup"""
    api_key = request.headers.get("authorization", "").replace("Bearer ", "")
    
    content = """
        <h2>Welcome to CIDS Compliant Test App</h2>
        
        <div class="api-key-form">
            <h3>🔑 API Key Configuration</h3>
            <div class="form-group">
                <label for="api_key">Enter your CIDS API Key:</label>
                <input type="password" id="api_key" placeholder="cids_ak_..." />
            </div>
            <button class="btn btn-primary" onclick="saveApiKey()">Save API Key</button>
            <button class="btn btn-danger" onclick="clearApiKey()">Clear API Key</button>
        </div>
        
        <div class="data-section">
            <h3>📋 Quick Start Guide</h3>
            <div class="data-card">
                <h4>1. Register Your App in CIDS</h4>
                <p>Go to the CIDS Admin Portal and register this application:</p>
                <ul style="margin: 10px 0 0 20px;">
                    <li>Name: CIDS Compliant Test App</li>
                    <li>Discovery URL: http://localhost:8001/discovery/endpoints</li>
                    <li>Enable "Create API Key" option during registration</li>
                </ul>
            </div>
            
            <div class="data-card">
                <h4>2. Enter Your API Key</h4>
                <p>Paste the API key you received during registration in the field above.</p>
            </div>
            
            <div class="data-card">
                <h4>3. Test Your Access</h4>
                <p>Navigate to Users, Orders, or Reports to test field-level permissions.</p>
            </div>
        </div>
        
        <div class="data-section">
            <h3>🔧 System Information</h3>
            <div class="data-card">
                <div class="data-field">
                    <strong>CIDS Base URL:</strong>
                    <span>""" + CIDS_CONFIG['cids_base_url'] + """</span>
                </div>
                <div class="data-field">
                    <strong>App Version:</strong>
                    <span>""" + CIDS_CONFIG['app_version'] + """</span>
                </div>
                <div class="data-field">
                    <strong>Discovery Enabled:</strong>
                    <span>""" + str(CIDS_CONFIG['discovery_enabled']) + """</span>
                </div>
            </div>
        </div>
    """
    
    return get_base_html(content, api_key)

@app.get("/ui/users", response_class=HTMLResponse)
async def users_page(request: Request):
    """Users data page"""
    content = """
        <h2>👥 Users Data</h2>
        
        <div class="alert alert-info">
            This page will show different fields based on your API key permissions.
            Fields you don't have access to will be hidden or show as [No Access].
        </div>
        
        <div class="tabs">
            <button class="tab active" onclick="testEndpoint('/api/users')">List Users</button>
            <button class="tab" onclick="testEndpoint('/api/users/user1')">Get User 1</button>
            <button class="tab" onclick="testEndpoint('/api/users/user2')">Get User 2</button>
        </div>
        
        <div id="test-result">
            <p>Click a button above to load user data with your current permissions.</p>
        </div>
    """
    
    return get_base_html(content)

@app.get("/ui/orders", response_class=HTMLResponse)
async def orders_page(request: Request):
    """Orders data page"""
    content = """
        <h2>📦 Orders Data</h2>
        
        <div class="alert alert-info">
            Order data contains financial information. Check if you can see payment details.
        </div>
        
        <div class="tabs">
            <button class="tab active" onclick="testEndpoint('/api/orders')">List Orders</button>
            <button class="tab" onclick="testEndpoint('/api/orders/order1')">Get Order 1</button>
        </div>
        
        <div id="test-result">
            <p>Click a button above to load order data.</p>
        </div>
    """
    
    return get_base_html(content)

@app.get("/ui/reports", response_class=HTMLResponse)
async def reports_page(request: Request):
    """Reports data page"""
    content = """
        <h2>📊 Reports Data</h2>
        
        <div class="alert alert-info">
            Reports may contain confidential and financial data. Access depends on your permissions.
        </div>
        
        <div class="tabs">
            <button class="tab active" onclick="testEndpoint('/api/reports')">List Reports</button>
            <button class="tab" onclick="testEndpoint('/api/reports/report1')">Get Financial Report</button>
        </div>
        
        <div id="test-result">
            <p>Click a button above to load report data.</p>
        </div>
    """
    
    return get_base_html(content)

@app.get("/ui/discovery", response_class=HTMLResponse)
async def discovery_page(request: Request):
    """Discovery endpoint visualization"""
    content = """
        <h2>🔍 Discovery Information</h2>
        
        <div class="alert alert-info">
            This shows all endpoints exposed to CIDS for discovery. No authentication required for this endpoint.
        </div>
        
        <div class="tabs">
            <button class="tab active" onclick="testEndpoint('/discovery/endpoints')">View Discovery</button>
        </div>
        
        <div id="test-result">
            <p>Click the button above to see the discovery endpoint data.</p>
        </div>
    """
    
    return get_base_html(content)

@app.get("/ui/test", response_class=HTMLResponse)
async def test_page(request: Request):
    """Test various endpoints"""
    content = """
        <h2>🧪 Test Endpoints</h2>
        
        <div class="alert alert-info">
            Test different endpoints and HTTP methods with your API key.
        </div>
        
        <div class="endpoint-list">
            <div class="endpoint-card">
                <span class="method-badge method-get">GET</span>
                <strong>/health</strong> - Health check (no auth required)
                <button class="btn btn-primary" style="float: right;" onclick="testEndpoint('/health')">Test</button>
            </div>
            
            <div class="endpoint-card protected">
                <span class="method-badge method-get">GET</span>
                <strong>/api/users</strong> - List all users (requires auth)
                <button class="btn btn-primary" style="float: right;" onclick="testEndpoint('/api/users')">Test</button>
            </div>
            
            <div class="endpoint-card protected">
                <span class="method-badge method-get">GET</span>
                <strong>/api/users/user1</strong> - Get specific user (requires auth)
                <button class="btn btn-primary" style="float: right;" onclick="testEndpoint('/api/users/user1')">Test</button>
            </div>
            
            <div class="endpoint-card protected">
                <span class="method-badge method-post">POST</span>
                <strong>/api/users</strong> - Create user (requires write permission)
                <button class="btn btn-primary" style="float: right;" onclick="testEndpoint('/api/users', 'POST')">Test</button>
            </div>
            
            <div class="endpoint-card protected">
                <span class="method-badge method-delete">DELETE</span>
                <strong>/api/users/user1</strong> - Delete user (requires delete permission)
                <button class="btn btn-primary" style="float: right;" onclick="testEndpoint('/api/users/user1', 'DELETE')">Test</button>
            </div>
        </div>
        
        <div id="test-result" style="margin-top: 30px;">
            <p>Test results will appear here.</p>
        </div>
    """
    
    return get_base_html(content)

# ============================================================================
# Authentication & Authorization (from original app)
# ============================================================================

class AuthData(BaseModel):
    """Validated authentication data from CIDS"""
    valid: bool
    app_client_id: Optional[str] = None
    permissions: List[str] = []
    auth_type: str = "unknown"
    user: Optional[Dict[str, Any]] = None
    rls_filters: Optional[List[Dict[str, Any]]] = None

async def validate_cids_token(
    authorization: Optional[str] = Header(None)
) -> AuthData:
    """Validate token/API key with CIDS"""
    if not authorization:
        return AuthData(valid=False, permissions=[])
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{CIDS_CONFIG['cids_base_url']}/auth/validate",
                headers={"Authorization": authorization},
                timeout=10.0
            )
        
        if response.status_code == 200:
            data = response.json()
            return AuthData(
                valid=True,
                app_client_id=data.get("app_client_id"),
                permissions=data.get("permissions", []),
                auth_type=data.get("auth_type", "jwt"),
                user=data.get("user"),
                rls_filters=data.get("rls_filters")
            )
    except Exception as e:
        logger.error(f"Error validating token: {e}")
    
    return AuthData(valid=False, permissions=[])

class PermissionManager:
    @staticmethod
    def has_permission(
        permissions: List[str],
        resource: str,
        action: str,
        field: Optional[str] = None
    ) -> bool:
        """Check if user has required permission"""
        if "admin" in permissions:
            return True
        
        if field:
            specific = f"compliant_app.{resource}.{action}.{field}"
            if specific in permissions:
                return True
            wildcard = f"compliant_app.{resource}.{action}.*"
            if wildcard in permissions:
                return True
        
        resource_perm = f"compliant_app.{resource}.{action}"
        return resource_perm in permissions
    
    @staticmethod
    def filter_fields(
        data: Dict[str, Any],
        permissions: List[str],
        resource: str,
        action: str = "read"
    ) -> Dict[str, Any]:
        """Filter response fields based on permissions"""
        if "admin" in permissions:
            return data
        
        filtered = {}
        for field, value in data.items():
            if PermissionManager.has_permission(permissions, resource, action, field):
                if isinstance(value, dict):
                    filtered[field] = PermissionManager.filter_fields(
                        value, permissions, f"{resource}.{field}", action
                    )
                elif isinstance(value, list) and value and isinstance(value[0], dict):
                    filtered[field] = [
                        PermissionManager.filter_fields(
                            item, permissions, f"{resource}.{field}", action
                        )
                        for item in value
                    ]
                else:
                    filtered[field] = value
        return filtered

def apply_rls_filters(
    data: List[Dict[str, Any]],
    rls_filters: Optional[List[Dict[str, Any]]],
    context: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Apply RLS filters to data"""
    if not rls_filters:
        return data
    
    filtered_data = []
    for item in data:
        include = True
        for filter_rule in rls_filters:
            expression = filter_rule.get("expression", "")
            for key, value in context.items():
                placeholder = f"@{key}"
                if placeholder in expression:
                    expression = expression.replace(placeholder, str(value))
            
            if "department" in expression and "department" in item:
                if item["department"]["name"] not in expression:
                    include = False
                    break
            
            if "user_id" in expression and "user_id" in item:
                if item["user_id"] not in expression:
                    include = False
                    break
        
        if include:
            filtered_data.append(item)
    
    return filtered_data

class AuditLogger:
    @staticmethod
    def log_access(
        user_id: Optional[str],
        resource: str,
        action: str,
        resource_id: Optional[str] = None,
        granted: bool = True,
        reason: Optional[str] = None
    ):
        """Log access attempt"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "resource": resource,
            "action": action,
            "resource_id": resource_id,
            "granted": granted,
            "reason": reason
        }
        
        if granted:
            logger.info(f"ACCESS_GRANTED: {json.dumps(log_entry)}")
        else:
            logger.warning(f"ACCESS_DENIED: {json.dumps(log_entry)}")

audit = AuditLogger()

# ============================================================================
# API Endpoints (from original app)
# ============================================================================

@app.get("/discovery/endpoints")
async def discover_endpoints(
    authorization: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """CIDS Discovery Endpoint - Accepts both JWT tokens and API keys"""
    logger.info(f"Discovery endpoint called with auth: {authorization[:20] if authorization else 'None'}")
    
    # Discovery endpoints should generally be publicly accessible
    # But if authentication is provided, validate it
    if authorization:
        if authorization.startswith("Bearer cids_ak_"):
            # API key format - used by external services
            api_key = authorization.replace("Bearer ", "")
            logger.info(f"Discovery called with API key: {api_key[:20]}...")
        elif authorization.startswith("Bearer ey"):
            # JWT format - used by CIDS for service-to-service communication
            logger.info("Discovery called with JWT token from CIDS")
        else:
            logger.warning(f"Unknown authorization format: {authorization[:30]}")
            # Still allow discovery - it's meant to be discoverable
    else:
        logger.info("Discovery called without authentication - public endpoint")
    
    return {
        "version": "2.0",
        "app_id": "compliant_app",
        "app_name": CIDS_CONFIG["app_name"],  # Changed from service_name to app_name
        "description": "CIDS-compliant test application with web UI",
        "base_url": "http://localhost:8005",
        "last_updated": datetime.utcnow().isoformat(),
        "endpoints": [
            {
                "method": "GET",
                "path": "/api/users",
                "operation_id": "list_users",
                "description": "List all users",
                "resource": "users",
                "action": "read",
                "response_fields": {
                    "users": {
                        "type": "array",
                        "description": "List of users"
                    }
                }
            },
            {
                "method": "GET",
                "path": "/api/users/{user_id}",
                "operation_id": "get_user",
                "description": "Get specific user details",
                "resource": "users",
                "action": "read",
                "parameters": [
                    {
                        "name": "user_id",
                        "in": "path",
                        "type": "string",
                        "required": True
                    }
                ]
            }
        ]
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": CIDS_CONFIG["app_version"]
    }

@app.get("/api/users")
async def list_users(
    auth: AuthData = Depends(validate_cids_token),
    limit: int = Query(10),
    offset: int = Query(0)
):
    """List all users with permission-based field filtering"""
    if not PermissionManager.has_permission(auth.permissions, "users", "read"):
        audit.log_access(
            auth.user.get("id") if auth.user else None,
            "users", "read", granted=False
        )
        raise HTTPException(status_code=403, detail="Permission denied")
    
    users_list = list(users_db.values())[offset:offset + limit]
    
    if auth.rls_filters:
        context = {
            "current_user_id": auth.user.get("id") if auth.user else None,
            "current_user_email": auth.user.get("email") if auth.user else None,
            "current_timestamp": datetime.utcnow().isoformat()
        }
        users_list = apply_rls_filters(
            [u.dict() for u in users_list],
            auth.rls_filters,
            context
        )
    else:
        users_list = [u.dict() for u in users_list]
    
    filtered_users = []
    for user in users_list:
        filtered_user = PermissionManager.filter_fields(
            user, auth.permissions, "users", "read"
        )
        if filtered_user:
            filtered_users.append(filtered_user)
    
    audit.log_access(
        auth.user.get("id") if auth.user else None,
        "users", "read", granted=True
    )
    
    return {"users": filtered_users, "total": len(users_db)}

@app.get("/api/users/{user_id}")
async def get_user(
    user_id: str,
    auth: AuthData = Depends(validate_cids_token)
):
    """Get specific user with field filtering"""
    if not PermissionManager.has_permission(auth.permissions, "users", "read"):
        audit.log_access(
            auth.user.get("id") if auth.user else None,
            "users", "read", user_id, granted=False
        )
        raise HTTPException(status_code=403, detail="Permission denied")
    
    if user_id not in users_db:
        raise HTTPException(status_code=404, detail="User not found")
    
    user_data = users_db[user_id].dict()
    filtered_user = PermissionManager.filter_fields(
        user_data, auth.permissions, "users", "read"
    )
    
    audit.log_access(
        auth.user.get("id") if auth.user else None,
        "users", "read", user_id, granted=True
    )
    
    return filtered_user

@app.post("/api/users")
async def create_user(
    user_data: Dict[str, Any],
    auth: AuthData = Depends(validate_cids_token)
):
    """Create new user"""
    if not PermissionManager.has_permission(auth.permissions, "users", "write"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    new_id = f"user{len(users_db) + 1}"
    return {
        "id": new_id,
        "created_at": datetime.utcnow().isoformat(),
        "message": "User created successfully"
    }

@app.put("/api/users/{user_id}")
async def update_user(
    user_id: str,
    user_data: Dict[str, Any],
    auth: AuthData = Depends(validate_cids_token)
):
    """Update user information"""
    if not PermissionManager.has_permission(auth.permissions, "users", "write"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    if user_id not in users_db:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "id": user_id,
        "updated_at": datetime.utcnow().isoformat(),
        "message": "User updated successfully"
    }

@app.delete("/api/users/{user_id}")
async def delete_user(
    user_id: str,
    auth: AuthData = Depends(validate_cids_token)
):
    """Delete user"""
    if not PermissionManager.has_permission(auth.permissions, "users", "delete"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    if user_id not in users_db:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "message": "User deleted successfully",
        "deleted_at": datetime.utcnow().isoformat()
    }

@app.get("/api/orders")
async def list_orders(
    auth: AuthData = Depends(validate_cids_token)
):
    """List all orders"""
    if not PermissionManager.has_permission(auth.permissions, "orders", "read"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    orders_list = [o.dict() for o in orders_db.values()]
    
    if auth.rls_filters:
        context = {
            "current_user_id": auth.user.get("id") if auth.user else None,
            "current_user_email": auth.user.get("email") if auth.user else None,
        }
        orders_list = apply_rls_filters(orders_list, auth.rls_filters, context)
    
    filtered_orders = []
    for order in orders_list:
        filtered_order = PermissionManager.filter_fields(
            order, auth.permissions, "orders", "read"
        )
        if filtered_order:
            filtered_orders.append(filtered_order)
    
    return {"orders": filtered_orders}

@app.get("/api/orders/{order_id}")
async def get_order(
    order_id: str,
    auth: AuthData = Depends(validate_cids_token)
):
    """Get specific order"""
    if not PermissionManager.has_permission(auth.permissions, "orders", "read"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    if order_id not in orders_db:
        raise HTTPException(status_code=404, detail="Order not found")
    
    order_data = orders_db[order_id].dict()
    filtered_order = PermissionManager.filter_fields(
        order_data, auth.permissions, "orders", "read"
    )
    
    return filtered_order

@app.get("/api/reports")
async def list_reports(
    auth: AuthData = Depends(validate_cids_token)
):
    """List all reports"""
    if not PermissionManager.has_permission(auth.permissions, "reports", "read"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    reports_list = []
    for report in reports_db.values():
        if report.confidential and not PermissionManager.has_permission(
            auth.permissions, "reports", "read", "confidential"
        ):
            continue
        
        report_data = report.dict()
        filtered_report = PermissionManager.filter_fields(
            report_data, auth.permissions, "reports", "read"
        )
        if filtered_report:
            reports_list.append(filtered_report)
    
    return {"reports": reports_list}

@app.get("/api/reports/{report_id}")
async def get_report(
    report_id: str,
    auth: AuthData = Depends(validate_cids_token)
):
    """Get specific report"""
    if not PermissionManager.has_permission(auth.permissions, "reports", "read"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    if report_id not in reports_db:
        raise HTTPException(status_code=404, detail="Report not found")
    
    report = reports_db[report_id]
    
    if report.confidential and not PermissionManager.has_permission(
        auth.permissions, "reports", "read", "confidential"
    ):
        raise HTTPException(status_code=403, detail="Access to confidential report denied")
    
    report_data = report.dict()
    filtered_report = PermissionManager.filter_fields(
        report_data, auth.permissions, "reports", "read"
    )
    
    return filtered_report

# ============================================================================
# Main entry point
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    print("=" * 60)
    print("CIDS COMPLIANT TEST APPLICATION WITH WEB UI")
    print("=" * 60)
    print(f"App Name: {CIDS_CONFIG['app_name']}")
    print(f"Version: {CIDS_CONFIG['app_version']}")
    print(f"CIDS URL: {CIDS_CONFIG['cids_base_url']}")
    print()
    print("📌 Quick Start:")
    print("1. Open browser: http://localhost:8005")
    print("2. Register app in CIDS Admin if not done")
    print("3. Enter your API key in the web interface")
    print("4. Test different endpoints and permissions")
    print()
    print("Starting server on http://localhost:8005")
    print("=" * 60)
    
    uvicorn.run(app, host="0.0.0.0", port=8005)
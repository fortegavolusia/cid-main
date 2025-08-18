"""
FastAPI Test Application for CIDS Integration

This app demonstrates:
1. CIDS authentication integration
2. Field-level discovery endpoint
3. Token validation and permission enforcement
"""
from fastapi import FastAPI, Header, HTTPException, Depends, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
import os
import httpx
import jwt
import logging
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="FastAPI Test App for CIDS",
    description="Test application demonstrating CIDS integration",
    version="1.0.0"
)

# Configuration from environment
CIDS_URL = os.getenv('CIDS_URL', 'http://localhost:8000')
CLIENT_ID = os.getenv('FASTAPI_CLIENT_ID', '')
CLIENT_SECRET = os.getenv('FASTAPI_CLIENT_SECRET', '')
APP_URL = os.getenv('APP_URL', 'http://localhost:5001')

# Store for demo data
PRODUCTS = {
    "prod001": {
        "id": "prod001",
        "name": "Laptop Pro X1",
        "description": "High-performance laptop for professionals",
        "price": 1299.99,
        "cost": 850.00,  # Sensitive field
        "inventory": 45,
        "supplier": "TechCorp Industries",  # Sensitive field
        "category": "Electronics",
        "created_at": "2024-01-15T10:30:00Z",
        "profit_margin": 34.6  # Sensitive field
    },
    "prod002": {
        "id": "prod002",
        "name": "Wireless Mouse",
        "description": "Ergonomic wireless mouse with precision tracking",
        "price": 49.99,
        "cost": 22.00,  # Sensitive field
        "inventory": 120,
        "supplier": "Peripheral Plus",  # Sensitive field
        "category": "Accessories",
        "created_at": "2024-02-01T14:20:00Z",
        "profit_margin": 56.0  # Sensitive field
    }
}

# Session storage (in production, use Redis or similar)
sessions = {}

# Templates directory
templates = Jinja2Templates(directory="templates")


# ==================== CIDS Token Validation ====================

async def validate_cids_token(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    """Validate CIDS token using the validation endpoint"""
    if not authorization:
        raise HTTPException(status_code=401, detail="No authorization header")
    
    token = authorization.replace('Bearer ', '') if authorization.startswith('Bearer ') else authorization
    
    try:
        # Validate token with CIDS
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.post(
                f"{CIDS_URL}/auth/validate",
                json={"token": token, "client_id": CLIENT_ID}
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=401, detail="Invalid token")
            
            result = response.json()
            if not result.get('valid'):
                raise HTTPException(status_code=401, detail=result.get('error', 'Invalid token'))
            
            return result.get('claims', {})
            
    except httpx.RequestError as e:
        logger.error(f"Error validating token: {e}")
        raise HTTPException(status_code=503, detail="Cannot validate token")


def filter_by_permissions(data: Dict[str, Any], permissions: List[str], resource: str) -> Dict[str, Any]:
    """Filter response data based on field-level permissions"""
    if not permissions:
        # No permissions, return only non-sensitive fields
        filtered = {}
        for key, value in data.items():
            if key not in ['cost', 'supplier', 'profit_margin']:
                filtered[key] = value
        return filtered
    
    # Check for wildcard permission
    wildcard_perm = f"{CLIENT_ID}:{resource}:read:*"
    if wildcard_perm in permissions:
        return data  # Full access
    
    # Filter based on specific field permissions
    filtered = {}
    for key, value in data.items():
        field_perm = f"{CLIENT_ID}:{resource}:read:{key}"
        if field_perm in permissions:
            filtered[key] = value
        elif key not in ['cost', 'supplier', 'profit_margin']:
            # Include non-sensitive fields by default
            filtered[key] = value
    
    return filtered


# ==================== Discovery Endpoint (No Auth Required) ====================

@app.get("/discovery/endpoints")
async def discover_endpoints(version: str = "2.0"):
    """
    CIDS Discovery Endpoint - Returns field metadata for permissions
    This endpoint MUST be accessible without authentication
    """
    
    if version != "2.0":
        # Return v1 format for backward compatibility
        return {
            "version": "1.0",
            "app_name": "FastAPI Test App",
            "endpoints": [
                {
                    "method": "GET",
                    "path": "/api/products",
                    "description": "List all products"
                },
                {
                    "method": "GET",
                    "path": "/api/products/{id}",
                    "description": "Get product details"
                }
            ]
        }
    
    # Return v2 format with field-level metadata
    return {
        "version": "2.0",
        "app_id": CLIENT_ID,  # Add the required app_id field
        "app_name": "FastAPI Test App",
        "app_description": "Test application for CIDS integration",
        "last_updated": datetime.utcnow().isoformat(),
        "endpoints": [
            {
                "method": "GET",
                "path": "/api/products",
                "operation_id": "list_products",
                "description": "List all products with filtering",
                "response_fields": {
                    "id": {
                        "type": "string",
                        "description": "Product identifier",
                        "required": True
                    },
                    "name": {
                        "type": "string",
                        "description": "Product name",
                        "required": True
                    },
                    "description": {
                        "type": "string",
                        "description": "Product description"
                    },
                    "price": {
                        "type": "number",
                        "description": "Retail price",
                        "required": True
                    },
                    "cost": {
                        "type": "number",
                        "description": "Product cost",
                        "sensitive": True,
                        "required": True
                    },
                    "inventory": {
                        "type": "integer",
                        "description": "Current inventory count"
                    },
                    "supplier": {
                        "type": "string",
                        "description": "Supplier name",
                        "sensitive": True
                    },
                    "category": {
                        "type": "string",
                        "description": "Product category"
                    },
                    "profit_margin": {
                        "type": "number",
                        "description": "Profit margin percentage",
                        "sensitive": True
                    }
                }
            },
            {
                "method": "GET",
                "path": "/api/products/{id}",
                "operation_id": "get_product",
                "description": "Get detailed product information",
                "response_fields": {
                    "id": {
                        "type": "string",
                        "description": "Product identifier",
                        "required": True
                    },
                    "name": {
                        "type": "string",
                        "description": "Product name",
                        "required": True
                    },
                    "description": {
                        "type": "string",
                        "description": "Product description"
                    },
                    "price": {
                        "type": "number",
                        "description": "Retail price",
                        "required": True
                    },
                    "cost": {
                        "type": "number",
                        "description": "Product cost",
                        "sensitive": True,
                        "required": True
                    },
                    "inventory": {
                        "type": "integer",
                        "description": "Current inventory count"
                    },
                    "supplier": {
                        "type": "string",
                        "description": "Supplier name",
                        "sensitive": True
                    },
                    "category": {
                        "type": "string",
                        "description": "Product category"
                    },
                    "created_at": {
                        "type": "string",
                        "description": "Creation timestamp"
                    },
                    "profit_margin": {
                        "type": "number",
                        "description": "Profit margin percentage",
                        "sensitive": True
                    }
                }
            },
            {
                "method": "POST",
                "path": "/api/products",
                "operation_id": "create_product",
                "description": "Create a new product",
                "request_fields": {
                    "name": {
                        "type": "string",
                        "description": "Product name",
                        "required": True
                    },
                    "description": {
                        "type": "string",
                        "description": "Product description"
                    },
                    "price": {
                        "type": "number",
                        "description": "Retail price",
                        "required": True
                    },
                    "cost": {
                        "type": "number",
                        "description": "Product cost",
                        "sensitive": True,
                        "required": True
                    },
                    "inventory": {
                        "type": "integer",
                        "description": "Initial inventory"
                    },
                    "supplier": {
                        "type": "string",
                        "description": "Supplier name",
                        "sensitive": True
                    },
                    "category": {
                        "type": "string",
                        "description": "Product category"
                    }
                }
            }
        ]
    }


# ==================== OAuth Flow Endpoints ====================

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page with login button"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>FastAPI CIDS Test App</title>
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
            }
            .container {
                background: white;
                border-radius: 10px;
                padding: 40px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.1);
            }
            h1 {
                color: #333;
                margin-bottom: 30px;
            }
            .info-box {
                background: #f8f9fa;
                border-left: 4px solid #667eea;
                padding: 20px;
                margin: 20px 0;
                border-radius: 5px;
            }
            .login-btn {
                display: inline-block;
                padding: 12px 30px;
                background: #667eea;
                color: white;
                text-decoration: none;
                border-radius: 5px;
                font-size: 16px;
                transition: all 0.3s;
            }
            .login-btn:hover {
                background: #5a67d8;
                transform: translateY(-2px);
                box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
            }
            .feature-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin: 30px 0;
            }
            .feature-card {
                background: #f8f9fa;
                padding: 20px;
                border-radius: 8px;
                border-top: 3px solid #667eea;
            }
            .feature-card h3 {
                margin-top: 0;
                color: #667eea;
            }
            code {
                background: #f1f3f5;
                padding: 2px 6px;
                border-radius: 3px;
                font-family: 'Courier New', monospace;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 FastAPI CIDS Test Application</h1>
            
            <div class="info-box">
                <h2>Welcome to the FastAPI CIDS Integration Demo</h2>
                <p>This application demonstrates how to integrate a FastAPI service with the Central Identity Service (CIDS).</p>
            </div>
            
            <div class="feature-grid">
                <div class="feature-card">
                    <h3>🔐 Authentication</h3>
                    <p>OAuth 2.0 flow with Azure AD through CIDS</p>
                </div>
                <div class="feature-card">
                    <h3>🎯 Field-Level Permissions</h3>
                    <p>Granular access control for sensitive data fields</p>
                </div>
                <div class="feature-card">
                    <h3>🔍 Discovery</h3>
                    <p>Automatic endpoint and field discovery for permissions</p>
                </div>
                <div class="feature-card">
                    <h3>📊 Sample Data</h3>
                    <p>Product inventory with sensitive cost and supplier fields</p>
                </div>
            </div>
            
            <div style="text-align: center; margin: 40px 0;">
                <a href="/login" class="login-btn">Login with CIDS</a>
            </div>
            
            <div class="info-box" style="background: #fff3cd; border-color: #ffc107;">
                <h3>🔧 Configuration Status</h3>
                <p><strong>CIDS URL:</strong> <code>""" + CIDS_URL + """</code></p>
                <p><strong>Client ID:</strong> <code>""" + (CLIENT_ID if CLIENT_ID else "Not configured") + """</code></p>
                <p><strong>App URL:</strong> <code>""" + APP_URL + """</code></p>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


@app.get("/login")
async def login():
    """Redirect to CIDS for authentication"""
    if not CLIENT_ID:
        raise HTTPException(status_code=500, detail="App not registered with CIDS")
    
    redirect_uri = f"{APP_URL}/auth/callback"
    auth_url = f"{CIDS_URL}/auth/authorize?client_id={CLIENT_ID}&redirect_uri={redirect_uri}&response_type=code&scope=openid profile email"
    
    return RedirectResponse(url=auth_url)


@app.get("/auth/callback")
async def auth_callback(code: str, request: Request):
    """Handle OAuth callback from CIDS"""
    try:
        # Exchange code for token
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.post(
                f"{CIDS_URL}/auth/token",
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "client_id": CLIENT_ID,
                    "client_secret": CLIENT_SECRET,
                    "redirect_uri": f"{APP_URL}/auth/callback"
                }
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=400, detail="Failed to exchange code for token")
            
            token_data = response.json()
            access_token = token_data.get('access_token')
            
            # Store in session (in production, use secure session management)
            import uuid
            session_id = str(uuid.uuid4())
            sessions[session_id] = {
                'access_token': access_token,
                'token_data': token_data
            }
            
            # Redirect to dashboard with session
            response = RedirectResponse(url="/dashboard")
            response.set_cookie(key="session_id", value=session_id, httponly=True)
            return response
            
    except Exception as e:
        logger.error(f"Auth callback error: {e}")
        raise HTTPException(status_code=500, detail="Authentication failed")


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Dashboard showing user info and products"""
    session_id = request.cookies.get("session_id")
    if not session_id or session_id not in sessions:
        return RedirectResponse(url="/")
    
    session = sessions[session_id]
    token = session['access_token']
    
    # Validate token and get user info
    try:
        user_info = await validate_cids_token(f"Bearer {token}")
    except:
        return RedirectResponse(url="/")
    
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>FastAPI Dashboard</title>
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
                background: #f5f5f5;
            }
            .header {
                background: white;
                padding: 20px;
                border-radius: 10px;
                margin-bottom: 20px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            .user-info {
                background: #e3f2fd;
                padding: 15px;
                border-radius: 5px;
                margin-bottom: 20px;
            }
            .products-section {
                background: white;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            table {
                width: 100%;
                border-collapse: collapse;
                margin-top: 20px;
            }
            th, td {
                padding: 12px;
                text-align: left;
                border-bottom: 1px solid #ddd;
            }
            th {
                background: #667eea;
                color: white;
            }
            .sensitive {
                background: #fff3cd;
                font-weight: bold;
            }
            .btn {
                display: inline-block;
                padding: 8px 16px;
                background: #667eea;
                color: white;
                text-decoration: none;
                border-radius: 5px;
                margin-right: 10px;
            }
            .btn:hover {
                background: #5a67d8;
            }
            .permissions {
                background: #f8f9fa;
                padding: 10px;
                border-radius: 5px;
                margin: 10px 0;
                font-family: monospace;
                font-size: 12px;
                max-height: 200px;
                overflow-y: auto;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>📊 FastAPI Dashboard</h1>
            <div class="user-info">
                <h3>User Information</h3>
                <p><strong>Email:</strong> """ + user_info.get('email', 'N/A') + """</p>
                <p><strong>Name:</strong> """ + user_info.get('name', 'N/A') + """</p>
                <p><strong>Roles:</strong> """ + str(user_info.get('roles', {}).get(CLIENT_ID, [])) + """</p>
            </div>
        </div>
        
        <div class="products-section">
            <h2>Product Inventory</h2>
            <p>Sensitive fields (cost, supplier, profit margin) are highlighted and require specific permissions.</p>
            
            <div style="margin: 20px 0;">
                <a href="/api/products" class="btn" target="_blank">View API Response</a>
                <a href="/logout" class="btn" style="background: #dc3545;">Logout</a>
            </div>
            
            <div id="products">Loading products...</div>
            
            <div class="permissions">
                <strong>Your Permissions:</strong><br>
                <pre id="permissions-list">Loading...</pre>
            </div>
        </div>
        
        <script>
            // Fetch and display products
            fetch('/api/products', {
                headers: {
                    'Authorization': 'Bearer """ + token + """'
                }
            })
            .then(response => response.json())
            .then(data => {
                let html = '<table>';
                html += '<tr><th>ID</th><th>Name</th><th>Price</th><th>Inventory</th>';
                
                // Check if sensitive fields are present
                const hasCost = data.products && data.products[0] && 'cost' in data.products[0];
                const hasSupplier = data.products && data.products[0] && 'supplier' in data.products[0];
                const hasMargin = data.products && data.products[0] && 'profit_margin' in data.products[0];
                
                if (hasCost) html += '<th class="sensitive">Cost</th>';
                if (hasSupplier) html += '<th class="sensitive">Supplier</th>';
                if (hasMargin) html += '<th class="sensitive">Margin %</th>';
                html += '</tr>';
                
                data.products.forEach(product => {
                    html += '<tr>';
                    html += `<td>${product.id}</td>`;
                    html += `<td>${product.name}</td>`;
                    html += `<td>$${product.price}</td>`;
                    html += `<td>${product.inventory || 'N/A'}</td>`;
                    if (hasCost) html += `<td class="sensitive">$${product.cost}</td>`;
                    if (hasSupplier) html += `<td class="sensitive">${product.supplier}</td>`;
                    if (hasMargin) html += `<td class="sensitive">${product.profit_margin}%</td>`;
                    html += '</tr>';
                });
                
                html += '</table>';
                
                if (!hasCost && !hasSupplier && !hasMargin) {
                    html += '<p style="color: #dc3545; margin-top: 20px;">⚠️ Sensitive fields are hidden due to insufficient permissions.</p>';
                }
                
                document.getElementById('products').innerHTML = html;
                
                // Display permissions
                if (data.permissions) {
                    document.getElementById('permissions-list').textContent = 
                        data.permissions.length > 0 ? data.permissions.join('\\n') : 'No specific permissions assigned';
                }
            })
            .catch(err => {
                document.getElementById('products').innerHTML = '<p style="color: red;">Error loading products: ' + err + '</p>';
            });
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


@app.get("/logout")
async def logout(request: Request):
    """Logout and clear session"""
    session_id = request.cookies.get("session_id")
    if session_id and session_id in sessions:
        del sessions[session_id]
    
    response = RedirectResponse(url="/")
    response.delete_cookie(key="session_id")
    return response


# ==================== Protected API Endpoints ====================

@app.get("/api/products")
async def get_products(authorization: Optional[str] = Header(None)):
    """Get all products with field-level filtering based on permissions"""
    # Validate token
    user_info = await validate_cids_token(authorization)
    
    # Get user's permissions for this app
    permissions = user_info.get('permissions', {}).get(CLIENT_ID, [])
    
    # Filter products based on permissions
    filtered_products = []
    for product_id, product_data in PRODUCTS.items():
        filtered_product = filter_by_permissions(product_data, permissions, "products")
        filtered_products.append(filtered_product)
    
    return {
        "products": filtered_products,
        "count": len(filtered_products),
        "user": user_info.get('email'),
        "permissions": permissions
    }


@app.get("/api/products/{product_id}")
async def get_product(product_id: str, authorization: Optional[str] = Header(None)):
    """Get specific product with field-level filtering"""
    # Validate token
    user_info = await validate_cids_token(authorization)
    
    # Check if product exists
    if product_id not in PRODUCTS:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Get user's permissions
    permissions = user_info.get('permissions', {}).get(CLIENT_ID, [])
    
    # Filter product based on permissions
    product = PRODUCTS[product_id]
    filtered_product = filter_by_permissions(product, permissions, "products")
    
    return {
        "product": filtered_product,
        "user": user_info.get('email'),
        "permissions": permissions
    }


class CreateProductRequest(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    cost: Optional[float] = None
    inventory: Optional[int] = 0
    supplier: Optional[str] = None
    category: Optional[str] = None


@app.post("/api/products")
async def create_product(
    product: CreateProductRequest,
    authorization: Optional[str] = Header(None)
):
    """Create a new product (requires write permissions)"""
    # Validate token
    user_info = await validate_cids_token(authorization)
    
    # Check for write permission
    permissions = user_info.get('permissions', {}).get(CLIENT_ID, [])
    write_perm = f"{CLIENT_ID}:products:write:*"
    
    if write_perm not in permissions:
        # Check for specific field permissions
        required_perms = [
            f"{CLIENT_ID}:products:write:name",
            f"{CLIENT_ID}:products:write:price"
        ]
        if not all(perm in permissions for perm in required_perms):
            raise HTTPException(status_code=403, detail="Insufficient permissions to create products")
    
    # Generate new product ID
    import uuid
    product_id = f"prod{str(uuid.uuid4())[:8]}"
    
    # Create product with allowed fields only
    new_product = {
        "id": product_id,
        "created_at": datetime.utcnow().isoformat()
    }
    
    # Add fields based on permissions
    if f"{CLIENT_ID}:products:write:*" in permissions:
        # Full write access
        new_product.update(product.dict(exclude_none=True))
    else:
        # Selective write based on field permissions
        for field in product.dict(exclude_none=True):
            field_perm = f"{CLIENT_ID}:products:write:{field}"
            if field_perm in permissions:
                new_product[field] = getattr(product, field)
    
    # Calculate profit margin if we have cost and price
    if 'cost' in new_product and 'price' in new_product:
        new_product['profit_margin'] = round(
            ((new_product['price'] - new_product['cost']) / new_product['price']) * 100, 1
        )
    
    # Store the product
    PRODUCTS[product_id] = new_product
    
    return {
        "message": "Product created successfully",
        "product": filter_by_permissions(new_product, permissions, "products"),
        "id": product_id
    }


# ==================== Health Check ====================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "app": "FastAPI CIDS Test App",
        "version": "1.0.0",
        "cids_configured": bool(CLIENT_ID and CLIENT_SECRET)
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5001)
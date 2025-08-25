#!/usr/bin/env python3
"""
CIDS-Compliant Test Application
This application demonstrates full compliance with CIDS API Registration standards.
It can be registered via the CIDS Admin GUI and uses API keys for authentication.
"""

from fastapi import FastAPI, Header, HTTPException, Depends, Request, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
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
    "api_key": os.getenv("CIDS_API_KEY", ""),  # Will be set after registration
    "cids_base_url": os.getenv("CIDS_BASE_URL", "http://localhost:8000"),
    "app_name": "CIDS Compliant Test App",
    "app_version": "2.0.0",
    "discovery_enabled": True
}

# Create FastAPI app
app = FastAPI(
    title="CIDS Compliant Test Application",
    description="A fully CIDS-compliant application demonstrating all features",
    version="2.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# Data Models
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

# ============================================================================
# Sample Data
# ============================================================================

# In-memory databases
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
# Authentication & Authorization
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
    """
    Validate token/API key with CIDS
    Supports both API keys (cids_ak_*) and JWT tokens
    """
    if not authorization:
        # For discovery endpoint, allow unauthenticated access
        return AuthData(valid=False, permissions=[])
    
    # Validate with CIDS
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

# ============================================================================
# Permission Management
# ============================================================================

class PermissionManager:
    @staticmethod
    def has_permission(
        permissions: List[str],
        resource: str,
        action: str,
        field: Optional[str] = None
    ) -> bool:
        """Check if user has required permission"""
        # Check for admin permission
        if "admin" in permissions:
            return True
        
        # Build permission string
        if field:
            # Check field-specific permission
            specific = f"compliant_app.{resource}.{action}.{field}"
            if specific in permissions:
                return True
            
            # Check wildcard permission
            wildcard = f"compliant_app.{resource}.{action}.*"
            if wildcard in permissions:
                return True
        
        # Check resource-level permission
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
            return data  # Admin sees everything
        
        filtered = {}
        
        for field, value in data.items():
            if PermissionManager.has_permission(permissions, resource, action, field):
                if isinstance(value, dict):
                    # Recursively filter nested objects
                    filtered[field] = PermissionManager.filter_fields(
                        value, permissions, f"{resource}.{field}", action
                    )
                elif isinstance(value, list) and value and isinstance(value[0], dict):
                    # Filter list of objects
                    filtered[field] = [
                        PermissionManager.filter_fields(
                            item, permissions, f"{resource}.{field}", action
                        )
                        for item in value
                    ]
                else:
                    filtered[field] = value
        
        return filtered

# ============================================================================
# RLS (Row-Level Security) Manager
# ============================================================================

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
            # Simple example: filter by department or user_id
            expression = filter_rule.get("expression", "")
            
            # Replace context variables
            for key, value in context.items():
                placeholder = f"@{key}"
                if placeholder in expression:
                    expression = expression.replace(placeholder, str(value))
            
            # Simple evaluation (in production, use proper SQL parser)
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

# ============================================================================
# Audit Logger
# ============================================================================

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
# Discovery Endpoint (REQUIRED FOR CIDS COMPLIANCE)
# ============================================================================

@app.get("/discovery/endpoints")
async def discover_endpoints(
    authorization: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """
    CIDS Discovery Endpoint
    Returns complete metadata about all available endpoints and fields
    """
    logger.info("Discovery endpoint called")
    
    return {
        "version": "2.0",
        "app_id": "compliant_app",
        "service_name": CIDS_CONFIG["app_name"],
        "description": "CIDS-compliant test application demonstrating all features",
        "base_url": "http://localhost:8001",
        "discovery_timestamp": datetime.utcnow().isoformat(),
        "endpoints": [
            # Users endpoints
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
                        "description": "List of users",
                        "item_fields": {
                            "id": {"type": "string", "description": "User ID", "required": True},
                            "email": {"type": "string", "description": "Email address", "pii": True},
                            "name": {"type": "string", "description": "Full name", "pii": True},
                            "salary": {"type": "number", "description": "Annual salary", "sensitive": True, "financial": True},
                            "ssn": {"type": "string", "description": "Social Security Number", "sensitive": True, "pii": True},
                            "phone": {"type": "string", "description": "Phone number", "pii": True},
                            "address": {"type": "string", "description": "Home address", "pii": True},
                            "department": {
                                "type": "object",
                                "description": "Department information",
                                "fields": {
                                    "id": {"type": "string"},
                                    "name": {"type": "string"},
                                    "budget": {"type": "number", "sensitive": True, "financial": True}
                                }
                            },
                            "medical_records": {"type": "object", "description": "Medical history", "sensitive": True, "phi": True},
                            "performance_rating": {"type": "number", "description": "Performance score", "sensitive": True},
                            "hire_date": {"type": "datetime", "description": "Employment start date"},
                            "is_active": {"type": "boolean", "description": "Active status"},
                            "roles": {"type": "array", "description": "User roles"}
                        }
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
                        "required": True,
                        "description": "User identifier"
                    }
                ],
                "response_fields": {
                    "id": {"type": "string", "description": "User ID", "required": True},
                    "email": {"type": "string", "description": "Email address", "pii": True},
                    "name": {"type": "string", "description": "Full name", "pii": True},
                    "salary": {"type": "number", "description": "Annual salary", "sensitive": True, "financial": True},
                    "ssn": {"type": "string", "description": "Social Security Number", "sensitive": True, "pii": True},
                    "phone": {"type": "string", "description": "Phone number", "pii": True},
                    "address": {"type": "string", "description": "Home address", "pii": True},
                    "department": {
                        "type": "object",
                        "description": "Department information",
                        "fields": {
                            "id": {"type": "string"},
                            "name": {"type": "string"},
                            "budget": {"type": "number", "sensitive": True, "financial": True},
                            "manager_id": {"type": "string"}
                        }
                    },
                    "medical_records": {"type": "object", "description": "Medical history", "sensitive": True, "phi": True},
                    "performance_rating": {"type": "number", "description": "Performance score", "sensitive": True},
                    "hire_date": {"type": "datetime", "description": "Employment start date"},
                    "is_active": {"type": "boolean", "description": "Active status"},
                    "roles": {"type": "array", "description": "User roles"},
                    "created_at": {"type": "datetime"},
                    "updated_at": {"type": "datetime"}
                }
            },
            {
                "method": "POST",
                "path": "/api/users",
                "operation_id": "create_user",
                "description": "Create new user",
                "resource": "users",
                "action": "write",
                "request_fields": {
                    "email": {"type": "string", "required": True, "pii": True},
                    "name": {"type": "string", "required": True, "pii": True},
                    "salary": {"type": "number", "sensitive": True, "financial": True},
                    "department_id": {"type": "string", "required": True}
                },
                "response_fields": {
                    "id": {"type": "string"},
                    "created_at": {"type": "datetime"},
                    "message": {"type": "string"}
                }
            },
            {
                "method": "PUT",
                "path": "/api/users/{user_id}",
                "operation_id": "update_user",
                "description": "Update user information",
                "resource": "users",
                "action": "write",
                "parameters": [
                    {
                        "name": "user_id",
                        "in": "path",
                        "type": "string",
                        "required": True
                    }
                ],
                "request_fields": {
                    "email": {"type": "string", "pii": True},
                    "name": {"type": "string", "pii": True},
                    "salary": {"type": "number", "sensitive": True, "financial": True},
                    "performance_rating": {"type": "number", "sensitive": True}
                },
                "response_fields": {
                    "id": {"type": "string"},
                    "updated_at": {"type": "datetime"},
                    "message": {"type": "string"}
                }
            },
            {
                "method": "DELETE",
                "path": "/api/users/{user_id}",
                "operation_id": "delete_user",
                "description": "Delete user",
                "resource": "users",
                "action": "delete",
                "parameters": [
                    {
                        "name": "user_id",
                        "in": "path",
                        "type": "string",
                        "required": True
                    }
                ],
                "response_fields": {
                    "message": {"type": "string"},
                    "deleted_at": {"type": "datetime"}
                }
            },
            # Orders endpoints
            {
                "method": "GET",
                "path": "/api/orders",
                "operation_id": "list_orders",
                "description": "List all orders",
                "resource": "orders",
                "action": "read",
                "response_fields": {
                    "orders": {
                        "type": "array",
                        "description": "List of orders",
                        "item_fields": {
                            "id": {"type": "string"},
                            "user_id": {"type": "string"},
                            "total_amount": {"type": "number", "financial": True},
                            "status": {"type": "string"},
                            "payment_method": {"type": "string", "sensitive": True},
                            "credit_card_last4": {"type": "string", "sensitive": True, "pii": True},
                            "created_at": {"type": "datetime"}
                        }
                    }
                }
            },
            {
                "method": "GET",
                "path": "/api/orders/{order_id}",
                "operation_id": "get_order",
                "description": "Get specific order",
                "resource": "orders",
                "action": "read",
                "parameters": [
                    {
                        "name": "order_id",
                        "in": "path",
                        "type": "string",
                        "required": True
                    }
                ],
                "response_fields": {
                    "id": {"type": "string"},
                    "user_id": {"type": "string"},
                    "total_amount": {"type": "number", "financial": True},
                    "items": {"type": "array"},
                    "status": {"type": "string"},
                    "payment_method": {"type": "string", "sensitive": True},
                    "credit_card_last4": {"type": "string", "sensitive": True, "pii": True},
                    "shipping_address": {"type": "string", "pii": True},
                    "created_at": {"type": "datetime"},
                    "shipped_at": {"type": "datetime"}
                }
            },
            # Reports endpoints
            {
                "method": "GET",
                "path": "/api/reports",
                "operation_id": "list_reports",
                "description": "List all reports",
                "resource": "reports",
                "action": "read",
                "response_fields": {
                    "reports": {
                        "type": "array",
                        "item_fields": {
                            "id": {"type": "string"},
                            "name": {"type": "string"},
                            "type": {"type": "string"},
                            "confidential": {"type": "boolean"},
                            "created_by": {"type": "string"},
                            "created_at": {"type": "datetime"}
                        }
                    }
                }
            },
            {
                "method": "GET",
                "path": "/api/reports/{report_id}",
                "operation_id": "get_report",
                "description": "Get specific report",
                "resource": "reports",
                "action": "read",
                "parameters": [
                    {
                        "name": "report_id",
                        "in": "path",
                        "type": "string",
                        "required": True
                    }
                ],
                "response_fields": {
                    "id": {"type": "string"},
                    "name": {"type": "string"},
                    "type": {"type": "string"},
                    "content": {"type": "object", "sensitive": True},
                    "confidential": {"type": "boolean"},
                    "financial_data": {"type": "object", "sensitive": True, "financial": True},
                    "created_by": {"type": "string"},
                    "created_at": {"type": "datetime"}
                }
            },
            # Health check
            {
                "method": "GET",
                "path": "/health",
                "operation_id": "health_check",
                "description": "Health check endpoint",
                "resource": "system",
                "action": "read",
                "response_fields": {
                    "status": {"type": "string"},
                    "timestamp": {"type": "datetime"},
                    "version": {"type": "string"}
                }
            }
        ]
    }

# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": CIDS_CONFIG["app_name"],
        "version": CIDS_CONFIG["app_version"],
        "status": "running",
        "discovery_endpoint": "/discovery/endpoints",
        "cids_compliant": True
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": CIDS_CONFIG["app_version"]
    }

# ============================================================================
# Users Resource
# ============================================================================

@app.get("/api/users")
async def list_users(
    auth: AuthData = Depends(validate_cids_token),
    limit: int = Query(10, description="Number of results"),
    offset: int = Query(0, description="Skip results")
):
    """List all users with permission-based field filtering"""
    
    # Check permission
    if not PermissionManager.has_permission(auth.permissions, "users", "read"):
        audit.log_access(
            auth.user.get("id") if auth.user else None,
            "users", "read", granted=False
        )
        raise HTTPException(status_code=403, detail="Permission denied")
    
    # Get users
    users_list = list(users_db.values())[offset:offset + limit]
    
    # Apply RLS filters
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
    
    # Filter fields based on permissions
    filtered_users = []
    for user in users_list:
        filtered_user = PermissionManager.filter_fields(
            user, auth.permissions, "users", "read"
        )
        if filtered_user:  # Only include if user has at least some field permissions
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
    
    # Check permission
    if not PermissionManager.has_permission(auth.permissions, "users", "read"):
        audit.log_access(
            auth.user.get("id") if auth.user else None,
            "users", "read", user_id, granted=False
        )
        raise HTTPException(status_code=403, detail="Permission denied")
    
    if user_id not in users_db:
        raise HTTPException(status_code=404, detail="User not found")
    
    user_data = users_db[user_id].dict()
    
    # Filter fields based on permissions
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
    
    # Check permission
    if not PermissionManager.has_permission(auth.permissions, "users", "write"):
        audit.log_access(
            auth.user.get("id") if auth.user else None,
            "users", "write", granted=False
        )
        raise HTTPException(status_code=403, detail="Permission denied")
    
    # Filter input fields based on write permissions
    filtered_input = PermissionManager.filter_fields(
        user_data, auth.permissions, "users", "write"
    )
    
    # Create user (simplified)
    new_id = f"user{len(users_db) + 1}"
    
    audit.log_access(
        auth.user.get("id") if auth.user else None,
        "users", "write", new_id, granted=True
    )
    
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
    
    # Check permission
    if not PermissionManager.has_permission(auth.permissions, "users", "write"):
        audit.log_access(
            auth.user.get("id") if auth.user else None,
            "users", "write", user_id, granted=False
        )
        raise HTTPException(status_code=403, detail="Permission denied")
    
    if user_id not in users_db:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Filter input fields based on write permissions
    filtered_input = PermissionManager.filter_fields(
        user_data, auth.permissions, "users", "write"
    )
    
    audit.log_access(
        auth.user.get("id") if auth.user else None,
        "users", "write", user_id, granted=True
    )
    
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
    
    # Check permission
    if not PermissionManager.has_permission(auth.permissions, "users", "delete"):
        audit.log_access(
            auth.user.get("id") if auth.user else None,
            "users", "delete", user_id, granted=False
        )
        raise HTTPException(status_code=403, detail="Permission denied")
    
    if user_id not in users_db:
        raise HTTPException(status_code=404, detail="User not found")
    
    audit.log_access(
        auth.user.get("id") if auth.user else None,
        "users", "delete", user_id, granted=True
    )
    
    return {
        "message": "User deleted successfully",
        "deleted_at": datetime.utcnow().isoformat()
    }

# ============================================================================
# Orders Resource
# ============================================================================

@app.get("/api/orders")
async def list_orders(
    auth: AuthData = Depends(validate_cids_token)
):
    """List all orders"""
    
    if not PermissionManager.has_permission(auth.permissions, "orders", "read"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    orders_list = [o.dict() for o in orders_db.values()]
    
    # Apply RLS filters
    if auth.rls_filters:
        context = {
            "current_user_id": auth.user.get("id") if auth.user else None,
            "current_user_email": auth.user.get("email") if auth.user else None,
        }
        orders_list = apply_rls_filters(orders_list, auth.rls_filters, context)
    
    # Filter fields
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
    
    # Filter fields
    filtered_order = PermissionManager.filter_fields(
        order_data, auth.permissions, "orders", "read"
    )
    
    return filtered_order

# ============================================================================
# Reports Resource
# ============================================================================

@app.get("/api/reports")
async def list_reports(
    auth: AuthData = Depends(validate_cids_token)
):
    """List all reports"""
    
    if not PermissionManager.has_permission(auth.permissions, "reports", "read"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    reports_list = []
    for report in reports_db.values():
        # Check if user can see confidential reports
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
    
    # Check confidential access
    if report.confidential and not PermissionManager.has_permission(
        auth.permissions, "reports", "read", "confidential"
    ):
        raise HTTPException(status_code=403, detail="Access to confidential report denied")
    
    report_data = report.dict()
    
    # Filter fields
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
    print("CIDS COMPLIANT TEST APPLICATION")
    print("=" * 60)
    print(f"App Name: {CIDS_CONFIG['app_name']}")
    print(f"Version: {CIDS_CONFIG['app_version']}")
    print(f"CIDS URL: {CIDS_CONFIG['cids_base_url']}")
    print(f"Discovery Enabled: {CIDS_CONFIG['discovery_enabled']}")
    print()
    print("To register this app:")
    print("1. Go to CIDS Admin Portal")
    print("2. Register app with:")
    print("   - Name: CIDS Compliant Test App")
    print("   - Discovery URL: http://localhost:8001/discovery/endpoints")
    print("3. Generate an API key")
    print("4. Set environment variable: CIDS_API_KEY=<your_key>")
    print()
    print("Starting server on http://localhost:8001")
    print("Discovery endpoint: http://localhost:8001/discovery/endpoints")
    print("=" * 60)
    
    uvicorn.run(app, host="0.0.0.0", port=8001, reload=True)
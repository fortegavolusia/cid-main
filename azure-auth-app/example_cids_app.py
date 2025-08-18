"""
Example CIDS-Compliant Application

This demonstrates how to build an application that:
1. Exposes field-level discovery metadata
2. Uses CIDS for authentication
3. Enforces field-level permissions from tokens
"""
from fastapi import FastAPI, Header, HTTPException, Depends
from fastapi.responses import JSONResponse
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel
import os
import logging

# Import CIDS auth library
from cids_auth import CIDSAuth, CIDSTokenError, CIDSPermissionDenied

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Example HR Service",
    description="CIDS-compliant HR microservice with field-level permissions",
    version="1.0.0"
)

# Initialize CIDS auth (would normally use from_env() in production)
auth = CIDSAuth(
    cids_url=os.getenv('CIDS_URL', 'https://10.1.5.58:8000'),
    client_id=os.getenv('CIDS_CLIENT_ID', 'hr_service'),
    verify_ssl=False  # Only for development!
)

# Sample data (in production, this would be from a database)
EMPLOYEES = {
    "emp001": {
        "id": "emp001",
        "name": "John Doe",
        "email": "john.doe@company.com",
        "department": "Engineering",
        "title": "Senior Engineer",
        "salary": 120000,
        "ssn": "123-45-6789",
        "performance_rating": 4.5,
        "manager_id": "emp010",
        "start_date": "2020-01-15",
        "benefits": {
            "health_plan": "Premium",
            "401k_contribution": 6,
            "vacation_days": 20
        }
    },
    "emp002": {
        "id": "emp002",
        "name": "Jane Smith",
        "email": "jane.smith@company.com",
        "department": "Marketing",
        "title": "Marketing Manager",
        "salary": 95000,
        "ssn": "987-65-4321",
        "performance_rating": 4.2,
        "manager_id": "emp011",
        "start_date": "2019-06-01",
        "benefits": {
            "health_plan": "Standard",
            "401k_contribution": 5,
            "vacation_days": 15
        }
    }
}


# Discovery endpoint - NO AUTHENTICATION REQUIRED
@app.get("/discovery/endpoints")
async def discover_endpoints(
    authorization: Optional[str] = Header(None),
    version: str = "2.0"
):
    """
    CIDS Discovery Endpoint - Returns complete field metadata
    
    This endpoint MUST be accessible to CIDS for discovery.
    It returns all fields with their types and sensitivity flags.
    """
    
    if version != "2.0":
        # Fallback to v1 discovery
        return {
            "endpoints": [
                {
                    "method": "GET",
                    "path": "/employees",
                    "description": "List all employees",
                    "required_roles": ["hr_viewer", "hr_admin"]
                },
                {
                    "method": "GET",
                    "path": "/employees/{employee_id}",
                    "description": "Get employee details",
                    "required_roles": ["hr_viewer", "hr_admin"]
                }
            ]
        }
    
    # V2 discovery with field-level metadata
    return {
        "version": "2.0",
        "app_id": auth.client_id,
        "app_name": "HR Service",
        "description": "Human Resources management service",
        "endpoints": [
            {
                "method": "GET",
                "path": "/employees",
                "operation_id": "list_employees",
                "description": "List all employees with permitted fields",
                "response_fields": {
                    "id": {
                        "type": "string",
                        "description": "Employee ID"
                    },
                    "name": {
                        "type": "string",
                        "description": "Employee full name"
                    },
                    "email": {
                        "type": "string",
                        "description": "Work email address",
                        "format": "email"
                    },
                    "department": {
                        "type": "string",
                        "description": "Department name"
                    },
                    "title": {
                        "type": "string",
                        "description": "Job title"
                    },
                    "salary": {
                        "type": "number",
                        "description": "Annual salary",
                        "sensitive": True
                    },
                    "ssn": {
                        "type": "string",
                        "description": "Social Security Number",
                        "sensitive": True,
                        "pii": True,
                        "format": "ssn"
                    },
                    "performance_rating": {
                        "type": "number",
                        "description": "Performance rating (1-5)",
                        "sensitive": True
                    },
                    "manager_id": {
                        "type": "string",
                        "description": "Manager's employee ID"
                    },
                    "start_date": {
                        "type": "string",
                        "description": "Employment start date",
                        "format": "date"
                    }
                }
            },
            {
                "method": "GET",
                "path": "/employees/{employee_id}",
                "operation_id": "get_employee",
                "description": "Get detailed employee information",
                "parameters": [
                    {
                        "name": "employee_id",
                        "in": "path",
                        "type": "string",
                        "description": "Employee ID",
                        "required": True
                    }
                ],
                "response_fields": {
                    "id": {
                        "type": "string",
                        "description": "Employee ID"
                    },
                    "name": {
                        "type": "string",
                        "description": "Employee full name"
                    },
                    "email": {
                        "type": "string",
                        "description": "Work email address",
                        "format": "email"
                    },
                    "department": {
                        "type": "string",
                        "description": "Department name"
                    },
                    "title": {
                        "type": "string",
                        "description": "Job title"
                    },
                    "salary": {
                        "type": "number",
                        "description": "Annual salary",
                        "sensitive": True
                    },
                    "ssn": {
                        "type": "string",
                        "description": "Social Security Number",
                        "sensitive": True,
                        "pii": True,
                        "format": "ssn"
                    },
                    "performance_rating": {
                        "type": "number",
                        "description": "Performance rating (1-5)",
                        "sensitive": True
                    },
                    "manager_id": {
                        "type": "string",
                        "description": "Manager's employee ID"
                    },
                    "start_date": {
                        "type": "string",
                        "description": "Employment start date",
                        "format": "date"
                    },
                    "benefits": {
                        "type": "object",
                        "description": "Employee benefits",
                        "fields": {
                            "health_plan": {
                                "type": "string",
                                "description": "Health insurance plan",
                                "sensitive": True,
                                "phi": True
                            },
                            "401k_contribution": {
                                "type": "number",
                                "description": "401k contribution percentage",
                                "sensitive": True
                            },
                            "vacation_days": {
                                "type": "number",
                                "description": "Annual vacation days"
                            }
                        }
                    }
                }
            },
            {
                "method": "PUT",
                "path": "/employees/{employee_id}/salary",
                "operation_id": "update_salary",
                "description": "Update employee salary",
                "parameters": [
                    {
                        "name": "employee_id",
                        "in": "path",
                        "type": "string",
                        "required": True
                    }
                ],
                "request_fields": {
                    "new_salary": {
                        "type": "number",
                        "description": "New annual salary",
                        "required": True,
                        "sensitive": True
                    },
                    "effective_date": {
                        "type": "string",
                        "format": "date",
                        "description": "Date when new salary takes effect",
                        "required": True
                    },
                    "reason": {
                        "type": "string",
                        "description": "Reason for salary change",
                        "required": True
                    }
                }
            }
        ],
        "last_updated": datetime.utcnow().isoformat()
    }


# Protected endpoints - these enforce field-level permissions

@app.get("/employees")
async def list_employees(
    authorization: Optional[str] = Header(None)
):
    """List all employees with field filtering based on permissions"""
    try:
        # Validate token and get user info
        user_info = auth.validate_token(authorization)
        logger.info(f"User {user_info['email']} accessing employee list")
        
        # Get all employee data
        all_employees = list(EMPLOYEES.values())
        
        # Filter fields based on user's permissions
        filtered_employees = auth.filter_fields(
            data=all_employees,
            user_permissions=user_info['permissions'],
            resource='employees',
            action='read'
        )
        
        return {
            "employees": filtered_employees,
            "count": len(filtered_employees),
            "filtered_by": "permissions"
        }
        
    except CIDSTokenError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        logger.error(f"Error listing employees: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/employees/{employee_id}")
async def get_employee(
    employee_id: str,
    authorization: Optional[str] = Header(None)
):
    """Get employee details with field filtering based on permissions"""
    try:
        # Validate token and get user info
        user_info = auth.validate_token(authorization)
        logger.info(f"User {user_info['email']} accessing employee {employee_id}")
        
        # Check if employee exists
        if employee_id not in EMPLOYEES:
            raise HTTPException(status_code=404, detail="Employee not found")
        
        # Get employee data
        employee_data = EMPLOYEES[employee_id]
        
        # Filter fields based on user's permissions
        filtered_data = auth.filter_fields(
            data=employee_data,
            user_permissions=user_info['permissions'],
            resource='employees',
            action='read'
        )
        
        return filtered_data
        
    except CIDSTokenError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting employee {employee_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.put("/employees/{employee_id}/salary")
async def update_salary(
    employee_id: str,
    new_salary: float,
    effective_date: str,
    reason: str,
    authorization: Optional[str] = Header(None)
):
    """Update employee salary - requires write permission on salary field"""
    try:
        # Validate token and get user info
        user_info = auth.validate_token(authorization)
        
        # Check specific permission for salary updates
        required_permission = f"{auth.client_id}.employees.write.salary"
        if not auth.check_permission(user_info, required_permission):
            logger.warning(f"User {user_info['email']} denied salary update - missing {required_permission}")
            raise HTTPException(
                status_code=403,
                detail=f"Permission denied. Required: {required_permission}"
            )
        
        logger.info(f"User {user_info['email']} updating salary for {employee_id}")
        
        # Check if employee exists
        if employee_id not in EMPLOYEES:
            raise HTTPException(status_code=404, detail="Employee not found")
        
        # Update salary (in production, this would update the database)
        old_salary = EMPLOYEES[employee_id]["salary"]
        EMPLOYEES[employee_id]["salary"] = new_salary
        
        # Log the change
        logger.info(
            f"Salary updated for {employee_id}: {old_salary} -> {new_salary} "
            f"by {user_info['email']} effective {effective_date}. Reason: {reason}"
        )
        
        return {
            "status": "success",
            "employee_id": employee_id,
            "old_salary": old_salary,
            "new_salary": new_salary,
            "effective_date": effective_date,
            "updated_by": user_info['email'],
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except CIDSTokenError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating salary for {employee_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "hr_service",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }


# Root endpoint with service info
@app.get("/")
async def root():
    """Service information"""
    return {
        "service": "HR Service",
        "description": "CIDS-compliant HR microservice",
        "version": "1.0.0",
        "cids_compliant": True,
        "discovery_endpoint": "/discovery/endpoints",
        "endpoints": [
            {"method": "GET", "path": "/employees", "description": "List employees"},
            {"method": "GET", "path": "/employees/{id}", "description": "Get employee details"},
            {"method": "PUT", "path": "/employees/{id}/salary", "description": "Update salary"}
        ]
    }


if __name__ == "__main__":
    import uvicorn
    
    # Get configuration from environment
    host = os.getenv('APP_HOST', '0.0.0.0')
    port = int(os.getenv('APP_PORT', '8001'))
    
    logger.info(f"Starting HR Service on {host}:{port}")
    logger.info(f"CIDS URL: {auth.cids_url}")
    logger.info(f"Client ID: {auth.client_id}")
    
    uvicorn.run(app, host=host, port=port)
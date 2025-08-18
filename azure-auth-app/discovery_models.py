"""
Enhanced Discovery Models for Field-Level Permissions

These models define the structure for discovering complete field-level metadata
from CIDS-compliant applications.
"""
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, validator
from datetime import datetime
from enum import Enum


class FieldType(str, Enum):
    """Supported field data types"""
    STRING = "string"
    NUMBER = "number"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    OBJECT = "object"
    ARRAY = "array"
    DATE = "date"
    DATETIME = "datetime"
    

class ParameterLocation(str, Enum):
    """Parameter location in request"""
    PATH = "path"
    QUERY = "query"
    HEADER = "header"
    COOKIE = "cookie"


class FieldMetadata(BaseModel):
    """Metadata for a single field"""
    type: FieldType
    description: Optional[str] = None
    sensitive: bool = False
    pii: bool = False  # Personally Identifiable Information
    phi: bool = False  # Protected Health Information
    required: bool = False
    read_only: bool = False
    write_only: bool = False
    format: Optional[str] = None  # e.g., "email", "uuid", "ssn"
    enum: Optional[List[Any]] = None  # Allowed values
    pattern: Optional[str] = None  # Regex pattern
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    minimum: Optional[Union[int, float]] = None
    maximum: Optional[Union[int, float]] = None
    # For nested objects
    fields: Optional[Dict[str, 'FieldMetadata']] = None
    # For arrays
    items: Optional['FieldMetadata'] = None
    
    @validator('fields')
    def validate_fields_for_objects(cls, v, values):
        """Ensure fields is only set for object types"""
        if v is not None and values.get('type') != FieldType.OBJECT:
            raise ValueError('fields can only be set for object type')
        return v
    
    @validator('items')
    def validate_items_for_arrays(cls, v, values):
        """Ensure items is only set for array types"""
        if v is not None and values.get('type') != FieldType.ARRAY:
            raise ValueError('items can only be set for array type')
        return v


class ParameterMetadata(BaseModel):
    """Metadata for request parameters"""
    name: str
    location: ParameterLocation = Field(..., alias="in")
    type: FieldType
    description: Optional[str] = None
    required: bool = False
    sensitive: bool = False
    enum: Optional[List[Any]] = None
    pattern: Optional[str] = None
    

class EndpointMetadata(BaseModel):
    """Complete metadata for an API endpoint"""
    method: str = Field(..., pattern="^(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)$")
    path: str
    operation_id: str  # Unique identifier for the operation
    description: str
    tags: Optional[List[str]] = []
    
    # Parameters (path, query, header, cookie)
    parameters: Optional[List[ParameterMetadata]] = []
    
    # Response fields for successful responses
    response_fields: Optional[Dict[str, FieldMetadata]] = None
    
    # Request body fields (for POST, PUT, PATCH)
    request_fields: Optional[Dict[str, FieldMetadata]] = None
    
    # Traditional role requirements (being phased out)
    required_roles: Optional[List[str]] = []
    
    # Metadata
    deprecated: bool = False
    internal: bool = False  # Internal-only endpoint
    rate_limit: Optional[int] = None  # Requests per minute
    
    class Config:
        allow_population_by_field_name = True


class ServiceMetadata(BaseModel):
    """Metadata for a service within an application"""
    name: str
    version: str
    description: Optional[str] = None
    base_path: Optional[str] = "/"
    endpoints: List[EndpointMetadata]


class DiscoveryResponse(BaseModel):
    """Complete discovery response from an application"""
    version: str = Field(default="2.0")
    app_id: str
    app_name: str
    description: Optional[str] = None
    
    # For single-service apps
    endpoints: Optional[List[EndpointMetadata]] = None
    
    # For multi-service apps
    services: Optional[List[ServiceMetadata]] = None
    
    # Metadata
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    contact: Optional[Dict[str, str]] = None  # {"email": "...", "name": "..."}
    documentation_url: Optional[str] = None
    
    @validator('services')
    def validate_endpoints_or_services(cls, v, values):
        """Ensure either endpoints or services is provided, not both"""
        if v is not None and values.get('endpoints') is not None:
            raise ValueError('Cannot specify both endpoints and services')
        if v is None and values.get('endpoints') is None:
            raise ValueError('Must specify either endpoints or services')
        return v


class PermissionMetadata(BaseModel):
    """Generated permission from discovered fields"""
    permission_key: str  # e.g., "users.read.salary"
    resource: str  # e.g., "users"
    action: str  # e.g., "read"
    field_path: str  # e.g., "salary" or "department.budget"
    description: str
    sensitive: bool = False
    pii: bool = False
    phi: bool = False
    endpoint_id: str  # operation_id of source endpoint
    auto_generated: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)


class DiscoveredPermissions(BaseModel):
    """Collection of auto-generated permissions for an app"""
    app_id: str
    permissions: Dict[str, PermissionMetadata]  # key = permission_key
    total_count: int
    sensitive_count: int
    last_discovered: datetime
    discovery_version: str = "2.0"


# Update forward references
FieldMetadata.model_rebuild()


# Helper functions for permission generation
def generate_permission_key(app_id: str, resource: str, action: str, field_path: str) -> str:
    """Generate a permission key from components"""
    # Remove {id} and similar from resource paths
    resource = resource.replace('/{', '/').replace('}', '').strip('/')
    resource = resource.replace('/', '_')
    
    return f"{app_id}.{resource}.{action}.{field_path}"


def extract_resource_from_path(path: str) -> str:
    """Extract resource name from API path"""
    # /api/users/{id} -> users
    # /api/users/{id}/profile -> users_profile
    parts = path.strip('/').split('/')
    # Remove 'api' prefix if present
    if parts and parts[0] == 'api':
        parts = parts[1:]
    
    # Remove parameter placeholders
    cleaned_parts = []
    for part in parts:
        if not (part.startswith('{') and part.endswith('}')):
            cleaned_parts.append(part)
    
    return '_'.join(cleaned_parts) if cleaned_parts else 'root'


def extract_action_from_method(method: str, is_collection: bool = False) -> str:
    """Map HTTP method to action"""
    mapping = {
        'GET': 'read',
        'POST': 'create' if is_collection else 'update',
        'PUT': 'update',
        'PATCH': 'update',
        'DELETE': 'delete',
        'HEAD': 'check',
        'OPTIONS': 'options'
    }
    return mapping.get(method.upper(), 'execute')
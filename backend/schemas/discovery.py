"""
Enhanced Discovery Models for Field-Level Permissions (migrated)
"""
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, validator
from datetime import datetime
from enum import Enum


class FieldType(str, Enum):
    STRING = "string"
    NUMBER = "number"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    OBJECT = "object"
    ARRAY = "array"
    DATE = "date"
    DATETIME = "datetime"


class ParameterLocation(str, Enum):
    PATH = "path"
    QUERY = "query"
    HEADER = "header"
    COOKIE = "cookie"


class FieldMetadata(BaseModel):
    type: FieldType
    description: Optional[str] = None
    sensitive: bool = False
    pii: bool = False
    phi: bool = False
    required: bool = False
    read_only: bool = False
    write_only: bool = False
    format: Optional[str] = None
    enum: Optional[List[Any]] = None
    pattern: Optional[str] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    minimum: Optional[Union[int, float]] = None
    maximum: Optional[Union[int, float]] = None
    fields: Optional[Dict[str, 'FieldMetadata']] = None
    items: Optional['FieldMetadata'] = None

    @validator('fields')
    def validate_fields_for_objects(cls, v, values):
        if v is not None and values.get('type') != FieldType.OBJECT:
            raise ValueError('fields can only be set for object type')
        return v

    @validator('items')
    def validate_items_for_arrays(cls, v, values):
        if v is not None and values.get('type') != FieldType.ARRAY:
            raise ValueError('items can only be set for array type')
        return v


class ParameterMetadata(BaseModel):
    name: str
    location: ParameterLocation = Field(..., alias="in")
    type: FieldType
    description: Optional[str] = None
    required: bool = False
    sensitive: bool = False
    enum: Optional[List[Any]] = None
    pattern: Optional[str] = None


class EndpointMetadata(BaseModel):
    method: str = Field(..., pattern="^(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)$")
    path: str
    operation_id: str
    description: str
    tags: Optional[List[str]] = []
    parameters: Optional[List[ParameterMetadata]] = []
    response_fields: Optional[Dict[str, FieldMetadata]] = None
    request_fields: Optional[Dict[str, FieldMetadata]] = None
    required_roles: Optional[List[str]] = []
    deprecated: bool = False
    internal: bool = False
    rate_limit: Optional[int] = None

    class Config:
        allow_population_by_field_name = True


class ServiceMetadata(BaseModel):
    name: str
    version: str
    description: Optional[str] = None
    base_path: Optional[str] = "/"
    endpoints: List[EndpointMetadata]


class DiscoveryResponse(BaseModel):
    version: str = Field(default="2.0")
    app_id: str
    app_name: str
    description: Optional[str] = None
    endpoints: Optional[List[EndpointMetadata]] = None
    services: Optional[List[ServiceMetadata]] = None
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    contact: Optional[Dict[str, str]] = None
    documentation_url: Optional[str] = None

    @validator('services')
    def validate_endpoints_or_services(cls, v, values):
        if v is not None and values.get('endpoints') is not None:
            raise ValueError('Cannot specify both endpoints and services')
        if v is None and values.get('endpoints') is None:
            raise ValueError('Must specify either endpoints or services')
        return v


class PermissionMetadata(BaseModel):
    permission_key: str
    resource: str
    action: str
    field_path: str
    description: str
    sensitive: bool = False
    pii: bool = False
    phi: bool = False
    endpoint_id: str
    auto_generated: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)


class DiscoveredPermissions(BaseModel):
    app_id: str
    permissions: Dict[str, PermissionMetadata]
    total_count: int
    sensitive_count: int
    last_discovered: datetime
    discovery_version: str = "2.0"


# Helper functions for permission generation

def generate_permission_key(app_id: str, resource: str, action: str, field_path: str) -> str:
    resource = resource.replace('/{', '/').replace('}', '').strip('/')
    resource = resource.replace('/', '_')
    return f"{app_id}.{resource}.{action}.{field_path}"


def extract_resource_from_path(path: str) -> str:
    parts = path.strip('/').split('/')
    if parts and parts[0] == 'api':
        parts = parts[1:]
    cleaned_parts = []
    for part in parts:
        if not (part.startswith('{') and part.endswith('}')):
            cleaned_parts.append(part)
    return '_'.join(cleaned_parts) if cleaned_parts else 'root'


def extract_action_from_method(method: str, is_collection: bool = False) -> str:
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


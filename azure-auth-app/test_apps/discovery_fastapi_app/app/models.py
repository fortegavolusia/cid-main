from typing import List, Optional, Dict, Literal
from pydantic import BaseModel, Field

HttpMethod = Literal["GET", "POST", "PUT", "PATCH", "DELETE"]


class FieldMeta(BaseModel):
    type: Literal["string", "number", "integer", "boolean", "object", "array"] = "string"
    description: Optional[str] = None
    required: Optional[bool] = None
    sensitive: Optional[bool] = None


class Endpoint(BaseModel):
    method: HttpMethod
    path: str = Field(..., description="Path template like /api/items or /api/items/{id}")
    operation_id: Optional[str] = None
    description: Optional[str] = None
    request_fields: Optional[Dict[str, FieldMeta]] = None
    response_fields: Optional[Dict[str, FieldMeta]] = None


class AppMeta(BaseModel):
    app_id: str
    app_name: str = "Discovery Test App"
    app_description: str = "Test app for generating CID-discoverable endpoints and fields"
    last_updated: str
    endpoints: List[Endpoint] = Field(default_factory=list)


class Metadata(BaseModel):
    app: AppMeta


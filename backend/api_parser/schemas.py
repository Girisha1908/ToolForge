from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class ParameterSchema(BaseModel):
    name: str
    in_location: str = Field(description="'query', 'path', 'header', or 'cookie'")
    type: str = Field(default="string")
    required: bool = False
    description: Optional[str] = None
    default: Optional[Any] = None
    enum: Optional[List[Any]] = None


class RequestBodySchema(BaseModel):
    content_type: str = Field(default="application/json")
    schema_definition: Optional[Dict[str, Any]] = Field(default_factory=dict, description="JSON schema or structure definition")
    required: bool = True
    description: Optional[str] = None


class ResponseSchema(BaseModel):
    status_code: int = 200
    description: Optional[str] = None
    content_type: str = Field(default="application/json")
    schema_definition: Optional[Dict[str, Any]] = Field(default_factory=dict)


class ErrorFormatSchema(BaseModel):
    status_code: Optional[int] = None
    code: Optional[str] = None
    message: Optional[str] = None
    description: Optional[str] = None
    schema_definition: Optional[Dict[str, Any]] = Field(default_factory=dict)


class PaginationSchema(BaseModel):
    type: str = Field(default="none", description="'cursor', 'offset_limit', 'page_number', 'link_header', or 'none'")
    page_param: Optional[str] = None
    limit_param: Optional[str] = None
    cursor_param: Optional[str] = None
    results_key: Optional[str] = None
    next_token_key: Optional[str] = None


class AuthenticationSchema(BaseModel):
    type: str = Field(default="none", description="'bearer', 'api_key', 'basic', 'oauth2', or 'none'")
    in_location: Optional[str] = Field(default=None, description="'header', 'query', or 'cookie'")
    name: Optional[str] = Field(default=None, description="Header or query param name (e.g., X-API-Key, Authorization)")
    scheme: Optional[str] = Field(default=None, description="e.g., Bearer, Basic")
    description: Optional[str] = None


class EndpointSchema(BaseModel):
    name: str
    summary: Optional[str] = None
    description: Optional[str] = None
    method: str = Field(description="HTTP method in uppercase: GET, POST, PUT, DELETE, PATCH, etc.")
    path: str = Field(description="URL path, e.g. /users/{id}")
    parameters: List[ParameterSchema] = Field(default_factory=list)
    request_body: Optional[RequestBodySchema] = None
    responses: List[ResponseSchema] = Field(default_factory=list)
    errors: List[ErrorFormatSchema] = Field(default_factory=list)
    pagination: Optional[PaginationSchema] = None
    constraints: List[str] = Field(default_factory=list, description="e.g. rate limits, required scopes, max payload size")


class NormalizedAPISpec(BaseModel):
    api_name: str
    version: Optional[str] = "1.0.0"
    base_url: Optional[str] = None
    description: Optional[str] = None
    authentication: AuthenticationSchema = Field(default_factory=AuthenticationSchema)
    endpoints: List[EndpointSchema] = Field(default_factory=list)
    error_formats: List[ErrorFormatSchema] = Field(default_factory=list)
    global_constraints: List[str] = Field(default_factory=list)
    source_url: Optional[str] = None

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from api_parser.schemas import AuthenticationSchema, ParameterSchema, RequestBodySchema, ResponseSchema, ErrorFormatSchema


class ToolParameter(BaseModel):
    name: str
    type: str = "string"
    in_location: str = "query"  # query, path, header, body
    required: bool = False
    description: Optional[str] = None
    default: Optional[Any] = None
    enum: Optional[List[Any]] = None


class ToolDefinition(BaseModel):
    id: str = Field(description="Unique tool identifier, e.g., get_user_by_id")
    name: str = Field(description="Deterministic snake_case unique name")
    description: str = Field(description="Agent-friendly description of what the tool does")
    method: str = Field(description="HTTP Method: GET, POST, PUT, DELETE, PATCH, etc.")
    path: str = Field(description="URL path, e.g., /users/{id}")
    base_url: Optional[str] = Field(default=None, description="Resolved API base URL")
    parameters: List[ToolParameter] = Field(default_factory=list)
    request_body_schema: Optional[Dict[str, Any]] = Field(default=None, description="JSON Schema for request body if applicable")
    expected_response_schema: Optional[Dict[str, Any]] = Field(default=None, description="Expected response schema")
    authentication: AuthenticationSchema = Field(default_factory=AuthenticationSchema)
    error_handling: List[ErrorFormatSchema] = Field(default_factory=list)


class GeneratedConnector(BaseModel):
    api_name: str
    version: str = "1.0.0"
    base_url: Optional[str] = None
    description: Optional[str] = None
    tools: List[ToolDefinition] = Field(default_factory=list)


class ToolExecutionRequest(BaseModel):
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Key-value arguments for execution")


class ToolExecutionResult(BaseModel):
    success: bool
    tool: str
    status_code: int
    latency_ms: float
    request: Dict[str, Any]
    response: Any
    error: Optional[str] = None

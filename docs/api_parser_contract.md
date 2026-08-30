# Integration Contract: API Parser -> Connector Generator

This document defines the interface and data contract between the **API Documentation Parser module** (`api_parser`) and the **Connector Generation module** (`tool_generator`).

---

## 1. Public Import & Interface

The connector-generation module should import the orchestrator class and Pydantic schemas directly from `api_parser`:

```python
from api_parser import APIParser, NormalizedAPISpec

# Asynchronous usage (recommended in FastAPI / async flows):
parser = APIParser()
spec: NormalizedAPISpec = await parser.parse_doc(url_or_raw_string)

# Synchronous usage:
spec: NormalizedAPISpec = parser.parse_spec(url_or_raw_string)
```

---

## 2. Interface Guarantees & Contract

The `NormalizedAPISpec` object returned by `parse_doc()` or `parse_spec()` strictly enforces the following guarantees:

### Top-Level Guarantees
- `api_name` *(str)*: **Guaranteed string**. Fallback is `"Example API"` or non-empty sanitized string.
- `version` *(str)*: **Guaranteed string**. Default is `"1.0.0"`.
- `base_url` *(Optional[str])*: Resolved base URL (e.g., `https://api.example.com/v1`) or `None` if absent in docs.
- `description` *(Optional[str])*: Brief summary string or empty string `""`.
- `authentication` *(AuthenticationSchema)*: **Guaranteed object**.
  - `type`: One of `"bearer"`, `"api_key"`, `"basic"`, `"oauth2"`, or `"none"`.
  - `in_location`: One of `"header"`, `"query"`, `"cookie"`, or `None`.
  - `name`: Parameter/header name (e.g., `"Authorization"`, `"X-API-Key"`) or `None`.
  - `scheme`: Scheme name (e.g., `"Bearer"`, `"Basic"`) or `None`.
- `endpoints` *(List[EndpointSchema])*: **Guaranteed list**. Can be empty if no endpoints could be found.
- `error_formats` *(List[ErrorFormatSchema])*: List of common global error schemas.
- `global_constraints` *(List[str])*: List of rate limits or scope constraints.
- `source_url` *(Optional[str])*: Original URL string or `None`.

### Endpoint-Level Guarantees (`EndpointSchema`)
- `name` *(str)*: **Guaranteed unique `snake_case` identifier** for code generation (e.g. `list_users`, `get_user_by_id`). Suffixes (`_1`, `_2`) are appended automatically if duplicate names occur.
- `method` *(str)*: **Guaranteed uppercase HTTP method**: `"GET"`, `"POST"`, `"PUT"`, `"DELETE"`, `"PATCH"`, `"HEAD"`, or `"OPTIONS"`.
- `path` *(str)*: **Guaranteed leading slash** path string (e.g. `/users/{id}`).
- `summary` *(Optional[str])*: Summary string or default `"{METHOD} {path}"`.
- `description` *(Optional[str])*: Detail string or `""`.
- `parameters` *(List[ParameterSchema])*: **Guaranteed list**.
  - `name`: Parameter name.
  - `in_location`: `"query"`, `"path"`, `"header"`, or `"cookie"`.
  - `type`: Low-case type name (e.g. `"string"`, `"integer"`, `"boolean"`, `"array"`).
  - `required`: Boolean flag.
- `request_body` *(Optional[RequestBodySchema])*: `None` for endpoints without body, or an object containing `content_type` and fully resolved `schema_definition` dict.
- `responses` *(List[ResponseSchema])*: **Guaranteed at least one entry**. Default contains `status_code=200` if unknown.
- `errors` *(List[ErrorFormatSchema])*: Error response definitions (status codes >= 400).
- `pagination` *(Optional[PaginationSchema])*: `None` if unpaginated, or `PaginationSchema` containing `type` (`"cursor"`, `"offset_limit"`, `"page_number"`), `page_param`, `limit_param`, `cursor_param`.
- `constraints` *(List[str])*: Specific constraints (e.g., `"Deprecated endpoint"`).

---

## 3. Example Normalized Specification Output

Below is a complete JSON representation of a `NormalizedAPISpec` object for a small API with 2 endpoints:

```json
{
  "api_name": "User Management Service",
  "version": "1.0.0",
  "base_url": "https://api.example.com/v1",
  "description": "API for managing user accounts and profiles.",
  "authentication": {
    "type": "bearer",
    "in_location": "header",
    "name": "Authorization",
    "scheme": "Bearer",
    "description": "Bearer token authentication header"
  },
  "endpoints": [
    {
      "name": "search_users",
      "summary": "List or search users",
      "description": "Returns a paginated list of active users.",
      "method": "GET",
      "path": "/users",
      "parameters": [
        {
          "name": "query",
          "in_location": "query",
          "type": "string",
          "required": false,
          "description": "Search string filter",
          "default": null,
          "enum": null
        },
        {
          "name": "limit",
          "in_location": "query",
          "type": "integer",
          "required": false,
          "description": "Page size limit",
          "default": 20,
          "enum": null
        },
        {
          "name": "page",
          "in_location": "query",
          "type": "integer",
          "required": false,
          "description": "Page number",
          "default": 1,
          "enum": null
        }
      ],
      "request_body": null,
      "responses": [
        {
          "status_code": 200,
          "description": "Successfully retrieved users",
          "content_type": "application/json",
          "schema_definition": {
            "type": "object",
            "properties": {
              "data": {
                "type": "array",
                "items": {
                  "type": "object",
                  "properties": {
                    "id": {"type": "string"},
                    "email": {"type": "string"}
                  }
                }
              }
            }
          }
        }
      ],
      "errors": [
        {
          "status_code": 401,
          "code": "401",
          "message": "HTTP 401 error",
          "description": "Unauthorized access token",
          "schema_definition": {}
        }
      ],
      "pagination": {
        "type": "page_number",
        "page_param": "page",
        "limit_param": "limit",
        "cursor_param": null,
        "results_key": null,
        "next_token_key": null
      },
      "constraints": []
    },
    {
      "name": "create_user",
      "summary": "Create user profile",
      "description": "Registers a new user account.",
      "method": "POST",
      "path": "/users",
      "parameters": [],
      "request_body": {
        "content_type": "application/json",
        "schema_definition": {
          "type": "object",
          "required": ["email", "name"],
          "properties": {
            "email": {"type": "string"},
            "name": {"type": "string"},
            "role": {"type": "string", "enum": ["admin", "member"]}
          }
        },
        "required": true,
        "description": "New user details"
      },
      "responses": [
        {
          "status_code": 201,
          "description": "User created successfully",
          "content_type": "application/json",
          "schema_definition": {
            "type": "object",
            "properties": {
              "id": {"type": "string"},
              "email": {"type": "string"}
            }
          }
        }
      ],
      "errors": [
        {
          "status_code": 400,
          "code": "400",
          "message": "HTTP 400 error",
          "description": "Invalid input payload",
          "schema_definition": {}
        }
      ],
      "pagination": null,
      "constraints": []
    }
  ],
  "error_formats": [],
  "global_constraints": ["Rate limit: 100 requests per minute"],
  "source_url": "https://api.example.com/docs"
}
```

"""Turn a ToolDefinition into what an MCP client needs: a name, a JSON input schema, a write flag."""

import re
from typing import Any, Dict

from tool_generator.schemas import ToolDefinition

WRITE_METHODS = ("POST", "PUT", "PATCH", "DELETE")
JSON_TYPES = ("string", "integer", "number", "boolean", "array", "object")


def api_slug(name: str) -> str:
    """'Pet Store API' -> 'pet_store_api'. Used for file names, tool prefixes and env var prefixes."""
    slug = re.sub(r"[^a-z0-9]+", "_", (name or "api").lower()).strip("_")
    return slug or "api"


def env_prefix(api_name: str) -> str:
    """Per-API environment variable prefix, e.g. 'Pet Store' -> 'PET_STORE' (PET_STORE_API_KEY...)."""
    return api_slug(api_name).upper()


def mcp_tool_name(api_name: str, tool: ToolDefinition) -> str:
    """<api>__<tool>, at most 64 characters (a common client limit)."""
    return f"{api_slug(api_name)}__{tool.name}"[:64]


def is_write(tool: ToolDefinition) -> bool:
    return (tool.method or "GET").upper() in WRITE_METHODS


def input_schema(tool: ToolDefinition) -> Dict[str, Any]:
    """JSON schema of the arguments the agent may supply. The agent never supplies URL, method or headers."""
    properties: Dict[str, Any] = {}
    required = []
    for param in tool.parameters:
        kind = param.type if param.type in JSON_TYPES else "string"
        prop: Dict[str, Any] = {"type": kind}
        if param.description:
            prop["description"] = param.description
        if param.enum:
            prop["enum"] = param.enum
        properties[param.name] = prop
        if param.required or f"{{{param.name}}}" in tool.path:
            required.append(param.name)
    # The executor sends any extra arguments as the JSON body, so expose the body's top-level fields.
    body = tool.request_body_schema or {}
    for name, sub in (body.get("properties") or {}).items():
        if name not in properties and isinstance(sub, dict):
            prop = {"type": sub.get("type") if sub.get("type") in JSON_TYPES else "string"}
            if sub.get("description"):
                prop["description"] = sub["description"]
            properties[name] = prop
    for name in body.get("required") or []:
        if name in properties and name not in required:
            required.append(name)
    if is_write(tool):
        properties["confirm"] = {
            "type": "boolean",
            "description": "Safe mode: this tool changes data. Without confirm=true it only returns a preview.",
        }
    schema: Dict[str, Any] = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required
    return schema

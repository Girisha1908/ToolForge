"""The MCP server. The model supplies arguments only; URL, method and auth come from the saved tool.

Safety rules (each has a test):
  1. Writes (POST/PUT/PATCH/DELETE) only return a preview until the agent passes confirm=true.
  2. Credentials come from environment variables and are scrubbed from everything we return.
  3. Responses are trimmed so one call cannot flood the model's context.
  4. All network access goes through the backend's SSRF-safe executor.
"""

import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from mcp_server.schema import env_prefix, input_schema, is_write, mcp_tool_name
from tool_executor.executor import ToolExecutionError, ToolExecutor
from tool_generator.schemas import GeneratedConnector, ToolDefinition

MAX_CHARS = 8000  # about 2,000 tokens; enough for most answers
MIN_SECRET_LEN = 6  # shorter values are not scrubbed: they would mangle normal text
SECRET_SUFFIXES = ("KEY", "TOKEN", "SECRET", "PASSWORD", "SID", "AUTH", "CREDENTIALS", "USERNAME")


class ToolForgeMCP:
    """Framework-free core: list tools and call them. The MCP wiring below is a thin layer on top."""

    def __init__(self, connectors: List[GeneratedConnector], executor: Optional[Any] = None,
                 safe_mode: bool = True, env: Optional[Dict[str, str]] = None):
        self.executor = executor or ToolExecutor()
        self.safe_mode = safe_mode
        self.env = env if env is not None else os.environ
        # name the agent sees -> (api_name, tool)
        self.tools: Dict[str, Tuple[str, ToolDefinition]] = {}
        for connector in connectors:
            for tool in connector.tools:
                self.tools[mcp_tool_name(connector.api_name, tool)] = (connector.api_name, tool)

    # ------------------------------------------------------------------ listing

    def list_tools(self) -> List[Dict[str, Any]]:
        listed = []
        for name, (api_name, tool) in self.tools.items():
            write = is_write(tool)
            note = " Changes data: asks for confirm=true first." if (write and self.safe_mode) else ""
            listed.append({
                "name": name,
                "description": (tool.description or f"{tool.method} {tool.path}") + note,
                "inputSchema": input_schema(tool),
                "readOnly": not write,
            })
        return listed

    # ------------------------------------------------------------------ calling

    async def call(self, name: str, arguments: Optional[Dict[str, Any]]) -> Tuple[str, bool]:
        """Run one tool. Returns (text for the model, is_error)."""
        if name not in self.tools:
            return f"Unknown tool '{name}'. Ask the user to run: python -m mcp_server list", True
        api_name, tool = self.tools[name]
        args = dict(arguments or {})
        confirmed = args.pop("confirm", False) is True
        prefix = env_prefix(api_name)

        if self.safe_mode and is_write(tool) and not confirmed:
            return self._preview(tool, args), False
        try:
            result = await self.executor.execute(tool, args, env_prefix=prefix)
        except ToolExecutionError as exc:
            return self._scrub(f"Error: {exc.message}", prefix), True
        body = result.response if result.response is not None else ""
        text = json.dumps(body, indent=2, default=str) if not isinstance(body, str) else body
        if not result.success:
            text = f"HTTP {result.status_code}. {result.error or ''}\n{text}"
        return self._trim(self._scrub(text, prefix)), (not result.success)

    # ------------------------------------------------------------------ helpers

    @staticmethod
    def _preview(tool: ToolDefinition, args: Dict[str, Any]) -> str:
        shown = json.dumps(args, indent=2, default=str)
        return (f"SAFE MODE: nothing was sent.\nThis would call {tool.method} {tool.path} with:\n{shown}\n"
                "If the user agrees, call the same tool again with confirm=true.")

    def _secrets(self, prefix: str) -> List[str]:
        """Values of credential-looking env vars for this API (and the global names the backend still reads)."""
        found = []
        for key, value in self.env.items():
            if not value or len(value) < MIN_SECRET_LEN:
                continue
            upper = key.upper()
            if upper.startswith(prefix + "_") or upper in ("API_KEY", "X_API_KEY", "AUTH_BEARER_TOKEN",
                                                           "API_BEARER_TOKEN", "BEARER_TOKEN"):
                if upper.endswith(SECRET_SUFFIXES) or upper.startswith(prefix + "_"):
                    found.append(value.strip())
        return sorted(set(found), key=len, reverse=True)

    def _scrub(self, text: str, prefix: str) -> str:
        for secret in self._secrets(prefix):
            text = text.replace(secret, "***")
        return text

    @staticmethod
    def _trim(text: str, limit: int = MAX_CHARS) -> str:
        if len(text) <= limit:
            return text
        return text[:limit] + f"\n... [trimmed {len(text) - limit} characters]"


# ---------------------------------------------------------------------- MCP wiring


def build_server(core: ToolForgeMCP, name: str = "toolforge"):
    """Attach the core to the official MCP SDK (lowlevel Server, SDK 2.x)."""
    from mcp import types
    from mcp.server.lowlevel import Server

    async def on_list_tools(ctx, params):
        tools = [
            types.Tool(
                name=item["name"], description=item["description"], inputSchema=item["inputSchema"],
                annotations=types.ToolAnnotations(readOnlyHint=item["readOnly"], openWorldHint=True),
            )
            for item in core.list_tools()
        ]
        return types.ListToolsResult(tools=tools)

    async def on_call_tool(ctx, params):
        text, failed = await core.call(params.name, params.arguments)
        return types.CallToolResult(content=[types.TextContent(type="text", text=text)], isError=failed)

    return Server(
        name, version="0.4.0",
        instructions=("ToolForge exposes API endpoints as tools. Tools that change data only preview "
                      "until you pass confirm=true; ask the user before confirming."),
        on_list_tools=on_list_tools, on_call_tool=on_call_tool,
    )


async def serve_stdio(core: ToolForgeMCP) -> None:
    from mcp.server.stdio import stdio_server

    server = build_server(core)
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())

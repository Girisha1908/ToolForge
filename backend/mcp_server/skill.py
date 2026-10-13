"""Write a SKILL.md for coding agents, and the credential checklist.

The skill's first job is the `description` line: it tells the agent WHEN to reach for this API,
so it can pick it up without being told. The body lists what the tools do and how credentials work.
"""

import os
from typing import Dict, List, Optional

from mcp_server.schema import api_slug, env_prefix, is_write, mcp_tool_name
from tool_generator.schemas import GeneratedConnector


def needed_credentials(connector: GeneratedConnector) -> List[Dict[str, object]]:
    """Env vars this API needs, by auth type. Returns names only, never values."""
    prefix = env_prefix(connector.api_name)
    kinds = {(t.authentication.type or "none").lower() for t in connector.tools}
    needs: List[Dict[str, object]] = []
    if "api_key" in kinds:
        needs.append({"kind": "api_key", "any_of": [f"{prefix}_API_KEY"]})
    if "bearer" in kinds:
        needs.append({"kind": "bearer", "any_of": [f"{prefix}_BEARER_TOKEN"]})
    if "basic" in kinds:
        needs.append({"kind": "basic", "any_of": [f"{prefix}_USERNAME", f"{prefix}_ACCOUNT_SID"],
                      "also": [f"{prefix}_PASSWORD", f"{prefix}_AUTH_TOKEN"]})
    if "oauth2" in kinds:
        needs.append({"kind": "oauth2", "unsupported": True, "any_of": []})
    return needs


def doctor(connector: GeneratedConnector, env: Optional[Dict[str, str]] = None) -> List[str]:
    """Human-readable checklist. Says which variables are set or missing; never prints a value."""
    env = env if env is not None else os.environ
    lines = []
    needs = needed_credentials(connector)
    if not needs:
        return ["No credentials needed for this API."]
    for need in needs:
        if need.get("unsupported"):
            lines.append("MISSING  OAuth2: not supported yet, so tools with OAuth2 cannot run.")
            continue
        names = list(need["any_of"]) + list(need.get("also", []))
        is_set = lambda n: bool((env.get(n) or "").strip())  # noqa: E731 - tiny local helper
        if need["kind"] == "basic":
            user_ok = any(is_set(n) for n in need["any_of"])
            pass_ok = any(is_set(n) for n in need["also"])
            ok = user_ok and pass_ok
        else:
            ok = any(is_set(n) for n in names)
        status = "OK      " if ok else "MISSING "
        lines.append(f"{status} {need['kind']}: set {' and '.join(names) if need['kind'] == 'basic' else names[0]}")
    return lines


def render_skill(connector: GeneratedConnector, max_tools: int = 40) -> str:
    slug = api_slug(connector.api_name)
    tools = connector.tools
    reads = [t for t in tools if not is_write(t)]
    writes = [t for t in tools if is_write(t)]
    # "Use when" line: name the API and a few real actions, so the agent knows when this applies.
    actions = ", ".join((t.name.replace("_", " ")) for t in tools[:4]) or "call its endpoints"
    description = (f"Use when the user wants to work with the {connector.api_name} API (for example: {actions}). "
                   f"Calls go through the ToolForge MCP tools named {slug}__*.")
    out = ["---", f"name: {slug}", f"description: {description}", "---", "",
           f"# {connector.api_name}", ""]
    if connector.description:
        out += [connector.description.strip(), ""]
    out += ["## How to use", "",
            f"1. Use the MCP tools whose names start with `{slug}__`. Do not write raw HTTP calls for this API.",
            "2. Read-only tools are safe to call. Tools that change data only show a preview first; "
            "show the preview to the user and call again with `confirm: true` only after they agree.",
            "3. Never ask the user to paste a key into the chat. Credentials live in environment variables.", ""]
    out += ["## Credentials", ""]
    for line in doctor(connector, env={}):
        out.append(f"- {line.replace('MISSING  ', '').replace('OK       ', '')}")
    out += ["", "Run `python -m mcp_server doctor " + slug + "` to check which are set.", ""]
    out += [f"## Read-only tools ({len(reads)})", ""]
    for t in reads[:max_tools]:
        out.append(f"- `{mcp_tool_name(connector.api_name, t)}`: {(t.description or t.path).strip()}")
    if writes:
        out += ["", f"## Tools that change data ({len(writes)}), preview first", ""]
        for t in writes[:max_tools]:
            out.append(f"- `{mcp_tool_name(connector.api_name, t)}` ({t.method}): {(t.description or t.path).strip()}")
    return "\n".join(out) + "\n"

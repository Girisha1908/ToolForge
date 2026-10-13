"""ToolForge MCP server: lets a coding agent (VS Code, Claude Code, Antigravity) use generated tools.

Reuses the backend's parser, generator and SSRF-safe executor. Adds: saving connectors to disk
(so a separate MCP process can load them), per-API credentials, safe mode for writes, trimmed and
scrubbed output, and a SKILL.md writer.
"""

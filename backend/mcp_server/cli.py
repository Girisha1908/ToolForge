"""Command line: python -m mcp_server <command>

  import <docs-url-or-file> [--name N]   read docs, generate tools, save them
  list                                   saved APIs and tool counts
  serve [--api N ...] [--unsafe]         run the MCP server over stdio (what VS Code launches)
  skill <api> [--out SKILL.md]           write a SKILL.md for coding agents
  config <api>                           print the VS Code / Claude Code setup
  doctor <api>                           check which credential variables are set (never prints values)
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import List, Optional

from mcp_server.schema import api_slug
from mcp_server.server import ToolForgeMCP, serve_stdio
from mcp_server.skill import doctor, render_skill
from mcp_server.store import ConnectorStore


def _load_text(source: str) -> str:
    """A path to a local file is read; anything else (URL or raw text) goes to the parser unchanged."""
    path = Path(source)
    if len(source) < 400 and "\n" not in source and path.exists() and path.is_file():
        return path.read_text(encoding="utf-8")
    return source


def cmd_import(args, store: ConnectorStore) -> int:
    from api_parser.parser import APIParser
    from tool_generator.generator import ConnectorGenerator

    async def run():
        spec = await APIParser().parse_doc(_load_text(args.source))
        if args.name:
            spec.api_name = args.name
        if args.base_url:
            spec.base_url = args.base_url
        return await ConnectorGenerator().generate_async(spec)

    connector = asyncio.run(run())
    if not connector.tools:
        print("No tools could be generated. Give an OpenAPI/Swagger/Postman file or a docs page.", file=sys.stderr)
        return 1
    path = store.save(connector)
    print(f"Saved '{connector.api_name}': {len(connector.tools)} tools -> {path}")
    for line in doctor(connector):
        print("  " + line)
    if not connector.base_url:
        print("Warning: no server address found. Re-import with --base-url.", file=sys.stderr)
    return 0


def cmd_list(args, store: ConnectorStore) -> int:
    names = store.list_names()
    if not names:
        print("Nothing saved yet. Run: python -m mcp_server import <docs-url>")
    for name in names:
        c = store.load(name)
        print(f"{name}: {len(c.tools)} tools")
    return 0


def cmd_serve(args, store: ConnectorStore) -> int:
    names = args.api or store.list_names()
    if not names:
        print("Nothing to serve. Run: python -m mcp_server import <docs-url>", file=sys.stderr)
        return 1
    core = ToolForgeMCP([store.load(n) for n in names], safe_mode=not args.unsafe)
    print(f"ToolForge MCP: {len(core.tools)} tools from {', '.join(names)}", file=sys.stderr)  # stderr: stdout is the protocol
    asyncio.run(serve_stdio(core))
    return 0


def cmd_skill(args, store: ConnectorStore) -> int:
    text = render_skill(store.load(args.api))
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"Wrote {args.out}")
    else:
        print(text)
    return 0


def cmd_config(args, store: ConnectorStore) -> int:
    store.load(args.api)  # fail early if unknown
    slug = api_slug(args.api)
    entry = {"type": "stdio", "command": sys.executable, "args": ["-m", "mcp_server", "serve", "--api", slug],
             "cwd": str(Path(__file__).resolve().parent.parent)}
    print("VS Code (.vscode/mcp.json):")
    print(json.dumps({"servers": {f"toolforge-{slug}": entry}}, indent=2))
    print("\nClaude Code:")
    print(f"claude mcp add toolforge-{slug} --cwd {entry['cwd']} -- {sys.executable} -m mcp_server serve --api {slug}")
    return 0


def cmd_doctor(args, store: ConnectorStore) -> int:
    lines = doctor(store.load(args.api))
    print("\n".join(lines))
    return 1 if any(line.startswith("MISSING") for line in lines) else 0


def main(argv: Optional[List[str]] = None, store: Optional[ConnectorStore] = None) -> int:
    parser = argparse.ArgumentParser(prog="mcp_server", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("import"); p.add_argument("source"); p.add_argument("--name"); p.add_argument("--base-url")
    p.set_defaults(func=cmd_import)
    p = sub.add_parser("list"); p.set_defaults(func=cmd_list)
    p = sub.add_parser("serve"); p.add_argument("--api", action="append")
    p.add_argument("--unsafe", action="store_true", help="skip the confirm step for tools that change data")
    p.set_defaults(func=cmd_serve)
    p = sub.add_parser("skill"); p.add_argument("api"); p.add_argument("--out"); p.set_defaults(func=cmd_skill)
    p = sub.add_parser("config"); p.add_argument("api"); p.set_defaults(func=cmd_config)
    p = sub.add_parser("doctor"); p.add_argument("api"); p.set_defaults(func=cmd_doctor)
    args = parser.parse_args(argv)
    try:
        return args.func(args, store or ConnectorStore())
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except BrokenPipeError:
        return 0


if __name__ == "__main__":
    sys.exit(main())

"""Save generated connectors to disk so the MCP server (a separate process) can load them.

The web backend keeps tools in memory only. The MCP server runs on its own when VS Code starts it,
so it needs a file. One JSON file per API under TOOLFORGE_HOME (default ~/.toolforge/connectors).
No credentials are ever written here.
"""

import json
import os
from pathlib import Path
from typing import List, Optional

from mcp_server.schema import api_slug
from tool_generator.schemas import GeneratedConnector


def default_home() -> Path:
    return Path(os.environ.get("TOOLFORGE_HOME") or Path.home() / ".toolforge")


class ConnectorStore:
    def __init__(self, home: Optional[Path] = None):
        self.dir = Path(home or default_home()) / "connectors"

    def path_for(self, api_name: str) -> Path:
        return self.dir / f"{api_slug(api_name)}.json"

    def save(self, connector: GeneratedConnector) -> Path:
        self.dir.mkdir(parents=True, exist_ok=True)
        path = self.path_for(connector.api_name)
        # Write to a temp file first so a crash cannot leave a half-written connector behind.
        tmp = path.with_suffix(".tmp")
        tmp.write_text(connector.model_dump_json(indent=2), encoding="utf-8")
        tmp.replace(path)
        return path

    def load(self, api_name: str) -> GeneratedConnector:
        path = self.path_for(api_name)
        if not path.exists():
            raise FileNotFoundError(f"No saved API called '{api_name}'. Run: python -m mcp_server import <docs-url>")
        return GeneratedConnector.model_validate(json.loads(path.read_text(encoding="utf-8")))

    def list_names(self) -> List[str]:
        if not self.dir.exists():
            return []
        return sorted(p.stem for p in self.dir.glob("*.json"))

    def delete(self, api_name: str) -> bool:
        path = self.path_for(api_name)
        if path.exists():
            path.unlink()
            return True
        return False

from typing import Dict, List, Optional
from tool_generator.schemas import ToolDefinition


class ToolRegistry:
    """In-memory registry for storing and managing generated tools."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ToolRegistry, cls).__new__(cls)
            cls._instance._tools: Dict[str, ToolDefinition] = {}
        return cls._instance

    def register_tool(self, tool: ToolDefinition) -> None:
        """Registers or updates a tool in the in-memory registry."""
        self._tools[tool.id] = tool
        self._tools[tool.name] = tool

    def register_tools(self, tools: List[ToolDefinition]) -> None:
        """Registers multiple tools."""
        for tool in tools:
            self.register_tool(tool)

    def get_tool(self, tool_id_or_name: str) -> Optional[ToolDefinition]:
        """Retrieves a tool by ID or unique name."""
        return self._tools.get(tool_id_or_name)

    def list_tools(self) -> List[ToolDefinition]:
        """Lists all unique registered tools."""
        unique_tools = {}
        for tool in self._tools.values():
            unique_tools[tool.id] = tool
        return list(unique_tools.values())

    def clear(self) -> None:
        """Clears all tools in the registry (useful for testing)."""
        self._tools.clear()


# Global default registry instance
default_registry = ToolRegistry()

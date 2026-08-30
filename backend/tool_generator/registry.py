from typing import Dict, List, Optional
from tool_generator.schemas import ToolDefinition


class ToolRegistry:
    """In-memory registry for storing and managing generated tools."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ToolRegistry, cls).__new__(cls)
            cls._instance._tools_by_id: Dict[str, ToolDefinition] = {}
            cls._instance._name_to_id: Dict[str, str] = {}
        return cls._instance

    def register_tool(self, tool: ToolDefinition) -> None:
        """Registers or updates a tool in the in-memory registry using canonical tool.id."""
        self._tools_by_id[tool.id] = tool
        self._name_to_id[tool.name] = tool.id

    def register_tools(self, tools: List[ToolDefinition]) -> None:
        """Registers multiple tools."""
        for tool in tools:
            self.register_tool(tool)

    def get_tool(self, tool_id_or_name: str) -> Optional[ToolDefinition]:
        """Retrieves a tool by ID or unique name."""
        if tool_id_or_name in self._tools_by_id:
            return self._tools_by_id[tool_id_or_name]
        
        target_id = self._name_to_id.get(tool_id_or_name)
        if target_id:
            return self._tools_by_id.get(target_id)

        return None

    def list_tools(self) -> List[ToolDefinition]:
        """Lists all unique registered tools."""
        return list(self._tools_by_id.values())

    def clear(self) -> None:
        """Clears all tools in the registry (useful for testing)."""
        self._tools_by_id.clear()
        self._name_to_id.clear()


# Global default registry instance
default_registry = ToolRegistry()

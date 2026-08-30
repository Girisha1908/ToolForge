from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class ToolDefinition(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any]
    method: str
    path: str

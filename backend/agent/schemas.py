from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from tool_generator.schemas import ToolDefinition, ToolExecutionResult


class ToolCallStep(BaseModel):
    tool_name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)
    execution_result: Optional[ToolExecutionResult] = None
    error: Optional[str] = None


class AgentResponse(BaseModel):
    success: bool
    final_answer: str
    tools_called: List[str] = Field(default_factory=list)
    steps: List[ToolCallStep] = Field(default_factory=list)
    total_iterations: int = 0
    total_latency_ms: float = 0.0
    error: Optional[str] = None


class AgentRunRequest(BaseModel):
    message: str = Field(description="User prompt or message for the agent")
    tools: Optional[List[ToolDefinition]] = Field(default=None, description="Optional list of tools; if omitted, active registered tools in ToolRegistry will be used")
    max_iterations: int = Field(default=5, description="Maximum allowed tool-execution loop iterations")

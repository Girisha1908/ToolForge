from fastapi import APIRouter, HTTPException, Body, Path
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

from api_parser.parser import APIParser
from api_parser.schemas import NormalizedAPISpec
from tool_generator.generator import ConnectorGenerator
from tool_generator.registry import default_registry
from tool_generator.schemas import (
    GeneratedConnector,
    ToolDefinition,
    ToolExecutionRequest,
    ToolExecutionResult
)
from tool_executor.executor import ToolExecutor, ToolExecutionError
from agent.runtime import AgentRuntime
from agent.schemas import AgentResponse, AgentRunRequest

router = APIRouter()

parser_instance = APIParser()
generator_instance = ConnectorGenerator()
executor_instance = ToolExecutor()
agent_runtime_instance = AgentRuntime()

ERROR_SPEC_TITLES = {"Inaccessible Documentation", "Invalid Documentation Source", "Malformed Documentation"}


class ParseDocRequest(BaseModel):
    url: str = Field(description="URL or raw text/JSON/YAML of the API documentation")


class GenerateToolsRequest(BaseModel):
    spec: Optional[NormalizedAPISpec] = Field(default=None, description="NormalizedAPISpec directly")
    url: Optional[str] = Field(default=None, description="Documentation URL or raw spec string to parse and generate")


@router.get("/status")
def status():
    return {"status": "ok"}


@router.post("/parse-doc", response_model=NormalizedAPISpec)
async def parse_documentation(request: ParseDocRequest):
    """
    Ingests and parses API documentation from a URL or raw content string.
    Returns a normalized structured API specification.
    """
    if not request.url or not request.url.strip():
        raise HTTPException(status_code=400, detail="Documentation URL or content cannot be empty.")

    try:
        spec = await parser_instance.parse_doc(request.url)
        if spec.api_name in ERROR_SPEC_TITLES:
            raise HTTPException(status_code=400, detail=spec.description or "Failed to fetch or parse documentation.")
        return spec
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to process documentation: {str(exc)}")


@router.post("/generate-tools", response_model=GeneratedConnector)
async def generate_tools(request: GenerateToolsRequest):
    """
    Generates agent-ready tool definitions from a NormalizedAPISpec (or URL) and registers them in the ToolRegistry.
    """
    spec = request.spec
    if not spec:
        if not request.url or not request.url.strip():
            raise HTTPException(status_code=400, detail="Must provide either 'spec' object or 'url' string.")
        spec = await parser_instance.parse_doc(request.url)

    if spec.api_name in ERROR_SPEC_TITLES:
        raise HTTPException(status_code=400, detail=spec.description or "Failed to fetch or parse documentation.")

    try:
        connector = await generator_instance.generate_async(spec)
        if not connector.tools:
            raise HTTPException(
                status_code=400,
                detail="No tools could be generated from the provided URL. Please enter an API documentation URL (OpenAPI, Swagger, Postman, or HTML documentation) rather than a direct API endpoint."
            )
        default_registry.clear()
        default_registry.register_tools(connector.tools)
        return connector
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to generate tools from API specification: {str(exc)}")


@router.get("/tools", response_model=List[ToolDefinition])
def list_tools():
    """
    Lists all registered agent tools currently stored in the in-memory tool registry.
    """
    return default_registry.list_tools()


@router.get("/tools/{tool_id}", response_model=ToolDefinition)
def get_tool(tool_id: str = Path(description="Tool ID or unique name")):
    """
    Retrieves a single tool definition from the registry.
    """
    tool = default_registry.get_tool(tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_id}' not found in registry.")
    return tool


@router.post("/tools/{tool_id}/execute", response_model=ToolExecutionResult)
async def execute_tool(
    tool_id: str = Path(description="Tool ID or unique name"),
    request: ToolExecutionRequest = Body(...)
):
    """
    Executes a registered tool using the generic HTTP executor against external APIs.
    """
    tool = default_registry.get_tool(tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Unknown tool '{tool_id}'. Please generate or register the tool first.")

    try:
        result = await executor_instance.execute(tool, request.arguments)
        return result
    except ToolExecutionError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Tool execution failed: {str(exc)}")


@router.post("/agent/run", response_model=AgentResponse)
async def run_agent(request: AgentRunRequest):
    """
    Runs the agent runtime with a user prompt and tool definitions.
    Dynamically executes requested tools and returns a structured AgentResponse.
    """
    if not request.message or not request.message.strip():
        raise HTTPException(status_code=400, detail="User message cannot be empty.")

    try:
        response = await agent_runtime_instance.run_async(
            user_message=request.message,
            tools=request.tools,
            max_iterations=request.max_iterations
        )
        return response
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Agent execution error: {str(exc)}")

import os
import json
import logging
import asyncio
import re
from typing import Dict, Any, List, Optional
from google import genai
from dotenv import load_dotenv

# Load env variables
load_dotenv()

logger = logging.getLogger("ToolForge.AgentEngine")


class AgentEngine:
    """
    Gemini Agent Layer built on top of ToolForge's existing Tool Registry and Generic HTTP Executor.
    Processes user natural language requests, selects matching registered tools, invokes the executor,
    and returns concise responses along with observable execution traces.
    """

    def __init__(self):
        self.api_key = os.environ.get("GEMINI_API_KEY")

    def is_available(self) -> bool:
        return bool(self.api_key and self.api_key != "your_gemini_api_key_here")

    async def run(self, user_prompt: str, tools: List[Any]) -> Dict[str, Any]:
        """
        Executes the Gemini agent flow:
        1. User message received & trace initialized
        2. Gemini Flash selects tool + arguments from provided registered tool definitions
        3. Arguments validated & ToolExecutor executes real API request
        4. Response received & Gemini synthesizes natural language answer
        """
        trace = ["request_received"]

        # Check API key presence
        if not self.is_available():
            return {
                "success": False,
                "message": "GEMINI_API_KEY is not set or unconfigured in the environment.",
                "tool": None,
                "arguments": {},
                "status_code": 500,
                "latency_ms": 0,
                "trace": trace,
                "action": "Agent Error",
                "args": {},
                "status": "API Key Missing",
                "resultText": "GEMINI_API_KEY is missing. Please add your Gemini API key to .env file.",
                "error": {
                    "code": "MISSING_GEMINI_API_KEY",
                    "message": "GEMINI_API_KEY environment variable is not configured."
                }
            }

        # Check if tools exist in registry
        if not tools:
            return {
                "success": False,
                "message": "No registered tools available for the agent to execute.",
                "tool": None,
                "arguments": {},
                "status_code": 400,
                "latency_ms": 0,
                "trace": trace,
                "action": "No Tools Registered",
                "args": {},
                "status": "No Tools Available",
                "resultText": "No registered tools found. Please analyze an API documentation URL first to generate tools.",
                "error": {
                    "code": "NO_REGISTERED_TOOLS",
                    "message": "Tool registry is empty."
                }
            }

        # Compact tool summaries for minimal Gemini token usage
        tools_summary = []
        for t in tools:
            tools_summary.append({
                "id": t.id,
                "name": t.name,
                "description": t.description,
                "parameters": [
                    {
                        "name": p.name,
                        "type": p.type,
                        "required": p.required,
                        "description": p.description
                    } for p in getattr(t, 'parameters', [])
                ]
            })

        system_instruction = """
You are an expert AI agent router. Given a user request and a list of available tools, select the single best tool to invoke and extract its required arguments.
You must output a JSON object in this exact format:
{
  "selected_tool": "tool_id_or_name",
  "arguments": {
    "param_name": "param_value"
  }
}

If no tool matches the request, return:
{
  "selected_tool": null,
  "arguments": {}
}

Return ONLY valid JSON.
"""

        prompt = f"""
Available Tools:
{json.dumps(tools_summary, indent=2)}

User Request: "{user_prompt}"
"""

        try:
            # Step 1: Gemini Tool Selection
            def _call_gemini_select():
                client = genai.Client(api_key=self.api_key)
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt,
                    config={"system_instruction": system_instruction}
                )
                return response.text.strip()

            response_text = await asyncio.to_thread(_call_gemini_select)

            if response_text.startswith("```"):
                response_text = re.sub(r'^```[a-z]*\n', '', response_text)
                response_text = re.sub(r'\n```$', '', response_text)

            decision = json.loads(response_text.strip())
            selected_tool_id = decision.get("selected_tool")
            args = decision.get("arguments", {})

            if not selected_tool_id:
                return {
                    "success": False,
                    "message": "I couldn't find a matching tool in the registered API tools to answer your request.",
                    "tool": None,
                    "arguments": {},
                    "status_code": 404,
                    "latency_ms": 0,
                    "trace": trace,
                    "action": "No Tool Selected",
                    "args": {},
                    "status": "No Match",
                    "resultText": "No matching tool found for your request.",
                    "error": {
                        "code": "NO_MATCHING_TOOL",
                        "message": "Agent could not match query to any registered tool."
                    }
                }

            # Locate tool definition in registry
            tool_def = next((t for t in tools if t.id == selected_tool_id or t.name == selected_tool_id), None)
            if not tool_def:
                return {
                    "success": False,
                    "message": f"Tool '{selected_tool_id}' was selected but is not found in the registry.",
                    "tool": selected_tool_id,
                    "arguments": args,
                    "status_code": 404,
                    "latency_ms": 0,
                    "trace": trace,
                    "action": f"Using {selected_tool_id}",
                    "args": args,
                    "status": "Tool Not Found",
                    "resultText": f"Selected tool '{selected_tool_id}' is not registered.",
                    "error": {
                        "code": "TOOL_NOT_FOUND",
                        "message": f"Tool '{selected_tool_id}' missing from registry."
                    }
                }

            trace.append(f"tool_selected: {tool_def.name}")

            # Step 2: Validate Arguments & Execute via existing ToolExecutor
            from tool_executor.executor import ToolExecutor, ToolExecutionError
            executor = ToolExecutor()

            trace.append("arguments_validated")
            trace.append("api_request_sent")

            execution_result = await executor.execute(tool_def, args)
            trace.append("response_received")

            # Step 3: Natural language response synthesis via Gemini
            summary_prompt = f"""
You are the ToolForge AI Agent. You executed the API tool '{tool_def.name}' for user query: "{user_prompt}".

Arguments Used: {json.dumps(args)}
HTTP Status Code: {execution_result.status_code}
API Response: {json.dumps(execution_result.response, indent=2)}

Synthesize a clear, direct, natural language answer for the user summarizing the result.
"""

            def _call_gemini_summary():
                client = genai.Client(api_key=self.api_key)
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=summary_prompt
                )
                return response.text.strip()

            summary_text = await asyncio.to_thread(_call_gemini_summary)
            trace.append("result_returned")

            return {
                "success": execution_result.success,
                "message": summary_text,
                "tool": tool_def.name,
                "arguments": args,
                "status_code": execution_result.status_code,
                "latency_ms": execution_result.latency_ms,
                "trace": trace,
                "action": f"Using {tool_def.name}",
                "args": args,
                "status": "API request successful" if execution_result.success else f"HTTP {execution_result.status_code}",
                "resultText": summary_text
            }

        except ToolExecutionError as exc:
            trace.append("execution_failed")
            return {
                "success": False,
                "message": exc.message,
                "tool": selected_tool_id if 'selected_tool_id' in locals() else None,
                "arguments": args if 'args' in locals() else {},
                "status_code": exc.status_code,
                "latency_ms": 0,
                "trace": trace,
                "action": "Execution Error",
                "args": args if 'args' in locals() else {},
                "status": f"HTTP {exc.status_code}",
                "resultText": exc.message,
                "error": {
                    "code": "TOOL_EXECUTION_FAILED",
                    "message": exc.message
                }
            }
        except Exception as exc:
            logger.error(f"Agent Engine error: {exc}")
            trace.append("error_occurred")
            return {
                "success": False,
                "message": f"Agent error: {str(exc)}",
                "tool": None,
                "arguments": {},
                "status_code": 500,
                "latency_ms": 0,
                "trace": trace,
                "action": "Agent Error",
                "args": {},
                "status": "Error",
                "resultText": f"An error occurred during agent processing: {str(exc)}",
                "error": {
                    "code": "AGENT_INTERNAL_ERROR",
                    "message": str(exc)
                }
            }

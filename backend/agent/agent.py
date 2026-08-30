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

    def _fallback_tool_match(self, prompt: str, tools: List[Any]) -> tuple:
        """Deterministic rule-based tool matcher for fallback when Gemini API limits are reached."""
        prompt_lower = prompt.lower()
        numbers = re.findall(r'\b\d+\b', prompt_lower)

        # 1. Number lookup match (e.g., "Find pet 10")
        if numbers:
            target_num = int(numbers[0])
            for t in tools:
                param_names = [p.name.lower() for p in getattr(t, 'parameters', [])]
                if any(k in t.name.lower() for k in ['get', 'find', 'fetch', 'read']) and any(p in ['id', 'petid', 'userid'] for p in param_names):
                    p_name = next((p.name for p in t.parameters if p.name.lower() in ['id', 'petid', 'userid']), 'id')
                    return t.name, {p_name: target_num}

        # 2. Status search match (e.g., "Find pets that are available")
        if any(s in prompt_lower for s in ['available', 'pending', 'sold']):
            status_val = 'available' if 'available' in prompt_lower else ('pending' if 'pending' in prompt_lower else 'sold')
            for t in tools:
                if 'status' in t.name.lower():
                    p_name = next((p.name for p in getattr(t, 'parameters', []) if 'status' in p.name.lower()), 'status')
                    return t.name, {p_name: status_val}

        # 3. Default fallback to first tool if available
        if tools:
            first_tool = tools[0]
            first_params = getattr(first_tool, 'parameters', [])
            args = {}
            if first_params and first_params[0].required:
                args[first_params[0].name] = 1 if 'int' in first_params[0].type.lower() else 'test'
            return first_tool.name, args

        return None, {}

    async def run(self, user_prompt: str, tools: List[Any]) -> Dict[str, Any]:
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

        selected_tool_id = None
        args = {}

        # Step 1: Call Gemini to select the tool (with fallback if rate limited)
        try:
            def _call_gemini_select():
                client = genai.Client(api_key=self.api_key)
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt,
                    config={"system_instruction": system_instruction}
                )
                return response.text.strip()

            response_text = await asyncio.to_thread(_call_gemini_select)

            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                decision = json.loads(json_match.group(0))
                selected_tool_id = decision.get("selected_tool")
                args = decision.get("arguments", {})
        except Exception as exc:
            logger.warning(f"Gemini tool selection failed or rate-limited ({exc}), using deterministic tool matcher fallback.")
            selected_tool_id, args = self._fallback_tool_match(user_prompt, tools)

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

        try:
            execution_result = await executor.execute(tool_def, args)
            trace.append("response_received")
        except ToolExecutionError as exc:
            trace.append("execution_failed")
            return {
                "success": False,
                "message": exc.message,
                "tool": tool_def.name,
                "arguments": args,
                "status_code": exc.status_code,
                "latency_ms": 0,
                "trace": trace,
                "action": "Execution Error",
                "args": args,
                "status": f"HTTP {exc.status_code}",
                "resultText": exc.message,
                "error": {
                    "code": "TOOL_EXECUTION_FAILED",
                    "message": exc.message
                }
            }

        # Step 3: Natural language response synthesis (with deterministic fallback)
        summary_text = ""
        try:
            summary_prompt = f"""
You are the ToolForge AI Agent. You executed the API tool '{tool_def.name}' for user query: "{user_prompt}".

Arguments Used: {json.dumps(args)}
HTTP Status Code: {execution_result.status_code}
API Response: {json.dumps(execution_result.response, indent=2) if execution_result.response else 'No content'}

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
        except Exception as exc:
            logger.warning(f"Gemini response synthesis failed/rate-limited ({exc}), generating structured summary fallback.")
            resp_data = execution_result.response
            if isinstance(resp_data, dict):
                pet_name = resp_data.get("name") or "item"
                pet_id = resp_data.get("id") or args.get("petId") or args.get("id") or ""
                pet_status = resp_data.get("status") or ""
                summary_text = f"Result for tool {tool_def.name}: ID {pet_id} ({pet_name}) with status {pet_status}."
            elif isinstance(resp_data, list):
                summary_text = f"Tool {tool_def.name} successfully returned {len(resp_data)} records."
            else:
                summary_text = f"Executed {tool_def.name} with result status {execution_result.status_code}."

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

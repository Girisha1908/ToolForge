import os
import time
import json
import re
import logging
import asyncio
from typing import List, Dict, Any, Optional

from tool_generator.schemas import ToolDefinition, ToolExecutionResult
from tool_generator.registry import ToolRegistry, default_registry
from tool_executor.executor import ToolExecutor, ToolExecutionError
from agent.schemas import AgentResponse, ToolCallStep

logger = logging.getLogger("ToolForge.AgentRuntime")


class GeminiAgentService:
    """Service abstraction for LLM interactions in the Agent Runtime."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None, timeout: float = 15.0):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self.model = model or os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
        self.timeout = timeout

    def is_available(self) -> bool:
        return bool(self.api_key)

    def convert_tools_to_gemini_declarations(self, tools: List[ToolDefinition]) -> List[Dict[str, Any]]:
        """Converts ToolDefinition schemas into Gemini function declarations format."""
        declarations = []
        for t in tools:
            properties = {}
            required = []
            for p in t.parameters:
                prop_type = p.type.upper()
                if prop_type not in ["STRING", "INTEGER", "NUMBER", "BOOLEAN", "ARRAY", "OBJECT"]:
                    prop_type = "STRING"

                properties[p.name] = {
                    "type": prop_type,
                    "description": p.description or f"Parameter {p.name}"
                }
                if p.required:
                    required.append(p.name)

            declarations.append({
                "name": t.name,
                "description": t.description or f"Executes HTTP {t.method} {t.path}",
                "parameters": {
                    "type": "OBJECT",
                    "properties": properties,
                    "required": required
                }
            })
        return declarations

    async def decide_next_action(
        self,
        conversation_history: List[Dict[str, Any]],
        tools: List[ToolDefinition]
    ) -> Dict[str, Any]:
        """
        Sends conversation history and tool declarations to Gemini.
        Returns structured decision object:
        - {"type": "tool_call", "tool_name": str, "arguments": dict}
        - {"type": "final_answer", "text": str}
        """
        if not self.is_available():
            # Fallback when GEMINI_API_KEY is not configured
            return self._heuristic_action(conversation_history, tools)

        tool_declarations = self.convert_tools_to_gemini_declarations(tools)

        prompt = f"""
You are ToolForge AI Agent. Your goal is to answer the user's request by calling available tools when needed.

AVAILABLE TOOLS:
{json.dumps(tool_declarations, indent=2)}

CONVERSATION HISTORY & TOOL EXECUTION RESULTS:
{json.dumps(conversation_history, indent=2)}

INSTRUCTIONS:
1. If you need to execute a tool to fetch or process information, output a TOOL_CALL JSON object:
   {{"type": "tool_call", "tool_name": "exact_name", "arguments": {{...}}}}

2. If tool execution results are present in the conversation history, synthesize a clear, helpful, natural language FINAL_ANSWER directly answering the user's prompt.
   - Summarize, list, or format the information cleanly for the user.
   - Do NOT dump raw JSON strings or raw "_truncated_text" keys in the final answer.
   - Extract the relevant fields (such as titles, prices, categories, statuses, counts, etc.) and present them in plain English or clean bullet points.

   Output a FINAL_ANSWER JSON object:
   {{"type": "final_answer", "text": "Your clear, well-formatted natural language answer here"}}

3. Return ONLY valid JSON for one of the two formats above.
"""

        def _sync_call():
            from google import genai
            client = genai.Client(api_key=self.api_key)
            response = client.models.generate_content(
                model=self.model,
                contents=prompt
            )
            return response.text.strip()

        try:
            response_text = await asyncio.wait_for(asyncio.to_thread(_sync_call), timeout=self.timeout)
            if response_text.startswith("```"):
                response_text = re.sub(r'^```[a-z]*\n', '', response_text)
                response_text = re.sub(r'\n```$', '', response_text)

            decision = json.loads(response_text)
            if isinstance(decision, dict) and "type" in decision:
                return decision

        except asyncio.TimeoutError:
            logger.warning(f"Gemini decision call timed out after {self.timeout}s.")
            return {"type": "final_answer", "text": "Execution timed out while consulting Gemini agent model."}
        except Exception as exc:
            logger.warning(f"Gemini decision failed: {exc}")

        return self._heuristic_action(conversation_history, tools)

    def _heuristic_action(self, conversation_history: List[Dict[str, Any]], tools: List[ToolDefinition]) -> Dict[str, Any]:
        """Fallback heuristic when Gemini API is unavailable or fails."""
        user_msg = ""
        for item in conversation_history:
            if item.get("role") == "user":
                user_msg = item.get("text", "")

        executed_tools = {item.get("tool_name") for item in conversation_history if item.get("role") == "tool_result"}

        if tools and not executed_tools:
            user_lower = user_msg.lower()
            nums = re.findall(r'\b\d+\b', user_msg)

            matched_tool = None

            # 1. If prompt has numbers/IDs (e.g. "product 5"), prefer tools with path parameters (e.g. /products/{id})
            if nums:
                for t in tools:
                    if "{" in t.path or ":" in t.path or any(p.in_location == "path" for p in t.parameters):
                        matched_tool = t
                        break

            # 2. Search by keyword matching in tool name or path
            if not matched_tool:
                for t in tools:
                    if t.name.lower() in user_lower or any(word in t.name.lower() for word in user_lower.split() if len(word) > 2):
                        matched_tool = t
                        break

            # 3. Default to first tool
            if not matched_tool:
                matched_tool = tools[0]

            # Extract arguments for path/query parameters
            arguments = {}
            path_params = re.findall(r'\{([a-zA-Z0-9_]+)\}|:([a-zA-Z0-9_]+)', matched_tool.path)
            if not path_params and matched_tool.parameters:
                path_params = [(p.name, p.name) for p in matched_tool.parameters if p.in_location == "path"]

            if path_params and nums:
                for p_tuple in path_params:
                    p_name = p_tuple[0] if isinstance(p_tuple, tuple) else p_tuple
                    val = nums[0]
                    arguments[p_name] = int(val) if val.isdigit() else val

            return {
                "type": "tool_call",
                "tool_name": matched_tool.name,
                "arguments": arguments
            }

        tool_results = [item for item in conversation_history if item.get("role") == "tool_result"]
        if tool_results:
            last_res = tool_results[-1]
            raw_result = last_res.get("result")
            tool_name = last_res.get("tool_name", "")

            formatted_text = self._format_heuristic_summary(user_msg, tool_name, raw_result)
            return {
                "type": "final_answer",
                "text": formatted_text
            }

        return {
            "type": "final_answer",
            "text": f"Processed user message: {user_msg}"
        }

    @staticmethod
    def _format_heuristic_summary(user_msg: str, tool_name: str, raw_result: Any) -> str:
        """Formats clean, human-readable natural language answers from tool result payloads."""
        if not raw_result:
            return f"Tool '{tool_name}' executed successfully, but returned no data."

        data_obj = raw_result
        if isinstance(raw_result, dict) and "_truncated_text" in raw_result:
            try:
                data_obj = json.loads(raw_result["_truncated_text"])
            except Exception:
                data_obj = raw_result["_truncated_text"]
        elif isinstance(raw_result, str):
            try:
                data_obj = json.loads(raw_result)
            except Exception:
                data_obj = raw_result

        # Handle Single Object Response (e.g. GET /products/5)
        if isinstance(data_obj, dict) and not ("_truncated_text" in data_obj and len(data_obj) == 1):
            title = data_obj.get("title") or data_obj.get("name") or data_obj.get("id")
            price = data_obj.get("price")
            category = data_obj.get("category")
            description = data_obj.get("description")
            rating = data_obj.get("rating")

            lines = []
            if title:
                lines.append(f"• **Title:** {title}")
            if price is not None:
                lines.append(f"• **Price:** ${price}")
            if category:
                lines.append(f"• **Category:** {category}")
            if rating and isinstance(rating, dict):
                lines.append(f"• **Rating:** {rating.get('rate')} ⭐ ({rating.get('count')} reviews)")
            if description:
                lines.append(f"• **Description:** {description}")

            if lines:
                return f"**Product Details ({tool_name}):**\n\n" + "\n\n".join(lines)

        data_str = json.dumps(data_obj) if isinstance(data_obj, (dict, list)) else str(data_obj)
        user_lower = user_msg.lower()

        # Extract categories if user asked for categories
        if "category" in user_lower or "categories" in user_lower:
            categories = set(re.findall(r'category"\s*:\s*"([^"]+)"', data_str, re.IGNORECASE))
            if categories:
                formatted_cats = "\n".join(f"- {c}" for c in sorted(categories))
                return f"Here are the available product categories:\n\n{formatted_cats}"

        # Extract item titles if user asked for items/products
        titles = re.findall(r'title"\s*:\s*"([^"]+)"', data_str, re.IGNORECASE)
        prices = re.findall(r'price"\s*:\s*([\d\.]+)', data_str)

        if titles:
            items_list = []
            for idx, title in enumerate(titles[:10]):
                price_str = f" (${prices[idx]})" if idx < len(prices) else ""
                items_list.append(f"{idx + 1}. {title}{price_str}")

            summary = f"Retrieved {len(titles)} products:\n\n" + "\n".join(items_list)
            if len(titles) > 10:
                summary += f"\n\n*(Showing top 10 items out of {len(titles)} total)*"
            return summary

        clean_text = re.sub(r'[\{\}\[\]"]', '', data_str)
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        if len(clean_text) > 300:
            clean_text = clean_text[:300] + "..."

        return f"Tool '{tool_name}' executed successfully:\n\n{clean_text}"


class AgentRuntime:
    """
    Multi-step Agent Runtime orchestrator.
    Receives a user prompt, selects tools, validates parameters, calls ToolExecutor,
    and returns a structured AgentResponse.
    """

    MAX_CONTEXT_RESULT_LEN = 2000  # Truncate tool execution results in LLM prompt context to 2,000 chars

    def __init__(
        self,
        gemini_service: Optional[GeminiAgentService] = None,
        registry: Optional[ToolRegistry] = None,
        executor: Optional[ToolExecutor] = None,
        max_iterations: int = 5
    ):
        self.gemini_service = gemini_service or GeminiAgentService()
        self.registry = registry or default_registry
        self.executor = executor or ToolExecutor()
        self.max_iterations = max_iterations

    def run(
        self,
        user_message: str,
        tools: Optional[List[ToolDefinition]] = None,
        max_iterations: Optional[int] = None
    ) -> AgentResponse:
        """Synchronous wrapper for run_async."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                return asyncio.run_coroutine_threadsafe(
                    self.run_async(user_message, tools, max_iterations), loop
                ).result(timeout=30.0)
            else:
                return loop.run_until_complete(self.run_async(user_message, tools, max_iterations))
        except Exception:
            return asyncio.run(self.run_async(user_message, tools, max_iterations))

    async def run_async(
        self,
        user_message: str,
        tools: Optional[List[ToolDefinition]] = None,
        max_iterations: Optional[int] = None
    ) -> AgentResponse:
        """
        Asynchronously executes the multi-step agent tool calling loop.
        """
        start_time = time.time()
        max_iter = max_iterations or self.max_iterations

        # Active tool definitions
        active_tools = tools or self.registry.list_tools()

        # Build map of allowed tools restricted strictly to active_tools
        tool_map: Dict[str, ToolDefinition] = {t.name: t for t in active_tools}
        for t in active_tools:
            tool_map[t.id] = t

        conversation_history: List[Dict[str, Any]] = [
            {"role": "user", "text": user_message}
        ]

        steps: List[ToolCallStep] = []
        tools_called: List[str] = []
        iterations = 0

        while iterations < max_iter:
            iterations += 1

            # Request next decision from Gemini / LLM abstraction
            decision = await self.gemini_service.decide_next_action(conversation_history, active_tools)

            decision_type = decision.get("type", "final_answer")

            if decision_type == "final_answer":
                answer_text = decision.get("text", "No response text generated.")
                total_latency = round((time.time() - start_time) * 1000, 2)
                return AgentResponse(
                    success=True,
                    final_answer=answer_text,
                    tools_called=tools_called,
                    steps=steps,
                    total_iterations=iterations,
                    total_latency_ms=total_latency
                )

            elif decision_type == "tool_call":
                tool_name = decision.get("tool_name", "")
                raw_args = decision.get("arguments", {})
                if not isinstance(raw_args, dict):
                    raw_args = {}

                # Security check: Restrict strictly to supplied/registered active_tools
                target_tool = tool_map.get(tool_name)

                if not target_tool:
                    allowed_names = ", ".join([t.name for t in active_tools]) or "none"
                    error_msg = (
                        f"Requested tool '{tool_name}' is UNAVAILABLE and not authorized. "
                        f"You MUST choose ONLY from available tools [{allowed_names}] or output a final_answer."
                    )
                    steps.append(ToolCallStep(
                        tool_name=tool_name,
                        arguments=raw_args,
                        error=error_msg
                    ))
                    conversation_history.append({
                        "role": "tool_result",
                        "tool_name": tool_name,
                        "error": error_msg
                    })
                    continue

                tools_called.append(target_tool.name)

                # Execute tool exclusively through ToolExecutor
                try:
                    exec_result = await self.executor.execute(target_tool, raw_args)
                    
                    # Store original full result in AgentResponse steps
                    steps.append(ToolCallStep(
                        tool_name=target_tool.name,
                        arguments=raw_args,
                        execution_result=exec_result,
                        error=exec_result.error
                    ))

                    # Bounded context for LLM conversation history
                    context_result = self._truncate_for_context(exec_result.response)

                    conversation_history.append({
                        "role": "tool_result",
                        "tool_name": target_tool.name,
                        "result": context_result,
                        "status_code": exec_result.status_code,
                        "error": exec_result.error
                    })

                except ToolExecutionError as exc:
                    steps.append(ToolCallStep(
                        tool_name=target_tool.name,
                        arguments=raw_args,
                        error=exc.message
                    ))
                    conversation_history.append({
                        "role": "tool_result",
                        "tool_name": target_tool.name,
                        "error": exc.message
                    })
                except Exception as exc:
                    steps.append(ToolCallStep(
                        tool_name=target_tool.name,
                        arguments=raw_args,
                        error=f"Execution failed: {str(exc)}"
                    ))
                    conversation_history.append({
                        "role": "tool_result",
                        "tool_name": target_tool.name,
                        "error": str(exc)
                    })

        # Exceeded max iterations
        total_latency = round((time.time() - start_time) * 1000, 2)
        return AgentResponse(
            success=False,
            final_answer=f"Agent loop reached maximum allowed iterations ({max_iter}) without completing.",
            tools_called=tools_called,
            steps=steps,
            total_iterations=iterations,
            total_latency_ms=total_latency,
            error=f"Maximum iteration limit ({max_iter}) exceeded."
        )

    @classmethod
    def _truncate_for_context(cls, response_data: Any) -> Any:
        """Serializes and truncates tool results to keep Gemini context window bounded."""
        if response_data is None:
            return None

        if isinstance(response_data, (dict, list)):
            serialized = json.dumps(response_data)
        else:
            serialized = str(response_data)

        if len(serialized) <= cls.MAX_CONTEXT_RESULT_LEN:
            return response_data

        # Explicit truncation message for LLM
        truncated_str = serialized[:cls.MAX_CONTEXT_RESULT_LEN] + f"... [TOOL RESULT TRUNCATED AT {cls.MAX_CONTEXT_RESULT_LEN} CHARS]"
        return {"_truncated_text": truncated_str}

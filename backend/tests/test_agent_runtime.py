import unittest
import asyncio
import json
import os
from unittest.mock import patch, AsyncMock, MagicMock

from agent.schemas import AgentResponse, ToolCallStep
from agent.runtime import AgentRuntime, GeminiAgentService
from tool_generator.schemas import ToolDefinition, ToolParameter, ToolExecutionResult
from tool_generator.registry import ToolRegistry, default_registry
from tool_generator.generator import ConnectorGenerator
from tool_executor.executor import ToolExecutor, ToolExecutionError
from api_parser.schemas import NormalizedAPISpec, EndpointSchema


class TestAgentRuntime(unittest.TestCase):

    def setUp(self):
        self.registry = ToolRegistry()
        self.registry.clear()

        self.tool1 = ToolDefinition(
            id="get_user",
            name="get_user",
            description="Get user details by ID",
            method="GET",
            path="/users/{id}",
            base_url="https://api.example.com",
            parameters=[ToolParameter(name="id", in_location="path", required=True)]
        )

        self.tool2 = ToolDefinition(
            id="list_user_orders",
            name="list_user_orders",
            description="List user orders",
            method="GET",
            path="/users/{user_id}/orders",
            base_url="https://api.example.com",
            parameters=[ToolParameter(name="user_id", in_location="path", required=True)]
        )

        self.registry.register_tools([self.tool1, self.tool2])

    @patch("agent.runtime.GeminiAgentService.decide_next_action", new_callable=AsyncMock)
    @patch("tool_executor.executor.ToolExecutor.execute", new_callable=AsyncMock)
    def test_successful_single_tool_execution(self, mock_execute, mock_decide):
        mock_decide.side_effect = [
            {"type": "tool_call", "tool_name": "get_user", "arguments": {"id": "42"}},
            {"type": "final_answer", "text": "User 42 is Alice."}
        ]

        mock_execute.return_value = ToolExecutionResult(
            success=True,
            tool="get_user",
            status_code=200,
            latency_ms=12.5,
            request={"method": "GET", "url": "https://api.example.com/users/42"},
            response={"id": "42", "name": "Alice"}
        )

        runtime = AgentRuntime(registry=self.registry, executor=ToolExecutor())
        response: AgentResponse = asyncio.run(runtime.run_async("Who is user 42?"))

        self.assertTrue(response.success)
        self.assertEqual(response.final_answer, "User 42 is Alice.")
        self.assertEqual(response.tools_called, ["get_user"])
        self.assertEqual(len(response.steps), 1)
        self.assertEqual(response.steps[0].tool_name, "get_user")
        self.assertEqual(response.steps[0].execution_result.response["name"], "Alice")

    @patch("agent.runtime.GeminiAgentService.decide_next_action", new_callable=AsyncMock)
    @patch("tool_executor.executor.ToolExecutor.execute", new_callable=AsyncMock)
    def test_context_truncation_for_large_responses(self, mock_execute, mock_decide):
        large_response = {"data": "X" * 3000, "items": list(range(100))}

        mock_decide.side_effect = [
            {"type": "tool_call", "tool_name": "get_user", "arguments": {"id": "42"}},
            {"type": "final_answer", "text": "Processed large user response."}
        ]

        mock_execute.return_value = ToolExecutionResult(
            success=True,
            tool="get_user",
            status_code=200,
            latency_ms=20.0,
            request={"method": "GET"},
            response=large_response
        )

        runtime = AgentRuntime(registry=self.registry, executor=ToolExecutor())
        response = asyncio.run(runtime.run_async("Get large user data"))

        self.assertTrue(response.success)
        self.assertEqual(response.steps[0].execution_result.response, large_response)

        call_args_list = mock_decide.call_args_list
        second_call_history = call_args_list[1][0][0]
        tool_result_entry = [h for h in second_call_history if h.get("role") == "tool_result"][0]
        
        self.assertIn("_truncated_text", tool_result_entry["result"])
        self.assertIn("[TOOL RESULT TRUNCATED AT 2000 CHARS]", tool_result_entry["result"]["_truncated_text"])

    @patch("agent.runtime.GeminiAgentService.decide_next_action", new_callable=AsyncMock)
    @patch("tool_executor.executor.ToolExecutor.execute", new_callable=AsyncMock)
    def test_multiple_sequential_tool_calls(self, mock_execute, mock_decide):
        mock_decide.side_effect = [
            {"type": "tool_call", "tool_name": "get_user", "arguments": {"id": "42"}},
            {"type": "tool_call", "tool_name": "list_user_orders", "arguments": {"user_id": "42"}},
            {"type": "final_answer", "text": "Alice has 2 active orders."}
        ]

        mock_execute.side_effect = [
            ToolExecutionResult(
                success=True,
                tool="get_user",
                status_code=200,
                latency_ms=10.0,
                request={"method": "GET"},
                response={"id": "42", "name": "Alice"}
            ),
            ToolExecutionResult(
                success=True,
                tool="list_user_orders",
                status_code=200,
                latency_ms=15.0,
                request={"method": "GET"},
                response=[{"order_id": 101}, {"order_id": 102}]
            )
        ]

        runtime = AgentRuntime(registry=self.registry, executor=ToolExecutor())
        response = asyncio.run(runtime.run_async("Show orders for user 42"))

        self.assertTrue(response.success)
        self.assertEqual(response.tools_called, ["get_user", "list_user_orders"])
        self.assertEqual(len(response.steps), 2)
        self.assertEqual(response.total_iterations, 3)

    @patch("agent.runtime.GeminiAgentService.decide_next_action", new_callable=AsyncMock)
    def test_unknown_tool_rejection(self, mock_decide):
        mock_decide.side_effect = [
            {"type": "tool_call", "tool_name": "unauthorized_admin_tool", "arguments": {}},
            {"type": "final_answer", "text": "Sorry, that tool is not available."}
        ]

        runtime = AgentRuntime(registry=self.registry, executor=ToolExecutor())
        response = asyncio.run(runtime.run_async("Run unauthorized command"))

        self.assertTrue(response.success)
        self.assertEqual(response.steps[0].tool_name, "unauthorized_admin_tool")
        self.assertIn("UNAVAILABLE and not authorized", response.steps[0].error)
        self.assertIn("You MUST choose ONLY from available tools", response.steps[0].error)

    @patch("agent.runtime.GeminiAgentService.decide_next_action", new_callable=AsyncMock)
    @patch("tool_executor.executor.ToolExecutor.execute", new_callable=AsyncMock)
    def test_invalid_arguments_handling(self, mock_execute, mock_decide):
        mock_decide.side_effect = [
            {"type": "tool_call", "tool_name": "get_user", "arguments": {}},
            {"type": "final_answer", "text": "Failed due to missing id."}
        ]

        mock_execute.side_effect = ToolExecutionError("Missing required arguments for tool 'get_user': id")

        runtime = AgentRuntime(registry=self.registry, executor=ToolExecutor())
        response = asyncio.run(runtime.run_async("Get user without id"))

        self.assertTrue(response.success)
        self.assertIn("Missing required arguments", response.steps[0].error)

    @patch("agent.runtime.GeminiAgentService.decide_next_action", new_callable=AsyncMock)
    def test_maximum_iteration_protection(self, mock_decide):
        mock_decide.return_value = {"type": "tool_call", "tool_name": "get_user", "arguments": {"id": "1"}}

        runtime = AgentRuntime(registry=self.registry, executor=ToolExecutor(), max_iterations=3)
        
        with patch("tool_executor.executor.ToolExecutor.execute", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = ToolExecutionResult(
                success=True, tool="get_user", status_code=200, latency_ms=5.0, request={}, response={}
            )
            response = asyncio.run(runtime.run_async("Infinite tool call loop prompt"))

        self.assertFalse(response.success)
        self.assertEqual(response.total_iterations, 3)
        self.assertIn("Maximum iteration limit (3) exceeded", response.error)

    @patch.dict(os.environ, {"GEMINI_API_KEY": "fake_key"})
    def test_gemini_service_declarations_conversion(self):
        service = GeminiAgentService()
        declarations = service.convert_tools_to_gemini_declarations([self.tool1])

        self.assertEqual(len(declarations), 1)
        self.assertEqual(declarations[0]["name"], "get_user")
        self.assertEqual(declarations[0]["parameters"]["type"], "OBJECT")
        self.assertIn("id", declarations[0]["parameters"]["properties"])

    @patch("agent.runtime.GeminiAgentService.decide_next_action", new_callable=AsyncMock)
    def test_sequential_api_analysis_workspace_clearing(self, mock_decide):
        """Verifies that analyzing API B clears API A tools from global workspace registry and Agent Runtime."""
        generator = ConnectorGenerator()
        default_registry.clear()

        # Step 1: Analyze API A
        spec_a = NormalizedAPISpec(
            api_name="API_A",
            endpoints=[EndpointSchema(name="search_users_a", method="GET", path="/users_a")]
        )
        connector_a = generator.generate(spec_a)
        default_registry.clear()
        default_registry.register_tools(connector_a.tools)

        self.assertIsNotNone(default_registry.get_tool("search_users_a"))

        # Step 2: Analyze API B
        spec_b = NormalizedAPISpec(
            api_name="API_B",
            endpoints=[EndpointSchema(name="get_product_b", method="GET", path="/product_b")]
        )
        connector_b = generator.generate(spec_b)
        default_registry.clear()
        default_registry.register_tools(connector_b.tools)

        # Step 3 & 4: Verify API A tools are cleared and API B tools are available
        self.assertIsNone(default_registry.get_tool("search_users_a"))
        self.assertIsNotNone(default_registry.get_tool("get_product_b"))

        # Step 5: Verify Agent Runtime using active registry tools rejects API A tool call
        mock_decide.side_effect = [
            {"type": "tool_call", "tool_name": "search_users_a", "arguments": {}},
            {"type": "final_answer", "text": "Cannot access API A tool."}
        ]

        runtime = AgentRuntime(registry=default_registry, executor=ToolExecutor())
        response = asyncio.run(runtime.run_async("Try using tool from API A"))

        self.assertTrue(response.success)
        self.assertIn("search_users_a", response.steps[0].tool_name)
        self.assertIn("UNAVAILABLE and not authorized", response.steps[0].error)


if __name__ == "__main__":
    unittest.main()

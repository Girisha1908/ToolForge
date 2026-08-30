import unittest
import asyncio
import json
import os
from unittest.mock import patch, AsyncMock, MagicMock

from api_parser.schemas import (
    NormalizedAPISpec, EndpointSchema, ParameterSchema,
    RequestBodySchema, ResponseSchema, AuthenticationSchema
)
from tool_generator.schemas import (
    ToolDefinition, ToolParameter, GeneratedConnector, ToolExecutionResult
)
from tool_generator.generator import ConnectorGenerator, GeminiService
from tool_generator.registry import ToolRegistry, default_registry
from tool_executor.executor import ToolExecutor, ToolExecutionError
from tool_executor.authentication import AuthHandler


class TestConnectorGenerator(unittest.TestCase):

    def setUp(self):
        self.generator = ConnectorGenerator()
        self.registry = ToolRegistry()
        self.registry.clear()

    def test_normal_tool_generation_multi_endpoint(self):
        spec = NormalizedAPISpec(
            api_name="PetStore API",
            version="1.0.0",
            base_url="https://petstore.example.com/v2",
            authentication=AuthenticationSchema(type="bearer", in_location="header", name="Authorization"),
            endpoints=[
                EndpointSchema(
                    name="get_pet_by_id",
                    summary="Get pet by ID",
                    method="GET",
                    path="/pet/{pet_id}",
                    parameters=[
                        ParameterSchema(name="pet_id", in_location="path", type="integer", required=True)
                    ]
                ),
                EndpointSchema(
                    name="search_pets",
                    summary="Search pets by status",
                    method="GET",
                    path="/pet/findByStatus",
                    parameters=[
                        ParameterSchema(name="status", in_location="query", type="string", required=False)
                    ]
                ),
                EndpointSchema(
                    name="add_pet",
                    summary="Add a new pet",
                    method="POST",
                    path="/pet",
                    request_body=RequestBodySchema(
                        content_type="application/json",
                        schema_definition={"type": "object", "properties": {"name": {"type": "string"}}}
                    )
                )
            ]
        )

        connector: GeneratedConnector = self.generator.generate(spec)

        self.assertEqual(connector.api_name, "PetStore API")
        self.assertEqual(len(connector.tools), 3)

        tool_get = [t for t in connector.tools if t.method == "GET" and "{pet_id}" in t.path][0]
        self.assertEqual(tool_get.name, "get_pet_by_id")
        self.assertEqual(len(tool_get.parameters), 1)
        self.assertEqual(tool_get.parameters[0].in_location, "path")

        tool_post = [t for t in connector.tools if t.method == "POST"][0]
        self.assertEqual(tool_post.name, "add_pet")
        self.assertIsNotNone(tool_post.request_body_schema)

    def test_duplicate_tool_name_handling(self):
        spec = NormalizedAPISpec(
            api_name="Duplicate Name API",
            endpoints=[
                EndpointSchema(name="get_user", method="GET", path="/user/v1"),
                EndpointSchema(name="get_user", method="GET", path="/user/v2")
            ]
        )
        connector = self.generator.generate(spec)
        self.assertEqual(len(connector.tools), 2)
        self.assertEqual(connector.tools[0].name, "get_user")
        self.assertEqual(connector.tools[1].name, "get_user_1")

    @patch("tool_generator.generator.GeminiService.generate_tool_descriptions", new_callable=AsyncMock)
    def test_malformed_gemini_fallback(self, mock_gemini):
        mock_gemini.side_effect = Exception("Gemini service failed or output malformed")
        spec = NormalizedAPISpec(
            api_name="Fallback API",
            endpoints=[EndpointSchema(name="list_items", method="GET", path="/items")]
        )
        # Fallback to deterministic generation
        connector = self.generator.generate(spec)
        self.assertEqual(len(connector.tools), 1)
        self.assertEqual(connector.tools[0].name, "list_items")


class TestToolRegistry(unittest.TestCase):

    def setUp(self):
        self.registry = ToolRegistry()
        self.registry.clear()

    def test_registry_operations(self):
        tool = ToolDefinition(
            id="test_tool",
            name="test_tool",
            description="Test Tool Description",
            method="GET",
            path="/test"
        )
        self.registry.register_tool(tool)

        retrieved = self.registry.get_tool("test_tool")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.name, "test_tool")

        tools_list = self.registry.list_tools()
        self.assertEqual(len(tools_list), 1)


class TestToolExecutor(unittest.TestCase):

    def setUp(self):
        self.executor = ToolExecutor()

    def test_missing_required_path_argument(self):
        tool = ToolDefinition(
            id="get_user",
            name="get_user",
            description="Get User",
            method="GET",
            path="/users/{user_id}",
            parameters=[
                ToolParameter(name="user_id", in_location="path", required=True)
            ]
        )
        with self.assertRaises(ToolExecutionError) as ctx:
            asyncio.run(self.executor.execute(tool, arguments={}))
        self.assertIn("Missing required arguments", str(ctx.exception))

    @patch("httpx.AsyncClient.request", new_callable=AsyncMock)
    @patch("api_parser.fetcher.DocFetcher.validate_and_resolve_url")
    def test_successful_get_with_path_and_query_parameters(self, mock_resolve, mock_httpx):
        mock_resolve.return_value = ("93.184.216.34", "api.example.com")
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": 42, "name": "Alice"}
        mock_httpx.return_value = mock_response

        tool = ToolDefinition(
            id="get_user_by_id",
            name="get_user_by_id",
            description="Get User by ID",
            method="GET",
            path="/users/{id}",
            base_url="https://api.example.com",
            parameters=[
                ToolParameter(name="id", in_location="path", required=True),
                ToolParameter(name="verbose", in_location="query", required=False)
            ]
        )

        result: ToolExecutionResult = asyncio.run(
            self.executor.execute(tool, arguments={"id": 42, "verbose": "true"})
        )

        self.assertTrue(result.success)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.response["name"], "Alice")
        mock_httpx.assert_called_once()

    @patch("httpx.AsyncClient.request", new_callable=AsyncMock)
    @patch("api_parser.fetcher.DocFetcher.validate_and_resolve_url")
    def test_successful_post_with_json_body(self, mock_resolve, mock_httpx):
        mock_resolve.return_value = ("93.184.216.34", "api.example.com")

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": 101, "status": "created"}
        mock_httpx.return_value = mock_response

        tool = ToolDefinition(
            id="create_user",
            name="create_user",
            description="Create User",
            method="POST",
            path="/users",
            base_url="https://api.example.com",
            request_body_schema={"type": "object", "properties": {"email": {"type": "string"}}}
        )

        result = asyncio.run(
            self.executor.execute(tool, arguments={"email": "alice@example.com", "name": "Alice"})
        )

        self.assertTrue(result.success)
        self.assertEqual(result.status_code, 201)
        self.assertEqual(result.response["id"], 101)


class TestAuthHandler(unittest.TestCase):

    @patch.dict(os.environ, {"AUTH_BEARER_TOKEN": "secret_token_123"})
    def test_bearer_token_application(self):
        headers = {}
        query = {}
        auth = AuthenticationSchema(type="bearer", in_location="header", name="Authorization")
        AuthHandler.apply_auth(headers, query, auth)
        self.assertEqual(headers.get("Authorization"), "Bearer secret_token_123")

    @patch.dict(os.environ, {"API_KEY": "my_api_key_val"})
    def test_api_key_header_application(self):
        headers = {}
        query = {}
        auth = AuthenticationSchema(type="api_key", in_location="header", name="X-API-Key")
        AuthHandler.apply_auth(headers, query, auth)
        self.assertEqual(headers.get("X-API-Key"), "my_api_key_val")


if __name__ == "__main__":
    unittest.main()

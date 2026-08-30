import unittest
import asyncio
import json
import os
from unittest.mock import patch, AsyncMock, MagicMock

from api_parser.schemas import (
    NormalizedAPISpec, EndpointSchema, ParameterSchema,
    RequestBodySchema, ResponseSchema, AuthenticationSchema
)
from api_parser.fetcher import DocFetchError
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

    @patch.dict(os.environ, {"GEMINI_API_KEY": "fake_key"})
    @patch("tool_generator.generator.GeminiService.generate_tool_enrichments", new_callable=AsyncMock)
    def test_successful_gemini_generation(self, mock_enrichments):
        mock_enrichments.return_value = [
            {
                "name": "fetch_user_profile",
                "description": "Enriched description for fetching user profile",
                "method": "GET",
                "path": "/users/{id}",
                "parameters": [{"name": "id", "description": "Enriched user ID parameter"}]
            }
        ]

        spec = NormalizedAPISpec(
            api_name="Gemini API",
            endpoints=[
                EndpointSchema(
                    name="get_user",
                    method="GET",
                    path="/users/{id}",
                    parameters=[ParameterSchema(name="id", in_location="path", required=True)]
                )
            ]
        )

        generator = ConnectorGenerator(gemini_service=GeminiService(api_key="fake_key"))
        connector = asyncio.run(generator.generate_async(spec))
        self.assertEqual(len(connector.tools), 1)
        self.assertEqual(connector.tools[0].name, "fetch_user_profile")
        self.assertEqual(connector.tools[0].description, "Enriched description for fetching user profile")
        self.assertEqual(connector.tools[0].parameters[0].description, "Enriched user ID parameter")

    @patch.dict(os.environ, {"GEMINI_API_KEY": "fake_key"})
    @patch("tool_generator.generator.GeminiService.generate_tool_enrichments", new_callable=AsyncMock)
    def test_malformed_gemini_response_fallback(self, mock_enrichments):
        mock_enrichments.side_effect = ValueError("Invalid JSON response from Gemini")
        spec = NormalizedAPISpec(
            api_name="Fallback API",
            endpoints=[EndpointSchema(name="list_items", method="GET", path="/items")]
        )
        generator = ConnectorGenerator(gemini_service=GeminiService(api_key="fake_key"))
        connector = asyncio.run(generator.generate_async(spec))
        self.assertEqual(len(connector.tools), 1)
        self.assertEqual(connector.tools[0].name, "list_items")

    @patch.dict(os.environ, {"GEMINI_API_KEY": "fake_key"})
    @patch("tool_generator.generator.GeminiService.generate_tool_enrichments", new_callable=AsyncMock)
    def test_gemini_timeout_fallback(self, mock_enrichments):
        mock_enrichments.side_effect = asyncio.TimeoutError("Gemini call timed out")
        spec = NormalizedAPISpec(
            api_name="Timeout API",
            endpoints=[EndpointSchema(name="get_stats", method="GET", path="/stats")]
        )
        generator = ConnectorGenerator(gemini_service=GeminiService(api_key="fake_key"))
        connector = asyncio.run(generator.generate_async(spec))
        self.assertEqual(len(connector.tools), 1)
        self.assertEqual(connector.tools[0].name, "get_stats")

    @patch.dict(os.environ, {"GEMINI_API_KEY": "fake_key"})
    @patch("tool_generator.generator.GeminiService.generate_tool_enrichments", new_callable=AsyncMock)
    def test_invented_endpoint_detection_fallback(self, mock_enrichments):
        mock_enrichments.return_value = [
            {"name": "get_user", "method": "GET", "path": "/users/{id}"},
            {"name": "invented_endpoint", "method": "DELETE", "path": "/users/all"}
        ]
        spec = NormalizedAPISpec(
            api_name="Invented Endpoint API",
            endpoints=[EndpointSchema(name="get_user", method="GET", path="/users/{id}")]
        )
        generator = ConnectorGenerator(gemini_service=GeminiService(api_key="fake_key"))
        connector = asyncio.run(generator.generate_async(spec))
        self.assertEqual(len(connector.tools), 1)
        self.assertEqual(connector.tools[0].name, "get_user")

    @patch.dict(os.environ, {"GEMINI_API_KEY": "fake_key"})
    @patch("tool_generator.generator.GeminiService.generate_tool_enrichments", new_callable=AsyncMock)
    def test_changed_method_or_path_detection_fallback(self, mock_enrichments):
        mock_enrichments.return_value = [
            {"name": "get_user", "method": "POST", "path": "/users/{id}"}
        ]
        spec = NormalizedAPISpec(
            api_name="Changed Method API",
            endpoints=[EndpointSchema(name="get_user", method="GET", path="/users/{id}")]
        )
        generator = ConnectorGenerator(gemini_service=GeminiService(api_key="fake_key"))
        connector = asyncio.run(generator.generate_async(spec))
        self.assertEqual(len(connector.tools), 1)
        self.assertEqual(connector.tools[0].method, "GET")


class TestToolRegistry(unittest.TestCase):

    def setUp(self):
        self.registry = ToolRegistry()
        self.registry.clear()

    def test_registry_operations_and_indexing(self):
        tool1 = ToolDefinition(
            id="tool_id_001",
            name="search_users",
            description="Search users",
            method="GET",
            path="/users"
        )
        tool2 = ToolDefinition(
            id="tool_id_002",
            name="get_user",
            description="Get single user",
            method="GET",
            path="/users/{id}"
        )
        self.registry.register_tools([tool1, tool2])

        self.assertEqual(self.registry.get_tool("tool_id_001").name, "search_users")
        self.assertEqual(self.registry.get_tool("search_users").id, "tool_id_001")
        
        tools_list = self.registry.list_tools()
        self.assertEqual(len(tools_list), 2)


class TestToolExecutor(unittest.TestCase):

    def setUp(self):
        self.executor = ToolExecutor()

    def test_url_construction_slashes_and_version_paths(self):
        """Verifies url construction with trailing slashes, version paths, and path parameters."""
        tool1 = ToolDefinition(
            id="petstore_tags",
            name="find_by_tags",
            description="Find by tags",
            method="GET",
            base_url="https://petstore3.swagger.io/api/v3",
            path="/pet/findByTags"
        )
        url1, _ = self.executor._build_path_url(tool1, {})
        self.assertEqual(url1, "https://petstore3.swagger.io/api/v3/pet/findByTags")

        tool2 = ToolDefinition(
            id="user_get",
            name="get_user",
            description="Get user",
            method="GET",
            base_url="https://api.example.com/v1/",
            path="/users/{id}",
            parameters=[ToolParameter(name="id", in_location="path", required=True)]
        )
        url2, _ = self.executor._build_path_url(tool2, {"id": "42"})
        self.assertEqual(url2, "https://api.example.com/v1/users/42")

        tool3 = ToolDefinition(
            id="no_slash_user",
            name="get_user_no_slash",
            description="Get user no slash",
            method="GET",
            base_url="https://api.example.com",
            path="users"
        )
        url3, _ = self.executor._build_path_url(tool3, {})
        self.assertEqual(url3, "https://api.example.com/users")

        tool4 = ToolDefinition(
            id="duplicate_prefix",
            name="dup_prefix",
            description="Duplicate prefix",
            method="GET",
            base_url="https://petstore3.swagger.io/api/v3",
            path="/api/v3/pet/findByStatus"
        )
        url4, _ = self.executor._build_path_url(tool4, {})
        self.assertEqual(url4, "https://petstore3.swagger.io/api/v3/pet/findByStatus")

    def test_ssrf_validation_applied_on_constructed_url(self):
        """Verifies SSRF validation blocks private IP target URLs built from base_url + path."""
        tool = ToolDefinition(
            id="private_ip_tool",
            name="private_tool",
            description="Private IP tool",
            method="GET",
            base_url="http://10.0.0.1/internal",
            path="/status"
        )
        with self.assertRaises(DocFetchError) as ctx:
            asyncio.run(self.executor.execute(tool, arguments={}))
        self.assertIn("blocked for security reasons", str(ctx.exception))

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
    def test_path_parameter_url_encoding(self, mock_resolve, mock_httpx):
        mock_resolve.return_value = ("93.184.216.34", "api.example.com")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ok"}
        mock_httpx.return_value = mock_response

        tool = ToolDefinition(
            id="get_file",
            name="get_file",
            description="Get File",
            method="GET",
            path="/files/{file_path}",
            base_url="https://api.example.com",
            parameters=[ToolParameter(name="file_path", in_location="path", required=True)]
        )

        asyncio.run(self.executor.execute(tool, arguments={"file_path": "docs/user @ home.pdf"}))

        target_url = self.executor._build_path_url(tool, {"file_path": "docs/user @ home.pdf"})[0]
        self.assertIn("docs%2Fuser%20%40%20home.pdf", target_url)

    @patch("httpx.AsyncClient.request", new_callable=AsyncMock)
    @patch("api_parser.fetcher.DocFetcher.validate_and_resolve_url")
    def test_http_error_reporting_with_body_snippet(self, mock_resolve, mock_httpx):
        mock_resolve.return_value = ("93.184.216.34", "api.example.com")

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.reason_phrase = "Bad Request"
        mock_response.json.return_value = {"error": "Invalid user ID provided", "code": 1002}
        mock_httpx.return_value = mock_response

        tool = ToolDefinition(
            id="get_user",
            name="get_user",
            description="Get User",
            method="GET",
            path="/users/{id}",
            base_url="https://api.example.com"
        )

        result: ToolExecutionResult = asyncio.run(self.executor.execute(tool, arguments={"id": "bad_id"}))

        self.assertFalse(result.success)
        self.assertEqual(result.status_code, 400)
        self.assertIn("HTTP 400: Bad Request - Invalid user ID provided", result.error)

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

    def setUp(self):
        self.auth_handler = AuthHandler()

    @patch.dict(os.environ, {"AUTH_BEARER_TOKEN": "secret_token_123"}, clear=True)
    def test_bearer_token_application(self):
        headers = {}
        query = {}
        auth = AuthenticationSchema(type="bearer", in_location="header", name="Authorization")
        self.auth_handler.apply_auth(headers, query, auth)
        self.assertEqual(headers.get("Authorization"), "Bearer secret_token_123")

    @patch.dict(os.environ, {"API_KEY": "my_api_key_val"}, clear=True)
    def test_api_key_header_application(self):
        headers = {}
        query = {}
        auth = AuthenticationSchema(type="api_key", in_location="header", name="X-API-Key")
        self.auth_handler.apply_auth(headers, query, auth)
        self.assertEqual(headers.get("X-API-Key"), "my_api_key_val")

    @patch.dict(os.environ, {
        "TWILIO_ACCOUNT_SID": "AC1234567890abcdef",
        "TWILIO_AUTH_TOKEN": "secret_auth_token_999",
        "BASIC_AUTH_TOKEN": "your_basic_auth_token_here"  # Placeholder should be ignored!
    }, clear=True)
    def test_twilio_credentials_basic_auth_construction(self):
        import base64
        headers = {}
        query = {}
        auth = AuthenticationSchema(type="basic", in_location="header", name="Authorization")
        self.auth_handler.apply_auth(headers, query, auth)
        
        expected_user_pass = "AC1234567890abcdef:secret_auth_token_999"
        expected_header = f"Basic {base64.b64encode(expected_user_pass.encode()).decode()}"
        self.assertEqual(headers.get("Authorization"), expected_header)

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_credentials_raises_401_error(self):
        headers = {}
        query = {}
        auth = AuthenticationSchema(type="basic", in_location="header", name="Authorization")
        with self.assertRaises(ToolExecutionError) as ctx:
            self.auth_handler.apply_auth(headers, query, auth)
        self.assertEqual(ctx.exception.status_code, 401)
        self.assertIn("Tool requires 'basic' authentication", ctx.exception.message)

    @patch.dict(os.environ, {
        "TWILIO_ACCOUNT_SID": "AC1234567890abcdef",
        "TWILIO_AUTH_TOKEN": "secret_auth_token_999"
    }, clear=True)
    @patch("httpx.AsyncClient.request", new_callable=AsyncMock)
    @patch("api_parser.fetcher.DocFetcher.validate_and_resolve_url")
    def test_secrets_not_exposed_in_result_or_response(self, mock_resolve, mock_httpx):
        mock_resolve.return_value = ("93.184.216.34", "api.twilio.com")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"accounts": []}
        mock_httpx.return_value = mock_response

        executor = ToolExecutor()
        tool = ToolDefinition(
            id="listaccount",
            name="listaccount",
            description="List Twilio Accounts",
            method="GET",
            path="/2010-04-01/Accounts.json",
            base_url="https://api.twilio.com",
            authentication=AuthenticationSchema(type="basic", in_location="header", name="Authorization")
        )

        result: ToolExecutionResult = asyncio.run(executor.execute(tool, arguments={}))
        self.assertTrue(result.success)
        
        # Verify secret token is NOT leaked in the request summary or result object
        result_json = json.dumps(result.model_dump())
        self.assertNotIn("secret_auth_token_999", result_json)
        self.assertNotIn("AC1234567890abcdef", result_json)


if __name__ == "__main__":
    unittest.main()

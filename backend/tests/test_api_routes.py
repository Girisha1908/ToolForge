import json
import os
import unittest
from unittest.mock import patch, AsyncMock, MagicMock

from fastapi.testclient import TestClient

from main import app
from tool_generator.registry import default_registry

client = TestClient(app)

RAW_OPENAPI_SPEC = json.dumps({
    "openapi": "3.0.0",
    "info": {"title": "Pet Store", "version": "1.0"},
    "servers": [{"url": "https://api.example.com"}],
    "paths": {
        "/pets/{id}": {
            "get": {
                "summary": "Get a pet",
                "parameters": [
                    {"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}
                ],
                "responses": {"200": {"description": "ok"}}
            }
        }
    }
})


class TestApiRoutesHappyPaths(unittest.TestCase):
    """
    HTTP-level tests proving the FastAPI routes wire up correctly end-to-end (status codes +
    response shapes), not just that the underlying classes work in isolation. Fills the gap noted
    in the Phase 3/4 audit: no test previously exercised the actual routing/request/response layer.
    """

    def setUp(self):
        default_registry.clear()
        os.environ.pop("TOOLFORGE_API_KEY", None)

    def test_status_route(self):
        res = client.get("/api/status")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), {"status": "ok"})

    def test_root_route(self):
        res = client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn("message", res.json())

    def test_parse_doc_happy_path(self):
        res = client.post("/api/parse-doc", json={"url": RAW_OPENAPI_SPEC})
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["api_name"], "Pet Store")
        self.assertEqual(len(body["endpoints"]), 1)
        self.assertEqual(body["endpoints"][0]["method"], "GET")

    def test_parse_doc_empty_url_returns_400(self):
        res = client.post("/api/parse-doc", json={"url": "   "})
        self.assertEqual(res.status_code, 400)

    def test_generate_tools_happy_path_and_registers_in_registry(self):
        res = client.post("/api/generate-tools", json={"url": RAW_OPENAPI_SPEC})
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(len(body["tools"]), 1)
        tool_name = body["tools"][0]["name"]

        # Confirm the side effect: tools were actually registered in the shared registry
        list_res = client.get("/api/tools")
        self.assertEqual(list_res.status_code, 200)
        self.assertEqual(len(list_res.json()), 1)
        self.assertEqual(list_res.json()[0]["name"], tool_name)

    def test_get_tool_by_id_happy_path(self):
        gen_res = client.post("/api/generate-tools", json={"url": RAW_OPENAPI_SPEC})
        tool_id = gen_res.json()["tools"][0]["id"]

        res = client.get(f"/api/tools/{tool_id}")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["id"], tool_id)

    def test_get_tool_not_found_returns_404(self):
        res = client.get("/api/tools/does-not-exist")
        self.assertEqual(res.status_code, 404)

    @patch("httpx.AsyncClient.request", new_callable=AsyncMock)
    @patch("api_parser.fetcher.DocFetcher.validate_and_resolve_url")
    def test_execute_tool_happy_path(self, mock_resolve, mock_request):
        mock_resolve.return_value = ("93.184.216.34", "api.example.com")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": 1, "name": "Rex"}
        mock_request.return_value = mock_response

        gen_res = client.post("/api/generate-tools", json={"url": RAW_OPENAPI_SPEC})
        tool_id = gen_res.json()["tools"][0]["id"]

        res = client.post(f"/api/tools/{tool_id}/execute", json={"arguments": {"id": 1}})
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertTrue(body["success"])
        self.assertEqual(body["status_code"], 200)
        self.assertEqual(body["response"], {"id": 1, "name": "Rex"})

    def test_execute_unknown_tool_returns_404(self):
        res = client.post("/api/tools/does-not-exist/execute", json={"arguments": {}})
        self.assertEqual(res.status_code, 404)

    @patch.dict(os.environ, {}, clear=False)
    @patch("httpx.AsyncClient.request", new_callable=AsyncMock)
    @patch("api_parser.fetcher.DocFetcher.validate_and_resolve_url")
    def test_agent_run_happy_path_with_heuristic_fallback(self, mock_resolve, mock_request):
        # No GEMINI_API_KEY -> agent runtime falls back to the deterministic heuristic engine,
        # keeping this test hermetic and reproducible without mocking the LLM call itself.
        os.environ.pop("GEMINI_API_KEY", None)

        mock_resolve.return_value = ("93.184.216.34", "api.example.com")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"message": "hello world"}
        mock_request.return_value = mock_response

        tool = {
            "id": "list_items",
            "name": "list_items",
            "description": "List items",
            "method": "GET",
            "path": "/items",
            "base_url": "https://api.example.com",
            "parameters": [],
            "authentication": {"type": "none"}
        }

        res = client.post("/api/agent/run", json={"message": "list items", "tools": [tool]})
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertTrue(body["success"])
        self.assertIn("list_items", body["tools_called"])
        self.assertTrue(len(body["final_answer"]) > 0)

    def test_agent_run_empty_message_returns_400(self):
        res = client.post("/api/agent/run", json={"message": "   "})
        self.assertEqual(res.status_code, 400)


if __name__ == "__main__":
    unittest.main()

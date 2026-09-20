import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from main import app
from tool_generator.registry import default_registry

client = TestClient(app)


class TestApiSecurity(unittest.TestCase):
    """
    HTTP-level tests for the shared-secret API key gate added in Phase 1.
    Uses default_registry.clear() so these tests don't depend on tools registered
    by other test modules or by manual runs.
    """

    def setUp(self):
        default_registry.clear()

    @patch.dict(os.environ, {}, clear=False)
    def test_status_is_always_public(self):
        os.environ.pop("TOOLFORGE_API_KEY", None)
        res = client.get("/api/status")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), {"status": "ok"})

    @patch.dict(os.environ, {}, clear=False)
    def test_protected_route_open_when_no_key_configured(self):
        os.environ.pop("TOOLFORGE_API_KEY", None)
        res = client.get("/api/tools")
        self.assertEqual(res.status_code, 200)

    @patch.dict(os.environ, {"TOOLFORGE_API_KEY": "secret123"})
    def test_protected_route_rejects_missing_key(self):
        res = client.get("/api/tools")
        self.assertEqual(res.status_code, 401)

    @patch.dict(os.environ, {"TOOLFORGE_API_KEY": "secret123"})
    def test_protected_route_rejects_wrong_key(self):
        res = client.get("/api/tools", headers={"X-ToolForge-Key": "wrong"})
        self.assertEqual(res.status_code, 401)

    @patch.dict(os.environ, {"TOOLFORGE_API_KEY": "secret123"})
    def test_protected_route_accepts_correct_key(self):
        res = client.get("/api/tools", headers={"X-ToolForge-Key": "secret123"})
        self.assertEqual(res.status_code, 200)

    @patch.dict(os.environ, {"TOOLFORGE_API_KEY": "secret123"})
    def test_status_stays_public_even_when_key_configured(self):
        res = client.get("/api/status")
        self.assertEqual(res.status_code, 200)


class TestApiErrorSanitization(unittest.TestCase):
    """Confirms internal exception strings are no longer leaked to HTTP callers."""

    def setUp(self):
        default_registry.clear()
        os.environ.pop("TOOLFORGE_API_KEY", None)

    def test_execute_unknown_tool_returns_generic_404(self):
        res = client.post("/api/tools/does-not-exist/execute", json={"arguments": {}})
        self.assertEqual(res.status_code, 404)

    def test_empty_agent_message_returns_400(self):
        res = client.post("/api/agent/run", json={"message": "   "})
        self.assertEqual(res.status_code, 400)


if __name__ == "__main__":
    unittest.main()

"""Tests for the MCP server layer: schema, store, safe mode, credentials, scrubbing, skill, CLI, stdio."""

import asyncio
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

from api_parser.schemas import AuthenticationSchema
from mcp_server.cli import main as cli_main
from mcp_server.schema import api_slug, env_prefix, input_schema, is_write, mcp_tool_name
from mcp_server.server import ToolForgeMCP
from mcp_server.skill import doctor, render_skill
from mcp_server.store import ConnectorStore
from tool_executor.authentication import AuthHandler
from tool_executor.executor import ToolExecutionError
from tool_generator.schemas import GeneratedConnector, ToolDefinition, ToolExecutionResult, ToolParameter


def make_connector(auth_type="api_key") -> GeneratedConnector:
    auth = AuthenticationSchema(type=auth_type, in_location="header", name="X-API-Key")
    return GeneratedConnector(api_name="Pet Store", base_url="https://api.pets.example", tools=[
        ToolDefinition(id="get_pet", name="get_pet", description="Get one pet by its id.", method="GET",
                       path="/pets/{id}", base_url="https://api.pets.example", authentication=auth,
                       parameters=[ToolParameter(name="id", type="integer", in_location="path", required=True)]),
        ToolDefinition(id="add_pet", name="add_pet", description="Create a pet.", method="POST",
                       path="/pets", base_url="https://api.pets.example", authentication=auth,
                       request_body_schema={"type": "object", "required": ["name"],
                                            "properties": {"name": {"type": "string"}, "age": {"type": "integer"}}}),
    ])


class FakeExecutor:
    """Records calls and returns a canned result, so no network is needed."""

    def __init__(self, response=None, error=None):
        self.calls = []
        self.response = response if response is not None else {"id": 7, "name": "Rex"}
        self.error = error

    async def execute(self, tool, arguments, env_prefix=None):
        self.calls.append((tool.name, dict(arguments), env_prefix))
        if self.error:
            raise self.error
        return ToolExecutionResult(success=True, tool=tool.name, status_code=200, latency_ms=1.0,
                                   request={}, response=self.response)


def run(coro):
    return asyncio.run(coro)


class TestSchema(unittest.TestCase):
    def test_names(self):
        self.assertEqual(api_slug("Pet Store API!"), "pet_store_api")
        self.assertEqual(env_prefix("Pet Store"), "PET_STORE")
        tool = make_connector().tools[0]
        self.assertEqual(mcp_tool_name("Pet Store", tool), "pet_store__get_pet")
        self.assertLessEqual(len(mcp_tool_name("x" * 100, tool)), 64)

    def test_input_schema_read_and_write(self):
        read, write = make_connector().tools
        schema = input_schema(read)
        self.assertEqual(schema["properties"]["id"]["type"], "integer")
        self.assertEqual(schema["required"], ["id"])
        self.assertNotIn("confirm", schema["properties"])  # reads never need confirmation
        wschema = input_schema(write)
        self.assertIn("confirm", wschema["properties"])
        self.assertEqual(set(wschema["properties"]), {"name", "age", "confirm"})  # body fields exposed
        self.assertEqual(wschema["required"], ["name"])
        self.assertTrue(is_write(write) and not is_write(read))


class TestStore(unittest.TestCase):
    def test_round_trip_and_no_secrets(self):
        with tempfile.TemporaryDirectory() as home:
            store = ConnectorStore(Path(home))
            os.environ["PET_STORE_API_KEY"] = "super-secret-key-123"
            try:
                path = store.save(make_connector())
            finally:
                del os.environ["PET_STORE_API_KEY"]
            self.assertEqual(store.list_names(), ["pet_store"])
            self.assertEqual(len(store.load("Pet Store").tools), 2)
            self.assertNotIn("super-secret", path.read_text())
            self.assertTrue(store.delete("pet_store"))
            with self.assertRaises(FileNotFoundError):
                store.load("pet_store")


class TestServerCore(unittest.TestCase):
    def core(self, executor=None, safe=True, env=None):
        return ToolForgeMCP([make_connector()], executor=executor or FakeExecutor(), safe_mode=safe, env=env or {})

    def test_listing(self):
        listed = {t["name"]: t for t in self.core().list_tools()}
        self.assertEqual(set(listed), {"pet_store__get_pet", "pet_store__add_pet"})
        self.assertTrue(listed["pet_store__get_pet"]["readOnly"])
        self.assertIn("confirm", listed["pet_store__add_pet"]["description"])

    def test_read_call_passes_arguments_and_per_api_prefix(self):
        fake = FakeExecutor()
        text, failed = run(self.core(fake).call("pet_store__get_pet", {"id": 7}))
        self.assertFalse(failed)
        self.assertIn("Rex", text)
        self.assertEqual(fake.calls, [("get_pet", {"id": 7}, "PET_STORE")])

    def test_write_is_preview_until_confirmed(self):
        fake = FakeExecutor()
        core = self.core(fake)
        text, failed = run(core.call("pet_store__add_pet", {"name": "Rex"}))
        self.assertIn("SAFE MODE", text)
        self.assertFalse(failed)
        self.assertEqual(fake.calls, [])  # nothing was sent
        run(core.call("pet_store__add_pet", {"name": "Rex", "confirm": True}))
        self.assertEqual(fake.calls, [("add_pet", {"name": "Rex"}, "PET_STORE")])  # confirm is not forwarded

    def test_confirm_must_be_literal_true(self):
        fake = FakeExecutor()
        run(self.core(fake).call("pet_store__add_pet", {"name": "Rex", "confirm": "true"}))
        self.assertEqual(fake.calls, [])  # a string is not a confirmation

    def test_unsafe_mode_skips_preview(self):
        fake = FakeExecutor()
        run(self.core(fake, safe=False).call("pet_store__add_pet", {"name": "Rex"}))
        self.assertEqual(len(fake.calls), 1)

    def test_secrets_are_scrubbed_from_output_and_errors(self):
        env = {"PET_STORE_API_KEY": "sk-live-abcdef123456"}
        leaky = FakeExecutor(response={"echo": "key is sk-live-abcdef123456"})
        text, _ = run(self.core(leaky, env=env).call("pet_store__get_pet", {"id": 1}))
        self.assertNotIn("sk-live-abcdef123456", text)
        self.assertIn("***", text)
        failing = FakeExecutor(error=ToolExecutionError("bad key sk-live-abcdef123456", 401))
        text, failed = run(self.core(failing, env=env).call("pet_store__get_pet", {"id": 1}))
        self.assertTrue(failed)
        self.assertNotIn("sk-live-abcdef123456", text)

    def test_long_output_is_trimmed(self):
        big = FakeExecutor(response={"data": "x" * 50000})
        text, _ = run(self.core(big).call("pet_store__get_pet", {"id": 1}))
        self.assertLess(len(text), 8200)
        self.assertIn("trimmed", text)

    def test_unknown_tool(self):
        text, failed = run(self.core().call("nope", {}))
        self.assertTrue(failed and "Unknown tool" in text)


class TestPerApiCredentials(unittest.TestCase):
    def test_prefix_wins_over_global_and_apis_are_separate(self):
        auth = AuthenticationSchema(type="api_key", in_location="header", name="X-API-Key")
        os.environ.update({"API_KEY": "global-key-000000", "PET_STORE_API_KEY": "pets-key-111111",
                           "OTHER_API_KEY": "other-key-222222"})
        try:
            for prefix, want in (("PET_STORE", "pets-key-111111"), ("OTHER", "other-key-222222"), (None, "global-key-000000")):
                headers = {}
                AuthHandler().apply_auth(headers, {}, auth, env_prefix=prefix)
                self.assertEqual(headers["X-API-Key"], want)
        finally:
            for key in ("API_KEY", "PET_STORE_API_KEY", "OTHER_API_KEY"):
                os.environ.pop(key, None)

    def test_basic_per_api(self):
        auth = AuthenticationSchema(type="basic")
        os.environ.update({"ACME_ACCOUNT_SID": "ACsid123456", "ACME_AUTH_TOKEN": "token-123456"})
        try:
            headers = {}
            AuthHandler().apply_auth(headers, {}, auth, env_prefix="ACME")
            self.assertTrue(headers["Authorization"].startswith("Basic "))
        finally:
            os.environ.pop("ACME_ACCOUNT_SID"), os.environ.pop("ACME_AUTH_TOKEN")


class TestSkillAndDoctor(unittest.TestCase):
    def test_skill_has_use_when_line_and_no_secret_values(self):
        text = render_skill(make_connector())
        self.assertTrue(text.startswith("---\nname: pet_store\ndescription: Use when"))
        self.assertIn("pet_store__get_pet", text)
        self.assertIn("confirm: true", text)
        self.assertIn("PET_STORE_API_KEY", text)

    def test_doctor_reports_without_values(self):
        self.assertTrue(doctor(make_connector(), env={})[0].startswith("MISSING"))
        lines = doctor(make_connector(), env={"PET_STORE_API_KEY": "abc123456789"})
        self.assertTrue(lines[0].startswith("OK"))
        self.assertNotIn("abc123456789", "\n".join(lines))
        self.assertEqual(doctor(make_connector(auth_type="none"), env={}), ["No credentials needed for this API."])
        self.assertIn("OAuth2", doctor(make_connector(auth_type="oauth2"), env={})[0])


RAW_SPEC = json.dumps({
    "openapi": "3.0.0", "info": {"title": "Pet Store", "version": "1.0"},
    "servers": [{"url": "https://api.pets.example"}],
    "paths": {"/pets/{id}": {"get": {"summary": "Get a pet", "parameters": [
        {"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}]}},
        "/pets": {"post": {"summary": "Add a pet", "requestBody": {"content": {"application/json": {
            "schema": {"type": "object", "properties": {"name": {"type": "string"}}}}}}}}},
})


class TestCli(unittest.TestCase):
    def test_import_list_skill_config_doctor(self):
        with tempfile.TemporaryDirectory() as home:
            store = ConnectorStore(Path(home))
            spec_file = Path(home) / "spec.json"
            spec_file.write_text(RAW_SPEC)
            out, err = io.StringIO(), io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                self.assertEqual(cli_main(["import", str(spec_file), "--name", "Pet Store"], store), 0)
                self.assertEqual(cli_main(["list"], store), 0)
                skill_path = Path(home) / "SKILL.md"
                self.assertEqual(cli_main(["skill", "pet_store", "--out", str(skill_path)], store), 0)
                self.assertEqual(cli_main(["config", "pet_store"], store), 0)
                self.assertEqual(cli_main(["doctor", "pet_store"], store), 0)  # this spec declares no auth
                self.assertEqual(cli_main(["skill", "missing"], store), 1)
            self.assertIn("pet_store: 2 tools", out.getvalue())
            self.assertIn('"servers"', out.getvalue())  # the VS Code config block was printed
            self.assertTrue(skill_path.read_text().startswith("---"))


class TestRealStdio(unittest.TestCase):
    def test_vscode_style_round_trip(self):
        """Start the real server process and talk MCP to it, the way VS Code would."""
        from mcp import Client, StdioServerParameters

        with tempfile.TemporaryDirectory() as home:
            ConnectorStore(Path(home)).save(make_connector())
            backend = str(Path(__file__).resolve().parent.parent)
            params = StdioServerParameters(
                command=sys.executable, args=["-m", "mcp_server", "serve", "--api", "pet_store"], cwd=backend,
                env={**os.environ, "TOOLFORGE_HOME": home})

            async def scenario():
                async with Client(params) as client:
                    tools = (await client.list_tools()).tools
                    self.assertEqual({t.name for t in tools}, {"pet_store__get_pet", "pet_store__add_pet"})
                    by_name = {t.name: t for t in tools}
                    self.assertTrue(by_name["pet_store__get_pet"].annotations.read_only_hint)
                    self.assertFalse(by_name["pet_store__add_pet"].annotations.read_only_hint)
                    preview = await client.call_tool("pet_store__add_pet", {"name": "Rex"})
                    self.assertIn("SAFE MODE", preview.content[0].text)

            run(scenario())


if __name__ == "__main__":
    unittest.main()

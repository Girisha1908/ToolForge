import unittest
import asyncio
import json
import os
from unittest.mock import patch, AsyncMock, MagicMock
from api_parser.schemas import (
    NormalizedAPISpec, EndpointSchema, ParameterSchema,
    RequestBodySchema, ResponseSchema, AuthenticationSchema, PaginationSchema
)
from api_parser.fetcher import DocFetcher, DocFetchError, HTMLTextExtractor, connect_with_ip_fallback
from api_parser.structured_parser import StructuredSpecParser
from api_parser.text_parser import TextDocParser
from api_parser.normalizer import APINormalizer
from api_parser.parser import APIParser


class TestDocFetcher(unittest.TestCase):

    def test_validate_url(self):
        self.assertTrue(DocFetcher.validate_url("http://example.com/api/docs"))
        self.assertTrue(DocFetcher.validate_url("https://api.github.com/openapi.json"))
        self.assertFalse(DocFetcher.validate_url("ftp://example.com"))
        self.assertFalse(DocFetcher.validate_url("not_a_url"))
        self.assertFalse(DocFetcher.validate_url(""))

    def test_ssrf_private_ip_blocking(self):
        # Localhost and loopback
        self.assertFalse(DocFetcher.is_safe_public_ip("127.0.0.1"))
        self.assertFalse(DocFetcher.is_safe_public_ip("::1"))
        # Private IPv4 ranges
        self.assertFalse(DocFetcher.is_safe_public_ip("10.0.0.1"))
        self.assertFalse(DocFetcher.is_safe_public_ip("172.16.0.5"))
        self.assertFalse(DocFetcher.is_safe_public_ip("192.168.1.1"))
        # AWS Cloud metadata IP
        self.assertFalse(DocFetcher.is_safe_public_ip("169.254.169.254"))
        # Public IPv4 address
        self.assertTrue(DocFetcher.is_safe_public_ip("8.8.8.8"))
        self.assertTrue(DocFetcher.is_safe_public_ip("1.1.1.1"))

    def test_ssrf_url_validation_rejection(self):
        with self.assertRaises(DocFetchError) as ctx:
            DocFetcher.validate_and_resolve_url("http://127.0.0.1/admin")
        self.assertIn("blocked for security reasons", str(ctx.exception))

        with self.assertRaises(DocFetchError) as ctx:
            DocFetcher.validate_and_resolve_url("http://169.254.169.254/latest/meta-data")
        self.assertIn("blocked for security reasons", str(ctx.exception))

    @patch("httpx.AsyncClient.stream")
    def test_redirect_ssrf_protection_and_dns_pinning(self, mock_stream):
        # Mock initial streamed GET to return a redirect to a private IP URL
        mock_response = MagicMock()
        mock_response.is_redirect = True
        mock_response.status_code = 302
        mock_response.headers = {"location": "http://10.0.0.1/secret.json"}

        class _FakeStreamContextManager:
            async def __aenter__(self):
                return mock_response

            async def __aexit__(self, *exc_info):
                return False

        mock_stream.return_value = _FakeStreamContextManager()

        fetcher = DocFetcher()
        with self.assertRaises(DocFetchError) as ctx:
            asyncio.run(fetcher.fetch("https://example.com/spec.json"))

        self.assertIn("blocked for security reasons", str(ctx.exception))

    def test_connect_fallback_caps_timeout_on_non_final_candidates(self):
        """
        Regression test: when multiple resolved IPs are available, a transiently-unreachable
        first candidate must not consume the full request timeout before falling back to the
        next IP - only the LAST candidate should get the full, uncapped timeout.
        """
        attempts = []

        async def fake_connect_tcp(ip, port, **kw):
            attempts.append((ip, kw.get("timeout")))
            if ip == "1.1.1.1":
                raise TimeoutError("simulated unreachable address")
            return f"connected:{ip}"

        result = asyncio.run(connect_with_ip_fallback(
            fake_connect_tcp, ["1.1.1.1", "2.2.2.2"], 443, timeout=30.0
        ))

        self.assertEqual(result, "connected:2.2.2.2")
        self.assertEqual(attempts[0][0], "1.1.1.1")
        self.assertLessEqual(attempts[0][1], 3.0)  # capped, not the full 30s
        self.assertEqual(attempts[1], ("2.2.2.2", 30.0))  # last candidate keeps full timeout

    def test_connect_fallback_raises_last_exception_if_all_candidates_fail(self):
        async def always_fails(ip, port, **kw):
            raise ConnectionRefusedError(f"refused: {ip}")

        with self.assertRaises(ConnectionRefusedError) as ctx:
            asyncio.run(connect_with_ip_fallback(always_fails, ["1.1.1.1", "2.2.2.2"], 443, timeout=10.0))
        self.assertIn("2.2.2.2", str(ctx.exception))

    @patch("httpx.AsyncClient.stream")
    def test_streaming_size_cap_truncates_before_full_download(self, mock_stream):
        """
        Regression test: the response body must be truncated via streaming (stopping early
        once MAX_TEXT_SIZE is reached) rather than buffering the full body before truncating.
        """
        mock_response = MagicMock()
        mock_response.is_redirect = False
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.charset_encoding = "utf-8"

        oversized_chunk = b"a" * (DocFetcher.MAX_TEXT_SIZE + 1000)
        chunks_yielded = []

        async def fake_aiter_bytes():
            # Yield in two pieces so the cap-check has a real chance to break out early.
            chunks_yielded.append(1)
            yield oversized_chunk[:DocFetcher.MAX_TEXT_SIZE]
            chunks_yielded.append(2)
            yield oversized_chunk[DocFetcher.MAX_TEXT_SIZE:]

        mock_response.aiter_bytes = fake_aiter_bytes

        class _FakeStreamContextManager:
            async def __aenter__(self):
                return mock_response

            async def __aexit__(self, *exc_info):
                return False

        mock_stream.return_value = _FakeStreamContextManager()

        fetcher = DocFetcher()
        content_type, text = asyncio.run(fetcher.fetch("https://example.com/spec.json"))

        self.assertEqual(content_type, "json")
        self.assertEqual(len(text), DocFetcher.MAX_TEXT_SIZE)
        # The second, over-cap chunk must never have been consumed.
        self.assertEqual(chunks_yielded, [1])

    def test_html_text_extraction(self):
        html = """
        <html>
            <head><script>alert('xss');</script></head>
            <body>
                <h1>User API</h1>
                <p>Authentication: Bearer Token</p>
                <div>GET /v1/users</div>
                <table>
                    <tr><td>limit</td><td>integer</td></tr>
                </table>
            </body>
        </html>
        """
        text = DocFetcher.extract_text_from_html(html)
        self.assertIn("User API", text)
        self.assertIn("Authentication: Bearer Token", text)
        self.assertIn("GET /v1/users", text)
        self.assertNotIn("alert", text)

    def test_detect_raw_content_type(self):
        json_str = '{"openapi": "3.0.0"}'
        self.assertEqual(DocFetcher._detect_raw_content_type(json_str)[0], "json")

        html_str = "<html><body>API Docs</body></html>"
        self.assertEqual(DocFetcher._detect_raw_content_type(html_str)[0], "html")

        yaml_str = "openapi: 3.0.0\ninfo:\n  title: Test"
        self.assertEqual(DocFetcher._detect_raw_content_type(yaml_str)[0], "yaml")


class TestStructuredSpecParser(unittest.TestCase):

    def setUp(self):
        self.parser = StructuredSpecParser()

    def test_local_ref_dereferencing(self):
        raw_openapi = {
            "openapi": "3.0.0",
            "info": {"title": "Ref Test API", "version": "1.0.0"},
            "components": {
                "schemas": {
                    "User": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer"},
                            "name": {"type": "string"}
                        }
                    },
                    "UserResponse": {
                        "type": "object",
                        "properties": {
                            "data": {"$ref": "#/components/schemas/User"}
                        }
                    }
                }
            },
            "paths": {
                "/user": {
                    "get": {
                        "summary": "Get User",
                        "responses": {
                            "200": {
                                "description": "OK",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/UserResponse"}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        spec = self.parser.parse(json.dumps(raw_openapi))
        ep = spec.endpoints[0]
        resp_schema = ep.responses[0].schema_definition
        # Ensure $ref was fully recursively dereferenced into properties
        self.assertIn("properties", resp_schema)
        user_props = resp_schema["properties"]["data"]["properties"]
        self.assertEqual(user_props["id"]["type"], "integer")
        self.assertEqual(user_props["name"]["type"], "string")

    def test_circular_ref_dereferencing_safety(self):
        raw_openapi = {
            "openapi": "3.0.0",
            "info": {"title": "Circular Ref API", "version": "1.0.0"},
            "components": {
                "schemas": {
                    "Node": {
                        "type": "object",
                        "properties": {
                            "value": {"type": "string"},
                            "child": {"$ref": "#/components/schemas/Node"}
                        }
                    }
                }
            },
            "paths": {
                "/tree": {
                    "get": {
                        "responses": {
                            "200": {
                                "description": "OK",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/Node"}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        # Should complete dereferencing safely without infinite recursion error
        spec = self.parser.parse(json.dumps(raw_openapi))
        ep = spec.endpoints[0]
        resp_schema = ep.responses[0].schema_definition
        child_schema = resp_schema["properties"]["child"]
        self.assertIn("Circular reference", child_schema.get("description", ""))

    def test_parse_postman_collection(self):
        postman_data = {
            "info": {
                "name": "Postman Test Collection",
                "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
            },
            "item": [
                {
                    "name": "Search Items",
                    "request": {
                        "method": "GET",
                        "url": {
                            "raw": "https://api.example.com/items?q=test",
                            "query": [{"key": "q", "value": "test"}]
                        }
                    }
                }
            ]
        }
        spec = self.parser.parse(json.dumps(postman_data))
        self.assertEqual(spec.api_name, "Postman Test Collection")
        self.assertEqual(len(spec.endpoints), 1)
        self.assertEqual(spec.endpoints[0].method, "GET")
        self.assertEqual(spec.endpoints[0].path, "/items")
        self.assertEqual(spec.endpoints[0].name, "search_items")


class TestTextDocParser(unittest.TestCase):

    def setUp(self):
        self.parser = TextDocParser()

    def test_parse_text_documentation(self):
        text_doc = """
        Payment Gateway API
        Authorization: Bearer <token>

        Endpoints:

        GET /v1/charges
        Parameters:
        limit (integer, optional) - Number of items to return
        starting_after (string, optional) - Cursor for pagination

        POST /v1/charges
        Body:
        {"amount": 1000, "currency": "usd"}

        Response 200:
        Success charge created.
        Status 400 Bad Request.
        """
        spec = self.parser.parse(text_doc)

        self.assertEqual(spec.api_name, "Payment Gateway API")
        self.assertEqual(spec.authentication.type, "bearer")
        self.assertEqual(len(spec.endpoints), 2)

        ep_get = [e for e in spec.endpoints if e.method == "GET"][0]
        self.assertEqual(ep_get.path, "/v1/charges")
        self.assertEqual(len(ep_get.parameters), 2)
        self.assertIsNotNone(ep_get.pagination)
        self.assertEqual(ep_get.pagination.type, "cursor")

        ep_post = [e for e in spec.endpoints if e.method == "POST"][0]
        self.assertEqual(ep_post.path, "/v1/charges")
        self.assertIsNotNone(ep_post.request_body)

    def test_oversized_input_truncation(self):
        oversized_text = "GET /v1/test\n" + ("A" * 200_000)
        spec = self.parser.parse(oversized_text)
        self.assertLessEqual(len(spec.description), 100_000)

    @patch.dict(os.environ, {"GEMINI_API_KEY": "fake_key"})
    @patch("api_parser.text_parser.generate_content_async", new_callable=AsyncMock)
    def test_async_gemini_execution(self, mock_generate):
        mock_generate.return_value = json.dumps({
            "api_name": "Gemini Parsed API",
            "endpoints": [{"name": "test", "method": "GET", "path": "/test"}]
        })
        spec = asyncio.run(self.parser.parse_async("Unstructured text with no regex match"))
        self.assertEqual(spec.api_name, "Gemini Parsed API")
        self.assertTrue(mock_generate.called)


class TestAPINormalizer(unittest.TestCase):

    def setUp(self):
        self.normalizer = APINormalizer()

    def test_normalize_deduplication_and_defaults(self):
        raw_spec = NormalizedAPISpec(
            api_name="  My API  ",
            base_url="https://api.example.com/",
            endpoints=[
                EndpointSchema(name="search", method="get", path="users"),
                EndpointSchema(name="search", method="get", path="users/detail")
            ]
        )
        norm = self.normalizer.normalize(raw_spec)

        self.assertEqual(norm.api_name, "My API")
        self.assertEqual(norm.base_url, "https://api.example.com")
        self.assertEqual(len(norm.endpoints), 2)
        self.assertEqual(norm.endpoints[0].name, "search")
        self.assertEqual(norm.endpoints[1].name, "search_1")
        self.assertEqual(norm.endpoints[0].path, "/users")


class TestAPIParserOrchestrator(unittest.TestCase):

    def setUp(self):
        self.orchestrator = APIParser()

    @patch("api_parser.fetcher.DocFetcher.fetch", new_callable=AsyncMock)
    def test_graceful_handling_invalid_url_fetch_error(self, mock_fetch):
        mock_fetch.side_effect = DocFetchError("HTTP Error 404: Not Found")

        spec = asyncio.run(self.orchestrator.parse_doc("https://invalid-url.com/docs"))

        self.assertEqual(spec.api_name, "Inaccessible Documentation")
        self.assertIn("404", spec.description)

    @patch("api_parser.fetcher.DocFetcher.fetch", new_callable=AsyncMock)
    def test_successful_end_to_end_parse(self, mock_fetch):
        openapi_sample = json.dumps({
            "openapi": "3.0.0",
            "info": {"title": "Sample Store API"},
            "paths": {
                "/products": {
                    "get": {
                        "summary": "Get Products",
                        "responses": {"200": {"description": "OK"}}
                    }
                }
            }
        })
        mock_fetch.return_value = ("json", openapi_sample)

        spec = asyncio.run(self.orchestrator.parse_doc("https://example.com/swagger.json"))

        self.assertEqual(spec.api_name, "Sample Store API")
        self.assertEqual(len(spec.endpoints), 1)
        self.assertEqual(spec.endpoints[0].method, "GET")
        self.assertEqual(spec.endpoints[0].path, "/products")


if __name__ == "__main__":
    unittest.main()

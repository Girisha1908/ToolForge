import unittest
import asyncio
import json
from api_parser import (
    APIParser,
    NormalizedAPISpec,
    EndpointSchema,
    ParameterSchema,
    RequestBodySchema,
    ResponseSchema,
    AuthenticationSchema,
    PaginationSchema
)


class TestIntegrationContract(unittest.TestCase):
    """
    Integration contract tests verifying that external modules (e.g. connector generation)
    can import and consume NormalizedAPISpec reliably from the api_parser public interface.
    """

    def setUp(self):
        self.parser = APIParser()

    def test_public_imports(self):
        """Verifies top-level exports from api_parser package."""
        self.assertIsNotNone(APIParser)
        self.assertIsNotNone(NormalizedAPISpec)
        self.assertIsNotNone(EndpointSchema)
        self.assertIsNotNone(ParameterSchema)
        self.assertIsNotNone(RequestBodySchema)
        self.assertIsNotNone(ResponseSchema)
        self.assertIsNotNone(AuthenticationSchema)
        self.assertIsNotNone(PaginationSchema)

    def test_contract_guarantees_on_raw_openapi_json(self):
        sample_openapi = json.dumps({
            "openapi": "3.0.0",
            "info": {
                "title": "Contract Test API",
                "version": "1.2.0",
                "description": "Integration test sample"
            },
            "servers": [{"url": "https://api.testcontract.com/v1"}],
            "components": {
                "securitySchemes": {
                    "ApiKeyHeader": {
                        "type": "apiKey",
                        "in": "header",
                        "name": "X-Custom-Token"
                    }
                }
            },
            "paths": {
                "/pets": {
                    "get": {
                        "summary": "List Pets",
                        "parameters": [
                            {"name": "category", "in": "query", "type": "string"}
                        ],
                        "responses": {
                            "200": {"description": "List of pets"}
                        }
                    },
                    "post": {
                        "summary": "Create Pet",
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "name": {"type": "string"}
                                        }
                                    }
                                }
                            }
                        },
                        "responses": {
                            "201": {"description": "Pet created"}
                        }
                    }
                }
            }
        })

        spec: NormalizedAPISpec = self.parser.parse_spec(sample_openapi)

        # Top-level guarantees
        self.assertEqual(spec.api_name, "Contract Test API")
        self.assertEqual(spec.version, "1.2.0")
        self.assertEqual(spec.base_url, "https://api.testcontract.com/v1")
        self.assertEqual(spec.authentication.type, "api_key")
        self.assertEqual(spec.authentication.name, "X-Custom-Token")
        self.assertEqual(len(spec.endpoints), 2)

        # Endpoint guarantees
        get_ep = [e for e in spec.endpoints if e.method == "GET"][0]
        self.assertEqual(get_ep.name, "list_pets")
        self.assertEqual(get_ep.path, "/pets")
        self.assertEqual(len(get_ep.parameters), 1)
        self.assertEqual(get_ep.parameters[0].name, "category")
        self.assertEqual(get_ep.parameters[0].in_location, "query")
        self.assertIsNone(get_ep.request_body)
        self.assertEqual(get_ep.responses[0].status_code, 200)

        post_ep = [e for e in spec.endpoints if e.method == "POST"][0]
        self.assertEqual(post_ep.name, "create_pet")
        self.assertEqual(post_ep.path, "/pets")
        self.assertIsNotNone(post_ep.request_body)
        self.assertEqual(post_ep.request_body.content_type, "application/json")
        self.assertEqual(post_ep.request_body.schema_definition["properties"]["name"]["type"], "string")
        self.assertEqual(post_ep.responses[0].status_code, 201)

    def test_json_serializability(self):
        """Verifies that NormalizedAPISpec serializes cleanly to JSON dictionary for downstream consumption."""
        sample_doc = "GET /v1/health\nResponse 200 OK"
        spec: NormalizedAPISpec = self.parser.parse_spec(sample_doc)
        
        # Convert to dictionary and dump to JSON string
        spec_dict = spec.model_dump()
        json_repr = json.dumps(spec_dict)
        
        self.assertIsInstance(json_repr, str)
        self.assertIn("health", json_repr)


if __name__ == "__main__":
    unittest.main()

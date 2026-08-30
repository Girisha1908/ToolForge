import os
import json
import re
import logging
import asyncio
from typing import List, Dict, Any, Optional
from api_parser.schemas import NormalizedAPISpec, EndpointSchema
from tool_generator.schemas import (
    GeneratedConnector,
    ToolDefinition,
    ToolParameter
)

logger = logging.getLogger("ToolForge.ToolGenerator")


class GeminiService:
    """Isolated LLM Service Abstraction for generating agent tool metadata via Gemini."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None, timeout: float = 10.0):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self.model = model or os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
        self.timeout = timeout

    def is_available(self) -> bool:
        return bool(self.api_key)

    async def generate_tool_enrichments(self, endpoints_summary: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Sends endpoints to Gemini to enrich agent-ready tool names, descriptions, and parameter documentation.
        Enforces strict structured JSON array response.
        Raises an exception if Gemini fails, times out, or returns invalid structure.
        """
        if not self.is_available():
            raise ValueError("GEMINI_API_KEY is missing or not configured.")

        prompt = f"""
You are an expert API Tool Generator. Enhance the tool names, descriptions, and parameter documentation for these API endpoints to make them agent-ready.
CRITICAL CONSTRAINTS:
1. Do NOT invent new endpoints.
2. Do NOT change HTTP methods or paths under any circumstance.
3. Return a JSON array matching the EXACT same number of endpoints ({len(endpoints_summary)}) in the exact same order.

Input Endpoints:
{json.dumps(endpoints_summary, indent=2)}

Return ONLY a valid JSON array of objects with the exact schema:
[
  {{
    "name": "lowercase_snake_case_name",
    "description": "Clear agent-friendly description of what the tool accomplishes",
    "method": "EXACT_INPUT_METHOD",
    "path": "EXACT_INPUT_PATH",
    "parameters": [
      {{
        "name": "param_name",
        "description": "Clear parameter description",
        "type": "string|integer|boolean|array",
        "in_location": "query|path|header|body",
        "required": true
      }}
    ]
  }}
]
"""
        def _sync_call():
            from google import genai
            client = genai.Client(api_key=self.api_key)
            response = client.models.generate_content(
                model=self.model,
                contents=prompt
            )
            return response.text.strip()

        # Run via thread pool with strict timeout
        try:
            response_text = await asyncio.wait_for(asyncio.to_thread(_sync_call), timeout=self.timeout)
            if response_text.startswith("```"):
                response_text = re.sub(r'^```[a-z]*\n', '', response_text)
                response_text = re.sub(r'\n```$', '', response_text)

            parsed = json.loads(response_text)
            if not isinstance(parsed, list):
                raise ValueError("Gemini output is not a JSON list.")
            return parsed
        except asyncio.TimeoutError:
            logger.warning(f"Gemini generation timed out after {self.timeout}s.")
            raise
        except Exception as exc:
            logger.warning(f"Gemini service generation failed: {exc}")
            raise


class ConnectorGenerator:
    """
    Main generator class that converts a NormalizedAPISpec into a GeneratedConnector
    containing validated ToolDefinitions for every endpoint.
    Includes automatic deterministic fallback if Gemini fails or produces invalid output.
    """

    def __init__(self, gemini_service: Optional[GeminiService] = None):
        self.gemini_service = gemini_service or GeminiService()

    def generate(self, spec: NormalizedAPISpec) -> GeneratedConnector:
        """Synchronous wrapper for generate_async."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                return self._deterministic_generate(spec)
            else:
                return loop.run_until_complete(self.generate_async(spec))
        except Exception:
            return self._deterministic_generate(spec)

    async def generate_async(self, spec: NormalizedAPISpec) -> GeneratedConnector:
        """
        Converts NormalizedAPISpec endpoints into agent-ready ToolDefinitions.
        Attempts Gemini enrichment first; if Gemini fails or violates constraints,
        falls back cleanly to deterministic generation.
        """
        if not spec.endpoints:
            return GeneratedConnector(
                api_name=spec.api_name,
                version=spec.version or "1.0.0",
                base_url=spec.base_url,
                description=spec.description,
                tools=[]
            )

        # Attempt Gemini-powered connector generation
        if self.gemini_service.is_available():
            try:
                connector = await self._gemini_generate(spec)
                if connector and len(connector.tools) == len(spec.endpoints):
                    return connector
            except Exception as exc:
                logger.info(f"Gemini generation path failed/rejected ({exc}); falling back to deterministic generation.")

        # Deterministic fallback
        return self._deterministic_generate(spec)

    async def _gemini_generate(self, spec: NormalizedAPISpec) -> GeneratedConnector:
        """Helper to request and strictly validate Gemini tool enrichments."""
        summaries = []
        for ep in spec.endpoints:
            summaries.append({
                "name": ep.name,
                "description": ep.description or ep.summary or f"Execute {ep.method} {ep.path}",
                "method": ep.method.upper(),
                "path": ep.path,
                "parameters": [p.model_dump() for p in ep.parameters]
            })

        enriched_list = await self.gemini_service.generate_tool_enrichments(summaries)

        # Constraint Check 1: Must match exact endpoint count
        if len(enriched_list) != len(spec.endpoints):
            raise ValueError(f"Gemini endpoint count mismatch: expected {len(spec.endpoints)}, got {len(enriched_list)}.")

        tools: List[ToolDefinition] = []
        seen_names = set()

        # Constraint Check 2: Must match exact method and path for each corresponding endpoint
        for idx, ep in enumerate(spec.endpoints):
            enriched = enriched_list[idx]
            if not isinstance(enriched, dict):
                raise ValueError("Gemini tool enrichment item is not a dictionary.")

            gen_method = (enriched.get("method") or "").upper()
            gen_path = enriched.get("path") or ""

            if gen_method != ep.method.upper():
                raise ValueError(f"Gemini changed HTTP method for endpoint {ep.path}: expected {ep.method}, got {gen_method}.")

            if gen_path.rstrip('/') != ep.path.rstrip('/'):
                raise ValueError(f"Gemini changed path for endpoint {ep.name}: expected {ep.path}, got {gen_path}.")

            # Sanitize and ensure unique tool name
            raw_name = enriched.get("name") or ep.name
            tool_name = self._sanitize_tool_name(raw_name)
            
            counter = 1
            unique_name = tool_name
            while unique_name in seen_names:
                unique_name = f"{tool_name}_{counter}"
                counter += 1
            seen_names.add(unique_name)

            # Build parameters combining input spec and Gemini parameter descriptions
            tool_params: List[ToolParameter] = []
            enriched_params = enriched.get("parameters", [])
            param_desc_map = {}
            if isinstance(enriched_params, list):
                for p in enriched_params:
                    if isinstance(p, dict) and "name" in p:
                        param_desc_map[p["name"]] = p.get("description")

            for p in ep.parameters:
                desc = param_desc_map.get(p.name) or p.description
                tool_params.append(ToolParameter(
                    name=p.name,
                    type=p.type,
                    in_location=p.in_location,
                    required=p.required,
                    description=desc,
                    default=p.default,
                    enum=p.enum
                ))

            req_body_schema = ep.request_body.schema_definition if ep.request_body else None
            resp_schema = ep.responses[0].schema_definition if ep.responses else None
            description = enriched.get("description") or ep.description or ep.summary or f"Execute {ep.method} {ep.path}"

            tool_def = ToolDefinition(
                id=unique_name,
                name=unique_name,
                description=description,
                method=ep.method.upper(),
                path=ep.path,
                base_url=spec.base_url,
                parameters=tool_params,
                request_body_schema=req_body_schema,
                expected_response_schema=resp_schema,
                authentication=spec.authentication,
                error_handling=ep.errors
            )

            # Validate each tool definition through Pydantic
            validated_tool = ToolDefinition.model_validate(tool_def.model_dump())
            tools.append(validated_tool)

        return GeneratedConnector(
            api_name=spec.api_name,
            version=spec.version or "1.0.0",
            base_url=spec.base_url,
            description=spec.description,
            tools=tools
        )

    def _deterministic_generate(self, spec: NormalizedAPISpec) -> GeneratedConnector:
        """Deterministic generator fallback without async LLM enrichment."""
        tools: List[ToolDefinition] = []
        seen_names = set()

        for ep in spec.endpoints:
            tool_name = self._sanitize_tool_name(ep.name)
            counter = 1
            unique_name = tool_name
            while unique_name in seen_names:
                unique_name = f"{tool_name}_{counter}"
                counter += 1
            seen_names.add(unique_name)

            tool_params = [
                ToolParameter(
                    name=p.name,
                    type=p.type,
                    in_location=p.in_location,
                    required=p.required,
                    description=p.description,
                    default=p.default,
                    enum=p.enum
                )
                for p in ep.parameters
            ]

            req_body_schema = ep.request_body.schema_definition if ep.request_body else None
            resp_schema = ep.responses[0].schema_definition if ep.responses else None

            tool_def = ToolDefinition(
                id=unique_name,
                name=unique_name,
                description=ep.description or ep.summary or f"Execute {ep.method} {ep.path}",
                method=ep.method.upper(),
                path=ep.path,
                base_url=spec.base_url,
                parameters=tool_params,
                request_body_schema=req_body_schema,
                expected_response_schema=resp_schema,
                authentication=spec.authentication,
                error_handling=ep.errors
            )
            tools.append(ToolDefinition.model_validate(tool_def.model_dump()))

        return GeneratedConnector(
            api_name=spec.api_name,
            version=spec.version or "1.0.0",
            base_url=spec.base_url,
            description=spec.description,
            tools=tools
        )

    @staticmethod
    def _sanitize_tool_name(name: str) -> str:
        clean = re.sub(r'[^a-zA-Z0-9_]', '_', name.lower()).strip('_')
        clean = re.sub(r'_+', '_', clean)
        return clean or "tool"

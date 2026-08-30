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

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")

    def is_available(self) -> bool:
        return bool(self.api_key)

    async def generate_tool_descriptions(self, endpoints_summary: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Sends endpoints to Gemini to enrich agent-ready descriptions and parameter documentation.
        Implements retries for malformed LLM responses.
        """
        if not self.is_available():
            return endpoints_summary

        prompt = f"""
You are an expert API Tool Generator. Enhance the descriptions and parameter hints for these API endpoints to make them agent-ready.
Do NOT invent new endpoints, change HTTP methods, or modify paths. Return a JSON array matching the exact same number of endpoints in the same order.

Input Endpoints:
{json.dumps(endpoints_summary, indent=2)}

Return ONLY valid JSON array with objects containing:
- name: string (lowercase_snake_case)
- description: string (clear description of what the tool accomplishes)
- parameters: array of {{ name, description, type, required }}
"""
        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                def _sync_call():
                    from google import genai
                    client = genai.Client(api_key=self.api_key)
                    response = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=prompt
                    )
                    return response.text.strip()

                response_text = await asyncio.to_thread(_sync_call)
                if response_text.startswith("```"):
                    response_text = re.sub(r'^```[a-z]*\n', '', response_text)
                    response_text = re.sub(r'\n```$', '', response_text)

                parsed = json.loads(response_text)
                if isinstance(parsed, list) and len(parsed) == len(endpoints_summary):
                    return parsed
            except Exception as exc:
                logger.warning(f"Gemini generation attempt {attempt + 1} failed: {exc}")
                if attempt == max_retries:
                    logger.error("Gemini retries exhausted, falling back to deterministic generation.")

        return endpoints_summary


class ConnectorGenerator:
    """
    Main generator class that converts a NormalizedAPISpec into a GeneratedConnector
    containing validated ToolDefinitions for every endpoint.
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
        Strictly enforces 1:1 correspondence with the input NormalizedAPISpec.
        """
        tools: List[ToolDefinition] = []
        seen_names = set()

        # Prepare summary for potential LLM enrichment
        summaries = []
        for ep in spec.endpoints:
            summaries.append({
                "name": ep.name,
                "description": ep.description or ep.summary,
                "method": ep.method,
                "path": ep.path,
                "parameters": [p.model_dump() for p in ep.parameters]
            })

        # Try Gemini enrichment if available
        enriched_summaries = summaries
        if self.gemini_service.is_available():
            enriched_summaries = await self.gemini_service.generate_tool_descriptions(summaries)

        # Build validated ToolDefinition for every endpoint in the NormalizedAPISpec
        for idx, ep in enumerate(spec.endpoints):
            enriched = enriched_summaries[idx] if idx < len(enriched_summaries) else {}
            
            # Ensure unique snake_case tool name
            raw_name = enriched.get("name") or ep.name
            tool_name = self._sanitize_tool_name(raw_name)
            
            counter = 1
            unique_name = tool_name
            while unique_name in seen_names:
                unique_name = f"{tool_name}_{counter}"
                counter += 1
            seen_names.add(unique_name)

            # Build parameters
            tool_params: List[ToolParameter] = []
            for p in ep.parameters:
                tool_params.append(ToolParameter(
                    name=p.name,
                    type=p.type,
                    in_location=p.in_location,
                    required=p.required,
                    description=p.description,
                    default=p.default,
                    enum=p.enum
                ))

            # Request body schema
            req_body_schema = None
            if ep.request_body and ep.request_body.schema_definition:
                req_body_schema = ep.request_body.schema_definition

            # Expected response schema
            resp_schema = None
            if ep.responses and ep.responses[0].schema_definition:
                resp_schema = ep.responses[0].schema_definition

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

            # Validate generated ToolDefinition with Pydantic
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

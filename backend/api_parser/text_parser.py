import re
import os
import json
import asyncio
from typing import List, Dict, Any, Optional
from api_parser.schemas import (
    NormalizedAPISpec,
    EndpointSchema,
    ParameterSchema,
    RequestBodySchema,
    ResponseSchema,
    ErrorFormatSchema,
    AuthenticationSchema,
    PaginationSchema
)

class TextDocParser:
    """Parses plain text / extracted HTML documentation using pattern matching and optional LLM fallback."""

    HTTP_METHODS = ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]
    MAX_TEXT_SIZE = 100_000  # Enforce 100k character limit on input

    async def parse_async(self, text: str, source_url: Optional[str] = None) -> NormalizedAPISpec:
        """Asynchronously parses documentation text using pattern matching first, then LLM if available."""
        # Truncate text safely if oversized
        safe_text = text[:self.MAX_TEXT_SIZE]

        # 1. First try deterministic pattern extraction
        spec = self._pattern_based_parse(safe_text, source_url)

        # 2. If pattern extraction found no endpoints, try async LLM fallback if GEMINI_API_KEY is available
        if not spec.endpoints and os.environ.get("GEMINI_API_KEY"):
            llm_spec = await self._llm_parse_async(safe_text, source_url)
            if llm_spec and llm_spec.endpoints:
                return llm_spec

        return spec

    def parse(self, text: str, source_url: Optional[str] = None) -> NormalizedAPISpec:
        """Synchronous wrapper for parse_async."""
        safe_text = text[:self.MAX_TEXT_SIZE]
        spec = self._pattern_based_parse(safe_text, source_url)
        if not spec.endpoints and os.environ.get("GEMINI_API_KEY"):
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    return spec
                else:
                    return loop.run_until_complete(self.parse_async(text, source_url))
            except Exception:
                return spec
        return spec

    def _pattern_based_parse(self, text: str, source_url: Optional[str] = None) -> NormalizedAPISpec:
        api_name = self._extract_api_name(text)
        auth = self._extract_authentication(text)
        endpoints = self._extract_endpoints(text)
        error_formats = self._extract_global_errors(text)
        constraints = self._extract_constraints(text)

        return NormalizedAPISpec(
            api_name=api_name,
            version="1.0.0",
            description=text[:300] if len(text) > 300 else text,
            authentication=auth,
            endpoints=endpoints,
            error_formats=error_formats,
            global_constraints=constraints,
            source_url=source_url
        )

    def _extract_api_name(self, text: str) -> str:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if lines:
            first = lines[0]
            if len(first) < 50 and not any(m in first.upper() for m in self.HTTP_METHODS):
                return first.strip('#').strip()
        return "Unspecified API"

    def _extract_authentication(self, text: str) -> AuthenticationSchema:
        text_lower = text.lower()
        if "bearer" in text_lower or "authorization: bearer" in text_lower:
            return AuthenticationSchema(
                type="bearer",
                in_location="header",
                name="Authorization",
                scheme="Bearer",
                description="Bearer token authentication"
            )
        if "api_key" in text_lower or "apikey" in text_lower or "x-api-key" in text_lower:
            name = "X-API-Key"
            if "x-api-key" in text_lower:
                name = "X-API-Key"
            elif "api-key" in text_lower:
                name = "api-key"
            return AuthenticationSchema(
                type="api_key",
                in_location="header",
                name=name,
                description="API key header authentication"
            )
        if "basic auth" in text_lower or "authorization: basic" in text_lower:
            return AuthenticationSchema(
                type="basic",
                in_location="header",
                name="Authorization",
                scheme="Basic",
                description="Basic HTTP authentication"
            )
        return AuthenticationSchema(type="none")

    def _extract_endpoints(self, text: str) -> List[EndpointSchema]:
        endpoints: List[EndpointSchema] = []

        # Regular expression matching "METHOD /path/to/resource"
        # e.g., "GET /v1/users", "POST /api/v1/users/{id}"
        endpoint_pattern = re.compile(
            r'\b(GET|POST|PUT|DELETE|PATCH)\s+(/[a-zA-Z0-9_\-\{\}/:\.]+)',
            re.IGNORECASE
        )

        matches = list(endpoint_pattern.finditer(text))
        
        for i, match in enumerate(matches):
            method = match.group(1).upper()
            path = match.group(2)
            
            # Context window between this match and the next match or end of text (cap context size to 5,000 chars)
            start_idx = match.start()
            end_idx = matches[i+1].start() if i + 1 < len(matches) else len(text)
            context = text[start_idx:min(end_idx, start_idx + 5000)]

            parameters = self._extract_parameters_from_context(context, path)
            req_body = self._extract_request_body_from_context(context, method)
            responses = self._extract_responses_from_context(context)
            pagination = self._extract_pagination_from_context(context, parameters)

            name = self._generate_endpoint_name(method, path)

            endpoints.append(EndpointSchema(
                name=name,
                method=method,
                path=path,
                summary=f"{method} {path}",
                description=context[:200].strip(),
                parameters=parameters,
                request_body=req_body,
                responses=responses,
                pagination=pagination
            ))

        return endpoints

    def _extract_parameters_from_context(self, context: str, path: str) -> List[ParameterSchema]:
        params: List[ParameterSchema] = []
        
        # 1. Path parameters from path e.g. /users/{id} or /users/:id
        path_params = re.findall(r'\{([a-zA-Z0-9_]+)\}|:([a-zA-Z0-9_]+)', path)
        for p_tuple in path_params:
            p_name = p_tuple[0] or p_tuple[1]
            if p_name:
                params.append(ParameterSchema(
                    name=p_name,
                    in_location="path",
                    type="string",
                    required=True,
                    description=f"Path parameter {p_name}"
                ))

        # 2. Query / header parameters from text patterns like "page (integer, optional)"
        param_lines = re.findall(r'([a-zA-Z0-9_]+)\s*\((string|integer|int|boolean|bool|array|number)\s*,?\s*(required|optional)?\)', context, re.IGNORECASE)
        existing_names = {p.name for p in params}

        for name, ptype, req in param_lines:
            if name not in existing_names:
                params.append(ParameterSchema(
                    name=name,
                    in_location="query",
                    type=ptype.lower(),
                    required=(req.lower() == "required" if req else False),
                    description=f"Parameter {name}"
                ))
                existing_names.add(name)

        return params

    def _extract_request_body_from_context(self, context: str, method: str) -> Optional[RequestBodySchema]:
        if method in ["GET", "DELETE"]:
            return None

        if "body" in context.lower() or "json" in context.lower() or method in ["POST", "PUT", "PATCH"]:
            # Check for JSON block in context
            json_match = re.search(r'\{[\s\S]*?\}', context)
            schema_def = {}
            if json_match:
                try:
                    schema_def = json.loads(json_match.group(0))
                except Exception:
                    schema_def = {"raw_sample": json_match.group(0)}

            return RequestBodySchema(
                content_type="application/json",
                schema_definition=schema_def if isinstance(schema_def, dict) else {},
                required=True,
                description="Request body content"
            )

        return None

    def _extract_responses_from_context(self, context: str) -> List[ResponseSchema]:
        responses = []
        status_matches = re.findall(r'\b(200|201|204|400|401|403|404|500)\b', context)
        
        for code_str in set(status_matches):
            code = int(code_str)
            if code < 400:
                responses.append(ResponseSchema(
                    status_code=code,
                    description=f"Response status {code}"
                ))
        
        if not responses:
            responses.append(ResponseSchema(status_code=200, description="Successful operation"))

        return responses

    def _extract_pagination_from_context(self, context: str, parameters: List[ParameterSchema]) -> Optional[PaginationSchema]:
        context_lower = context.lower()
        param_names = {p.name.lower(): p.name for p in parameters}

        if "cursor" in context_lower or "next_token" in param_names:
            return PaginationSchema(type="cursor", cursor_param=param_names.get("cursor") or param_names.get("next_token"))
        if "page" in param_names or "per_page" in param_names:
            return PaginationSchema(type="page_number", page_param=param_names.get("page"), limit_param=param_names.get("per_page") or param_names.get("limit"))
        if "offset" in param_names or "limit" in param_names:
            return PaginationSchema(type="offset_limit", page_param=param_names.get("offset"), limit_param=param_names.get("limit"))

        return None

    def _extract_global_errors(self, text: str) -> List[ErrorFormatSchema]:
        errors = []
        for code in [400, 401, 403, 404, 429, 500]:
            if str(code) in text:
                errors.append(ErrorFormatSchema(
                    status_code=code,
                    description=f"Standard status error {code}"
                ))
        return errors

    def _extract_constraints(self, text: str) -> List[str]:
        constraints = []
        rate_limit_match = re.search(r'(\d+)\s*(requests|calls)\s*per\s*(minute|hour|second|day)', text, re.IGNORECASE)
        if rate_limit_match:
            constraints.append(f"Rate limit: {rate_limit_match.group(0)}")
        return constraints

    def _generate_endpoint_name(self, method: str, path: str) -> str:
        clean_path = re.sub(r'\{[^}]+\}|:[a-zA-Z0-9_]+', '', path)
        parts = [p for p in clean_path.split('/') if p]
        suffix = "_".join(parts) if parts else "root"
        return re.sub(r'[^a-zA-Z0-9_]', '_', f"{method.lower()}_{suffix}").strip('_')

    async def _llm_parse_async(self, text: str, source_url: Optional[str]) -> Optional[NormalizedAPISpec]:
        """Async Gemini LLM execution using asyncio.to_thread / async genai client to prevent event loop blocking."""
        def _sync_call():
            try:
                from google import genai
                client = genai.Client()
                prompt = f"""
Analyze the following API documentation text and extract structured API details.
Return ONLY valid JSON with this exact structure:
{{
  "api_name": "API Name",
  "version": "1.0.0",
  "description": "Brief description",
  "authentication": {{
    "type": "bearer|api_key|basic|none",
    "in_location": "header|query",
    "name": "Header or param name",
    "scheme": "Bearer|Basic|null"
  }},
  "endpoints": [
    {{
      "name": "snake_case_name",
      "summary": "Summary",
      "description": "Description",
      "method": "GET|POST|PUT|DELETE|PATCH",
      "path": "/endpoint/path",
      "parameters": [
        {{
          "name": "param_name",
          "in_location": "query|path|header",
          "type": "string|integer|boolean",
          "required": true|false,
          "description": "desc"
        }}
      ],
      "responses": [
        {{
          "status_code": 200,
          "description": "desc"
        }}
      ]
    }}
  ]
}}

API Documentation Content:
{text[:4000]}
"""
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt
                )

                response_text = response.text.strip()
                if response_text.startswith("```"):
                    response_text = re.sub(r'^```[a-z]*\n', '', response_text)
                    response_text = re.sub(r'\n```$', '', response_text)

                data = json.loads(response_text)
                return NormalizedAPISpec.model_validate(data)
            except Exception:
                return None

        return await asyncio.to_thread(_sync_call)

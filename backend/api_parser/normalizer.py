import re
from typing import Dict, Any, List
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


class APINormalizer:
    """Normalizes raw parsed data or partial specification objects into a standardized NormalizedAPISpec."""

    def normalize(self, spec: NormalizedAPISpec) -> NormalizedAPISpec:
        """Cleans, formats, and validates the NormalizedAPISpec instance."""
        
        # 1. Clean API name
        api_name = spec.api_name.strip() if spec.api_name else "Example API"

        # 2. Clean Base URL
        base_url = spec.base_url.rstrip("/") if spec.base_url else None
        if base_url and spec.source_url and not (base_url.startswith("http://") or base_url.startswith("https://")):
            from urllib.parse import urljoin
            base_url = urljoin(spec.source_url, base_url).rstrip("/")
        elif not base_url and spec.source_url:
            from urllib.parse import urlparse
            p = urlparse(spec.source_url)
            base_url = f"{p.scheme}://{p.netloc}"

        # 3. Clean Authentication
        auth = self._normalize_auth(spec.authentication)

        # 4. Clean Endpoints
        normalized_endpoints: List[EndpointSchema] = []
        seen_names = set()

        for ep in spec.endpoints:
            norm_ep = self._normalize_endpoint(ep, seen_names)
            normalized_endpoints.append(norm_ep)

        # 5. Clean Global Errors
        global_errors = self._normalize_errors(spec.error_formats)

        return NormalizedAPISpec(
            api_name=api_name,
            version=spec.version or "1.0.0",
            base_url=base_url,
            description=spec.description or "",
            authentication=auth,
            endpoints=normalized_endpoints,
            error_formats=global_errors,
            global_constraints=list(set(spec.global_constraints or [])),
            source_url=spec.source_url
        )

    def _normalize_auth(self, auth: AuthenticationSchema) -> AuthenticationSchema:
        auth_type = (auth.type or "none").lower()
        if auth_type not in ["bearer", "api_key", "basic", "oauth2", "none"]:
            auth_type = "none"

        in_loc = (auth.in_location or "").lower()
        if in_loc not in ["header", "query", "cookie"]:
            in_loc = "header" if auth_type in ["bearer", "basic", "oauth2", "api_key"] else None

        name = auth.name
        if not name:
            if auth_type in ["bearer", "basic", "oauth2"]:
                name = "Authorization"
            elif auth_type == "api_key":
                name = "X-API-Key"

        scheme = auth.scheme
        if not scheme:
            if auth_type == "bearer":
                scheme = "Bearer"
            elif auth_type == "basic":
                scheme = "Basic"

        return AuthenticationSchema(
            type=auth_type,
            in_location=in_loc,
            name=name,
            scheme=scheme,
            description=auth.description
        )

    def _normalize_endpoint(self, ep: EndpointSchema, seen_names: set) -> EndpointSchema:
        method = ep.method.upper().strip()
        if method not in ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]:
            method = "GET"

        path = ep.path.strip()
        if not path.startswith("/"):
            path = "/" + path

        # Ensure valid snake_case endpoint name
        base_name = re.sub(r'[^a-zA-Z0-9_]', '_', ep.name.lower()).strip('_')
        base_name = re.sub(r'_+', '_', base_name)
        if not base_name:
            base_name = f"{method.lower()}_endpoint"

        unique_name = base_name
        counter = 1
        while unique_name in seen_names:
            unique_name = f"{base_name}_{counter}"
            counter += 1
        seen_names.add(unique_name)

        # Normalize parameters
        norm_params: List[ParameterSchema] = []
        for p in ep.parameters:
            p_in = (p.in_location or "query").lower()
            if p_in not in ["query", "path", "header", "cookie"]:
                p_in = "query"
            
            norm_params.append(ParameterSchema(
                name=p.name.strip(),
                in_location=p_in,
                type=p.type.lower() if p.type else "string",
                required=p.required,
                description=p.description,
                default=p.default,
                enum=p.enum
            ))

        # Normalize request body
        norm_body = ep.request_body
        if norm_body:
            norm_body = RequestBodySchema(
                content_type=norm_body.content_type or "application/json",
                schema_definition=norm_body.schema_definition or {},
                required=norm_body.required,
                description=norm_body.description
            )

        # Normalize responses
        norm_responses: List[ResponseSchema] = []
        if ep.responses:
            for r in ep.responses:
                norm_responses.append(ResponseSchema(
                    status_code=r.status_code if isinstance(r.status_code, int) else 200,
                    description=r.description or "Response",
                    content_type=r.content_type or "application/json",
                    schema_definition=r.schema_definition or {}
                ))
        else:
            norm_responses.append(ResponseSchema(status_code=200, description="Successful Operation"))

        # Normalize errors
        norm_errors = self._normalize_errors(ep.errors)

        return EndpointSchema(
            name=unique_name,
            summary=ep.summary or f"{method} {path}",
            description=ep.description or "",
            method=method,
            path=path,
            parameters=norm_params,
            request_body=norm_body,
            responses=norm_responses,
            errors=norm_errors,
            pagination=ep.pagination,
            constraints=list(set(ep.constraints or []))
        )

    def _normalize_errors(self, errors: List[ErrorFormatSchema]) -> List[ErrorFormatSchema]:
        norm_errors: List[ErrorFormatSchema] = []
        seen_codes = set()

        for err in errors:
            code = err.status_code if isinstance(err.status_code, int) else 400
            if code not in seen_codes:
                seen_codes.add(code)
                norm_errors.append(ErrorFormatSchema(
                    status_code=code,
                    code=err.code or str(code),
                    message=err.message or f"HTTP {code} error",
                    description=err.description or "",
                    schema_definition=err.schema_definition or {}
                ))

        return norm_errors

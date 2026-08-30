import json
import yaml
import re
from typing import Dict, Any, List, Optional, Set
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


class StructuredSpecParser:
    """Parses OpenAPI 2.0 (Swagger), OpenAPI 3.0/3.1, and Postman Collection v2/v2.1 formats."""

    def can_parse(self, content: str, content_type: str) -> bool:
        """Determines if the content is structured JSON/YAML spec (OpenAPI/Swagger/Postman)."""
        data = self._load_data(content)
        if not isinstance(data, dict):
            return False
        
        return any(key in data for key in ["openapi", "swagger", "paths", "info", "item"])

    def parse(self, content: str, source_url: Optional[str] = None) -> NormalizedAPISpec:
        data = self._load_data(content)
        if not isinstance(data, dict):
            raise ValueError("Content is not a valid JSON/YAML object.")

        # Postman collection check
        if "item" in data and ("info" in data and "schema" in str(data.get("info"))):
            return self._parse_postman(data, source_url)
        
        # OpenAPI / Swagger check
        if "openapi" in data or "swagger" in data or "paths" in data:
            # Dereference local $ref before parsing
            dereferenced_data = self.dereference_spec(data)
            return self._parse_openapi(dereferenced_data, source_url)

        raise ValueError("Unrecognized structured API format.")

    def dereference_spec(self, root_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recursively resolves local JSON pointers (e.g., '#/components/schemas/User' or '#/definitions/User').
        Safely handles nested and circular references.
        """

        def resolve_pointer(ref_path: str) -> Optional[Any]:
            if not ref_path.startswith("#/"):
                return None  # Ignore external or non-local refs
            parts = ref_path.lstrip("#/").split("/")
            curr = root_data
            for part in parts:
                # Unescape JSON pointer syntax (~1 -> /, ~0 -> ~)
                part = part.replace("~1", "/").replace("~0", "~")
                if isinstance(curr, dict) and part in curr:
                    curr = curr[part]
                else:
                    return None
            return curr

        def _deref_node(node: Any, visited_refs: Set[str]) -> Any:
            if isinstance(node, dict):
                if "$ref" in node and isinstance(node["$ref"], str):
                    ref_str = node["$ref"]
                    if ref_str in visited_refs:
                        # Circular reference detected! Return simplified reference stub to avoid infinite loop
                        clean_name = ref_str.split("/")[-1]
                        return {
                            "type": "object",
                            "description": f"Circular reference to {clean_name}",
                            "properties": {}
                        }

                    resolved_target = resolve_pointer(ref_str)
                    if resolved_target is not None:
                        # Merge sibling properties alongside $ref
                        siblings = {k: v for k, v in node.items() if k != "$ref"}
                        next_visited = visited_refs | {ref_str}
                        resolved_deref = _deref_node(resolved_target, next_visited)

                        if isinstance(resolved_deref, dict):
                            # Sibling values override resolved values, or join them
                            merged = {**resolved_deref, **siblings}
                            return merged
                        return resolved_deref

                # Recursively dereference dictionary values
                return {k: _deref_node(v, visited_refs) for k, v in node.items()}

            elif isinstance(node, list):
                return [_deref_node(item, visited_refs) for item in node]

            return node

        return _deref_node(root_data, set())

    def _load_data(self, content: str) -> Optional[Dict[str, Any]]:
        content_clean = content.strip()
        # Try JSON first
        if content_clean.startswith("{") or content_clean.startswith("["):
            try:
                return json.loads(content_clean)
            except Exception:
                pass
        
        # Try YAML
        try:
            parsed = yaml.safe_load(content_clean)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass

        return None

    def _parse_openapi(self, data: Dict[str, Any], source_url: Optional[str]) -> NormalizedAPISpec:
        info = data.get("info", {})
        api_name = info.get("title", "Parsed API")
        version = info.get("version", "1.0.0")
        description = info.get("description", "")

        # Extract base_url
        base_url = None
        servers = data.get("servers", [])
        if servers and isinstance(servers, list) and len(servers) > 0:
            base_url = servers[0].get("url")
        elif "host" in data:
            schemes = data.get("schemes", ["https"])
            base_path = data.get("basePath", "")
            base_url = f"{schemes[0]}://{data['host']}{base_path}"

        components = data.get("components", {})
        definitions = data.get("definitions", {})

        auth_spec = self._extract_openapi_auth(data)
        endpoints: List[EndpointSchema] = []
        global_errors: List[ErrorFormatSchema] = []

        paths = data.get("paths", {})
        if isinstance(paths, dict):
            for path_str, path_item in paths.items():
                if not isinstance(path_item, dict):
                    continue
                
                # Path-level parameters
                path_level_params = path_item.get("parameters", [])

                for method in ["get", "post", "put", "delete", "patch", "head", "options"]:
                    if method not in path_item or not isinstance(path_item[method], dict):
                        continue
                    
                    op = path_item[method]
                    endpoint = self._parse_openapi_operation(
                        method=method.upper(),
                        path=path_str,
                        op=op,
                        path_params=path_level_params,
                        components=components,
                        definitions=definitions
                    )
                    endpoints.append(endpoint)

        return NormalizedAPISpec(
            api_name=api_name,
            version=version,
            base_url=base_url,
            description=description,
            authentication=auth_spec,
            endpoints=endpoints,
            error_formats=global_errors,
            source_url=source_url
        )

    def _extract_openapi_auth(self, data: Dict[str, Any]) -> AuthenticationSchema:
        auth_schema = AuthenticationSchema(type="none")
        
        # OpenAPI 3.x
        security_schemes = data.get("components", {}).get("securitySchemes", {})
        # Swagger 2.0
        if not security_schemes:
            security_schemes = data.get("securityDefinitions", {})

        if not security_schemes or not isinstance(security_schemes, dict):
            return auth_schema

        # Take first security scheme found
        for scheme_name, scheme_def in security_schemes.items():
            if not isinstance(scheme_def, dict):
                continue
            
            stype = scheme_def.get("type", "").lower()

            if stype == "http":
                scheme = scheme_def.get("scheme", "").lower()
                if scheme == "bearer":
                    return AuthenticationSchema(
                        type="bearer",
                        in_location="header",
                        name="Authorization",
                        scheme="Bearer",
                        description=scheme_def.get("description")
                    )
                elif scheme == "basic":
                    return AuthenticationSchema(
                        type="basic",
                        in_location="header",
                        name="Authorization",
                        scheme="Basic",
                        description=scheme_def.get("description")
                    )
            elif stype in ["apikey", "api_key"]:
                return AuthenticationSchema(
                    type="api_key",
                    in_location=scheme_def.get("in", "header"),
                    name=scheme_def.get("name", "X-API-Key"),
                    description=scheme_def.get("description")
                )
            elif stype in ["oauth2", "openIdConnect"]:
                return AuthenticationSchema(
                    type="oauth2",
                    in_location="header",
                    name="Authorization",
                    scheme="Bearer",
                    description=scheme_def.get("description")
                )

        return auth_schema

    def _parse_openapi_operation(
        self,
        method: str,
        path: str,
        op: Dict[str, Any],
        path_params: List[Any],
        components: Dict[str, Any],
        definitions: Dict[str, Any]
    ) -> EndpointSchema:
        operation_id = op.get("operationId")
        summary = op.get("summary", "")
        description = op.get("description", "")
        
        name = operation_id or self._generate_endpoint_name(method, path, summary)

        # Combine path-level parameters and operation-level parameters
        raw_params = (path_params if isinstance(path_params, list) else []) + (op.get("parameters", []) if isinstance(op.get("parameters"), list) else [])
        
        parameters: List[ParameterSchema] = []
        req_body: Optional[RequestBodySchema] = None

        for p in raw_params:
            if not isinstance(p, dict):
                continue
            
            p_in = p.get("in", "query")
            if p_in == "body":
                # Swagger 2.0 body param
                req_body = RequestBodySchema(
                    content_type="application/json",
                    schema_definition=p.get("schema", {}),
                    required=p.get("required", True),
                    description=p.get("description")
                )
            else:
                schema_info = p.get("schema", {})
                param_type = p.get("type") or schema_info.get("type", "string")
                parameters.append(ParameterSchema(
                    name=p.get("name", ""),
                    in_location=p_in,
                    type=param_type,
                    required=p.get("required", False),
                    description=p.get("description"),
                    default=p.get("default") or schema_info.get("default"),
                    enum=p.get("enum") or schema_info.get("enum")
                ))

        # OpenAPI 3.x requestBody
        if "requestBody" in op and isinstance(op["requestBody"], dict):
            rb = op["requestBody"]
            content_dict = rb.get("content", {})
            content_type = "application/json"
            schema_def = {}
            if content_dict and isinstance(content_dict, dict):
                content_type = list(content_dict.keys())[0]
                first_media = content_dict[content_type]
                if isinstance(first_media, dict):
                    schema_def = first_media.get("schema", {})

            req_body = RequestBodySchema(
                content_type=content_type,
                schema_definition=schema_def,
                required=rb.get("required", True),
                description=rb.get("description")
            )

        # Parse responses
        responses: List[ResponseSchema] = []
        errors: List[ErrorFormatSchema] = []

        raw_responses = op.get("responses", {})
        if isinstance(raw_responses, dict):
            for status_code_str, resp_def in raw_responses.items():
                if not isinstance(resp_def, dict):
                    continue
                
                try:
                    status_code = int(status_code_str)
                except ValueError:
                    status_code = 200

                resp_desc = resp_def.get("description", "")
                resp_schema_def = {}
                content_type = "application/json"

                if "content" in resp_def and isinstance(resp_def["content"], dict):
                    if resp_def["content"]:
                        content_type = list(resp_def["content"].keys())[0]
                        resp_schema_def = resp_def["content"][content_type].get("schema", {})
                elif "schema" in resp_def:
                    resp_schema_def = resp_def.get("schema", {})

                if status_code >= 400:
                    errors.append(ErrorFormatSchema(
                        status_code=status_code,
                        description=resp_desc,
                        schema_definition=resp_schema_def
                    ))
                else:
                    responses.append(ResponseSchema(
                        status_code=status_code,
                        description=resp_desc,
                        content_type=content_type,
                        schema_definition=resp_schema_def
                    ))

        # Detect pagination
        pagination = self._detect_pagination(parameters, responses)

        # Detect constraints
        constraints = []
        if op.get("deprecated"):
            constraints.append("Deprecated endpoint")

        return EndpointSchema(
            name=name,
            summary=summary,
            description=description,
            method=method,
            path=path,
            parameters=parameters,
            request_body=req_body,
            responses=responses,
            errors=errors,
            pagination=pagination,
            constraints=constraints
        )

    def _parse_postman(self, data: Dict[str, Any], source_url: Optional[str]) -> NormalizedAPISpec:
        info = data.get("info", {})
        api_name = info.get("name", "Postman Collection API")
        description = info.get("description", "")

        endpoints: List[EndpointSchema] = []
        items = data.get("item", [])

        def flatten_items(item_list: List[Any]):
            for item in item_list:
                if not isinstance(item, dict):
                    continue
                if "item" in item and isinstance(item["item"], list):
                    flatten_items(item["item"])
                elif "request" in item:
                    endpoints.append(self._parse_postman_item(item))

        flatten_items(items)

        return NormalizedAPISpec(
            api_name=api_name,
            version="1.0.0",
            description=description,
            endpoints=endpoints,
            source_url=source_url
        )

    def _parse_postman_item(self, item: Dict[str, Any]) -> EndpointSchema:
        name = item.get("name", "endpoint")
        req = item.get("request", {})
        
        method = "GET"
        path = "/"
        
        if isinstance(req, dict):
            method = req.get("method", "GET").upper()
            url_info = req.get("url", {})
            if isinstance(url_info, dict):
                raw_path = url_info.get("raw", "/")
                if "?" in raw_path:
                    raw_path = raw_path.split("?")[0]
                if "://" in raw_path:
                    path = "/" + "/".join(raw_path.split("://")[1].split("/")[1:])
                else:
                    path = raw_path
            elif isinstance(url_info, str):
                path = url_info

        parameters: List[ParameterSchema] = []
        if isinstance(req, dict) and isinstance(req.get("url"), dict):
            query = req["url"].get("query", [])
            if isinstance(query, list):
                for q in query:
                    if isinstance(q, dict):
                        parameters.append(ParameterSchema(
                            name=q.get("key", ""),
                            in_location="query",
                            type="string",
                            description=q.get("description")
                        ))

        return EndpointSchema(
            name=re.sub(r'[^a_zA_Z0_9_]', '_', name.lower()).strip('_'),
            summary=name,
            method=method,
            path=path if path.startswith("/") else "/" + path,
            parameters=parameters
        )

    def _detect_pagination(self, parameters: List[ParameterSchema], responses: List[ResponseSchema]) -> Optional[PaginationSchema]:
        param_names = {p.name.lower(): p.name for p in parameters}
        
        # Offset-limit
        if ("limit" in param_names or "per_page" in param_names) and ("offset" in param_names or "skip" in param_names):
            return PaginationSchema(
                type="offset_limit",
                limit_param=param_names.get("limit") or param_names.get("per_page"),
                page_param=param_names.get("offset") or param_names.get("skip")
            )

        # Page-number
        if "page" in param_names or "page_number" in param_names:
            return PaginationSchema(
                type="page_number",
                page_param=param_names.get("page") or param_names.get("page_number"),
                limit_param=param_names.get("limit") or param_names.get("per_page") or param_names.get("size")
            )

        # Cursor
        if "cursor" in param_names or "starting_after" in param_names or "next_token" in param_names:
            return PaginationSchema(
                type="cursor",
                cursor_param=param_names.get("cursor") or param_names.get("starting_after") or param_names.get("next_token")
            )

        return None

    def _generate_endpoint_name(self, method: str, path: str, summary: str) -> str:
        if summary:
            clean = re.sub(r'[^a-zA-Z0-9_]', '_', summary.lower()).strip('_')
            clean = re.sub(r'_+', '_', clean)
            if clean:
                return clean
        
        # Fallback based on path and method
        clean_path = re.sub(r'\{[^}]+\}', '', path) # remove path params
        parts = [p for p in clean_path.split('/') if p]
        suffix = "_".join(parts) if parts else "root"
        return re.sub(r'[^a-zA-Z0-9_]', '_', f"{method.lower()}_{suffix}").strip('_')

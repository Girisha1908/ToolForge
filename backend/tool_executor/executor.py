import time
import httpx
import re
import json
from typing import Dict, Any, Optional, Tuple
from urllib.parse import urlparse, quote
from api_parser.fetcher import DocFetcher, SSRFSafeAsyncHTTPTransport
from tool_generator.schemas import ToolDefinition, ToolExecutionResult
from tool_executor.authentication import AuthHandler


class ToolExecutionError(Exception):
    """Custom exception raised when tool execution fails due to arguments or network issues."""
    def __init__(self, message: str, status_code: int = 400, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class ToolExecutor:
    """
    Generic HTTP Executor that executes tool definitions safely against external APIs.
    Performs path parameter substitution, query parameter assembly, JSON request body
    serialization, SSRF safety validation, and error handling.
    """

    def __init__(self, timeout: float = 15.0):
        self.timeout = timeout
        self.auth_handler = AuthHandler()

    async def execute(self, tool: ToolDefinition, arguments: Dict[str, Any]) -> ToolExecutionResult:
        start_time = time.time()

        # Step 1: Validate required arguments
        self._validate_arguments(tool, arguments)

        # Step 2: Build URL, path parameters, query parameters, and body payload
        target_url, remaining_params = self._build_path_url(tool, arguments)
        headers = {"User-Agent": "ToolForge-Executor/1.0", "Accept": "application/json, */*"}
        query_params: Dict[str, Any] = {}
        json_body: Optional[Dict[str, Any]] = None

        # Categorize remaining arguments into query, header, or body
        body_args = {}
        for param in tool.parameters:
            p_name = param.name
            if p_name in remaining_params:
                val = remaining_params[p_name]
                if param.in_location == "query":
                    query_params[p_name] = val
                elif param.in_location == "header":
                    headers[p_name] = str(val)
                elif param.in_location in ["body", "request_body"]:
                    body_args[p_name] = val

        # Handle request body if method supports body
        if tool.method in ["POST", "PUT", "PATCH"]:
            if body_args:
                json_body = body_args
            else:
                # If arguments contain body fields not explicitly in path/query
                non_path_query_args = {k: v for k, v in arguments.items() if k not in query_params and k not in headers and f"{{{k}}}" not in tool.path and f":{k}" not in tool.path}
                if non_path_query_args:
                    json_body = non_path_query_args

            if json_body is not None:
                headers["Content-Type"] = "application/json"

        # Apply authentication safely
        self.auth_handler.apply_auth(headers, query_params, tool.authentication)

        # Step 3: Validate target URL against SSRF safety rules
        resolved_ip, hostname = DocFetcher.validate_and_resolve_url(target_url)
        dns_map = {hostname: resolved_ip}

        parsed = urlparse(target_url)
        is_https = parsed.scheme == "https"

        transport = SSRFSafeAsyncHTTPTransport(
            dns_map=dns_map,
            verify=True if is_https else False,
            retries=2
        )

        # Step 4: Execute HTTP request
        try:
            async with httpx.AsyncClient(
                transport=transport,
                timeout=self.timeout,
                follow_redirects=False
            ) as client:
                res = await client.request(
                    method=tool.method,
                    url=target_url,
                    params=query_params,
                    headers=headers,
                    json=json_body
                )

                latency = round((time.time() - start_time) * 1000, 2)
                
                # Parse response payload
                try:
                    resp_data = res.json()
                except Exception:
                    resp_data = res.text

                success = res.status_code < 400

                # Build error message with truncated response snippet for 4xx/5xx
                error_msg = None
                if not success:
                    error_msg = f"HTTP {res.status_code}: {res.reason_phrase}"
                    body_snippet = self._format_error_body_snippet(resp_data)
                    if body_snippet:
                        error_msg += f" - {body_snippet}"

                return ToolExecutionResult(
                    success=success,
                    tool=tool.name,
                    status_code=res.status_code,
                    latency_ms=latency,
                    request={
                        "method": tool.method,
                        "url": target_url,
                        "path": tool.path,
                        "query_params": query_params
                    },
                    response=resp_data,
                    error=error_msg
                )

        except httpx.TimeoutException:
            latency = round((time.time() - start_time) * 1000, 2)
            return ToolExecutionResult(
                success=False,
                tool=tool.name,
                status_code=504,
                latency_ms=latency,
                request={"method": tool.method, "url": target_url, "path": tool.path},
                response=None,
                error=f"API request timed out after {self.timeout} seconds."
            )
        except Exception as exc:
            latency = round((time.time() - start_time) * 1000, 2)
            return ToolExecutionResult(
                success=False,
                tool=tool.name,
                status_code=500,
                latency_ms=latency,
                request={"method": tool.method, "url": target_url, "path": tool.path},
                response=None,
                error=f"Network/Execution error: {str(exc)}"
            )

    def _validate_arguments(self, tool: ToolDefinition, arguments: Dict[str, Any]) -> None:
        """Validates that all required parameters are supplied in arguments."""
        missing = []
        for param in tool.parameters:
            if param.required and param.name not in arguments and f"{{{param.name}}}" in tool.path:
                missing.append(param.name)

        if missing:
            raise ToolExecutionError(
                message=f"Missing required arguments for tool '{tool.name}': {', '.join(missing)}",
                status_code=400,
                details={"missing_arguments": missing}
            )

    def _build_path_url(self, tool: ToolDefinition, arguments: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """Substitutes path parameters (safely URL-encoded) and constructs full target URL."""
        base_url = (tool.base_url or "https://api.example.com").strip()
        path = (tool.path or "/").strip()

        # Ensure base_url has scheme
        if not (base_url.startswith("http://") or base_url.startswith("https://")):
            if base_url.startswith("/"):
                base_url = f"https://api.example.com{base_url}"
            else:
                base_url = f"https://{base_url}"

        remaining_args = dict(arguments)

        # Substitute {param} or :param in path with urllib.parse.quote(val, safe="")
        path_params = re.findall(r'\{([a-zA-Z0-9_]+)\}|:([a-zA-Z0-9_]+)', path)
        for p_tuple in path_params:
            p_name = p_tuple[0] or p_tuple[1]
            if p_name in remaining_args:
                raw_val = str(remaining_args.pop(p_name))
                encoded_val = quote(raw_val, safe="")
                path = path.replace(f"{{{p_name}}}", encoded_val).replace(f":{p_name}", encoded_val)
            else:
                raise ToolExecutionError(f"Path parameter '{p_name}' was not provided in arguments.")

        # Construct final URL avoiding path duplication or double slashes
        parsed_base = urlparse(base_url)
        origin = f"{parsed_base.scheme}://{parsed_base.netloc}"
        base_path = parsed_base.path.rstrip("/")
        clean_path = path if path.startswith("/") else f"/{path}"

        if base_path and (clean_path == base_path or clean_path.startswith(f"{base_path}/")):
            full_url = f"{origin}{clean_path}"
        else:
            full_url = f"{base_url.rstrip('/')}/{clean_path.lstrip('/')}"

        return full_url, remaining_args

    @staticmethod
    def _format_error_body_snippet(resp_data: Any, max_len: int = 250) -> Optional[str]:
        """Formats and truncates error response data into a sanitized snippet."""
        if not resp_data:
            return None

        if isinstance(resp_data, dict):
            # Extract common error fields if present
            msg = resp_data.get("message") or resp_data.get("error") or resp_data.get("detail")
            if msg:
                snippet = str(msg)
            else:
                snippet = json.dumps(resp_data)
        elif isinstance(resp_data, str):
            snippet = resp_data.strip()
        else:
            snippet = str(resp_data)

        # Sanitize single-line & truncate
        snippet = re.sub(r'[\r\n\t]+', ' ', snippet)
        if len(snippet) > max_len:
            snippet = snippet[:max_len] + "..."

        return snippet

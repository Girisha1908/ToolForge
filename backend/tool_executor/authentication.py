import os
from typing import Dict, Any, Optional
from api_parser.schemas import AuthenticationSchema


class AuthHandler:
    """Handles server-side authentication headers and query parameters safely without exposing secrets."""

    @staticmethod
    def apply_auth(headers: Dict[str, str], query_params: Dict[str, Any], auth_config: AuthenticationSchema) -> None:
        """
        Applies authentication headers or query parameters from server-side environment variables.
        Never hardcodes credentials or logs keys/tokens.
        """
        if not auth_config or auth_config.type == "none":
            return

        auth_type = auth_config.type.lower()
        header_or_param_name = auth_config.name or "Authorization"

        if auth_type == "bearer":
            # Priority: AUTH_BEARER_TOKEN -> API_BEARER_TOKEN -> BEARER_TOKEN
            token = os.environ.get("AUTH_BEARER_TOKEN") or os.environ.get("API_BEARER_TOKEN") or os.environ.get("BEARER_TOKEN")
            if token:
                headers["Authorization"] = f"Bearer {token.strip()}"

        elif auth_type == "api_key":
            # Priority: API_KEY -> X_API_KEY
            key_val = os.environ.get("API_KEY") or os.environ.get("X_API_KEY")
            if key_val:
                if auth_config.in_location == "query":
                    query_params[header_or_param_name] = key_val.strip()
                else:
                    headers[header_or_param_name] = key_val.strip()

        elif auth_type == "basic":
            # Priority: BASIC_AUTH_TOKEN -> BASIC_AUTH_CREDENTIALS
            basic_val = os.environ.get("BASIC_AUTH_TOKEN") or os.environ.get("BASIC_AUTH_CREDENTIALS")
            if basic_val:
                if not basic_val.lower().startswith("basic "):
                    basic_val = f"Basic {basic_val.strip()}"
                headers["Authorization"] = basic_val

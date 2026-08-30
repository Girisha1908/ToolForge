import os
import base64
from typing import Dict, Any, Optional
from api_parser.schemas import AuthenticationSchema


class AuthHandler:
    """Handles server-side authentication headers and query parameters safely without exposing secrets."""

    @staticmethod
    def is_valid_credential(val: Optional[str]) -> bool:
        """Returns True if val is a non-empty, non-placeholder credential string."""
        if not val or not isinstance(val, str):
            return False
        cleaned = val.strip()
        if not cleaned:
            return False
        # Filter out default placeholder values from .env.example
        if (
            cleaned.startswith("your_")
            or cleaned.endswith("_here")
            or cleaned in ("placeholder", "your_bearer_token_here", "your_api_key_here", "your_x_api_key_here", "your_basic_auth_token_here")
        ):
            return False
        return True

    def apply_auth(self, headers: Dict[str, str], query_params: Dict[str, Any], auth_config: AuthenticationSchema) -> None:
        """
        Applies authentication headers or query parameters from server-side environment variables.
        Never hardcodes credentials or logs keys/tokens.
        """
        auth_type = (auth_config.type or "none").lower() if auth_config else "none"
        header_or_param_name = auth_config.name if (auth_config and auth_config.name) else "Authorization"

        # 1. Basic Authentication (supports TWILIO_ACCOUNT_SID + TWILIO_AUTH_TOKEN or BASIC_AUTH_TOKEN)
        account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
        auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
        raw_basic = os.environ.get("BASIC_AUTH_TOKEN") or os.environ.get("BASIC_AUTH_CREDENTIALS")

        if self.is_valid_credential(account_sid) and self.is_valid_credential(auth_token):
            user_pass = f"{account_sid.strip()}:{auth_token.strip()}"
            headers["Authorization"] = f"Basic {base64.b64encode(user_pass.encode()).decode()}"
        elif self.is_valid_credential(raw_basic):
            basic_str = raw_basic.strip()
            if not basic_str.lower().startswith("basic "):
                basic_str = f"Basic {basic_str}"
            headers["Authorization"] = basic_str

        # 2. Bearer Authentication
        if "Authorization" not in headers and auth_type == "bearer":
            bearer_token = (
                os.environ.get("AUTH_BEARER_TOKEN")
                or os.environ.get("API_BEARER_TOKEN")
                or os.environ.get("BEARER_TOKEN")
                or os.environ.get("TWILIO_BEARER_TOKEN")
            )
            if self.is_valid_credential(bearer_token):
                headers["Authorization"] = f"Bearer {bearer_token.strip()}"

        # 3. API Key Authentication
        if auth_type == "api_key":
            api_key_val = (
                os.environ.get("API_KEY")
                or os.environ.get("X_API_KEY")
                or os.environ.get("TWILIO_API_KEY")
            )
            if self.is_valid_credential(api_key_val):
                if auth_config and auth_config.in_location == "query":
                    query_params[header_or_param_name] = api_key_val.strip()
                else:
                    headers[header_or_param_name] = api_key_val.strip()

        # 4. Error check if authentication was required by schema but no valid credentials exist in server environment
        if (
            auth_type in ["basic", "bearer", "api_key"]
            and "Authorization" not in headers
            and header_or_param_name not in headers
            and header_or_param_name not in query_params
        ):
            from tool_executor.executor import ToolExecutionError
            raise ToolExecutionError(
                message=f"Tool requires '{auth_type}' authentication, but no valid credentials were found in server environment variables. Please configure environment credentials in .env.",
                status_code=401
            )

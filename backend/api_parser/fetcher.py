import httpx
import re
import socket
import ipaddress
from urllib.parse import urlparse
from html.parser import HTMLParser
from typing import Tuple, Dict, Any, Optional, List


class DocFetchError(Exception):
    """Custom exception raised when documentation fetching fails."""
    pass


class HTMLTextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.result = []
        self.skip_tags = {"script", "style", "noscript", "svg", "header", "footer", "nav"}
        self.current_skip = 0

    def handle_starttag(self, tag, attrs):
        if tag.lower() in self.skip_tags:
            self.current_skip += 1
        elif tag.lower() in ["h1", "h2", "h3", "h4", "h5", "h6", "p", "div", "tr", "li"]:
            self.result.append("\n")

    def handle_endtag(self, tag):
        if tag.lower() in self.skip_tags:
            if self.current_skip > 0:
                self.current_skip -= 1
        elif tag.lower() in ["h1", "h2", "h3", "h4", "h5", "h6", "p", "div", "tr", "li"]:
            self.result.append("\n")

    def handle_data(self, data):
        if self.current_skip == 0:
            text = data.strip()
            if text:
                self.result.append(f" {text} ")

    def get_text(self) -> str:
        raw_text = "".join(self.result)
        # Collapse multiple empty lines / spaces
        lines = [re.sub(r'[ \t]+', ' ', line).strip() for line in raw_text.splitlines()]
        cleaned = "\n".join(line for line in lines if line)
        return cleaned


class SSRFSafeAsyncHTTPTransport(httpx.AsyncHTTPTransport):
    """
    Custom httpx transport that hooks TCP socket creation to route connections to
    pre-validated public IP addresses, preventing DNS rebinding while preserving the original
    hostname in request.url for TLS SNI extension and SSL certificate verification.
    """
    def __init__(self, dns_map: Dict[str, Any], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dns_map = dns_map  # hostname -> pre-validated resolved_ip or list of resolved_ips

        original_connect_tcp = self._pool._network_backend.connect_tcp

        async def ssrf_connect_tcp(host: str, port: int, **kw):
            target_ip = self.dns_map.get(host, host)
            if isinstance(target_ip, (list, tuple, set)):
                last_exc = None
                for ip in target_ip:
                    try:
                        return await original_connect_tcp(ip, port, **kw)
                    except Exception as exc:
                        last_exc = exc
                if last_exc:
                    raise last_exc
            return await original_connect_tcp(target_ip, port, **kw)

        self._pool._network_backend.connect_tcp = ssrf_connect_tcp


class DocFetcher:
    """Fetches raw API documentation from a URL or raw text input."""

    MAX_TEXT_SIZE = 10_000_000  # Maximum input size limit (10MB for large JSON/YAML specs)
    MAX_HTML_SIZE = 100_000     # Maximum size limit for HTML extraction (100k characters)

    @staticmethod
    def validate_url(url: str) -> bool:
        """Validates that a string is a well-formed http/https URL."""
        try:
            result = urlparse(url)
            return all([result.scheme in ("http", "https"), result.netloc])
        except Exception:
            return False

    @classmethod
    def is_safe_public_ip(cls, ip_str: str) -> bool:
        """Checks if an IP string is a safe public IPv4/IPv6 address."""
        try:
            ip = ipaddress.ip_address(ip_str)
            return not (
                ip.is_private
                or ip.is_loopback
                or ip.is_reserved
                or ip.is_link_local
                or ip.is_multicast
                or ip.is_unspecified
            )
        except ValueError:
            return False

    @classmethod
    def validate_and_resolve_url(cls, url: str) -> Tuple[List[str], str]:
        """
        Validates URL against SSRF and resolves host IPs.
        Returns tuple of (resolved_ips_list, hostname).
        Throws DocFetchError if unsafe or unreachable.
        """
        if not cls.validate_url(url):
            raise DocFetchError(f"Invalid URL schema or format: {url}")

        parsed = urlparse(url)
        hostname = parsed.hostname
        if not hostname:
            raise DocFetchError(f"Invalid hostname in URL: {url}")

        # Check direct IP addresses
        try:
            ip = ipaddress.ip_address(hostname)
            if not cls.is_safe_public_ip(str(ip)):
                raise DocFetchError(f"Access to private/reserved IP address {hostname} is blocked for security reasons.")
            return [str(ip)], hostname
        except ValueError:
            pass

        # Resolve hostname via DNS
        try:
            addr_info = socket.getaddrinfo(hostname, parsed.port or (443 if parsed.scheme == "https" else 80), socket.AF_UNSPEC, socket.SOCK_STREAM)
            resolved_ips = list({info[4][0] for info in addr_info})
        except Exception as exc:
            raise DocFetchError(f"DNS resolution failed for hostname {hostname}: {str(exc)}")

        if not resolved_ips:
            raise DocFetchError(f"No IP address found for hostname {hostname}")

        for ip_str in resolved_ips:
            if not cls.is_safe_public_ip(ip_str):
                raise DocFetchError(f"Hostname {hostname} resolves to private/reserved IP address {ip_str}, which is blocked for security reasons.")

        # Return list of resolved safe IPs and original hostname
        return resolved_ips, hostname

    async def fetch(self, url_or_raw: str, timeout: float = 30.0) -> Tuple[str, str]:
        """
        Fetches content from URL or returns raw string.
        Returns tuple of (content_type, content_string).
        content_type can be 'json', 'yaml', 'html', 'text', or 'raw'.
        """
        if not url_or_raw or not url_or_raw.strip():
            raise DocFetchError("URL or content input cannot be empty.")

        url_or_raw = url_or_raw.strip()

        # Check if it's already a JSON string or YAML string or raw text
        if not self.validate_url(url_or_raw):
            text_content = url_or_raw[:self.MAX_TEXT_SIZE]
            return self._detect_raw_content_type(text_content)

        # Validate URL and resolve IP safely against SSRF
        resolved_ips, hostname = self.validate_and_resolve_url(url_or_raw)
        dns_map = {hostname: resolved_ips}

        parsed = urlparse(url_or_raw)
        is_https = parsed.scheme == "https"

        transport = SSRFSafeAsyncHTTPTransport(
            dns_map=dns_map,
            verify=True if is_https else False,
            retries=2
        )

        try:
            async with httpx.AsyncClient(
                transport=transport,
                follow_redirects=False,
                timeout=timeout
            ) as client:
                
                curr_url = url_or_raw
                redirects = 0

                while redirects < 5:
                    response = await client.get(curr_url, headers={
                        "User-Agent": "ToolForge-DocParser/1.0 (API Specification Parser)",
                        "Accept": "application/json, application/x-yaml, text/yaml, text/html, text/plain, */*"
                    })
                    
                    if response.is_redirect or response.status_code in (301, 302, 303, 307, 308):
                        redirect_location = response.headers.get("location")
                        if not redirect_location:
                            break
                        
                        # Handle relative vs absolute redirect URLs
                        if not redirect_location.startswith("http://") and not redirect_location.startswith("https://"):
                            p_curr = urlparse(curr_url)
                            redirect_location = f"{p_curr.scheme}://{p_curr.netloc}{redirect_location}"

                        # Validate SSRF on redirect URL
                        res_ips, res_host = self.validate_and_resolve_url(redirect_location)
                        dns_map[res_host] = res_ips
                        curr_url = redirect_location
                        redirects += 1
                        continue

                    if response.status_code >= 400:
                        raise DocFetchError(f"HTTP Error {response.status_code} when fetching documentation: {response.reason_phrase}")
                    
                    content_type_header = response.headers.get("content-type", "").lower()
                    text_content = response.text[:self.MAX_TEXT_SIZE]

                    if "json" in content_type_header:
                        return ("json", text_content)
                    elif "yaml" in content_type_header or "yml" in content_type_header:
                        return ("yaml", text_content)
                    elif "html" in content_type_header:
                        return ("html", text_content)
                    else:
                        return self._detect_raw_content_type(text_content)

                raise DocFetchError("Too many HTTP redirects when fetching documentation.")

        except httpx.RequestError as exc:
            raise DocFetchError(f"Failed to connect to {url_or_raw}: {str(exc)}")
        except Exception as exc:
            if isinstance(exc, DocFetchError):
                raise exc
            raise DocFetchError(f"Unexpected error fetching documentation: {str(exc)}")

    @staticmethod
    def _detect_raw_content_type(text: str) -> Tuple[str, str]:
        stripped = text.strip()
        if (stripped.startswith("{") and stripped.endswith("}")) or (stripped.startswith("[") and stripped.endswith("]")):
            return ("json", text)
        if "openapi:" in stripped or "swagger:" in stripped or "info:" in stripped and "paths:" in stripped:
            return ("yaml", text)
        if "<html" in stripped.lower() or "<!doctype html" in stripped.lower():
            return ("html", text)
        return ("text", text)

    @classmethod
    def extract_text_from_html(cls, html_content: str) -> str:
        """Extracts readable structured text from HTML documentation with size safety."""
        truncated_html = html_content[:cls.MAX_HTML_SIZE]
        parser = HTMLTextExtractor()
        parser.feed(truncated_html)
        return parser.get_text()[:cls.MAX_HTML_SIZE]
